"""Host-only controls for the prospective post-capture lifecycle gate."""
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'inputs'))
from post_capture_lifecycle import capture_has_ended
from post_capture_audit import audit

with tempfile.TemporaryDirectory() as scratch:
    root = Path(scratch)
    assert not capture_has_ended(root)
    (root / 'capture_end.ready').write_text('6000000000\n')
    assert capture_has_ended(root)
    (root / 'receiver_quiesced.ready').write_text('6001000000\n')
    events = [{'kind': 'capture_end', 'monotonic_ns': 6000000000},
              {'kind': 'post_capture_receiver_quiesce_ack', 'quiesce_ns': 6001000000},
              {'kind': 'post_capture_monitor_drain_ack', 'result': {'status': 'PASS'},
               'tick_property_count': 300, 'tick_status_count': 300}]
    lineage = [{'kind': 'publish', 'stage': 'receiver_native_monitor_input',
                'monotonic_ns': 5999000000},
               {'kind': 'post_capture_receiver_quiesced', 'monotonic_ns': 6001000000}]
    (root / 'events.jsonl').write_text(''.join(json.dumps(x)+'\n' for x in events))
    (root / 'lineage.jsonl').write_text(''.join(json.dumps(x)+'\n' for x in lineage))
    assert audit(root, 'b2')['status'] == 'PASS'
    lineage.append({'kind': 'publish', 'stage': 'receiver_native_monitor_input',
                    'monotonic_ns': 6001000001})
    (root / 'lineage.jsonl').write_text(''.join(json.dumps(x)+'\n' for x in lineage))
    assert 'ORIGINAL_PUBLICATION_AFTER_QUIESCE' in audit(root, 'b2')['issues']
    events.pop()
    (root / 'events.jsonl').write_text(''.join(json.dumps(x)+'\n' for x in events))
    assert 'EXACT_OFFICIAL_MONITOR_DRAIN_ACK_MISSING' in audit(root, 'b2')['issues']

q2 = ROOT.parent / 's4b_cp12_d3q2_20260928T010551Z/raw/docker_b2c_native_cp12d3setup01'
assert audit(q2, 'b2')['status'] == 'BLOCKED_MEASUREMENT'
print('D3Q3_POST_CAPTURE_LIFECYCLE_POSITIVE_NEGATIVE_PASS')
