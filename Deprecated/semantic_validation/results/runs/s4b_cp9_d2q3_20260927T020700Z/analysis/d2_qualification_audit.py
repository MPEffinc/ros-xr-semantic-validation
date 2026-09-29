#!/usr/bin/env python3
"""Prospectively frozen D2 setup/evidence audit; not a formal result scorer."""
import argparse
import csv
import importlib.util
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
Q4 = ROOT.parent / 's4b_cp6b_resource_q4_20260923T070559Z'
sys.path.insert(0, str(Q4 / 'analysis'))
from q4_measurement_audit import audit as measurement_audit  # noqa: E402
from q3_measurement_audit import rows, source_origin  # noqa: E402
sys.path.insert(0, str(ROOT / 'inputs'))
from d1_contract import payload_hash  # noqa: E402

PAIR_PATH = ROOT.parent / 's4b_cp2_qualification_20260923T003626Z/analysis/pair_audit.py'
spec = importlib.util.spec_from_file_location('fixed_pair_audit', PAIR_PATH)
pair = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pair)
pair.ROOT, pair.RAW = ROOT, ROOT / 'raw'
ARM = ('shoulder_pan_joint', 'shoulder_lift_joint', 'elbow_joint',
       'wrist_1_joint', 'wrist_2_joint', 'wrist_3_joint')


def normalized_source(root):
    sent = rows(root / 'sent.jsonl')
    problems = []
    if len(sent) != 120 or [r.get('index') for r in sent] != list(range(120)):
        problems.append('PLANNED_SOURCE_INDEX_COVERAGE')
    if len(sent) != 120:
        return sent, problems
    for row in sent:
        idx = row['index']
        wire = json.loads(row['wire'])
        hand = wire['right_hand']
        meta = wire['_qualification']
        expect_phase = ('idle' if idx < 20 else 'reference' if idx < 36 else
                        'active' if idx < 56 else 'fault_window' if idx < 76 else 'tail')
        if (row['phase'] != expect_phase or row['scheduled_ns'] != rows(root / 'barrier.json')[0]['start_monotonic_ns'] + idx * 50_000_000):
            problems.append(f'SCHEDULE_OR_PHASE_{idx}')
        if (hand['isTracked'] != (not 56 <= idx < 76) or
                hand['pos'] != {'x': .35 if 36 <= idx < 76 else .2, 'y': .2, 'z': .3} or
                wire['controls']['teleop_enable'] != (20 <= idx < 76) or
                meta.get('sample_id') != f'docker:{idx}' or meta.get('generation_id') != 1 or
                meta.get('native_state', {}).get('isTracked') != hand['isTracked'] or
                meta.get('phase') != expect_phase or
                meta.get('source_timestamp_ns') != row['sample_ns']):
            problems.append(f'FIXTURE_{idx}')
    return sent, problems


