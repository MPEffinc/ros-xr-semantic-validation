#!/usr/bin/env python3
"""Prospective D4 setup/measurement audit (D4Q2: + sender transport check); NOT a policy score.

Unchanged Q6 checks are imported (official monitor tick/source association,
calibration, post-capture drain, 100 ms CPU/RSS, wait4 lifecycle). D4-specific
parts: the per-sample stamped fixture, the exact source->Servo callback join on
the RECORDED source stamp (D4 decouples it from creation time), and a motion
positive control that is required only where the registered cell expects it.
"""
import csv
import hashlib
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / 'raw'
Q6 = ROOT.parent / 's4b_cp16_d3q6_20260928T032320Z'
sys.path.insert(0, str(Q6 / 'analysis'))
import d3_qualification_audit as q6  # noqa: E402  frozen Q6 helpers (monitor_events)
# The Q6 import chain prepends Q6 inputs/analysis to sys.path; restore D4Q1's own
# copies first and drop any shadowing module so D4 code is never replaced by Q6's.
for _name in ('d3_monitor_audit', 'post_capture_audit', 'calibration_audit',
              'servo_callback_drain', 'source_path_readiness'):
    sys.modules.pop(_name, None)
sys.path.insert(0, str(ROOT / 'inputs'))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from d4_age import CONDITIONS, stamp  # noqa: E402
from d3_monitor_audit import audit as source_monitor_audit  # noqa: E402
from post_capture_audit import audit as lifecycle_audit  # noqa: E402
from calibration_audit import audit as calibration_audit  # noqa: E402

rows = q6.rows
source_origin = q6.source_origin
resources = q6.resources
lifecycle_trial = q6.lifecycle_trial
ARM = q6.ARM
PHASES = [('idle', False, .2)] * 20 + [('reference', True, .2)] * 16 + \
         [('active', True, .35)] * 20 + [('tail', False, .2)] * 64


def fixture(root, condition):
    sent = rows(root / 'sent.jsonl')
    if len(sent) != 120 or [x.get('index') for x in sent] != list(range(120)):
        return sent, ['PLANNED_120_SOURCE_SLOTS_INCOMPLETE']
    barrier = json.loads((root / 'barrier.json').read_text())['start_monotonic_ns']
    errors = []
    for item in sent:
        i = item['index']
        phase, teleop, x = PHASES[i]
        try:
            payload = json.loads(item['wire'])
            meta = payload['_qualification']
            hand = payload['right_hand']
            ok = (item.get('phase') == phase and item.get('scheduled_ns') == barrier + i * 50_000_000
                  and item.get('age_condition') == condition
                  and item['source_timestamp_ns'] == stamp(condition, item['sample_ns'])
                  and meta['source_timestamp_ns'] == item['source_timestamp_ns']
                  and payload['timestamp'] == item['source_timestamp_ns'] / 1e9
                  and meta['sample_id'] == f'docker:{i}' and meta['generation_id'] == 1
                  and meta['native_state'] == {'isTracked': True} and hand['isTracked'] is True
                  and hand['pos'] == {'x': x, 'y': .2, 'z': .3}
                  and payload['controls']['teleop_enable'] is teleop
                  and (item['sent'] is True or item.get('allowed') is False))
        except (KeyError, TypeError, ValueError):
            ok = False
        if not ok:
            errors.append(f'D4_FIXTURE_{i}')
    if len({x['source_timestamp_ns'] for x in sent}) != (1 if condition == 'H1P0' else 120):
        errors.append('PER_SAMPLE_STAMP_REUSE_OR_HISTORICAL_MISMATCH')
    return sent, errors


def normalized_hash(sent):
    normalized = []
    for row in sent:
        wire = json.loads(row['wire'])
        wire.pop('timestamp', None)
        wire['_qualification'].pop('source_timestamp_ns', None)
        normalized.append({'index': row['index'], 'phase': row['phase'],
                           'age_condition': row['age_condition'], 'wire': wire})
    return hashlib.sha256(json.dumps(normalized, sort_keys=True,
                                      separators=(',', ':')).encode()).hexdigest()


