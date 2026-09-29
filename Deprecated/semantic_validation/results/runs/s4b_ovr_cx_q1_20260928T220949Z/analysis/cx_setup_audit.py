#!/usr/bin/env python3
"""Prospective OpenVR C-ID / C-MON (C-X) setup audit; NOT a policy score.

Reuses the frozen OpenVR Q1 checks (ovr_setup_audit) and adds, for C-MON faults,
the Docker C-MON Q3 principle that a record missing BECAUSE of the injected fault
is part of the fault, not a recorder failure:
  * fault proof from cmon_fault.jsonl (absence / owned-healthy-then-killed or
    stopped / gate marker) and the official monitor's own records;
  * ORACLE_DISCONNECT: the killed oracle's resource target may be MISSING only
    strictly after the proven kill (every other label OBSERVED throughout);
  * B2 association: every envelope published before the fault (ABSENT: every
    envelope) has exactly one official status, a property row (none under ABSENT)
    and a matching receipt; after the fault, envelopes may lack a property row;
    envelopes lacking an official status (the Q1-observed official Jazzy monitor
    stall) are recorded as a B2 outcome, not invalidity (OpenVR formal rule).
C-ID cells: the bound fixture with exactly one injected poll-150 fault.
"""
import csv
import json
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
RAW = ROOT / 'raw'
Q1 = ROOT.parent / 's4b_ovr_q1_20260928T184158Z'
sys.path.insert(0, str(Q1 / 'analysis'))
import ovr_setup_audit as q1  # noqa: E402  frozen OpenVR Q1 checks

rows = q1.rows
ORACLE_FAULTS = ('ORACLE_ABSENT', 'ORACLE_DISCONNECT', 'ORACLE_NONRESPONSIVE')


def fault_proof(root, fault):
    ev = {r['kind']: r for r in rows(root / 'cmon_fault.jsonl')}
    statuses = rows(root / 'monitor_full_status.jsonl')
    issues, t = [], None
    if fault == 'ORACLE_ABSENT':
        a, p = ev.get('armed'), ev.get('absence_proof')
        log = ''.join((root / d / 'monitor.log').read_text(errors='replace') for d in ('stderr', 'stdout') if (root / d / 'monitor.log').exists())
        if not (a and p and a['oracle_pid_file'] is False and a['oracle_port_refuses'] is True and
                p['oracle_pid_file'] is False and p['oracle_port_refuses'] is True):
            issues.append('ORACLE_ABSENCE_NOT_PROVEN')
        if 'could not connect to oracle' not in log:
            issues.append('MONITOR_DID_NOT_RECORD_ORACLE_UNAVAILABLE')
        if rows(root / 'property.jsonl'):
            issues.append('ORACLE_PROPERTY_RECORD_PRESENT_DESPITE_ABSENCE')
        t = json.loads((root / 'barrier.json').read_text())['start_monotonic_ns']
    elif fault in ('ORACLE_DISCONNECT', 'ORACLE_NONRESPONSIVE'):
        h, i = ev.get('pre_fault_health'), ev.get('injected')
        if not (h and h['owned'] and h['healthy']):
            issues.append('ORACLE_NOT_PROVEN_OWNED_AND_HEALTHY_BEFORE_FAULT')
        want = ('SIGKILL', False, None) if fault == 'ORACLE_DISCONNECT' else ('SIGSTOP', True, 'T')
        if not i or (i['signal'], i['process_exists_after_50ms'], i['process_state_after_50ms']) != want:
            issues.append('ORACLE_FAULT_NOT_PROVEN_INJECTED')
        t = i['injected_monotonic_ns'] if i else None
        if not any(s.get('status') == 'oracle_error' for s in statuses):
            issues.append('OFFICIAL_MONITOR_RECORDED_NO_ORACLE_ERROR')
    else:
        i = ev.get('injected')
        marker = 'b1_gate_failed' if fault == 'B1_GATE_FAIL' else 'b3_check_failed'
        if not i or i.get('marker') != marker or not (root / marker).exists():
            issues.append('GATE_FAULT_NOT_PROVEN_INJECTED')
        t = i['injected_monotonic_ns'] if i else None
    return t, issues


