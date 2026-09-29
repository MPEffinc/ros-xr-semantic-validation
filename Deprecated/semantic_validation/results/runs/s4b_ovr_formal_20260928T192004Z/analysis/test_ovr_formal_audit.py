#!/usr/bin/env python3
"""No-Gazebo scorer regressions using the retained OpenVR Q1 SETUP raw as a fixture
(setup evidence, not formal outcomes), plus the boundary-band helper."""
import csv
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ovr_formal_audit as audit  # noqa: E402


class Q1Fixture(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        saved, audit.RAW = audit.RAW, audit.Q / 'raw'
        try:
            cls.t = {(r['baseline'], r['case']): audit.score_row(dict(r, repetition='1'))
                     for r in csv.DictReader((audit.Q / 'qualification_schedule.csv').open())}
        finally:
            audit.RAW = saved

    def test_all_valid_including_official_monitor_halt(self):
        self.assertEqual({x['comparison_status'] for x in self.t.values()}, {'VALID_FORMAL_TRIAL'})
        self.assertEqual(self.t[('b2', 'W1')]['official_unprocessed_envelopes'], 560)

    def test_w1_defenses(self):
        for arm in ('b1', 'b2c', 'b3', 'b2stc'):
            self.assertEqual(self.t[(arm, 'W1')]['policy_status'], 'PASS_POLICY', arm)
        self.assertEqual(self.t[('b2', 'W1')]['violation_attribution']['N1_VALID_GRIP_SAMPLE_NOT_ADMITTED'],
                         'OFFICIAL_MONITOR_NO_DECISION')

    def test_w4_reference_mapping_only_for_timely_defenses(self):
        for arm in ('b1', 'b3', 'b2stc'):
            x = self.t[(arm, 'W4')]
            self.assertEqual(x['policy_violations'], ['R8_FRESH_REFERENCE_ADDED_DISPLACEMENT'], arm)
            self.assertEqual(x['first_admitted_grip_after_fault'], 250)
        self.assertIn('R6_FORBIDDEN_HELD_GRIP_RESTART_REACHED_SERVO_INPUT', self.t[('b0', 'W4')]['policy_violations'])
        self.assertEqual(set(self.t[('b2c', 'W4')]['attribution_classes']), {'OFFICIAL_MONITOR_LATE_DECISION_STALE_LATCH'})

    def test_w2_official_latency(self):
        self.assertEqual(set(self.t[('b2c', 'W2')]['attribution_classes']), {'OFFICIAL_MONITOR_LATENCY'})


class Band(unittest.TestCase):
    def test_within(self):
        self.assertEqual([audit.within(x) for x in (None, 10, 49.5, 50.9, 51.2)], ['missing', 'ok', 'band', 'band', 'over'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
