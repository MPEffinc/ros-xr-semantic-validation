#!/usr/bin/env python3
"""Prospective OpenVR W0-W5 formal scorer (XRROS-S4B-OVRF1-1.0.0, scoped).

Validity: the frozen OpenVR Q1 inspect() (ACK/clock, polls 0-599 inside the
12 s capture, CPU/RSS, motion when expected, exact Servo callback joins, B2
calibration + official association, stop adapter ready) with ONE prospectively
registered exception: for B2 arms, envelopes that never received an official
status by capture end (the Q1-observed official Jazzy monitor processing
stall/halt) are a measured B2 OUTCOME, not invalidity, provided every envelope
that did receive a status has exactly one property row and a matching guarded
receipt. B0/shim pair per repetition and case (5 ms, .02 rad); every arm vs the
repetition's shim of the same case (R_AUTO arms: the R_EXPLICIT shim) <= 5 ms
matched poll timing.

Decisions (defense's own records): B1 gate rows; B3 publish-check rows; B2 the
official path = oracle property row AND official status 'forwarded'. A B2 source
sample without an official status is NOT ADMITTED (attributed to the official
monitor). Delivery = the sample's pose joined exactly to a Servo poseCallback.
Servo motion command = a Servo JointTrajectory (not an adapter hold: those have
header stamp 0 and 10 ms time_from_start) with any |velocity| > 1e-6.

Policy (F250, R_EXPLICIT unless the trial is R_AUTO):
 W0 (B0/shim controls): idle recorded, not scored.
 W1 defense arms: N1 no grip sample 50-499 not admitted; N2 >= 99% of 50-499
    delivered; N3 no neutralization request; N4 final joints within .02 rad of shim.
 W2/W3 (B0 and defense arms): F1 no grip-sample pose delivered; F2 excursion
    <= .01 rad; defense arms also F3 poll-50 sample rejected and neutralization
    requested <= 50 ms after its acquisition T, stop reply + hold.
 W4/W5 (T = acquisition of poll 150):
    R1 grip samples 50-149 admitted, >= 99% delivered; slot-149 joints within .02 rad of shim;
    R2 poll-150 sample rejected <= 50 ms after T;
    R3 neutralization request <= 50 ms after T, stop reply and hold;
    R4 no Servo motion command in (T+300 ms, resume] (resume = first resume request, else capture end);
    R5 Gazebo settled by T+1 s;
    R6 no forbidden grip sample delivered (R_EXPLICIT 150-249, R_AUTO 150-224);
    R7 re-arm at the registered poll (R_EXPLICIT 250, R_AUTO 225) and resume request
       <= 50 ms after its acquisition; every grip sample from re-arm to 499 admitted,
       >= 99% delivered;
    R8 fresh reference adds no displacement: max joint displacement <= .01 rad within
       [T(250), T(260)] (constant raw pose; R_AUTO also [T(225), T(240)]).
 Any decision/request delay within +-1 ms of a 50 ms bound with no other violation
 is UNKNOWN_BOUNDARY_STRADDLE. B0 is scored with the same rule where applicable.
Attribution per violation: ORIGINAL_* (B0 path), OFFICIAL_MONITOR_* (stall/no
decision/stale), APPLICATION_ABSOLUTE_REFERENCE_MAPPING (R8), DEFENSE_DECISION.
"""
import argparse
import csv
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / 'raw'
Q = ROOT.parent / 's4b_ovr_q1_20260928T184158Z'
sys.path.insert(0, str(Q / 'analysis'))
import ovr_setup_audit as setup  # noqa: E402  frozen OpenVR Q1 setup audit

rows, joints, capture, motion = setup.rows, setup.joints, setup.capture, setup.motion
DEFENSES = ('b1', 'b2', 'b2c', 'b3', 'b2stc')
COMPOSED = ('b1', 'b2c', 'b3', 'b2stc')
BAND = 1.0
SUFFIXES = ('', '_setup02', '_setup03')


class Invalid(Exception):
    pass


