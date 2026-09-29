#!/usr/bin/env python3
"""No-Gazebo positive/negative fixtures for the frozen D4 formal scorer.

Fixtures are temporary COPIES of immutable D4Q1/D4Q2 SETUP raw (never formal
repetitions). D4Q1 copies lack the D4Q2 transport log; a synthetic single
`connect` record is added to those copies only (test adaptation, labelled).
"""
import csv
import json
import shutil
import tempfile
import unittest
from pathlib import Path

import d4_formal_audit as f

RUNS = f.ROOT.parent
Q1 = RUNS / 's4b_cp18_d4q1_20260928T050614Z'
Q2 = RUNS / 's4b_cp18_d4q2_20260928T052627Z'


def load(path):
    return [json.loads(x) for x in path.read_text().splitlines() if x.strip()]


def dump(path, items):
    path.write_text(''.join(json.dumps(x, sort_keys=True) + '\n' for x in items))


def schedule_row(q, trial_id):
    row = next(r for r in csv.DictReader((q / 'qualification_schedule.csv').open()) if r['trial_id'] == trial_id)
    return dict(row, repetition='0')


class D4Formal(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.n = 0

    def copy(self, q, trial_id):
        self.n += 1
        dst = Path(self.tmp.name) / str(self.n) / trial_id
        shutil.copytree(q / 'raw' / trial_id, dst)
        if q == Q1:
            (dst / 'sender_transport.jsonl').write_text(json.dumps({'kind': 'connect', 'connection_index': 1,
                                                                    'monotonic_ns': 0}) + '\n')
        return dst

    def score(self, q, trial_id, root=None, **override):
        return f.audit_trial(dict(schedule_row(q, trial_id), **override), root or self.copy(q, trial_id))

    def test_fresh_accept_pass_and_native_unobservable(self):
        for b in ('b2', 'b2c', 'b3'):
            out = self.score(Q1, f'docker_{b}_full_A000_F250_d4q1s01')
            self.assertEqual(out['policy_status'], 'PASS_POLICY', (b, out['policy_violations']))
            self.assertFalse(out['expected_rejection'])
            native = self.score(Q1, f'docker_{b}_native_A000_F250_d4q1s01')
            self.assertEqual(native['policy_status'], 'UNOBSERVABLE')
            self.assertFalse(native['freshness_observable_to_defense'])
        b1 = self.score(Q2, 'docker_b1_full_A000_F250_d4q2s01')
        self.assertEqual(b1['policy_status'], 'PASS_POLICY')

    def test_stale_reject_pass_attribution(self):
        b2c = self.score(Q1, 'docker_b2c_full_A750_F250_d4q1s01')
        self.assertEqual(b2c['policy_status'], 'PASS_POLICY')
        self.assertEqual(b2c['neutralization']['detection_attribution'],
                         'OFFICIAL_ROSMONITORING_VERDICT_CURRENTLY_FALSE')
        self.assertEqual(b2c['neutralization']['actuation_attribution'],
                         'COMMON_STOP_ADAPTER_NOT_NATIVE_ROSMONITORING')
        b1 = self.score(Q2, 'docker_b1_full_A150_F100_d4q2s01')
        self.assertEqual(b1['policy_status'], 'PASS_POLICY')
        self.assertEqual(b1['neutralization']['detection_attribution'], 'B1_SOURCE_SIDE_FRESHNESS_DECISION')
        for trial in ('docker_b2c_full_H1P0_F250_d4q1s01', 'docker_b3_full_A750_F250_d4q1s01'):
            self.assertEqual(self.score(Q1, trial)['policy_status'], 'PASS_POLICY', trial)

    def test_b2_native_blocks_but_no_neutralization_fails(self):
        for trial in ('docker_b2_full_A750_F250_d4q1s01', 'docker_b2_full_FUT1S_F250_d4q1s01'):
            out = self.score(Q1, trial)
            self.assertEqual(out['policy_violations'], ['NO_EXPLICIT_NEUTRALIZATION_REQUEST'])
            self.assertGreater(out['rejected_decisions'], 0)
            self.assertEqual(out['false_accept_count'], 0)

    def test_profile_changes_expectation_not_data(self):
        # Same A350 raw judged under F250 would require rejection; the arm accepted
        # under its runtime F500 profile, so relabelling the profile must FAIL.
        out = self.score(Q1, 'docker_b3_full_A350_F500_d4q1s01', profile='F250')
        self.assertEqual(out['policy_status'], 'FAIL_POLICY')
        self.assertIn('FALSE_ACCEPTANCE_OF_OVER_BUDGET_INPUT', out['policy_violations'])
        self.assertIn('FORBIDDEN_NONZERO_SERVO_CALLBACK_FROM_OVER_BUDGET_SOURCE', out['policy_violations'])
        self.assertEqual(self.score(Q1, 'docker_b3_full_A350_F500_d4q1s01')['policy_status'], 'PASS_POLICY')

    def test_false_acceptance_mutation(self):
        root = self.copy(Q1, 'docker_b3_full_A750_F250_d4q1s01')
        lineage = load(root / 'lineage.jsonl')
        for x in lineage:
            if x.get('kind') == 'b3_mapper_verdict' and x.get('reason') == 'STALE_SOURCE':
                x['verdict'] = True
                break
        dump(root / 'lineage.jsonl', lineage)
        out = self.score(Q1, 'docker_b3_full_A750_F250_d4q1s01', root)
        self.assertIn('FALSE_ACCEPTANCE_OF_OVER_BUDGET_INPUT', out['policy_violations'])

    def test_false_rejection_of_fresh_input(self):
        root = self.copy(Q1, 'docker_b3_full_A000_F250_d4q1s01')
        lineage = load(root / 'lineage.jsonl')
        for x in lineage:
            if x.get('kind') == 'b3_mapper_verdict' and x.get('reason') == 'VALID_D1':
                x['verdict'] = False
                break
        dump(root / 'lineage.jsonl', lineage)
        out = self.score(Q1, 'docker_b3_full_A000_F250_d4q1s01', root)
        self.assertEqual(out['policy_status'], 'FAIL_POLICY')
        self.assertIn('FALSE_REJECTION_OF_FRESH_TELEOP_INPUT', out['policy_violations'])
        native_root = self.copy(Q1, 'docker_b3_native_A000_F250_d4q1s01')
        lineage = load(native_root / 'lineage.jsonl')
        for x in lineage:
            if x.get('kind') == 'b3_mapper_verdict' and x.get('event_kind') is None:
                o = f.source_origin(x.get('source_origin')) or {}
                if o.get('sample_id') == 'docker:40':
                    x['verdict'] = False
                    break
        dump(native_root / 'lineage.jsonl', lineage)
        self.assertEqual(self.score(Q1, 'docker_b3_native_A000_F250_d4q1s01', native_root)['policy_status'],
                         'FAIL_POLICY')

    def test_stamp_regenerated_downstream_is_invalid(self):
        root = self.copy(Q1, 'docker_b3_full_A750_F250_d4q1s01')
        lineage = load(root / 'lineage.jsonl')
        for x in lineage:
            if x.get('kind') == 'b3_mapper_verdict' and x.get('event_kind') is None:
                o = f.source_origin(x.get('source_origin'))
                if o and o.get('sample_id') == 'docker:30':
                    o['source_timestamp_ns'] = x['monotonic_ns']   # regenerated/fresh-looking stamp
        dump(root / 'lineage.jsonl', lineage)
        out = self.score(Q1, 'docker_b3_full_A750_F250_d4q1s01', root)
        self.assertEqual(out['comparison_status'], 'INVALID_COMPARISON')
        self.assertIn('SOURCE_STAMP_NOT_PRESERVED_TO_DEFENSE', out['invalid_reasons'])

    def test_neutralization_timing(self):
        base = self.copy(Q1, 'docker_b2c_full_A750_F250_d4q1s01')
        t = self.score(Q1, 'docker_b2c_full_A750_F250_d4q1s01', base)['local_trigger_ns']
        for shift, violation in ((120_000_000, 'NEUTRALIZATION_REQUEST_OVER_50MS'),
                                 (-100_000_000, 'PREMATURE_NEUTRALIZATION_REQUEST'), (None, 'NO_EXPLICIT_NEUTRALIZATION_REQUEST')):
            root = self.copy(Q1, 'docker_b2c_full_A750_F250_d4q1s01')
            events = load(root / 'stop_adapter.jsonl')
            if shift is None:
                events = [e for e in events if e['kind'] == 'ready']
            else:
                for e in events:
                    if e['kind'] == 'stop_request':
                        e['monotonic_ns'] = t + shift
            dump(root / 'stop_adapter.jsonl', events)
            out = self.score(Q1, 'docker_b2c_full_A750_F250_d4q1s01', root)
            self.assertIn(violation, out['policy_violations'], shift)

    def test_unexpected_stop_in_fresh_case(self):
        root = self.copy(Q1, 'docker_b3_full_A000_F250_d4q1s01')
        events = load(root / 'stop_adapter.jsonl')
        events.append(dict(kind='stop_request', source='B3_POLICY_REJECT', monotonic_ns=events[-1]['monotonic_ns'] + 1))
        dump(root / 'stop_adapter.jsonl', events)
        out = self.score(Q1, 'docker_b3_full_A000_F250_d4q1s01', root)
        self.assertIn('UNEXPECTED_NEUTRALIZATION_WITH_NO_OVER_BUDGET_INPUT', out['policy_violations'])

    def test_measurement_gaps_invalid(self):
        root = self.copy(Q1, 'docker_b2c_full_A000_F250_d4q1s01')
        lineage = load(root / 'lineage.jsonl')
        release = next(x['monotonic_ns'] for x in lineage if x.get('kind') == 'receiver_timer_release')
        i = next(i for i, x in enumerate(lineage) if x.get('kind') == 'monitor_output_received' and x['monotonic_ns'] > release)
        dump(root / 'lineage.jsonl', lineage[:i] + lineage[i + 1:])
        self.assertEqual(self.score(Q1, 'docker_b2c_full_A000_F250_d4q1s01', root)['comparison_status'], 'INVALID_COMPARISON')
        root2 = self.copy(Q1, 'docker_b3_full_A750_F250_d4q1s01')
        events = load(root2 / 'events.jsonl')
        ack = next(x for x in events if x.get('kind') == 'readiness_ack')
        ack['participant_clocks'][sorted(ack['participant_clocks'])[0]]['boot_id'] = 'other'
        dump(root2 / 'events.jsonl', events)
        out = self.score(Q1, 'docker_b3_full_A750_F250_d4q1s01', root2)
        self.assertEqual((out['comparison_status'], out['policy_status']), ('INVALID_COMPARISON', 'UNKNOWN'))
        root3 = self.copy(Q1, 'docker_b3_full_A000_F250_d4q1s01')
        (root3 / 'sender_transport.jsonl').write_text(json.dumps({'kind': 'connect', 'connection_index': 1}) + '\n' +
            json.dumps({'kind': 'reconnect_after_peer_close', 'connection_index': 2, 'before_index': 60}) + '\n')
        self.assertIn('UNEXPLAINED_SENDER_RECONNECT', self.score(Q1, 'docker_b3_full_A000_F250_d4q1s01', root3)['invalid_reasons'])

    def test_blocked_and_not_run(self):
        raw = Path(self.tmp.name) / 'raw'
        (raw / 'docker_b1_full_A750_F250_d4r09').mkdir(parents=True)
        saved, f.RAW = f.RAW, raw
        try:
            row = dict(trial_id='docker_b1_full_A750_F250_d4r09', repetition='9', baseline='b1', regime='full',
                       condition='A750', profile='F250', mode='b1')
            self.assertEqual(f.score_row(row)['comparison_status'], 'BLOCKED_MEASUREMENT')
            self.assertEqual(f.score_row(dict(row, trial_id='x_d4r08'))['comparison_status'], 'NOT_RUN')
        finally:
            f.RAW = saved


if __name__ == '__main__':
    unittest.main(verbosity=2)
