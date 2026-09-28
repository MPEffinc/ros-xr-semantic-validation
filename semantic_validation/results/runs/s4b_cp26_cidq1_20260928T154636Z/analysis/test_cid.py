#!/usr/bin/env python3
"""No-Gazebo C-ID regressions: binding contract, ingestion duplicates, sender, coverage/drain."""
import copy
import json
import os
import socket
import struct
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
INPUTS = HERE.parent / 'inputs'
sys.path.insert(0, str(INPUTS))
import cid_fixture as fx  # noqa: E402
from cid_binding import (Ingestion, binding_hash, check, projection, projection_from_ros_fields,  # noqa: E402
                         projection_from_wire)
from receiver_coverage import check_receiver_coverage  # noqa: E402
import servo_callback_drain  # noqa: E402

F32 = lambda v: struct.unpack('f', struct.pack('f', v))[0]


def bound_sample(sid='docker:40', x=.35, teleop=True, stamp=10**12):
    native = {'isTracked': True}
    meta = dict(sample_id=sid, generation_id=1, source_timestamp_ns=stamp, native_state=native,
                binding_sha256=binding_hash(sid, 1, stamp, native, projection(True, [x, .2, .3], [0, 0, 0, 1],
                                                                              teleop, 1. if teleop else 0.)))
    payload = {'right_hand': {'isTracked': True, 'pos': {'x': x, 'y': .2, 'z': .3},
                              'rot': {'x': 0., 'y': 0., 'z': 0., 'w': 1.}},
               'controls': {'right_teleop_enable': teleop, 'teleop_enable': teleop, 'grip_value': 1. if teleop else 0.},
               '_qualification': meta}
    return meta, payload


def ros_fields_as_receiver(payload):
    """What the pinned receiver's _parse_payload/_make_msg put into ReceivedPoseStates."""
    hand, c = payload['right_hand'], payload['controls']
    return {'tracked': bool(hand['isTracked']),
            'pose': {'position': {a: float(hand['pos'][a]) for a in 'xyz'},
                     'orientation': {a: float(hand['rot'][a]) for a in 'xyzw'}},
            'teleop_enable': bool(c.get('right_teleop_enable', c.get('teleop_enable'))),
            'grip_value': F32(float(c['grip_value']))}


