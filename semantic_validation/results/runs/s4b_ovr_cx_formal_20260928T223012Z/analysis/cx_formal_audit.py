#!/usr/bin/env python3
"""Prospective OpenVR C-ID / C-MON formal scorer (XRROS-S4B-OVRCXF1-1.0.0, scoped).

Validity: the registered C-X Q2 setup audit (frozen C-X Q1 checks + Q2-a/Q2-b
fault-caused-record rules) applied to each formal trial; B0/shim pair per
repetition and family (5 ms, .02 rad); every arm vs the repetition's shim of the
same family <= 5 ms matched poll timing.

Decisions/delivery as in the OpenVR W formal scorer (frozen at 6961fa0): the
defense's own records; B2 = property row AND official 'forwarded'; delivery =
exact Servo poseCallback join, by POLL INDEX (a duplicate ID reuses another ID).
T = acquisition of poll 150 unless stated.

C-ID (R_EXPLICIT):
  P1 grip polls 50-149 admitted; >= 99% delivered; slot-149 joints within .02 rad of shim.
  P2 poll-150 sample rejected with the registered reason (MISMATCH ->
     STATE_COMMAND_MISMATCH, DUPLICATE_ID -> DUPLICATE_SOURCE_EVENT_ID) <= 50 ms after T;
     neutralization request <= 50 ms; stop reply + hold; no Servo motion command after
     T+300 ms; Gazebo settled by T+1 s.
  P3 poll 150 never delivered.  P4 no delivery of polls 151-499 (no held-grip restart).
C-MON (the Docker C-MON formal rule): T/A = ABSENT barrier/0; DISCONNECT proven kill/0;
  NONRESPONSIVE proven stop/50 ms; B1/B3 gate crash last verdict record/250 ms.
  M1 no neutralization before T-1 ms; (not ABSENT) slot-149 joints within .02 rad of shim.
  M2 request <= T+A+50 ms; stop reply + hold; no Servo motion command after
     T+A+300 ms; settled by T+A+1 s.  B2-native scored with the same rule (measured).
+-1 ms around a 50 ms bound with no other violation -> UNKNOWN_BOUNDARY_STRADDLE.
B0/shim are controls (injected-sample consequences reported for the shim).
"""
import argparse
import csv
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / 'raw'
Q = ROOT.parent / 's4b_ovr_cx_q1_20260928T220949Z'
W = ROOT.parent / 's4b_ovr_formal_20260928T192004Z'
sys.path.insert(0, str(Q / 'analysis'))
sys.path.insert(1, str(W / 'analysis'))
import cx_setup_audit_q2 as q2  # noqa: E402  registered C-X Q2 validity
import ovr_formal_audit as w  # noqa: E402  frozen OpenVR W scorer helpers

rows, setup = w.rows, w.setup
REASON = {'MISMATCH': 'STATE_COMMAND_MISMATCH', 'DUPLICATE_ID': 'DUPLICATE_SOURCE_EVENT_ID'}
ALLOW = {'ORACLE_ABSENT': 0, 'ORACLE_DISCONNECT': 0, 'ORACLE_NONRESPONSIVE': 50_000_000,
         'B1_GATE_FAIL': 250_000_000, 'B3_GATE_FAIL': 250_000_000}
DEFENSES = ('b1', 'b2', 'b2c', 'b3', 'b2stc')
COMPOSED = ('b1', 'b2c', 'b3', 'b2stc')
SUFFIXES = ('', '_setup02', '_setup03')


def delivered_by_index(root, baseline):
    stage = 'stripper_servo_input' if baseline.startswith('b2') else 'production_pose'
    cbs = Counter(setup.pose_key(dict(sec=c['stamp_sec'], nanosec=c['stamp_nanosec']), c['position'])
                  for c in rows(root / 'servo_callback_overlay.jsonl'))
    out = set()
    for p in rows(root / 'lineage.jsonl'):
        if p.get('kind') == 'publish' and p.get('stage') == stage:
            pl = p['payload']
            pos = pl['pose']['position']
            if cbs[setup.pose_key(pl['header']['stamp'], [pos['x'], pos['y'], pos['z']])] == 1:
                idx = (p.get('parent') or {}).get('index')
                if idx is not None:
                    out.add(int(idx))
    return out


