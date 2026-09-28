#!/usr/bin/env python3
"""Prospective Docker D3 moving source-silence formal scorer (XRROS-S4B-D3F1-1.0.0).

Layer 1 (validity) calls the UNCHANGED frozen Q6 setup function
``d3_qualification_audit.inspect``/``pair`` on each formal raw root, then adds
formal completeness checks. Layer 2 (policy) applies the XRROS-S4-1.0.0 rules:

* local trigger = last REAL source receipt at the defense location + 250 ms;
* decision and neutralization request <= 50 ms after that trigger;
* no nonzero controller command after trigger + 300 ms;
* Gazebo settled (|v| < .001 rad/s, drift < .0001 rad over .5 s) by trigger + 1 s;
* no false rejection among valid steady-active source IDs docker:36..55;
* pre-fault allowed-path joint position vs same-repetition shim <= .02 rad.

Seven mechanisms are kept separate and never credited to one another:
source-side detection (B1), official ROSMonitoring verdict (B2/B2c), B2-composed
health/watchdog action, receiving-side detection (B3), original receiver
timeout, existing Servo timeout, common stop adapter actuation. Settling after
the original timeout alone is never a defense PASS. Source->Servo callback is an
exact event join; controller and joints are interval observations only.
"""
import argparse
import csv
import json
import math
import sys
import tempfile
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / 'raw'
Q6 = ROOT.parent / 's4b_cp16_d3q6_20260928T032320Z'
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Q6 / 'analysis'))
import d3_qualification_audit as q6  # noqa: E402  frozen Q6 setup analyzer
from trajectory_pair import joint_at_source_index  # noqa: E402  byte-identical D2 copy

rows = q6.rows
source_origin = q6.source_origin
ARM = q6.ARM
ELIGIBLE = {f'docker:{i}' for i in range(36, 56)}
LAST_REAL = 'docker:55'
RESUME = 'docker:76'
LIMIT_NS = 250_000_000
DECISION_MS = 50.0
CONTINUE_MS = 300.0
SETTLE_MS = 1000.0
DEFENSES = ('b1', 'b2', 'b2c', 'b3')
RECEIVER_STAGES = ('receiver', 'receiver_envelope', 'receiver_native_monitor_input')
ATTEMPT_SUFFIXES = ('', '_setup02', '_setup03')
TRIGGER_ATTRIBUTION = {
    'B1_POLICY_REJECT': 'B1_SOURCE_SIDE_SILENCE_DETECTION',
    'B2_ORACLE_POLICY_REJECT': 'OFFICIAL_ROSMONITORING_VERDICT_CURRENTLY_FALSE',
    'B2_MONITOR_HEALTH': 'B2_COMPOSED_MONITOR_HEALTH_UNKNOWN_OR_ERROR',
    'B3_POLICY_REJECT': 'B3_RECEIVING_SIDE_SILENCE_DETECTION',
    'B1_VERDICT_HEARTBEAT_MISSING': 'COMMON_WATCHDOG_HEARTBEAT',
    'B2_VERDICT_HEARTBEAT_MISSING': 'B2_COMPOSED_COMMON_WATCHDOG_HEARTBEAT',
    'B3_VERDICT_HEARTBEAT_MISSING': 'COMMON_WATCHDOG_HEARTBEAT',
}


class Invalid(Exception):
    """Mandatory formal evidence incomplete: INVALID_COMPARISON, policy UNKNOWN."""


def percentile(values, p=.95):
    if not values:
        return None
    ordered = sorted(values)
    return ordered[max(0, math.ceil(len(ordered) * p) - 1)]


def with_q6_name(roots, call):
    """Run a frozen Q6 function on formal roots via temporary Q6-style names."""
    with tempfile.TemporaryDirectory() as tmp:
        for q6_name, root in roots.items():
            (Path(tmp) / q6_name).symlink_to(Path(root).resolve(), target_is_directory=True)
        saved = q6.RAW
        q6.RAW = Path(tmp)
        try:
            return call()
        finally:
            q6.RAW = saved


def setup_evidence(root, baseline, regime):
    name = f'docker_{baseline}_{regime}_cp16d3setup01'
    result = with_q6_name({name: root}, lambda: q6.inspect(baseline, regime))
    result['trial'] = Path(root).name
    result['setup_function'] = 'Q6 d3_qualification_audit.inspect (frozen, unchanged)'
    return result


