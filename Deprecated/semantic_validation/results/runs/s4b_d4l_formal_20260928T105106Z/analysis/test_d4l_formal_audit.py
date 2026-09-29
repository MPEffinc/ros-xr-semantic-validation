#!/usr/bin/env python3
"""No-Gazebo fixtures for the frozen D4-L scorer (temporary copies of D4LQ1 setup raw)."""
import csv
import json
import shutil
import tempfile
import unittest
from pathlib import Path

import d4l_formal_audit as f
from d4_age import PROFILES

Q1 = f.ROOT.parent / 's4b_cp20_d4lq1_20260928T053735Z'


def load(path):
    return [json.loads(x) for x in path.read_text().splitlines() if x.strip()]


def dump(path, items):
    path.write_text(''.join(json.dumps(x, sort_keys=True) + '\n' for x in items))


def row(trial_id, **override):
    r = next(x for x in csv.DictReader((Q1 / 'qualification_schedule.csv').open()) if x['trial_id'] == trial_id)
    return dict(r, repetition='0', **override)


class D4LFormal(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.n = 0

    def copy(self, trial_id):
        self.n += 1
        dst = Path(self.tmp.name) / str(self.n) / trial_id
        shutil.copytree(Q1 / 'raw' / trial_id, dst)
        return dst

    def score(self, trial_id, root=None, **override):
        return f.audit_trial(row(trial_id, **override), root or self.copy(trial_id))

    def test_placement_effect_b1(self):
        out = self.score('docker_b1_full_L750_F250_d4lq1s01')
        self.assertEqual(out['policy_status'], 'FAIL_POLICY')
        self.assertEqual(out['policy_violations'], ['OVER_BUDGET_SAMPLE_REACHED_CONSUMER_PLACEMENT_EFFECT_POST_DECISION_DELAY'])
        self.assertEqual(out['gate']['false_accept_count'], 0)           # gate-local decisions correct
        self.assertTrue(out['b1_profile_invariant_runtime'])
        self.assertEqual(out['b1_inferred_other_profiles']['F500']['status'], 'INFERRED_FAIL_POLICY')

    def test_b1_inference_refused_when_gate_age_large(self):
        root = self.copy('docker_b1_full_L750_F250_d4lq1s01')
        verdicts = load(root / 'gate_verdict.jsonl')
        for v in verdicts:
            if v.get('sample_id') == 'docker:30' and v.get('kind') is None:
                v['decision_monotonic_ns'] += 150_000_000
        dump(root / 'gate_verdict.jsonl', verdicts)
        out = self.score('docker_b1_full_L750_F250_d4lq1s01', root)
        self.assertFalse(out['b1_profile_invariant_runtime'])
        self.assertTrue(out['b1_inferred_other_profiles']['F100']['status'].startswith('NOT_INFERABLE'))

    def test_receiving_side_rejects_delayed_input(self):
        for trial in ('docker_b2c_full_L750_F250_d4lq1s01', 'docker_b3_full_L750_F250_d4lq1s01',
                      'docker_b2c_full_L150_F100_d4lq1s01'):
            out = self.score(trial)
            self.assertEqual(out['policy_status'], 'PASS_POLICY', (trial, out['policy_violations']))
            self.assertEqual(out['gate']['consumer_level']['over_budget_samples_reached_consumer'], 0)
        b2 = self.score('docker_b2_full_L750_F250_d4lq1s01')
        self.assertEqual(b2['policy_violations'], ['NO_EXPLICIT_NEUTRALIZATION_REQUEST'])

    def test_accept_cases_and_native(self):
        for trial in ('docker_b3_full_L000_F250_d4lq1s01', 'docker_b3_full_L350_F500_d4lq1s01'):
            self.assertEqual(self.score(trial)['policy_status'], 'PASS_POLICY', trial)
        self.assertEqual(self.score('docker_b3_native_L750_F250_d4lq1s01')['policy_status'], 'UNOBSERVABLE')
        # Judging the accepted L350/F500 run under F250 must expose false acceptance at the gate.
        relabel = self.score('docker_b3_full_L350_F500_d4lq1s01', profile='F250')
        self.assertIn('FALSE_ACCEPTANCE_OF_OVER_BUDGET_INPUT', relabel['policy_violations'])
        self.assertIn('OVER_BUDGET_SAMPLE_REACHED_CONSUMER', relabel['policy_violations'])

    def test_boundary_straddle_prospective(self):
        # Synthetic decisions: first rejection in band, no clear over-budget -> straddle.
        root = self.copy('docker_b3_full_L000_F250_d4lq1s01')
        lineage = load(root / 'lineage.jsonl')
        sent = {f'docker:{r["index"]}': r for r in load(root / 'sent.jsonl')}
        dec = f.decisions(root, 'b3', 'full', lineage, sent)
        dec[5] = dict(dec[5], allowed=False, source_age_ns=PROFILES['F250'] + 400_000)
        events = load(root / 'stop_adapter.jsonl')
        events.append(dict(kind='stop_request', source='B3_POLICY_REJECT', monotonic_ns=dec[5]['t'] + 1_000_000))
        dump(root / 'stop_adapter.jsonl', events)
        rx = {}
        for x in lineage:
            if x.get('kind') == 'source_received':
                rx.setdefault((x.get('metadata') or {}).get('sample_id'), []).append(x['receiver_receipt_monotonic_ns'])
        capture_end = next(x['monotonic_ns'] for x in load(root / 'events.jsonl') if x.get('kind') == 'capture_end')
        g = f.gate_policy(root, 'b3', PROFILES['F250'], dec, rx, sent, capture_end,
                          f.setup.callback_join(root), f.setup.motion(root))
        self.assertTrue(g['boundary_straddle'])
        self.assertNotIn('UNEXPECTED_NEUTRALIZATION_WITH_NO_OVER_BUDGET_INPUT', g['violations'])

    def test_measurement_gaps_invalid(self):
        root = self.copy('docker_b3_full_L750_F250_d4lq1s01')
        rel = load(root / 'delivery.jsonl')
        rel[40]['release_ns'] = rel[40]['due_ns'] - 1
        dump(root / 'delivery.jsonl', rel)
        out = self.score('docker_b3_full_L750_F250_d4lq1s01', root)
        self.assertEqual((out['comparison_status'], out['policy_status']), ('INVALID_COMPARISON', 'UNKNOWN'))
        self.assertIn('D4L_DELIVERY_QUEUE_INCOMPLETE', out['invalid_reasons'])
        root2 = self.copy('docker_b2c_full_L750_F250_d4lq1s01')
        lineage = load(root2 / 'lineage.jsonl')
        for x in lineage:
            if x.get('stage') == 'receiver_envelope' and (x.get('selected_origin') or {}).get('sample_id') == 'docker:30':
                x['selected_origin']['source_timestamp_ns'] = x['monotonic_ns']   # restamped downstream
        dump(root2 / 'lineage.jsonl', lineage)
        self.assertEqual(self.score('docker_b2c_full_L750_F250_d4lq1s01', root2)['comparison_status'], 'INVALID_COMPARISON')

    def test_not_run_registry_and_blocked(self):
        nr = f.not_run_registered()
        self.assertEqual(sum(1 for x in nr if x['status'] == 'NOT_RUN_SCOPED_UNOBSERVABLE_BY_CONSTRUCTION'), 16)
        self.assertEqual(sum(1 for x in nr if x['status'] == 'NOT_RUN_B1_PROFILE_INVARIANT_OFFLINE_INFERENCE'), 10)
        self.assertEqual(sum(1 for x in nr if x['status'] == 'NOT_RUN_INFERRED_BY_MONOTONICITY'), 24)
        raw = Path(self.tmp.name) / 'raw'
        (raw / 'x_d4lr09').mkdir(parents=True)
        saved, f.RAW = f.RAW, raw
        try:
            r = dict(trial_id='x_d4lr09', repetition='9', baseline='b1', regime='full', delay='L750', profile='F250')
            self.assertEqual(f.score_row(r)['comparison_status'], 'BLOCKED_MEASUREMENT')
            self.assertEqual(f.score_row(dict(r, trial_id='y'))['comparison_status'], 'NOT_RUN')
        finally:
            f.RAW = saved


if __name__ == '__main__':
    unittest.main(verbosity=2)