def decisions_by_index(root, baseline):
    """Like the W scorer, but keyed strictly by poll index (B2 via the envelope origin index)."""
    return w.decisions(root, baseline)


def gate_trigger(root, baseline, t_fault):
    if baseline == 'b1':
        times = [g['decision_monotonic_ns'] for g in rows(root / 'gate_verdict.jsonl')]
    else:
        times = [r['decision_monotonic_ns'] for r in rows(root / 'lineage.jsonl') if r.get('kind') == 'b3_publish_check']
    before = [t for t in times if t <= t_fault]
    if not before or any(t > t_fault for t in times):
        return None
    return max(before)


def audit_trial(row, root):
    arm, fam, kind, fault = row['baseline'], row['family'], row['cid_kind'], row['fault']
    base = dict(trial_id=row['trial_id'], attempt=root.name, repetition=int(row['repetition']), arm=arm, family=fam,
                cid_kind=kind, fault=fault)
    ev = q2.inspect(root, arm, fault, row['expect_motion'] == '1')
    if ev['status'] != 'MEASUREMENT_QUALIFIED':
        return dict(base, comparison_status='INVALID_COMPARISON', policy_status='UNKNOWN', invalid_reasons=ev.get('issues'))
    unprocessed = (ev.get('cx_b2_association') or {}).get('unprocessed_by_official_monitor')
    common = dict(base, comparison_status='VALID_FORMAL_TRIAL', motion=ev['motion'], official_unprocessed_envelopes=unprocessed,
                  fault_injected_monotonic_ns=ev.get('fault_injected_monotonic_ns'))
    src = w.source_times(root)
    _, start, end = setup.capture(root)
    if arm in ('b0', 'shim'):
        out = dict(common, policy_status='ORIGINAL_CONTROL_NOT_SCORED' if arm == 'b0' else 'OBSERVATIONAL_SHIM_NOT_SCORED')
        if arm == 'shim' and kind != 'NONE':
            dl = delivered_by_index(root, arm)
            out['shim_consequence'] = dict(injected_poll_delivered=150 in dl, polls_151_499_delivered=len(dl & set(range(151, 500))))
        return out
    dec = w.decisions(root, arm)
    dlv = delivered_by_index(root, arm)
    a = rows(root / 'stop_adapter.jsonl')
    stops = [x for x in a if x.get('kind') == 'stop_request']
    v, why, band, extra = [], {}, False, {}

    def viol(code, attr):
        v.append(code)
        why.setdefault(code, attr)

    def delay_attr(d):
        if d is None:
            return 'OFFICIAL_MONITOR_NO_DECISION' if arm.startswith('b2') else 'DEFENSE_DECISION'
        lat = d.get('official_path_latency_ms')
        return 'OFFICIAL_MONITOR_LATENCY' if lat is not None and lat > 50 else 'DEFENSE_DECISION'

    first_trigger = next((x for x in a if x.get('kind') in ('verdict_trigger', 'health_trigger')), None)
    watchdog_by_stall = (arm.startswith('b2') and first_trigger is not None and
                         str(first_trigger.get('source', '')).endswith('VERDICT_HEARTBEAT_MISSING'))

    def pre_stop_attr():
        return 'OFFICIAL_MONITOR_STALL_TRIPPED_COMMON_WATCHDOG' if watchdog_by_stall else stale_or('DEFENSE_DECISION')

    def stale_or(default):
        if arm.startswith('b2') and any(d['reason'] == 'STALE_SOURCE' for ds in dec.values() for d in ds):
            return 'OFFICIAL_MONITOR_LATE_DECISION_STALE_LATCH'
        return default

    if fam == 'CID':
        T, A = src[150], 0
        bad = [i for i in range(50, 150) if not dec.get(i) or not all(d['admitted'] for d in dec[i])]
        if bad:
            viol('P1_VALID_SAMPLE_NOT_ADMITTED', stale_or(Counter(d['why'] for i in bad for d in dec.get(i, [dict(why='OFFICIAL_MONITOR_NO_DECISION')])).most_common(1)[0][0]))
        if len(dlv & set(range(50, 150))) / 100 < .99:
            viol('P1_DELIVERY_BELOW_99PCT', stale_or('DELIVERY_PATH'))
        rej = next((d for d in dec.get(150, []) if not d['admitted'] and d['t'] is not None), None)
        dms = None if rej is None else (rej['t'] - T) / 1e6
        wv = w.within(dms)
        if wv in ('missing', 'over'):
            viol('P2_INJECTED_REJECTION_ABSENT_OR_OVER_50MS', delay_attr(rej))
        band |= wv == 'band'
        if rej is not None and rej['reason'] != REASON[kind]:
            viol('P2_INJECTED_REJECTED_FOR_OTHER_REASON', stale_or('DEFENSE_DECISION'))
        extra.update(injected_decision_delay_ms=dms, injected_rejection_reason=None if rej is None else rej['reason'])
        if 150 in dlv:
            viol('P3_INJECTED_SAMPLE_DELIVERED', 'DEFENSE_DECISION')
        if dlv & set(range(151, 500)):
            viol('P4_HELD_GRIP_RESTART_DELIVERED', 'DEFENSE_DECISION')
        prefix = 'P2'
    else:
        tf = ev.get('fault_injected_monotonic_ns')
        A = ALLOW[fault]
        if fault in ('B1_GATE_FAIL', 'B3_GATE_FAIL'):
            T = gate_trigger(root, arm, tf)
            if T is None:
                return dict(base, comparison_status='INVALID_COMPARISON', policy_status='UNKNOWN',
                            invalid_reasons=['GATE_LAST_VERDICT_MISSING_OR_VERDICT_AFTER_CRASH'])
        else:
            T = tf
        prefix = 'M2'
        pre = [s for s in stops if s['monotonic_ns'] < T - 1_000_000]
        if pre:
            viol('M1_NEUTRALIZATION_BEFORE_LOCAL_TRIGGER', pre_stop_attr())
        op = w.decisions(root, arm) if arm.startswith('b2') else {}
        if arm.startswith('b2'):
            fwd_after = sum(1 for p in rows(root / 'lineage.jsonl') if p.get('stage') == 'stripper_servo_input' and p['monotonic_ns'] >= T)
            extra['official_forwarded_servo_inputs_after_T'] = fwd_after
    post = [s for s in stops if s['monotonic_ns'] >= T - 1_000_000]
    if arm in COMPOSED:
        rms = None if not post else (post[0]['monotonic_ns'] - T) / 1e6
        wv2 = w.within(rms, 50 + A / 1e6)
        if wv2 in ('missing', 'over'):
            already = any(s['monotonic_ns'] < T - 1_000_000 for s in stops)
            viol(f'{prefix}_NEUTRALIZATION_REQUEST_ABSENT_OR_LATE', pre_stop_attr() if already else
                 ('OFFICIAL_MONITOR_LATENCY' if arm.startswith('b2') else 'DEFENSE_DECISION'))
        band |= wv2 == 'band'
        if post and not (any(x.get('kind') == 'stop_reply' for x in a) and any(x.get('kind') == 'controller_hold' for x in a)):
            viol(f'{prefix}_STOP_REPLY_OR_HOLD_ABSENT', 'COMMON_STOP_ADAPTER')
        extra['neutralization_request_delay_ms'] = rms
        extra['stop_trigger_source'] = next((x.get('source') for x in a if x.get('kind') in ('verdict_trigger', 'health_trigger')), None)
    else:
        viol(f'{prefix}_NO_EXPLICIT_NEUTRALIZATION', 'B2_NATIVE_HAS_NO_STOP_INTEGRATION')
    moving = [t for t in w.servo_motion(root) if T + A + 300_000_000 < t <= end]
    if moving:
        viol(f'{prefix}_SERVO_MOTION_AFTER_T_PLUS_300MS', 'B2_NATIVE_FAIL_OPEN_CONTINUED' if arm == 'b2' else 'COMMON_STOP_ADAPTER')
    settled = w.settle_after(root, T + A)
    if settled is None or settled > 1000:
        viol(f'{prefix}_NOT_SETTLED_BY_T_PLUS_1S', 'B2_NATIVE_FAIL_OPEN_CONTINUED' if arm == 'b2' else 'COMMON_STOP_ADAPTER')
    status = 'FAIL_POLICY' if v else ('UNKNOWN_BOUNDARY_STRADDLE' if band else 'PASS_POLICY')
    return dict(common, policy_status=status, policy_violations=sorted(set(v)), violation_attribution=why,
                attribution_classes=sorted(set(why.values())), local_trigger_ns=T, detection_allowance_ms=A / 1e6,
                servo_motion_after_t300=len(moving), settled_after_due_ms=settled, **extra,
                exact_source_to_specific_joint_parent='UNKNOWN_INTERVAL_ONLY')


