#!/usr/bin/env python3
"""Prospective Docker D6 invalidation/recovery formal scorer (XRROS-S4B-D6F1-1.0.0, scoped).

Derived from the frozen D5 scorer; D6 differences only. Validity: frozen D6
setup inspect() (D5 inspect with D6 fixture/transport rules); motion required
for every arm; B0/shim pair (5 ms, .02 rad) per repetition; arm schedule vs
shim (5 ms). Policy for I_FULL defenses (XRROS-S4-1.0.0 sections 5/8, F250):
 P1 no rejection of docker:36..55 decided before the local invalidation trigger;
    exact callbacks for them; pre-fault joint within .02 rad of the shim.
 P2 local trigger = first observation of tracked=false docker:56 (B1 creation,
    else ORIGINAL receiver receipt); decision and explicit neutralization request
    <= 50 ms; stop reply + controller zero; no controller output from +300 ms
    until the defense's re-arm; settled by +1 s.
 P3 every decision on invalid docker:56..75 rejects; none reaches Servo nonzero.
 P4 no allowed teleop decision or nonzero Servo command before the registered
    re-arm. R_EXPLICIT: re-arm on docker:96 (edge after >=100 ms release following
    the dwell). R_AUTO: re-arm >= 500 ms (-1 ms band) after the first valid
    evaluation following the last invalid evaluation.
 P5 joint change < .01 rad between re-arm and the first docker:112 callback.
 P6 docker:112..131 allowed, moved, resumed by the defense's own decision.
B0/shim are controls (held-grip restart consequences reported). Final pose vs
shim is descriptive only.
"""
import argparse
import csv
import json
import math
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / 'raw'
Q = ROOT.parent / 's4b_cp24_d6q1_20260928T141053Z'
sys.path.insert(0, str(Q / 'analysis'))
import d6_setup_audit as setup  # noqa: E402  frozen D6 setup audit

rows = setup.rows
d4 = setup.base.d4
source_origin = d4.source_origin
ELIGIBLE = {f'docker:{i}' for i in range(36, 56)}
INVALID = {f'docker:{i}' for i in range(56, 76)}
HELD = {f'docker:{i}' for i in range(76, 92)}
EDGE = 'docker:96'
MOVE = {f'docker:{i}' for i in range(112, 132)}
U = 1_000_000
DEFENSES = ('b1', 'b2', 'b2c', 'b3')
ATTEMPT_SUFFIXES = ('', '_setup02', '_setup03')
TRIGGER_ATTRIBUTION = {'B1_POLICY_REJECT': 'B1_SOURCE_SIDE_DECISION',
                       'B2_ORACLE_POLICY_REJECT': 'OFFICIAL_ROSMONITORING_VERDICT_CURRENTLY_FALSE',
                       'B3_POLICY_REJECT': 'B3_RECEIVING_SIDE_DECISION',
                       'VERDICT_HEARTBEAT_MISSING': 'COMMON_WATCHDOG_HEARTBEAT'}


class Invalid(Exception):
    pass


def idx(sid):
    return int(sid.split(':')[1])


def decisions(root, baseline, lineage):
    """Exact per-event decisions (source-parented) at the defense, in time order."""
    out = []
    if baseline == 'b1':
        for g in rows(root / 'gate_verdict.jsonl'):
            if g.get('kind') is None and g.get('sample_id'):
                out.append(dict(sample_id=g['sample_id'], t=g['decision_monotonic_ns'], allowed=g['allowed'] is True,
                                teleop=bool(g.get('teleop')), reason=g.get('reason')))
    elif baseline in ('b2', 'b2c'):
        props = {}
        for p in rows(root / 'property.jsonl'):
            if p.get('event_kind') != 'tick':
                props.setdefault(p.get('monitor_event_id'), []).append(p)
        for pub in lineage:
            if pub.get('kind') == 'publish' and pub.get('stage') == 'receiver_envelope':
                origin = pub.get('selected_origin') or {}
                if origin.get('sample_id') is None:
                    continue
                match = props.get(pub.get('monitor_event_id'), [])
                if len(match) != 1:
                    raise Invalid('SOURCE_PROPERTY_JOIN_NOT_UNIQUE')
                out.append(dict(sample_id=origin['sample_id'], t=match[0]['monotonic_ns'],
                                allowed=match[0]['safe'] is True, teleop=bool(match[0].get('teleop')),
                                reason=match[0].get('reason')))
    elif baseline == 'b3':
        for x in lineage:
            if x.get('kind') == 'b3_mapper_verdict' and x.get('event_kind') is None:
                o = source_origin(x.get('source_origin')) or {}
                if o.get('sample_id'):
                    out.append(dict(sample_id=o['sample_id'], t=x['monotonic_ns'], allowed=x.get('verdict') is True,
                                    teleop=bool(x.get('teleop')), reason=x.get('reason')))
    return sorted(out, key=lambda d: d['t'])