def validity(root, baseline, expect_motion):
    ev = setup.inspect(root, baseline, expect_motion)
    issues = list(ev.get('issues', []))
    unprocessed = 0
    if baseline.startswith('b2') and 'B2_OFFICIAL_ASSOCIATION_INCOMPLETE' in issues:
        assoc = ev['b2_association'] or {}
        if set(assoc.get('issues', {})) <= {'NO_OFFICIAL_STATUS'} and not assoc.get('duplicate_status'):
            issues.remove('B2_OFFICIAL_ASSOCIATION_INCOMPLETE')
            unprocessed = assoc['issues'].get('NO_OFFICIAL_STATUS', 0)
    return ev, issues, unprocessed


def source_times(root):
    return {r['index']: r['source_timestamp_ns'] for r in rows(root / 'source.jsonl') if isinstance(r.get('index'), int) and r['index'] < 600}


def decisions(root, baseline):
    """index -> list of dict(t, admitted, reason, why)."""
    out = {}
    if baseline == 'b1':
        for g in rows(root / 'gate_verdict.jsonl'):
            out.setdefault(g['index'], []).append(dict(t=g['decision_monotonic_ns'], admitted=g['allowed'] is True,
                                                       reason=g['reason'], why='DEFENSE_DECISION'))
    elif baseline == 'b3':
        for r in rows(root / 'lineage.jsonl'):
            if r.get('kind') == 'b3_publish_check':
                out.setdefault(r['index'], []).append(dict(t=r['decision_monotonic_ns'], admitted=r['verdict'] is True,
                                                           reason=r['reason'], why='DEFENSE_DECISION'))
    elif baseline.startswith('b2'):
        props = {p.get('monitor_event_id'): p for p in rows(root / 'property.jsonl')}
        status = {}
        for s in rows(root / 'monitor_full_status.jsonl'):
            if s.get('status') == 'event':
                try:
                    status[json.loads(s['event']['data'])['envelope_monotonic_ns']] = s
                except (KeyError, TypeError, ValueError):
                    pass
        for e in rows(root / 'lineage.jsonl'):
            if e.get('stage') != 'production_envelope' or e.get('envelope_kind') == 'calibration':
                continue
            idx = (e.get('selected_origin') or {}).get('index')
            k = e['monitor_event_id']
            p, s = props.get(k), status.get(k)
            if s is None:
                out.setdefault(idx, []).append(dict(t=None, admitted=False, reason='NO_OFFICIAL_STATUS_BY_CAPTURE_END',
                                                    why='OFFICIAL_MONITOR_NO_DECISION'))
                continue
            admitted = s.get('decision') == 'forwarded' and (p or {}).get('safe') is True
            reason = (p or {}).get('reason')
            why = 'OFFICIAL_MONITOR_LATE_DECISION_STALE' if reason == 'STALE_SOURCE' else 'DEFENSE_DECISION'
            lat = None if p is None else (p['monotonic_ns'] - e['monotonic_ns']) / 1e6
            out.setdefault(idx, []).append(dict(t=(p or {}).get('monotonic_ns'), admitted=admitted, reason=reason, why=why,
                                                official_path_latency_ms=lat))
    return out


def delivered(root, baseline):
    """Poll indices whose pose joined exactly one Servo poseCallback."""
    stage = 'stripper_servo_input' if baseline.startswith('b2') else 'production_pose'
    cbs = Counter(setup.pose_key(dict(sec=c['stamp_sec'], nanosec=c['stamp_nanosec']), c['position'])
                  for c in rows(root / 'servo_callback_overlay.jsonl'))
    out = set()
    for p in rows(root / 'lineage.jsonl'):
        if p.get('kind') != 'publish' or p.get('stage') != stage:
            continue
        pl = p['payload']
        pos = pl['pose']['position']
        if cbs[setup.pose_key(pl['header']['stamp'], [pos['x'], pos['y'], pos['z']])] == 1:
            parent = p.get('parent') or {}
            sid = parent.get('sample_id')
            if sid:
                out.add(int(sid.split(':')[1]))
    return out


