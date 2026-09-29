#!/usr/bin/env python3
"""Prospective C-MON Q1 setup audit; NOT a monitor-failure policy score.

A missing oracle property/status record CAUSED by the injected fault is part of
the fault, not a recorder failure. This audit therefore requires:
  * proof of the injected fault (absence / owned-healthy-then-killed / stopped /
    gate marker) from cmon_fault.jsonl and the official monitor's own records;
  * complete official association for every original event BEFORE the fault
    (ABSENT: every event officially `unknown`-forwarded with guarded receipt and
    no oracle property record at all);
  * valid source input continuing through the fault (all 120 real samples
    transmitted and received by the original receiver);
  * the unchanged C-ID Q1 checks otherwise (ACK/clock, ticks, CPU/RSS, exact
    source->Servo callbacks, post-capture producer quiesce and Servo drain).
"""
import csv
import json
import os
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
RAW = ROOT / 'raw'
sys.path.insert(0, str(HERE))
import cid_setup_audit as cid  # noqa: E402
d4 = cid.d4
rows = cid.rows
ORACLE_FAULTS = ('ORACLE_ABSENT', 'ORACLE_DISCONNECT', 'ORACLE_NONRESPONSIVE')


def fixture(root):
    sent = rows(root / 'sent.jsonl')
    errors = []
    if len(sent) != 120 or [x.get('index') for x in sent] != list(range(120)):
        return sent, ['PLANNED_120_SLOTS_INCOMPLETE']
    for item in sent:
        payload = json.loads(item['wire'])
        meta = payload['_qualification']
        if (meta.get('sample_id') != f"docker:{item['index']}" or item.get('sent') is not True or
                cid.check(meta, cid.projection_from_wire(payload))[1] != 'BOUND' or
                item.get('cid_kind') != 'NONE'):
            errors.append(f"CMON_VALID_SOURCE_{item['index']}")
    return sent, errors


def fault_proof(root, fault, regime):
    ev = rows(root / 'cmon_fault.jsonl')
    kinds = {r['kind']: r for r in ev}
    issues = []
    status_path = root / f'monitor_{regime}_status.jsonl'
    statuses = rows(status_path)
    t_fault = None
    if fault == 'ORACLE_ABSENT':
        armed, proof = kinds.get('armed'), kinds.get('absence_proof')
        text = ''.join(f.read_text(errors='replace') for f in (root / 'stderr' / 'monitor.log', root / 'stdout' / 'monitor.log')
                       if f.exists())
        if not (armed and proof and armed['oracle_pid_file'] is False and armed['oracle_port_refuses'] is True
                and proof['oracle_pid_file'] is False and proof['oracle_port_refuses'] is True):
            issues.append('ORACLE_ABSENCE_NOT_PROVEN')
        if 'could not connect to oracle' not in text:
            issues.append('MONITOR_DID_NOT_RECORD_ORACLE_UNAVAILABLE')
        if any(r.get('event_kind') is not None for r in rows(root / 'property.jsonl')):
            issues.append('ORACLE_PROPERTY_RECORD_PRESENT_DESPITE_ABSENCE')
        t_fault = json.loads((root / 'barrier.json').read_text())['start_monotonic_ns'] if (root / 'barrier.json').exists() else None
    elif fault in ('ORACLE_DISCONNECT', 'ORACLE_NONRESPONSIVE'):
        health, inj = kinds.get('pre_fault_health'), kinds.get('injected')
        if not (health and health['owned'] and health['healthy']):
            issues.append('ORACLE_NOT_PROVEN_OWNED_AND_HEALTHY_BEFORE_FAULT')
        want = ('SIGKILL', False, None) if fault == 'ORACLE_DISCONNECT' else ('SIGSTOP', True, 'T')
        if not inj or (inj['signal'], inj['process_exists_after_50ms'], inj['process_state_after_50ms']) != want:
            issues.append('ORACLE_FAULT_NOT_PROVEN_INJECTED')
        t_fault = inj['injected_monotonic_ns'] if inj else None
        if not any(s.get('status') == 'oracle_error' for s in statuses):
            issues.append('OFFICIAL_MONITOR_RECORDED_NO_ORACLE_ERROR')
    else:
        inj = kinds.get('injected')
        marker = 'b1_gate_failed' if fault == 'B1_GATE_FAIL' else 'b3_check_failed'
        if not inj or inj.get('marker') != marker or not (root / marker).exists():
            issues.append('GATE_FAULT_NOT_PROVEN_INJECTED')
        t_fault = inj['injected_monotonic_ns'] if inj else None
    return t_fault, issues