def b0_shim_pair(b0_root, shim_root):
    names = {'docker_b0_full_cp16d3setup01': b0_root,
             'docker_shim_full_cp16d3setup01': shim_root}
    return with_q6_name(names, lambda: q6.pair(*names))


def capture_window(root):
    events = rows(root / 'events.jsonl')
    barrier = [x['start_monotonic_ns'] for x in events if x.get('kind') == 'barrier_release']
    end = [x['monotonic_ns'] for x in events if x.get('kind') == 'capture_end']
    if len(barrier) != 1 or len(end) != 1:
        raise Invalid('CAPTURE_WINDOW_EVENTS_NOT_UNIQUE')
    return barrier[0], end[0]


def unique(items, reason):
    if len(items) != 1:
        raise Invalid(reason)
    return items[0]


def receipts(root, lineage):
    """Exact last-real and resume receipts; never a nearest-time join."""
    sent = rows(root / 'sent.jsonl')
    by_index = {x['index']: x for x in sent}
    send55 = by_index[55].get('send_ns')
    send76 = by_index[76].get('send_ns')
    if send55 is None or send76 is None or by_index[55].get('sent') is not True:
        raise Invalid('LAST_REAL_OR_RESUME_SEND_MISSING')
    received = {}
    for item in lineage:
        if item.get('kind') == 'source_received':
            sid = (item.get('metadata') or {}).get('sample_id')
            received.setdefault(sid, []).append(item['receiver_receipt_monotonic_ns'])
    rx = {}
    for sid in (LAST_REAL, RESUME):
        values = received.get(sid, [])
        rx[sid] = unique(values, f'RECEIVER_RECEIPT_NOT_UNIQUE_{sid}')
    return dict(send55=send55, send76=send76, rx55=rx[LAST_REAL], rx76=rx[RESUME])


