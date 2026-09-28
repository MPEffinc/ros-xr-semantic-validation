#!/usr/bin/env python3
"""No-Gazebo C-MON fault-injector regressions with a stand-in process named like the oracle.

This verifies the injector's ownership check, health proof, signals and absence
proof only. The OFFICIAL monitor/oracle fault behavior is established separately
by the genuine component test (cmon_monitor_preflight.py), not by this stand-in.
"""
import json
import os
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

INPUTS = Path(__file__).resolve().parents[1] / 'inputs'
STAND_IN = '''import sys, time
from pathlib import Path
p = Path(sys.argv[-1])
while True:
    with p.open("a") as f:
        f.write("{}\\n")
    time.sleep(.01)
'''


class Injector(unittest.TestCase):
    def run_fault(self, fault, stand_in_name='TLOracle/oracle.py', start_oracle=True):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        oracle = None
        if start_oracle:
            script = root / stand_in_name
            script.parent.mkdir(parents=True, exist_ok=True)
            script.write_text(STAND_IN)
            oracle = subprocess.Popen([sys.executable, str(script), '--property', 'd3_tloracle_property',
                                       str(root / 'property.jsonl')])
            self.addCleanup(lambda: (oracle.poll() is None) and (os.kill(oracle.pid, signal.SIGCONT), oracle.kill()))
            (root / 'oracle.pid').write_text(str(oracle.pid) + '\n')
        (root / 'oracle.port').write_text('18999\n')
        env = dict(os.environ, TRIAL_ROOT=str(root), CMON_FAULT=fault)
        inj = subprocess.Popen([sys.executable, str(INPUTS / 'cmon_fault.py')], env=env)
        self.addCleanup(inj.kill)
        while not (root / 'cmon_fault.ready').exists():
            time.sleep(.005)
        (root / 'barrier.json').write_text(json.dumps({'start_monotonic_ns': time.monotonic_ns() - 2_200_000_000}))
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline and not (root / 'cmon_fault.done').exists() and inj.poll() is None:
            time.sleep(.01)
        rows = [json.loads(x) for x in (root / 'cmon_fault.jsonl').read_text().splitlines()]
        return root, oracle, inj, rows

    def test_disconnect_kills_owned_healthy_oracle(self):
        root, oracle, _, rows = self.run_fault('ORACLE_DISCONNECT')
        health = next(r for r in rows if r['kind'] == 'pre_fault_health')
        self.assertTrue(health['owned'] and health['healthy'])
        inj = next(r for r in rows if r['kind'] == 'injected')
        self.assertEqual(inj['signal'], 'SIGKILL')
        oracle.wait(timeout=2)
        self.assertEqual(oracle.returncode, -9)

    def test_nonresponsive_stops_oracle(self):
        root, oracle, _, rows = self.run_fault('ORACLE_NONRESPONSIVE')
        inj = next(r for r in rows if r['kind'] == 'injected')
        self.assertEqual((inj['signal'], inj['process_exists_after_50ms'], inj['process_state_after_50ms']),
                         ('SIGSTOP', True, 'T'))

    def test_absent_proof(self):
        root, _, _, rows = self.run_fault('ORACLE_ABSENT', start_oracle=False)
        proof = next(r for r in rows if r['kind'] == 'absence_proof')
        self.assertEqual((proof['oracle_pid_file'], proof['oracle_port_refuses']), (False, True))

    def test_gate_markers(self):
        for fault, marker in (('B1_GATE_FAIL', 'b1_gate_failed'), ('B3_GATE_FAIL', 'b3_check_failed')):
            root, _, _, rows = self.run_fault(fault, start_oracle=False)
            self.assertTrue((root / marker).exists())
            self.assertEqual(next(r for r in rows if r['kind'] == 'injected')['marker'], marker)

    def test_refuses_unowned_process(self):
        root, oracle, inj, rows = self.run_fault('ORACLE_DISCONNECT', stand_in_name='other/unrelated.py')
        inj.wait(timeout=2)
        self.assertEqual(inj.returncode, 3)
        self.assertTrue(any(r['kind'] == 'refused_not_owned' for r in rows))
        self.assertIsNone(oracle.poll())            # the unrelated process was NOT signalled


if __name__ == '__main__':
    unittest.main(verbosity=2)