def callback_join(root):
    """Q3 exact join, except the source-time check uses the recorded stamp."""
    pub_key = q6.callback_latency.__globals__['pub_key']
    callback_key = q6.callback_latency.__globals__['callback_key']
    sent = {f'docker:{r["index"]}': r for r in rows(root / 'sent.jsonl') if r.get('sent')}
    pubs = [r for r in rows(root / 'lineage.jsonl')
            if r.get('kind') == 'publish' and r.get('stage') == 'bridge_servo_input']
    by_key = defaultdict(list)
    for r in rows(root / 'servo_callback_payload.jsonl'):
        by_key[callback_key(r)].append(r)
    counts = Counter(pub_key(r) for r in pubs)
    joined, missing = [], []
    source_pubs = [r for r in pubs if source_origin(r.get('parent'))]
    for r in source_pubs:
        origin = source_origin(r['parent'])
        sid = origin['sample_id']
        cands = by_key[pub_key(r)]
        if counts[pub_key(r)] != 1 or len(cands) != 1 or sid not in sent or \
                sent[sid]['source_timestamp_ns'] != origin['source_timestamp_ns']:
            missing.append(dict(sample_id=sid, command_id=r['command_id']))
            continue
        cb = cands[0]
        twist = r['payload']['twist']
        joined.append(dict(sample_id=sid, command_id=r['command_id'], phase=origin['phase'],
                           sample_ns=sent[sid]['sample_ns'],
                           source_timestamp_ns=origin['source_timestamp_ns'],
                           publish_ns=r['monotonic_ns'], callback_entry_ns=cb['entry_ns'],
                           sample_to_callback_ms=(cb['entry_ns'] - sent[sid]['sample_ns']) / 1e6,
                           source_age_at_callback_ms=(cb['entry_ns'] - origin['source_timestamp_ns']) / 1e6,
                           nonzero=any(abs(twist[k][a]) > 1e-6 for k in ('linear', 'angular') for a in 'xyz')))
    return dict(source_parent_publications=len(source_pubs), exact_joins=len(joined),
                missing=missing[:20], missing_count=len(missing), joined=joined)


def joints(root, start_ns=None):
    out = []
    for record in rows(root / 'topics.jsonl'):
        if record.get('topic') != '/joint_states' or (start_ns and record['monotonic_ns'] < start_ns):
            continue
        p = record['payload']
        try:
            pos = [p['position'][p['name'].index(n)] for n in ARM]
            vel = [p['velocity'][p['name'].index(n)] for n in ARM]
        except (KeyError, ValueError, IndexError):
            continue
        if all(math.isfinite(v) for v in pos + vel):
            out.append((record['monotonic_ns'], pos, vel))
    return out


def motion(root):
    barrier = json.loads((root / 'barrier.json').read_text())['start_monotonic_ns']
    js = joints(root, barrier)
    nonzero = [r['monotonic_ns'] for r in rows(root / 'topics.jsonl')
               if r.get('topic') == '/joint_group_velocity_controller/commands'
               and r['monotonic_ns'] >= barrier and any(abs(x) > 1e-6 for x in r['payload']['data'])]
    if not js:
        return dict(joint_samples=0, max_excursion_rad=None, controller_nonzero=len(nonzero))
    first = js[0][1]
    return dict(joint_samples=len(js), controller_nonzero=len(nonzero),
                max_excursion_rad=max(abs(p[k] - first[k]) for _, p, _ in js for k in range(6)),
                final_positions_rad=js[-1][1])


