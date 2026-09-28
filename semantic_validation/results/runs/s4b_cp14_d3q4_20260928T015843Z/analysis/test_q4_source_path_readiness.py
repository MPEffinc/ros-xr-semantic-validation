"""Host-only exact ACK controls; they do not qualify the official ROS path."""
import hashlib
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'inputs'))
from source_path_readiness import canonical_hash, exact_ack


def put(root, filename, *items):
    (root / filename).write_text(''.join(json.dumps(x) + '\n' for x in items))


def full_fixture(root):
    payload = {'tracked': False, 'teleop_enable': False,
               'header': {'stamp': {'sec': 1, 'nanosec': 2}}}
    key = 123456
    attempt = {'attempt': 1, 'regime': 'full', 'key': key,
               'created_monotonic_ns': 100, 'native_payload': payload,
               'source_sample': False, 'control_input': False}
    put(root, 'calibration.jsonl', attempt)
    put(root, 'property.jsonl', {'event_kind': 'source_or_original_output',
        'monitor_event_id': key, 'monotonic_ns': 110,
        'payload_sha256': canonical_hash(payload), 'safe': True})
    status = {'status': 'event', 'interface': '/s4b/d1/envelope',
              'decision': 'forwarded', 'verdict': True,
              'event': {'data': json.dumps({'envelope_monotonic_ns': key,
                  'original_payload_sha256': canonical_hash(payload)})}}
    put(root, 'monitor_full_status.jsonl', status)
    receipt = {'kind': 'monitor_output_received', 'regime': 'full',
               'monitor_event_id': key, 'monotonic_ns': 120,
               'original_payload_sha256': canonical_hash(payload)}
    put(root, 'lineage.jsonl', receipt)
    return attempt, status, receipt


with tempfile.TemporaryDirectory() as scratch:
    root = Path(scratch)
    attempt, status, receipt = full_fixture(root)
    assert exact_ack(root, 'full', attempt)['ok']
    wrong = dict(attempt, key=attempt['key'] + 1)
    assert not exact_ack(root, 'full', wrong)['ok']
    put(root, 'lineage.jsonl')  # Forwarded intention without guarded receipt.
    assert not exact_ack(root, 'full', attempt)['ok']
    put(root, 'lineage.jsonl', dict(receipt, original_payload_sha256='wrong'))
    assert not exact_ack(root, 'full', attempt)['ok']
    put(root, 'lineage.jsonl', receipt)
    put(root, 'monitor_full_status.jsonl', dict(status, decision='blocked'))
    assert not exact_ack(root, 'full', attempt)['ok']
    put(root, 'monitor_full_status.jsonl', status)
    put(root, 'property.jsonl')  # No oracle property despite forwarded output.
    assert not exact_ack(root, 'full', attempt)['ok']
    (root / 'property.jsonl').write_text('{"incomplete":')
    assert not exact_ack(root, 'full', attempt)['ok']
    put(root, 'calibration.jsonl', attempt, dict(attempt, attempt=2))
    assert exact_ack(root, 'full', attempt)['reason'] == 'DUPLICATE_CALIBRATION_ID'

with tempfile.TemporaryDirectory() as scratch:
    root = Path(scratch)
    payload = {'tracked': False, 'teleop_enable': False,
               'header': {'stamp': {'sec': 1, 'nanosec': 2}}}
    key = canonical_hash(payload)
    attempt = {'attempt': 1, 'regime': 'native', 'key': key,
               'created_monotonic_ns': 100, 'native_payload': payload,
               'source_sample': False, 'control_input': False}
    put(root, 'calibration.jsonl', attempt)
    put(root, 'property.jsonl', {'event_kind': 'source_or_original_output',
        'payload_sha256': key, 'monotonic_ns': 110, 'safe': True})
    put(root, 'monitor_native_status.jsonl', {'status': 'event',
        'interface': '/s4b/d1/native_input', 'payload': payload,
        'decision': 'forwarded', 'verdict': True})
    receipt = {'kind': 'monitor_output_received', 'regime': 'native',
               'payload_sha256': key, 'monotonic_ns': 120}
    assert not exact_ack(root, 'native', attempt)['ok']  # No subscriber.
    put(root, 'lineage.jsonl', receipt)
    assert exact_ack(root, 'native', attempt)['ok']  # Delayed exact receipt.
    put(root, 'calibration.jsonl', attempt, dict(attempt, attempt=2))
    assert exact_ack(root, 'native', attempt)['reason'] == 'DUPLICATE_CALIBRATION_ID'
    put(root, 'calibration.jsonl', attempt)
    put(root, 'lineage.jsonl', receipt, dict(receipt, monotonic_ns=121))
    assert not exact_ack(root, 'native', attempt)['ok']
    put(root, 'lineage.jsonl', receipt)
    put(root, 'property.jsonl', {'event_kind': 'source_or_original_output',
        'payload_sha256': key, 'monotonic_ns': 99, 'safe': True})
    assert exact_ack(root, 'native', attempt)['reason'] == 'BOUNDARY_TIME_ORDER_INVALID'
print('Q4_EXACT_ACK_HOST_POSITIVE_NEGATIVE_PASS')
