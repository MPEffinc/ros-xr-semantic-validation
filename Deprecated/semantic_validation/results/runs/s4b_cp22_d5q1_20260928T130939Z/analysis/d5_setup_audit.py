#!/usr/bin/env python3
"""Prospective D5Q1 setup/measurement audit; NOT a recovery-policy score.

Reuses the frozen D4LQ2 audit's unchanged checks (callback join on the recorded
stamp, motion, parameterized official tick/source association, calibration,
post-capture drain, CPU/RSS, lifecycle). D5-specific: the fixture/generation
schedule (d5_fixture), 500 ticks for the 10 s capture, the source-initiated
close at slot 56 and new-generation connect at slot 70 (the only legal
transport events besides the idle-time peer-close rule), and the ORIGINAL
receiver's own accept/drop observation used by the I_FULL defenses.
"""
import csv
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / 'raw'
sys.path.insert(0, str(Path(__file__).resolve().parent))
import d4_setup_audit as d4  # noqa: E402  (D4LQ2 analyzer copy; imports D5Q1 inputs first)
sys.path.insert(0, str(ROOT / 'inputs'))
import d5_fixture as fx  # noqa: E402

rows = d4.rows
TICKS = fx.CAPTURE_NS // 20_000_000


def fixture(root):
    sent = rows(root / 'sent.jsonl')
    if len(sent) != fx.SLOTS or [x.get('index') for x in sent] != list(range(fx.SLOTS)):
        return sent, ['PLANNED_200_SLOTS_INCOMPLETE']
    barrier = json.loads((root / 'barrier.json').read_text())['start_monotonic_ns']
    errors = []
    for item in sent:
        i, s = item['index'], fx.spec(item['index'])
        if item.get('phase') != s['phase'] or item.get('scheduled_ns') != barrier + i * fx.PERIOD_NS:
            errors.append(f'D5_SCHEDULE_{i}')
            continue
        if not s['sent']:
            if item.get('sent') is not False or item.get('wire') is not None:
                errors.append(f'D5_DISCONNECT_SLOT_CREATED_SOURCE_{i}')
            continue
        try:
            payload = json.loads(item['wire'])
            meta, hand = payload['_qualification'], payload['right_hand']
            ok = (meta['sample_id'] == f'docker:{i}' and meta['generation_id'] == s['generation']
                  and item['generation_id'] == s['generation']
                  and meta['source_timestamp_ns'] == item['sample_ns'] == item['source_timestamp_ns']
                  and payload['timestamp'] == item['sample_ns'] / 1e9
                  and meta['native_state'] == {'isTracked': True} and hand['pos']['x'] == s['x']
                  and payload['controls']['teleop_enable'] is s['teleop']
                  and (item['sent'] is True or item.get('allowed') is False))
        except (KeyError, TypeError, ValueError):
            ok = False
        if not ok:
            errors.append(f'D5_FIXTURE_{i}')
    return sent, errors


