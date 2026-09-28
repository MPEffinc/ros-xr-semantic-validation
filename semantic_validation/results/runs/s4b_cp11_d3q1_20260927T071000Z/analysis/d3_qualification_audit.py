#!/usr/bin/env python3
"""Prospective D3 setup audit; no formal policy score or source-to-joint claim."""
import csv
import hashlib
import json
import math
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / 'raw'
Q3 = ROOT.parent / 's4b_cp5b_measurement_20260923T054101Z'
Q4 = ROOT.parent / 's4b_cp6b_resource_q4_20260923T070559Z'
sys.path.insert(0, str(Q3 / 'analysis'))
sys.path.insert(0, str(Q4 / 'analysis'))
from q3_measurement_audit import rows, source_origin, callback_latency, resources
from lifecycle_resource_audit import trial as lifecycle_trial

ARM = ('shoulder_pan_joint', 'shoulder_lift_joint', 'elbow_joint',
       'wrist_1_joint', 'wrist_2_joint', 'wrist_3_joint')
MODES = [('b0', 'full'), ('shim', 'full'), ('b1', 'native'), ('b1', 'full'),
         ('b2', 'native'), ('b2', 'full'), ('b2c', 'native'), ('b2c', 'full'),
         ('b3', 'native'), ('b3', 'full')]


def fixture(root):
    sent = rows(root / 'sent.jsonl')
    errors = []
    if len(sent) != 120 or [x.get('index') for x in sent] != list(range(120)):
        return sent, ['PLANNED_120_SOURCE_SLOTS_INCOMPLETE']
    barrier = json.loads((root / 'barrier.json').read_text())['start_monotonic_ns']
    for item in sent:
        i = item['index']
        expected_phase = ('idle' if i < 20 else 'reference' if i < 36 else
                          'active' if i < 56 else 'fault_window' if i < 76 else 'tail')
        if item.get('phase') != expected_phase or item.get('scheduled_ns') != barrier + i * 50_000_000:
            errors.append(f'SCHEDULE_OR_PHASE_{i}')
        if 56 <= i < 76:
            if (item.get('sent') is not False or item.get('wire') is not None or
                    item.get('sample_ns') is not None or item.get('send_ns') is not None):
                errors.append(f'NO_BYTE_SLOT_CREATED_SOURCE_{i}')
            continue
        try:
            payload = json.loads(item['wire'])
            meta = payload['_qualification']
            hand = payload['right_hand']
            if (item['sent'] is not True or meta['sample_id'] != f'docker:{i}' or
                    meta['generation_id'] != 1 or meta['source_timestamp_ns'] != item['sample_ns'] or
                    meta['native_state'] != {'isTracked': True} or hand['isTracked'] is not True or
                    hand['pos'] != {'x': .35 if 36 <= i < 76 else .2, 'y': .2, 'z': .3} or
                    payload['controls']['teleop_enable'] != (20 <= i < 56)):
                errors.append(f'REAL_SOURCE_FIXTURE_{i}')
        except (KeyError, TypeError, ValueError):
            errors.append(f'REAL_SOURCE_PARSE_{i}')
    return sent, errors


def normalized_hash(sent):
    normalized = []
    for row in sent:
        item = {'index': row['index'], 'phase': row['phase'], 'sent': row['sent']}
        if row['sent']:
            wire = json.loads(row['wire'])
            wire.pop('timestamp', None)
            wire['_qualification'].pop('source_timestamp_ns', None)
            item['wire'] = wire
        normalized.append(item)
    return hashlib.sha256(json.dumps(normalized, sort_keys=True,
                                      separators=(',', ':')).encode()).hexdigest()


def joint_control(root, trigger_ns):
    topic_rows = rows(root / 'topics.jsonl')
    joints, nonzero = [], []
    for record in topic_rows:
        payload = record['payload']
        if record['topic'] == '/joint_states':
            try:
                pos = [payload['position'][payload['name'].index(name)] for name in ARM]
                vel = [payload['velocity'][payload['name'].index(name)] for name in ARM]
                if all(math.isfinite(v) for v in pos + vel):
                    joints.append((record['monotonic_ns'], pos, vel))
            except (KeyError, ValueError, IndexError):
                pass
        elif record['topic'] == '/joint_group_velocity_controller/commands':
            if any(abs(x) > 1e-6 for x in payload['data']):
                nonzero.append(record['monotonic_ns'])
    before = [max(abs(v) for v in vel) for t, _, vel in joints
              if trigger_ns - 100_000_000 <= t < trigger_ns]
    settled = None
    for t, pos, vel in joints:
        if t < trigger_ns:
            continue
        window = [(q, p, v) for q, p, v in joints if t <= q <= t + 520_000_000]
        if (len(window) >= 5 and window[-1][0] - t >= 500_000_000 and
                all(max(abs(x) for x in v) < .001 for _, _, v in window) and
                all(abs(p[k] - pos[k]) < .0001 for _, p, _ in window for k in range(6))):
            settled = t
            break
    return dict(joint_samples=len(joints), controller_nonzero_count=len(nonzero),
                max_joint_velocity_before_trigger=max(before, default=None),
                nonzero_controller_before_trigger=sum(trigger_ns - 100_000_000 <= t < trigger_ns
                                                      for t in nonzero),
                last_post_trigger_nonzero_ns=max((t for t in nonzero if t >= trigger_ns), default=None),
                settled_ns=settled,
                settled_after_trigger_ms=None if settled is None else (settled - trigger_ns) / 1e6)