class Binding(unittest.TestCase):
    def test_valid_sample_binds_at_every_check_point(self):
        meta, payload = bound_sample()
        self.assertEqual(check(meta, projection_from_wire(payload)), (True, 'BOUND'))
        self.assertEqual(check(meta, projection_from_ros_fields(ros_fields_as_receiver(payload))), (True, 'BOUND'))

    def test_every_command_field_mutation_is_a_mismatch(self):
        meta, payload = bound_sample()
        for path, value in ((('right_hand', 'pos', 'x'), .65), (('right_hand', 'pos', 'z'), .31),
                            (('right_hand', 'rot', 'w'), .9), (('right_hand', 'isTracked'), False),
                            (('controls', 'right_teleop_enable'), False), (('controls', 'grip_value'), .5)):
            p = copy.deepcopy(payload)
            node = p
            for k in path[:-1]:
                node = node[k]
            node[path[-1]] = value
            for proj in (projection_from_wire(p), projection_from_ros_fields(ros_fields_as_receiver(p))):
                self.assertEqual(check(meta, proj), (False, 'STATE_COMMAND_MISMATCH'), path)

    def test_non_command_field_change_is_not_a_mismatch(self):
        # The pinned receiver takes right_teleop_enable before teleop_enable, so changing
        # only teleop_enable does not change the command it produces (attempt 1 retained).
        meta, payload = bound_sample()
        payload['controls']['teleop_enable'] = False
        self.assertEqual(ros_fields_as_receiver(payload)['teleop_enable'], True)
        self.assertEqual(check(meta, projection_from_ros_fields(ros_fields_as_receiver(payload))), (True, 'BOUND'))

    def test_state_claim_mismatch_detected(self):
        meta, payload = bound_sample()
        m = dict(meta, native_state={'isTracked': False})
        self.assertEqual(check(m, projection_from_wire(payload))[1], 'STATE_COMMAND_MISMATCH')

    def test_missing_fields_and_id(self):
        meta, payload = bound_sample()
        proj = projection_from_wire(payload)
        for key, reason in (('sample_id', 'MISSING_SOURCE_EVENT_ID'), ('generation_id', 'MISSING_REQUIRED_FIELD'),
                            ('source_timestamp_ns', 'MISSING_REQUIRED_FIELD'), ('native_state', 'MISSING_REQUIRED_FIELD'),
                            ('binding_sha256', 'MISSING_REQUIRED_FIELD')):
            m = {k: v for k, v in meta.items() if k != key}
            self.assertEqual(check(m, proj), (False, reason), key)
        self.assertEqual(check(None, proj), (False, 'UNBOUND_REQUIRED_STATE'))

    def test_reference_regenerated_downstream_would_hide_the_mismatch(self):
        # Anti-pattern demonstration: recomputing the "reference" from the modified
        # downstream payload always agrees; the contract forbids it.
        meta, payload = bound_sample()
        payload['right_hand']['pos']['x'] = .65
        proj = projection_from_wire(payload)
        forged = dict(meta, binding_sha256=binding_hash(meta['sample_id'], 1, meta['source_timestamp_ns'],
                                                        meta['native_state'], proj))
        self.assertEqual(check(forged, proj), (True, 'BOUND'))           # what a regenerated reference would say
        self.assertEqual(check(meta, proj)[1], 'STATE_COMMAND_MISMATCH')  # the independent reference catches it


class Duplicates(unittest.TestCase):
    def test_cached_repeat_is_not_duplicate_new_ingestion_is(self):
        g = Ingestion()
        self.assertEqual(g.observe('docker:40', 111), (True, 'NEW_OR_CACHED'))
        self.assertEqual(g.observe('docker:40', 111), (True, 'NEW_OR_CACHED'))   # cached republication
        self.assertEqual(g.observe('docker:41', 222), (True, 'NEW_OR_CACHED'))
        self.assertEqual(g.observe('docker:40', 333), (False, 'DUPLICATE_SOURCE_EVENT_ID'))
        self.assertEqual(g.observe(None, 1)[0], False)
        self.assertEqual(g.observe('docker:42', None), (False, 'MISSING_INGESTION_KEY'))


def run_sender(tmp, mode, regime, kind):
    root = Path(tmp)
    got = []
    server = socket.socket()
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(('127.0.0.1', 5005))
    server.listen(1)

    def serve():
        conn, _ = server.accept()
        buf = b''
        while True:
            data = conn.recv(65536)
            if not data:
                break
            buf += data
        got.extend(json.loads(x) for x in buf.decode().splitlines() if x)
        conn.close()
    th = threading.Thread(target=serve)
    th.start()
    env = dict(os.environ, TRIAL_ROOT=str(root), MODE=mode, INFO_REGIME=regime, CASE_ID='CID', CID_KIND=kind,
               AGE_CONDITION='A000', XR_REARM_POLICY='R_EXPLICIT', PYTHONDONTWRITEBYTECODE='1')
    proc = subprocess.Popen([sys.executable, str(INPUTS / 'd1_sender.py')], env=env)
    while not (root / 'sender.ready').exists():
        time.sleep(.005)
    (root / 'barrier.json').write_text(json.dumps({'start_monotonic_ns': time.monotonic_ns() + 50_000_000}))
    assert proc.wait(timeout=20) == 0
    th.join(timeout=5)
    server.close()
    return got, [json.loads(x) for x in (root / 'sent.jsonl').read_text().splitlines()]


