#!/usr/bin/env python3
"""Prospective Docker D4-L post-gate delivery-delay formal scorer (XRROS-S4B-D4LF1-1.0.0).

Validity: frozen D4LQ2 setup audit per attempt (fixture/stamps, FIFO delivery,
idle-time reconnect rule, ACK+clock, delay-scaled ticks, CPU/RSS, exact
callbacks on the recorded stamp, B2 association, drain); motion is a validity
gate only for B0/shim. B0/shim pair (5 ms, .02 rad) per repetition/delay and
each arm's schedule vs shim (5 ms) gate defense arms.

Policy (XRROS-S4-1.0.0 sections 5/8, D4-L "judge age at consumer as well as
each gate"). Source age = time - independently recorded stamp; expected accept
iff -5 ms <= age <= F; +/-1 ms band = UNKNOWN. Prospectively (learned from D4's
post-freeze finding) the expectation is PER DECISION:
* gate level: every decision at the defense judged; rejection is expected once
  any decision is clearly over budget; local trigger = max(arrival at the
  defense, stamp + F + 1 ms) of that sample; decision and neutralization
  request <= 50 ms after it, no controller output after +300 ms, settled by +1 s;
  a stop caused solely by an in-band rejection -> UNKNOWN_BOUNDARY_STRADDLE;
* consumer level: source age at each sample's FIRST exact Servo callback; a
  nonzero command whose sample was clearly over budget there is
  OVER_BUDGET_SAMPLE_REACHED_CONSUMER (for B1 attributed to the architectural
  placement effect: post-decision delay is invisible to a source gate);
* acceptance: zero false rejection, no stop, exact callbacks 36..55, motion,
  final joints <= .02 rad vs shim.
B1 I_FULL runs once per delay (F250): its decisions see age ~0, so its runtime is
profile-invariant; F100/F500 consumer-level results are computed offline from
the same run and flagged INFERRED, and the inference is refused if any B1
decision age exceeds 99 ms. I_NATIVE: UNOBSERVABLE (observable false rejection
or allowed-path failure is FAIL). Common stop adapter never credited to native
ROSMonitoring.
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
Q = ROOT.parent / 's4b_cp20_d4lq2_20260928T104414Z'
sys.path.insert(0, str(Q / 'analysis'))
import d4_setup_audit as setup  # noqa: E402  frozen D4LQ2 setup audit
from d4_age import PROFILES, expected  # noqa: E402

rows = setup.rows
source_origin = setup.source_origin
TELEOP = {f'docker:{i}' for i in range(20, 56)}
ELIGIBLE = {f'docker:{i}' for i in range(36, 56)}
U = 1_000_000
DECISION_MS, CONTINUE_MS, SETTLE_MS = 50.0, 300.0, 1000.0
DEFENSES = ('b1', 'b2', 'b2c', 'b3')
DELAYS = ['L000', 'L050', 'L150', 'L350', 'L750']
FULL_CELLS = {'L000': ['F100'], 'L050': ['F100'], 'L150': ['F100', 'F250'],
              'L350': ['F250', 'F500'], 'L750': ['F500']}
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
    out = []
    if baseline == 'b1':
        for g in rows(root / 'gate_verdict.jsonl'):
            if g.get('kind') is None and g.get('sample_id') in TELEOP:
                out.append(dict(sample_id=g['sample_id'], t=g['decision_monotonic_ns'],
                                allowed=g['allowed'] is True, defense_stamp=g.get('source_timestamp_ns')))
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
                            defense_stamp=(origin or {}).get('source_timestamp_ns')))
    elif baseline == 'b3':
        for x in lineage:
            if x.get('kind') == 'b3_mapper_verdict' and x.get('event_kind') is None:
                o = source_origin(x.get('source_origin')) or {}
                if o.get('sample_id') in TELEOP:
                    out.append(dict(sample_id=o['sample_id'], t=x['monotonic_ns'],
                                    allowed=x.get('verdict') is True, defense_stamp=o.get('source_timestamp_ns')))
    for d in out:
        stamp = sent_by_id[d['sample_id']]['source_timestamp_ns']
        if regime == 'full' and d['defense_stamp'] != stamp:
            raise Invalid('SOURCE_STAMP_NOT_PRESERVED_TO_DEFENSE')
        d['source_age_ns'] = d['t'] - stamp
    return sorted(out, key=lambda d: d['t'])


def consumer_level(callback, F):
    """Source age at each sample's FIRST exact Servo callback (cached repeats reported only)."""
    first = {}
    for c in callback['joined']:
        if c['sample_id'] in TELEOP and (c['sample_id'] not in first or c['callback_entry_ns'] < first[c['sample_id']]['callback_entry_ns']):
            first[c['sample_id']] = c
    over = [c for c in first.values() if c['nonzero'] and expected(c['source_age_at_callback_ms'] * 1e6, F) is False]
    band = [c for c in first.values() if c['nonzero'] and expected(c['source_age_at_callback_ms'] * 1e6, F) is None]
    cached_over = sum(1 for c in callback['joined'] if c['nonzero'] and c['sample_id'] in TELEOP
                      and expected(c['source_age_at_callback_ms'] * 1e6, F) is False) - len(over)
    ages = [c['source_age_at_callback_ms'] for c in first.values()]
    return dict(over_budget_samples_reached_consumer=len(over), in_band_samples_at_consumer=len(band),
                cached_repeat_over_budget_callbacks=cached_over,
                first_callback_source_age_ms=dict(min=min(ages, default=None), max=max(ages, default=None)))


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