def inspect(root, baseline, regime, condition, expect_motion):
    """Setup/measurement checks for one cell; policy is scored elsewhere."""
    issues = []
    exit_record = json.loads((root / 'exit.json').read_text()) if (root / 'exit.json').exists() else {}
    if exit_record.get('launch_exit') != 0:
        issues.append('LAUNCH_NONZERO')
    if not (root / 'barrier.json').exists():
        return dict(trial=root.name, status='BLOCKED_MEASUREMENT', issues=issues + ['NO_START_BARRIER'])
    sent, fixture_issues = fixture(root, condition)
    issues += fixture_issues
    if len(sent) != 120:
        return dict(trial=root.name, status='BLOCKED_MEASUREMENT', issues=issues)
    transport = rows(root / 'sender_transport.jsonl')
    reconnects = [t for t in transport if t.get('kind') == 'reconnect_after_peer_close']
    if not transport or transport[0].get('kind') != 'connect':
        issues.append('SENDER_TRANSPORT_LOG_MISSING')
    for t in reconnects:
        # D4Q2: legal only for B1 after a withheld run long enough for the ORIGINAL
        # receiver's 1.5 s idle disconnect; never a retransmission.
        i = t['before_index']
        run = 0
        while i - 1 - run >= 0 and not sent[i - 1 - run]['sent']:
            run += 1
        if baseline != 'b1' or run * 50 < 1500:
            issues.append('UNEXPLAINED_SENDER_RECONNECT')
    events = rows(root / 'events.jsonl')
    ack = next((x for x in events if x.get('kind') == 'readiness_ack'), None)
    if not ack or len({x.get('boot_id') for x in ack.get('participant_clocks', {}).values()}) != 1:
        issues.append('FULL_ACK_OR_COMMON_CLOCK_MISSING')
    ticks = rows(root / 'd3_ticks.jsonl')
    if (len(ticks) != 300 or [x.get('index') for x in ticks] != list(range(300)) or
            any(x.get('source_sample_id') is not None for x in ticks)):
        issues.append('COMMON_TICK_INCOMPLETE_OR_FABRICATED_SOURCE')
    if baseline == 'b1' and len(rows(root / 'd3_gate_ticks.jsonl')) != 300:
        issues.append('B1_TICK_DECISION_INCOMPLETE')
    res, life = resources(root), lifecycle_trial(root)
    if res['status'] != 'COMPLETE_CAPTURE' or life['status'] != 'PASS':
        issues.append('RESOURCE_CAPTURE_INCOMPLETE')
    callback = None if baseline == 'b0' else callback_join(root)
    if callback and (callback['missing_count'] or callback['exact_joins'] != callback['source_parent_publications']):
        issues.append('EXACT_SOURCE_TO_SERVO_CALLBACK_INCOMPLETE')
    mv = motion(root)
    if expect_motion and (mv['max_excursion_rad'] is None or mv['max_excursion_rad'] <= .01
                          or not mv['controller_nonzero']):
        issues.append('POSITIVE_CONTROL_MOTION_ABSENT')
    monitor = q6.monitor_events(root, regime) if baseline in ('b2', 'b2c') else None
    if monitor and monitor['issues']:
        issues.append('OFFICIAL_TICK_EVENT_ASSOCIATION_INCOMPLETE')
    source_monitor = source_monitor_audit(root, regime) if baseline in ('b2', 'b2c') else None
    if source_monitor and source_monitor['issues']:
        issues.append('OFFICIAL_SOURCE_EVENT_ASSOCIATION_INCOMPLETE')
    calibration = calibration_audit(root, regime) if baseline in ('b2', 'b2c') else None
    if calibration and calibration['status'] != 'PASS':
        issues.append('CALIBRATION_SOURCE_PATH_OR_BARRIER_INCOMPLETE')
    post = lifecycle_audit(root, 'b2' if baseline == 'b2c' else baseline)
    if post['issues']:
        issues.append('POST_CAPTURE_PRODUCER_OR_MONITOR_DRAIN_INCOMPLETE')
    if baseline in ('b1', 'b3', 'b2c') and not (root / 'stop_adapter.ready').exists():
        issues.append('ORDINARY_STOP_ADAPTER_NOT_READY')
    if baseline != 'b0':
        cov = json.loads((root / 'receiver_coverage.json').read_text()) if (root / 'receiver_coverage.json').exists() else None
        if cov is None or cov.get('ok') is not True:
            issues.append('POST_CAPTURE_RECEIVER_COVERAGE_GATE_MISSING_OR_FAILED')
        seen = [(x.get('metadata') or {}) for x in rows(root / 'lineage.jsonl') if x.get('kind') == 'source_received']
        by_id = {f'docker:{r["index"]}': r for r in sent if r['sent']}
        if {m.get('sample_id') for m in seen} != set(by_id) or any(
                m.get('source_timestamp_ns') != by_id[m['sample_id']]['source_timestamp_ns']
                for m in seen if m.get('sample_id') in by_id):
            issues.append('ORIGINAL_RECEIVER_SOURCE_OR_STAMP_COVERAGE')
    return dict(trial=root.name, status='MEASUREMENT_QUALIFIED' if not issues else 'BLOCKED_MEASUREMENT',
                issues=issues, condition=condition, fixture_sha256=normalized_hash(sent),
                real_sent=sum(1 for r in sent if r['sent']), sender_reconnects=len(reconnects),
                withheld_by_b1=[r['index'] for r in sent if not r['sent']],
                callback_exact_joins=None if callback is None else callback['exact_joins'],
                callback_missing=None if callback is None else callback['missing_count'],
                motion=mv, monitor=monitor, source_monitor=source_monitor, calibration=calibration,
                post_capture=post, resources=res['status'], lifecycle=life['status'],
                policy_verdict='NOT_SCORED_BY_SETUP_AUDIT',
                source_to_specific_controller_or_joint_parent='UNKNOWN')


