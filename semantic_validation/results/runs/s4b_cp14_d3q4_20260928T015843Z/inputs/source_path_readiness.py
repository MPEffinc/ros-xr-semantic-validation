"""Exact calibration-event acknowledgments; no XR policy decisions.

Calibration events are pre-barrier non-control ROS messages, never sender
source samples. Each attempt stays in calibration.jsonl, including losses.
"""
import hashlib
import json
from pathlib import Path


def canonical_hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True,
                                     separators=(',', ':')).encode()).hexdigest()


def rows(path):
    path = Path(path)
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line]


def exact_ack(root, regime, key):
    root = Path(root)
    props = [r for r in rows(root / 'property.jsonl')
             if r.get('event_kind') != 'tick' and
             (r.get('monitor_event_id') if regime == 'full' else r.get('payload_sha256')) == key]
    status_path = root / ('monitor_full_status.jsonl' if regime == 'full'
                          else 'monitor_native_status.jsonl')
    statuses = []
    for r in rows(status_path):
        if r.get('status') != 'event' or r.get('interface') == '/s4b/d3/tick':
            continue
        found = (json.loads(r['event']['data'])['envelope_monotonic_ns'] if regime == 'full'
                 else canonical_hash(r['payload']))
        if found == key:
            statuses.append(r)
    receipts = [r for r in rows(root / 'lineage.jsonl')
                if r.get('kind') == 'monitor_output_received' and r.get('regime') == regime and
                (r.get('monitor_event_id') if regime == 'full' else r.get('payload_sha256')) == key]
    ok = (len(props) == len(statuses) == len(receipts) == 1 and props[0].get('safe') is True
          and statuses[0].get('verdict') is True and statuses[0].get('decision') == 'forwarded')
    return dict(ok=ok, property_count=len(props), status_count=len(statuses),
                guarded_receipt_count=len(receipts), key=key)