def monitor_events(root, regime):
    suffix = 'full' if regime == 'full' else 'native'
    property_rows = rows(root / 'property.jsonl')
    statuses = [x for x in rows(root / f'monitor_{suffix}_status.jsonl') if x.get('status') == 'event']
    props_by_tick = {x['tick_id']: x for x in property_rows if x.get('event_kind') == 'tick'}
    status_by_tick = defaultdict(list)
    for status in statuses:
        if status.get('interface') == '/s4b/d3/tick':
            try:
                status_by_tick[json.loads(status['event']['data'])['tick_id']].append(status)
            except (KeyError, TypeError, ValueError):
                pass
    received_tick_ids = [json.loads(x['payload']['data'])['tick_id'] for x in rows(root / 'topics.jsonl')
                         if x.get('topic') == '/s4b/d3/tick']
    problems = []
    expected = {f'tick:{i}' for i in range(300)}
    if set(props_by_tick) != expected or set(status_by_tick) != expected:
        problems.append('OFFICIAL_TICK_PROPERTY_STATUS_COVERAGE')
    if any(len(x) != 1 for x in status_by_tick.values()):
        problems.append('DUPLICATE_TICK_STATUS_ID')
    for tick_id, prop in props_by_tick.items():
        stats = status_by_tick.get(tick_id, [])
        if len(stats) != 1:
            continue
        decision = stats[0].get('decision')
        receipt_count = received_tick_ids.count(tick_id)
        if prop['safe'] and (decision != 'forwarded' or receipt_count != 1):
            problems.append(f'SAFE_TICK_NOT_RECEIVED_{tick_id}')
        if not prop['safe'] and (decision != 'blocked' or receipt_count):
            problems.append(f'BLOCKED_TICK_LEAK_{tick_id}')
    if len(received_tick_ids) != len(set(received_tick_ids)):
        problems.append('DUPLICATE_TICK_RECEIPT')
    return dict(property_ticks=len(props_by_tick), official_status_ticks=sum(map(len, status_by_tick.values())),
                forwarded_tick_receipts=len(received_tick_ids),
                first_silence_tick=next((x for x in property_rows
                                         if x.get('event_kind') == 'tick' and not x.get('safe')), None),
                issues=problems[:100], issue_count=len(problems))


def inspect(mode, regime):
    name = f'docker_{mode}_{regime}_cp11d3setup01'
    root = RAW / name
    if not root.exists():
        return dict(trial=name, status='NOT_RUN')
    issues = []
    exit_record = json.loads((root / 'exit.json').read_text()) if (root / 'exit.json').exists() else {}
    if exit_record.get('launch_exit') != 0:
        issues.append('LAUNCH_NONZERO')
    if not (root / 'barrier.json').exists():
        return dict(trial=name, status='BLOCKED_MEASUREMENT', issues=issues+['NO_START_BARRIER'])
    sent, fixture_issues = fixture(root)
    issues += fixture_issues
    if len(sent) != 120:
        return dict(trial=name, status='BLOCKED_MEASUREMENT', issues=issues)
    events = rows(root / 'events.jsonl')
    ack = next((x for x in events if x.get('kind') == 'readiness_ack'), None)
    if not ack or len({x.get('boot_id') for x in ack.get('participant_clocks', {}).values()}) != 1:
        issues.append('FULL_ACK_OR_COMMON_CLOCK_MISSING')
    ticks = rows(root / 'd3_ticks.jsonl')
    if (len(ticks) != 300 or [x.get('index') for x in ticks] != list(range(300)) or
            any(x.get('source_sample_id') is not None for x in ticks)):
        issues.append('COMMON_TICK_INCOMPLETE_OR_FABRICATED_SOURCE')
    if mode == 'b1':
        gate_ticks = rows(root / 'd3_gate_ticks.jsonl')
        if len(gate_ticks) != 300:
            issues.append('B1_TICK_DECISION_INCOMPLETE')
    measurements = dict(resources=resources(root), lifecycle=lifecycle_trial(root))
    if measurements['resources']['status'] != 'COMPLETE_CAPTURE' or measurements['lifecycle']['status'] != 'PASS':
        issues.append('RESOURCE_CAPTURE_INCOMPLETE')
    callback = None if mode == 'b0' else callback_latency(root)
    if callback and (callback['missing'] or callback['exact_joins'] != callback['source_parent_publications']):
        issues.append('EXACT_SOURCE_TO_SERVO_CALLBACK_INCOMPLETE')
    trigger_ns = sent[55]['send_ns'] + 250_000_000 if sent[55].get('send_ns') else None
    control = joint_control(root, trigger_ns) if trigger_ns else None
    if not control or not control['max_joint_velocity_before_trigger'] or control['max_joint_velocity_before_trigger'] <= .001:
        issues.append('NOT_MOVING_AT_SILENCE_TRIGGER')
    if control and not control['nonzero_controller_before_trigger']:
        issues.append('NO_PRETRIGGER_CONTROLLER_OUTPUT')
    monitor = monitor_events(root, regime) if mode in ('b2', 'b2c') else None
    if monitor and monitor['issues']:
        issues.append('OFFICIAL_TICK_EVENT_ASSOCIATION_INCOMPLETE')
    if mode in ('b1', 'b3', 'b2c') and not (root / 'stop_adapter.ready').exists():
        issues.append('ORDINARY_STOP_ADAPTER_NOT_READY')
    source_events = [x for x in rows(root / 'lineage.jsonl') if x.get('kind') == 'source_received']
    if mode != 'b0' and {f'docker:{i}' for i in range(120) if not 56 <= i < 76} - {
            (x.get('metadata') or {}).get('sample_id') for x in source_events}:
        issues.append('ORIGINAL_RECEIVER_SOURCE_COVERAGE')
    return dict(trial=name, status='MEASUREMENT_QUALIFIED' if not issues else 'BLOCKED_MEASUREMENT',
                issues=issues, source_real_count=100, no_byte_indices=list(range(56, 76)),
                fixture_sha256=normalized_hash(sent),
                fault_trigger_from_sender_send_ns=trigger_ns,
                fault_trigger_note='B0 comparison proxy; B1/B2/B3 local receipt differs and is scored separately',
                callback_exact_joins=None if callback is None else callback['exact_joins'],
                callback_missing=None if callback is None else callback['missing'],
                monitor=monitor, control=control,
                resources=measurements['resources']['status'], lifecycle=measurements['lifecycle']['status'],
                policy_verdict='NOT_SCORED_BY_SETUP_AUDIT',
                source_to_specific_controller_or_joint_parent='UNKNOWN')


