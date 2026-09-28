#!/usr/bin/env python3
"""No-Gazebo D4Q1 host regressions: predicate, fixture, sender loopback, joins."""
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
import d4_setup_audit as audit  # noqa: E402
from d4_age import CONDITIONS, PROFILES, expected, stamp  # noqa: E402
import servo_callback_drain  # noqa: E402


def allow_in_env(profile_ns, age_ns, teleop=True, generation=1, source_ns=None):
    code = ('import json,sys; sys.path.insert(0, sys.argv[1]); from d1_contract import d1_allow, FRESHNESS_NS;'
            'now=10**15; src=now-int(sys.argv[2]) if sys.argv[4]=="x" else int(sys.argv[4]);'
            'print(json.dumps([FRESHNESS_NS]+list(d1_allow({"isTracked":True}, sys.argv[3]=="1", src, now, %d))))'
            % generation)
    out = subprocess.run([sys.executable, '-c', code, str(INPUTS), str(age_ns), '1' if teleop else '0',
                          'x' if source_ns is None else str(source_ns)],
                         env=dict(os.environ, XR_FRESHNESS_NS=str(profile_ns)),
                         capture_output=True, text=True, check=True)
    return json.loads(out.stdout)


class Predicate(unittest.TestCase):
    def test_thresholds_inclusive_each_profile(self):
        for name, f in PROFILES.items():
            self.assertEqual(allow_in_env(f, 0)[:2], [f, True], name)
            self.assertTrue(allow_in_env(f, f)[1], f'{name} equality allowed')
            self.assertEqual(allow_in_env(f, f + 1)[1:], [False, 'STALE_SOURCE'])
            self.assertTrue(allow_in_env(f, -5_000_000)[1])
            self.assertEqual(allow_in_env(f, -5_000_001)[1:], [False, 'FUTURE_TIME'])
            self.assertEqual(allow_in_env(f, -1_000_000_000)[1:], [False, 'FUTURE_TIME'])
            self.assertEqual(allow_in_env(f, 0, source_ns=1_000_000_000)[1:], [False, 'STALE_SOURCE'])
            self.assertEqual(allow_in_env(f, f + 10**9, teleop=False)[1:], [True, 'INTENTIONAL_UNGRIPPED_NEUTRAL'])

    def test_default_profile_is_f250(self):
        env = {k: v for k, v in os.environ.items() if k != 'XR_FRESHNESS_NS'}
        out = subprocess.run([sys.executable, '-c', f'import sys; sys.path.insert(0,"{INPUTS}"); '
                              'import d1_contract; print(d1_contract.FRESHNESS_NS)'],
                             env=env, capture_output=True, text=True, check=True)
        self.assertEqual(int(out.stdout), 250_000_000)

    def test_analyzer_expectation_and_uncertainty(self):
        f = 250_000_000
        self.assertTrue(expected(f - 2_000_000, f))
        self.assertIsNone(expected(f, f))             # equality within uncertainty -> UNKNOWN
        self.assertIsNone(expected(f + 900_000, f))
        self.assertFalse(expected(f + 1_100_000, f))
        self.assertIsNone(expected(-5_000_000, f))
        self.assertFalse(expected(-7_000_000, f))
        self.assertTrue(expected(-3_000_000, f))

    def test_stamps(self):
        self.assertEqual(stamp('A000', 10**12), 10**12)
        self.assertEqual(stamp('A350', 10**12), 10**12 - 350_000_000)
        self.assertEqual(stamp('FUT1S', 10**12), 10**12 + 10**9)
        self.assertEqual(stamp('H1P0', 10**12), 1_000_000_000)
        self.assertEqual(stamp('H1P0', 5 * 10**12), 1_000_000_000)   # literal epoch value, not an offset
        self.assertNotEqual(stamp('H1P0', 10**12), stamp('A750', 10**12) - 250_000_000)


def run_sender(tmp, condition, mode, regime, profile_ns):
    root = Path(tmp)
    received = []
    server = socket.socket()
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(('127.0.0.1', 5005))
    server.listen(1)

    def accept():
        conn, _ = server.accept()
        buf = b''
        while True:
            data = conn.recv(65536)
            if not data:
                break
            buf += data
        received.extend(json.loads(x) for x in buf.decode().splitlines() if x)
        conn.close()
    thread = threading.Thread(target=accept)
    thread.start()
    env = dict(os.environ, TRIAL_ROOT=str(root), MODE=mode, INFO_REGIME=regime, CASE_ID='D4',
               AGE_CONDITION=condition, XR_FRESHNESS_NS=str(profile_ns), PYTHONDONTWRITEBYTECODE='1')
    proc = subprocess.Popen([sys.executable, str(INPUTS / 'd1_sender.py')], env=env)
    while not (root / 'sender.ready').exists():
        time.sleep(.005)
    start = time.monotonic_ns() + 50_000_000
    (root / 'barrier.json').write_text(json.dumps({'start_monotonic_ns': start}))
    assert proc.wait(timeout=20) == 0
    thread.join(timeout=5)
    server.close()
    return received


