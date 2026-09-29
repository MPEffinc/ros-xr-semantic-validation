#!/usr/bin/env python3
"""Prospective Docker C-MON monitor/oracle-failure formal scorer (XRROS-S4B-CMONF1-1.0.0, scoped).

Validity: the frozen C-MON Q3 setup inspect() (fault proof, pre-fault official
association, continuous valid source 120/120, ACK/clock, 300 ticks, CPU/RSS with
the killed-oracle exemption, exact callbacks, calibration, post-capture drain,
receiver coverage). B0/shim pair (5 ms, .02 rad) per repetition; every arm vs the
repetition's shim: identical normalized fixture and source offsets <= 5 ms.

Local trigger T (earliest time the failure is locally determinable) and the
registered detection allowance A:
  ORACLE_ABSENT         T = start barrier; A = 0 (unavailable before any control).
  ORACLE_DISCONNECT     T = proven SIGKILL time; A = 0.
  ORACLE_NONRESPONSIVE  T = proven SIGSTOP time; A = 50 ms (official configured
                        oracle response timeout; a slower reply is not yet a fault).
  B1/B3 gate failure    T = the gate's last verdict record; A = 250 ms (the common
                        verdict-heartbeat budget).
Policy (fail-closed requirement on a failed defense while valid input continues):
  M1 no neutralization request before T - 1 ms; for faults during motion the
     joint vector at slot 44 is within .02 rad of the repetition's shim.
  M2 explicit neutralization request <= T + A + 50 ms; stop reply and controller
     zero; no nonzero controller output after T + A + 300 ms; Gazebo settled by
     T + A + 1 s. A request delay within the +-1 ms uncertainty band around the
     50 ms bound, with no other violation, is UNKNOWN_BOUNDARY_STRADDLE.
B2-native has no neutralization integration and is scored with the same rule
(its native fail-open or fail-closed behavior is measured, not presumed).
Attribution kept separate: official ROSMonitoring status (unknown/oracle_error),
B2-composed monitor-health stop (common stop adapter), common verdict-heartbeat
watchdog (not ROSMonitoring), original receiver timeout, Servo timeout.
"""
import argparse
import csv
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / 'raw'
Q = ROOT.parent / 's4b_cp28_cmonq3_20260928T175202Z'
sys.path.insert(0, str(Q / 'analysis'))
import cmon_setup_audit as setup  # noqa: E402  frozen C-MON Q3 setup audit

cid, d4, rows = setup.cid, setup.d4, setup.rows
ORACLE_FAULTS = setup.ORACLE_FAULTS
ALLOWANCE_NS = {'ORACLE_ABSENT': 0, 'ORACLE_DISCONNECT': 0, 'ORACLE_NONRESPONSIVE': 50_000_000,
                'B1_GATE_FAIL': 250_000_000, 'B3_GATE_FAIL': 250_000_000}
DEFENSES = ('b1', 'b2', 'b2c', 'b3')
ATTEMPT_SUFFIXES = ('', '_setup02', '_setup03')
BAND_MS = 1.0
TRIGGER_ATTRIBUTION = {
    'B2_MONITOR_HEALTH': 'OFFICIAL_ROSMONITORING_UNKNOWN_STATUS_TO_B2_COMPOSED_MONITOR_HEALTH_STOP',
    'B2_ORACLE_POLICY_REJECT': 'OFFICIAL_ROSMONITORING_VERDICT_CURRENTLY_FALSE',
    'B1_VERDICT_HEARTBEAT_MISSING': 'COMMON_VERDICT_HEARTBEAT_WATCHDOG_NOT_ROSMONITORING',
    'B3_VERDICT_HEARTBEAT_MISSING': 'COMMON_VERDICT_HEARTBEAT_WATCHDOG_NOT_ROSMONITORING',
    'B2_VERDICT_HEARTBEAT_MISSING': 'COMMON_VERDICT_HEARTBEAT_WATCHDOG_NOT_ROSMONITORING',
    'B1_POLICY_REJECT': 'B1_SOURCE_SIDE_POLICY_DECISION', 'B3_POLICY_REJECT': 'B3_RECEIVING_SIDE_POLICY_DECISION'}


class Invalid(Exception):
    pass


def settle_after(root, t_ns):
    """Identical to the frozen C-ID formal scorer's settle rule."""
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
                       max_tree_rss_bytes=x['max_tree_rss_bytes']) for label, x in m.get('per_label', {}).items()}
    out['sender'] = dict(cpu_seconds=life.get('cpu_seconds'), cpu_percent=life.get('cpu_percent'),
                         max_tree_rss_bytes=life.get('observed_peak_rss_bytes'))
    return out


