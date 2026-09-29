#!/usr/bin/env python3
"""XRROS-S4B-OVRCXQ2-1.0.0: analyzer-only refinement of the C-X setup audit, applied
to the RETAINED Q1 raw (no new trial). Registered before this re-audit ran.

Q2-a (B2 association under oracle faults): a property row is required exactly for
      envelopes that received a real oracle verdict (verdict_raw currently_true /
      currently_false). An official 'unknown' status without a property row is the
      fault's own record, allowed only for envelopes published no earlier than
      1 s before the proven fault (monitor-queue lag bound; ABSENT: always).
      Envelopes without any official status remain a recorded B2 outcome.
Q2-b (gate-crash cells): Servo-input publications at or after the common adapter's
      first stop request that lack a Servo callback are a consequence of the fault
      response, not an observation gap; every publication before it must still join
      exactly one callback, and no callback may be unjoined.
Everything else is the frozen Q1 C-X audit.
"""
import json
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import cx_setup_audit as q  # noqa: E402

LAG_NS = 1_000_000_000


def b2_association(root, fault, t_fault):
    lin = q.rows(root / 'lineage.jsonl')
    env = [r for r in lin if r.get('stage') == 'production_envelope' and r.get('envelope_kind') != 'calibration']
    props = Counter(p.get('monitor_event_id') for p in q.rows(root / 'property.jsonl'))
    status = {}
    for s in q.rows(root / 'monitor_full_status.jsonl'):
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
        real = st.get('verdict_raw') in ('currently_true', 'currently_false')
        if real and props[k] != 1:
            issues['PROPERTY_NOT_EXACTLY_ONE_FOR_REAL_VERDICT'] += 1
        if not real:
            fault_record = fault == 'ORACLE_ABSENT' or (fault in q.ORACLE_FAULTS and t_fault is not None and
                                                         e['monotonic_ns'] >= t_fault - LAG_NS)
            if not fault_record or props[k] != 0:
                issues['UNKNOWN_STATUS_NOT_ATTRIBUTABLE_TO_FAULT'] += 1
        if rec[k] != (1 if st.get('decision') == 'forwarded' else 0):
            issues['RECEIPT_MISMATCH'] += 1
    return dict(envelopes=len(env), unprocessed_by_official_monitor=unprocessed, issues=dict(issues))


def gate_callback_ok(root, baseline):
    stops = [x['monotonic_ns'] for x in q.rows(root / 'stop_adapter.jsonl') if x.get('kind') == 'stop_request']
    t_stop = stops[0] if stops else None
    stage = 'stripper_servo_input' if baseline.startswith('b2') else 'production_pose'
    cbs = Counter(q.q1.pose_key(dict(sec=c['stamp_sec'], nanosec=c['stamp_nanosec']), c['position'])
                  for c in q.rows(root / 'servo_callback_overlay.jsonl'))
    pubs = {}
    for p in q.rows(root / 'lineage.jsonl'):
        if p.get('kind') == 'publish' and p.get('stage') == stage:
            pl = p['payload']
            pos = pl['pose']['position']
            pubs.setdefault(q.q1.pose_key(pl['header']['stamp'], [pos['x'], pos['y'], pos['z']]), []).append(p['monotonic_ns'])
    unjoined = sum(n for k, n in cbs.items() if len(pubs.get(k, [])) != 1)
    before_bad = sum(1 for k, ts in pubs.items() for t in ts if (t_stop is None or t < t_stop) and cbs[k] != 1)
    after_missing = sum(1 for k, ts in pubs.items() for t in ts if t_stop is not None and t >= t_stop and cbs[k] != 1)
    return unjoined == 0 and before_bad == 0, dict(unjoined_callbacks=unjoined, pre_stop_without_one_callback=before_bad,
                                                   post_stop_without_callback=after_missing)


def inspect(root, baseline, fault, expect_motion):
    out = q.inspect(root, baseline, fault, expect_motion)
    if 'NO_START_BARRIER' in out.get('issues', []):
        return out
    issues = list(out['issues'])
    if baseline.startswith('b2'):
        issues = [i for i in issues if i != 'B2_OFFICIAL_ASSOCIATION_INCOMPLETE']
        a = b2_association(root, fault, out.get('fault_injected_monotonic_ns'))
        out['cx_b2_association'] = a
        if a['issues']:
            issues.append('B2_OFFICIAL_ASSOCIATION_INCOMPLETE')
    if fault in ('B1_GATE_FAIL', 'B3_GATE_FAIL') and 'SERVO_CALLBACK_EXACT_JOIN_INCOMPLETE' in issues:
        ok, detail = gate_callback_ok(root, baseline)
        out['gate_fault_callback_detail'] = detail
        if ok:
            issues.remove('SERVO_CALLBACK_EXACT_JOIN_INCOMPLETE')
    out.update(issues=issues, status='MEASUREMENT_QUALIFIED' if not issues else 'BLOCKED_MEASUREMENT')
    return out


def main():
    q.inspect_frozen = q.inspect
    import csv
    schedule = list(csv.DictReader((q.ROOT / 'qualification_schedule.csv').open()))
    cells = []
    for row in schedule:
        root = q.RAW / row['trial_id']
        out = inspect(root, row['baseline'], row['fault'], row['expect_motion'] == '1')
        cells.append(out)
    b0 = next(r for r in schedule if r['baseline'] == 'b0')
    shim = next(r for r in schedule if r['baseline'] == 'shim')
    pr = q.q1.pair(q.RAW / b0['trial_id'], q.RAW / shim['trial_id'])
    ok = all(c['status'] == 'MEASUREMENT_QUALIFIED' for c in cells) and pr['status'] == 'PASS'
    out = dict(status='CX_Q2_REAUDIT_SETUP_COMPLETE' if ok else 'CX_Q2_REAUDIT_INCOMPLETE', cells=cells, b0_shim_equivalence=pr,
               note='analyzer-only re-audit of retained Q1 raw', policy_verdict='NOT_SCORED')
    (HERE / 'cx_q2_reaudit_summary.json').write_text(json.dumps(out, indent=2, sort_keys=True) + '\n')
    print(out['status'])
    for c in cells:
        print(' ', c['trial'], c['status'], c.get('issues'), c.get('gate_fault_callback_detail') or '')


if __name__ == '__main__':
    main()