class SenderLoopback(unittest.TestCase):
    def check(self, condition, mode, regime, profile, expect_withheld):
        with tempfile.TemporaryDirectory() as tmp:
            received = run_sender(tmp, condition, mode, regime, PROFILES[profile])
            sent, errors = audit.fixture(Path(tmp), condition)
            self.assertEqual(errors, [], (condition, mode, profile))
            withheld = [r['index'] for r in sent if not r['sent']]
            self.assertEqual(withheld, expect_withheld, (condition, mode, profile))
            self.assertEqual([p['_qualification']['sample_id'] for p in received],
                             [f'docker:{r["index"]}' for r in sent if r['sent']])
            for p, r in zip(received, [r for r in sent if r['sent']]):
                self.assertEqual(p['_qualification']['source_timestamp_ns'], r['source_timestamp_ns'])
                self.assertEqual(p['timestamp'], r['source_timestamp_ns'] / 1e9)
            if mode == 'b1':
                verdicts = [json.loads(x) for x in (Path(tmp) / 'gate_verdict.jsonl').read_text().splitlines()]
                self.assertEqual(len(verdicts), 120)
                self.assertTrue(all(v['freshness_ns'] == PROFILES[profile] for v in verdicts))
            return sent

    def test_all_conditions_b1_full_f250(self):
        teleop = list(range(20, 56))
        for condition, withheld in (('A000', []), ('A050', []), ('A150', []), ('A350', teleop),
                                    ('A750', teleop), ('H1P0', teleop), ('FUT1S', teleop)):
            self.check(condition, 'b1', 'full', 'F250', withheld)

    def test_profiles_change_only_threshold(self):
        teleop = list(range(20, 56))
        self.check('A150', 'b1', 'full', 'F100', teleop)
        self.check('A350', 'b1', 'full', 'F500', [])
        self.check('A050', 'b1', 'full', 'F100', [])

    def test_native_and_b0_never_withhold(self):
        self.check('A750', 'b1', 'native', 'F250', [])
        sent = self.check('H1P0', 'b0', 'full', 'F250', [])
        self.assertEqual(len({r['source_timestamp_ns'] for r in sent}), 1)


class Joins(unittest.TestCase):
    def test_modules_resolve_to_d4_root(self):
        import d3_monitor_audit, post_capture_audit, calibration_audit, source_path_readiness
        root = str(HERE.parent)
        for module in (servo_callback_drain, d3_monitor_audit, post_capture_audit,
                       calibration_audit, source_path_readiness, audit):
            self.assertTrue(module.__file__.startswith(root), module.__file__)

    def test_drain_uses_recorded_stamp(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            payload = {'header': {'stamp': {'sec': 1, 'nanosec': 2}, 'frame_id': 'base_link'},
                       'twist': {'linear': {'x': .1, 'y': 0., 'z': 0.}, 'angular': {'x': 0., 'y': 0., 'z': 0.}}}
            origin = {'sample_id': 'docker:40', 'source_timestamp_ns': 500, 'phase': 'active'}
            (root / 'sent.jsonl').write_text(json.dumps({'index': 40, 'sent': True, 'sample_ns': 900,
                                                         'source_timestamp_ns': 500}) + '\n')
            (root / 'lineage.jsonl').write_text(json.dumps({'kind': 'publish', 'stage': 'bridge_servo_input',
                'command_id': 'b:1', 'monotonic_ns': 1000, 'parent': origin, 'payload': payload}) + '\n')
            (root / 'servo_callback_payload.jsonl').write_text(json.dumps({'stamp_sec': 1, 'stamp_nanosec': 2,
                'frame_id': 'base_link', 'linear': [.1, 0., 0.], 'angular': [0., 0., 0.], 'entry_ns': 1100}) + '\n')
            self.assertEqual(servo_callback_drain.audit(root)['status'], 'PASS')
            self.assertEqual(audit.callback_join(root)['exact_joins'], 1)
            self.assertAlmostEqual(audit.callback_join(root)['joined'][0]['source_age_at_callback_ms'], 0.0006)
            (root / 'sent.jsonl').write_text(json.dumps({'index': 40, 'sent': True, 'sample_ns': 900,
                                                         'source_timestamp_ns': 501}) + '\n')
            self.assertEqual(servo_callback_drain.audit(root)['status'], 'PENDING')
            self.assertEqual(audit.callback_join(root)['missing_count'], 1)

    def test_fixture_rejects_stamp_regeneration_and_reuse(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_sender(tmp, 'A350', 'b0', 'full', 250_000_000)
            path = Path(tmp) / 'sent.jsonl'
            rows = [json.loads(x) for x in path.read_text().splitlines()]
            bad = [dict(r) for r in rows]
            wire = json.loads(bad[40]['wire'])
            wire['_qualification']['source_timestamp_ns'] = bad[40]['sample_ns']  # regenerated stamp
            bad[40]['wire'] = json.dumps(wire)
            path.write_text(''.join(json.dumps(r) + '\n' for r in bad))
            self.assertIn('D4_FIXTURE_40', audit.fixture(Path(tmp), 'A350')[1])
            reuse = [dict(r) for r in rows]
            for r in reuse:
                r['source_timestamp_ns'] = rows[0]['source_timestamp_ns']
            path.write_text(''.join(json.dumps(r) + '\n' for r in reuse))
            self.assertIn('PER_SAMPLE_STAMP_REUSE_OR_HISTORICAL_MISMATCH', audit.fixture(Path(tmp), 'A350')[1])
            self.assertTrue(audit.fixture(Path(tmp), 'A350')[1])
            self.assertTrue(audit.fixture(Path(tmp), 'A000')[1])   # wrong condition label


if __name__ == '__main__':
    unittest.main(verbosity=2)