def pre_fault_association(root, regime, t_fault, fault):
    """Every original monitor-input publication before the fault has status (+property unless ABSENT) + receipt."""
    lineage = rows(root / 'lineage.jsonl')
    stage = 'receiver_envelope' if regime == 'full' else 'receiver_native_monitor_input'
    key = 'monitor_event_id' if regime == 'full' else 'payload_sha256'
    pubs = [r for r in lineage if r.get('kind') == 'publish' and r.get('stage') == stage
            and (fault == 'ORACLE_ABSENT' or r['monotonic_ns'] < t_fault - 20_000_000)]
    props = defaultdict(list)
    for p in rows(root / 'property.jsonl'):
        if p.get('event_kind') != 'tick':
            props[p.get(key)].append(p)
    stat = defaultdict(list)
    for s in rows(root / f'monitor_{regime}_status.jsonl'):
        if s.get('status') == 'event' and s.get('interface') != '/s4b/d3/tick':
            k = (json.loads(s['event']['data'])['envelope_monotonic_ns'] if regime == 'full'
                 else d4.source_monitor_audit.__globals__['canonical_hash'](s['payload']))
            stat[k].append(s)
    recv = defaultdict(int)
    for r in lineage:
        if r.get('kind') == 'monitor_output_received' and r.get('regime') == regime:
            recv[r.get(key)] += 1
    issues = []
    for p in pubs:
        k = p.get(key)
        st = stat.get(k, [])
        if len(st) != 1 or recv[k] != (1 if st and st[0].get('decision') == 'forwarded' else 0):
            issues.append('PRE_FAULT_STATUS_OR_RECEIPT')
            continue
        if fault == 'ORACLE_ABSENT':
            if st[0].get('verdict_raw') != 'unknown' or props.get(k):
                issues.append('ABSENT_EVENT_NOT_UNKNOWN_OR_HAS_PROPERTY')
        elif len(props.get(k, [])) != 1:
            issues.append('PRE_FAULT_PROPERTY')
    return dict(pre_fault_publications=len(pubs), issue_count=len(issues), issues=sorted(set(issues)))


def killed_oracle_resources(root, res):
    """ORACLE_DISCONNECT: the injected SIGKILL removes the oracle, so its resource
    target is necessarily MISSING after the fault. Every expected label must still be
    OBSERVED in every capture sample, except the oracle strictly after the proven
    injection time; the oracle must be OBSERVED in every capture sample before it."""
    inj = next((r for r in rows(root / 'cmon_fault.jsonl') if r.get('kind') == 'injected'), None)
    events = rows(root / 'events.jsonl')
    barrier = next((x['start_monotonic_ns'] for x in events if x.get('kind') == 'barrier_release'), None)
    end = next((x['monotonic_ns'] for x in events if x.get('kind') == 'capture_end'), None)
    if inj is None or barrier is None or end is None or res.get('absent_labels'):
        return res
    capture = [x for x in rows(root / 'resource_samples.jsonl') if x.get('kind') == 'sample'
               and barrier <= x['monotonic_ns'] <= end]
    t = inj['injected_monotonic_ns']
    before = [x for x in capture if x['monotonic_ns'] < t]
    ok = len(capture) >= 2 and before and all(
        x['targets'].get(label, {}).get('status') == 'OBSERVED'
        for x in capture for label in res['expected_labels']
        if not (label == 'oracle' and x['monotonic_ns'] > t))
    ok = ok and all(x['targets'].get('oracle', {}).get('status') == 'OBSERVED' for x in before)
    return dict(res, status='COMPLETE_CAPTURE' if ok else res['status'],
                cmon_oracle_missing_after_injected_kill_exempt=bool(ok),
                cmon_oracle_capture_samples_before_kill=len(before))