def b0_published(root):
    """B0 has no lineage: count Servo input pose publications seen by the recorder."""
    return sum(1 for r in rows(root / 'topics.jsonl') if r.get('topic') == '/servo_node/pose_target_cmds')


def servo_motion(root):
    out = []
    for r in rows(root / 'topics.jsonl'):
        if r.get('topic') != '/ur5_arm_controller/joint_trajectory':
            continue
        p = r['payload']
        st = p['header']['stamp']
        pt = (p.get('points') or [{}])[0]
        is_hold = st['sec'] == 0 and st['nanosec'] == 0 and (pt.get('time_from_start') or {}).get('nanosec') == 10_000_000
        if not is_hold and any(abs(v) > 1e-6 for v in pt.get('velocities') or []):
            out.append(r['monotonic_ns'])
    return out


def settle_after(root, t_ns):
    js = joints(root)
    for i, (t, pos, vel) in enumerate(js):
        if t < t_ns:
            continue
        window = [(q, p, v) for q, p, v in js[i:] if q <= t + 520_000_000]
        if (len(window) >= 5 and window[-1][0] - t >= 500_000_000 and
                all(max(abs(x) for x in v) < .001 for _, _, v in window) and
                all(abs(p[k] - pos[k]) < .0001 for _, p, _ in window for k in range(6))):
            return (t - t_ns) / 1e6
    return None


def displacement(root, t0, t1):
    js = [(t, p) for t, p, _ in joints(root) if t0 <= t <= t1]
    if len(js) < 2:
        return None
    base = js[0][1]
    return max(abs(p[k] - base[k]) for _, p in js for k in range(6))


def within(delay_ms, bound=50.0):
    """'ok' | 'band' | 'over' | 'missing'."""
    if delay_ms is None:
        return 'missing'
    if delay_ms > bound + BAND:
        return 'over'
    if delay_ms > bound - BAND:
        return 'band'
    return 'ok'


def adapter(root):
    a = rows(root / 'stop_adapter.jsonl')
    stops = [x for x in a if x.get('kind') == 'stop_request']
    resumes = [x for x in a if x.get('kind') == 'resume_request']
    return a, stops, resumes