def rejections(root, baseline, lineage, dec):
    """All defense rejection times, including non-sample events (B1 disconnect row)."""
    times = [d['t'] for d in dec if not d['allowed']]
    if baseline == 'b1':
        times += [g['decision_monotonic_ns'] for g in rows(root / 'gate_verdict.jsonl')
                  if g.get('kind') == 'b1_disconnect']
    if baseline in ('b2', 'b2c'):
        times += [p['monotonic_ns'] for p in rows(root / 'property.jsonl')
                  if p.get('event_kind') != 'tick' and p.get('safe') is False]
    return sorted(set(times))


def joint_window_max_change(root, t0, t1):
    js = [(t, p) for t, p, _ in d4.joints(root) if t0 <= t <= t1]
    if len(js) < 2:
        return None
    base = js[0][1]
    return max(abs(p[k] - base[k]) for _, p in js for k in range(6))


def settle_after(root, t_ns):
    js = d4.joints(root)
    for i, (t, pos, vel) in enumerate(js):
        if t < t_ns:
            continue
        window = [(q, p, v) for q, p, v in js[i:] if q <= t + 520_000_000]
        if (len(window) >= 5 and window[-1][0] - t >= 500_000_000 and
                all(max(abs(x) for x in v) < .001 for _, _, v in window) and
                all(abs(p[k] - pos[k]) < .0001 for _, p, _ in window for k in range(6))):
            return (t - t_ns) / 1e6
    return None


def resources(root):
    m, life = d4.resources(root), d4.lifecycle_trial(root)
    out = {label: dict(cpu_seconds=x['cpu_seconds'], cpu_percent=x['cpu_percent'],
                       max_tree_rss_bytes=x['max_tree_rss_bytes']) for label, x in m['per_label'].items()}
    out['sender'] = dict(cpu_seconds=life.get('cpu_seconds'), cpu_percent=life.get('cpu_percent'),
                         max_tree_rss_bytes=life.get('observed_peak_rss_bytes'))
    return out


def consequences(callback):
    nz = Counter(c['sample_id'] for c in callback['joined'] if c['nonzero'])
    return dict(invalid_nonzero_callbacks=sum(n for s, n in nz.items() if s in INVALID),
                held_nonzero_callbacks=sum(n for s, n in nz.items() if s in HELD),
                subsequent_move_nonzero_callbacks=sum(n for s, n in nz.items() if s in MOVE))


