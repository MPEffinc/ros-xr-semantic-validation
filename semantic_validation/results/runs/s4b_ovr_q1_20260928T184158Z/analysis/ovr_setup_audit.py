#!/usr/bin/env python3
"""Prospective OpenVR Q1 setup/measurement audit; NOT a policy score.

Per cell (MEASUREMENT_QUALIFIED only if all hold):
  * launch exit 0, start barrier, readiness ACK with every participant clock on
    the recorder's boot/time namespace, capture end;
  * fake API polls 0..599 all inside the 12 s capture (complete source input);
  * CPU/RSS capture complete for every ACKed participant (frozen Q3 resource rule);
  * motion (> .01 rad excursion) when the cell expects it;
  * non-B0: every production publication (shim/B1/B3) or stripper Servo input (B2)
    joins exactly one Servo overlay poseCallback by header stamp + pose, and every
    callback joins exactly one publication (no nearest-time matching);
  * B2: ACKed calibration through the genuine official path; every source envelope
    has exactly one oracle property row and one official status, and each forwarded
    one exactly one guarded receipt;
  * B1/B2-composed/B3: stop adapter ready.
B0/shim pair: matched source-index timing <= 5 ms, final joint difference <= .02 rad.
"""
import csv
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
RAW = ROOT / 'raw'
sys.path.insert(0, str(ROOT.parent / 's4b_cp5b_measurement_20260923T054101Z' / 'analysis'))
from q3_measurement_audit import resources  # noqa: E402  frozen Q3 resource rule

NAMES = ['shoulder_pan_joint', 'shoulder_lift_joint', 'elbow_joint', 'wrist_1_joint', 'wrist_2_joint', 'wrist_3_joint']
POLLS = 600


def rows(path):
    path = Path(path)
    if not path.exists():
        return []
    out = []
    for line in path.read_text(errors='replace').splitlines():
        if line.strip():
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                out.append({'_malformed': True})
    return out


def joints(root, start_ns=None, end_ns=None):
    out = []
    for r in rows(root / 'topics.jsonl'):
        if r.get('topic') != '/joint_states':
            continue
        t = r['monotonic_ns']
        if (start_ns is not None and t < start_ns) or (end_ns is not None and t > end_ns):
            continue
        p = r['payload']
        try:
            out.append((t, [p['position'][p['name'].index(n)] for n in NAMES], [p['velocity'][p['name'].index(n)] for n in NAMES]))
        except (KeyError, ValueError, IndexError):
            continue
    return out


def capture(root):
    ev = rows(root / 'events.jsonl')
    start = next((x['start_monotonic_ns'] for x in ev if x.get('kind') == 'barrier_release'), None)
    end = next((x['monotonic_ns'] for x in ev if x.get('kind') == 'capture_end'), None)
    return ev, start, end


def motion(root):
    _, start, end = capture(root)
    js = joints(root, start, end)
    if not js:
        return dict(joint_samples=0, max_excursion_rad=None, final_positions_rad=None)
    first = js[0][1]
    return dict(joint_samples=len(js), max_excursion_rad=max(abs(p[k] - first[k]) for _, p, _ in js for k in range(6)),
                final_positions_rad=js[-1][1])


def source(root):
    _, start, end = capture(root)
    src = [r for r in rows(root / 'source.jsonl') if isinstance(r.get('index'), int) and r['index'] < POLLS]
    ok = ([r['index'] for r in src] == list(range(POLLS)) and start is not None and end is not None and
          all(start <= r['source_timestamp_ns'] <= end for r in src))
    return src, ok


def pose_key(stamp, pos):
    return (int(stamp['sec']), int(stamp['nanosec']), tuple(round(float(x), 12) for x in pos))


def callback_join(root, baseline):
    """Exact joins of Servo-input publications to overlay poseCallback records."""
    stage = 'stripper_servo_input' if baseline.startswith('b2') else 'production_pose'
    pubs = [r for r in rows(root / 'lineage.jsonl') if r.get('kind') == 'publish' and r.get('stage') == stage]
    by = defaultdict(list)
    for p in pubs:
        pl = p['payload']
        pos = pl['pose']['position']
        by[pose_key(pl['header']['stamp'], [pos['x'], pos['y'], pos['z']])].append(p)
    cbs = rows(root / 'servo_callback_overlay.jsonl')
    joined, unjoined_cb = 0, 0
    seen = Counter()
    for c in cbs:
        k = pose_key(dict(sec=c['stamp_sec'], nanosec=c['stamp_nanosec']), c['position'])
        if len(by.get(k, [])) == 1:
            joined += 1
            seen[k] += 1
        else:
            unjoined_cb += 1
    missing = sum(1 for k, v in by.items() if seen[k] != len(v))
    return dict(publications=len(pubs), callbacks=len(cbs), exact_joins=joined, unjoined_callbacks=unjoined_cb,
                publications_without_exactly_one_callback=missing)


def b2_association(root):
    lin = rows(root / 'lineage.jsonl')
    env = [r for r in lin if r.get('stage') == 'production_envelope' and r.get('envelope_kind') != 'calibration']
    props = Counter(p.get('monitor_event_id') for p in rows(root / 'property.jsonl'))
    status = {}
    dup = 0
    for s in rows(root / 'monitor_full_status.jsonl'):
        if s.get('status') == 'event':
            try:
                k = json.loads(s['event']['data'])['envelope_monotonic_ns']
            except (KeyError, TypeError, ValueError):
                continue
            dup += k in status
            status[k] = s
    rec = Counter(r.get('monitor_event_id') for r in lin if r.get('kind') == 'monitor_output_received')
    issues = Counter()
    for e in env:
        k = e['monitor_event_id']
        st = status.get(k)
        if st is None:
            issues['NO_OFFICIAL_STATUS'] += 1
            continue
        if props[k] != 1:
            issues['PROPERTY_NOT_EXACTLY_ONE'] += 1
        if rec[k] != (1 if st.get('decision') == 'forwarded' else 0):
            issues['RECEIPT_MISMATCH'] += 1
    return dict(envelopes=len(env), duplicate_status=dup, issues=dict(issues))


