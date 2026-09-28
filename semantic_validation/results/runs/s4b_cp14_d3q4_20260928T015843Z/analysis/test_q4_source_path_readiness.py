"""Host-only exact ACK positive/negative controls for unfrozen Q4 draft."""
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'inputs'))
from source_path_readiness import canonical_hash, exact_ack

def write(path, row):
    path.write_text(json.dumps(row) + '\n')

with tempfile.TemporaryDirectory() as scratch:
    root = Path(scratch)
    key = 123456
    write(root / 'property.jsonl', {'event_kind': 'source_or_original_output',
                                     'monitor_event_id': key, 'safe': True})
    status = {'status': 'event', 'interface': '/s4b/d1/envelope', 'decision': 'forwarded',
              'verdict': True, 'event': {'data': json.dumps({'envelope_monotonic_ns': key})}}
    write(root / 'monitor_full_status.jsonl', status)
    assert not exact_ack(root, 'full', key)['ok']  # No guarded receipt.
    write(root / 'lineage.jsonl', {'kind': 'monitor_output_received', 'regime': 'full',
                                   'monitor_event_id': key})
    assert exact_ack(root, 'full', key)['ok']
    assert not exact_ack(root, 'full', key + 1)['ok']  # Wrong event ID.
    status['decision'] = 'blocked'
    write(root / 'monitor_full_status.jsonl', status)
    assert not exact_ack(root, 'full', key)['ok']  # Safe predicate not enough.

with tempfile.TemporaryDirectory() as scratch:
    root = Path(scratch)
    payload = {'tracked': False, 'teleop_enable': False, 'header': {'stamp': {'sec': 1, 'nanosec': 2}}}
    key = canonical_hash(payload)
    write(root / 'property.jsonl', {'event_kind': 'source_or_original_output',
                                     'payload_sha256': key, 'safe': True})
    write(root / 'monitor_native_status.jsonl', {'status': 'event',
          'interface': '/s4b/d1/native_input', 'payload': payload,
          'decision': 'forwarded', 'verdict': True})
    write(root / 'lineage.jsonl', {'kind': 'monitor_output_received',
                                   'regime': 'native', 'payload_sha256': key})
    assert exact_ack(root, 'native', key)['ok']
    assert not exact_ack(root, 'native', 'wrong')['ok']
print('Q4_SOURCE_PATH_EXACT_ACK_HOST_CONTROLS_PASS')