def monitor_integrity(root, regime):
    lineage, props = rows(root / 'lineage.jsonl'), rows(root / 'property.jsonl')
    file = 'monitor_full_status.jsonl' if regime == 'full' else 'monitor_native_status.jsonl'
    status = [r for r in rows(root / file) if r.get('status') == 'event']
    pub_stage = 'receiver_envelope' if regime == 'full' else 'receiver_native_monitor_input'
    pubs = [r for r in lineage if r.get('stage') == pub_stage]
    outputs = [r for r in lineage if r.get('kind') == 'monitor_output_received'
               and r.get('regime') == regime]
    issues, invalid_ids, active_ids, functional_flags = [], set(), set(), []
    if regime == 'full':
        pub_by_id = {r['monitor_event_id']: r for r in pubs}
        output_by_id = defaultdict(list)
        status_by_id = defaultdict(list)
        for r in outputs:
            output_by_id[r['monitor_event_id']].append(r)
        for r in status:
            status_by_id[json.loads(r['event']['data'])['envelope_monotonic_ns']].append(r)
        if len(pub_by_id) != len(pubs):
            issues.append('DUPLICATE_MONITOR_EVENT_ID')
        if set(pub_by_id) != {p['monitor_event_id'] for p in props}:
            issues.append('PUBLICATION_PROPERTY_ID_SET_MISMATCH')
        if set(pub_by_id) != set(status_by_id):
            issues.append('PUBLICATION_STATUS_ID_SET_MISMATCH')
        for p in props:
            eid = p['monitor_event_id']
            pub, stat, got = pub_by_id.get(eid), status_by_id[eid], output_by_id[eid]
            if pub is None or pub['original_payload_sha256'] != p['payload_sha256'] or len(stat) != 1:
                issues.append(f'UNBOUND_PROPERTY_OR_STATUS_{eid}')
                continue
            source = pub.get('selected_origin') or {}
            if source.get('sample_id') != p.get('sample_id'):
                issues.append(f'PARENT_MISMATCH_{eid}')
            if p['safe']:
                if stat[0].get('decision') != 'forwarded' or len(got) != 1:
                    issues.append(f'SAFE_OUTPUT_RECEIPT_MISSING_{eid}')
            elif stat[0].get('decision') != 'blocked' or got:
                issues.append(f'BLOCK_VERDICT_OR_LEAK_{eid}')
            if source.get('phase') == 'fault_window':
                invalid_ids.add(source.get('sample_id'))
            if source.get('phase') == 'active':
                active_ids.add(source.get('sample_id'))
                if p['safe'] is not True:
                    functional_flags.append(f'VALID_ACTIVE_REJECTED_{eid}')
    else:
        groups = []
        for data, key in ((pubs, lambda r: r['payload_sha256']),
                          (props, lambda r: r['payload_sha256']),
                          (status, lambda r: payload_hash(r['payload'])),
                          (outputs, lambda r: r['payload_sha256'])):
            group = defaultdict(list)
            for r in data:
                group[key(r)].append(r)
            groups.append(group)
        for digest, publication in groups[0].items():
            pr, pt, st, out = [g.get(digest, []) for g in groups]
            if len(pr) != 1 or len(pt) != 1 or len(st) != 1:
                issues.append(f'UNBOUND_NATIVE_PROPERTY_{digest}')
                continue
            origin = source_origin(pr[0].get('parent'))
            if pt[0]['safe']:
                if st[0].get('decision') != 'forwarded' or len(out) != 1:
                    issues.append(f'SAFE_NATIVE_RECEIPT_MISSING_{digest}')
            elif st[0].get('decision') != 'blocked' or out:
                issues.append(f'NATIVE_BLOCK_VERDICT_OR_LEAK_{digest}')
            if origin and origin.get('phase') == 'fault_window':
                invalid_ids.add(origin['sample_id'])
            if origin and origin.get('phase') == 'active':
                active_ids.add(origin['sample_id'])
                if pt[0]['safe'] is not True:
                    functional_flags.append(f'VALID_ACTIVE_REJECTED_{digest}')
        if set(groups[0]) != set(groups[1]) or set(groups[0]) != set(groups[2]):
            issues.append('NATIVE_PUBLICATION_PROPERTY_STATUS_SET_MISMATCH')
    expected = {f'docker:{i}' for i in range(56, 76)}
    if invalid_ids != expected:
        issues.append('INVALID_SOURCE_ID_COVERAGE')
    if active_ids != {f'docker:{i}' for i in range(36, 56)}:
        issues.append('ELIGIBLE_ACTIVE_SOURCE_ID_COVERAGE')
    return dict(property_rows=len(props), status_rows=len(status), input_publications=len(pubs),
                output_receipts=len(outputs), invalid_source_ids=sorted(invalid_ids),
                active_source_ids=sorted(active_ids), functional_flags=functional_flags,
                issues=issues[:100], issue_count=len(issues),
                monitor_internal_publish_time='UNKNOWN')


def consequence(root, fault_ns):
    topics = rows(root / 'topics.jsonl')
    joints = []
    for r in topics:
        if r.get('topic') != '/joint_states':
            continue
        p = r['payload']
        if not all(n in p['name'] for n in ARM):
            continue
        pos = [p['position'][p['name'].index(n)] for n in ARM]
        vel = [p['velocity'][p['name'].index(n)] for n in ARM]
        if all(math.isfinite(v) for v in pos + vel):
            joints.append((r['monotonic_ns'], pos, vel))
    before = [max(abs(v) for v in vel) for t, _, vel in joints
              if fault_ns - 100_000_000 <= t < fault_ns]
    controls = [r for r in topics if r.get('topic') == '/joint_group_velocity_controller/commands']
    nonzero = [r['monotonic_ns'] for r in controls
               if any(abs(v) > 1e-6 for v in r['payload']['data'])]
    after = [t for t in nonzero if t >= fault_ns]
    settled = None
    for t, pos, vel in joints:
        if t < fault_ns:
            continue
        window = [(q, x, w) for q, x, w in joints if t <= q <= t + 520_000_000]
        if (len(window) >= 5 and window[-1][0] - t >= 500_000_000 and
                all(max(abs(v) for v in w) < .001 for _, _, w in window) and
                all(abs(x[i] - pos[i]) < .0001 for _, x, _ in window for i in range(6))):
            settled = t
            break
    return dict(joint_samples=len(joints), controller_samples=len(controls),
                moving_before_fault=max(before, default=None),
                nonzero_controller_before_fault=sum(fault_ns - 100_000_000 <= t < fault_ns
                                                    for t in nonzero),
                last_post_fault_nonzero_ns=max(after, default=None),
                settled_ns=settled, settled_after_fault_ms=None if settled is None else
                (settled - fault_ns) / 1e6)


