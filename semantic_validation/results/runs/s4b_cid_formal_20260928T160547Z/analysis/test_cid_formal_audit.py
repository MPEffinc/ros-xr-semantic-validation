#!/usr/bin/env python3
"""No-Gazebo fixtures for the frozen C-ID scorer (temporary copies of C-ID Q1 setup raw)."""
import csv
import json
import shutil
import tempfile
import unittest
from pathlib import Path

import cid_formal_audit as f

Q = f.Q


def load(p):
    return [json.loads(x) for x in p.read_text().splitlines() if x.strip()]


def dump(p, items):
    p.write_text(''.join(json.dumps(x, sort_keys=True) + '\n' for x in items))


def row(trial):
    return dict(next(r for r in csv.DictReader((Q / 'qualification_schedule.csv').open()) if r['trial_id'] == trial),
                repetition='0')


class CIDFormal(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.n = 0

    def copy(self, trial):
        self.n += 1
        dst = Path(self.tmp.name) / str(self.n) / trial
        shutil.copytree(Q / 'raw' / trial, dst)
        return dst

    def score(self, trial, root=None):
        return f.audit_trial(row(trial), root or self.copy(trial))

    def b3_mutate(self, trial, stamp_index, field, value):
        root = self.copy(trial)
        stamp = {r['index']: r['sample_ns'] for r in load(root / 'sent.jsonl')}[stamp_index]
        lineage = load(root / 'lineage.jsonl')
        for x in lineage:
            if x.get('kind') == 'b3_mapper_verdict' and f.stamp_of(x.get('source_origin')) == stamp:
                x[field] = value
        dump(root / 'lineage.jsonl', lineage)
        return root

    def test_pass_fail_split(self):
        for kind in ('MISSING_FIELD', 'MISSING_ID', 'DUPLICATE_ID', 'MISMATCH'):
            for b in ('b1', 'b2c', 'b3'):
                t = f'docker_{b}_full_{kind}_cidq1s01'
                self.assertEqual(self.score(t)['policy_status'], 'PASS_POLICY', t)
            self.assertEqual(self.score(f'docker_b2_full_{kind}_cidq1s01')['policy_violations'],
                             ['P2_NO_EXPLICIT_NEUTRALIZATION_REQUEST'])
        shim = self.score('docker_shim_full_MISMATCH_cidq1s01')
        self.assertGreater(shim['original_consequences']['injected_nonzero_commands'], 0)

    def test_injected_accepted_fails(self):
        t = 'docker_b3_full_MISMATCH_cidq1s01'
        out = self.score(t, self.b3_mutate(t, 50, 'verdict', True))
        self.assertIn('P3_INJECTED_EVENT_ACCEPTED', out['policy_violations'])

    def test_wrong_reason_fails(self):
        t = 'docker_b3_full_DUPLICATE_ID_cidq1s01'
        out = self.score(t, self.b3_mutate(t, 50, 'reason', 'STALE_SOURCE'))
        self.assertIn('P2_INJECTED_EVENT_REJECTED_FOR_WRONG_REASON', out['policy_violations'])

    def test_normal_false_rejection_fails(self):
        t = 'docker_b3_full_MISSING_ID_cidq1s01'
        out = self.score(t, self.b3_mutate(t, 40, 'verdict', False))
        self.assertIn('P1_FALSE_REJECTION_OF_NORMAL_INPUT', out['policy_violations'])

    def test_late_or_absent_request(self):
        t = 'docker_b2c_full_MISMATCH_cidq1s01'
        base = self.score(t)
        for shift, violation in ((90_000_000, 'P2_NEUTRALIZATION_REQUEST_OVER_50MS'), (None, 'P2_NO_EXPLICIT_NEUTRALIZATION_REQUEST')):
            root = self.copy(t)
            ev = load(root / 'stop_adapter.jsonl')
            if shift is None:
                ev = [e for e in ev if e['kind'] != 'stop_request']
            else:
                for e in ev:
                    if e['kind'] == 'stop_request':
                        e['monotonic_ns'] = base['local_trigger_ns'] + shift
            dump(root / 'stop_adapter.jsonl', ev)
            self.assertIn(violation, self.score(t, root)['policy_violations'])

    def test_missing_injected_receipt_invalid(self):
        t = 'docker_b3_full_MISSING_ID_cidq1s01'
        root = self.copy(t)
        stamp = {r['index']: r['sample_ns'] for r in load(root / 'sent.jsonl')}[50]
        dump(root / 'lineage.jsonl', [x for x in load(root / 'lineage.jsonl') if not (
            x.get('kind') == 'source_received' and (x.get('metadata') or {}).get('source_timestamp_ns') == stamp)])
        out = self.score(t, root)
        self.assertEqual((out['comparison_status'], out['policy_status']), ('INVALID_COMPARISON', 'UNKNOWN'))

    def test_blocked_and_not_run(self):
        raw = Path(self.tmp.name) / 'raw'
        (raw / 'x_cidr09').mkdir(parents=True)
        saved, f.RAW = f.RAW, raw
        try:
            r = dict(trial_id='x_cidr09', repetition='9', baseline='b3', kind='MISMATCH', mode='b3')
            self.assertEqual(f.score_row(r)['comparison_status'], 'BLOCKED_MEASUREMENT')
            self.assertEqual(f.score_row(dict(r, trial_id='y'))['comparison_status'], 'NOT_RUN')
        finally:
            f.RAW = saved


if __name__ == '__main__':
    unittest.main(verbosity=2)
