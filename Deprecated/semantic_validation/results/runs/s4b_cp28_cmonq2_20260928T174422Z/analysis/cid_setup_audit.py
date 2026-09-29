#!/usr/bin/env python3
"""Prospective C-ID Q1 setup audit; NOT a binding-policy score.

Unchanged checks are delegated to the frozen D4-family audit (ACK/clock, 300
ticks, CPU/RSS, lifecycle, official tick/source association, calibration,
post-capture drain). C-ID-specific: the bound fixture with one injected fault,
the source->Servo callback join on the transmitted (ID, stamp) pair (IDs may be
absent or reused), and receiver coverage on the transmitted wire IDs.
"""
import csv
import hashlib
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
RAW = ROOT / 'raw'
sys.path.insert(0, str(HERE))
import d4_setup_audit as d4  # noqa: E402
sys.path.insert(0, str(ROOT / 'inputs'))
import cid_fixture as fx  # noqa: E402
from cid_binding import check, projection_from_wire  # noqa: E402

rows = d4.rows
source_origin = d4.source_origin


def expected_id(index, kind):
    if index == fx.INJECT_INDEX and kind == 'MISSING_ID':
        return None
    if index == fx.INJECT_INDEX and kind == 'DUPLICATE_ID':
        return fx.DUPLICATE_OF
    return f'docker:{index}'


def fixture(root, kind):
    sent = rows(root / 'sent.jsonl')
    if len(sent) != fx.SLOTS or [x.get('index') for x in sent] != list(range(fx.SLOTS)):
        return sent, ['PLANNED_120_SLOTS_INCOMPLETE']
    barrier = json.loads((root / 'barrier.json').read_text())['start_monotonic_ns']
    errors = []
    for item in sent:
        i, s = item['index'], fx.spec(item['index'])
        try:
            payload = json.loads(item['wire'])
            meta = payload['_qualification']
            inj = i == fx.INJECT_INDEX
            want_reason = ('BOUND' if not inj else {'MISSING_FIELD': 'MISSING_REQUIRED_FIELD',
                                                    'MISSING_ID': 'MISSING_SOURCE_EVENT_ID',
                                                    'DUPLICATE_ID': 'BOUND',
                                                    'MISMATCH': 'STATE_COMMAND_MISMATCH'}[kind])
            ok = (item.get('phase') == s['phase'] and item.get('scheduled_ns') == barrier + i * fx.PERIOD_NS
                  and item.get('cid_kind') == kind and meta.get('sample_id') == expected_id(i, kind)
                  and meta['source_timestamp_ns'] == item['sample_ns']
                  and payload['controls']['teleop_enable'] is s['teleop']
                  and payload['right_hand']['pos']['x'] == (fx.MISMATCH_X if inj and kind == 'MISMATCH' else s['x'])
                  and check(meta, projection_from_wire(payload))[1] == want_reason
                  and (item['sent'] is True or item.get('allowed') is False))
        except (KeyError, TypeError, ValueError):
            ok = False
        if not ok:
            errors.append(f'CID_FIXTURE_{i}')
    return sent, errors