def detection(root, baseline, regime, lineage, t_local, resume_ns):
    """First explicit silence decision of the tested defense, if any."""
    decisions, tracker = [], []   # tracker: (eval_ns, last_sample_id, trigger_ns, genuine_count)
    observable = True
    official = None
    if baseline == 'b1':
        for g in rows(root / 'gate_verdict.jsonl'):
            if g.get('kind') != 'b1_source_silence_tick':
                continue
            tracker.append((g['decision_monotonic_ns'], g.get('parent_sample_id'),
                            g.get('trigger_monotonic_ns'), None))
            if g.get('allowed') is False:
                decisions.append(dict(t=g['decision_monotonic_ns'], tick_id=g.get('tick_id'),
                                      reported_trigger_ns=g.get('trigger_monotonic_ns')))
        for t in rows(root / 'd3_gate_ticks.jsonl'):
            if t.get('state') == 'SOURCE_SILENCE':
                tracker.append((t['tick_monotonic_ns'], t.get('last_sample_id'), t.get('trigger_ns'),
                                t.get('genuine_receipt_count')))
        mechanism = 'B1_SOURCE_SIDE_SILENCE_DETECTION'
    elif baseline in ('b2', 'b2c'):
        ticks = [p for p in rows(root / 'property.jsonl') if p.get('event_kind') == 'tick']
        if len(ticks) != 300:
            raise Invalid('ORACLE_TICK_PROPERTY_COVERAGE')
        observable = any(p.get('reason') not in ('UNOBSERVABLE', 'UNOBSERVABLE_SOURCE_RECEIPT_I_NATIVE')
                         for p in ticks)
        status = [s for s in rows(root / f'monitor_{regime}_status.jsonl')
                  if s.get('status') == 'event' and s.get('interface') == '/s4b/d3/tick']
        status_by = {}
        for s in status:
            status_by.setdefault(json.loads(s['event']['data'])['tick_id'], []).append(s)
        for p in ticks:
            if p.get('reason') == 'SOURCE_SILENCE' or p.get('safe') is False:
                tracker.append((p['monotonic_ns'], p.get('sample_id'),
                                p.get('source_timeout_trigger_ns'), None))
            if p.get('safe') is False:
                decisions.append(dict(t=p['monotonic_ns'], tick_id=p['tick_id'],
                                      reported_trigger_ns=p.get('source_timeout_trigger_ns')))
        if decisions:
            first = min(decisions, key=lambda d: d['t'])
            match = status_by.get(first['tick_id'], [])
            if len(match) != 1:
                raise Invalid('OFFICIAL_STATUS_FOR_FIRST_SILENCE_TICK_NOT_UNIQUE')
            official = dict(tick_id=first['tick_id'], decision=match[0].get('decision'),
                            verdict_raw=match[0].get('verdict_raw'),
                            status_wall_time=match[0].get('time'),
                            status_clock='WALL_TIME_NOT_SUBTRACTED_FROM_MONOTONIC')
            if official['decision'] != 'blocked' or official['verdict_raw'] != 'currently_false':
                raise Invalid('ORACLE_PROPERTY_AND_OFFICIAL_STATUS_DISAGREE')
        mechanism = 'OFFICIAL_ROSMONITORING_TLORACLE_VERDICT'
    elif baseline == 'b3':
        ticks = [x for x in lineage if x.get('kind') == 'b3_silence_tick']
        if len(ticks) != 300:
            raise Invalid('B3_SILENCE_TICK_COVERAGE')
        observable = any((x.get('state') or {}).get('state') != 'UNOBSERVABLE' for x in ticks)
        for x in ticks:
            state = x.get('state') or {}
            if state.get('state') == 'SOURCE_SILENCE':
                tracker.append((x['monotonic_ns'], state.get('last_sample_id'), state.get('trigger_ns'),
                                state.get('genuine_receipt_count')))
        for x in lineage:
            if (x.get('kind') == 'b3_mapper_verdict' and x.get('event_kind') == 'health_tick'
                    and x.get('verdict') is False):
                decisions.append(dict(t=x['monotonic_ns'], tick_id=x.get('tick_id'),
                                      reported_trigger_ns=x.get('trigger_monotonic_ns')))
        mechanism = 'B3_RECEIVING_SIDE_SILENCE_DETECTION'
    else:
        return dict(mechanism='NONE_CONTROL_ARM', observed=False, observable=False)
    tracker_issues = []
    for eval_ns, sid, trig, count in tracker:
        if t_local <= eval_ns < resume_ns:
            if sid != LAST_REAL or trig != t_local:
                tracker_issues.append('SILENCE_TRACKER_NOT_BOUND_TO_LAST_REAL_SOURCE')
            if count is not None and count != 56:
                tracker_issues.append('SILENCE_TRACKER_COUNTED_NON_SOURCE_AS_RECEIPT')
    for d in decisions:
        if d['reported_trigger_ns'] is not None and d['reported_trigger_ns'] != t_local:
            tracker_issues.append('SILENCE_DECISION_TRIGGER_NOT_LAST_REAL_RECEIPT_PLUS_250MS')
    first = min(decisions, key=lambda d: d['t']) if decisions else None
    return dict(mechanism=mechanism, observable=observable, observed=first is not None,
                first_decision_ns=first['t'] if first else None,
                first_decision_tick_id=first['tick_id'] if first else None,
                decision_delay_ms=None if first is None else (first['t'] - t_local) / 1e6,
                premature_decisions=sum(d['t'] < t_local for d in decisions),
                negative_decisions=len(decisions), official_status=official,
                tracker_issues=sorted(set(tracker_issues)))


def neutralization(root, baseline, t_local):
    events = rows(root / 'stop_adapter.jsonl')
    requests = [x for x in events if x.get('kind') == 'stop_request']
    replies = [x for x in events if x.get('kind') == 'stop_reply']
    zeros = [x for x in events if x.get('kind') == 'controller_zero']
    failed = [x for x in events if x.get('kind') == 'stop_failed']
    first = min(requests, key=lambda x: x['monotonic_ns']) if requests else None
    source = first.get('source') if first else None
    return dict(adapter_present=(root / 'stop_adapter.ready').exists(),
                request_ns=first['monotonic_ns'] if first else None,
                request_delay_ms=None if first is None else (first['monotonic_ns'] - t_local) / 1e6,
                request_trigger_source=source,
                detection_attribution=TRIGGER_ATTRIBUTION.get(source, source),
                actuation_attribution='COMMON_STOP_ADAPTER_NOT_NATIVE_ROSMONITORING' if first else None,
                reply_ok=bool(replies) and all('success=True' in str(x.get('reply')) for x in replies),
                controller_zero=bool(zeros), stop_failed=bool(failed), request_count=len(requests))


def original_timeout(lineage, rx55, rx76):
    """First original receiver stale_timeout neutral after the last real receipt."""
    for item in sorted((x for x in lineage if x.get('kind') == 'publish'
                        and x.get('stage') in RECEIVER_STAGES), key=lambda x: x['monotonic_ns']):
        origin = item.get('selected_origin') if item.get('stage') == 'receiver_envelope' else item.get('parent')
        if (rx55 < item['monotonic_ns'] < rx76 and isinstance(origin, dict)
                and origin.get('origin') == 'ORIGINAL_NEUTRAL' and origin.get('reason') == 'stale_timeout'):
            return item['monotonic_ns']
    return None