def pair(a, b, condition):
    sent_a, err_a = fixture(a, condition)
    sent_b, err_b = fixture(b, condition)
    if err_a or err_b:
        return dict(status='INVALID_COMPARISON', issues=(err_a + err_b)[:10])
    starts = [json.loads((r / 'barrier.json').read_text())['start_monotonic_ns'] for r in (a, b)]
    timing = [abs((x['sample_ns'] - starts[0]) - (y['sample_ns'] - starts[1])) / 1e6
              for x, y in zip(sent_a, sent_b)]
    finals = [motion(r).get('final_positions_rad') for r in (a, b)]
    diff = max(abs(x - y) for x, y in zip(*finals)) if all(finals) else None
    boots = [next((x.get('boot_id') for x in rows(r / 'events.jsonl') if x.get('kind') == 'clock'), None)
             for r in (a, b)]
    same = normalized_hash(sent_a) == normalized_hash(sent_b)
    ok = same and boots[0] and boots[0] == boots[1] and max(timing) <= 5 and diff is not None and diff <= .02
    return dict(status='PASS' if ok else 'INVALID_COMPARISON', same_fixture=same,
                same_boot_id=boots[0] == boots[1], samples_compared=len(timing),
                max_source_index_time_difference_ms=max(timing), max_final_joint_difference_rad=diff)


def main():
    schedule = list(csv.DictReader((ROOT / 'qualification_schedule.csv').open()))
    cells = []
    for row in schedule:
        root = RAW / row['trial_id']
        attempts = [RAW / (row['trial_id'] + s) for s in ('', '_setup02', '_setup03')]
        attempts = [r for r in attempts if r.exists()]
        chosen = next((r for r in attempts if (r / 'barrier.json').exists()), None)
        if chosen is None:
            cells.append(dict(trial=row['trial_id'], status='NOT_RUN' if not attempts else 'BLOCKED_MEASUREMENT',
                              attempts=[r.name for r in attempts]))
            continue
        result = inspect(chosen, row['baseline'], row['regime'], row['condition'], row['expect_motion'] == '1')
        result['attempts'] = [r.name for r in attempts]
        cells.append(result)
    pairs = []
    for condition in sorted({r['condition'] for r in schedule}):
        b0 = next((r for r in schedule if r['condition'] == condition and r['baseline'] == 'b0'), None)
        shim = next((r for r in schedule if r['condition'] == condition and r['baseline'] == 'shim'), None)
        if b0 and shim and (RAW / b0['trial_id'] / 'barrier.json').exists() and (RAW / shim['trial_id'] / 'barrier.json').exists():
            pairs.append(dict(condition=condition, **pair(RAW / b0['trial_id'], RAW / shim['trial_id'], condition)))
        elif b0 and shim:
            pairs.append(dict(condition=condition, status='NOT_RUN'))
    qualified = all(c['status'] == 'MEASUREMENT_QUALIFIED' for c in cells) and all(p['status'] == 'PASS' for p in pairs)
    result = dict(status='D4_SETUP_COMPLETE' if qualified else 'D4_SETUP_INCOMPLETE_OR_BLOCKED',
                  cells=cells, b0_shim_equivalence=pairs, formal_trials='NOT_STARTED', policy_verdict='NOT_SCORED')
    (ROOT / 'analysis/d4_setup_summary.json').write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
    print(result['status'])
    for c in cells:
        print(' ', c['trial'], c['status'], c.get('issues', []))
    for p in pairs:
        print(' pair', p['condition'], p['status'], p.get('max_source_index_time_difference_ms'), p.get('max_final_joint_difference_rad'))


if __name__ == '__main__':
    main()
