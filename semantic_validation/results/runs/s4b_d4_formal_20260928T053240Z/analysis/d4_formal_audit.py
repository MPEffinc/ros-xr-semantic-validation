#!/usr/bin/env python3
"""Prospective Docker D4 source-freshness formal scorer (XRROS-S4B-D4F1-1.0.0).

Validity: the frozen D4Q2 setup audit (fixture/stamps, ACK+clock, ticks, CPU/RSS,
exact source->Servo callback on the recorded stamp, B2 calibration and official
association, post-capture drain) on each formal root; motion is a validity gate
only for B0/shim positive controls. Policy (XRROS-S4-1.0.0 sections 5/8):

* every teleop-true decision of a defense is judged against the SOURCE age at
  that decision = decision time - independently recorded source stamp (never the
  ROS header, never receipt age); expected = accept iff -5 ms <= age <= F, with a
  1 ms uncertainty band scored UNKNOWN;
* false acceptance / false rejection counts; forbidden consequence = nonzero
  Servo callback parented to a sample the defense should have rejected;
* where rejection is expected: decision and neutralization request <= 50 ms after
  the local trigger (first over-budget sample observable at the defense), no
  nonzero controller after trigger+300 ms, Gazebo settled by trigger+1 s;
* where acceptance is expected: zero false rejection, no stop request, exact
  callbacks for docker:36..55, final joints within .02 rad of the same
  repetition/condition shim.

I_NATIVE interfaces carry no source time: freshness is UNOBSERVABLE to those
defenses (never a method failure); an observable false rejection or allowed-path
failure is still FAIL_POLICY. Mechanisms are attributed separately; the common
stop adapter is never credited to native ROSMonitoring.
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
Q = ROOT.parent / 's4b_cp18_d4q2_20260928T052627Z'
sys.path.insert(0, str(Q / 'analysis'))
import d4_setup_audit as setup  # noqa: E402  frozen D4Q2 setup audit
from d4_age import CONDITIONS, PROFILES, expected  # noqa: E402

rows = setup.rows
source_origin = setup.source_origin
TELEOP = {f'docker:{i}' for i in range(20, 56)}
ELIGIBLE = {f'docker:{i}' for i in range(36, 56)}
U = 1_000_000
DECISION_MS, CONTINUE_MS, SETTLE_MS = 50.0, 300.0, 1000.0
DEFENSES = ('b1', 'b2', 'b2c', 'b3')
ATTEMPT_SUFFIXES = ('', '_setup02', '_setup03')
TRIGGER_ATTRIBUTION = {
    'B1_POLICY_REJECT': 'B1_SOURCE_SIDE_FRESHNESS_DECISION',
    'B2_ORACLE_POLICY_REJECT': 'OFFICIAL_ROSMONITORING_VERDICT_CURRENTLY_FALSE',
    'B2_MONITOR_HEALTH': 'B2_COMPOSED_MONITOR_HEALTH_UNKNOWN_OR_ERROR',
    'B3_POLICY_REJECT': 'B3_RECEIVING_SIDE_FRESHNESS_DECISION',
    'B1_VERDICT_HEARTBEAT_MISSING': 'COMMON_WATCHDOG_HEARTBEAT',
    'B2_VERDICT_HEARTBEAT_MISSING': 'B2_COMPOSED_COMMON_WATCHDOG_HEARTBEAT',
    'B3_VERDICT_HEARTBEAT_MISSING': 'COMMON_WATCHDOG_HEARTBEAT',
}


class Invalid(Exception):
    pass


def percentile(values, p=.95):
    if not values:
        return None
    ordered = sorted(values)
    return ordered[max(0, math.ceil(len(ordered) * p) - 1)]


def decisions(root, baseline, regime, lineage, sent_by_id):
    """Exact per-event teleop-true decisions at this defense; no time joins."""
    out = []
    if baseline == 'b1':
        for g in rows(root / 'gate_verdict.jsonl'):
            if g.get('kind') is None and g.get('sample_id') in TELEOP:
                out.append(dict(sample_id=g['sample_id'], t=g['decision_monotonic_ns'],
                                allowed=g['allowed'] is True, reason=g.get('reason'),
                                defense_stamp=g.get('source_timestamp_ns')))
    elif baseline in ('b2', 'b2c'):
        stage = 'receiver_envelope' if regime == 'full' else 'receiver_native_monitor_input'
        key = 'monitor_event_id' if regime == 'full' else 'payload_sha256'
        props = {}
        for p in rows(root / 'property.jsonl'):
            if p.get('event_kind') != 'tick':
                props.setdefault(p.get(key), []).append(p)
        for pub in lineage:
            if pub.get('kind') != 'publish' or pub.get('stage') != stage:
                continue
            origin = pub.get('selected_origin') if regime == 'full' else pub.get('parent')
            sid = (origin or {}).get('sample_id')
            if sid not in TELEOP:
                continue
            match = props.get(pub.get(key), [])
            if len(match) != 1:
                raise Invalid('TELEOP_SOURCE_PROPERTY_JOIN_NOT_UNIQUE')
            out.append(dict(sample_id=sid, t=match[0]['monotonic_ns'], allowed=match[0]['safe'] is True,
                            reason=match[0].get('reason'), defense_stamp=(origin or {}).get('source_timestamp_ns')))
    elif baseline == 'b3':
        for x in lineage:
            if x.get('kind') == 'b3_mapper_verdict' and x.get('event_kind') is None:
                o = source_origin(x.get('source_origin')) or {}
                if o.get('sample_id') in TELEOP:
                    out.append(dict(sample_id=o['sample_id'], t=x['monotonic_ns'],
                                    allowed=x.get('verdict') is True, reason=x.get('reason'),
                                    defense_stamp=o.get('source_timestamp_ns')))
    for d in out:
        stamp = sent_by_id[d['sample_id']]['source_timestamp_ns']
        if regime == 'full' and d['defense_stamp'] != stamp:
            raise Invalid('SOURCE_STAMP_NOT_PRESERVED_TO_DEFENSE')
        d['source_age_ns'] = d['t'] - stamp
    return out


def neutralization(root, t_trig):
    events = rows(root / 'stop_adapter.jsonl')
    req = sorted((x for x in events if x.get('kind') == 'stop_request'), key=lambda x: x['monotonic_ns'])
    first = req[0] if req else None
    src = first.get('source') if first else None
    return dict(adapter_present=(root / 'stop_adapter.ready').exists(),
                request_ns=first['monotonic_ns'] if first else None,
                request_delay_ms=None if first is None or t_trig is None else (first['monotonic_ns'] - t_trig) / 1e6,
                request_trigger_source=src, detection_attribution=TRIGGER_ATTRIBUTION.get(src, src),
                actuation_attribution='COMMON_STOP_ADAPTER_NOT_NATIVE_ROSMONITORING' if first else None,
                reply_ok=any(x.get('kind') == 'stop_reply' and 'success=True' in str(x.get('reply')) for x in events),
                controller_zero=any(x.get('kind') == 'controller_zero' for x in events),
                stop_failed=any(x.get('kind') == 'stop_failed' for x in events))


def audit_trial(row, root):
    baseline, regime, mode = row['baseline'], row['regime'], row['mode']
    condition, profile = row['condition'], row['profile']
    F = PROFILES[profile]
    base = dict(trial_id=row['trial_id'], attempt=root.name, repetition=int(row['repetition']),
                arm=baseline, regime=regime, condition=condition, profile=profile)
    ev = setup.inspect(root, baseline, regime, condition, expect_motion=baseline in ('b0', 'shim'))
    if ev['status'] != 'MEASUREMENT_QUALIFIED':
        return dict(base, comparison_status='INVALID_COMPARISON', policy_status='UNKNOWN',
                    invalid_reasons=ev.get('issues', []))
    try:
        sent = rows(root / 'sent.jsonl')
        sent_by_id = {f'docker:{r["index"]}': r for r in sent}
        capture_end = next(x['monotonic_ns'] for x in rows(root / 'events.jsonl') if x.get('kind') == 'capture_end')
        mv = ev['motion']
        common = dict(base, comparison_status='VALID_FORMAL_TRIAL', motion=mv,
                      process_resource=resources(root))
        if mode in ('b0', 'shim'):
            extra = {}
            if mode == 'shim':
                first = {}
                for c in setup.callback_join(root)['joined']:
                    if c['sample_id'] in ELIGIBLE:
                        first[c['sample_id']] = min(first.get(c['sample_id'], 1e18), c['sample_to_callback_ms'])
                extra = dict(first_callback_latency_by_source_ms=first,
                             first_callback_latency_p95_ms=percentile(list(first.values())))
            return dict(common, policy_status='ORIGINAL_CONTROL_NOT_SCORED' if mode == 'b0'
                        else 'OBSERVATIONAL_SHIM_NOT_SCORED',
                        stale_input_moved_robot=mv['max_excursion_rad'] > .01, **extra)
        lineage = rows(root / 'lineage.jsonl')
        callback = setup.callback_join(root)
        dec = decisions(root, baseline, regime, lineage, sent_by_id)
        if {d['sample_id'] for d in dec} != {sid for sid in TELEOP if sent_by_id[sid]['sent'] or baseline == 'b1'}:
            raise Invalid('TELEOP_DECISION_EXACT_COVERAGE_INCOMPLETE')
        rx = {}
        for x in lineage:
            if x.get('kind') == 'source_received':
                rx.setdefault((x.get('metadata') or {}).get('sample_id'), []).append(x['receiver_receipt_monotonic_ns'])
    except Invalid as exc:
        return dict(base, comparison_status='INVALID_COMPARISON', policy_status='UNKNOWN', invalid_reasons=[str(exc)])
    except (KeyError, IndexError, ValueError, TypeError, FileNotFoundError, StopIteration, json.JSONDecodeError) as exc:
        return dict(base, comparison_status='INVALID_COMPARISON', policy_status='UNKNOWN',
                    invalid_reasons=['EVIDENCE_PARSE_ERROR'], evidence_error=f'{type(exc).__name__}: {exc}')

    observable = regime == 'full'
    judged = []
    for d in dec:
        exp = expected(d['source_age_ns'], F) if observable else None
        judged.append(dict(d, expected=exp))
    false_accept = sum(1 for d in judged if d['expected'] is False and d['allowed'])
    false_reject = sum(1 for d in judged if (d['expected'] is True or not observable) and not d['allowed'])
    unknown = sum(1 for d in judged if observable and d['expected'] is None)
    over_budget = {sid for sid in TELEOP if observable and
                   [d for d in judged if d['sample_id'] == sid] and
                   all(d['expected'] is False for d in judged if d['sample_id'] == sid)}
    expect_reject = bool(over_budget)
    # Consequence by the ANALYZER's own source age, reported for every arm
    # (for I_NATIVE this quantifies what an unobservable defense let through;
    # it is not a policy score for that arm).
    analyzer_over_budget = {sid for sid in TELEOP if [d for d in judged if d['sample_id'] == sid] and
                            all(expected(d['source_age_ns'], F) is False for d in judged if d['sample_id'] == sid)}
    analyzer_over_budget_nonzero = sum(1 for c in callback['joined']
                                       if c['nonzero'] and c['sample_id'] in analyzer_over_budget)
    forbidden = [c for c in callback['joined'] if c['nonzero'] and c['sample_id'] in over_budget]
    # Local trigger: first over-budget sample observable at the defense location.
    t_trig = None
    if expect_reject:
        first = min(over_budget, key=lambda s: int(s.split(':')[1]))
        if baseline == 'b1':
            t_trig = sent_by_id[first]['sample_ns']
        else:
            receipts = rx.get(first, [])
            if len(receipts) != 1:
                return dict(base, comparison_status='INVALID_COMPARISON', policy_status='UNKNOWN',
                            invalid_reasons=['FIRST_OVER_BUDGET_RECEIPT_NOT_UNIQUE'])
            stamp = sent_by_id[first]['source_timestamp_ns']
            age_at_rx = receipts[0] - stamp
            t_trig = receipts[0] if (age_at_rx > F + U or age_at_rx < -5_000_000 - U) else stamp + F + U
    rejections = sorted(d['t'] for d in judged if not d['allowed'])
    neutral = neutralization(root, t_trig)
    violations = []
    if false_reject:
        violations.append('FALSE_REJECTION_OF_FRESH_TELEOP_INPUT')
    if false_accept:
        violations.append('FALSE_ACCEPTANCE_OF_OVER_BUDGET_INPUT')
    if forbidden:
        violations.append('FORBIDDEN_NONZERO_SERVO_CALLBACK_FROM_OVER_BUDGET_SOURCE')
    controller_after = []
    settled_ms = None
    if expect_reject:
        decision_ms = None if not rejections else (rejections[0] - t_trig) / 1e6
        if decision_ms is None or decision_ms > DECISION_MS or decision_ms < -U / 1e6:
            violations.append('LOCAL_DECISION_ABSENT_PREMATURE_OR_OVER_50MS')
        if neutral['request_ns'] is None:
            violations.append('NO_EXPLICIT_NEUTRALIZATION_REQUEST')
        else:
            if neutral['request_delay_ms'] < -U / 1e6:
                violations.append('PREMATURE_NEUTRALIZATION_REQUEST')
            elif neutral['request_delay_ms'] > DECISION_MS:
                violations.append('NEUTRALIZATION_REQUEST_OVER_50MS')
            if neutral['stop_failed'] or not neutral['reply_ok'] or not neutral['controller_zero']:
                violations.append('STOP_REPLY_OR_CONTROLLER_ZERO_ABSENT')
        controller_after = [r['monotonic_ns'] for r in rows(root / 'topics.jsonl')
                            if r.get('topic') == '/joint_group_velocity_controller/commands'
                            and t_trig + CONTINUE_MS * 1e6 < r['monotonic_ns'] <= capture_end
                            and any(abs(v) > 1e-6 for v in r['payload']['data'])]
        if controller_after:
            violations.append('CONTROLLER_NONZERO_AFTER_TRIGGER_PLUS_300MS')
        settled_ms = settle_after(root, t_trig)
        if settled_ms is None or settled_ms > SETTLE_MS:
            violations.append('GAZEBO_NOT_SETTLED_BY_TRIGGER_PLUS_1S')
    else:
        decision_ms = None
        if neutral['request_ns'] is not None:
            violations.append('UNEXPECTED_NEUTRALIZATION_WITH_NO_OVER_BUDGET_INPUT')
        first_cb = {c['sample_id'] for c in callback['joined']}
        if not false_reject and not ELIGIBLE <= first_cb:
            return dict(base, comparison_status='INVALID_COMPARISON', policy_status='UNKNOWN',
                        invalid_reasons=['ACTIVE_SOURCE_TO_SERVO_CALLBACK_INCOMPLETE'])
        if mv['max_excursion_rad'] is None or mv['max_excursion_rad'] <= .01:
            violations.append('ADMITTED_MOTION_ABSENT')
    if not observable:
        policy = 'FAIL_POLICY' if (false_reject or (not expect_reject and violations)) else 'UNOBSERVABLE'
    else:
        policy = 'FAIL_POLICY' if violations else 'PASS_POLICY'
    first_cb_ms = {}
    for c in callback['joined']:
        if c['sample_id'] in ELIGIBLE:
            first_cb_ms[c['sample_id']] = min(first_cb_ms.get(c['sample_id'], 1e18), c['sample_to_callback_ms'])
    ages = [d['source_age_ns'] / 1e6 for d in judged]
    return dict(common, policy_status=policy, policy_violations=sorted(set(violations)),
                freshness_observable_to_defense=observable, freshness_ns=F,
                expected_rejection=expect_reject, over_budget_samples=len(over_budget),
                analyzer_over_budget_samples=len(analyzer_over_budget),
                analyzer_over_budget_nonzero_servo_callbacks=analyzer_over_budget_nonzero,
                decisions=len(judged), false_accept_count=false_accept, false_reject_count=false_reject,
                unknown_band_decisions=unknown, rejected_decisions=len(rejections),
                decision_source_age_ms=dict(min=min(ages, default=None), max=max(ages, default=None)),
                local_trigger_ns=t_trig, local_decision_delay_ms=decision_ms,
                neutralization=neutral, forbidden_nonzero_servo_callbacks=len(forbidden),
                nonzero_servo_callbacks=sum(c['nonzero'] for c in callback['joined']),
                controller_nonzero_after_trigger_300ms=len(controller_after),
                gazebo_settled_after_trigger_ms=settled_ms,
                first_callback_latency_by_source_ms=first_cb_ms,
                first_callback_latency_p95_ms=percentile(list(first_cb_ms.values())),
                source_age_at_first_eligible_callback_ms_p95=percentile(
                    [c['source_age_at_callback_ms'] for c in callback['joined'] if c['sample_id'] in ELIGIBLE]),
                total_observed_cpu_seconds=sum(x['cpu_seconds'] or 0 for x in common['process_resource'].values()),
                original_receiver_timestamp_ignored='BY_VENDOR_SOURCE_REVIEW; B0 motion reported',
                monitor_internal_post_verdict_publish_time='UNKNOWN',
                exact_source_to_specific_servo_output_controller_joint='UNKNOWN_INTERVAL_ONLY')


def settle_after(root, t_ns):
    js = setup.joints(root)
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
    m, life = setup.resources(root), setup.lifecycle_trial(root)
    out = {label: dict(cpu_seconds=x['cpu_seconds'], cpu_percent=x['cpu_percent'],
                       max_tree_rss_bytes=x['max_tree_rss_bytes']) for label, x in m['per_label'].items()}
    out['sender'] = dict(cpu_seconds=life.get('cpu_seconds'), cpu_percent=life.get('cpu_percent'),
                         max_tree_rss_bytes=life.get('observed_peak_rss_bytes'))
    return out


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
        return dict(trial_id=row['trial_id'], repetition=int(row['repetition']), arm=row['baseline'],
                    regime=row['regime'], condition=row['condition'], profile=row['profile'],
                    comparison_status='BLOCKED_MEASUREMENT' if tried else 'NOT_RUN',
                    policy_status='NOT_SCORED', setup_attempts=tried)
    out = audit_trial(row, root)
    out['setup_attempts'] = tried
    return out


def summarize(schedule):
    trials = [score_row(r) for r in schedule]
    by_id = {t['trial_id']: t for t in trials}
    pairs, eq = [], []
    for rep in range(1, 6):
        for cond in CONDITIONS:
            group = [r for r in schedule if int(r['repetition']) == rep and r['condition'] == cond]
            shim = next(r for r in group if r['baseline'] == 'shim')
            b0 = next(r for r in group if r['baseline'] == 'b0')
            ts, tb = by_id[shim['trial_id']], by_id[b0['trial_id']]
            if 'attempt' in ts and 'attempt' in tb:
                e = setup.pair(RAW / tb['attempt'], RAW / ts['attempt'], cond)
            else:
                e = dict(status='NOT_RUN')
            eq.append(dict(e, repetition=rep, condition=cond))
            for arm in group:
                if arm is shim or arm is b0:
                    continue
                t = by_id[arm['trial_id']]
                pc = dict(pair=[shim['trial_id'], arm['trial_id']], status='NOT_RUN')
                if 'attempt' in ts and 'attempt' in t:
                    a, b = RAW / ts['attempt'], RAW / t['attempt']
                    sa, ea = setup.fixture(a, cond)
                    sb, eb = setup.fixture(b, cond)
                    if ea or eb:
                        pc['status'] = 'INVALID_COMPARISON'
                    else:
                        starts = [json.loads((r / 'barrier.json').read_text())['start_monotonic_ns'] for r in (a, b)]
                        timing = max(abs((x['sample_ns'] - starts[0]) - (y['sample_ns'] - starts[1])) / 1e6
                                     for x, y in zip(sa, sb))
                        same = setup.normalized_hash(sa) == setup.normalized_hash(sb)
                        pc.update(status='PASS_SCHEDULE' if same and timing <= 5 else 'INVALID_COMPARISON',
                                  max_source_offset_difference_ms=timing, same_fixture=same)
                        fa, fb = setup.motion(a).get('final_positions_rad'), setup.motion(b).get('final_positions_rad')
                        if fa and fb:
                            pc['final_joint_difference_rad'] = max(abs(x - y) for x, y in zip(fa, fb))
                        fa_ms, fb_ms = ts.get('first_callback_latency_by_source_ms'), t.get('first_callback_latency_by_source_ms')
                        if fa_ms and fb_ms:
                            common_ids = sorted(set(fa_ms) & set(fb_ms))
                            pc['paired_source_to_first_callback_delta_p95_ms'] = percentile(
                                [fb_ms[k] - fa_ms[k] for k in common_ids])
                        if 'total_observed_cpu_seconds' in t:
                            shim_cpu = sum(x['cpu_seconds'] or 0 for x in ts.get('process_resource', {}).values())
                            pc['observed_cpu_seconds_delta_vs_shim'] = t['total_observed_cpu_seconds'] - shim_cpu
                pairs.append(pc)
                if t.get('comparison_status') != 'VALID_FORMAL_TRIAL' or arm['baseline'] not in DEFENSES:
                    continue
                if e.get('status') != 'PASS' or pc['status'] != 'PASS_SCHEDULE':
                    t.update(comparison_status='INVALID_COMPARISON', policy_status_before_pair_gate=t['policy_status'],
                             policy_status='UNKNOWN', invalid_reasons=['REPETITION_B0_SHIM_OR_MATCHED_SCHEDULE_NOT_PASS'])
                elif not t.get('expected_rejection'):
                    diff = pc.get('final_joint_difference_rad')
                    if diff is None or diff > .02:
                        t['policy_violations'] = sorted(set(t['policy_violations'] + ['ALLOWED_PATH_FINAL_JOINT_OVER_0_02RAD']))
                        t['policy_status'] = 'FAIL_POLICY'
    counts = Counter(t['comparison_status'] for t in trials)
    complete = counts.get('VALID_FORMAL_TRIAL', 0) == len(schedule) and all(x.get('status') == 'PASS' for x in eq)
    return dict(status='D4_FORMAL_COMPLETE' if complete else 'D4_FORMAL_PARTIAL_OR_INVALID',
                formal_configuration='XRROS-S4B-D4F1-1.0.0', protocol='XRROS-S4-1.0.0', seed=20260922,
                trials=trials, comparison_counts=dict(counts),
                policy_counts={f'{a}|{r}|{c}|{p}|{s}': n for (a, r, c, p, s), n in Counter(
                    (t['arm'], t['regime'], t['condition'], t['profile'], t['policy_status']) for t in trials).items()},
                b0_shim_equivalence=eq, matched_source_schedule_pairs=pairs,
                exact_internal_added_gate_transport_latency='UNKNOWN',
                exact_source_to_specific_joint_parent='UNKNOWN_INTERVAL_ONLY',
                setup_trials_not_formal='CP18 D4Q1 qualification raw excluded')


def load_schedule():
    with (ROOT / 'schedule.csv').open(newline='') as f:
        schedule = list(csv.DictReader(f))
    assert [int(x['order']) for x in schedule] == list(range(1, len(schedule) + 1))
    assert all(x['case'] == 'D4' and int(x['seed']) == 20260922 for x in schedule)
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