def inspect(root, baseline, regime, fault, expect_motion):
    issues = []
    exit_record = json.loads((root / 'exit.json').read_text()) if (root / 'exit.json').exists() else {}
    if exit_record.get('launch_exit') != 0:
        issues.append('LAUNCH_NONZERO')
    if not (root / 'barrier.json').exists():
        return dict(trial=root.name, status='BLOCKED_MEASUREMENT', issues=issues + ['NO_START_BARRIER'])
    sent, fx_issues = fixture(root)
    issues += fx_issues
    events = rows(root / 'events.jsonl')
    ack = next((x for x in events if x.get('kind') == 'readiness_ack'), None)
    if not ack or len({x.get('boot_id') for x in ack.get('participant_clocks', {}).values()}) != 1:
        issues.append('FULL_ACK_OR_COMMON_CLOCK_MISSING')
    ticks = rows(root / 'd3_ticks.jsonl')
    if len(ticks) != 300 or any(x.get('source_sample_id') is not None for x in ticks):
        issues.append('COMMON_TICK_INCOMPLETE_OR_FABRICATED_SOURCE')
    res, life = d4.resources(root), d4.lifecycle_trial(root)
    if fault == 'ORACLE_DISCONNECT' and res['status'] != 'COMPLETE_CAPTURE':
        res = killed_oracle_resources(root, res)
    if res['status'] != 'COMPLETE_CAPTURE' or life['status'] != 'PASS':
        issues.append('RESOURCE_CAPTURE_INCOMPLETE')
    callback = None if baseline == 'b0' else cid.callback_join(root)
    if callback and (callback['missing_count'] or callback['exact_joins'] != callback['source_parent_publications']):
        issues.append('EXACT_SOURCE_TO_SERVO_CALLBACK_INCOMPLETE')
    mv = d4.motion(root)
    if expect_motion and (mv['max_excursion_rad'] is None or mv['max_excursion_rad'] <= .01):
        issues.append('POSITIVE_CONTROL_MOTION_ABSENT')
    t_fault, proof_issues = (None, []) if fault == 'NONE' else fault_proof(root, fault, regime)
    issues += proof_issues
    assoc = None
    if baseline in ('b2', 'b2c'):
        if fault in ORACLE_FAULTS:
            assoc = pre_fault_association(root, regime, t_fault, fault)
            if assoc['issues']:
                issues.append('PRE_FAULT_OFFICIAL_ASSOCIATION_INCOMPLETE')
            if not any(e.get('kind') == 'cmon_monitor_drain_not_required_intended_oracle_fault' for e in events):
                issues.append('CMON_PROBE_FAULT_MODE_NOT_RECORDED')
        saved = os.environ.get('CMON_FAULT')
        if fault == 'ORACLE_ABSENT':
            os.environ['CMON_FAULT'] = 'ORACLE_ABSENT'
        try:
            cal = d4.calibration_audit(root, regime)
        finally:
            if saved is None:
                os.environ.pop('CMON_FAULT', None)
            else:
                os.environ['CMON_FAULT'] = saved
        cal_issues = list(cal['issues'])
        if fault == 'ORACLE_ABSENT' and cal_issues == ['CALIBRATION_CLOCK_ORDER_INVALID'] and cal['monotonic_chain']:
            chain = [v for i, v in enumerate(cal['monotonic_chain']) if i != 2]   # no oracle decision exists
            if all(a <= b for a, b in zip(chain, chain[1:])):
                cal_issues = []
        if cal_issues:
            issues.append('CALIBRATION_SOURCE_PATH_OR_BARRIER_INCOMPLETE')
    post = d4.lifecycle_audit(root, 'b2x' if fault in ORACLE_FAULTS else ('b2' if baseline == 'b2c' else baseline), 300)
    if post['issues']:
        issues.append('POST_CAPTURE_PRODUCER_OR_SERVO_DRAIN_INCOMPLETE')
    if baseline in ('b1', 'b3', 'b2c') and not (root / 'stop_adapter.ready').exists():
        issues.append('ORDINARY_STOP_ADAPTER_NOT_READY')
    if baseline != 'b0':
        cov = json.loads((root / 'receiver_coverage.json').read_text()) if (root / 'receiver_coverage.json').exists() else None
        if cov is None or cov.get('ok') is not True or cov.get('expected_count') != 120:
            issues.append('SOURCE_INPUT_NOT_CONTINUOUS_THROUGH_FAULT')
    return dict(trial=root.name, status='MEASUREMENT_QUALIFIED' if not issues else 'BLOCKED_MEASUREMENT',
                issues=issues, fault=fault, fault_injected_monotonic_ns=t_fault, pre_fault_association=assoc,
                callback_exact_joins=None if callback is None else callback['exact_joins'], motion=mv,
                resources=res['status'], lifecycle=life['status'], policy_verdict='NOT_SCORED_BY_SETUP_AUDIT')