def receiver_mapper_completeness(lineage, baseline):
    """Original sources AND original neutrals must each have one exact Mapper consume."""
    if baseline in ('b2', 'b2c'):
        stage = 'stripper_restored'  # upstream of Stripper is audited by d3_monitor_audit
    else:
        stage = 'receiver'
    pubs = [x for x in lineage if x.get('kind') == 'publish' and x.get('stage') == stage]
    consumed = Counter((x.get('exact_parent') or {}).get('command_id') for x in lineage
                       if x.get('kind') == 'consume' and x.get('stage') == 'mapper')
    missing = [x['command_id'] for x in pubs if consumed[x['command_id']] != 1]
    neutral = sum(1 for x in pubs if not source_origin(x.get('parent')))
    return dict(publications=len(pubs), original_neutral_publications=neutral,
                missing=missing[:20], missing_count=len(missing))


def eligible_verdicts(root, baseline, regime, lineage):
    """Exact per-source normal-phase verdicts for docker:36..55; never time joins."""
    verdicts = {}
    if baseline == 'b1':
        for g in rows(root / 'gate_verdict.jsonl'):
            if g.get('kind') is None and g.get('sample_id') in ELIGIBLE:
                verdicts.setdefault(g['sample_id'], []).append(g.get('allowed') is True)
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
            if sid in ELIGIBLE:
                match = props.get(pub.get(key), [])
                if len(match) != 1:
                    raise Invalid('ELIGIBLE_SOURCE_PROPERTY_JOIN_NOT_UNIQUE')
                verdicts.setdefault(sid, []).append(match[0].get('safe') is True)
    elif baseline == 'b3':
        for x in lineage:
            if x.get('kind') == 'b3_mapper_verdict' and x.get('event_kind') is None:
                sid = (source_origin(x.get('source_origin')) or {}).get('sample_id')
                if sid in ELIGIBLE:
                    verdicts.setdefault(sid, []).append(x.get('verdict') is True)
    if set(verdicts) != ELIGIBLE:
        raise Invalid('ELIGIBLE_ACTIVE_VERDICT_EXACT_COVERAGE_INCOMPLETE')
    return sum(not all(v) for v in verdicts.values())


def post_trigger_commands(root, lineage, t_local, capture_end, callback):
    joined = {x['command_id'] for x in callback['joined']}
    cached, restart = Counter(), Counter()
    for pub in lineage:
        if pub.get('kind') != 'publish' or pub.get('stage') != 'bridge_servo_input':
            continue
        if not (t_local <= pub['monotonic_ns'] <= capture_end) or pub['command_id'] not in joined:
            continue
        twist = pub['payload']['twist']
        if not any(abs(twist[k][a]) > 1e-6 for k in ('linear', 'angular') for a in 'xyz'):
            continue
        sid = (source_origin(pub.get('parent')) or {}).get('sample_id')
        index = int(sid.split(':')[1])
        (cached if index <= 55 else restart)[sid] += 1
    controller = [x['monotonic_ns'] for x in rows(root / 'topics.jsonl')
                  if x.get('topic') == '/joint_group_velocity_controller/commands'
                  and t_local <= x['monotonic_ns'] <= capture_end
                  and any(abs(v) > 1e-6 for v in x['payload']['data'])]
    servo_inputs = sorted(x['monotonic_ns'] for x in lineage if x.get('kind') == 'publish'
                          and x.get('stage') == 'bridge_servo_input'
                          and t_local <= x['monotonic_ns'] <= capture_end)
    gaps = [(b - a) / 1e6 for a, b in zip(servo_inputs, servo_inputs[1:])]
    return dict(cached_prior_source_nonzero_servo_callbacks_after_trigger=sum(cached.values()),
                cached_parent_ids=dict(cached),
                post_silence_source_nonzero_servo_callbacks=sum(restart.values()),
                controller_nonzero_after_trigger=len(controller),
                last_nonzero_controller_after_trigger_ms=(
                    0.0 if not controller else (max(controller) - t_local) / 1e6),
                servo_input_publications_after_trigger=len(servo_inputs),
                servo_input_max_gap_after_trigger_ms=max(gaps, default=None))


