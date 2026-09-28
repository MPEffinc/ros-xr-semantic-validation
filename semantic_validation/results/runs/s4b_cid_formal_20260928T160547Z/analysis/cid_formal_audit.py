#!/usr/bin/env python3
"""Prospective Docker C-ID binding-integrity formal scorer (XRROS-S4B-CIDF1-1.0.0, scoped).

Validity: frozen C-ID Q1 setup inspect() (bound fixture + one injected fault,
transport, ACK/clock, 300 ticks, CPU/RSS, exact callbacks on the transmitted
(ID, stamp), B2 association/calibration/drain, receiver coverage on wire IDs);
motion required for every arm (movement precedes slot 50). B0/shim pair
(5 ms, .02 rad) per repetition/kind; arm schedule vs shim (5 ms).

Policy (XRROS-S4-1.0.0 C-ID, section 5 invalidation; R_EXPLICIT) for I_FULL:
 P1 no rejection of teleop decisions on docker:36..49 made before the local
    trigger; exact callbacks for 36..49; pre-fault joint at slot 49 within .02 rad
    of the shim.
 P2 local trigger = arrival of the injected ingestion at the defense (B1 its
    creation; else the ORIGINAL receiver receipt of the slot-50 stamp). The first
    rejection OF THE INJECTED EVENT carries the registered reason for the kind and
    comes <= 50 ms after the trigger; explicit neutralization request <= 50 ms;
    stop reply + controller zero; no controller output after +300 ms; settled +1 s.
 P3 the injected event is never accepted at any evaluation and no nonzero Servo
    command derives from it (lineage followed by its bound stamp, since the ID may be
    absent or reused).
 P4 no nonzero Servo command from the held samples 51..55 (R_EXPLICIT latch).
B2-native is kept distinct; B0/shim are controls (injected-sample consequences
reported). Old generation is the D5 formal evidence, not scored here.
"""
import argparse
import csv
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / 'raw'
Q = ROOT.parent / 's4b_cp26_cidq1_20260928T154636Z'
sys.path.insert(0, str(Q / 'analysis'))
import cid_setup_audit as setup  # noqa: E402  frozen C-ID Q1 setup audit

rows = setup.rows
d4 = setup.d4
REASON = {'MISSING_FIELD': 'MISSING_REQUIRED_FIELD', 'MISSING_ID': 'MISSING_SOURCE_EVENT_ID',
          'DUPLICATE_ID': 'DUPLICATE_SOURCE_EVENT_ID', 'MISMATCH': 'STATE_COMMAND_MISMATCH'}
NORMAL = range(36, 50)
HELD = range(51, 56)
DEFENSES = ('b1', 'b2', 'b2c', 'b3')
ATTEMPT_SUFFIXES = ('', '_setup02', '_setup03')
TRIGGER_ATTRIBUTION = {'B1_POLICY_REJECT': 'B1_SOURCE_SIDE_BINDING_DECISION',
                       'B2_ORACLE_POLICY_REJECT': 'OFFICIAL_ROSMONITORING_VERDICT_CURRENTLY_FALSE',
                       'B2_MONITOR_HEALTH': 'B2_COMPOSED_MONITOR_HEALTH_UNKNOWN_OR_ERROR',
                       'B3_POLICY_REJECT': 'B3_RECEIVING_SIDE_BINDING_DECISION'}


class Invalid(Exception):
    pass


def stamp_of(parent):
    while isinstance(parent, dict):
        if parent.get('source_timestamp_ns') is not None:
            return parent['source_timestamp_ns']
        parent = parent.get('parent')
    return None


