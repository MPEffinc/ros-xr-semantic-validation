"""Calibration may be excluded as a distinct class; original neutrals may not."""
import json
import tempfile
from pathlib import Path

from d3_monitor_audit import audit, canonical_hash


def write(root, name, records):
    (root / name).write_text(''.join(json.dumps(row) + '\n' for row in records))


for regime in ('native', 'full'):
    with tempfile.TemporaryDirectory() as scratch:
        root = Path(scratch)
        calibration_payload = {'source': 'readiness_calibration', 'tracked': False,
                               'header': {'stamp': 1}}
        original_payload = {'source': 'stale_timeout', 'tracked': False,
                            'header': {'stamp': 2}}
        calibration_key = (canonical_hash(calibration_payload) if regime == 'native'
                           else 1001)
        original_key = (canonical_hash(original_payload) if regime == 'native'
                        else 1002)
        write(root, 'calibration.jsonl', [{'attempt': 1, 'key': calibration_key}])
        stage = ('receiver_native_monitor_input' if regime == 'native'
                 else 'receiver_envelope')
        keyfield = 'payload_sha256' if regime == 'native' else 'monitor_event_id'
        pub = {'stage': stage, keyfield: original_key,
               'original_payload_sha256': canonical_hash(original_payload)}
        receipt = {'kind': 'monitor_output_received', 'regime': regime,
                   keyfield: original_key}
        calibration_receipt = dict(receipt, **{keyfield: calibration_key})
        write(root, 'lineage.jsonl', [pub, calibration_receipt, receipt])
        prop = {'event_kind': 'source_or_original_output', keyfield: original_key,
                'payload_sha256': canonical_hash(original_payload), 'safe': True}
        calibration_prop = dict(prop, **{keyfield: calibration_key})
        write(root, 'property.jsonl', [calibration_prop, prop])

        def status(key, payload):
            item = {'status': 'event', 'interface': '/s4b/d1/' +
                    ('native_input' if regime == 'native' else 'envelope'),
                    'decision': 'forwarded', 'verdict': True}
            if regime == 'native':
                item['payload'] = payload
            else:
                item['event'] = {'data': json.dumps({'envelope_monotonic_ns': key})}
            return item

        status_path = 'monitor_' + regime + '_status.jsonl'
        write(root, status_path, [status(calibration_key, calibration_payload),
                                  status(original_key, original_payload)])
        result = audit(root, regime)
        assert result['status'] == 'PASS', result
        assert result['original_publications'] == 1 and result['calibration_attempts'] == 1
        write(root, 'lineage.jsonl', [pub, calibration_receipt])
        result = audit(root, regime)
        assert result['status'] == 'BLOCKED_MEASUREMENT', result
        assert any('SAFE_ORIGINAL_GUARDED_RECEIPT_MISSING' in issue
                   for issue in result['issues']), result
print('Q4_CALIBRATION_SEPARATE_ORIGINAL_NEUTRAL_RETAINED_PASS')
