"""Q4 raw regression for two distinct prospective Q5 causal corrections."""
import json
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
q4 = root.parent / 's4b_cp14_d3q4_20260928T015843Z' / 'raw'
sys.path.insert(0, str(root / 'inputs'))
from source_path_readiness import exact_ack, full_guarded_receipt_fields
from servo_callback_drain import audit as servo_drain

failed_full = q4 / 'docker_b2_full_cp14d3setup01'
attempts = [json.loads(line) for line in (failed_full / 'calibration.jsonl').read_text().splitlines()]
attempt5 = attempts[4]
old = exact_ack(failed_full, 'full', attempt5)
assert old['reason'] == 'OFFICIAL_ENVELOPE_PAYLOAD_MISMATCH', old
statuses = [json.loads(line) for line in (failed_full / 'monitor_full_status.jsonl').read_text().splitlines()]
matching = [row for row in statuses if row.get('status') == 'event' and
            json.loads(row['event']['data'])['envelope_monotonic_ns'] == attempt5['key']]
assert len(matching) == 1
envelope = json.loads(matching[0]['event']['data'])
fields = full_guarded_receipt_fields(envelope)
assert fields['original_payload_sha256'] == envelope['original_payload_sha256']
assert fields['monitor_event_id'] == attempt5['key']
assert 'full_guarded_receipt_fields(envelope)' in (root / 'inputs/d1_nodes.py').read_text()
assert 'full_guarded_receipt_fields(envelope)' in (root / 'inputs/q4_calibration_component.py').read_text()
wrong = dict(envelope, original_payload_sha256='wrong')
try:
    full_guarded_receipt_fields(wrong)
    raise AssertionError('corrupted payload hash accepted')
except ValueError:
    pass

native = servo_drain(q4 / 'docker_b3_native_cp14d3setup01')
full = servo_drain(q4 / 'docker_b3_full_cp14d3setup01')
assert native['status'] == 'PENDING' and native['missing_count'] == 1, native
assert native['missing'][0]['command_id'] == 'bridge_servo_input:920', native
assert full['status'] == 'PASS' and full['missing_count'] == 0, full
capture = int((q4 / 'docker_b3_native_cp14d3setup01/capture_end.ready').read_text())
assert native['missing'][0]['publish_monotonic_ns'] > capture
print('Q5_Q4_RAW_HASH_DEFECT_AND_POSTCAPTURE_SERVO_DRAIN_REGRESSION_PASS')