def pair(first, second):
    a, b = (RAW / first, RAW / second)
    if not a.exists() or not b.exists():
        return None
    sent_a, errors_a = fixture(a)
    sent_b, errors_b = fixture(b)
    if errors_a or errors_b:
        return dict(status='INVALID_COMPARISON', issues=errors_a+errors_b)
    starts = [json.loads((root / 'barrier.json').read_text())['start_monotonic_ns'] for root in (a, b)]
    timing = [abs((x['sample_ns']-starts[0])-(y['sample_ns']-starts[1])) / 1e6
              for x, y in zip(sent_a, sent_b) if x['sent'] and y['sent']]
    joints = []
    for root in (a, b):
        arm = [row for row in rows(root / 'topics.jsonl') if row.get('topic') == '/joint_states'
               and row['monotonic_ns'] >= json.loads((root / 'barrier.json').read_text())['start_monotonic_ns']]
        last = arm[-1]['payload'] if arm else None
        joints.append({name: last['position'][last['name'].index(name)] for name in ARM} if last else {})
    joint_diff = max((abs(joints[0][n]-joints[1][n]) for n in ARM), default=None) if all(joints) else None
    same_hash = normalized_hash(sent_a) == normalized_hash(sent_b)
    same_boot = [next((x.get('boot_id') for x in rows(root / 'events.jsonl') if x.get('kind') == 'clock'), None)
                 for root in (a, b)]
    okay = bool(same_hash and same_boot[0] and same_boot[0] == same_boot[1] and
                len(timing) == 100 and max(timing) <= 5 and joint_diff is not None and joint_diff <= .02)
    return dict(status='PASS' if okay else 'INVALID_COMPARISON', same_fixture=same_hash,
                same_boot_id=same_boot[0] == same_boot[1], real_samples_compared=len(timing),
                max_source_index_time_difference_ms=max(timing, default=None),
                max_final_joint_difference_rad=joint_diff)


def main():
    schedule = list(csv.DictReader((ROOT / 'qualification_schedule.csv').open()))
    assert [(x['mode'], x['regime']) for x in schedule] == MODES
    verdicts = [inspect(mode, regime) for mode, regime in MODES]
    pair_result = pair('docker_b0_full_cp11d3setup01', 'docker_shim_full_cp11d3setup01')
    qualified = all(x['status'] == 'MEASUREMENT_QUALIFIED' for x in verdicts)
    result = dict(status='D3_SETUP_COMPLETE' if qualified and pair_result and pair_result['status'] == 'PASS'
                  else 'D3_FORMAL_BLOCKED', cells=verdicts, b0_shim_equivalence=pair_result,
                  formal_trials='NOT_STARTED', policy_verdict='NOT_SCORED')
    (ROOT / 'analysis/d3_qualification_summary.json').write_text(json.dumps(result, indent=2, sort_keys=True)+'\n')
    print(json.dumps({'status': result['status'], 'cells': [(x['trial'], x['status'], x.get('issues', []))
                                                      for x in verdicts]}, sort_keys=True))


if __name__ == '__main__':
    main()