def formal_attempt(row):
    tried = []
    for s in SUFFIXES:
        r = RAW / (row['trial_id'] + s)
        if not r.exists():
            break
        tried.append(r.name)
        if (r / 'barrier.json').exists():
            return r, tried
    return None, tried


def score_row(row):
    root, tried = formal_attempt(row)
    if root is None:
        return dict(trial_id=row['trial_id'], repetition=int(row['repetition']), arm=row['baseline'], family=row['family'],
                    cid_kind=row['cid_kind'], fault=row['fault'],
                    comparison_status='BLOCKED_MEASUREMENT' if tried else 'NOT_RUN', policy_status='NOT_SCORED', setup_attempts=tried)
    try:
        out = audit_trial(row, root)
    except (KeyError, IndexError, ValueError, TypeError, FileNotFoundError, StopIteration, json.JSONDecodeError) as exc:
        out = dict(trial_id=row['trial_id'], attempt=root.name, repetition=int(row['repetition']), arm=row['baseline'],
                   family=row['family'], cid_kind=row['cid_kind'], fault=row['fault'], comparison_status='INVALID_COMPARISON',
                   policy_status='UNKNOWN', invalid_reasons=['EVIDENCE_PARSE_ERROR'], evidence_error=f'{type(exc).__name__}: {exc}')
    out['setup_attempts'] = tried
    return out