def b2_association(root, fault, t_fault):
    lin = rows(root / 'lineage.jsonl')
    env = [r for r in lin if r.get('stage') == 'production_envelope' and r.get('envelope_kind') != 'calibration']
    props = Counter(p.get('monitor_event_id') for p in rows(root / 'property.jsonl'))
    status = {}
    for s in rows(root / 'monitor_full_status.jsonl'):
        if s.get('status') == 'event':
            try:
                status[json.loads(s['event']['data'])['envelope_monotonic_ns']] = s
            except (KeyError, TypeError, ValueError):
                pass
    rec = Counter(r.get('monitor_event_id') for r in lin if r.get('kind') == 'monitor_output_received')
    issues, unprocessed = Counter(), 0
    for e in env:
        k = e['monitor_event_id']
        st = status.get(k)
        if st is None:
            unprocessed += 1
            continue
        pre = fault not in ORACLE_FAULTS or (t_fault is not None and e['monotonic_ns'] < t_fault - 20_000_000)
        if fault == 'ORACLE_ABSENT':
            if props[k] != 0 or st.get('verdict_raw') != 'unknown':
                issues['ABSENT_EVENT_NOT_UNKNOWN_OR_HAS_PROPERTY'] += 1
        elif pre and props[k] != 1:
            issues['PROPERTY_NOT_EXACTLY_ONE'] += 1
        if rec[k] != (1 if st.get('decision') == 'forwarded' else 0):
            issues['RECEIPT_MISMATCH'] += 1
    return dict(envelopes=len(env), unprocessed_by_official_monitor=unprocessed, issues=dict(issues))


def killed_oracle_resources(root, res, t_kill):
    ev, start, end = q1.capture(root)
    cap = [x for x in rows(root / 'resource_samples.jsonl') if x.get('kind') == 'sample' and start <= x['monotonic_ns'] <= end]
    before = [x for x in cap if x['monotonic_ns'] < t_kill]
    ok = len(cap) >= 2 and before and not res.get('absent_labels') and all(
        x['targets'].get(lab, {}).get('status') == 'OBSERVED' for x in cap for lab in res['expected_labels']
        if not (lab == 'oracle' and x['monotonic_ns'] > t_kill)) and all(
        x['targets'].get('oracle', {}).get('status') == 'OBSERVED' for x in before)
    return 'COMPLETE_CAPTURE' if ok else res['status']


def inspect(root, baseline, fault, expect_motion):
    out = q1.inspect(root, baseline, expect_motion)
    if out['status'] == 'BLOCKED_MEASUREMENT' and 'NO_START_BARRIER' in out.get('issues', []):
        return out
    issues = [i for i in out['issues'] if i not in ('B2_OFFICIAL_ASSOCIATION_INCOMPLETE', 'RESOURCE_CAPTURE_INCOMPLETE')]
    t_fault = None
    if fault != 'NONE':
        t_fault, fi = fault_proof(root, fault)
        issues += fi
    res = q1.resources(root)
    status = res['status']
    if status != 'COMPLETE_CAPTURE' and fault == 'ORACLE_DISCONNECT' and t_fault is not None:
        status = killed_oracle_resources(root, res, t_fault)
    if status != 'COMPLETE_CAPTURE':
        issues.append('RESOURCE_CAPTURE_INCOMPLETE')
    assoc = None
    if baseline.startswith('b2'):
        assoc = b2_association(root, fault, t_fault)
        if assoc['issues']:
            issues.append('B2_OFFICIAL_ASSOCIATION_INCOMPLETE')
    out.update(status='MEASUREMENT_QUALIFIED' if not issues else 'BLOCKED_MEASUREMENT', issues=issues,
               fault=fault, fault_injected_monotonic_ns=t_fault, cx_b2_association=assoc, resources=status)
    return out


def main():
    schedule = list(csv.DictReader((ROOT / 'qualification_schedule.csv').open()))
    cells = []
    for row in schedule:
        attempts = [RAW / (row['trial_id'] + s) for s in ('', '_setup02', '_setup03') if (RAW / (row['trial_id'] + s)).exists()]
        chosen = next((r for r in attempts if (r / 'barrier.json').exists()), None)
        out = (inspect(chosen, row['baseline'], row['fault'], row['expect_motion'] == '1') if chosen
               else dict(trial=row['trial_id'], status='BLOCKED_MEASUREMENT' if attempts else 'NOT_RUN'))
        out['attempts'] = [r.name for r in attempts]
        cells.append(out)
    b0 = next((r for r in schedule if r['baseline'] == 'b0'), None)
    shim = next((r for r in schedule if r['baseline'] == 'shim'), None)
    pr = (q1.pair(RAW / b0['trial_id'], RAW / shim['trial_id'])
          if b0 and shim and all((RAW / r['trial_id'] / 'barrier.json').exists() for r in (b0, shim)) else dict(status='NOT_RUN'))
    ok = all(c['status'] == 'MEASUREMENT_QUALIFIED' for c in cells) and pr['status'] == 'PASS'
    out = dict(status='CX_SETUP_COMPLETE' if ok else 'CX_SETUP_INCOMPLETE_OR_BLOCKED', cells=cells, b0_shim_equivalence=pr,
               policy_verdict='NOT_SCORED')
    (HERE / 'cx_setup_summary.json').write_text(json.dumps(out, indent=2, sort_keys=True) + '\n')
    print(out['status'])
    for c in cells:
        print(' ', c['trial'], c['status'], c.get('issues', []), round((c.get('motion') or {}).get('max_excursion_rad') or 0, 4),
              (c.get('cx_b2_association') or {}).get('unprocessed_by_official_monitor'))
    print(' pair', pr)


if __name__ == '__main__':
    main()
