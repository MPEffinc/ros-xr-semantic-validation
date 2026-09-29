"""Frozen Docker D1 read-only scoring; setup, exact acceptance and interval motion differ."""
import argparse
import csv
import importlib.util
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT.parent
Q4_ANALYSIS = RUNS / 's4b_cp6b_resource_q4_20260923T070559Z/analysis'
PAIR_PATH = RUNS / 's4b_cp2_qualification_20260923T003626Z/analysis/pair_audit.py'
sys.path.insert(0, str(Q4_ANALYSIS))
from q4_measurement_audit import audit as measure, rows  # noqa: E402

spec = importlib.util.spec_from_file_location('frozen_pair_audit', PAIR_PATH)
pair = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pair)
pair.ROOT = ROOT
pair.RAW = ROOT / 'raw'
FIXTURE_SHA256 = '20dcbc12db4f54f3660f00662ed554c220a5de35ba1b2116d40e727ba83c918b'


def percentile(values, percentile=0.95):
    if not values:
        return None
    ordered = sorted(values)
    return ordered[max(0, int(len(ordered) * percentile + 0.999999999) - 1)]


def source_id(record):
    origin = record.get('source_origin')
    while isinstance(origin, dict):
        if 'sample_id' in origin:
            return origin['sample_id']
        origin = origin.get('parent')
    return None


