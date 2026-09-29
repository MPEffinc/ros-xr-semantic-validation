"""Exact, fail-closed observation of a pre-barrier official source-path probe.

This module never makes a defense decision. A probe is not a sender sample.
Official forwarded status is intent; guarded subscriber receipt is independent.
"""
import hashlib
import json
from pathlib import Path


def canonical_hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True,
                                     separators=(',', ':')).encode()).hexdigest()


def read_rows(path):
    path = Path(path)
    if not path.exists():
        return [], None
    try:
        return [json.loads(line) for line in path.read_text().splitlines() if line], None
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        return [], f'MALFORMED_LOG_{path.name}_{type(exc).__name__}'


def exact_ack(root, regime, attempt):
    """Require this attempt's unique identity at every recorded boundary."""
    root = Path(root)
    key = attempt['key']
    created = attempt['created_monotonic_ns']
    all_attempts, error = read_rows(root / 'calibration.jsonl')
    if error:
        return dict(ok=False, reason=error, key=key)
    current = [row for row in all_attempts if row.get('attempt') == attempt['attempt']]
    if len(current) != 1 or current[0].get('key') != key:
        return dict(ok=False, reason='ATTEMPT_RECORD_MISSING_OR_AMBIGUOUS', key=key)
    if sum(row.get('key') == key for row in all_attempts) != 1:
        return dict(ok=False, reason='DUPLICATE_CALIBRATION_ID', key=key)
    if regime == 'native' and canonical_hash(attempt['native_payload']) != key:
        return dict(ok=False, reason='NATIVE_CANONICAL_PAYLOAD_HASH_MISMATCH', key=key)
    paths = [root / 'property.jsonl',
             root / ('monitor_full_status.jsonl' if regime == 'full'
                     else 'monitor_native_status.jsonl'), root / 'lineage.jsonl']
    collections = [read_rows(path) for path in paths]
    malformed = next((failure for _, failure in collections if failure), None)
    if malformed:
        return dict(ok=False, reason=malformed, key=key)
    properties, statuses, lineage = (item[0] for item in collections)
    original_stages = {'receiver_envelope', 'receiver_native_monitor_input'}
    originals = [r for r in lineage if r.get('kind') == 'publish'
                 and r.get('stage') in original_stages and
                 (r.get('monitor_event_id') if regime == 'full'
                  else r.get('payload_sha256')) == key]
    if originals:
        return dict(ok=False, reason='CALIBRATION_COLLIDES_WITH_ORIGINAL', key=key)
    props = [r for r in properties if r.get('event_kind') != 'tick' and
             (r.get('monitor_event_id') if regime == 'full'
              else r.get('payload_sha256')) == key]
    matching_status = []
    for row in statuses:
        source_interface = '/s4b/d1/envelope' if regime == 'full' else '/s4b/d1/native_input'
        if row.get('status') != 'event' or row.get('interface') != source_interface:
            continue
        try:
            status_key = (json.loads(row['event']['data'])['envelope_monotonic_ns']
                          if regime == 'full' else canonical_hash(row['payload']))
        except (KeyError, TypeError, json.JSONDecodeError):
            return dict(ok=False, reason='MALFORMED_OFFICIAL_STATUS_EVENT', key=key)
        if status_key == key:
            matching_status.append(row)
    receipts = [r for r in lineage if r.get('kind') == 'monitor_output_received'
                and r.get('regime') == regime and
                (r.get('monitor_event_id') if regime == 'full'
                 else r.get('payload_sha256')) == key]
    counts = dict(property_count=len(props), status_count=len(matching_status),
                  guarded_receipt_count=len(receipts))
    if any(value != 1 for value in counts.values()):
        return dict(ok=False, reason='INCOMPLETE_OR_AMBIGUOUS_PATH', key=key, **counts)
    prop, status, receipt = props[0], matching_status[0], receipts[0]
    if regime == 'full':
        if prop.get('payload_sha256') != canonical_hash(attempt['native_payload']):
            return dict(ok=False, reason='FULL_PAYLOAD_HASH_MISMATCH', key=key, **counts)
        if (json.loads(status['event']['data']).get('original_payload_sha256') != prop['payload_sha256'] or
                receipt.get('original_payload_sha256') != prop['payload_sha256']):
            return dict(ok=False, reason='OFFICIAL_ENVELOPE_PAYLOAD_MISMATCH', key=key, **counts)
    elif canonical_hash(status.get('payload')) != key or receipt.get('payload_sha256') != key:
        return dict(ok=False, reason='NATIVE_PAYLOAD_NOT_PRESERVED', key=key, **counts)
    if prop.get('safe') is not True or status.get('verdict') is not True or status.get('decision') != 'forwarded':
        return dict(ok=False, reason='NOT_SAFE_AND_OFFICIALLY_FORWARDED', key=key, **counts)
    if (prop.get('monotonic_ns', -1) < created or
            receipt.get('monotonic_ns', -1) < prop.get('monotonic_ns', 0)):
        return dict(ok=False, reason='BOUNDARY_TIME_ORDER_INVALID', key=key, **counts)
    return dict(ok=True, reason='EXACT_OFFICIAL_SOURCE_PATH_RECEIPT', key=key,
                oracle_decision_monotonic_ns=prop['monotonic_ns'],
                guarded_receipt_monotonic_ns=receipt['monotonic_ns'],
                official_status_wall_s=status.get('time'),
                official_status_clock='CLOCK_REALTIME; no exact monotonic mapping', **counts)
