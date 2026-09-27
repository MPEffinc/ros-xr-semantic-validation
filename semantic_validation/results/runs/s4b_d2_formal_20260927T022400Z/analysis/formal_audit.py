#!/usr/bin/env python3
"""Prospective D2 policy scorer: frozen setup evidence plus separate policy rules.

Exact source→Servo callback is event-level. Controller and joints are only
interval outcomes; no per-source joint parent is invented. CP9 setup raw may
be used for software preflight, never counted as formal repetitions.
"""
import argparse
import csv
import json
import math
import sys
from pathlib import Path
from local_trigger import local_invalid_observation
from trajectory_pair import joint_at_source_index

ROOT = Path(__file__).resolve().parents[1]
Q9 = ROOT.parent / 's4b_cp9_d2q3_20260927T020700Z'
sys.path.insert(0, str(Q9 / 'analysis'))
import cp9_qualification_audit as qualified  # noqa: E402

qualified.ROOT = ROOT
qualified.RAW = ROOT / 'raw'
qualified.prior.ROOT = ROOT
qualified.prior.pair.ROOT = ROOT
qualified.prior.pair.RAW = ROOT / 'raw'
rows = qualified.prior.rows
source_origin = qualified.prior.source_origin
ELIGIBLE = {f'docker:{i}' for i in range(36, 56)}
FORBIDDEN = {f'docker:{i}' for i in range(56, 76)}


def first_callback_latency(measurement):
    first = {}
    for item in measurement['callback']['joined']:
        sid = item['sample_id']
        if sid in ELIGIBLE:
            first[sid] = min(first.get(sid, float('inf')),
                             item['sample_to_callback_ms'])
    return first


def percentile(values, p=.95):
    if not values:
        return None
    ordered = sorted(values)
    return ordered[max(0, math.ceil(len(ordered) * p) - 1)]


def active_verdicts(root, mode, regime, monitor):
    """Return 20 exact source verdicts or UNKNOWN, never a time join."""
    if mode == 'b1':
        items = [r for r in rows(root / 'gate_verdict.jsonl')
                 if r.get('sample_id') in ELIGIBLE]
        groups = {r['sample_id']: r['allowed'] for r in items}
        if len(items) != 20 or set(groups) != ELIGIBLE:
            return None
        return groups
    if mode == 'b3':
        items = [r for r in rows(root / 'lineage.jsonl')
                 if r.get('kind') == 'b3_mapper_verdict' and
                 (source_origin(r.get('source_origin')) or {}).get('sample_id') in ELIGIBLE]
        groups = {(source_origin(r['source_origin']) or {})['sample_id']: r['verdict']
                  for r in items}
        if set(groups) != ELIGIBLE or any(v is not True and v is not False for v in groups.values()):
            return None
        return groups
    if mode == 'b2':
        # The frozen CP9 monitor_integrity checks exact ID/hash/property/status
        # association and every active source. This is not a timestamp join.
        if monitor is None or monitor['issues'] or set(monitor['active_source_ids']) != ELIGIBLE:
            return None
        bad = {s.rsplit('_', 1)[-1] for s in monitor['functional_flags']}
        if bad:
            # A flag is a property event ID/hash, not necessarily a source ID.
            # Retain explicit event failures without fabricating per-source IDs.
            return {'event_failure_count': len(monitor['functional_flags']),
                    'source_coverage': 20}
        return {sid: True for sid in ELIGIBLE}
    return None