def local_detection(root, baseline, regime):
    if baseline == 'b1':
        found = [r for r in rows(root / 'gate_verdict.jsonl')
                 if r.get('index') == 56 and r.get('allowed') is False]
        return found[0]['decision_monotonic_ns'] if found else None
    if baseline in ('b2', 'b2c'):
        props = rows(root / 'property.jsonl')
        if regime == 'full':
            found = [p for p in props if p.get('sample_id') == 'docker:56'
                     and p.get('safe') is False]
        else:
            digests = {r['payload_sha256'] for r in rows(root / 'lineage.jsonl')
                       if r.get('stage') == 'receiver_native_monitor_input'
                       and (source_origin(r.get('parent')) or {}).get('sample_id') == 'docker:56'}
            found = [p for p in props if p.get('payload_sha256') in digests
                     and p.get('safe') is False]
        return min((p['monotonic_ns'] for p in found), default=None)
    if baseline == 'b3':
        found = [r for r in rows(root / 'lineage.jsonl')
                 if r.get('kind') == 'b3_mapper_verdict'
                 and (source_origin(r.get('source_origin')) or {}).get('sample_id') == 'docker:56'
                 and r.get('verdict') is False]
        return min((r['monotonic_ns'] for r in found), default=None)
    return None  # B0 original has no installed policy-decision timestamp.


def callback_fault_classification(root, callback, decision_ns):
    if callback is None or decision_ns is None:
        return dict(status='UNKNOWN')
    publications = {r['command_id']: r for r in rows(root / 'lineage.jsonl')
                    if r.get('stage') == 'bridge_servo_input' and r.get('kind') == 'publish'}
    forbidden, earlier_cached = [], []
    for edge in callback['joined']:
        if edge['callback_entry_ns'] < decision_ns:
            continue
        pub = publications.get(edge['command_id'])
        if pub is None:
            continue
        twist = pub['payload']['twist']
        nonzero = any(abs(twist[k][axis]) > 1e-6 for k in ('linear', 'angular')
                      for axis in 'xyz')
        if not nonzero:
            continue
        index = int(edge['sample_id'].split(':')[-1])
        record = dict(sample_id=edge['sample_id'], command_id=edge['command_id'],
                      callback_entry_ns=edge['callback_entry_ns'], source_ns=edge['source_ns'])
        (forbidden if 56 <= index < 76 else earlier_cached).append(record)
    return dict(status='EXACT_CALLBACK_BOUNDARY',
                forbidden_fault_source_nonzero_callbacks=forbidden,
                earlier_source_nonzero_callbacks_after_detection=earlier_cached,
                unjoined_publications=callback['missing'])