def normalized_hash(sent):
    out = []
    for row in sent:
        item = {'index': row['index'], 'phase': row['phase']}
        if row.get('wire'):
            wire = json.loads(row['wire'])
            wire.pop('timestamp', None)
            wire['_qualification'].pop('source_timestamp_ns', None)
            item['wire'] = wire
        out.append(item)
    return hashlib.sha256(json.dumps(out, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def transport_audit(root, baseline):
    t = rows(root / 'sender_transport.jsonl')
    kinds = [x.get('kind') for x in t]
    issues = []
    if kinds[:3] != ['connect', 'source_close_while_moving', 'connect_new_generation'] or \
            any(k not in ('connect', 'source_close_while_moving', 'connect_new_generation') for k in kinds):
        issues.append('D5_TRANSPORT_SEQUENCE')
    log = root / 'stderr' / ('receiver.log' if baseline == 'b0' else 'observed.log')
    text = log.read_text(errors='replace') if log.exists() else ''
    if text.count('TCP client disconnected (peer closed)') < 1 or text.count('TCP client connected') != 2:
        issues.append('ORIGINAL_RECEIVER_CLOSE_OR_RECONNECT_UNOBSERVED')
    if baseline != 'b0':
        conn = [x for x in rows(root / 'lineage.jsonl') if x.get('kind') == 'receiver_connection']
        if [(c['event'], c['index']) for c in conn][:3] != [('accepted', 1), ('dropped', 1), ('accepted', 2)]:
            issues.append('RECEIVER_CONNECTION_OBSERVATION_INCOMPLETE')
    return dict(status='PASS' if not issues else 'BLOCKED_MEASUREMENT', issues=issues,
                close_ns=next((x['monotonic_ns'] for x in t if x.get('kind') == 'source_close_while_moving'), None),
                reconnect_ns=next((x['monotonic_ns'] for x in t if x.get('kind') == 'connect_new_generation'), None))


def inspect(root, baseline, regime, expect_motion=True):
    issues = []
    exit_record = json.loads((root / 'exit.json').read_text()) if (root / 'exit.json').exists() else {}
    if exit_record.get('launch_exit') != 0:
        issues.append('LAUNCH_NONZERO')
    if not (root / 'barrier.json').exists():
        return dict(trial=root.name, status='BLOCKED_MEASUREMENT', issues=issues + ['NO_START_BARRIER'])
    sent, fixture_issues = fixture(root)
    issues += fixture_issues
    if len(sent) != fx.SLOTS:
        return dict(trial=root.name, status='BLOCKED_MEASUREMENT', issues=issues)
    events = rows(root / 'events.jsonl')
    ack = next((x for x in events if x.get('kind') == 'readiness_ack'), None)
    if not ack or len({x.get('boot_id') for x in ack.get('participant_clocks', {}).values()}) != 1:
        issues.append('FULL_ACK_OR_COMMON_CLOCK_MISSING')
    ticks = rows(root / 'd3_ticks.jsonl')
    if len(ticks) != TICKS or [x.get('index') for x in ticks] != list(range(TICKS)) or \
            any(x.get('source_sample_id') is not None for x in ticks):
        issues.append('COMMON_TICK_INCOMPLETE_OR_FABRICATED_SOURCE')
    if baseline == 'b1' and len(rows(root / 'd3_gate_ticks.jsonl')) != TICKS:
        issues.append('B1_TICK_DECISION_INCOMPLETE')
    res, life = d4.resources(root), d4.lifecycle_trial(root)
    if res['status'] != 'COMPLETE_CAPTURE' or life['status'] != 'PASS':
        issues.append('RESOURCE_CAPTURE_INCOMPLETE')
    callback = None if baseline == 'b0' else d4.callback_join(root)
    if callback and (callback['missing_count'] or callback['exact_joins'] != callback['source_parent_publications']):
        issues.append('EXACT_SOURCE_TO_SERVO_CALLBACK_INCOMPLETE')
    mv = d4.motion(root)
    if expect_motion and (mv['max_excursion_rad'] is None or mv['max_excursion_rad'] <= .01 or not mv['controller_nonzero']):
        issues.append('POSITIVE_CONTROL_MOTION_ABSENT')
    transport = transport_audit(root, baseline)
    issues += transport['issues']
    monitor = d4.monitor_events(root, regime, TICKS) if baseline in ('b2', 'b2c') else None
    if monitor and monitor['issues']:
        issues.append('OFFICIAL_TICK_EVENT_ASSOCIATION_INCOMPLETE')
    source_monitor = d4.source_monitor_audit(root, regime) if baseline in ('b2', 'b2c') else None
    if source_monitor and source_monitor['issues']:
        issues.append('OFFICIAL_SOURCE_EVENT_ASSOCIATION_INCOMPLETE')
    calibration = d4.calibration_audit(root, regime) if baseline in ('b2', 'b2c') else None
    if calibration and calibration['status'] != 'PASS':
        issues.append('CALIBRATION_SOURCE_PATH_OR_BARRIER_INCOMPLETE')
    post = d4.lifecycle_audit(root, 'b2' if baseline == 'b2c' else baseline, TICKS)
    if post['issues']:
        issues.append('POST_CAPTURE_PRODUCER_OR_MONITOR_DRAIN_INCOMPLETE')
    if baseline in ('b1', 'b3', 'b2c') and not (root / 'stop_adapter.ready').exists():
        issues.append('ORDINARY_STOP_ADAPTER_NOT_READY')
    if baseline != 'b0':
        cov = json.loads((root / 'receiver_coverage.json').read_text()) if (root / 'receiver_coverage.json').exists() else None
        if cov is None or cov.get('ok') is not True:
            issues.append('POST_CAPTURE_RECEIVER_COVERAGE_GATE_MISSING_OR_FAILED')
    return dict(trial=root.name, status='MEASUREMENT_QUALIFIED' if not issues else 'BLOCKED_MEASUREMENT',
                issues=issues, fixture_sha256=normalized_hash(sent),
                withheld_by_b1=[r['index'] for r in sent if fx.spec(r['index'])['sent'] and not r['sent']],
                callback_exact_joins=None if callback is None else callback['exact_joins'],
                motion=mv, transport=transport, monitor=monitor, source_monitor=source_monitor,
                calibration=calibration, post_capture=post, resources=res['status'], lifecycle=life['status'],
                policy_verdict='NOT_SCORED_BY_SETUP_AUDIT')


def pair(a, b):
    sa, ea = fixture(a)
    sb, eb = fixture(b)
    if ea or eb:
        return dict(status='INVALID_COMPARISON', issues=(ea + eb)[:10])
    starts = [json.loads((r / 'barrier.json').read_text())['start_monotonic_ns'] for r in (a, b)]
    timing = [abs((x['sample_ns'] - starts[0]) - (y['sample_ns'] - starts[1])) / 1e6
              for x, y in zip(sa, sb) if x.get('sample_ns') and y.get('sample_ns')]
    fa, fb = d4.motion(a).get('final_positions_rad'), d4.motion(b).get('final_positions_rad')
    diff = max(abs(x - y) for x, y in zip(fa, fb)) if fa and fb else None
    same = normalized_hash(sa) == normalized_hash(sb)
    ok = same and max(timing) <= 5 and diff is not None and diff <= .02
    return dict(status='PASS' if ok else 'INVALID_COMPARISON', same_fixture=same, samples_compared=len(timing),
                max_source_index_time_difference_ms=max(timing), max_final_joint_difference_rad=diff)


def main():
    schedule = list(csv.DictReader((ROOT / 'qualification_schedule.csv').open()))
    cells = []
    for row in schedule:
        attempts = [RAW / (row['trial_id'] + s) for s in ('', '_setup02', '_setup03') if (RAW / (row['trial_id'] + s)).exists()]
        chosen = next((r for r in attempts if (r / 'barrier.json').exists()), None)
        if chosen is None:
            cells.append(dict(trial=row['trial_id'], status='NOT_RUN' if not attempts else 'BLOCKED_MEASUREMENT'))
            continue
        out = inspect(chosen, row['baseline'], row['regime'], row['expect_motion'] == '1')
        out['attempts'] = [r.name for r in attempts]
        cells.append(out)
    b0 = next(r for r in schedule if r['baseline'] == 'b0')
    shim = next(r for r in schedule if r['baseline'] == 'shim')
    pr = (pair(RAW / b0['trial_id'], RAW / shim['trial_id'])
          if (RAW / b0['trial_id'] / 'barrier.json').exists() and (RAW / shim['trial_id'] / 'barrier.json').exists()
          else dict(status='NOT_RUN'))
    ok = all(c['status'] == 'MEASUREMENT_QUALIFIED' for c in cells) and pr['status'] == 'PASS'
    out = dict(status='D5_SETUP_COMPLETE' if ok else 'D5_SETUP_INCOMPLETE_OR_BLOCKED', cells=cells,
               b0_shim_equivalence=pr, policy_verdict='NOT_SCORED')
    (ROOT / 'analysis/d5_setup_summary.json').write_text(json.dumps(out, indent=2, sort_keys=True) + '\n')
    print(out['status'])
    for c in cells:
        print(' ', c['trial'], c['status'], c.get('issues', []))
    print(' pair', pr.get('status'), pr.get('max_source_index_time_difference_ms'), pr.get('max_final_joint_difference_rad'))


if __name__ == '__main__':
    main()