def audit_trial(row):
    name = row['trial_id']
    root = ROOT / 'raw' / name
    if not root.exists():
        return dict(trial_id=name, comparison_status='NOT_RUN', policy_status='NOT_SCORED')
    try:
        evidence = qualified.prior.inspect(dict(row, cell=name))
        if row['mode'] != 'b0':
            cache = qualified.mapper_cache_audit(root, row['baseline'])
            if cache['status'] != 'PASS':
                evidence['reasons'].append('MAPPER_CACHED_PARENT_AUDIT')
        if row['mode'] == 'b2':
            call = qualified.monitor_call_audit(root)
            if call['status'] != 'PASS':
                evidence['reasons'].append('MONITOR_PUBLISH_CALL_AUDIT')
    except (AssertionError, KeyError, IndexError, ValueError, FileNotFoundError, TypeError, StopIteration) as exc:
        return dict(trial_id=name, comparison_status='INVALID_COMPARISON',
                    policy_status='NOT_SCORED', evidence_error=f'{type(exc).__name__}: {exc}')
    if evidence['status'] == 'NOT_RUN' or evidence.get('reasons'):
        return dict(trial_id=name, comparison_status='INVALID_COMPARISON',
                    policy_status='NOT_SCORED', setup_reasons=evidence.get('reasons', []),
                    setup_status=evidence['status'])

    mode, regime = row['mode'], row['regime']
    measurement = qualified.prior.measurement_audit(root)
    first = first_callback_latency(measurement)
    resource = measurement['resources']
    per_label = {label: dict(cpu_percent=m['cpu_percent'],
                             cpu_seconds=m['cpu_seconds'],
                             max_tree_rss_bytes=m['max_tree_rss_bytes'])
                 for label, m in resource['per_label'].items()}
    per_label['sender'] = dict(cpu_percent=resource['q4_sender_lifecycle']['cpu_percent'],
                               cpu_seconds=resource['q4_sender_lifecycle']['cpu_seconds'],
                               max_tree_rss_bytes=resource['q4_sender_lifecycle']['observed_peak_rss_bytes'])
    verdicts = active_verdicts(root, mode, regime, evidence.get('monitor'))
    if mode in ('b1', 'b2', 'b3') and verdicts is None:
        return dict(trial_id=name, comparison_status='INVALID_COMPARISON',
                    policy_status='NOT_SCORED', setup_reasons=['ACTIVE_VERDICT_EXACT_COVERAGE_UNKNOWN'])

    violations = []
    if evidence.get('functional_flags'):
        violations += evidence['functional_flags']
    if isinstance(verdicts, dict) and verdicts.get('event_failure_count'):
        violations.append('ELIGIBLE_ACTIVE_ORACLE_FALSE_REJECTION')
    if isinstance(verdicts, dict) and all(isinstance(x, bool) for x in verdicts.values()):
        false_rejects = sum(v is False for v in verdicts.values())
    else:
        false_rejects = None if verdicts is None else verdicts.get('event_failure_count')
    if mode in ('b1', 'b2', 'b3') and false_rejects:
        violations.append('NORMAL_ACTIVE_FALSE_REJECTION')
    if mode != 'b0' and set(first) != ELIGIBLE:
        return dict(trial_id=name, comparison_status='INVALID_COMPARISON',
                    policy_status='NOT_SCORED', setup_reasons=['ACTIVE_SOURCE_TO_SERVO_CALLBACK_INCOMPLETE'])

    decision = evidence['local_detection_ns']
    local_trigger_ns = local_invalid_observation(root, mode, evidence['fault_sample_ns'], rows)
    if mode in ('b1', 'b2', 'b3') and local_trigger_ns is None:
        return dict(trial_id=name, comparison_status='INVALID_COMPARISON',
                    policy_status='NOT_SCORED', setup_reasons=['EXACT_LOCAL_INVALID_OBSERVATION_MISSING'])
    decision_delay_ms = None if decision is None or local_trigger_ns is None else (decision - local_trigger_ns) / 1e6
    fault_callbacks = evidence['fault_callbacks']
    forbidden_commands = fault_callbacks.get('forbidden_fault_source_nonzero_callbacks')
    if mode in ('b1', 'b2', 'b3'):
        if fault_callbacks['status'] != 'EXACT_CALLBACK_BOUNDARY' or forbidden_commands is None:
            return dict(trial_id=name, comparison_status='INVALID_COMPARISON',
                        policy_status='NOT_SCORED', setup_reasons=['FORBIDDEN_CALLBACK_PARENT_UNKNOWN'])
        if forbidden_commands:
            violations.append('FORBIDDEN_FAULT_SOURCE_NONZERO_SERVO_CALLBACK')
    stop = evidence['stop_events']
    requests = [x for x in stop if x['kind'] == 'stop_request']
    replies = [x for x in stop if x['kind'] == 'stop_reply']
    zeros = [x for x in stop if x['kind'] == 'controller_zero']
    request_delay_ms = None if not requests or local_trigger_ns is None else (
        requests[0]['monotonic_ns'] - local_trigger_ns) / 1e6
    if mode in ('b1', 'b2', 'b3') and (decision_delay_ms is None or decision_delay_ms > 50):
        violations.append('LOCAL_DECISION_OVER_50MS')
    if mode in ('b1', 'b2', 'b3'):
        if not requests:
            violations.append('NO_EXPLICIT_NEUTRALIZATION_REQUEST')
        elif request_delay_ms is None or request_delay_ms > 50:
            violations.append('NEUTRALIZATION_REQUEST_OVER_50MS')
        if requests and (not replies or not zeros):
            violations.append('STOP_REPLY_OR_CONTROLLER_ZERO_ABSENT')

    consequence = evidence['consequence']
    trigger_ns = local_trigger_ns if local_trigger_ns is not None else evidence['fault_sample_ns']
    last = consequence['last_post_fault_nonzero_ns']
    last_nonzero_after_trigger_ms = 0.0 if last is None or last <= trigger_ns else (
        last - trigger_ns) / 1e6
    settled_ns = consequence['settled_ns']
    settled_after_trigger_ms = None if settled_ns is None else (
        settled_ns - trigger_ns) / 1e6
    if mode in ('b1', 'b2', 'b3'):
        if last_nonzero_after_trigger_ms > 300:
            violations.append('CONTROLLER_NONZERO_OVER_300MS')
        if settled_after_trigger_ms is None or settled_after_trigger_ms > 1000:
            violations.append('GAZEBO_NOT_SETTLED_BY_TRIGGER_PLUS_1S')

    policy = ('ORIGINAL_CONTROL_NOT_SCORED' if mode == 'b0' else
              'OBSERVATIONAL_SHIM_NOT_SCORED' if mode == 'shim' else
              'FAIL_POLICY' if violations else 'PASS_POLICY')
    return dict(trial_id=name, repetition=int(row['repetition']), arm=row['baseline'],
                regime=regime, comparison_status='VALID_FORMAL_TRIAL', policy_status=policy,
                policy_violations=sorted(set(violations)),
                eligible_active_source_count=20, active_false_reject_count=false_rejects,
                exact_eligible_servo_callback_count=len(first),
                first_callback_latency_by_source_ms=first,
                first_callback_latency_p95_ms=percentile(list(first.values())),
                exact_forbidden_fault_source_nonzero_callback_count=(
                    None if forbidden_commands is None else len(forbidden_commands)),
                earlier_accepted_source_nonzero_callbacks_after_detection=len(
                    fault_callbacks.get('earlier_source_nonzero_callbacks_after_detection', [])),
                local_invalid_observation_ns=local_trigger_ns,
                local_decision_delay_ms=decision_delay_ms,
                neutral_request_delay_ms=request_delay_ms,
                stop_request_source=requests[0]['source'] if requests else None,
                stop_reply_observed=bool(replies), controller_zero_observed=bool(zeros),
                last_nonzero_controller_after_trigger_ms=last_nonzero_after_trigger_ms,
                gazebo_settled_after_trigger_ms=settled_after_trigger_ms,
                gazebo_moving_before_fault_rad_s=consequence['moving_before_fault'],
                gazebo_joint_samples=consequence['joint_samples'],
                controller_output_samples=consequence['controller_samples'],
                monitor_input_publications=(evidence.get('monitor') or {}).get('input_publications'),
                monitor_property_rows=(evidence.get('monitor') or {}).get('property_rows'),
                monitor_status_rows=(evidence.get('monitor') or {}).get('status_rows'),
                resource_100ms_status=resource['status'], process_resource=per_label,
                total_observed_cpu_seconds=sum(x['cpu_seconds'] for x in per_label.values()),
                monitor_internal_post_verdict_publish_time='UNKNOWN',
                exact_source_to_specific_servo_output_controller_joint='UNKNOWN_INTERVAL_ONLY')