def resources(root):
    measurement = q6.resources(root)
    lifecycle = q6.lifecycle_trial(root)
    per_label = {label: dict(cpu_percent=m['cpu_percent'], cpu_seconds=m['cpu_seconds'],
                             max_tree_rss_bytes=m['max_tree_rss_bytes'])
                 for label, m in measurement['per_label'].items()}
    per_label['sender'] = dict(cpu_percent=lifecycle.get('cpu_percent'),
                               cpu_seconds=lifecycle.get('cpu_seconds'),
                               max_tree_rss_bytes=lifecycle.get('observed_peak_rss_bytes'))
    return per_label


def settling_displacement(root, t_local, settled_ns):
    joints = []
    for record in rows(root / 'topics.jsonl'):
        if record.get('topic') != '/joint_states':
            continue
        payload = record['payload']
        try:
            joints.append((record['monotonic_ns'],
                           [payload['position'][payload['name'].index(n)] for n in ARM]))
        except (KeyError, ValueError, IndexError):
            continue
    before = [p for t, p in joints if t <= t_local]
    after = [p for t, p in joints if settled_ns is not None and t <= settled_ns]
    if not before or not after:
        return None
    return max(abs(a - b) for a, b in zip(after[-1], before[-1]))


def audit_trial(row, root):
    baseline, regime, mode = row['baseline'], row['regime'], row['mode']
    base = dict(trial_id=row['trial_id'], attempt=root.name, repetition=int(row['repetition']),
                arm=baseline, regime=regime)
    setup = setup_evidence(root, baseline, regime)
    if setup['status'] != 'MEASUREMENT_QUALIFIED':
        return dict(base, comparison_status='INVALID_COMPARISON', policy_status='UNKNOWN',
                    invalid_reasons=setup.get('issues', []), setup_status=setup['status'])
    try:
        barrier, capture_end = capture_window(root)
        if mode == 'b0':
            return dict(base, comparison_status='VALID_FORMAL_TRIAL',
                        policy_status='ORIGINAL_CONTROL_NOT_SCORED', setup_control=setup['control'],
                        original_receiver_timeout='UNOBSERVED_UNINSTRUMENTED_B0',
                        servo_timeout='UNOBSERVABLE_NOT_INSTRUMENTED',
                        process_resource=resources(root))
        lineage = rows(root / 'lineage.jsonl')
        rc = receipts(root, lineage)
        t_local = (rc['send55'] if baseline == 'b1' else rc['rx55']) + LIMIT_NS
        resume_ns = rc['send76'] if baseline == 'b1' else rc['rx76']
        t_original_trigger = rc['rx55'] + LIMIT_NS
        t_orig = original_timeout(lineage, rc['rx55'], rc['rx76'])
        if t_orig is None:
            raise Invalid('ORIGINAL_RECEIVER_TIMEOUT_NEUTRAL_UNOBSERVED')
        completeness = receiver_mapper_completeness(lineage, baseline)
        if completeness['missing_count']:
            raise Invalid('ORIGINAL_EVENT_TO_MAPPER_ASSOCIATION_INCOMPLETE')
        callback = q6.callback_latency(root)
        first = {}
        for item in callback['joined']:
            if item['sample_id'] in ELIGIBLE:
                first[item['sample_id']] = min(first.get(item['sample_id'], float('inf')),
                                               item['sample_to_callback_ms'])
        if set(first) != ELIGIBLE:
            raise Invalid('ACTIVE_SOURCE_TO_SERVO_CALLBACK_INCOMPLETE')
        control = q6.joint_control(root, t_local)
        if not control['max_joint_velocity_before_trigger'] or control['max_joint_velocity_before_trigger'] <= .001:
            raise Invalid('NOT_MOVING_AT_LOCAL_SILENCE_TRIGGER')
        commands = post_trigger_commands(root, lineage, t_local, capture_end, callback)
        det = detection(root, baseline, regime, lineage, t_local, resume_ns)
        neutral = neutralization(root, baseline, t_local)
        false_rejects = eligible_verdicts(root, baseline, regime, lineage) if baseline in DEFENSES else None
        per_label = resources(root)
    except Invalid as exc:
        return dict(base, comparison_status='INVALID_COMPARISON', policy_status='UNKNOWN',
                    invalid_reasons=[str(exc)])
    except (KeyError, IndexError, ValueError, TypeError, FileNotFoundError, StopIteration,
            json.JSONDecodeError) as exc:
        return dict(base, comparison_status='INVALID_COMPARISON', policy_status='UNKNOWN',
                    invalid_reasons=['EVIDENCE_PARSE_ERROR'], evidence_error=f'{type(exc).__name__}: {exc}')

    violations = []
    if baseline in DEFENSES:
        if false_rejects:
            violations.append('NORMAL_ACTIVE_FALSE_REJECTION')
        if det['premature_decisions']:
            violations.append('PREMATURE_SILENCE_DECISION_FALSE_REJECTION')
        violations += det['tracker_issues']
        if not det['observed'] or det['decision_delay_ms'] > DECISION_MS:
            violations.append('LOCAL_DECISION_ABSENT_OR_OVER_50MS')
        if neutral['request_ns'] is None:
            violations.append('NO_EXPLICIT_NEUTRALIZATION_REQUEST')
        else:
            if neutral['request_delay_ms'] < 0:
                violations.append('PREMATURE_NEUTRALIZATION_REQUEST_FALSE_REJECTION')
            elif neutral['request_delay_ms'] > DECISION_MS:
                violations.append('NEUTRALIZATION_REQUEST_OVER_50MS')
            if neutral['stop_failed'] or not neutral['reply_ok'] or not neutral['controller_zero']:
                violations.append('STOP_REPLY_OR_CONTROLLER_ZERO_ABSENT')
        if commands['post_silence_source_nonzero_servo_callbacks']:
            violations.append('NONZERO_COMMAND_FROM_POST_SILENCE_SOURCE_WITHOUT_REARM')
        if commands['last_nonzero_controller_after_trigger_ms'] > CONTINUE_MS:
            violations.append('CONTROLLER_NONZERO_OVER_300MS')
        if control['settled_after_trigger_ms'] is None or control['settled_after_trigger_ms'] > SETTLE_MS:
            violations.append('GAZEBO_NOT_SETTLED_BY_TRIGGER_PLUS_1S')

    if mode == 'shim':
        policy = 'OBSERVATIONAL_SHIM_NOT_SCORED'
    elif not violations:
        policy = 'PASS_POLICY'
    elif (regime == 'native' and baseline in ('b2', 'b2c', 'b3') and not det['observable']
          and not det['observed'] and neutral['request_ns'] is None and not false_rejects
          and not commands['post_silence_source_nonzero_servo_callbacks']):
        # I_NATIVE carries no source-receipt time/ID at this defense's location.
        # Missing information is UNOBSERVABLE, not a method failure (section 6).
        policy = 'UNOBSERVABLE'
    else:
        policy = 'FAIL_POLICY'
    settled_ns = control['settled_ns']
    return dict(base, comparison_status='VALID_FORMAL_TRIAL', policy_status=policy,
                policy_violations=sorted(set(violations)),
                policy_violations_if_information_were_available=(
                    sorted(set(violations)) if policy == 'UNOBSERVABLE' else None),
                last_real_source_send_ns=rc['send55'], last_real_receiver_receipt_ns=rc['rx55'],
                local_silence_trigger_ns=t_local,
                local_trigger_definition=('B1 source-side last real send + 250 ms' if baseline == 'b1'
                                          else 'receiver receipt of docker:55 + 250 ms'),
                source_resume_receipt_ns=resume_ns,
                silence_detection=det, detection_mechanism=det['mechanism'],
                neutralization=neutral,
                original_receiver_timeout_neutral_ns=t_orig,
                original_receiver_timeout_after_its_trigger_ms=(t_orig - t_original_trigger) / 1e6,
                original_receiver_timeout_credited_to_defense=False,
                existing_servo_timeout='UNOBSERVABLE_NOT_INSTRUMENTED_NO_INTERNAL_EVENT_LOG',
                receiver_mapper_association=completeness,
                eligible_active_source_count=20, active_false_reject_count=false_rejects,
                exact_eligible_servo_callback_count=len(first),
                first_callback_latency_by_source_ms=first,
                first_callback_latency_p95_ms=percentile(list(first.values())),
                post_trigger_commands=commands,
                gazebo_moving_before_trigger_rad_s=control['max_joint_velocity_before_trigger'],
                gazebo_settled_after_trigger_ms=control['settled_after_trigger_ms'],
                gazebo_max_joint_displacement_during_settling_rad=settling_displacement(
                    root, t_local, settled_ns),
                gazebo_joint_samples=control['joint_samples'],
                settling_attribution='INTERVAL_ONLY_NO_CAUSAL_PARENT',
                process_resource=per_label,
                total_observed_cpu_seconds=sum(x['cpu_seconds'] or 0 for x in per_label.values()),
                monitor_internal_post_verdict_publish_time='UNKNOWN',
                exact_source_to_specific_servo_output_controller_joint='UNKNOWN_INTERVAL_ONLY')