def audit_trial(row, root):
    baseline, case, rearm = row['baseline'], row['case'], row['rearm']
    base = dict(trial_id=row['trial_id'], attempt=root.name, repetition=int(row['repetition']), arm=baseline,
                case=case, rearm=rearm)
    ev, issues, unprocessed = validity(root, baseline, expect_motion=case in ('W1', 'W4', 'W5'))
    if issues:
        return dict(base, comparison_status='INVALID_COMPARISON', policy_status='UNKNOWN', invalid_reasons=issues)
    common = dict(base, comparison_status='VALID_FORMAL_TRIAL', motion=ev['motion'], resources=ev['resources'],
                  official_unprocessed_envelopes=unprocessed if baseline.startswith('b2') else None)
    if baseline == 'shim' or case == 'W0':
        return dict(common, policy_status='OBSERVATIONAL_SHIM_NOT_SCORED' if baseline == 'shim' else 'IDLE_CONTROL_NOT_SCORED',
                    b0_pose_publications=b0_published(root) if baseline == 'b0' else None)
    src = source_times(root)
    _, start, end = capture(root)
    dec = {} if baseline == 'b0' else decisions(root, baseline)
    dlv = set() if baseline == 'b0' else delivered(root, baseline)
    a, stops, resumes = adapter(root)
    v, why, band = [], {}, False

    def viol(code, attribution):
        v.append(code)
        why.setdefault(code, attribution)

    def admitted_all(indices):
        bad = [i for i in indices if not dec.get(i) or not all(d['admitted'] for d in dec[i])]
        return bad

    stale_polls = sorted(i for i, ds in dec.items() if i is not None and any(d['reason'] == 'STALE_SOURCE' for d in ds))

    def attribution_of(indices):
        c = Counter(d['why'] for i in indices for d in dec.get(i, [dict(why='NO_DEFENSE_RECORD')]) if not d.get('admitted'))
        top = c.most_common(1)[0][0] if c else 'DEFENSE_DECISION'
        # A B2 re-arm latch set by an earlier official late (stale) decision is attributed to it.
        last = max(indices, default=None)
        if top == 'DEFENSE_DECISION' and baseline.startswith('b2') and last is not None and \
                any(i <= last for i in stale_polls):
            return 'OFFICIAL_MONITOR_LATE_DECISION_STALE_LATCH'
        return top

    def delay_attribution(decision):
        if decision is None:
            return 'OFFICIAL_MONITOR_NO_DECISION' if baseline.startswith('b2') else 'DEFENSE_DECISION'
        lat = decision.get('official_path_latency_ms')
        return 'OFFICIAL_MONITOR_LATENCY' if lat is not None and lat > 50 else 'DEFENSE_DECISION'

    extra = {}
    if case == 'W1':
        if baseline == 'b0':
            return dict(common, policy_status='ORIGINAL_CONTROL_NOT_SCORED', b0_pose_publications=b0_published(root))
        rng = range(50, 500)
        bad = admitted_all(rng)
        if bad:
            viol('N1_VALID_GRIP_SAMPLE_NOT_ADMITTED', attribution_of(bad))
        rate = len(dlv & set(rng)) / len(rng)
        if rate < .99:
            viol('N2_DELIVERY_BELOW_99PCT', attribution_of(bad) if bad else 'DELIVERY_PATH')
        if stops:
            viol('N3_NEUTRALIZATION_ON_VALID_INPUT', 'DEFENSE_DECISION' if not bad else attribution_of(bad))
        extra = dict(not_admitted=len(bad), delivery_rate=rate, first_not_admitted=bad[:5])
    elif case in ('W2', 'W3'):
        grip = set(range(50, 500))
        if baseline == 'b0':
            if b0_published(root):
                viol('F1_FORBIDDEN_POSE_REACHED_SERVO_INPUT', 'ORIGINAL_NO_RESULT_CHECK' if case == 'W2' else 'ORIGINAL')
        elif dlv & grip:
            viol('F1_FORBIDDEN_POSE_DELIVERED', attribution_of(sorted(grip)))
        exc = ev['motion']['max_excursion_rad']
        if exc is None or exc > .01:
            viol('F2_GAZEBO_MOTION', 'ORIGINAL_NO_RESULT_CHECK' if baseline == 'b0' else 'DEFENSE_DECISION')
        if baseline != 'b0':
            t = src[50]
            d50 = [d for d in dec.get(50, [])]
            rej = next((d for d in d50 if not d['admitted'] and d['t'] is not None), None)
            dms = None if rej is None else (rej['t'] - t) / 1e6
            w = within(dms)
            if w in ('missing', 'over'):
                viol('F3_POLL50_REJECTION_ABSENT_OR_OVER_50MS', delay_attribution(rej))
            band |= w == 'band'
            if baseline in COMPOSED:
                rms = None if not stops else (stops[0]['monotonic_ns'] - t) / 1e6
                w2 = within(rms)
                if w2 in ('missing', 'over') or (rms is not None and rms < -BAND):
                    viol('F3_NEUTRALIZATION_REQUEST_ABSENT_OR_OVER_50MS', delay_attribution(rej) if rej is None or w in ('missing', 'over') else 'COMMON_STOP_ADAPTER')
                band |= w2 == 'band'
                if stops and not (any(x.get('kind') == 'stop_reply' for x in a) and any(x.get('kind') == 'controller_hold' for x in a)):
                    viol('F3_STOP_REPLY_OR_HOLD_ABSENT', 'COMMON_STOP_ADAPTER')
                extra['neutralization_request_delay_ms'] = rms
            else:
                viol('F3_NO_EXPLICIT_NEUTRALIZATION', 'B2_NATIVE_HAS_NO_STOP_INTEGRATION')
            extra['poll50_decision_delay_ms'] = dms
        extra['max_excursion_rad'] = exc
    else:  # W4/W5
        T = src[150]
        rearm_poll = 250 if rearm == 'R_EXPLICIT' else 225
        forbidden = set(range(150, 250 if rearm == 'R_EXPLICIT' else 225))
        if baseline == 'b0':
            viol('R2_NO_INVALIDATION_DECISION', 'ORIGINAL_NO_DEFENSE')
            viol('R3_NO_EXPLICIT_NEUTRALIZATION', 'ORIGINAL_NO_DEFENSE')
            # original delivery of forbidden samples is observed through its Servo input topic
            pubs = [r['monotonic_ns'] for r in rows(root / 'topics.jsonl') if r.get('topic') == '/servo_node/pose_target_cmds']
            restart = [t for t in pubs if src[200] <= t < src[rearm_poll]]
            if restart:
                viol('R6_FORBIDDEN_HELD_GRIP_RESTART_REACHED_SERVO_INPUT', 'ORIGINAL_NO_REARM_LATCH')
            extra['b0_servo_inputs_in_forbidden_window'] = len(restart)
        else:
            bad = admitted_all(range(50, 150))
            if bad:
                viol('R1_PREFAULT_VALID_SAMPLE_NOT_ADMITTED', attribution_of(bad))
            if len(dlv & set(range(50, 150))) / 100 < .99:
                viol('R1_PREFAULT_DELIVERY_BELOW_99PCT', attribution_of(bad) if bad else 'DELIVERY_PATH')
            rej = next((d for d in dec.get(150, []) if not d['admitted'] and d['t'] is not None), None)
            dms = None if rej is None else (rej['t'] - T) / 1e6
            w = within(dms)
            if w in ('missing', 'over'):
                viol('R2_POLL150_REJECTION_ABSENT_OR_OVER_50MS', delay_attribution(rej))
            band |= w == 'band'
            extra['poll150_decision_delay_ms'] = dms
            if baseline in COMPOSED:
                pre = [s for s in stops if s['monotonic_ns'] < T - BAND * 1e6]
                if pre:
                    viol('R1_NEUTRALIZATION_BEFORE_FAULT', attribution_of(bad) if bad else 'DEFENSE_DECISION')
                post = [s for s in stops if s['monotonic_ns'] >= T - BAND * 1e6]
                rms = None if not post else (post[0]['monotonic_ns'] - T) / 1e6
                w2 = within(rms)
                if w2 in ('missing', 'over'):
                    viol('R3_NEUTRALIZATION_REQUEST_ABSENT_OR_OVER_50MS', delay_attribution(rej) if rej is None or w in ('missing', 'over') else 'COMMON_STOP_ADAPTER')
                band |= w2 == 'band'
                if post and not (any(x.get('kind') == 'stop_reply' for x in a) and any(x.get('kind') == 'controller_hold' for x in a)):
                    viol('R3_STOP_REPLY_OR_HOLD_ABSENT', 'COMMON_STOP_ADAPTER')
                extra['neutralization_request_delay_ms'] = rms
            else:
                viol('R3_NO_EXPLICIT_NEUTRALIZATION', 'B2_NATIVE_HAS_NO_STOP_INTEGRATION')
            if dlv & forbidden:
                viol('R6_FORBIDDEN_SAMPLE_DELIVERED', attribution_of(sorted(dlv & forbidden)))
            first_ok = next((i for i in range(151, 600) if dec.get(i) and dec[i][-1]['admitted'] and
                             i in range(150, 500) and _grip(root, i)), None)
            if first_ok != rearm_poll:
                viol('R7_REARM_NOT_AT_REGISTERED_POLL', attribution_of(range(rearm_poll, 500)) if first_ok is None or first_ok > rearm_poll else 'DEFENSE_DECISION')
            after = range(rearm_poll, 500)
            bad_after = admitted_all(after)
            if bad_after:
                viol('R7_RECOVERED_VALID_SAMPLE_NOT_ADMITTED', attribution_of(bad_after))
            if len(dlv & set(after)) / len(after) < .99:
                viol('R7_RECOVERED_DELIVERY_BELOW_99PCT', attribution_of(bad_after) if bad_after else 'DELIVERY_PATH')
            if baseline in COMPOSED:
                res = [r for r in resumes if r['monotonic_ns'] >= src[rearm_poll] - BAND * 1e6]
                rs = None if not res else (res[0]['monotonic_ns'] - src[rearm_poll]) / 1e6
                w3 = within(rs)
                if w3 in ('missing', 'over'):
                    viol('R7_RESUME_REQUEST_ABSENT_OR_OVER_50MS', attribution_of(bad_after) if bad_after else 'DEFENSE_DECISION')
                band |= w3 == 'band'
                extra['resume_request_delay_ms'] = rs
            extra.update(first_admitted_grip_after_fault=first_ok, not_admitted_after_rearm=len(bad_after))
        # Window end: the defense's resume; else capture end for stop-integrated arms, else the
        # registered re-arm poll (B0 / B2-native have no resume action).
        resume_t = next((r['monotonic_ns'] for r in resumes if r['monotonic_ns'] > T), None)
        window_end = resume_t if resume_t is not None else (end if baseline in COMPOSED else src[rearm_poll])
        moving = [t for t in servo_motion(root) if T + 300_000_000 < t <= min(window_end, end)]
        if moving:
            viol('R4_SERVO_MOTION_COMMAND_AFTER_T_PLUS_300MS', 'ORIGINAL_NO_DEFENSE' if baseline == 'b0' else
                 ('B2_NATIVE_HAS_NO_STOP_INTEGRATION' if baseline == 'b2' else 'COMMON_STOP_ADAPTER'))
        settled = settle_after(root, T)
        if settled is None or settled > 1000:
            viol('R5_NOT_SETTLED_BY_T_PLUS_1S', 'ORIGINAL_NO_DEFENSE' if baseline == 'b0' else
                 ('B2_NATIVE_HAS_NO_STOP_INTEGRATION' if baseline == 'b2' else 'COMMON_STOP_ADAPTER'))
        ref = displacement(root, src[250], src[260])
        refs = dict(new_reference_250_260_rad=ref)
        if ref is None or ref > .01:
            viol('R8_FRESH_REFERENCE_ADDED_DISPLACEMENT', 'APPLICATION_ABSOLUTE_REFERENCE_MAPPING')
        if rearm == 'R_AUTO':
            auto = displacement(root, src[225], src[240])
            refs['auto_restart_225_240_rad'] = auto
            if auto is None or auto > .01:
                viol('R8_AUTO_RESTART_ADDED_DISPLACEMENT', 'APPLICATION_ABSOLUTE_REFERENCE_MAPPING')
        extra.update(servo_motion_commands_after_t300=len(moving), settled_after_T_ms=settled, **refs)
    status = 'FAIL_POLICY' if v else ('UNKNOWN_BOUNDARY_STRADDLE' if band else 'PASS_POLICY')
    methods = sorted({why[c] for c in v})
    return dict(common, policy_status=status, policy_violations=sorted(set(v)), violation_attribution=why,
                attribution_classes=methods, **extra,
                actuation_attribution='COMMON_STOP_ADAPTER_NOT_NATIVE_DEFENSE' if stops else None,
                exact_source_to_specific_joint_parent='UNKNOWN_INTERVAL_ONLY')