def pair_comparison(shim_row, arm_row, by_id):
    first, second = shim_row['trial_id'], arm_row['trial_id']
    if first not in by_id or second not in by_id or not (ROOT / 'raw' / first).exists() or not (ROOT / 'raw' / second).exists():
        return dict(pair=[first, second], status='NOT_RUN')
    try:
        a, b = (qualified.prior.pair.trial(name, 120) for name in (first, second))
    except (AssertionError, KeyError, IndexError, ValueError, FileNotFoundError, StopIteration) as exc:
        return dict(pair=[first, second], status='INVALID_COMPARISON', evidence_error=f'{type(exc).__name__}: {exc}')
    schedule_ms = max(abs(x-y) for x, y in zip(a['actual_offsets_ms'], b['actual_offsets_ms']))
    same = a['fixture_sha256'] == b['fixture_sha256']
    clock = a['boot_id'] == b['boot_id'] and a['time_namespace'] == b['time_namespace']
    status = ('PASS_SCHEDULE' if same and clock and schedule_ms <= 5 else 'INVALID_COMPARISON')
    result = dict(pair=[first, second], status=status, same_fixture=same,
                  same_clock_namespace=clock, max_source_offset_difference_ms=schedule_ms)
    pre_a = joint_at_source_index(ROOT / 'raw' / first, 55, rows, qualified.prior.ARM)
    pre_b = joint_at_source_index(ROOT / 'raw' / second, 55, rows, qualified.prior.ARM)
    if pre_a is None or pre_b is None:
        result['pre_fault_allowed_path'] = 'UNKNOWN_MISSING_JOINT_SAMPLE'
    else:
        diff = max(abs(x-y) for x, y in zip(pre_a['positions_rad'], pre_b['positions_rad']))
        result['pre_fault_allowed_path'] = ('PASS' if diff <= .02 else 'FAIL_POLICY')
        result['pre_fault_max_joint_difference_rad'] = diff
        result['pre_fault_joint_sample_offset_ms'] = [pre_a['joint_sample_offset_ms'],
                                                      pre_b['joint_sample_offset_ms']]
    # The source-index-aligned joint state is an interval trajectory comparison;
    # it does not prove a specific source sample caused a specific joint sample.
    if result['pre_fault_allowed_path'] == 'UNKNOWN_MISSING_JOINT_SAMPLE':
        result['status'] = 'INVALID_COMPARISON'
        return result
    x, y = by_id[first], by_id[second]
    if x.get('comparison_status') == y.get('comparison_status') == 'VALID_FORMAL_TRIAL':
        common = sorted(set(x['first_callback_latency_by_source_ms']) &
                        set(y['first_callback_latency_by_source_ms']))
        result['paired_source_to_first_callback_delta_p95_ms'] = percentile([
            y['first_callback_latency_by_source_ms'][sid] -
            x['first_callback_latency_by_source_ms'][sid] for sid in common])
        result['paired_callback_source_count'] = len(common)
        result['observed_cpu_seconds_delta_vs_shim'] = (
            y['total_observed_cpu_seconds'] - x['total_observed_cpu_seconds'])
        if arm_row['mode'] not in ('b0', 'shim') and result['pre_fault_allowed_path'] == 'FAIL_POLICY':
            y['policy_violations'].append('NORMAL_PREFAULT_JOINT_PATH_OVER_0_02RAD')
            y['policy_violations'] = sorted(set(y['policy_violations']))
            y['policy_status'] = 'FAIL_POLICY'
            result['policy_effect_recorded_in_arm'] = True
    # Fault-case final position is an outcome, NOT a fairness gate. The
    # <=.02 rad allowed-path criterion is already qualified by B0/shim and
    # must not invalidate a defense for changing the post-fault trajectory.
    result['post_fault_final_joint_difference_is_policy_outcome_not_pair_gate'] = True
    result['exact_added_gate_transport_latency_p95_ms'] = None
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--order', type=int)
    parser.add_argument('--all', action='store_true')
    args = parser.parse_args()
    assert (args.order is None) != (not args.all)
    with (ROOT / 'schedule.csv').open(newline='') as stream:
        schedule = list(csv.DictReader(stream))
    assert len(schedule) == 50 and [int(x['order']) for x in schedule] == list(range(1, 51))
    assert all(x['case'] == 'D2' and int(x['seed']) == 20260922 for x in schedule)
    if args.order is not None:
        assert 1 <= args.order <= 50
        row = schedule[args.order-1]
        out = audit_trial(row)
        (ROOT / 'analysis' / (row['trial_id'] + '.json')).write_text(
            json.dumps(out, indent=2, sort_keys=True) + '\n')
        print(row['trial_id'], out['comparison_status'], out['policy_status'])
        return
    trials = [audit_trial(r) for r in schedule]
    by_id = {x['trial_id']: x for x in trials}
    pairs = []
    b0_shim = []
    for repeat in range(1, 6):
        group = [x for x in schedule if int(x['repetition']) == repeat]
        shim = next(x for x in group if x['mode'] == 'shim')
        b0 = next(x for x in group if x['mode'] == 'b0')
        if (ROOT / 'raw' / shim['trial_id']).exists() and (ROOT / 'raw' / b0['trial_id']).exists():
            try:
                b0_shim.append(qualified.prior.pair.summarize(b0['trial_id'], shim['trial_id'], 120))
            except (AssertionError, KeyError, IndexError, ValueError, FileNotFoundError, StopIteration) as exc:
                b0_shim.append(dict(pair=[b0['trial_id'], shim['trial_id']],
                                    status='INVALID_COMPARISON', evidence_error=f'{type(exc).__name__}: {exc}'))
        else:
            b0_shim.append(dict(pair=[b0['trial_id'], shim['trial_id']], status='NOT_RUN'))
        for arm in group:
            if arm is not shim:
                pairs.append(pair_comparison(shim, arm, by_id))
    complete = (all(x['comparison_status'] == 'VALID_FORMAL_TRIAL' for x in trials) and
                all(x['status'] == 'PASS' for x in b0_shim) and
                all(x['status'] == 'PASS_SCHEDULE' for x in pairs))
    output = dict(status='D2_FORMAL_COMPLETE' if complete else 'D2_FORMAL_PARTIAL_OR_INVALID',
                  protocol='XRROS-S4-1.0.0', seed=20260922, trials=trials,
                  b0_shim_equivalence=b0_shim, matched_source_schedule_pairs=pairs,
                  exact_internal_added_gate_transport_latency='UNKNOWN',
                  exact_source_to_specific_joint_parent='UNKNOWN_INTERVAL_ONLY',
                  setup_trials_not_formal='CP9 D2Q3 qualification raw excluded')
    (ROOT / 'analysis/formal_summary.json').write_text(json.dumps(output, indent=2,
                                                                   sort_keys=True) + '\n')
    print(output['status'], sum(x['comparison_status'] == 'VALID_FORMAL_TRIAL' for x in trials), '/50')


if __name__ == '__main__':
    main()
