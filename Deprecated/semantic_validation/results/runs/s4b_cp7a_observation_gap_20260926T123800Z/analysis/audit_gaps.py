#!/usr/bin/env python3
"""Read-only exact-ID audit of frozen D1 I_FULL monitor observations.

The official monitor's ``decision=forwarded`` status is written before its
ROS publisher call. It is evidence of intent, never proof of DDS delivery.
"""
import argparse
import csv
import json
from pathlib import Path


def rows(path):
    with path.open() as stream:
        for line in stream:
            if line.strip():
                yield json.loads(line)


def event_id(status):
    return json.loads(status['event']['data'])['envelope_monotonic_ns']


def audit(trial):
    root = Path(trial)
    lineage = list(rows(root / 'lineage.jsonl'))
    props = list(rows(root / 'property.jsonl'))
    status = list(rows(root / 'monitor_full_status.jsonl'))
    official_events = list(rows(root / 'monitor_full_events.jsonl'))
    recorder = {json.loads(r['payload']['data'])['envelope_monotonic_ns']: r
                for r in rows(root / 'topics.jsonl')
                if r.get('topic') == '/s4b/d1/envelope'}
    receiver = {r['monitor_event_id']: r for r in lineage if r.get('stage') == 'receiver_envelope'}
    forwarded = {event_id(r): r for r in status if r.get('decision') == 'forwarded'}
    received = {r['monitor_event_id']: r for r in lineage if r.get('kind') == 'monitor_output_received'}
    restored = {r['parent']['monitor_event_id']: r for r in lineage if r.get('stage') == 'stripper_restored'}
    mapper = {r['exact_parent']['parent']['monitor_event_id']: r for r in lineage
              if r.get('kind') == 'consume' and r.get('stage') == 'mapper'
              and isinstance(r.get('exact_parent'), dict)
              and isinstance(r['exact_parent'].get('parent'), dict)
              and 'monitor_event_id' in r['exact_parent']['parent']}
    official = {json.loads(r['data'])['envelope_monotonic_ns'] for r in official_events}
    barrier = json.loads((root / 'barrier.json').read_text())
    ack = next(r for r in rows(root / 'events.jsonl') if r.get('kind') == 'readiness_ack')
    capture = next(r for r in rows(root / 'events.jsonl') if r.get('kind') == 'capture_end')
    seen = set()
    events = []
    for p in props:
        eid = p['monitor_event_id']
        if eid in seen:
            raise ValueError(f'duplicate property event ID {eid}')
        seen.add(eid)
        source = receiver.get(eid)
        if source and source['original_payload_sha256'] != p['payload_sha256']:
            raise ValueError(f'original payload hash mismatch {eid}')
        s = forwarded.get(eid)
        receipt = received.get(eid)
        rec = restored.get(eid)
        m = mapper.get(eid)
        events.append(dict(
            trial=root.name, event_id=eid, payload_sha256=p['payload_sha256'],
            native_parent=json.dumps(source.get('selected_origin') if source else None, sort_keys=True),
            sample_id=p.get('sample_id'), safe=p.get('safe'),
            receiver_publish_ns=source.get('monotonic_ns') if source else None,
            official_monitor_event= eid in official,
            oracle_decision_ns=p['monotonic_ns'],
            monitor_forward_intent=bool(s), monitor_status=s.get('decision') if s else None,
            stripper_receipt_ns=receipt.get('monotonic_ns') if receipt else None,
            recorder_receipt_ns=recorder[eid]['monotonic_ns'] if eid in recorder else None,
            stripper_restored_ns=rec.get('monotonic_ns') if rec else None,
            mapper_consume_ns=m.get('monotonic_ns') if m else None,
            barrier_delta_ms=round((p['monotonic_ns']-barrier['start_monotonic_ns'])/1e6, 3),
            ack_delta_ms=round((p['monotonic_ns']-ack['monotonic_ns'])/1e6, 3),
            capture_end_delta_ms=round((p['monotonic_ns']-capture['monotonic_ns'])/1e6, 3),
        ))
    missing = [r for r in events if r['stripper_receipt_ns'] is None]
    return dict(trial=root.name, property_count=len(props), receiver_count=len(receiver),
                official_event_count=len(official), forward_intent_count=len(forwarded),
                receipt_count=len(received), recorder_receipt_count=len(recorder),
                restored_count=len(restored),
                mapper_exact_consume_count=len(mapper), missing_count=len(missing),
                missing_with_forward_intent=sum(r['monitor_forward_intent'] for r in missing),
                missing_pre_barrier=sum(r['barrier_delta_ms'] < 0 for r in missing),
                missing_after_capture=sum(r['capture_end_delta_ms'] > 0 for r in missing),
                ack_ns=ack['monotonic_ns'], barrier_ns=barrier['start_monotonic_ns'],
                capture_end_ns=capture['monotonic_ns'],
                all_receiver_hashes_match=True), missing


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--raw-root', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('trials', nargs='+')
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    summaries, gaps = [], []
    for trial in args.trials:
        summary, missing = audit(args.raw_root / trial)
        summaries.append(summary)
        gaps.extend(missing)
    (args.out / 'summary.json').write_text(json.dumps(summaries, indent=2, sort_keys=True) + '\n')
    with (args.out / 'unjoined_events.csv').open('w', newline='') as stream:
        columns = ['trial', 'event_id', 'payload_sha256', 'native_parent', 'sample_id',
                   'safe', 'receiver_publish_ns', 'official_monitor_event',
                   'oracle_decision_ns', 'monitor_forward_intent', 'monitor_status',
                   'stripper_receipt_ns', 'recorder_receipt_ns', 'stripper_restored_ns', 'mapper_consume_ns',
                   'barrier_delta_ms', 'ack_delta_ms', 'capture_end_delta_ms']
        writer = csv.DictWriter(stream, fieldnames=columns, lineterminator='\n')
        writer.writeheader()
        writer.writerows(gaps)
    print(json.dumps(dict(trials=len(summaries), unjoined=len(gaps)), sort_keys=True))


if __name__ == '__main__':
    main()