def decisions(root, baseline, lineage):
    """(slot stamp, time, allowed, teleop, reason) for every source-event decision at the defense."""
    out = []
    if baseline == 'b1':
        for g in rows(root / 'gate_verdict.jsonl'):
            if g.get('kind') is None and g.get('index') is not None:
                out.append(dict(stamp=g['source_timestamp_ns'], t=g['decision_monotonic_ns'], allowed=g['allowed'] is True,
                                teleop=bool(g.get('teleop')), reason=g.get('reason')))
    elif baseline in ('b2', 'b2c'):
        props = {}
        for p in rows(root / 'property.jsonl'):
            if p.get('event_kind') != 'tick':
                props.setdefault(p.get('monitor_event_id'), []).append(p)
        for pub in lineage:
            if pub.get('kind') == 'publish' and pub.get('stage') == 'receiver_envelope':
                o = pub.get('selected_origin') or {}
                if o.get('origin') == 'ORIGINAL_NEUTRAL':
                    continue
                match = props.get(pub.get('monitor_event_id'), [])
                if len(match) != 1:
                    raise Invalid('SOURCE_PROPERTY_JOIN_NOT_UNIQUE')
                out.append(dict(stamp=o.get('source_timestamp_ns'), t=match[0]['monotonic_ns'],
                                allowed=match[0]['safe'] is True,
                                teleop=bool(match[0].get('teleop')),
                                reason=match[0].get('reason')))
    elif baseline == 'b3':
        for x in lineage:
            if x.get('kind') == 'b3_mapper_verdict' and x.get('event_kind') is None:
                o = x.get('source_origin') or {}
                if o.get('origin') == 'ORIGINAL_NEUTRAL':
                    continue
                out.append(dict(stamp=stamp_of(o), t=x['monotonic_ns'], allowed=x.get('verdict') is True,
                                teleop=bool(x.get('teleop')), reason=x.get('reason')))
    return sorted(out, key=lambda d: d['t'])


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


def derived_nonzero(lineage, stamps):
    """Nonzero bridge->Servo publications whose lineage carries one of the given source stamps."""
    return sum(1 for r in lineage if r.get('kind') == 'publish' and r.get('stage') == 'bridge_servo_input'
               and stamp_of(r.get('parent')) in stamps
               and any(abs(r['payload']['twist'][k][a]) > 1e-6 for k in ('linear', 'angular') for a in 'xyz'))


