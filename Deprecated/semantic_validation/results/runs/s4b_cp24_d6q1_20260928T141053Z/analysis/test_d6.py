#!/usr/bin/env python3
"""No-Gazebo D6 regressions: registered recovery timeline and sender loopback."""
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
import d6_setup_audit as audit  # noqa: E402
import d6_fixture as fx  # noqa: E402
from d5_rearm import Rearm  # noqa: E402


class Timeline(unittest.TestCase):
    def run_policy(self, policy):
        r, out = Rearm(policy), {}
        for i in range(fx.SLOTS):
            s = fx.spec(i)
            out[i] = r.sample(1, s['teleop'], s['tracked'], i * fx.PERIOD_NS, i * fx.PERIOD_NS + 200_000, True)
        return r, out

    def test_r_explicit(self):
        r, out = self.run_policy('R_EXPLICIT')
        self.assertTrue(all(out[i][0] for i in range(56)))
        self.assertTrue(all(out[i] == (False, 'INVALID_TRACKING') for i in fx.INVALID))
        self.assertFalse(any(out[i][0] for i in fx.HELD))                   # held grip never restarts
        self.assertEqual(out[fx.EDGE_INDEX], (True, 'R_EXPLICIT_REARMED_ON_RISING_EDGE'))
        self.assertTrue(all(out[i][0] for i in range(fx.EDGE_INDEX, fx.SLOTS)))

    def test_r_auto(self):
        r, out = self.run_policy('R_AUTO')
        first = min(i for i in fx.HELD if out[i][0])
        self.assertEqual(first, 86)                                        # 500 ms after the first valid sample 76
        self.assertEqual(out[first], (True, 'R_AUTO_REARMED'))
        self.assertTrue(all(out[i][0] for i in range(first, fx.SLOTS)))


def run(tmp, mode, regime, policy, idle_drop_s=1.5):
    root = Path(tmp)
    got = []
    server = socket.socket()
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(('127.0.0.1', 5005))
    server.listen(2)
    server.settimeout(15)

    def serve():
        while True:
            try:
                conn, _ = server.accept()
            except socket.timeout:
                return
            conn.settimeout(.05)
            last, buf, peer = time.monotonic(), b'', False
            while True:
                try:
                    data = conn.recv(65536)
                except socket.timeout:
                    if time.monotonic() - last > idle_drop_s:
                        break
                    continue
                if not data:
                    peer = True
                    break
                buf, last = buf + data, time.monotonic()
            got.extend(json.loads(x) for x in buf.decode().splitlines() if x)
            conn.close()
            if peer:
                return
    th = threading.Thread(target=serve)
    th.start()
    env = dict(os.environ, TRIAL_ROOT=str(root), MODE=mode, INFO_REGIME=regime, CASE_ID='D6',
               XR_REARM_POLICY=policy, AGE_CONDITION='A000', PYTHONDONTWRITEBYTECODE='1')
    proc = subprocess.Popen([sys.executable, str(INPUTS / 'd1_sender.py')], env=env)
    while not (root / 'sender.ready').exists():
        time.sleep(.005)
    (root / 'barrier.json').write_text(json.dumps({'start_monotonic_ns': time.monotonic_ns() + 50_000_000}))
    assert proc.wait(timeout=30) == 0
    th.join(timeout=20)
    server.close()
    return got


class Sender(unittest.TestCase):
    def check(self, mode, regime, policy, withheld):
        with tempfile.TemporaryDirectory() as tmp:
            got = run(tmp, mode, regime, policy)
            sent, errors = audit.fixture(Path(tmp))
            self.assertEqual(errors, [], (mode, regime, policy))
            self.assertEqual([r['index'] for r in sent if not r['sent']], withheld, (mode, regime, policy))
            self.assertEqual([p['_qualification']['sample_id'] for p in got],
                             [f'docker:{r["index"]}' for r in sent if r['sent']])      # nothing lost, no retransmit
            kinds = [json.loads(x)['kind'] for x in (Path(tmp) / 'sender_transport.jsonl').read_text().splitlines()]
            return kinds

    def test_b0(self):
        self.assertEqual(self.check('b0', 'full', 'R_EXPLICIT', []), ['connect'])

    def test_b1_full_r_explicit(self):
        kinds = self.check('b1', 'full', 'R_EXPLICIT', list(range(56, 92)))   # 1.8 s withheld
        self.assertEqual(kinds, ['connect', 'reconnect_after_peer_close'])    # original 1.5 s idle drop

    def test_b1_full_r_auto(self):
        # The 500 ms dwell boundary falls exactly on slot 86 at the real-time source;
        # microsecond jitter may defer the re-arm to slot 87 (attempt 1 retained).
        with tempfile.TemporaryDirectory() as tmp:
            run(tmp, 'b1', 'full', 'R_AUTO')
            sent, errors = audit.fixture(Path(tmp))
            self.assertEqual(errors, [])
            withheld = [r['index'] for r in sent if not r['sent']]
            self.assertIn(withheld, (list(range(56, 86)), list(range(56, 87))))

    def test_b1_native_detects_tracking_but_no_recovery(self):
        self.assertEqual(self.check('b1', 'native', 'R_EXPLICIT', list(range(56, 76))), ['connect'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