def audit_trial(row, root):
    baseline, mode, policy = row['baseline'], row['mode'], row['rearm']
    base = dict(trial_id=row['trial_id'], attempt=root.name, repetition=int(row['repetition']),
                arm=baseline, regime='full', rearm=policy)
    ev = setup.inspect(root, baseline, 'full', True)
    if ev['status'] != 'MEASUREMENT_QUALIFIED':
        return dict(base, comparison_status='INVALID_COMPARISON', policy_status='UNKNOWN',
                    invalid_reasons=ev.get('issues', []))
    try:
        capture_end = next(x['monotonic_ns'] for x in rows(root / 'events.jsonl') if x.get('kind') == 'capture_end')
        callback = None if mode == 'b0' else d4.callback_join(root)
        common = dict(base, comparison_status='VALID_FORMAL_TRIAL', motion=ev['motion'],
                      process_resource=resources(root))
        if mode in ('b0', 'shim'):
            return dict(common, policy_status='ORIGINAL_CONTROL_NOT_SCORED' if mode == 'b0'
                        else 'OBSERVATIONAL_SHIM_NOT_SCORED',
                        original_consequences=None if callback is None else consequences(callback))
        lineage = rows(root / 'lineage.jsonl')
        dec = decisions(root, baseline, lineage)
        by_sid = {}
        for d in dec:
            by_sid.setdefault(d['sample_id'], []).append(d)
        needed = ELIGIBLE | INVALID | HELD | MOVE
        if not needed <= set(by_sid):
            raise Invalid('DECISION_EXACT_COVERAGE_INCOMPLETE')
        sent = {f'docker:{r["index"]}': r for r in rows(root / 'sent.jsonl')}
        if baseline == 'b1':
            t_trig = sent['docker:56']['sample_ns']
        else:
            rx = [x['receiver_receipt_monotonic_ns'] for x in lineage if x.get('kind') == 'source_received'
                  and (x.get('metadata') or {}).get('sample_id') == 'docker:56']
            if len(rx) != 1:
                raise Invalid('FIRST_INVALID_RECEIPT_NOT_UNIQUE')
            t_trig = rx[0]
        rej = [t for t in rejections(root, baseline, lineage, dec) if t >= t_trig - U]
        stops = [x for x in rows(root / 'stop_adapter.jsonl') if x.get('kind') == 'stop_request']
        starts = [x for x in rows(root / 'stop_adapter.jsonl') if x.get('kind') == 'start_request']
        replies = [x for x in rows(root / 'stop_adapter.jsonl') if x.get('kind') in ('stop_reply', 'start_reply')]
        failed = [x for x in rows(root / 'stop_adapter.jsonl') if x.get('kind') in ('stop_failed', 'start_failed')]
        zeros = [x for x in rows(root / 'stop_adapter.jsonl') if x.get('kind') == 'controller_zero']
        post = [d for d in dec if idx(d['sample_id']) >= 76]
        first_allowed = next((d for d in post if d['allowed'] and d['teleop']), None)
        invalid_evals = [d for s in INVALID for d in by_sid[s]]
    except Invalid as exc:
        return dict(base, comparison_status='INVALID_COMPARISON', policy_status='UNKNOWN', invalid_reasons=[str(exc)])
    except (KeyError, IndexError, ValueError, TypeError, FileNotFoundError, StopIteration, json.JSONDecodeError) as exc:
        return dict(base, comparison_status='INVALID_COMPARISON', policy_status='UNKNOWN',
                    invalid_reasons=['EVIDENCE_PARSE_ERROR'], evidence_error=f'{type(exc).__name__}: {exc}')
    v = []
    # P1
    # Only decisions BEFORE the local disconnect trigger are normal-phase; cached
    # copies re-evaluated after the drop are correctly rejected (DISCONNECTED).
    if any(not d['allowed'] for s in ELIGIBLE for d in by_sid[s] if d['t'] < t_trig):
        v.append('P1_FALSE_REJECTION_OF_NORMAL_ACTIVE_INPUT')
    if not ELIGIBLE <= {c['sample_id'] for c in callback['joined']}:
        return dict(common, comparison_status='INVALID_COMPARISON', policy_status='UNKNOWN',
                    invalid_reasons=['ACTIVE_SOURCE_TO_SERVO_CALLBACK_INCOMPLETE'])
    # P2
    decision_ms = None if not rej else (rej[0] - t_trig) / 1e6
    stop_after = [s for s in stops if s['monotonic_ns'] >= t_trig - U]
    request_ms = None if not stop_after else (stop_after[0]['monotonic_ns'] - t_trig) / 1e6
    if decision_ms is None or decision_ms > 50:
        v.append('P2_DISCONNECT_DECISION_ABSENT_OR_OVER_50MS')
    if request_ms is None:
        v.append('P2_NO_EXPLICIT_NEUTRALIZATION_REQUEST')
    elif request_ms > 50:
        v.append('P2_NEUTRALIZATION_REQUEST_OVER_50MS')
    if stops and (failed or not zeros):
        v.append('P2_STOP_REPLY_OR_CONTROLLER_ZERO_ABSENT')
    if any(s['monotonic_ns'] < t_trig - U for s in stops):
        v.append('P1_PREMATURE_NEUTRALIZATION_BEFORE_DISCONNECT')
    t_rearm = first_allowed['t'] if first_allowed else None
    late = [r['monotonic_ns'] for r in rows(root / 'topics.jsonl')
            if r.get('topic') == '/joint_group_velocity_controller/commands'
            and t_trig + 300_000_000 < r['monotonic_ns'] <= (t_rearm or capture_end)
            and any(abs(x) > 1e-6 for x in r['payload']['data'])]
    if late:
        v.append('P2_CONTROLLER_NONZERO_AFTER_TRIGGER_PLUS_300MS_BEFORE_REARM')
    settled = settle_after(root, t_trig)
    if settled is None or settled > 1000:
        v.append('P2_GAZEBO_NOT_SETTLED_BY_TRIGGER_PLUS_1S')
    # P3
    cons = consequences(callback)
    if any(d['allowed'] and d['teleop'] for d in invalid_evals):
        v.append('P3_INVALID_TRACKING_INPUT_ACCEPTED')
    if cons['invalid_nonzero_callbacks']:
        v.append('P3_INVALID_TRACKING_INPUT_REACHED_SERVO')
    # P4
    valid_start = None
    if first_allowed is not None:
        last_invalid = max(d['t'] for d in invalid_evals)
        after = [d for d in post if d['t'] > last_invalid]
        valid_start = after[0]['t'] if after else None
    if first_allowed is None:
        v.append('P4_NO_REARM_OBSERVED')
    elif policy == 'R_EXPLICIT':
        if first_allowed['sample_id'] != EDGE:
            v.append('P4_R_EXPLICIT_REARM_NOT_ON_RELEASE_THEN_EDGE')
    else:
        if valid_start is None or first_allowed['t'] - valid_start < 500_000_000 - U:
            v.append('P4_R_AUTO_REARM_BEFORE_500MS_VALID_DWELL')
    if policy == 'R_EXPLICIT' and cons['held_nonzero_callbacks']:
        v.append('P4_HELD_GRIP_RESTARTED_MOTION')
    if first_allowed is not None:
        early = [c for c in callback['joined'] if c['nonzero'] and idx(c['sample_id']) >= 56
                 and c['publish_ns'] < first_allowed['t']]
        if early:
            v.append('P4_MOTION_COMMAND_BEFORE_REARM')
    # P5 / P6
    cb_move = sorted(c['callback_entry_ns'] for c in callback['joined'] if c['sample_id'] in MOVE)
    jump = None
    if t_rearm is not None and cb_move:
        jump = joint_window_max_change(root, t_rearm, cb_move[0])
        if jump is None or jump >= .01:
            v.append('P5_REFERENCE_JUMP_AFTER_REARM')
    if any(not d['allowed'] for s in MOVE for d in by_sid[s]):
        v.append('P6_SUBSEQUENT_VALID_MOVEMENT_REJECTED')
    move_exc = joint_window_max_change(root, cb_move[0], capture_end) if cb_move else None
    if not cons['subsequent_move_nonzero_callbacks'] or move_exc is None or move_exc <= .01:
        v.append('P6_SUBSEQUENT_VALID_MOVEMENT_ABSENT')
    if baseline in ('b1', 'b2c', 'b3') and stops and not starts:
        v.append('P6_NO_DEFENSE_DECIDED_RESUME')
    src = next((x.get('source') for x in rows(root / 'stop_adapter.jsonl') if x.get('kind') == 'verdict_trigger'), None)
    return dict(common, policy_status='FAIL_POLICY' if v else 'PASS_POLICY', policy_violations=sorted(set(v)),
                local_disconnect_trigger_ns=t_trig, disconnect_decision_delay_ms=decision_ms,
                neutralization_request_delay_ms=request_ms, stop_requests=len(stops), resume_requests=len(starts),
                detection_attribution=TRIGGER_ATTRIBUTION.get(src, src),
                actuation_attribution='COMMON_STOP_ADAPTER_NOT_NATIVE_ROSMONITORING' if stops else None,
                gazebo_settled_after_trigger_ms=settled,
                rearm_sample=None if first_allowed is None else first_allowed['sample_id'],
                rearm_after_valid_start_ms=None if (first_allowed is None or valid_start is None)
                else (first_allowed['t'] - valid_start) / 1e6,
                rearm_after_disconnect_ms=None if t_rearm is None else (t_rearm - t_trig) / 1e6,
                reference_jump_rad=jump, subsequent_move_excursion_rad=move_exc, consequences=cons,
                invalid_decision_reasons=sorted({d['reason'] for d in invalid_evals}),
                total_observed_cpu_seconds=sum(x['cpu_seconds'] or 0 for x in common['process_resource'].values()),
                exact_source_to_specific_servo_output_controller_joint='UNKNOWN_INTERVAL_ONLY')


