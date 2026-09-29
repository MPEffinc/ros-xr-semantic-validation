#!/usr/bin/env python3
"""No-Gazebo C-X scorer regressions on the retained C-X Q1 SETUP raw (not formal outcomes)."""
import csv
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cx_formal_audit as audit  # noqa: E402


class Q1Fixture(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        saved, audit.RAW = audit.RAW, audit.Q / 'raw'
        try:
            cls.t = {(r['baseline'], r['cid_kind'], r['fault']): audit.score_row(
                dict(r, repetition='1', family='CID' if r['cid_kind'] != 'NONE' else 'CMON'))
                for r in csv.DictReader((audit.Q / 'qualification_schedule.csv').open())}
        finally:
            audit.RAW = saved

    def test_all_valid(self):
        self.assertEqual({x['comparison_status'] for x in self.t.values()}, {'VALID_FORMAL_TRIAL'})

    def test_cid_timely_defenses_pass_with_registered_reason(self):
        for kind in ('MISMATCH', 'DUPLICATE_ID'):
            for arm in ('b1', 'b3', 'b2stc'):
                x = self.t[(arm, kind, 'NONE')]
                self.assertEqual(x['policy_status'], 'PASS_POLICY', (arm, kind))
                self.assertEqual(x['injected_rejection_reason'], audit.REASON[kind])

    def test_cmon(self):
        for key in (('b2c', 'NONE', 'ORACLE_ABSENT'), ('b1', 'NONE', 'B1_GATE_FAIL'), ('b3', 'NONE', 'B3_GATE_FAIL')):
            self.assertEqual(self.t[key]['policy_status'], 'PASS_POLICY', key)
        native = self.t[('b2', 'NONE', 'ORACLE_DISCONNECT')]
        self.assertIn('B2_NATIVE_FAIL_OPEN_CONTINUED', native['attribution_classes'])
        self.assertEqual(self.t[('b2c', 'NONE', 'ORACLE_DISCONNECT')]['attribution_classes'],
                         ['OFFICIAL_MONITOR_STALL_TRIPPED_COMMON_WATCHDOG'])

    def test_shim_consequence(self):
        self.assertTrue(self.t[('shim', 'MISMATCH', 'NONE')]['shim_consequence']['injected_poll_delivered'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