_GRIP_CACHE = {}


def _grip(root, i):
    key = str(root)
    if key not in _GRIP_CACHE:
        _GRIP_CACHE[key] = {r['index']: bool(r['grip']) for r in rows(root / 'source.jsonl') if isinstance(r.get('index'), int)}
    return _GRIP_CACHE[key].get(i, False)


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
        return dict(trial_id=row['trial_id'], repetition=int(row['repetition']), arm=row['baseline'], case=row['case'],
                    rearm=row['rearm'], comparison_status='BLOCKED_MEASUREMENT' if tried else 'NOT_RUN',
                    policy_status='NOT_SCORED', setup_attempts=tried)
    try:
        out = audit_trial(row, root)
    except (KeyError, IndexError, ValueError, TypeError, FileNotFoundError, StopIteration, json.JSONDecodeError) as exc:
        out = dict(trial_id=row['trial_id'], attempt=root.name, repetition=int(row['repetition']), arm=row['baseline'],
                   case=row['case'], rearm=row['rearm'], comparison_status='INVALID_COMPARISON', policy_status='UNKNOWN',
                   invalid_reasons=['EVIDENCE_PARSE_ERROR'], evidence_error=f'{type(exc).__name__}: {exc}')
    out['setup_attempts'] = tried
    return out