def pair_comparison(shim, arm, by_id):
    a, b = by_id.get(shim['trial_id']), by_id.get(arm['trial_id'])
    result = dict(pair=[shim['trial_id'], arm['trial_id']])
    if not a or not b or 'attempt' not in a or 'attempt' not in b:
        return dict(result, status='NOT_RUN')
    ra, rb = RAW / a['attempt'], RAW / b['attempt']
    try:
        sent_a, err_a = q6.fixture(ra)
        sent_b, err_b = q6.fixture(rb)
        if err_a or err_b:
            return dict(result, status='INVALID_COMPARISON', issues=(err_a + err_b)[:10])
        starts = [json.loads((r / 'barrier.json').read_text())['start_monotonic_ns'] for r in (ra, rb)]
        timing = [abs((x['sample_ns'] - starts[0]) - (y['sample_ns'] - starts[1])) / 1e6
                  for x, y in zip(sent_a, sent_b) if x['sent'] and y['sent']]
        same = q6.normalized_hash(sent_a) == q6.normalized_hash(sent_b)
        boots = [next((x.get('boot_id') for x in rows(r / 'events.jsonl') if x.get('kind') == 'clock'), None)
                 for r in (ra, rb)]
        clock = bool(boots[0]) and boots[0] == boots[1]
        pre_a = joint_at_source_index(ra, 55, rows, ARM)
        pre_b = joint_at_source_index(rb, 55, rows, ARM)
    except (KeyError, IndexError, ValueError, TypeError, FileNotFoundError, json.JSONDecodeError) as exc:
        return dict(result, status='INVALID_COMPARISON', evidence_error=f'{type(exc).__name__}: {exc}')
    result.update(same_fixture=same, same_boot_id=clock, real_samples_compared=len(timing),
                  max_source_offset_difference_ms=max(timing, default=None))
    ok = same and clock and len(timing) == 100 and max(timing) <= 5
    if pre_a is None or pre_b is None:
        result['pre_fault_allowed_path'] = 'UNKNOWN_MISSING_JOINT_SAMPLE'
        ok = False
    else:
        diff = max(abs(x - y) for x, y in zip(pre_a['positions_rad'], pre_b['positions_rad']))
        result['pre_fault_max_joint_difference_rad'] = diff
        result['pre_fault_joint_sample_offset_ms'] = [pre_a['joint_sample_offset_ms'],
                                                      pre_b['joint_sample_offset_ms']]
        result['pre_fault_allowed_path'] = 'PASS' if diff <= .02 else 'FAIL_POLICY'
    result['status'] = 'PASS_SCHEDULE' if ok else 'INVALID_COMPARISON'
    if ok and a.get('comparison_status') == b.get('comparison_status') == 'VALID_FORMAL_TRIAL':
        fa, fb = a.get('first_callback_latency_by_source_ms'), b.get('first_callback_latency_by_source_ms')
        if fa and fb:
            common = sorted(set(fa) & set(fb))
            result['paired_source_to_first_callback_delta_p95_ms'] = percentile(
                [fb[s] - fa[s] for s in common])
        if a.get('total_observed_cpu_seconds') is not None and b.get('total_observed_cpu_seconds') is not None:
            result['observed_cpu_seconds_delta_vs_shim'] = (
                b['total_observed_cpu_seconds'] - a['total_observed_cpu_seconds'])
    result['post_fault_final_joint_difference_is_policy_outcome_not_pair_gate'] = True
    result['exact_added_gate_transport_latency_p95_ms'] = None
    return result