def trigger(root, baseline, fault, t_fault):
    """(T, how) for a defense arm; raises Invalid when the anchor cannot be proven."""
    if fault == 'ORACLE_ABSENT':
        return json.loads((root / 'barrier.json').read_text())['start_monotonic_ns'], 'START_BARRIER'
    if fault in ('ORACLE_DISCONNECT', 'ORACLE_NONRESPONSIVE'):
        if t_fault is None:
            raise Invalid('FAULT_TIME_MISSING')
        return t_fault, 'PROVEN_INJECTION_TIME'
    if baseline == 'b1':
        times = [g['decision_monotonic_ns'] for g in rows(root / 'gate_verdict.jsonl')
                 if g.get('decision_monotonic_ns') is not None]
    else:
        times = [x['monotonic_ns'] for x in rows(root / 'lineage.jsonl') if x.get('kind') == 'b3_mapper_verdict']
    before = [t for t in times if t <= t_fault]
    if not before:
        raise Invalid('GATE_LAST_VERDICT_MISSING')
    if any(t > t_fault for t in times):
        raise Invalid('GATE_VERDICT_AFTER_INJECTED_GATE_FAILURE')
    return max(before), 'GATE_LAST_VERDICT_RECORD'


def official_path(root, regime, t_ns):
    """Measured official-filter behavior at/after T: forwarded vs dropped, verdicts, latency."""
    stage = 'receiver_envelope' if regime == 'full' else 'receiver_native_monitor_input'
    key = 'monitor_event_id' if regime == 'full' else 'payload_sha256'
    lineage = rows(root / 'lineage.jsonl')
    pubs = [r for r in lineage if r.get('kind') == 'publish' and r.get('stage') == stage and r['monotonic_ns'] >= t_ns]
    recv = {}
    for r in lineage:
        if r.get('kind') == 'monitor_output_received' and r.get('regime') == regime:
            recv.setdefault(r.get(key), r['monotonic_ns'])
    lat = [(recv[p.get(key)] - p['monotonic_ns']) / 1e6 for p in pubs if p.get(key) in recv]
    statuses = rows(root / f'monitor_{regime}_status.jsonl')
    verdicts = Counter((s.get('verdict_raw'), s.get('decision')) for s in statuses
                       if s.get('status') == 'event' and s.get('interface') not in ('/s4b/d3/tick',))
    return dict(source_events_published_after_trigger=len(pubs),
                forwarded_to_original_consumer_after_trigger=len(lat),
                not_received_after_trigger=len(pubs) - len(lat),
                max_publish_to_guarded_receipt_ms_after_trigger=max(lat) if lat else None,
                official_source_event_status_counts={f'{v}|{d}': n for (v, d), n in sorted(verdicts.items(), key=str)},
                official_oracle_error_statuses=sum(s.get('status') == 'oracle_error' for s in statuses))


