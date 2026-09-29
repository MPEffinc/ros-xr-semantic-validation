"""Test only the D1 predicate mapping used by official TLOracle/Reelay."""
import json
import os
import sys
import time
from pathlib import Path

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / 'inputs'))
import reelay
from d1_contract import make_envelope
import d1_tloracle_property as prop


def message(tracked=True, source_age_ns=1_000_000, neutral=False, ungripped=False):
    now = time.monotonic_ns()
    fields = {'teleop_enable': not (neutral or ungripped), 'tracked': tracked,
              'header': {'stamp': {'sec': 123, 'nanosec': 456}, 'frame_id': 'unity_world'}}
    origin = ({'origin': 'ORIGINAL_NEUTRAL', 'reason': 'stale_timeout'} if neutral else
              {'sample_id': 'unit:1', 'generation_id': 1,
               'native_state': {'isTracked': tracked},
               'source_timestamp_ns': now - source_age_ns})
    return {'data': json.dumps(make_envelope(fields, origin, now)), 'time': time.time()}


os.environ['INFO_REGIME'] = 'full'
monitor = reelay.discrete_timed_monitor(pattern=prop.PROPERTY)
cases = [('valid', message(), True),
         ('ungripped_source', message(ungripped=True), True),
         ('untracked', message(tracked=False), False),
         ('old', message(source_age_ns=300_000_000), False),
         ('neutral', message(neutral=True), True)]
results = []
last_verdict = True
for name, event, expected in cases:
    abstracted = prop.abstract_message(event)
    verdict = monitor.update(abstracted)
    if verdict:
        last_verdict = verdict['value']
    assert abstracted['safe'] is expected, (name, abstracted)
    assert last_verdict is expected, (name, verdict, last_verdict)
    results.append({'case': name, 'safe': abstracted['safe'], 'reelay_effective': last_verdict,
                    'reelay_update': verdict})
os.environ['INFO_REGIME'] = 'native'
assert prop.abstract_message({'teleop_enable': True, 'tracked': True, 'time': time.time()})['safe'] is True
assert prop.abstract_message({'teleop_enable': True, 'tracked': False, 'time': time.time()})['safe'] is False
summary = {'full_cases': results, 'native_wire_gate': 'PASS_BOUNDED; age/generation UNOBSERVABLE',
           'evidence_level': 'OFFLINE_PROPERTY_ONLY_NOT_ROS_GAZEBO'}
(root / 'analysis/d1_property_offline.json').write_text(json.dumps(summary, indent=2) + '\n')
print(json.dumps(summary, sort_keys=True))
