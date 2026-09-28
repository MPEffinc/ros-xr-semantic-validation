#!/usr/bin/env python3
"""No-Gazebo regression for the ORACLE_DISCONNECT resource exemption (Q3)."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cmon_setup_audit as audit  # noqa: E402

LABELS = ['monitor', 'oracle', 'servo']


def make(root, t_kill, oracle_missing_before=False, servo_missing_after=False):
    with (root / 'events.jsonl').open('w') as f:
        f.write(json.dumps(dict(kind='barrier_release', start_monotonic_ns=1000)) + '\n')
        f.write(json.dumps(dict(kind='capture_end', monotonic_ns=2000)) + '\n')
    (root / 'cmon_fault.jsonl').write_text(json.dumps(dict(kind='injected', injected_monotonic_ns=t_kill)) + '\n')
    with (root / 'resource_samples.jsonl').open('w') as f:
        for t in range(1000, 2001, 100):
            tg = {}
            for label in LABELS:
                missing = ((label == 'oracle' and (t > t_kill or oracle_missing_before)) or
                           (label == 'servo' and servo_missing_after and t > t_kill))
                tg[label] = dict(status='MISSING' if missing else 'OBSERVED')
            f.write(json.dumps(dict(kind='sample', monotonic_ns=t, targets=tg)) + '\n')


class Exemption(unittest.TestCase):
    def check(self, **kw):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            make(root, 1450, **kw)
            res = dict(status='UNKNOWN_INCOMPLETE_CAPTURE', expected_labels=LABELS, absent_labels=[])
            return audit.killed_oracle_resources(root, res)['status']

    def test_oracle_missing_only_after_kill_is_complete(self):
        self.assertEqual(self.check(), 'COMPLETE_CAPTURE')

    def test_oracle_missing_before_kill_stays_incomplete(self):
        self.assertEqual(self.check(oracle_missing_before=True), 'UNKNOWN_INCOMPLETE_CAPTURE')

    def test_other_label_missing_stays_incomplete(self):
        self.assertEqual(self.check(servo_missing_after=True), 'UNKNOWN_INCOMPLETE_CAPTURE')


if __name__ == '__main__':
    unittest.main(verbosity=2)