def pair(a, b):
    sa, ea = fixture(a)
    sb, eb = fixture(b)
    if ea or eb:
        return dict(status='INVALID_COMPARISON', issues=(ea + eb)[:10])
    starts = [json.loads((r / 'barrier.json').read_text())['start_monotonic_ns'] for r in (a, b)]
    timing = max(abs((x['sample_ns'] - starts[0]) - (y['sample_ns'] - starts[1])) / 1e6 for x, y in zip(sa, sb))
    fa, fb = d4.motion(a).get('final_positions_rad'), d4.motion(b).get('final_positions_rad')
    diff = max(abs(x - y) for x, y in zip(fa, fb)) if fa and fb else None
    ok = timing <= 5 and diff is not None and diff <= .02
    return dict(status='PASS' if ok else 'INVALID_COMPARISON', max_source_index_time_difference_ms=timing,
                max_final_joint_difference_rad=diff)


def main():
    schedule = list(csv.DictReader((ROOT / 'qualification_schedule.csv').open()))
    cells = []
    for row in schedule:
        attempts = [RAW / (row['trial_id'] + s) for s in ('', '_setup02', '_setup03') if (RAW / (row['trial_id'] + s)).exists()]
        chosen = next((r for r in attempts if (r / 'barrier.json').exists()), None)
        out = (inspect(chosen, row['baseline'], row['regime'], row['fault'], row['expect_motion'] == '1') if chosen
               else dict(trial=row['trial_id'], status='BLOCKED_MEASUREMENT' if attempts else 'NOT_RUN'))
        out['attempts'] = [r.name for r in attempts]
        cells.append(out)
    b0 = next((r for r in schedule if r['baseline'] == 'b0'), None)
    shim = next((r for r in schedule if r['baseline'] == 'shim'), None)
    pr = (pair(RAW / b0['trial_id'], RAW / shim['trial_id']) if b0 and shim and
          (RAW / b0['trial_id'] / 'barrier.json').exists() and (RAW / shim['trial_id'] / 'barrier.json').exists()
          else dict(status='NOT_RUN'))
    ok = all(c['status'] == 'MEASUREMENT_QUALIFIED' for c in cells) and pr['status'] == 'PASS'
    out = dict(status='CMON_SETUP_COMPLETE' if ok else 'CMON_SETUP_INCOMPLETE_OR_BLOCKED', cells=cells,
               b0_shim_equivalence=pr, policy_verdict='NOT_SCORED')
    (HERE / 'cmon_setup_summary.json').write_text(json.dumps(out, indent=2, sort_keys=True) + '\n')
    print(out['status'])
    for c in cells:
        print(' ', c['trial'], c['status'], c.get('issues', []), round((c.get('motion') or {}).get('max_excursion_rad') or 0, 4))
    print(' pair', pr.get('status'), pr.get('max_source_index_time_difference_ms'), pr.get('max_final_joint_difference_rad'))


if __name__ == '__main__':
    main()