def gate_policy(root, baseline, F, judged, rx, sent_by_id, capture_end, callback, mv):
    """Per-decision gate-level policy for one profile F."""
    exp = [(d, expected(d['source_age_ns'], F)) for d in judged]
    false_accept = sum(1 for d, e in exp if e is False and d['allowed'])
    false_reject = sum(1 for d, e in exp if e is True and not d['allowed'])
    rejects = [d for d in judged if not d['allowed']]
    clear = [d for d, e in exp if e is False]
    t_trig = None
    if clear:
        s = clear[0]['sample_id']
        stamp = sent_by_id[s]['source_timestamp_ns']
        arrival = sent_by_id[s]['sample_ns'] if baseline == 'b1' else (rx.get(s) or [None])[0]
        if arrival is None:
            raise Invalid('FIRST_OVER_BUDGET_ARRIVAL_UNOBSERVED')
        t_trig = max(arrival, stamp + F + U)
    neutral = neutralization(root, t_trig)
    violations = []
    straddle = False
    if false_reject:
        violations.append('FALSE_REJECTION_OF_FRESH_TELEOP_INPUT')
    if false_accept:
        violations.append('FALSE_ACCEPTANCE_OF_OVER_BUDGET_INPUT')
    decision_ms = settled = None
    if t_trig is not None:
        before = [d for d in rejects if d['t'] < t_trig]
        if before and all(expected(d['source_age_ns'], F) is None for d in before):
            straddle = True   # stop caused by an in-band rejection before the clear trigger
        clear_rejects = [d for d in rejects if d['t'] >= t_trig - U]
        decision_ms = None if not clear_rejects else (clear_rejects[0]['t'] - t_trig) / 1e6
        if not straddle:
            if decision_ms is None or decision_ms > DECISION_MS:
                violations.append('LOCAL_DECISION_ABSENT_OR_OVER_50MS')
            if neutral['request_ns'] is None:
                violations.append('NO_EXPLICIT_NEUTRALIZATION_REQUEST')
            else:
                if neutral['request_delay_ms'] < -U / 1e6:
                    violations.append('PREMATURE_NEUTRALIZATION_REQUEST')
                elif neutral['request_delay_ms'] > DECISION_MS:
                    violations.append('NEUTRALIZATION_REQUEST_OVER_50MS')
        if neutral['request_ns'] is not None and (neutral['stop_failed'] or not neutral['reply_ok']
                                                  or not neutral['controller_zero']):
            violations.append('STOP_REPLY_OR_CONTROLLER_ZERO_ABSENT')
        late = [r['monotonic_ns'] for r in rows(root / 'topics.jsonl')
                if r.get('topic') == '/joint_group_velocity_controller/commands'
                and t_trig + CONTINUE_MS * 1e6 < r['monotonic_ns'] <= capture_end
                and any(abs(v) > 1e-6 for v in r['payload']['data'])]
        if late:
            violations.append('CONTROLLER_NONZERO_AFTER_TRIGGER_PLUS_300MS')
        settled = settle_after(root, t_trig)
        if settled is None or settled > SETTLE_MS:
            violations.append('GAZEBO_NOT_SETTLED_BY_TRIGGER_PLUS_1S')
    else:
        if rejects and all(expected(d['source_age_ns'], F) is None for d in rejects):
            straddle = neutral['request_ns'] is not None
        elif neutral['request_ns'] is not None:
            violations.append('UNEXPECTED_NEUTRALIZATION_WITH_NO_OVER_BUDGET_INPUT')
        if not straddle:
            if not false_reject and not ELIGIBLE <= {c['sample_id'] for c in callback['joined']}:
                raise Invalid('ACTIVE_SOURCE_TO_SERVO_CALLBACK_INCOMPLETE')
            if mv['max_excursion_rad'] is None or mv['max_excursion_rad'] <= .01:
                violations.append('ADMITTED_MOTION_ABSENT')
    consumer = consumer_level(callback, F)
    if consumer['over_budget_samples_reached_consumer']:
        violations.append('OVER_BUDGET_SAMPLE_REACHED_CONSUMER' +
                          ('_PLACEMENT_EFFECT_POST_DECISION_DELAY' if baseline == 'b1' else ''))
    return dict(expected_rejection=t_trig is not None, local_trigger_ns=t_trig, local_decision_delay_ms=decision_ms,
                false_accept_count=false_accept, false_reject_count=false_reject,
                unknown_band_decisions=sum(1 for _, e in exp if e is None),
                rejected_decisions=len(rejects), boundary_straddle=straddle, neutralization=neutral,
                gazebo_settled_after_trigger_ms=settled, consumer_level=consumer,
                violations=sorted(set(violations)))