def audit_trial(row, root):
    baseline, mode, kind = row['baseline'], row['mode'], row['kind']
    base = dict(trial_id=row['trial_id'], attempt=root.name, repetition=int(row['repetition']),
                arm=baseline, regime='full', kind=kind)
    ev = setup.inspect(root, baseline, 'full', kind, True)
    if ev['status'] != 'MEASUREMENT_QUALIFIED':
        return dict(base, comparison_status='INVALID_COMPARISON', policy_status='UNKNOWN',
                    invalid_reasons=ev.get('issues', []))
    try:
        sent = rows(root / 'sent.jsonl')
        stamps = {r['index']: r['sample_ns'] for r in sent}
        inj = stamps[50]
        capture_end = next(x['monotonic_ns'] for x in rows(root / 'events.jsonl') if x.get('kind') == 'capture_end')
        lineage = rows(root / 'lineage.jsonl') if mode != 'b0' else []
        common = dict(base, comparison_status='VALID_FORMAL_TRIAL', motion=ev['motion'], process_resource=resources(root))
        consequences = dict(injected_nonzero_commands=derived_nonzero(lineage, {inj}),
                            held_nonzero_commands=derived_nonzero(lineage, {stamps[i] for i in HELD}))
        if mode in ('b0', 'shim'):
            return dict(common, policy_status='ORIGINAL_CONTROL_NOT_SCORED' if mode == 'b0' else 'OBSERVATIONAL_SHIM_NOT_SCORED',
                        original_consequences=None if mode == 'b0' else consequences)
        dec = decisions(root, baseline, lineage)
        by_stamp = {}
        for d in dec:
            by_stamp.setdefault(d['stamp'], []).append(d)
        if not ({stamps[i] for i in NORMAL} | {inj} | {stamps[i] for i in HELD}) <= set(by_stamp):
            raise Invalid('DECISION_EXACT_COVERAGE_INCOMPLETE')
        if baseline == 'b1':
            t_trig = stamps[50]
        else:
            rx = [x['receiver_receipt_monotonic_ns'] for x in lineage if x.get('kind') == 'source_received'
                  and (x.get('metadata') or {}).get('source_timestamp_ns') == inj]
            if len(rx) != 1:
                raise Invalid('INJECTED_INGESTION_RECEIPT_NOT_UNIQUE')
            t_trig = rx[0]
    except Invalid as exc:
        return dict(base, comparison_status='INVALID_COMPARISON', policy_status='UNKNOWN', invalid_reasons=[str(exc)])
    except (KeyError, IndexError, ValueError, TypeError, FileNotFoundError, StopIteration, json.JSONDecodeError) as exc:
        return dict(base, comparison_status='INVALID_COMPARISON', policy_status='UNKNOWN',
                    invalid_reasons=['EVIDENCE_PARSE_ERROR'], evidence_error=f'{type(exc).__name__}: {exc}')
    v = []
    if any(not d['allowed'] for i in NORMAL for d in by_stamp[stamps[i]] if d['t'] < t_trig):
        v.append('P1_FALSE_REJECTION_OF_NORMAL_INPUT')
    callback = setup.callback_join(root)
    if not {f'docker:{i}' for i in NORMAL} <= {c['sample_id'] for c in callback['joined']}:
        return dict(common, comparison_status='INVALID_COMPARISON', policy_status='UNKNOWN',
                    invalid_reasons=['NORMAL_SOURCE_TO_SERVO_CALLBACK_INCOMPLETE'])
    inj_dec = by_stamp[inj]
    first_rej = next((d for d in inj_dec if not d['allowed']), None)
    decision_ms = None if first_rej is None else (first_rej['t'] - t_trig) / 1e6
    reason_ok = first_rej is not None and first_rej['reason'] == REASON[kind]
    if first_rej is None or decision_ms > 50 or decision_ms < -1:
        v.append('P2_INJECTED_EVENT_DECISION_ABSENT_OR_OVER_50MS')
    if not reason_ok:
        v.append('P2_INJECTED_EVENT_REJECTED_FOR_WRONG_REASON')
    adapter = rows(root / 'stop_adapter.jsonl')
    stops = [x for x in adapter if x.get('kind') == 'stop_request']
    request_ms = None if not stops else (stops[0]['monotonic_ns'] - t_trig) / 1e6
    if request_ms is None:
        v.append('P2_NO_EXPLICIT_NEUTRALIZATION_REQUEST')
    elif request_ms < -1:
        v.append('P1_PREMATURE_NEUTRALIZATION_BEFORE_INJECTION')
    elif request_ms > 50:
        v.append('P2_NEUTRALIZATION_REQUEST_OVER_50MS')
    if stops and (not any(x.get('kind') == 'stop_reply' for x in adapter) or
                  not any(x.get('kind') == 'controller_zero' for x in adapter)):
        v.append('P2_STOP_REPLY_OR_CONTROLLER_ZERO_ABSENT')
    late = [r for r in rows(root / 'topics.jsonl') if r.get('topic') == '/joint_group_velocity_controller/commands'
            and t_trig + 300_000_000 < r['monotonic_ns'] <= capture_end and any(abs(x) > 1e-6 for x in r['payload']['data'])]
    if late:
        v.append('P2_CONTROLLER_NONZERO_AFTER_TRIGGER_PLUS_300MS')
    settled = settle_after(root, t_trig)
    if settled is None or settled > 1000:
        v.append('P2_GAZEBO_NOT_SETTLED_BY_TRIGGER_PLUS_1S')
    if any(d['allowed'] and d['teleop'] for d in inj_dec):
        v.append('P3_INJECTED_EVENT_ACCEPTED')
    if consequences['injected_nonzero_commands']:
        v.append('P3_INJECTED_EVENT_REACHED_SERVO')
    if consequences['held_nonzero_commands']:
        v.append('P4_HELD_GRIP_RESTARTED_AFTER_BINDING_FAULT')
    src = next((x.get('source') for x in adapter if x.get('kind') == 'verdict_trigger'), None)
    return dict(common, policy_status='FAIL_POLICY' if v else 'PASS_POLICY', policy_violations=sorted(set(v)),
                local_trigger_ns=t_trig, injected_decision_delay_ms=decision_ms,
                injected_rejection_reason=None if first_rej is None else first_rej['reason'],
                injected_evaluations=len(inj_dec), neutralization_request_delay_ms=request_ms,
                detection_attribution=TRIGGER_ATTRIBUTION.get(src, src),
                actuation_attribution='COMMON_STOP_ADAPTER_NOT_NATIVE_ROSMONITORING' if stops else None,
                gazebo_settled_after_trigger_ms=settled, consequences=consequences,
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
                    kind=row['kind'], comparison_status='BLOCKED_MEASUREMENT' if tried else 'NOT_RUN',
                    policy_status='NOT_SCORED', setup_attempts=tried)
    out = audit_trial(row, root)
    out['setup_attempts'] = tried
    return out