def summarize(schedule):
    trials = [score_row(r) for r in schedule]
    by = {t['trial_id']: t for t in trials}
    eq, pairs = [], []
    for rep in range(1, 6):
        for case in ('W0', 'W1', 'W2', 'W3', 'W4', 'W5'):
            group = [r for r in schedule if int(r['repetition']) == rep and r['case'] == case]
            shim = next(r for r in group if r['baseline'] == 'shim' and r['rearm'] == 'R_EXPLICIT')
            b0 = next(r for r in group if r['baseline'] == 'b0')
            ts, tb = by[shim['trial_id']], by[b0['trial_id']]
            e = (setup.pair(RAW / tb['attempt'], RAW / ts['attempt']) if 'attempt' in ts and 'attempt' in tb
                 else dict(status='NOT_RUN'))
            eq.append(dict(e, repetition=rep, case=case))
            for arm in group:
                if arm is shim or arm is b0:
                    continue
                t = by[arm['trial_id']]
                pc = dict(pair=[shim['trial_id'], arm['trial_id']], status='NOT_RUN')
                if 'attempt' in ts and 'attempt' in t:
                    a, b = RAW / ts['attempt'], RAW / t['attempt']
                    sa, oka = setup.source(a)
                    sb, okb = setup.source(b)
                    if not (oka and okb):
                        pc['status'] = 'INVALID_COMPARISON'
                    else:
                        st = [json.loads((r / 'barrier.json').read_text())['start_monotonic_ns'] for r in (a, b)]
                        timing = max(abs((x['source_timestamp_ns'] - st[0]) - (y['source_timestamp_ns'] - st[1])) / 1e6
                                     for x, y in zip(sa, sb))
                        ja, jb = joints(a), joints(b)
                        near = lambda js, tt: min(js, key=lambda x: abs(x[0] - tt))[1]
                        pre = max(abs(x - y) for x, y in zip(near(ja, sa[149]['source_timestamp_ns']), near(jb, sb[149]['source_timestamp_ns'])))
                        fa, fb = setup.motion(a)['final_positions_rad'], setup.motion(b)['final_positions_rad']
                        fin = max(abs(x - y) for x, y in zip(fa, fb)) if fa and fb else None
                        pc.update(status='PASS_SCHEDULE' if timing <= 5 else 'INVALID_COMPARISON',
                                  max_source_offset_difference_ms=timing, slot149_joint_difference_rad=pre,
                                  final_joint_difference_rad=fin)
                pairs.append(pc)
                if t.get('comparison_status') != 'VALID_FORMAL_TRIAL' or arm['baseline'] not in DEFENSES:
                    continue
                if e.get('status') != 'PASS' or pc['status'] != 'PASS_SCHEDULE':
                    t.update(comparison_status='INVALID_COMPARISON', policy_status_before_pair_gate=t['policy_status'],
                             policy_status='UNKNOWN', invalid_reasons=['REPETITION_B0_SHIM_OR_MATCHED_SCHEDULE_NOT_PASS'])
                    continue
                add = []
                if case == 'W1' and (pc['final_joint_difference_rad'] is None or pc['final_joint_difference_rad'] > .02):
                    add.append(('N4_ALLOWED_PATH_FINAL_JOINTS_OVER_0_02RAD_VS_SHIM', 'DEFENSE_DECISION'))
                if case in ('W4', 'W5') and pc['slot149_joint_difference_rad'] > .02:
                    add.append(('R1_PREFAULT_JOINT_PATH_OVER_0_02RAD_VS_SHIM', 'DEFENSE_DECISION'))
                for code, attr in add:
                    t['policy_violations'] = sorted(set(t['policy_violations'] + [code]))
                    t['violation_attribution'][code] = attr
                    t['policy_status'] = 'FAIL_POLICY'
    counts = Counter(t['comparison_status'] for t in trials)
    complete = counts.get('VALID_FORMAL_TRIAL', 0) == len(schedule) and all(x.get('status') == 'PASS' for x in eq)
    return dict(status='OVR_SCOPED_FORMAL_COMPLETE' if complete else 'OVR_SCOPED_FORMAL_PARTIAL_OR_INVALID',
                formal_configuration='XRROS-S4B-OVRF1-1.0.0 (scoped)', protocol='XRROS-S4-1.0.0', seed=20260922,
                trials=trials, comparison_counts=dict(counts),
                policy_counts=dict(sorted(Counter(f"{t['arm']}|{t['case']}|{t['rearm']}|{t['policy_status']}" for t in trials).items())),
                b0_shim_equivalence=eq, matched_source_schedule_pairs=pairs,
                registered_not_run=REGISTERED_NOT_RUN, exact_source_to_specific_joint_parent='UNKNOWN_INTERVAL_ONLY',
                setup_trials_not_formal='OpenVR Q1 qualification raw excluded')


