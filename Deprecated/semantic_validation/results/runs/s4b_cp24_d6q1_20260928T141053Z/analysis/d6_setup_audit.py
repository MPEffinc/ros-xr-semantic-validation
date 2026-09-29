#!/usr/bin/env python3
"""Prospective D6Q1 setup audit: the frozen D5 inspect() with D6 fixture/transport rules.

D6 has one connection and no replay. A reconnect is legal only after >= 1.5 s
without bytes (the ORIGINAL receiver's idle disconnect, e.g. during B1
withholding), matched one-to-one by the receiver's own idle-drop log.
"""
import csv
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
RAW = ROOT / 'raw'
sys.path.insert(0, str(HERE))
import d5_setup_audit as base  # noqa: E402
sys.path.insert(0, str(ROOT / 'inputs'))
import d6_fixture as fx  # noqa: E402

rows = base.rows


def fixture(root):
    sent = rows(root / 'sent.jsonl')
    if len(sent) != fx.SLOTS or [x.get('index') for x in sent] != list(range(fx.SLOTS)):
        return sent, ['PLANNED_200_SLOTS_INCOMPLETE']
    barrier = json.loads((root / 'barrier.json').read_text())['start_monotonic_ns']
    errors = []
    for item in sent:
        i, s = item['index'], fx.spec(item['index'])
        try:
            payload = json.loads(item['wire'])
            meta, hand = payload['_qualification'], payload['right_hand']
            ok = (item.get('phase') == s['phase'] and item.get('scheduled_ns') == barrier + i * fx.PERIOD_NS
                  and meta['sample_id'] == f'docker:{i}' and meta['generation_id'] == 1
                  and meta['source_timestamp_ns'] == item['sample_ns'] == item['source_timestamp_ns']
                  and payload['timestamp'] == item['sample_ns'] / 1e9
                  and meta['native_state'] == {'isTracked': s['tracked']} and hand['isTracked'] is s['tracked']
                  and hand['pos']['x'] == s['x'] and payload['controls']['teleop_enable'] is s['teleop']
                  and (item['sent'] is True or item.get('allowed') is False))
        except (KeyError, TypeError, ValueError):
            ok = False
        if not ok:
            errors.append(f'D6_FIXTURE_{i}')
    return sent, errors


def transport_audit(root, baseline):
    t = rows(root / 'sender_transport.jsonl')
    sent = rows(root / 'sent.jsonl')
    issues = []
    if not t or t[0].get('kind') != 'connect' or any(x.get('kind') not in ('connect', 'reconnect_after_peer_close') for x in t):
        issues.append('D6_TRANSPORT_SEQUENCE')
    reconnects = [x for x in t if x.get('kind') == 'reconnect_after_peer_close']
    tx = [(r['index'], r['send_ns']) for r in sent if r.get('sent')]
    activity = [x['monotonic_ns'] for x in t if x.get('kind') == 'connect']
    for x in reconnects:
        earlier = [ns for i, ns in tx if i < x['before_index']]
        prev = max([a for a in activity + earlier if a < x['monotonic_ns']], default=None)
        if prev is None or x['monotonic_ns'] - prev < 1_500_000_000:
            issues.append('UNEXPLAINED_SENDER_RECONNECT')
        activity.append(x['monotonic_ns'])
    log = root / 'stderr' / ('receiver.log' if baseline == 'b0' else 'observed.log')
    text = log.read_text(errors='replace') if log.exists() else ''
    if text.count('TCP client disconnected (idle no bytes)') != len(reconnects):
        issues.append('RECONNECT_WITHOUT_MATCHING_ORIGINAL_IDLE_DISCONNECT')
    return dict(status='PASS' if not issues else 'BLOCKED_MEASUREMENT', issues=issues,
                reconnects=len(reconnects), close_ns=None, reconnect_ns=None)


# The frozen D5 inspect()/pair() resolve these module globals at call time.
base.fx = fx
base.fixture = fixture
base.transport_audit = transport_audit
inspect = base.inspect
pair = base.pair
normalized_hash = base.normalized_hash


def main():
    schedule = list(csv.DictReader((ROOT / 'qualification_schedule.csv').open()))
    cells = []
    for row in schedule:
        attempts = [RAW / (row['trial_id'] + s) for s in ('', '_setup02', '_setup03') if (RAW / (row['trial_id'] + s)).exists()]
        chosen = next((r for r in attempts if (r / 'barrier.json').exists()), None)
        out = (inspect(chosen, row['baseline'], row['regime'], row['expect_motion'] == '1') if chosen else
               dict(trial=row['trial_id'], status='BLOCKED_MEASUREMENT' if attempts else 'NOT_RUN'))
        out['attempts'] = [r.name for r in attempts]
        cells.append(out)
    b0 = next((r for r in schedule if r['baseline'] == 'b0'), None)
    shim = next((r for r in schedule if r['baseline'] == 'shim'), None)
    pr = (pair(RAW / b0['trial_id'], RAW / shim['trial_id']) if b0 and shim and
          (RAW / b0['trial_id'] / 'barrier.json').exists() and (RAW / shim['trial_id'] / 'barrier.json').exists()
          else dict(status='NOT_RUN'))
    ok = all(c['status'] == 'MEASUREMENT_QUALIFIED' for c in cells) and pr['status'] == 'PASS'
    out = dict(status='D6_SETUP_COMPLETE' if ok else 'D6_SETUP_INCOMPLETE_OR_BLOCKED', cells=cells,
               b0_shim_equivalence=pr, policy_verdict='NOT_SCORED')
    (HERE / 'd6_setup_summary.json').write_text(json.dumps(out, indent=2, sort_keys=True) + '\n')
    print(out['status'])
    for c in cells:
        print(' ', c['trial'], c['status'], c.get('issues', []), (c.get('transport') or {}).get('reconnects'))
    print(' pair', pr.get('status'), pr.get('max_source_index_time_difference_ms'), pr.get('max_final_joint_difference_rad'))


if __name__ == '__main__':
    main()