def audit_trial(row):
    root = ROOT / 'raw' / row['trial_id']
    if not root.exists():
        return dict(trial_id=row['trial_id'], status='NOT_RUN')
    reasons = []
    exit_record = json.loads((root / 'exit.json').read_text()) if (root / 'exit.json').exists() else {}
    if exit_record.get('launch_exit') != 0:
        reasons.append('NO_SUCCESSFUL_CHILD_LAUNCH')
    sent = rows(root / 'sent.jsonl')
    if [x.get('index') for x in sent] != list(range(120)):
        reasons.append('NOT_120_ORDERED_SOURCE_INDICES')
    events = rows(root / 'events.jsonl')
    ack = next((x for x in events if x.get('kind') == 'readiness_ack'), None)
    barrier = next((x for x in events if x.get('kind') == 'barrier_release'), None)
    if not ack or not barrier:
        reasons.append('NO_FULL_GRAPH_RECORDER_START_ACK')
    if not ack or len({x.get('boot_id') for x in ack.get('participant_clocks', {}).values()}) != 1:
        reasons.append('CLOCK_CONTRACT_UNVERIFIED')
    if reasons:
        return dict(trial_id=row['trial_id'], status='INVALID_COMPARISON', reasons=reasons,
                    source_count=len(sent), exit=exit_record)

    motion = pair.trial(row['trial_id'], 120)
    measurement = measure(root)
    resource = measurement['resources']
    if motion['fixture_sha256'] != FIXTURE_SHA256:
        reasons.append('NORMALIZED_FIXTURE_CHANGED')
    if motion['initial_position_error_rad'] > 0.0001 or motion['initial_max_velocity_rad_s'] >= 0.001 or motion['initial_drift_rad'] >= 0.0001:
        reasons.append('INITIAL_GAZEBO_STATE_OUTSIDE_REGISTERED_TOLERANCE')
    if motion['active_controller_output_records'] <= 0 or motion['max_joint_excursion_rad'] <= 0.01:
        reasons.append('NO_POSITIVE_CONTROLLER_GAZEBO_CONTROL')
    if resource['status'] != 'COMPLETE_CAPTURE' or resource['q4_sender_lifecycle']['status'] != 'PASS':
        reasons.append('INCOMPLETE_100MS_OR_SENDER_LIFECYCLE_MEASUREMENT')
    eligible = {f'docker:{x["index"]}' for x in sent if x.get('phase') == 'active'}
    if len(eligible) != 20:
        reasons.append('UNEXPECTED_ACTIVE_FIXTURE_SIZE')
    callback = measurement['callback']
    if row['mode'] != 'b0' and (callback['source_parent_publications'] != 372 or
                               callback['exact_joins'] != 372 or callback['missing']):
        reasons.append('INCOMPLETE_EXACT_SOURCE_TO_SERVO_CALLBACK_BINDING')
    callback_first = {}
    for x in callback['joined']:
        if x['sample_id'] in eligible:
            callback_first[x['sample_id']] = min(callback_first.get(x['sample_id'], float('inf')),
                                                   x['sample_to_callback_ms'])
    if row['mode'] != 'b0' and set(callback_first) != eligible:
        reasons.append('ELIGIBLE_SOURCE_NOT_ALL_SEEN_AT_SERVO_CALLBACK')

    verdict_ids = set()
    denied = set()
    verdict_boundary = 'NO_ADDED_GATE'
    if row['mode'] == 'b1':
        verdict_boundary = 'SOURCE_SIDE_GATE'
        for x in rows(root / 'gate_verdict.jsonl'):
            sid = x.get('sample_id')
            if sid in eligible:
                verdict_ids.add(sid)
                if x.get('allowed') is False:
                    denied.add(sid)
    elif row['mode'] == 'b2':
        verdict_boundary = 'OFFICIAL_ROSMONITORING_ORACLE'
        source = (measurement.get('native_b2_exact_binding') or {}).get('joined', []) \
            if row['regime'] == 'native' else (measurement.get('monitor') or {}).get('joined', [])
        for x in source:
            sid = x.get('sample_id')
            if sid in eligible:
                verdict_ids.add(sid)
                safe = x.get('oracle_safe') if row['regime'] == 'native' else None
                if row['regime'] == 'full':
                    # Full transport joins are by event ID. Inspect the original
                    # property row for each exactly joined event, never by time.
                    safe = next((p.get('safe') for p in rows(root / 'property.jsonl')
                                 if p.get('monitor_event_id') == x['event_id']), None)
                if safe is False:
                    denied.add(sid)
        if row['regime'] == 'native':
            native = measurement.get('native_b2_exact_binding') or {}
            if native.get('source_bound_joins') != 372 or native.get('ambiguous'):
                reasons.append('NATIVE_PROPERTY_SOURCE_ASSOCIATION_INCOMPLETE')
        else:
            full = measurement.get('monitor') or {}
            if full.get('exact_full_transport_joins') != full.get('property_records'):
                reasons.append('FULL_PROPERTY_RECEIPT_BINDING_INCOMPLETE')
    elif row['mode'] == 'b3':
        verdict_boundary = 'ORIGINAL_MAPPER_CALLBACK_DIRECT_CHECK'
        for x in rows(root / 'lineage.jsonl'):
            if x.get('kind') != 'b3_mapper_verdict':
                continue
            sid = source_id(x)
            if sid in eligible:
                verdict_ids.add(sid)
                if x.get('verdict') is False:
                    denied.add(sid)
    if row['mode'] in ('b1', 'b2', 'b3') and verdict_ids != eligible:
        reasons.append('ELIGIBLE_SOURCE_VERDICT_COVERAGE_INCOMPLETE')
    # A complete, explicit rejection is a functional result, not setup failure.
    status = 'INVALID_COMPARISON' if reasons else 'VALID_FORMAL_TRIAL'
    resources = {label: dict(cpu_percent=metric['cpu_percent'],
                             cpu_seconds=metric['cpu_seconds'],
                             max_tree_rss_bytes=metric['max_tree_rss_bytes'])
                 for label, metric in resource['per_label'].items()}
    resources['sender'] = dict(cpu_percent=resource['q4_sender_lifecycle']['cpu_percent'],
                               cpu_seconds=resource['q4_sender_lifecycle']['cpu_seconds'],
                               max_tree_rss_bytes=resource['q4_sender_lifecycle']['observed_peak_rss_bytes'])
    resource_samples = [x for x in rows(root / 'resource_samples.jsonl')
                        if x.get('kind') == 'sample' and
                        barrier['start_monotonic_ns'] <= x.get('monotonic_ns', -1) <=
                        next(y['monotonic_ns'] for y in events if y.get('kind') == 'capture_end')]
    participant_wall_seconds = (resource_samples[-1]['monotonic_ns'] -
                                resource_samples[0]['monotonic_ns']) / 1e9
    return dict(trial_id=row['trial_id'], repetition=int(row['repetition']),
                arm=('b2c' if row['composed'] == '1' else row['mode']), regime=row['regime'],
                status=status, reasons=reasons, source_count=len(sent),
                active_eligible_source_count=len(eligible), exact_eligible_callback_count=len(callback_first),
                verdict_boundary=verdict_boundary,
                exact_eligible_verdict_source_count=len(verdict_ids),
                explicitly_denied_eligible_source_count=len(denied),
                false_reject_count=None if verdict_boundary == 'NO_ADDED_GATE' or verdict_ids != eligible else len(denied),
                first_callback_latency_p95_ms=percentile(list(callback_first.values())),
                first_callback_latency_by_source_ms=callback_first,
                callback_publications=callback['source_parent_publications'],
                exact_callback_joins=callback['exact_joins'],
                controller_output_records=motion['active_controller_output_records'],
                max_joint_excursion_rad=motion['max_joint_excursion_rad'],
                final_joint_position_rad=motion['final_joint_position_rad'],
                normalized_fixture_sha256=motion['fixture_sha256'],
                resources=resources,
                measured_participant_resource_wall_seconds=participant_wall_seconds,
                measured_sender_resource_wall_seconds=resource['q4_sender_lifecycle']['wall_seconds'],
                total_observed_process_cpu_seconds=sum(x['cpu_seconds'] for x in resources.values()),
                b2_native_source_bound_joins=None if row['mode'] != 'b2' or row['regime'] != 'native'
                    else measurement['native_b2_exact_binding']['source_bound_joins'],
                monitor_internal_forward_time='UNKNOWN',
                source_to_specific_controller_or_joint_parent='UNKNOWN_INTERVAL_ONLY')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--order', type=int)
    parser.add_argument('--all', action='store_true')
    args = parser.parse_args()
    assert (args.order is None) != (not args.all)
    with (ROOT / 'schedule.csv').open(newline='') as file:
        schedule = list(csv.DictReader(file))
    assert len(schedule) == 50
    if args.order:
        row = schedule[args.order - 1]
        (ROOT / 'analysis' / (row['trial_id'] + '.json')).write_text(
            json.dumps(audit_trial(row), indent=2, sort_keys=True) + '\n')
        return
    trials = [audit_trial(row) for row in schedule]
    comparisons = []
    for repetition in range(1, 6):
        group = [x for x in schedule if int(x['repetition']) == repetition]
        shim = next(x for x in group if x['mode'] == 'shim')
        for row in group:
            if row is shim:
                continue
            first, second = shim['trial_id'], row['trial_id']
            if not (ROOT / 'raw' / first).exists() or not (ROOT / 'raw' / second).exists():
                comparisons.append(dict(pair=[first, second], status='NOT_RUN'))
            else:
                comparisons.append(pair.summarize(first, second, 120))
    by_id = {x['trial_id']: x for x in trials}
    for comparison in comparisons:
        if comparison['status'] != 'PASS':
            continue
        shim, arm = (by_id[name] for name in comparison['pair'])
        comparison['observed_cpu_seconds_delta_vs_shim'] = (
            arm['total_observed_process_cpu_seconds'] - shim['total_observed_process_cpu_seconds'])
        comparison['resource_wall_seconds'] = [
            shim['measured_participant_resource_wall_seconds'],
            arm['measured_participant_resource_wall_seconds']]
        common = sorted(set(shim['resources']) & set(arm['resources']))
        comparison['shared_process_cpu_percent_delta_vs_shim'] = {
            label: arm['resources'][label]['cpu_percent'] - shim['resources'][label]['cpu_percent']
            for label in common}
        comparison['shared_process_peak_rss_bytes_delta_vs_shim'] = {
            label: arm['resources'][label]['max_tree_rss_bytes'] -
                   shim['resources'][label]['max_tree_rss_bytes'] for label in common}
        first_shim = shim['first_callback_latency_by_source_ms']
        first_arm = arm['first_callback_latency_by_source_ms']
        same_sources = sorted(set(first_shim) & set(first_arm))
        comparison['paired_first_callback_latency_delta_p95_ms'] = percentile(
            [first_arm[sid] - first_shim[sid] for sid in same_sources])
        comparison['paired_first_callback_latency_joined_sources'] = len(same_sources)
        comparison['exact_internal_gate_transport_latency_p95_ms'] = None
    status = 'D1_FORMAL_COMPLETE' if all(x['status'] == 'VALID_FORMAL_TRIAL' for x in trials) and \
        all(x['status'] == 'PASS' for x in comparisons) else 'D1_FORMAL_INCOMPLETE_OR_INVALID'
    output = dict(status=status, protocol='XRROS-S4-1.0.0', seed=20260922,
                  trials=trials, matched_pairs=comparisons,
                  no_invalid_state_or_recovery_test='D1_NORMAL_ONLY')
    (ROOT / 'analysis/formal_summary.json').write_text(json.dumps(output, indent=2,
                                                                   sort_keys=True) + '\n')
    print(status, sum(x['status'] == 'VALID_FORMAL_TRIAL' for x in trials), '/50')


if __name__ == '__main__':
    main()
