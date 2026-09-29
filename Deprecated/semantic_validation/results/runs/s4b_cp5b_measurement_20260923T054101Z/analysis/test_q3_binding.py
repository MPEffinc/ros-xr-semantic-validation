"""No-Gazebo Q3 oracle-event identity and audit-UNKNOWN preflight."""
import hashlib
import importlib.util
import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'inputs'))
from d1_contract import canonical, make_envelope
import d1_tloracle_property as prop
from q3_measurement_audit import callback_latency

q2 = ROOT.parent / 's4b_cp4b_preflight_20260923T044458Z'
old = q2 / 'raw/docker_b1_full_q2b1fsetup01'
observed = callback_latency(old)
assert observed['source_parent_publications'] == 372
assert observed['exact_joins'] == 372
assert observed['missing'] == []
assert observed['active_source_to_servo_callback_ms']['count'] > 0

fields = dict(header=dict(frame_id='unity_world', stamp=dict(sec=1, nanosec=2)),
              teleop_enable=True, tracked=True)
origin = dict(sample_id='fixture:1', generation_id=1,
              native_state=dict(isTracked=True), source_timestamp_ns=0)
envelope = make_envelope(fields, origin, 123456789)
with tempfile.TemporaryDirectory(prefix='s4b_q3_binding_') as temp:
    os.environ['INFO_REGIME'] = 'full'
    os.environ['XR_D1_PROPERTY_LOG'] = str(Path(temp) / 'property.jsonl')
    prop.abstract_message(dict(data=json.dumps(envelope)))
    logged = json.loads(Path(os.environ['XR_D1_PROPERTY_LOG']).read_text().splitlines()[0])
    assert logged['monitor_event_id'] == envelope['envelope_monotonic_ns']
    assert logged['sample_id'] == origin['sample_id']
    assert logged['payload_sha256'] == hashlib.sha256(canonical(fields).encode()).hexdigest()
    test_root = Path(temp) / 'ambiguous'
    test_root.mkdir()
    exact_origin = dict(sample_id='docker:0', generation_id=1, phase='active',
                        source_timestamp_ns=1000, native_state={'isTracked': True})
    payload = dict(header=dict(stamp=dict(sec=1, nanosec=2), frame_id='base_link'),
                   twist=dict(linear=dict(x=1., y=0., z=0.),
                              angular=dict(x=0., y=0., z=0.)))
    publication = dict(kind='publish', stage='bridge_servo_input',
                       parent=exact_origin, command_id='bridge:1',
                       monotonic_ns=1200, payload=payload)
    callback = dict(stamp_sec=1, stamp_nanosec=2, frame_id='base_link',
                    linear=[1., 0., 0.], angular=[0., 0., 0.], entry_ns=1300)
    (test_root / 'sent.jsonl').write_text(json.dumps(dict(index=0, sample_ns=1000)) + '\n')
    (test_root / 'lineage.jsonl').write_text(json.dumps(publication) + '\n')
    (test_root / 'servo_callback_payload.jsonl').write_text(json.dumps(callback) + '\n')
    assert callback_latency(test_root)['exact_joins'] == 1
    (test_root / 'lineage.jsonl').write_text(json.dumps(publication) + '\n' +
                                             json.dumps(dict(publication, command_id='bridge:2')) + '\n')
    duplicate = callback_latency(test_root)
    assert duplicate['exact_joins'] == 0 and len(duplicate['missing']) == 2
    (test_root / 'lineage.jsonl').write_text(json.dumps(dict(publication, parent={})) + '\n')
    assert callback_latency(test_root)['exact_joins'] == 0
del os.environ['XR_D1_PROPERTY_LOG']

result = dict(status='PASS_NON_GAZEBO_PREFLIGHT', q2_exact_join_count=372,
              oracle_envelope_id_exact=True, duplicate_payload_refused=True,
              missing_parent_refused=True, native_full_policy_unmodified=True,
              q2_resources='UNKNOWN_NOT_RECORDED',
              q2_monitor_internal_forward='UNKNOWN_NOT_MONOTONIC_LOGGED',
              caveat='Synthetic fixture and old raw only; no new ROS/Gazebo run')
(ROOT / 'analysis/q3_binding_preflight.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result, sort_keys=True))