def summarize(schedule):
    trials = [score_row(r) for r in schedule]
    by_id = {t['trial_id']: t for t in trials}
    eq, pairs = [], []
    for rep in range(1, 6):
        for kind in REASON:
            group = [r for r in schedule if int(r['repetition']) == rep and r['kind'] == kind]
            shim = next(r for r in group if r['baseline'] == 'shim')
            b0 = next(r for r in group if r['baseline'] == 'b0')
            ts, tb = by_id[shim['trial_id']], by_id[b0['trial_id']]
            e = (setup.pair(RAW / tb['attempt'], RAW / ts['attempt'], kind) if 'attempt' in ts and 'attempt' in tb
                 else dict(status='NOT_RUN'))
            eq.append(dict(e, repetition=rep, kind=kind))
            for arm in group:
                if arm is shim or arm is b0:
                    continue
                t = by_id[arm['trial_id']]
                pc = dict(pair=[shim['trial_id'], arm['trial_id']], status='NOT_RUN')
                if 'attempt' in ts and 'attempt' in t:
                    a, b = RAW / ts['attempt'], RAW / t['attempt']
                    sa, ea = setup.fixture(a, kind)
                    sb, eb = setup.fixture(b, kind)
                    if ea or eb:
                        pc['status'] = 'INVALID_COMPARISON'
                    else:
                        starts = [json.loads((r / 'barrier.json').read_text())['start_monotonic_ns'] for r in (a, b)]
                        timing = max(abs((x['sample_ns'] - starts[0]) - (y['sample_ns'] - starts[1])) / 1e6
                                     for x, y in zip(sa, sb))
                        same = setup.normalized_hash(sa) == setup.normalized_hash(sb)
                        ja, jb = d4.joints(a), d4.joints(b)
                        near = lambda js, t: min(js, key=lambda x: abs(x[0] - t))[1]
                        pre = max(abs(x - y) for x, y in zip(near(ja, sa[49]['sample_ns']), near(jb, sb[49]['sample_ns'])))
                        cpu = lambda x: sum(v['cpu_seconds'] or 0 for v in x.get('process_resource', {}).values())
                        pc.update(status='PASS_SCHEDULE' if same and timing <= 5 else 'INVALID_COMPARISON',
                                  max_source_offset_difference_ms=timing, same_fixture=same,
                                  pre_fault_joint_difference_rad=pre,
                                  observed_cpu_seconds_delta_vs_shim=cpu(t) - cpu(ts))
                pairs.append(pc)
                if t.get('comparison_status') != 'VALID_FORMAL_TRIAL' or arm['baseline'] not in DEFENSES:
                    continue
                if e.get('status') != 'PASS' or pc['status'] != 'PASS_SCHEDULE':
                    t.update(comparison_status='INVALID_COMPARISON', policy_status_before_pair_gate=t['policy_status'],
                             policy_status='UNKNOWN', invalid_reasons=['REPETITION_B0_SHIM_OR_MATCHED_SCHEDULE_NOT_PASS'])
                elif pc['pre_fault_joint_difference_rad'] > .02:
                    t['policy_violations'] = sorted(set(t['policy_violations'] + ['P1_PREFAULT_JOINT_PATH_OVER_0_02RAD']))
                    t['policy_status'] = 'FAIL_POLICY'
    counts = Counter(t['comparison_status'] for t in trials)
    complete = counts.get('VALID_FORMAL_TRIAL', 0) == len(schedule) and all(x.get('status') == 'PASS' for x in eq)
    return dict(status='CID_SCOPED_FORMAL_COMPLETE' if complete else 'CID_SCOPED_FORMAL_PARTIAL_OR_INVALID',
                formal_configuration='XRROS-S4B-CIDF1-1.0.0 (scoped)', protocol='XRROS-S4-1.0.0', seed=20260922,
                trials=trials, comparison_counts=dict(counts),
                policy_counts={f'{a}|{k}|{s}': n for (a, k, s), n in Counter(
                    (t['arm'], t['kind'], t['policy_status']) for t in trials).items()},
                b0_shim_equivalence=eq, matched_source_schedule_pairs=pairs,
                registered_not_run=[dict(arm=a, regime='native', kind=k, repetitions=5,
                                         status='NOT_RUN_SCOPED_UNOBSERVABLE_BY_CONSTRUCTION_SETUP_EVIDENCE_IN_CIDQ1')
                                    for a in ('b1', 'b2', 'b2c', 'b3') for k in REASON],
                reused_evidence=dict(old_generation='D5 formal s4b_d5_formal_20260928T133632Z (not a C-ID trial)'),
                exact_internal_added_gate_transport_latency='UNKNOWN',
                exact_source_to_specific_joint_parent='UNKNOWN_INTERVAL_ONLY',
                setup_trials_not_formal='C-ID Q1 qualification raw excluded')


def load_schedule():
    with (ROOT / 'schedule.csv').open(newline='') as f:
        schedule = list(csv.DictReader(f))
    assert [int(x['order']) for x in schedule] == list(range(1, len(schedule) + 1))
    assert all(x['case'] == 'CID' and int(x['seed']) == 20260922 for x in schedule)
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
