#!/usr/bin/env python3
"""No-Gazebo positive/negative fixtures for the frozen D3 formal scorer.

Fixtures are copies of immutable Q6 SETUP raw (never formal repetitions),
optionally mutated in a temporary directory. Q6 raw itself is never written.
"""
import json
import shutil
import tempfile
import unittest
from pathlib import Path

import d3_formal_audit as f

Q6RAW = f.Q6 / 'raw'


def cell(baseline, regime):
    return f'docker_{baseline}_{regime}_cp16d3setup01'


def row(baseline, regime):
    mode = 'b2' if baseline == 'b2c' else baseline
    return dict(trial_id=cell(baseline, regime), repetition='0', baseline=baseline,
                regime=regime, mode=mode)


def load(path):
    return [json.loads(x) for x in path.read_text().splitlines() if x.strip()]


def dump(path, items):
    path.write_text(''.join(json.dumps(x, sort_keys=True) + '\n' for x in items))


class D3FormalFixtures(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def copy(self, baseline, regime, tag='a'):
        target = Path(self.tmp.name) / tag / cell(baseline, regime)
        shutil.copytree(Q6RAW / cell(baseline, regime), target)
        return target

    def score(self, baseline, regime, root=None):
        return f.audit_trial(row(baseline, regime), root or Q6RAW / cell(baseline, regime))

    def t_local(self, root, baseline):
        lineage = f.rows(root / 'lineage.jsonl')
        rc = f.receipts(root, lineage)
        return (rc['send55'] if baseline == 'b1' else rc['rx55']) + f.LIMIT_NS

    # A. valid moving-state source-silence traces with explicit defense stop.
    def test_A_valid_moving_silence_pass(self):
        for baseline in ('b1', 'b2c', 'b3'):
            out = self.score(baseline, 'full')
            self.assertEqual(out['comparison_status'], 'VALID_FORMAL_TRIAL', baseline)
            self.assertEqual(out['policy_status'], 'PASS_POLICY', (baseline, out['policy_violations']))
            self.assertGreater(out['gazebo_moving_before_trigger_rad_s'], .001)
            self.assertEqual(out['active_false_reject_count'], 0)

    # B. only the original receiver timeout causes settling -> not credited.
    def test_B_original_timeout_only_not_credited(self):
        out = self.score('b2', 'full')
        self.assertEqual(out['comparison_status'], 'VALID_FORMAL_TRIAL')
        self.assertEqual(out['policy_status'], 'FAIL_POLICY')
        self.assertEqual(out['policy_violations'], ['NO_EXPLICIT_NEUTRALIZATION_REQUEST'])
        self.assertTrue(out['silence_detection']['observed'])      # official verdict exists
        self.assertLessEqual(out['gazebo_settled_after_trigger_ms'], 1000)  # yet settled
        self.assertFalse(out['original_receiver_timeout_credited_to_defense'])
        self.assertIsNotNone(out['original_receiver_timeout_neutral_ns'])
        native = self.score('b3', 'native')
        self.assertEqual(native['policy_status'], 'UNOBSERVABLE')
        self.assertFalse(native['silence_detection']['observable'])

    # C. explicit defense-triggered neutral request, attribution kept separate.
    def test_C_explicit_neutral_request_attribution(self):
        b1 = self.score('b1', 'full')['neutralization']
        self.assertEqual(b1['detection_attribution'], 'B1_SOURCE_SIDE_SILENCE_DETECTION')
        self.assertEqual(b1['actuation_attribution'], 'COMMON_STOP_ADAPTER_NOT_NATIVE_ROSMONITORING')
        b2c = self.score('b2c', 'full')
        self.assertEqual(b2c['neutralization']['detection_attribution'],
                         'OFFICIAL_ROSMONITORING_VERDICT_CURRENTLY_FALSE')
        self.assertEqual(b2c['silence_detection']['official_status']['decision'], 'blocked')
        self.assertLessEqual(b2c['neutralization']['request_delay_ms'], 50)

    # D. ticks continue while bytes stop; a tick must never refresh receipt.
    def test_D_ticks_continue_bytes_stop(self):
        out = self.score('b3', 'full')
        self.assertEqual(out['silence_detection']['tracker_issues'], [])
        ticks = f.rows(Q6RAW / cell('b3', 'full') / 'd3_ticks.jsonl')
        self.assertEqual(len(ticks), 300)
        self.assertTrue(all(t['source_sample_id'] is None for t in ticks))
        root = self.copy('b3', 'full')
        t_local = self.t_local(root, 'b3')
        lineage = load(root / 'lineage.jsonl')
        for item in lineage:   # Simulate a tracker whose receipt a tick/cached command refreshed.
            if item.get('kind') == 'b3_silence_tick' and (item.get('state') or {}).get('state') == 'SOURCE_SILENCE':
                item['state']['trigger_ns'] += 100_000_000
            if item.get('kind') == 'b3_mapper_verdict' and item.get('event_kind') == 'health_tick':
                item['trigger_monotonic_ns'] = t_local + 100_000_000
        dump(root / 'lineage.jsonl', lineage)
        bad = self.score('b3', 'full', root)
        self.assertEqual(bad['policy_status'], 'FAIL_POLICY')
        self.assertIn('SILENCE_TRACKER_NOT_BOUND_TO_LAST_REAL_SOURCE', bad['policy_violations'])
        root2 = self.copy('b1', 'full', 'b')
        ticks = load(root2 / 'd3_ticks.jsonl')
        ticks[160]['source_sample_id'] = 'docker:56'   # a tick fabricated as a source sample
        dump(root2 / 'd3_ticks.jsonl', ticks)
        fab = self.score('b1', 'full', root2)
        self.assertEqual(fab['comparison_status'], 'INVALID_COMPARISON')
        self.assertIn('COMMON_TICK_INCOMPLETE_OR_FABRICATED_SOURCE', fab['invalid_reasons'])

    # E. cached/continuing nonzero commands after source silence.
    def test_E_continuing_commands(self):
        good = self.score('b2c', 'full')
        self.assertIn('cached_prior_source_nonzero_servo_callbacks_after_trigger', good['post_trigger_commands'])
        root = self.copy('b1', 'full')
        t_local = self.t_local(root, 'b1')
        topics = load(root / 'topics.jsonl')
        topics.append(dict(topic='/joint_group_velocity_controller/commands',
                           monotonic_ns=t_local + 400_000_000,
                           payload=dict(data=[.05, 0, 0, 0, 0, 0], layout=dict(data_offset=0, dim=[]))))
        dump(root / 'topics.jsonl', sorted(topics, key=lambda x: x['monotonic_ns']))
        out = self.score('b1', 'full', root)
        self.assertEqual(out['policy_status'], 'FAIL_POLICY')
        self.assertIn('CONTROLLER_NONZERO_OVER_300MS', out['policy_violations'])
        # A nonzero command parented to a post-silence (teleop-false) source = restart.
        root2 = self.copy('b1', 'full', 'b')
        lineage = load(root2 / 'lineage.jsonl')
        callbacks = load(root2 / 'servo_callback_payload.jsonl')
        target = next(x for x in lineage if x.get('stage') == 'bridge_servo_input' and
                      (f.source_origin(x.get('parent')) or {}).get('sample_id') == 'docker:90')
        key = f.q6.callback_latency.__globals__['pub_key'](target)
        cb = next(c for c in callbacks if f.q6.callback_latency.__globals__['callback_key'](c) == key)
        target['payload']['twist']['linear']['x'] = .1
        cb['linear'][0] = .1
        dump(root2 / 'lineage.jsonl', lineage)
        dump(root2 / 'servo_callback_payload.jsonl', callbacks)
        restart = self.score('b1', 'full', root2)
        self.assertIn('NONZERO_COMMAND_FROM_POST_SILENCE_SOURCE_WITHOUT_REARM', restart['policy_violations'])

    # F. incomplete source-to-Servo association.
    def test_F_incomplete_source_servo_association(self):
        root = self.copy('b3', 'full')
        lineage = load(root / 'lineage.jsonl')
        target = next(x for x in lineage if x.get('stage') == 'bridge_servo_input' and
                      (f.source_origin(x.get('parent')) or {}).get('sample_id') == 'docker:40')
        key = f.q6.callback_latency.__globals__['pub_key'](target)
        callbacks = [c for c in load(root / 'servo_callback_payload.jsonl')
                     if f.q6.callback_latency.__globals__['callback_key'](c) != key]
        dump(root / 'servo_callback_payload.jsonl', callbacks)
        out = self.score('b3', 'full', root)
        self.assertEqual(out['comparison_status'], 'INVALID_COMPARISON')
        self.assertEqual(out['policy_status'], 'UNKNOWN')

    # G. missing official monitor property/status/guarded receipt.
    def test_G_missing_official_monitor_evidence(self):
        root = self.copy('b2c', 'full')
        lineage = load(root / 'lineage.jsonl')
        release = next(x['monotonic_ns'] for x in lineage if x.get('kind') == 'receiver_timer_release')
        index = next(i for i, x in enumerate(lineage) if x.get('kind') == 'monitor_output_received'
                     and x['monotonic_ns'] > release)
        dump(root / 'lineage.jsonl', lineage[:index] + lineage[index + 1:])
        out = self.score('b2c', 'full', root)
        self.assertEqual(out['comparison_status'], 'INVALID_COMPARISON')
        self.assertIn('OFFICIAL_SOURCE_EVENT_ASSOCIATION_INCOMPLETE', out['invalid_reasons'])
        root2 = self.copy('b2', 'full')
        status = load(root2 / 'monitor_full_status.jsonl')
        index = next(i for i, x in enumerate(status) if x.get('interface') == '/s4b/d3/tick')
        dump(root2 / 'monitor_full_status.jsonl', status[:index] + status[index + 1:])
        self.assertEqual(self.score('b2', 'full', root2)['comparison_status'], 'INVALID_COMPARISON')

    # H. complete active-source evidence but incomplete original-neutral association.
    def test_H_original_neutral_association_retained(self):
        root = self.copy('b2', 'full')
        props = load(root / 'property.jsonl')
        index = next(i for i, x in enumerate(props) if x.get('reason') == 'ORIGINAL_NEUTRAL')
        dump(root / 'property.jsonl', props[:index] + props[index + 1:])
        out = self.score('b2', 'full', root)
        self.assertEqual(out['comparison_status'], 'INVALID_COMPARISON')
        root2 = self.copy('b1', 'full')
        lineage = load(root2 / 'lineage.jsonl')
        neutral = next(x['command_id'] for x in lineage if x.get('kind') == 'publish'
                       and x.get('stage') == 'receiver' and not f.source_origin(x.get('parent')))
        kept = [x for x in lineage if not (x.get('kind') == 'consume' and x.get('stage') == 'mapper'
                                           and (x.get('exact_parent') or {}).get('command_id') == neutral)]
        dump(root2 / 'lineage.jsonl', kept)
        out2 = self.score('b1', 'full', root2)
        self.assertEqual(out2['comparison_status'], 'INVALID_COMPARISON')
        self.assertEqual(out2['invalid_reasons'], ['ORIGINAL_EVENT_TO_MAPPER_ASSOCIATION_INCOMPLETE'])

    # I. incomplete CPU/RSS or clock evidence -> INVALID, policy UNKNOWN.
    def test_I_resource_or_clock_incomplete(self):
        root = self.copy('b1', 'full')
        events = load(root / 'events.jsonl')
        ack = next(x for x in events if x.get('kind') == 'readiness_ack')
        label = sorted(ack['participant_clocks'])[0]
        ack['participant_clocks'][label]['boot_id'] = 'different-boot'
        dump(root / 'events.jsonl', events)
        out = self.score('b1', 'full', root)
        self.assertEqual((out['comparison_status'], out['policy_status']), ('INVALID_COMPARISON', 'UNKNOWN'))
        self.assertIn('FULL_ACK_OR_COMMON_CLOCK_MISSING', out['invalid_reasons'])
        root2 = self.copy('b3', 'full')
        samples = load(root2 / 'resource_samples.jsonl')
        barrier, end = f.capture_window(root2)
        index = [i for i, x in enumerate(samples) if x.get('kind') == 'sample'
                 and barrier < x['monotonic_ns'] < end][20]
        label = sorted(samples[index]['targets'])[0]
        samples[index]['targets'][label]['status'] = 'MISSING'
        dump(root2 / 'resource_samples.jsonl', samples)
        out2 = self.score('b3', 'full', root2)
        self.assertEqual((out2['comparison_status'], out2['policy_status']), ('INVALID_COMPARISON', 'UNKNOWN'))
        self.assertIn('RESOURCE_CAPTURE_INCOMPLETE', out2['invalid_reasons'])

    # J. Gazebo settles but no qualifying explicit neutralization.
    def test_J_settled_without_qualifying_neutralization(self):
        root = self.copy('b2c', 'full')
        events = [x for x in load(root / 'stop_adapter.jsonl') if x['kind'] in ('ready',)]
        dump(root / 'stop_adapter.jsonl', events)
        out = self.score('b2c', 'full', root)
        self.assertLessEqual(out['gazebo_settled_after_trigger_ms'], 1000)
        self.assertEqual(out['policy_status'], 'FAIL_POLICY')
        self.assertIn('NO_EXPLICIT_NEUTRALIZATION_REQUEST', out['policy_violations'])
        for shift, violation in ((120_000_000, 'NEUTRALIZATION_REQUEST_OVER_50MS'),
                                 (-100_000_000, 'PREMATURE_NEUTRALIZATION_REQUEST_FALSE_REJECTION')):
            root2 = Path(self.tmp.name) / f'shift_{shift}'
            shutil.copytree(Q6RAW / cell('b2c', 'full'), root2)
            t_local = self.t_local(root2, 'b2c')
            events = load(root2 / 'stop_adapter.jsonl')
            for item in events:
                if item['kind'] == 'stop_request':
                    item['monotonic_ns'] = t_local + shift
            dump(root2 / 'stop_adapter.jsonl', events)
            late = self.score('b2c', 'full', root2)
            self.assertEqual(late['policy_status'], 'FAIL_POLICY')
            self.assertIn(violation, late['policy_violations'])

    def test_normal_false_rejection_is_fail_not_invalid(self):
        root = self.copy('b1', 'full')
        verdicts = load(root / 'gate_verdict.jsonl')
        for item in verdicts:
            if item.get('kind') is None and item.get('sample_id') == 'docker:40':
                item['allowed'] = False
        dump(root / 'gate_verdict.jsonl', verdicts)
        out = self.score('b1', 'full', root)
        self.assertEqual(out['comparison_status'], 'VALID_FORMAL_TRIAL')
        self.assertIn('NORMAL_ACTIVE_FALSE_REJECTION', out['policy_violations'])

    def test_blocked_pre_barrier_and_not_run(self):
        raw = Path(self.tmp.name) / 'raw'
        (raw / 'docker_b1_full_d3r09').mkdir(parents=True)
        (raw / 'docker_b1_full_d3r09' / 'exit.json').write_text('{"launch_exit": 1}\n')
        saved = f.RAW
        f.RAW = raw
        try:
            blocked = f.score_row(dict(row('b1', 'full'), trial_id='docker_b1_full_d3r09'))
            missing = f.score_row(dict(row('b1', 'full'), trial_id='docker_b1_full_d3r08'))
        finally:
            f.RAW = saved
        self.assertEqual((blocked['comparison_status'], blocked['policy_status']),
                         ('BLOCKED_MEASUREMENT', 'NOT_SCORED'))
        self.assertEqual(missing['comparison_status'], 'NOT_RUN')

    def test_pair_and_equivalence_on_setup(self):
        saved = f.RAW
        f.RAW = Q6RAW
        try:
            by_id = {'s': dict(attempt=cell('shim', 'full'), comparison_status='X'),
                     'a': dict(attempt=cell('b1', 'full'), comparison_status='X')}
            pc = f.pair_comparison(dict(trial_id='s'), dict(trial_id='a'), by_id)
            eq = f.b0_shim_pair(Q6RAW / cell('b0', 'full'), Q6RAW / cell('shim', 'full'))
        finally:
            f.RAW = saved
        self.assertEqual(pc['status'], 'PASS_SCHEDULE')
        self.assertEqual(pc['pre_fault_allowed_path'], 'PASS')
        self.assertEqual(eq['status'], 'PASS')
        self.assertAlmostEqual(eq['max_source_index_time_difference_ms'], 0.039295, places=6)

    def test_constants_match_registered_policy(self):
        self.assertEqual(f.ELIGIBLE, {f'docker:{i}' for i in range(36, 56)})
        self.assertEqual((f.LIMIT_NS, f.DECISION_MS, f.CONTINUE_MS, f.SETTLE_MS),
                         (250_000_000, 50.0, 300.0, 1000.0))


if __name__ == '__main__':
    unittest.main(verbosity=2)
