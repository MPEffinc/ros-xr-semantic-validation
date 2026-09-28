#!/usr/bin/env python3
"""No-Gazebo fixtures for the frozen D5 scorer (temporary copies of D5Q1/D5Q2 setup raw)."""
import csv
import json
import shutil
import tempfile
import unittest
from pathlib import Path

import d5_formal_audit as f

RUNS = f.ROOT.parent
Q1 = RUNS / 's4b_cp22_d5q1_20260928T130939Z'
Q2 = RUNS / 's4b_cp22_d5q2_20260928T132939Z'


def load(p):
    return [json.loads(x) for x in p.read_text().splitlines() if x.strip()]


def dump(p, items):
    p.write_text(''.join(json.dumps(x, sort_keys=True) + '\n' for x in items))


def row(q, trial):
    return dict(next(r for r in csv.DictReader((q / 'qualification_schedule.csv').open()) if r['trial_id'] == trial),
                repetition='0')


class D5Formal(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.n = 0

    def copy(self, q, trial):
        self.n += 1
        dst = Path(self.tmp.name) / str(self.n) / trial
        shutil.copytree(q / 'raw' / trial, dst)
        return dst

    def score(self, q, trial, root=None):
        return f.audit_trial(row(q, trial), root or self.copy(q, trial))

    def mutate_b3(self, trial, sid, allowed):
        root = self.copy(Q2, trial)
        lineage = load(root / 'lineage.jsonl')
        for x in lineage:
            if x.get('kind') == 'b3_mapper_verdict' and x.get('event_kind') is None and \
                    (f.source_origin(x.get('source_origin')) or {}).get('sample_id') == sid:
                x['verdict'] = allowed
        dump(root / 'lineage.jsonl', lineage)
        return root

    def test_pass_and_b2_native_fail(self):
        for trial in ('docker_b3_full_R_EXPLICIT_d5q2s01', 'docker_b2c_full_R_AUTO_d5q2s01'):
            self.assertEqual(self.score(Q2, trial)['policy_status'], 'PASS_POLICY', trial)
        self.assertEqual(self.score(Q1, 'docker_b1_full_R_AUTO_d5q1s01')['policy_status'], 'PASS_POLICY')
        out = self.score(Q2, 'docker_b2_full_R_EXPLICIT_d5q2s01')
        self.assertEqual(out['policy_violations'], ['P2_NO_EXPLICIT_NEUTRALIZATION_REQUEST'])
        shim = self.score(Q1, 'docker_shim_full_R_EXPLICIT_d5q1s01')
        self.assertGreater(shim['original_consequences']['replay_nonzero_callbacks'], 0)   # original accepts old gen

    def test_replay_acceptance_fails(self):
        t = 'docker_b3_full_R_AUTO_d5q2s01'
        out = self.score(Q2, t, self.mutate_b3(t, 'docker:72', True))
        self.assertIn('P3_OLD_GENERATION_REPLAY_ACCEPTED', out['policy_violations'])

    def test_r_explicit_held_grip_rearm_fails(self):
        t = 'docker_b3_full_R_EXPLICIT_d5q2s01'
        out = self.score(Q2, t, self.mutate_b3(t, 'docker:85', True))
        self.assertIn('P4_R_EXPLICIT_REARM_NOT_ON_RELEASE_THEN_EDGE', out['policy_violations'])

    def test_r_auto_short_dwell_fails(self):
        t = 'docker_b3_full_R_AUTO_d5q2s01'
        out = self.score(Q2, t, self.mutate_b3(t, 'docker:78', True))
        self.assertIn('P4_R_AUTO_REARM_BEFORE_500MS_VALID_DWELL', out['policy_violations'])

    def test_normal_false_rejection_fails(self):
        t = 'docker_b3_full_R_AUTO_d5q2s01'
        out = self.score(Q2, t, self.mutate_b3(t, 'docker:40', False))
        self.assertIn('P1_FALSE_REJECTION_OF_NORMAL_ACTIVE_INPUT', out['policy_violations'])

    def test_neutralization_timing(self):
        t = 'docker_b2c_full_R_EXPLICIT_d5q2s01'
        base = self.score(Q2, t)
        for shift, violation in ((80_000_000, 'P2_NEUTRALIZATION_REQUEST_OVER_50MS'), (None, 'P2_NO_EXPLICIT_NEUTRALIZATION_REQUEST')):
            root = self.copy(Q2, t)
            ev = load(root / 'stop_adapter.jsonl')
            if shift is None:
                ev = [e for e in ev if e['kind'] != 'stop_request']
            else:
                first = next(e for e in ev if e['kind'] == 'stop_request')
                first['monotonic_ns'] = base['local_disconnect_trigger_ns'] + shift
            dump(root / 'stop_adapter.jsonl', ev)
            self.assertIn(violation, self.score(Q2, t, root)['policy_violations'])

    def test_measurement_gap_invalid(self):
        t = 'docker_b3_full_R_EXPLICIT_d5q2s01'
        root = self.copy(Q2, t)
        dump(root / 'lineage.jsonl', [x for x in load(root / 'lineage.jsonl')
                                       if not (x.get('kind') == 'receiver_connection' and x.get('event') == 'dropped')])
        out = self.score(Q2, t, root)
        self.assertEqual((out['comparison_status'], out['policy_status']), ('INVALID_COMPARISON', 'UNKNOWN'))

    def test_blocked_and_not_run(self):
        raw = Path(self.tmp.name) / 'raw'
        (raw / 'x_d5r09').mkdir(parents=True)
        saved, f.RAW = f.RAW, raw
        try:
            r = dict(trial_id='x_d5r09', repetition='9', baseline='b3', rearm='R_AUTO', mode='b3')
            self.assertEqual(f.score_row(r)['comparison_status'], 'BLOCKED_MEASUREMENT')
            self.assertEqual(f.score_row(dict(r, trial_id='y'))['comparison_status'], 'NOT_RUN')
        finally:
            f.RAW = saved


if __name__ == '__main__':
    unittest.main(verbosity=2)