def formal_attempt(row):
    """The first attempt that reached the start barrier is THE formal trial."""
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
        status = 'BLOCKED_MEASUREMENT' if tried else 'NOT_RUN'
        return dict(trial_id=row['trial_id'], repetition=int(row['repetition']),
                    arm=row['baseline'], regime=row['regime'], comparison_status=status,
                    policy_status='NOT_SCORED', setup_attempts=tried,
                    note='no attempt reached the start barrier' if tried else 'not executed')
    result = audit_trial(row, root)
    result['setup_attempts'] = tried
    return result


def summarize(schedule):
    trials = [score_row(r) for r in schedule]
    by_id = {x['trial_id']: x for x in trials}
    b0_shim, pairs = [], []
    for repeat in range(1, 6):
        group = [x for x in schedule if int(x['repetition']) == repeat]
        shim = next(x for x in group if x['mode'] == 'shim')
        b0 = next(x for x in group if x['mode'] == 'b0')
        ts, tb = by_id[shim['trial_id']], by_id[b0['trial_id']]
        if 'attempt' in ts and 'attempt' in tb:
            try:
                eq = b0_shim_pair(RAW / tb['attempt'], RAW / ts['attempt'])
            except (KeyError, IndexError, ValueError, TypeError, FileNotFoundError, json.JSONDecodeError) as exc:
                eq = dict(status='INVALID_COMPARISON', evidence_error=f'{type(exc).__name__}: {exc}')
        else:
            eq = dict(status='NOT_RUN')
        eq = dict(eq or dict(status='NOT_RUN'), repetition=repeat, pair=[b0['trial_id'], shim['trial_id']])
        b0_shim.append(eq)
        for arm in group:
            if arm is shim:
                continue
            pc = pair_comparison(shim, arm, by_id)
            pairs.append(pc)
            t = by_id[arm['trial_id']]
            if arm['baseline'] not in DEFENSES or t.get('comparison_status') != 'VALID_FORMAL_TRIAL':
                continue
            # Prospective rule: the repetition's allowed-path reference must be valid.
            if eq.get('status') != 'PASS' or pc['status'] != 'PASS_SCHEDULE':
                t['comparison_status'] = 'INVALID_COMPARISON'
                t['invalid_reasons'] = ['REPETITION_B0_SHIM_OR_MATCHED_SCHEDULE_NOT_PASS']
                t['policy_status_before_pair_gate'] = t['policy_status']
                t['policy_status'] = 'UNKNOWN'
            elif pc.get('pre_fault_allowed_path') == 'FAIL_POLICY':
                t['policy_violations'] = sorted(set(t['policy_violations'] +
                                                    ['NORMAL_PREFAULT_JOINT_PATH_OVER_0_02RAD']))
                t['policy_status'] = 'FAIL_POLICY'
    counts = Counter(x['comparison_status'] for x in trials)
    complete = (counts.get('VALID_FORMAL_TRIAL', 0) == 50 and
                all(x.get('status') == 'PASS' for x in b0_shim))
    return dict(status='D3_FORMAL_COMPLETE' if complete else 'D3_FORMAL_PARTIAL_OR_INVALID',
                formal_configuration='XRROS-S4B-D3F1-1.0.0', protocol='XRROS-S4-1.0.0',
                seed=20260922, trials=trials, comparison_counts=dict(counts),
                policy_counts={f"{a}|{r}|{p}": n for (a, r, p), n in
                               Counter((x['arm'], x['regime'], x['policy_status'])
                                       for x in trials).items()},
                b0_shim_equivalence=b0_shim, matched_source_schedule_pairs=pairs,
                exact_internal_added_gate_transport_latency='UNKNOWN',
                exact_source_to_specific_joint_parent='UNKNOWN_INTERVAL_ONLY',
                setup_trials_not_formal='CP16 D3Q6 qualification raw excluded')


