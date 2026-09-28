#!/usr/bin/env python3
"""No-Gazebo D5 sender loopback: close while moving, gen-2 reconnect, replay, B1 withholding."""
import json
import os
import socket
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
INPUTS = HERE.parent / 'inputs'
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(INPUTS))
import d5_setup_audit as audit  # noqa: E402
import d5_fixture as fx  # noqa: E402


def run(tmp, mode, regime, policy):
    root = Path(tmp)
    conns = []
    server = socket.socket()
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(('127.0.0.1', 5005))
    server.listen(2)
    server.settimeout(15)

    def serve():
        for _ in range(2):
            try:
                conn, _ = server.accept()
            except socket.timeout:
                return
            buf = b''
            while True:
                data = conn.recv(65536)
                if not data:
                    break
                buf += data
            conns.append([json.loads(x) for x in buf.decode().splitlines() if x])
            conn.close()
    thread = threading.Thread(target=serve)
    thread.start()
    env = dict(os.environ, TRIAL_ROOT=str(root), MODE=mode, INFO_REGIME=regime, CASE_ID='D5',
               XR_REARM_POLICY=policy, AGE_CONDITION='A000', PYTHONDONTWRITEBYTECODE='1')
    proc = subprocess.Popen([sys.executable, str(INPUTS / 'd1_sender.py')], env=env)
    while not (root / 'sender.ready').exists():
        time.sleep(.005)
    (root / 'barrier.json').write_text(json.dumps({'start_monotonic_ns': time.monotonic_ns() + 50_000_000}))
    assert proc.wait(timeout=30) == 0
    thread.join(timeout=10)
    server.close()
    return conns


class D5Sender(unittest.TestCase):
    def check(self, mode, regime, policy, withheld):
        with tempfile.TemporaryDirectory() as tmp:
            conns = run(tmp, mode, regime, policy)
            sent, errors = audit.fixture(Path(tmp))
            self.assertEqual(errors, [], (mode, regime, policy))
            self.assertEqual(len(conns), 2)
            first = [p['_qualification']['sample_id'] for p in conns[0]]
            second = [p['_qualification'] for p in conns[1]]
            self.assertEqual(first, [f'docker:{i}' for i in range(56)])          # closed while moving
            self.assertEqual({m['generation_id'] for m in second if m['sample_id'] != 'docker:72'}, {2})
            got = [r['index'] for r in sent if fx.spec(r['index'])['sent'] and not r['sent']]
            self.assertEqual(got, withheld, (mode, regime, policy))
            if 72 not in withheld:
                replay = next(m for m in second if m['sample_id'] == 'docker:72')
                self.assertEqual(replay['generation_id'], 1)                     # old gen on the new connection
            kinds = [json.loads(x)['kind'] for x in (Path(tmp) / 'sender_transport.jsonl').read_text().splitlines()]
            self.assertEqual(kinds, ['connect', 'source_close_while_moving', 'connect_new_generation'])
            if mode == 'b1':
                v = [json.loads(x) for x in (Path(tmp) / 'gate_verdict.jsonl').read_text().splitlines()]
                self.assertEqual(v[56]['kind'], 'b1_disconnect') if regime == 'full' else None
            return sent

    def test_b0_sends_everything(self):
        self.check('b0', 'full', 'R_EXPLICIT', [])

    def test_b1_full_r_explicit_withholds_held_grip_until_edge(self):
        self.check('b1', 'full', 'R_EXPLICIT', list(range(70, 90)))

    def test_b1_full_r_auto_withholds_until_dwell(self):
        self.check('b1', 'full', 'R_AUTO', list(range(70, 83)))

    def test_b1_native_cannot_see_generation(self):
        self.check('b1', 'native', 'R_EXPLICIT', [])

    def test_fixture_negative(self):
        with tempfile.TemporaryDirectory() as tmp:
            run(tmp, 'b0', 'full', 'R_AUTO')
            p = Path(tmp) / 'sent.jsonl'
            rows = [json.loads(x) for x in p.read_text().splitlines()]
            wire = json.loads(rows[72]['wire'])
            wire['_qualification']['generation_id'] = 2               # replay relabelled as current gen
            rows[72]['wire'] = json.dumps(wire)
            p.write_text(''.join(json.dumps(r) + '\n' for r in rows))
            self.assertIn('D5_FIXTURE_72', audit.fixture(Path(tmp))[1])


if __name__ == '__main__':
    unittest.main(verbosity=2)