def summarize(schedule):
    trials = [score_row(r) for r in schedule]
    by = {t['trial_id']: t for t in trials}
    eq, pairs = [], []
    for rep in range(1, 6):
        for fam, kind in (('CID', 'MISMATCH'), ('CID', 'DUPLICATE_ID'), ('CMON', 'NONE')):
            group = [r for r in schedule if int(r['repetition']) == rep and r['family'] == fam and r['cid_kind'] == kind]
            shim = next(r for r in group if r['baseline'] == 'shim')
            b0 = next(r for r in group if r['baseline'] == 'b0')
            ts, tb = by[shim['trial_id']], by[b0['trial_id']]
            e = (setup.pair(RAW / tb['attempt'], RAW / ts['attempt']) if 'attempt' in ts and 'attempt' in tb else dict(status='NOT_RUN'))
            eq.append(dict(e, repetition=rep, family=fam, cid_kind=kind))
            for arm in group:
                if arm is shim or arm is b0:
                    continue
                t = by[arm['trial_id']]
                pc = dict(pair=[shim['trial_id'], arm['trial_id']], status='NOT_RUN')
                if 'attempt' in ts and 'attempt' in t:
                    ra, rb = RAW / ts['attempt'], RAW / t['attempt']
                    sa, oka = setup.source(ra)
                    sb, okb = setup.source(rb)
                    if oka and okb:
                        st = [json.loads((r / 'barrier.json').read_text())['start_monotonic_ns'] for r in (ra, rb)]
                        timing = max(abs((x['source_timestamp_ns'] - st[0]) - (y['source_timestamp_ns'] - st[1])) / 1e6 for x, y in zip(sa, sb))
                        near = lambda js, tt: min(js, key=lambda x: abs(x[0] - tt))[1]
                        ja, jb = w.joints(ra), w.joints(rb)
                        pre = max(abs(x - y) for x, y in zip(near(ja, sa[149]['source_timestamp_ns']), near(jb, sb[149]['source_timestamp_ns'])))
                        pc.update(status='PASS_SCHEDULE' if timing <= 5 else 'INVALID_COMPARISON',
                                  max_source_offset_difference_ms=timing, slot149_joint_difference_rad=pre)
                    else:
                        pc['status'] = 'INVALID_COMPARISON'
                pairs.append(pc)
                if t.get('comparison_status') != 'VALID_FORMAL_TRIAL' or arm['baseline'] not in DEFENSES:
                    continue
                if e.get('status') != 'PASS' or pc['status'] != 'PASS_SCHEDULE':
                    t.update(comparison_status='INVALID_COMPARISON', policy_status_before_pair_gate=t['policy_status'],
                             policy_status='UNKNOWN', invalid_reasons=['REPETITION_B0_SHIM_OR_MATCHED_SCHEDULE_NOT_PASS'])
                elif pc['slot149_joint_difference_rad'] > .02 and arm['fault'] != 'ORACLE_ABSENT':
                    code = 'P1_PREFAULT_JOINT_PATH_OVER_0_02RAD_VS_SHIM' if fam == 'CID' else 'M1_PREFAULT_JOINT_PATH_OVER_0_02RAD_VS_SHIM'
                    t['policy_violations'] = sorted(set(t['policy_violations'] + [code]))
                    t['violation_attribution'][code] = 'DEFENSE_DECISION'
                    t['attribution_classes'] = sorted(set(t['violation_attribution'].values()))
                    t['policy_status'] = 'FAIL_POLICY'
    counts = Counter(t['comparison_status'] for t in trials)
    complete = counts.get('VALID_FORMAL_TRIAL', 0) == len(schedule) and all(x.get('status') == 'PASS' for x in eq)
    return dict(status='CX_SCOPED_FORMAL_COMPLETE' if complete else 'CX_SCOPED_FORMAL_PARTIAL_OR_INVALID',
                formal_configuration='XRROS-S4B-OVRCXF1-1.0.0 (scoped)', protocol='XRROS-S4-1.0.0', seed=20260922,
                trials=trials, comparison_counts=dict(counts),
                policy_counts=dict(sorted(Counter(f"{t['arm']}|{t['cid_kind'] if t['family']=='CID' else t['fault']}|{t['policy_status']}" for t in trials).items())),
                b0_shim_equivalence=eq, matched_source_schedule_pairs=pairs,
                registered_not_run=[dict(cells='C-ID MISSING_FIELD, MISSING_ID', status='NOT_RUN_SCOPED_SAME_SHARED_FIELD_PRESENCE_CHECK_TRANSPORT_EXERCISED'),
                                    dict(cells='C-ID B2-native', status='NOT_RUN_SCOPED_NO_STOP_INTEGRATION_ESTABLISHED'),
                                    dict(cells='all I_NATIVE', status='NOT_RUN_UNOBSERVABLE_BY_CONSTRUCTION'),
                                    dict(cells='C-MON native-regime', status='NOT_RUN_SCOPED_HEALTH_PATH_REGIME_INDEPENDENT')],
                exact_source_to_specific_joint_parent='UNKNOWN_INTERVAL_ONLY')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--order', type=int)
    a = ap.parse_args()
    schedule = list(csv.DictReader((ROOT / 'schedule.csv').open()))
    if a.order:
        out = score_row(schedule[a.order - 1])
        print(out['trial_id'], out['comparison_status'], out['policy_status'], out.get('policy_violations', out.get('invalid_reasons')))
        return
    out = summarize(schedule)
    (ROOT / 'analysis/formal_summary.json').write_text(json.dumps(out, indent=2, sort_keys=True) + '\n')
    print(out['status'], json.dumps(out['comparison_counts'], sort_keys=True))


if __name__ == '__main__':
    main()