def inspect(root, baseline, expect_motion):
    issues = []
    ex = json.loads((root / 'exit.json').read_text()) if (root / 'exit.json').exists() else {}
    if ex.get('launch_exit') != 0:
        issues.append('LAUNCH_NONZERO')
    if not (root / 'barrier.json').exists():
        return dict(trial=root.name, status='BLOCKED_MEASUREMENT', issues=issues + ['NO_START_BARRIER'])
    ev, start, end = capture(root)
    ack = next((x for x in ev if x.get('kind') == 'readiness_ack'), None)
    if not ack or len({c.get('boot_id') for c in ack.get('participant_clocks', {}).values()}) != 1 or end is None:
        issues.append('ACK_CLOCK_OR_CAPTURE_END_MISSING')
    src, src_ok = source(root)
    if not src_ok:
        issues.append('SOURCE_POLLS_0_599_NOT_COMPLETE_IN_CAPTURE')
    res = resources(root)
    if res['status'] != 'COMPLETE_CAPTURE':
        issues.append('RESOURCE_CAPTURE_INCOMPLETE')
    mv = motion(root)
    if expect_motion and (mv['max_excursion_rad'] is None or mv['max_excursion_rad'] <= .01):
        issues.append('POSITIVE_CONTROL_MOTION_ABSENT')
    cb = None if baseline == 'b0' else callback_join(root, baseline)
    if cb and (cb['unjoined_callbacks'] or cb['publications_without_exactly_one_callback']):
        issues.append('SERVO_CALLBACK_EXACT_JOIN_INCOMPLETE')
    assoc = None
    if baseline.startswith('b2'):
        if not (ack or {}).get('source_path_calibration'):
            issues.append('B2_CALIBRATION_NOT_ACKED')
        assoc = b2_association(root)
        if assoc['issues'] or assoc['duplicate_status']:
            issues.append('B2_OFFICIAL_ASSOCIATION_INCOMPLETE')
    if baseline in ('b1', 'b3') or baseline.endswith('c'):
        if not (root / 'stop_adapter.ready').exists():
            issues.append('STOP_ADAPTER_NOT_READY')
    return dict(trial=root.name, status='MEASUREMENT_QUALIFIED' if not issues else 'BLOCKED_MEASUREMENT', issues=issues,
                motion=mv, resources=res['status'], callback=cb, b2_association=assoc, policy_verdict='NOT_SCORED_BY_SETUP_AUDIT')


def pair(a, b):
    sa, oka = source(a)
    sb, okb = source(b)
    if not (oka and okb):
        return dict(status='INVALID_COMPARISON', reason='SOURCE_INCOMPLETE')
    starts = [json.loads((r / 'barrier.json').read_text())['start_monotonic_ns'] for r in (a, b)]
    diffs = [abs((x['source_timestamp_ns'] - starts[0]) - (y['source_timestamp_ns'] - starts[1])) / 1e6 for x, y in zip(sa, sb)]
    fa, fb = motion(a)['final_positions_rad'], motion(b)['final_positions_rad']
    fd = max(abs(x - y) for x, y in zip(fa, fb)) if fa and fb else None
    ok = max(diffs) <= 5 and fd is not None and fd <= .02
    return dict(status='PASS' if ok else 'INVALID_COMPARISON', max_source_index_time_difference_ms=max(diffs),
                indices_over_5ms=sum(d > 5 for d in diffs), max_final_joint_difference_rad=fd)


def main():
    schedule = list(csv.DictReader((ROOT / 'qualification_schedule.csv').open()))
    cells = []
    for row in schedule:
        attempts = [RAW / (row['trial_id'] + s) for s in ('', '_setup02', '_setup03') if (RAW / (row['trial_id'] + s)).exists()]
        chosen = next((r for r in attempts if (r / 'barrier.json').exists()), None)
        out = (inspect(chosen, row['baseline'], row['expect_motion'] == '1') if chosen
               else dict(trial=row['trial_id'], status='BLOCKED_MEASUREMENT' if attempts else 'NOT_RUN'))
        out['attempts'] = [r.name for r in attempts]
        cells.append(out)
    b0 = next(r for r in schedule if r['baseline'] == 'b0' and r['case'] == 'W1')
    shim = next(r for r in schedule if r['baseline'] == 'shim')
    pr = (pair(RAW / b0['trial_id'], RAW / shim['trial_id'])
          if all((RAW / r['trial_id'] / 'barrier.json').exists() for r in (b0, shim)) else dict(status='NOT_RUN'))
    ok = all(c['status'] == 'MEASUREMENT_QUALIFIED' for c in cells) and pr['status'] == 'PASS'
    out = dict(status='OVR_SETUP_COMPLETE' if ok else 'OVR_SETUP_INCOMPLETE_OR_BLOCKED', cells=cells,
               b0_shim_equivalence=pr, policy_verdict='NOT_SCORED')
    (HERE / 'ovr_setup_summary.json').write_text(json.dumps(out, indent=2, sort_keys=True) + '\n')
    print(out['status'])
    for c in cells:
        print(' ', c['trial'], c['status'], c.get('issues', []), round((c.get('motion') or {}).get('max_excursion_rad') or 0, 4),
              (c.get('callback') or {}).get('exact_joins'))
    print(' pair', pr)


if __name__ == '__main__':
    main()