def audit_trial(row, root):
    baseline, regime, mode, delay = row['baseline'], row['regime'], row['mode'], row['delay']
    base = dict(trial_id=row['trial_id'], attempt=root.name, repetition=int(row['repetition']),
                arm=baseline, regime=regime, delay=delay, profile=row['profile'])
    ev = setup.inspect(root, baseline, regime, 'A000', expect_motion=baseline in ('b0', 'shim'), delay=delay)
    if ev['status'] != 'MEASUREMENT_QUALIFIED':
        return dict(base, comparison_status='INVALID_COMPARISON', policy_status='UNKNOWN',
                    invalid_reasons=ev.get('issues', []))
    try:
        sent = rows(root / 'sent.jsonl')
        sent_by_id = {f'docker:{r["index"]}': r for r in sent}
        capture_end = next(x['monotonic_ns'] for x in rows(root / 'events.jsonl') if x.get('kind') == 'capture_end')
        mv = ev['motion']
        common = dict(base, comparison_status='VALID_FORMAL_TRIAL', motion=mv, delivery=ev.get('delivery'),
                      process_resource=resources(root))
        callback = setup.callback_join(root) if mode != 'b0' else None
        first_cb = {}
        if callback:
            for c in callback['joined']:
                if c['sample_id'] in ELIGIBLE:
                    first_cb[c['sample_id']] = min(first_cb.get(c['sample_id'], 1e18), c['sample_to_callback_ms'])
        common.update(first_callback_latency_by_source_ms=first_cb,
                      first_callback_latency_p95_ms=percentile(list(first_cb.values())))
        if mode in ('b0', 'shim'):
            extra = {} if callback is None else dict(consumer_level_F250=consumer_level(callback, PROFILES['F250']))
            return dict(common, policy_status='ORIGINAL_CONTROL_NOT_SCORED' if mode == 'b0'
                        else 'OBSERVATIONAL_SHIM_NOT_SCORED', **extra)
        lineage = rows(root / 'lineage.jsonl')
        dec = decisions(root, baseline, regime, lineage, sent_by_id)
        if {d['sample_id'] for d in dec} != TELEOP:
            raise Invalid('TELEOP_DECISION_EXACT_COVERAGE_INCOMPLETE')
        rx = {}
        for x in lineage:
            if x.get('kind') == 'source_received':
                rx.setdefault((x.get('metadata') or {}).get('sample_id'), []).append(x['receiver_receipt_monotonic_ns'])
        F = PROFILES[row['profile']]
        if regime == 'native':
            consumer = consumer_level(callback, F)
            false_reject = sum(1 for d in dec if not d['allowed'])
            viol = ['FALSE_REJECTION_OF_TELEOP_INPUT'] if false_reject else []
            return dict(common, policy_status='FAIL_POLICY' if viol else 'UNOBSERVABLE', policy_violations=viol,
                        freshness_observable_to_defense=False, consumer_level_by_analyzer_F250=consumer,
                        consumer_level_by_analyzer_F100=consumer_level(callback, PROFILES['F100']),
                        consumer_level_by_analyzer_F500=consumer_level(callback, PROFILES['F500']))
        gate = gate_policy(root, baseline, F, dec, rx, sent_by_id, capture_end, callback, mv)
    except Invalid as exc:
        return dict(base, comparison_status='INVALID_COMPARISON', policy_status='UNKNOWN', invalid_reasons=[str(exc)])
    except (KeyError, IndexError, ValueError, TypeError, FileNotFoundError, StopIteration, json.JSONDecodeError) as exc:
        return dict(base, comparison_status='INVALID_COMPARISON', policy_status='UNKNOWN',
                    invalid_reasons=['EVIDENCE_PARSE_ERROR'], evidence_error=f'{type(exc).__name__}: {exc}')
    status = ('UNKNOWN_BOUNDARY_STRADDLE' if gate['boundary_straddle'] and not gate['violations']
              else 'FAIL_POLICY' if gate['violations'] else 'PASS_POLICY')
    out = dict(common, policy_status=status, policy_violations=gate['violations'],
               freshness_observable_to_defense=True, freshness_ns=F, gate=gate,
               decision_source_age_ms=dict(min=min(d['source_age_ns'] for d in dec) / 1e6,
                                           max=max(d['source_age_ns'] for d in dec) / 1e6),
               receiver_receipt_source_age_ms=dict(
                   min=min(rx[s][0] - sent_by_id[s]['source_timestamp_ns'] for s in TELEOP if s in rx) / 1e6,
                   max=max(rx[s][0] - sent_by_id[s]['source_timestamp_ns'] for s in TELEOP if s in rx) / 1e6),
               total_observed_cpu_seconds=sum(x['cpu_seconds'] or 0 for x in common['process_resource'].values()),
               monitor_internal_post_verdict_publish_time='UNKNOWN',
               exact_source_to_specific_servo_output_controller_joint='UNKNOWN_INTERVAL_ONLY')
    if baseline == 'b1':
        max_gate_age = max(d['source_age_ns'] for d in dec)
        invariant = max_gate_age <= 99_000_000
        inferred = {}
        for name in ('F100', 'F500'):
            if invariant:
                g = gate_policy(root, 'b1', PROFILES[name], dec, rx, sent_by_id, capture_end, callback, mv)
                inferred[name] = dict(status='INFERRED_' + ('FAIL_POLICY' if g['violations'] else 'PASS_POLICY'),
                                      violations=g['violations'], consumer_level=g['consumer_level'])
            else:
                inferred[name] = dict(status='NOT_INFERABLE_B1_DECISION_AGE_OVER_99MS')
        out.update(b1_profile_invariant_runtime=invariant, b1_max_gate_decision_age_ms=max_gate_age / 1e6,
                   b1_inferred_other_profiles=inferred)
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
                    regime=row['regime'], delay=row['delay'], profile=row['profile'],
                    comparison_status='BLOCKED_MEASUREMENT' if tried else 'NOT_RUN',
                    policy_status='NOT_SCORED', setup_attempts=tried)
    out = audit_trial(row, root)
    out['setup_attempts'] = tried
    return out