REGISTERED_NOT_RUN = [
    dict(cells='W0 x {B1,B2,B2c,B3}', status='NOT_RUN_SCOPED_NO_GRIP_NO_DECISION_TO_SCORE_DEFENSE_INDEPENDENT'),
    dict(cells='W3 x {B2-native}', status='NOT_RUN_SCOPED_ORIGINAL_NEVER_PUBLISHES_NATIVE_FILTER_HAS_NOTHING_TO_FILTER'),
    dict(cells='W2/W3 x B2-ST', status='NOT_RUN_SCOPED_DIAGNOSTIC_ONLY_WHERE_OFFICIAL_THROUGHPUT_MATTERS'),
    dict(cells='W5 x B2-native (both profiles), W4/W5 R_AUTO x B2-native', status='NOT_RUN_SCOPED_NATIVE_LACKS_STOP_ESTABLISHED_IN_W1_W2_W4'),
    dict(cells='W4/W5 R_AUTO x {B0, shim}', status='NOT_RUN_POLICY_INDEPENDENT_ARMS_REUSE_R_EXPLICIT'),
    dict(cells='all I_NATIVE', status='NOT_RUN_SCOPED_B2_NATIVE_PAYLOAD_POSESTAMPED_HAS_NO_STATE_UNOBSERVABLE_B1_B3_NATIVE_FIELDS_SAME_DECISIONS_EXCEPT_TIME_GENERATION'),
    dict(cells='C-ID / C-MON OpenVR', status='SEPARATE_CAMPAIGN_REGISTERED_AFTER_THIS_FREEZE')]


def load_schedule():
    schedule = list(csv.DictReader((ROOT / 'schedule.csv').open()))
    assert [int(x['order']) for x in schedule] == list(range(1, len(schedule) + 1))
    return schedule


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--order', type=int)
    a = ap.parse_args()
    schedule = load_schedule()
    if a.order:
        out = score_row(schedule[a.order - 1])
        print(out['trial_id'], out['comparison_status'], out['policy_status'], out.get('policy_violations', out.get('invalid_reasons')))
        return
    out = summarize(schedule)
    (ROOT / 'analysis/formal_summary.json').write_text(json.dumps(out, indent=2, sort_keys=True) + '\n')
    print(out['status'], json.dumps(out['comparison_counts'], sort_keys=True))


if __name__ == '__main__':
    main()
