"""Official TLOracle/Reelay property preflight; no ROS graph or Gazebo."""
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'inputs'))
import reelay
from d1_contract import make_envelope, verify_transport
import d1_tloracle_property as prop


def full(teleop=True, tracked=True, age_ns=1_000_000, generation=1,
         neutral=False, missing=False):
    now = time.monotonic_ns()
    payload = {'teleop_enable': teleop, 'tracked': tracked,
               'header': {'stamp': {'sec': 123, 'nanosec': 456},
                          'frame_id': 'unity_world'}}
    selected = ({'origin': 'ORIGINAL_NEUTRAL', 'reason': 'stale_timeout'} if neutral
                else {'sample_id': 'preflight:1', 'generation_id': generation,
                      'native_state': {'isTracked': tracked},
                      'source_timestamp_ns': now - age_ns})
    if missing:
        selected.pop('generation_id')
    envelope = make_envelope(payload, selected, now)
    assert verify_transport(envelope) == payload
    assert envelope['selected_origin'] == selected
    return {'data': json.dumps(envelope)}


os.environ['INFO_REGIME'] = 'full'
monitor = reelay.discrete_timed_monitor(pattern=prop.PROPERTY)
cases = [
    ('active', full(), True),
    ('reference', full(), True),
    ('ungripped_neutral', full(teleop=False), True),
    ('original_neutral', full(teleop=False, neutral=True), True),
    ('invalid_tracked', full(tracked=False), False),
    ('stale', full(age_ns=300_000_000), False),
    ('future', full(age_ns=-20_000_000), False),
    ('old_generation', full(generation=0), False),
    ('missing_generation', full(missing=True), False),
]
results = []
effective = True
for name, message, expected in cases:
    state = prop.abstract_message(message)
    verdict = monitor.update(state)
    if verdict:
        effective = verdict['value']
    assert state['safe'] is expected, (name, state)
    assert effective is expected, (name, verdict, effective)
    results.append({'case': name, 'safe': state['safe'], 'effective': effective})

os.environ['INFO_REGIME'] = 'native'
native_valid = dict(prop.abstract_message({'teleop_enable': True, 'tracked': True}))
native_invalid = dict(prop.abstract_message({'teleop_enable': True, 'tracked': False}))
assert native_valid['safe'] is True and native_invalid['safe'] is False
tampered = full()['data']
tampered = json.loads(tampered)
tampered['original_payload']['tracked'] = False
try:
    verify_transport(tampered)
except ValueError:
    pass
else:
    raise AssertionError('tampered ROS payload passed transport hash')

summary = dict(status='PASS_NON_GAZEBO_PREFLIGHT', cases=results,
               native='wire tracked/teleop only; age and generation UNOBSERVABLE',
               atomic_state_payload_binding=True, tamper_rejected=True,
               caveat='No official ROSMonitoring filter or downstream graph in this test')
(ROOT / 'analysis/property_preflight.json').write_text(json.dumps(summary, indent=2) + '\n')
print(json.dumps(summary, sort_keys=True))