def not_run_registered():
    """Registered D4-L combinations deliberately excluded by the scoped design."""
    out = []
    for delay in DELAYS:
        for arm in ('b2', 'b2c', 'b3'):
            for profile in PROFILES:
                if profile not in FULL_CELLS[delay]:
                    out.append(dict(arm=arm, regime='full', delay=delay, profile=profile,
                                    status='NOT_RUN_INFERRED_BY_MONOTONICITY'))
        for profile in ('F100', 'F500'):
            out.append(dict(arm='b1', regime='full', delay=delay, profile=profile,
                            status='NOT_RUN_B1_PROFILE_INVARIANT_OFFLINE_INFERENCE'))
        if delay != 'L750':
            for arm in ('b1', 'b2', 'b2c', 'b3'):
                out.append(dict(arm=arm, regime='native', delay=delay, profile='any',
                                status='NOT_RUN_SCOPED_UNOBSERVABLE_BY_CONSTRUCTION'))
    return out


def summarize(schedule):
    trials = [score_row(r) for r in schedule]
    by_id = {t['trial_id']: t for t in trials}
    eq, pairs = [], []
    for rep in range(1, 6):
        for delay in DELAYS:
            group = [r for r in schedule if int(r['repetition']) == rep and r['delay'] == delay]
            shim = next(r for r in group if r['baseline'] == 'shim')
            b0 = next(r for r in group if r['baseline'] == 'b0')
            ts, tb = by_id[shim['trial_id']], by_id[b0['trial_id']]
            e = (setup.pair(RAW / tb['attempt'], RAW / ts['attempt'], 'A000')
                 if 'attempt' in ts and 'attempt' in tb else dict(status='NOT_RUN'))
            eq.append(dict(e, repetition=rep, delay=delay))
            for arm in group:
                if arm is shim or arm is b0:
                    continue
                t = by_id[arm['trial_id']]
                pc = dict(pair=[shim['trial_id'], arm['trial_id']], status='NOT_RUN')
                if 'attempt' in ts and 'attempt' in t:
                    a, b = RAW / ts['attempt'], RAW / t['attempt']
                    sa, ea = setup.fixture(a, 'A000')
                    sb, eb = setup.fixture(b, 'A000')
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
                            pc['paired_source_to_first_callback_delta_p95_ms'] = percentile(
                                [fb_ms[k] - fa_ms[k] for k in sorted(set(fa_ms) & set(fb_ms))])
                        if 'total_observed_cpu_seconds' in t or t.get('process_resource'):
                            cpu = lambda x: sum(v['cpu_seconds'] or 0 for v in x.get('process_resource', {}).values())
                            pc['observed_cpu_seconds_delta_vs_shim'] = cpu(t) - cpu(ts)
                pairs.append(pc)
                if t.get('comparison_status') != 'VALID_FORMAL_TRIAL' or arm['baseline'] not in DEFENSES:
                    continue
                if e.get('status') != 'PASS' or pc['status'] != 'PASS_SCHEDULE':
                    t.update(comparison_status='INVALID_COMPARISON', policy_status_before_pair_gate=t['policy_status'],
                             policy_status='UNKNOWN', invalid_reasons=['REPETITION_B0_SHIM_OR_MATCHED_SCHEDULE_NOT_PASS'])
                elif t.get('regime') == 'full' and not t['gate']['expected_rejection'] \
                        and t['policy_status'] != 'UNKNOWN_BOUNDARY_STRADDLE':
                    diff = pc.get('final_joint_difference_rad')
                    if diff is None or diff > .02:
                        t['policy_violations'] = sorted(set(t['policy_violations'] + ['ALLOWED_PATH_FINAL_JOINT_OVER_0_02RAD']))
                        t['policy_status'] = 'FAIL_POLICY'
    counts = Counter(t['comparison_status'] for t in trials)
    complete = counts.get('VALID_FORMAL_TRIAL', 0) == len(schedule) and all(x.get('status') == 'PASS' for x in eq)
    return dict(status='D4L_SCOPED_FORMAL_COMPLETE' if complete else 'D4L_SCOPED_FORMAL_PARTIAL_OR_INVALID',
                formal_configuration='XRROS-S4B-D4LF1-1.0.0 (scoped)', protocol='XRROS-S4-1.0.0', seed=20260922,
                trials=trials, comparison_counts=dict(counts),
                policy_counts={f'{a}|{r}|{d}|{p}|{s}': n for (a, r, d, p, s), n in Counter(
                    (t['arm'], t['regime'], t['delay'], t['profile'], t['policy_status']) for t in trials).items()},
                b0_shim_equivalence=eq, matched_source_schedule_pairs=pairs,
                registered_not_run=not_run_registered(),
                exact_internal_added_gate_transport_latency='UNKNOWN',
                exact_source_to_specific_joint_parent='UNKNOWN_INTERVAL_ONLY',
                setup_trials_not_formal='D4LQ1/D4LQ2 qualification raw excluded')


def load_schedule():
    with (ROOT / 'schedule.csv').open(newline='') as f:
        schedule = list(csv.DictReader(f))
    assert [int(x['order']) for x in schedule] == list(range(1, len(schedule) + 1))
    assert all(x['case'] == 'D4L' and int(x['seed']) == 20260922 for x in schedule)
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