def load_schedule():
    with (ROOT / 'schedule.csv').open(newline='') as stream:
        schedule = list(csv.DictReader(stream))
    assert len(schedule) == 50 and [int(x['order']) for x in schedule] == list(range(1, 51))
    assert all(x['case'] == 'D3' and int(x['seed']) == 20260922 for x in schedule)
    return schedule


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--order', type=int)
    parser.add_argument('--all', action='store_true')
    args = parser.parse_args()
    assert (args.order is None) != (not args.all)
    schedule = load_schedule()
    if args.order is not None:
        row = schedule[args.order - 1]
        out = score_row(row)
        (ROOT / 'analysis' / (row['trial_id'] + '.json')).write_text(
            json.dumps(out, indent=2, sort_keys=True) + '\n')
        print(row['trial_id'], out['comparison_status'], out['policy_status'],
              out.get('policy_violations', out.get('invalid_reasons', [])))
        return
    output = summarize(schedule)
    (ROOT / 'analysis/formal_summary.json').write_text(json.dumps(output, indent=2, sort_keys=True) + '\n')
    print(output['status'], json.dumps(output['comparison_counts'], sort_keys=True))
    for key, n in sorted(output['policy_counts'].items()):
        print(' ', key, n)


if __name__ == '__main__':
    main()