def formal_attempt(row):
    tried = []
    for suffix in ATTEMPT_SUFFIXES:
        root = RAW / (row['trial_id'] + suffix)
        if not root.exists():
            break
        tried.append(root.name)
        if (root / 'barrier.json').exists():
            return root, tried
    return None, tried


def score_row(row):
    root, tried = formal_attempt(row)
    if root is None:
        return dict(trial_id=row['trial_id'], repetition=int(row['repetition']), arm=row['baseline'], regime='full',
                    rearm=row['rearm'], comparison_status='BLOCKED_MEASUREMENT' if tried else 'NOT_RUN',
                    policy_status='NOT_SCORED', setup_attempts=tried)
    out = audit_trial(row, root)
    out['setup_attempts'] = tried
    return out


def summarize(schedule):
    trials = [score_row(r) for r in schedule]
    by_id = {t['trial_id']: t for t in trials}
    eq, pairs = [], []
    for rep in range(1, 6):
        group = [r for r in schedule if int(r['repetition']) == rep]
        shim = next(r for r in group if r['baseline'] == 'shim')
        b0 = next(r for r in group if r['baseline'] == 'b0')
        ts, tb = by_id[shim['trial_id']], by_id[b0['trial_id']]
        e = setup.pair(RAW / tb['attempt'], RAW / ts['attempt']) if 'attempt' in ts and 'attempt' in tb else dict(status='NOT_RUN')
        eq.append(dict(e, repetition=rep))
        for arm in group:
            if arm is shim or arm is b0:
                continue
            t = by_id[arm['trial_id']]
            pc = dict(pair=[shim['trial_id'], arm['trial_id']], status='NOT_RUN')
            if 'attempt' in ts and 'attempt' in t:
                a, b = RAW / ts['attempt'], RAW / t['attempt']
                sa, ea = setup.fixture(a)
                sb, eb = setup.fixture(b)
                if ea or eb:
                    pc['status'] = 'INVALID_COMPARISON'
                else:
                    starts = [json.loads((r / 'barrier.json').read_text())['start_monotonic_ns'] for r in (a, b)]
                    timing = max(abs((x['sample_ns'] - starts[0]) - (y['sample_ns'] - starts[1])) / 1e6
                                 for x, y in zip(sa, sb) if x.get('sample_ns') and y.get('sample_ns'))
                    same = setup.normalized_hash(sa) == setup.normalized_hash(sb)
                    pa = d4.motion(a).get('final_positions_rad')
                    pb = d4.motion(b).get('final_positions_rad')
                    ja = d4.joints(a)
                    jb = d4.joints(b)
                    s55a, s55b = sa[55]['sample_ns'], sb[55]['sample_ns']
                    near = lambda js, t: min(js, key=lambda x: abs(x[0] - t))[1] if js else None
                    pre = (max(abs(x - y) for x, y in zip(near(ja, s55a), near(jb, s55b)))
                           if ja and jb else None)
                    pc.update(status='PASS_SCHEDULE' if same and timing <= 5 else 'INVALID_COMPARISON',
                              max_source_offset_difference_ms=timing, same_fixture=same,
                              pre_fault_joint_difference_rad=pre,
                              final_joint_difference_rad_descriptive=(max(abs(x - y) for x, y in zip(pa, pb))
                                                                      if pa and pb else None))
                    cpu = lambda x: sum(v['cpu_seconds'] or 0 for v in x.get('process_resource', {}).values())
                    pc['observed_cpu_seconds_delta_vs_shim'] = cpu(t) - cpu(ts)
            pairs.append(pc)
            if t.get('comparison_status') != 'VALID_FORMAL_TRIAL' or arm['baseline'] not in DEFENSES:
                continue
            if e.get('status') != 'PASS' or pc['status'] != 'PASS_SCHEDULE' or pc.get('pre_fault_joint_difference_rad') is None:
                t.update(comparison_status='INVALID_COMPARISON', policy_status_before_pair_gate=t['policy_status'],
                         policy_status='UNKNOWN', invalid_reasons=['REPETITION_B0_SHIM_OR_MATCHED_SCHEDULE_NOT_PASS'])
            elif pc['pre_fault_joint_difference_rad'] > .02:
                t['policy_violations'] = sorted(set(t['policy_violations'] + ['P1_PREFAULT_JOINT_PATH_OVER_0_02RAD']))
                t['policy_status'] = 'FAIL_POLICY'
    counts = Counter(t['comparison_status'] for t in trials)
    complete = counts.get('VALID_FORMAL_TRIAL', 0) == len(schedule) and all(x.get('status') == 'PASS' for x in eq)
    return dict(status='D6_SCOPED_FORMAL_COMPLETE' if complete else 'D6_SCOPED_FORMAL_PARTIAL_OR_INVALID',
                formal_configuration='XRROS-S4B-D6F1-1.0.0 (scoped)', protocol='XRROS-S4-1.0.0', seed=20260922,
                trials=trials, comparison_counts=dict(counts),
                policy_counts={f'{a}|{p}|{s}': n for (a, p, s), n in Counter(
                    (t['arm'], t['rearm'], t['policy_status']) for t in trials).items()},
                b0_shim_equivalence=eq, matched_source_schedule_pairs=pairs,
                registered_not_run=[dict(arm=a, regime='native', rearm=p, repetitions=5,
                                         status='NOT_RUN_SCOPED_RECOVERY_STATE_UNOBSERVABLE_NATIVELY_SETUP_EVIDENCE_IN_D6Q1')
                                    for a in ('b1', 'b2', 'b2c', 'b3') for p in ('R_EXPLICIT', 'R_AUTO')],
                exact_internal_added_gate_transport_latency='UNKNOWN',
                exact_source_to_specific_joint_parent='UNKNOWN_INTERVAL_ONLY',
                setup_trials_not_formal='D6Q1 qualification raw excluded')


def load_schedule():
    with (ROOT / 'schedule.csv').open(newline='') as f:
        schedule = list(csv.DictReader(f))
    assert [int(x['order']) for x in schedule] == list(range(1, len(schedule) + 1))
    assert all(x['case'] == 'D6' and int(x['seed']) == 20260922 for x in schedule)
    return schedule


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--order', type=int)
    ap.add_argument('--all', action='store_true')
    args = ap.parse_args()
    schedule = load_schedule()
    if args.order:
        out = score_row(schedule[args.order - 1])
        print(out['trial_id'], out['comparison_status'], out['policy_status'],
              out.get('policy_violations', out.get('invalid_reasons')))
        return
    out = summarize(schedule)
    (ROOT / 'analysis/formal_summary.json').write_text(json.dumps(out, indent=2, sort_keys=True) + '\n')
    print(out['status'], json.dumps(out['comparison_counts'], sort_keys=True))


if __name__ == '__main__':
    main()