def inspect(cell):
    name = f'docker_{cell["baseline"]}_{cell["regime"]}_{cell["attempt_id"]}'
    root = ROOT / 'raw' / name
    if not root.exists():
        return dict(cell=cell['cell'], trial=name, status='NOT_RUN')
    reasons, functional_flags = [], []
    exit_data = json.loads((root / 'exit.json').read_text()) if (root / 'exit.json').exists() else {}
    if exit_data.get('launch_exit') != 0:
        reasons.append('LAUNCH_NOT_SUCCESSFUL')
    if not (root / 'barrier.json').exists():
        return dict(cell=cell['cell'], trial=name, status='BLOCKED_MEASUREMENT',
                    reasons=reasons + ['NO_BARRIER'])
    sent, fixture_issues = normalized_source(root)
    reasons += fixture_issues
    events = rows(root / 'events.jsonl')
    ack = next((x for x in events if x.get('kind') == 'readiness_ack'), None)
    if not ack or len({x.get('boot_id') for x in ack.get('participant_clocks', {}).values()}) != 1:
        reasons.append('FULL_START_OR_CLOCK_ACK_MISSING')
    if len(sent) != 120 or not ack:
        return dict(cell=cell['cell'], trial=name, status='BLOCKED_MEASUREMENT', reasons=reasons)
    fault_ns = sent[56]['sample_ns']
    measure = measurement_audit(root)
    resources = measure['resources']
    if resources['status'] != 'COMPLETE_CAPTURE' or resources['q4_sender_lifecycle']['status'] != 'PASS':
        reasons.append('RESOURCE_CAPTURE_INCOMPLETE')
    consequence_result = consequence(root, fault_ns)
    if not consequence_result['moving_before_fault'] or consequence_result['moving_before_fault'] <= .001:
        reasons.append('NO_ACTUAL_MOVEMENT_AT_FAULT')
    if not consequence_result['nonzero_controller_before_fault']:
        reasons.append('NO_PREFAULT_CONTROLLER_OUTPUT')
    callback = measure['callback'] if cell['baseline'] != 'b0' else None
    if callback and (callback['missing'] or
                     callback['exact_joins'] != callback['source_parent_publications']):
        reasons.append('SOURCE_TO_SERVO_CALLBACK_INCOMPLETE')
    if callback and {f'docker:{i}' for i in range(36, 56)} - {
            r['sample_id'] for r in callback['joined']}:
        reasons.append('ELIGIBLE_ACTIVE_CALLBACK_COVERAGE')
    detection_ns = local_detection(root, cell['baseline'], cell['regime'])
    if cell['baseline'] in ('b1', 'b2', 'b2c', 'b3') and detection_ns is None:
        reasons.append('LOCAL_INVALID_DETECTION_NOT_OBSERVED')
    fault_callbacks = callback_fault_classification(root, callback, detection_ns)
    monitor = monitor_integrity(root, cell['regime']) if cell['baseline'] in ('b2', 'b2c') else None
    if monitor and monitor['issues']:
        reasons.append('B2_EVENT_ASSOCIATION_INCOMPLETE')
    if monitor:
        functional_flags.extend(monitor['functional_flags'])
    if cell['baseline'] == 'b1':
        verdicts = {r['index']: r for r in rows(root / 'gate_verdict.jsonl')}
        if any(i not in verdicts or verdicts[i]['allowed'] is not True
               for i in range(36, 56)):
            functional_flags.append('B1_VALID_ACTIVE_FALSE_REJECTION')
    if cell['baseline'] in ('b1', 'b2c', 'b3') and not (root / 'stop_adapter.ready').exists():
        reasons.append('GENERIC_STOP_ADAPTER_NOT_READY')
    stop = rows(root / 'stop_adapter.jsonl')
    return dict(cell=cell['cell'], trial=name,
                status=('BLOCKED_MEASUREMENT' if reasons else
                        'FAIL_POLICY_CONTROL' if functional_flags else 'MEASUREMENT_QUALIFIED'),
                reasons=reasons, functional_flags=functional_flags,
                setup_retry_eligible=bool(reasons) and not functional_flags,
                fault_sample_id='docker:56',
                fault_sample_ns=fault_ns, callback_exact_joins=None if callback is None else
                callback['exact_joins'], local_detection_ns=detection_ns,
                fault_callbacks=fault_callbacks,
                monitor=monitor, consequence=consequence_result,
                stop_events=[x for x in stop if x.get('kind') in ('stop_request','stop_reply','controller_zero')],
                resource_status=resources['status'],
                policy_outcome='NOT_SCORED_BY_SETUP_AUDIT')


def main():
    with (ROOT / 'qualification_schedule.csv').open() as stream:
        schedule = list(csv.DictReader(stream))
    assert len(schedule) == 10 and [r['order'] for r in schedule] == list(map(str, range(1, 11)))
    result = [inspect(row) for row in schedule]
    b0_name, shim_name = (f'docker_{mode}_full_cp7d2setup01' for mode in ('b0', 'shim'))
    pair_result = pair.summarize(b0_name, shim_name, 120) if (
        (ROOT / 'raw' / b0_name).exists() and (ROOT / 'raw' / shim_name).exists()) else None
    output = dict(status='D2_SETUP_COMPLETE' if all(r['status'] == 'MEASUREMENT_QUALIFIED'
                                                 for r in result) and pair_result and
                  pair_result['status'] == 'PASS' else 'D2_FORMAL_BLOCKED',
                  setup_cells=result, b0_shim_equivalence=pair_result,
                  policy_verdict='NOT_SCORED_BY_SETUP_AUDIT', formal_trials='NOT_STARTED',
                  source_to_specific_joint_parent='UNKNOWN')
    (ROOT / 'analysis' / 'd2_qualification_summary.json').write_text(
        json.dumps(output, indent=2, sort_keys=True) + '\n')
    print(json.dumps({'status': output['status'],
                      'cells': [(x['cell'], x['status'], x.get('reasons', [])) for x in result]},
                     sort_keys=True))


if __name__ == '__main__':
    main()