def normalized_hash(sent):
    out = []
    for row in sent:
        wire = json.loads(row['wire'])
        wire.pop('timestamp', None)
        wire['_qualification'].pop('source_timestamp_ns', None)
        wire['_qualification'].pop('binding_sha256', None)
        out.append({'index': row['index'], 'phase': row['phase'], 'wire': wire})
    return hashlib.sha256(json.dumps(out, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def callback_join(root):
    """Exact bridge->Servo join; parent identified by the transmitted (ID, stamp) pair."""
    pub_key = d4.q6.callback_latency.__globals__['pub_key']
    callback_key = d4.q6.callback_latency.__globals__['callback_key']
    sent_pairs = {}
    for r in rows(root / 'sent.jsonl'):
        if r.get('sent'):
            m = json.loads(r['wire'])['_qualification']
            sent_pairs[(m.get('sample_id'), m['source_timestamp_ns'])] = r
    pubs = [r for r in rows(root / 'lineage.jsonl') if r.get('kind') == 'publish' and r.get('stage') == 'bridge_servo_input']
    by_key = defaultdict(list)
    for r in rows(root / 'servo_callback_payload.jsonl'):
        by_key[callback_key(r)].append(r)
    counts = Counter(pub_key(r) for r in pubs)
    joined, missing = [], []
    source_pubs = [r for r in pubs if source_origin(r.get('parent'))]
    for r in source_pubs:
        o = source_origin(r['parent'])
        key = (o['sample_id'], o.get('source_timestamp_ns'))
        cands = by_key[pub_key(r)]
        if counts[pub_key(r)] != 1 or len(cands) != 1 or key not in sent_pairs:
            missing.append(dict(sample_id=o['sample_id'], command_id=r['command_id']))
            continue
        twist = r['payload']['twist']
        joined.append(dict(sample_id=o['sample_id'], slot=sent_pairs[key]['index'], command_id=r['command_id'],
                           sample_ns=sent_pairs[key]['sample_ns'], publish_ns=r['monotonic_ns'],
                           callback_entry_ns=cands[0]['entry_ns'],
                           sample_to_callback_ms=(cands[0]['entry_ns'] - sent_pairs[key]['sample_ns']) / 1e6,
                           nonzero=any(abs(twist[k][a]) > 1e-6 for k in ('linear', 'angular') for a in 'xyz')))
    return dict(source_parent_publications=len(source_pubs), exact_joins=len(joined),
                missing=missing[:20], missing_count=len(missing), joined=joined)


def inspect(root, baseline, regime, kind, expect_motion):
    issues = []
    exit_record = json.loads((root / 'exit.json').read_text()) if (root / 'exit.json').exists() else {}
    if exit_record.get('launch_exit') != 0:
        issues.append('LAUNCH_NONZERO')
    if not (root / 'barrier.json').exists():
        return dict(trial=root.name, status='BLOCKED_MEASUREMENT', issues=issues + ['NO_START_BARRIER'])
    sent, fixture_issues = fixture(root, kind)
    issues += fixture_issues
    if len(sent) != fx.SLOTS:
        return dict(trial=root.name, status='BLOCKED_MEASUREMENT', issues=issues)
    t = rows(root / 'sender_transport.jsonl')
    if [x.get('kind') for x in t] != ['connect']:
        issues.append('CID_TRANSPORT_SEQUENCE')
    events = rows(root / 'events.jsonl')
    ack = next((x for x in events if x.get('kind') == 'readiness_ack'), None)
    if not ack or len({x.get('boot_id') for x in ack.get('participant_clocks', {}).values()}) != 1:
        issues.append('FULL_ACK_OR_COMMON_CLOCK_MISSING')
    ticks = rows(root / 'd3_ticks.jsonl')
    if len(ticks) != 300 or [x.get('index') for x in ticks] != list(range(300)) or \
            any(x.get('source_sample_id') is not None for x in ticks):
        issues.append('COMMON_TICK_INCOMPLETE_OR_FABRICATED_SOURCE')
    if baseline == 'b1' and len(rows(root / 'd3_gate_ticks.jsonl')) != 300:
        issues.append('B1_TICK_DECISION_INCOMPLETE')
    res, life = d4.resources(root), d4.lifecycle_trial(root)
    if res['status'] != 'COMPLETE_CAPTURE' or life['status'] != 'PASS':
        issues.append('RESOURCE_CAPTURE_INCOMPLETE')
    callback = None if baseline == 'b0' else callback_join(root)
    if callback and (callback['missing_count'] or callback['exact_joins'] != callback['source_parent_publications']):
        issues.append('EXACT_SOURCE_TO_SERVO_CALLBACK_INCOMPLETE')
    mv = d4.motion(root)
    if expect_motion and (mv['max_excursion_rad'] is None or mv['max_excursion_rad'] <= .01 or not mv['controller_nonzero']):
        issues.append('POSITIVE_CONTROL_MOTION_ABSENT')
    monitor = d4.monitor_events(root, regime, 300) if baseline in ('b2', 'b2c') else None
    if monitor and monitor['issues']:
        issues.append('OFFICIAL_TICK_EVENT_ASSOCIATION_INCOMPLETE')
    source_monitor = d4.source_monitor_audit(root, regime) if baseline in ('b2', 'b2c') else None
    if source_monitor and source_monitor['issues']:
        issues.append('OFFICIAL_SOURCE_EVENT_ASSOCIATION_INCOMPLETE')
    calibration = d4.calibration_audit(root, regime) if baseline in ('b2', 'b2c') else None
    if calibration and calibration['status'] != 'PASS':
        issues.append('CALIBRATION_SOURCE_PATH_OR_BARRIER_INCOMPLETE')
    post = d4.lifecycle_audit(root, 'b2' if baseline == 'b2c' else baseline, 300)
    if post['issues']:
        issues.append('POST_CAPTURE_PRODUCER_OR_MONITOR_DRAIN_INCOMPLETE')
    if baseline in ('b1', 'b3', 'b2c') and not (root / 'stop_adapter.ready').exists():
        issues.append('ORDINARY_STOP_ADAPTER_NOT_READY')
    if baseline != 'b0':
        cov = json.loads((root / 'receiver_coverage.json').read_text()) if (root / 'receiver_coverage.json').exists() else None
        if cov is None or cov.get('ok') is not True:
            issues.append('POST_CAPTURE_RECEIVER_COVERAGE_GATE_MISSING_OR_FAILED')
    return dict(trial=root.name, status='MEASUREMENT_QUALIFIED' if not issues else 'BLOCKED_MEASUREMENT',
                issues=issues, kind=kind, fixture_sha256=normalized_hash(sent),
                withheld_by_b1=[r['index'] for r in sent if not r['sent']],
                callback_exact_joins=None if callback is None else callback['exact_joins'], motion=mv,
                monitor=monitor, source_monitor=source_monitor, calibration=calibration, post_capture=post,
                resources=res['status'], lifecycle=life['status'], policy_verdict='NOT_SCORED_BY_SETUP_AUDIT')


def pair(a, b, kind):
    sa, ea = fixture(a, kind)
    sb, eb = fixture(b, kind)
    if ea or eb:
        return dict(status='INVALID_COMPARISON', issues=(ea + eb)[:10])
    starts = [json.loads((r / 'barrier.json').read_text())['start_monotonic_ns'] for r in (a, b)]
    timing = max(abs((x['sample_ns'] - starts[0]) - (y['sample_ns'] - starts[1])) / 1e6 for x, y in zip(sa, sb))
    fa, fb = d4.motion(a).get('final_positions_rad'), d4.motion(b).get('final_positions_rad')
    diff = max(abs(x - y) for x, y in zip(fa, fb)) if fa and fb else None
    same = normalized_hash(sa) == normalized_hash(sb)
    ok = same and timing <= 5 and diff is not None and diff <= .02
    return dict(status='PASS' if ok else 'INVALID_COMPARISON', same_fixture=same,
                max_source_index_time_difference_ms=timing, max_final_joint_difference_rad=diff)


def main():
    schedule = list(csv.DictReader((ROOT / 'qualification_schedule.csv').open()))
    cells = []
    for row in schedule:
        attempts = [RAW / (row['trial_id'] + s) for s in ('', '_setup02', '_setup03') if (RAW / (row['trial_id'] + s)).exists()]
        chosen = next((r for r in attempts if (r / 'barrier.json').exists()), None)
        out = (inspect(chosen, row['baseline'], row['regime'], row['kind'], row['expect_motion'] == '1') if chosen
               else dict(trial=row['trial_id'], status='BLOCKED_MEASUREMENT' if attempts else 'NOT_RUN'))
        out['attempts'] = [r.name for r in attempts]
        cells.append(out)
    pairs = []
    for kind in sorted({r['kind'] for r in schedule}):
        b0 = next((r for r in schedule if r['kind'] == kind and r['baseline'] == 'b0'), None)
        shim = next((r for r in schedule if r['kind'] == kind and r['baseline'] == 'shim'), None)
        if b0 and shim:
            ok = (RAW / b0['trial_id'] / 'barrier.json').exists() and (RAW / shim['trial_id'] / 'barrier.json').exists()
            pairs.append(dict(kind=kind, **(pair(RAW / b0['trial_id'], RAW / shim['trial_id'], kind) if ok else dict(status='NOT_RUN'))))
    good = all(c['status'] == 'MEASUREMENT_QUALIFIED' for c in cells) and all(p['status'] == 'PASS' for p in pairs)
    out = dict(status='CID_SETUP_COMPLETE' if good else 'CID_SETUP_INCOMPLETE_OR_BLOCKED', cells=cells,
               b0_shim_equivalence=pairs, policy_verdict='NOT_SCORED')
    (HERE / 'cid_setup_summary.json').write_text(json.dumps(out, indent=2, sort_keys=True) + '\n')
    print(out['status'])
    for c in cells:
        print(' ', c['trial'], c['status'], c.get('issues', []), round((c.get('motion') or {}).get('max_excursion_rad') or 0, 4))
    for p in pairs:
        print(' pair', p['kind'], p['status'], p.get('max_source_index_time_difference_ms'), p.get('max_final_joint_difference_rad'))


if __name__ == '__main__':
    main()
