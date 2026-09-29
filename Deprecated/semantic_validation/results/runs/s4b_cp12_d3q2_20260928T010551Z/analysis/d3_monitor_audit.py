"""Exact original-output/official-oracle/guarded-receipt association for D3.

Tick events are audited separately. Publication attempts prove neither DDS
delivery nor a downstream callback; every missing boundary remains invalid.
"""
import hashlib
import json
from collections import defaultdict


def rows(path):
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line]


def canonical_hash(payload):
    return hashlib.sha256(json.dumps(payload, sort_keys=True,
                                     separators=(',', ':')).encode()).hexdigest()


def audit(root, regime):
    lineage = rows(root / 'lineage.jsonl')
    props = [r for r in rows(root / 'property.jsonl')
             if r.get('event_kind') != 'tick']
    statuses = [r for r in rows(root / f'monitor_{regime}_status.jsonl')
                if r.get('status') == 'event' and r.get('interface') != '/s4b/d3/tick']
    stage = 'receiver_envelope' if regime == 'full' else 'receiver_native_monitor_input'
    pubs = [r for r in lineage if r.get('stage') == stage]
    outputs = [r for r in lineage if r.get('kind') == 'monitor_output_received'
               and r.get('regime') == regime]
    errors = []
    by_type = []
    if regime == 'full':
        for collection, key in ((pubs, lambda r: r['monitor_event_id']),
                                (props, lambda r: r['monitor_event_id']),
                                (statuses, lambda r: json.loads(r['event']['data'])['envelope_monotonic_ns']),
                                (outputs, lambda r: r['monitor_event_id'])):
            table = defaultdict(list)
            for record in collection:
                table[key(record)].append(record)
            by_type.append(table)
    else:
        for collection, key in ((pubs, lambda r: r['payload_sha256']),
                                (props, lambda r: r['payload_sha256']),
                                (statuses, lambda r: canonical_hash(r['payload'])),
                                (outputs, lambda r: r['payload_sha256'])):
            table = defaultdict(list)
            for record in collection:
                table[key(record)].append(record)
            by_type.append(table)
    publication, property_by, status_by, output_by = by_type
    if set(publication) != set(property_by) or set(publication) != set(status_by):
        errors.append('ORIGINAL_PUBLICATION_PROPERTY_STATUS_ID_SET_MISMATCH')
    if set(output_by) - set(publication):
        errors.append('GUARDED_RECEIPT_WITHOUT_ORIGINAL_PUBLICATION')
    for event_id in set(publication) | set(property_by) | set(status_by) | set(output_by):
        p, prop, status, out = (table.get(event_id, []) for table in by_type)
        if len(p) != 1 or len(prop) != 1 or len(status) != 1:
            errors.append(f'AMBIGUOUS_OR_MISSING_ORIGINAL_EVENT_{event_id}')
            continue
        if bool(prop[0]['safe']) != bool(status[0].get('verdict')):
            errors.append(f'PROPERTY_STATUS_VERDICT_MISMATCH_{event_id}')
        if regime == 'full' and p[0]['original_payload_sha256'] != prop[0]['payload_sha256']:
            errors.append(f'ORIGINAL_PAYLOAD_HASH_MISMATCH_{event_id}')
        if prop[0]['safe']:
            if status[0].get('decision') != 'forwarded' or len(out) != 1:
                errors.append(f'SAFE_ORIGINAL_GUARDED_RECEIPT_MISSING_{event_id}')
        elif status[0].get('decision') != 'blocked' or out:
            errors.append(f'BLOCKED_ORIGINAL_LEAK_{event_id}')
    return dict(status='PASS' if not errors else 'BLOCKED_MEASUREMENT',
                original_publications=len(pubs), property_events=len(props),
                official_status_events=len(statuses), guarded_receipts=len(outputs),
                issue_count=len(errors), issues=errors[:100],
                exact_monitor_internal_publish_time='UNKNOWN')