def audit_trial(row, root):
    baseline, mode, regime, fault = row['baseline'], row['mode'], row['regime'], row['fault']
    base = dict(trial_id=row['trial_id'], attempt=root.name, repetition=int(row['repetition']),
                arm=baseline, regime=regime, fault=fault)
    ev = setup.inspect(root, baseline, regime, fault, row['expect_motion'] == '1')
    if ev['status'] != 'MEASUREMENT_QUALIFIED':
        return dict(base, comparison_status='INVALID_COMPARISON', policy_status='UNKNOWN',
                    invalid_reasons=ev.get('issues', []))
    common = dict(base, comparison_status='VALID_FORMAL_TRIAL', motion=ev['motion'],
                  process_resource=resources(root), fault_injected_monotonic_ns=ev['fault_injected_monotonic_ns'])
    if mode in ('b0', 'shim'):
        return dict(common, policy_status='ORIGINAL_CONTROL_NOT_SCORED' if mode == 'b0' else 'OBSERVATIONAL_SHIM_NOT_SCORED')
    try:
        t_trig, how = trigger(root, baseline, fault, ev['fault_injected_monotonic_ns'])
        capture_end = next(x['monotonic_ns'] for x in rows(root / 'events.jsonl') if x.get('kind') == 'capture_end')
    except Invalid as exc:
        return dict(base, comparison_status='INVALID_COMPARISON', policy_status='UNKNOWN', invalid_reasons=[str(exc)])
    except (KeyError, ValueError, TypeError, FileNotFoundError, StopIteration, json.JSONDecodeError) as exc:
        return dict(base, comparison_status='INVALID_COMPARISON', policy_status='UNKNOWN',
                    invalid_reasons=['EVIDENCE_PARSE_ERROR'], evidence_error=f'{type(exc).__name__}: {exc}')
    allowance = ALLOWANCE_NS[fault]
    t_due = t_trig + allowance
    v = []
    adapter = rows(root / 'stop_adapter.jsonl')
    stops = [x for x in adapter if x.get('kind') == 'stop_request']
    request_ms = None if not stops else (stops[0]['monotonic_ns'] - t_trig) / 1e6
    straddle = False
    if request_ms is None:
        v.append('M2_NO_EXPLICIT_NEUTRALIZATION_REQUEST')
    elif request_ms < -BAND_MS:
        v.append('M1_NEUTRALIZATION_BEFORE_LOCAL_TRIGGER')
    else:
        over = request_ms - allowance / 1e6 - 50
        if over > BAND_MS:
            v.append('M2_NEUTRALIZATION_REQUEST_OVER_ALLOWANCE_PLUS_50MS')
        elif over > -BAND_MS:
            straddle = True
    if stops and (not any(x.get('kind') == 'stop_reply' for x in adapter) or
                  not any(x.get('kind') == 'controller_zero' for x in adapter)):
        v.append('M2_STOP_REPLY_OR_CONTROLLER_ZERO_ABSENT')
    controller = [r for r in rows(root / 'topics.jsonl') if r.get('topic') == '/joint_group_velocity_controller/commands'
                  and any(abs(x) > 1e-6 for x in r['payload']['data'])]
    late = [r for r in controller if t_due + 300_000_000 < r['monotonic_ns'] <= capture_end]
    if late:
        v.append('M2_CONTROLLER_NONZERO_AFTER_TRIGGER_ALLOWANCE_PLUS_300MS')
    settled = settle_after(root, t_due)
    if settled is None or settled > 1000:
        v.append('M2_GAZEBO_NOT_SETTLED_BY_TRIGGER_ALLOWANCE_PLUS_1S')
    last_nonzero = max((r['monotonic_ns'] for r in controller if r['monotonic_ns'] <= capture_end), default=None)
    src = next((x.get('source') for x in adapter if x.get('kind') in ('verdict_trigger', 'health_trigger')), None)
    if stops:
        halt = TRIGGER_ATTRIBUTION.get(src, src)
    elif late:
        halt = 'NO_HALT_CONTROL_CONTINUED_FAIL_OPEN'
    else:
        halt = 'UNREQUESTED_HALT_ORIGINAL_RECEIVER_MAPPER_OR_SERVO_TIMEOUT_NOT_A_DEFENSE_DECISION'
    status = 'FAIL_POLICY' if v else ('UNKNOWN_BOUNDARY_STRADDLE' if straddle else 'PASS_POLICY')
    return dict(common, policy_status=status, policy_violations=sorted(set(v)),
                local_trigger_ns=t_trig, local_trigger_anchor=how, detection_allowance_ms=allowance / 1e6,
                neutralization_request_delay_ms=request_ms, stop_trigger_source=src,
                detection_and_stop_attribution=halt,
                actuation_attribution='COMMON_STOP_ADAPTER_NOT_NATIVE_ROSMONITORING' if stops else None,
                nonzero_controller_outputs_after_due_plus_300ms=len(late),
                last_nonzero_controller_after_trigger_ms=None if last_nonzero is None or last_nonzero < t_trig
                else (last_nonzero - t_trig) / 1e6,
                gazebo_settled_after_due_ms=settled,
                official_path=official_path(root, regime, t_trig) if baseline in ('b2', 'b2c') else None,
                source_input_continued_through_fault=True,
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
        return dict(trial_id=row['trial_id'], repetition=int(row['repetition']), arm=row['baseline'],
                    regime=row['regime'], fault=row['fault'],
                    comparison_status='BLOCKED_MEASUREMENT' if tried else 'NOT_RUN',
                    policy_status='NOT_SCORED', setup_attempts=tried)
    out = audit_trial(row, root)
    out['setup_attempts'] = tried
    return out


def near(js, t):
    return min(js, key=lambda x: abs(x[0] - t))[1]


def summarize(schedule):
    trials = [score_row(r) for r in schedule]
    by_id = {t['trial_id']: t for t in trials}
    eq, pairs = [], []
    for rep in range(1, 6):
        group = [r for r in schedule if int(r['repetition']) == rep]
        shim = next(r for r in group if r['baseline'] == 'shim')
        b0 = next(r for r in group if r['baseline'] == 'b0')
        ts, tb = by_id[shim['trial_id']], by_id[b0['trial_id']]
        e = (setup.pair(RAW / tb['attempt'], RAW / ts['attempt']) if 'attempt' in ts and 'attempt' in tb
             else dict(status='NOT_RUN'))
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
                                 for x, y in zip(sa, sb))
                    same = cid.normalized_hash(sa) == cid.normalized_hash(sb)
                    ja, jb = d4.joints(a), d4.joints(b)
                    pre = max(abs(x - y) for x, y in zip(near(ja, sa[44]['sample_ns']), near(jb, sb[44]['sample_ns'])))
                    cpu = lambda x: sum(v['cpu_seconds'] or 0 for v in x.get('process_resource', {}).values())
                    pc.update(status='PASS_SCHEDULE' if same and timing <= 5 else 'INVALID_COMPARISON',
                              max_source_offset_difference_ms=timing, same_fixture=same,
                              slot44_joint_difference_rad=pre,
                              observed_cpu_seconds_delta_vs_shim=cpu(t) - cpu(ts))
            pairs.append(pc)
            if t.get('comparison_status') != 'VALID_FORMAL_TRIAL' or arm['baseline'] not in DEFENSES:
                continue
            if e.get('status') != 'PASS' or pc['status'] != 'PASS_SCHEDULE':
                t.update(comparison_status='INVALID_COMPARISON', policy_status_before_pair_gate=t['policy_status'],
                         policy_status='UNKNOWN', invalid_reasons=['REPETITION_B0_SHIM_OR_MATCHED_SCHEDULE_NOT_PASS'])
            elif arm['fault'] != 'ORACLE_ABSENT' and pc['slot44_joint_difference_rad'] > .02:
                t['policy_violations'] = sorted(set(t['policy_violations'] + ['M1_PREFAULT_JOINT_PATH_OVER_0_02RAD']))
                t['policy_status'] = 'FAIL_POLICY'
    counts = Counter(t['comparison_status'] for t in trials)
    complete = counts.get('VALID_FORMAL_TRIAL', 0) == len(schedule) and all(x.get('status') == 'PASS' for x in eq)
    not_run = ([dict(arm=a, regime='native', fault=f, repetitions=5,
                     status='NOT_RUN_SCOPED_HEALTH_PATH_REGIME_INDEPENDENT_DISCONNECT_TESTED_IN_BOTH')
                for a in ('b2', 'b2c') for f in ('ORACLE_ABSENT', 'ORACLE_NONRESPONSIVE')] +
               [dict(arm=a, regime='native', fault=f, repetitions=5,
                     status='NOT_RUN_SCOPED_GATE_CRASH_AND_WATCHDOG_REGIME_INDEPENDENT')
                for a, f in (('b1', 'B1_GATE_FAIL'), ('b3', 'B3_GATE_FAIL'))])
    return dict(status='CMON_SCOPED_FORMAL_COMPLETE' if complete else 'CMON_SCOPED_FORMAL_PARTIAL_OR_INVALID',
                formal_configuration='XRROS-S4B-CMONF1-1.0.0 (scoped)', protocol='XRROS-S4-1.0.0', seed=20260922,
                trials=trials, comparison_counts=dict(counts),
                policy_counts={f'{a}|{r}|{f}|{s}': n for (a, r, f, s), n in sorted(Counter(
                    (t['arm'], t['regime'], t['fault'], t['policy_status']) for t in trials).items())},
                b0_shim_equivalence=eq, matched_source_schedule_pairs=pairs, registered_not_run=not_run,
                exact_internal_added_gate_transport_latency='UNKNOWN',
                exact_source_to_specific_joint_parent='UNKNOWN_INTERVAL_ONLY',
                setup_trials_not_formal='C-MON Q1/Q2/Q3 qualification raw excluded')


def load_schedule():
    with (ROOT / 'schedule.csv').open(newline='') as f:
        schedule = list(csv.DictReader(f))
    assert [int(x['order']) for x in schedule] == list(range(1, len(schedule) + 1))
    assert all(x['case'] == 'CMON' and int(x['seed']) == 20260922 for x in schedule)
    return schedule


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--order', type=int)
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