class Sender(unittest.TestCase):
    def test_kinds(self):
        for kind in fx.KINDS:
            for mode, regime, withheld in (('b0', 'full', []), ('b1', 'native', []),
                                           ('b1', 'full', list(range(50, 56)))):
                with tempfile.TemporaryDirectory() as tmp:
                    got, sent = run_sender(tmp, mode, regime, kind)
                    self.assertEqual([r['index'] for r in sent if not r['sent']], withheld, (kind, mode, regime))
                    metas = [p['_qualification'] for p in got]
                    self.assertEqual(len(metas), 120 - len(withheld))
                    inj = json.loads(sent[50]['wire'])
                    m = inj['_qualification']
                    ok, reason = check(m, projection_from_wire(inj))
                    expect = {'MISSING_FIELD': 'MISSING_REQUIRED_FIELD', 'MISSING_ID': 'MISSING_SOURCE_EVENT_ID',
                              'DUPLICATE_ID': 'BOUND', 'MISMATCH': 'STATE_COMMAND_MISMATCH'}[kind]
                    self.assertEqual(reason, expect, kind)
                    for r in sent:           # every other sample binds at the wire
                        if r['index'] != 50:
                            w = json.loads(r['wire'])
                            self.assertEqual(check(w['_qualification'], projection_from_wire(w)), (True, 'BOUND'))
                    if kind == 'DUPLICATE_ID':
                        self.assertEqual(m['sample_id'], 'docker:40')
                    if mode == 'b1' and regime == 'full':
                        v = [json.loads(x) for x in (Path(tmp) / 'gate_verdict.jsonl').read_text().splitlines()]
                        want = expect if kind != 'DUPLICATE_ID' else 'DUPLICATE_SOURCE_EVENT_ID'
                        self.assertEqual(v[50]['reason'], want)
                        self.assertTrue(all(x['reason'] == 'DISARMED_HELD_GRIP' or x['reason'] == 'DISARMED_DWELL'
                                            for x in v[51:56]))


class CoverageAndDrain(unittest.TestCase):
    def test_coverage_uses_wire_ids(self):
        sent = []
        lineage = []
        for i, sid in enumerate(['docker:0', 'docker:40', None]):
            sent.append(dict(index=i, sent=True, wire=json.dumps({'_qualification': {'sample_id': sid}})))
            lineage.append(dict(kind='source_received', metadata={'sample_id': sid}))
            if sid is not None:
                lineage.append(dict(kind='original_receiver_source_stored', sample_id=sid))
        self.assertTrue(check_receiver_coverage(sent, lineage)['ok'])
        self.assertFalse(check_receiver_coverage(sent, lineage[:-1])['ok'])

    def test_drain_matches_wire_id_and_stamp(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            payload = {'header': {'stamp': {'sec': 1, 'nanosec': 2}, 'frame_id': 'base_link'},
                       'twist': {'linear': {'x': .1, 'y': 0., 'z': 0.}, 'angular': {'x': 0., 'y': 0., 'z': 0.}}}
            (root / 'sent.jsonl').write_text(json.dumps({'index': 50, 'sent': True, 'sample_ns': 7,
                'wire': json.dumps({'_qualification': {'sample_id': 'docker:40', 'source_timestamp_ns': 7}})}) + '\n')
            (root / 'lineage.jsonl').write_text(json.dumps({'kind': 'publish', 'stage': 'bridge_servo_input',
                'command_id': 'b:1', 'monotonic_ns': 9, 'payload': payload,
                'parent': {'sample_id': 'docker:40', 'source_timestamp_ns': 7}}) + '\n')
            (root / 'servo_callback_payload.jsonl').write_text(json.dumps({'stamp_sec': 1, 'stamp_nanosec': 2,
                'frame_id': 'base_link', 'linear': [.1, 0., 0.], 'angular': [0., 0., 0.], 'entry_ns': 10}) + '\n')
            self.assertEqual(servo_callback_drain.audit(root)['status'], 'PASS')


if __name__ == '__main__':
    unittest.main(verbosity=2)
