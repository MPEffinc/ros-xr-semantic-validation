"""Host-only invariant: Q4 native log hash changes, safety predicate does not."""
import importlib.util
import json
import os
import sys
import tempfile
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
Q3 = ROOT.parent / 's4b_cp5b_measurement_20260923T054101Z'
sys.path.insert(0, str(ROOT / 'inputs'))
from d1_contract import payload_hash


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


old = module('q3_property', Q3 / 'inputs/d1_tloracle_property.py')
new = module('q4_property', ROOT / 'inputs/d1_tloracle_property.py')
os.environ['INFO_REGIME'] = 'native'
summary = []
with tempfile.TemporaryDirectory(prefix='xr_q4_property_') as temp:
    log_path = Path(temp) / 'property.jsonl'
    os.environ['XR_D1_PROPERTY_LOG'] = str(log_path)
    for name in ('docker_b2_native_q3b2nsetup01', 'docker_b2c_native_q3b2cnsetup01'):
        trial = Q3 / 'raw' / name
        events = [json.loads(x) for x in (trial / 'monitor_native_events.jsonl').read_text().splitlines() if x]
        statuses = [json.loads(x) for x in (trial / 'monitor_native_status.jsonl').read_text().splitlines() if x]
        statuses = [x for x in statuses if x.get('status') == 'event']
        assert len(events) == len(statuses)
        safe_same, hash_same = 0, 0
        for event, status in zip(events, statuses):
            log_path.write_text('')
            a = dict(old.abstract_message(event))
            log_path.write_text('')
            b = dict(new.abstract_message(event))
            row = json.loads(log_path.read_text())
            safe_same += a['safe'] == b['safe'] == bool(status['verdict'])
            hash_same += row['payload_sha256'] == payload_hash(status['payload'])
        hashes = [payload_hash(x['payload']) for x in statuses]
        summary.append(dict(trial=name, events=len(events), same_predicate=safe_same,
                            canonical_payload_hashes=hash_same,
                            duplicate_payload_hashes=sum(n > 1 for n in Counter(hashes).values())))
    # Identical payload twice is intentionally ambiguous, never fabricated ID.
    duplicate = dict(statuses[0]['payload'])
    assert payload_hash(duplicate) == payload_hash(dict(duplicate))
    assert len([duplicate, dict(duplicate)]) != len({payload_hash(duplicate)})
    policy_fixtures = [
        dict(teleop_enable=True, tracked=True, expected=True),
        dict(teleop_enable=True, tracked=False, expected=False),
        dict(teleop_enable=False, tracked=False, expected=True),
    ]
    for fixture in policy_fixtures:
        message = dict(teleop_enable=fixture['teleop_enable'],
                       tracked=fixture['tracked'], time=123.456,
                       topic='/s4b/d1/native_input')
        log_path.write_text('')
        prior = dict(old.abstract_message(message))
        log_path.write_text('')
        current = dict(new.abstract_message(message))
        assert prior['safe'] is current['safe'] is fixture['expected']
        assert json.loads(log_path.read_text())['payload_sha256'] == payload_hash(
            dict(teleop_enable=fixture['teleop_enable'], tracked=fixture['tracked']))
del os.environ['XR_D1_PROPERTY_LOG']
result = dict(status='PASS_NON_GAZEBO_PREFLIGHT', trials=summary,
              policy_fixture_count=3,
              duplicate_payload_association='UNKNOWN_NOT_UNIQUE',
              native_age_generation_provided_to_defense=False,
              official_monitor_modified=False)
assert all(x['events'] == x['same_predicate'] == x['canonical_payload_hashes'] and
           x['duplicate_payload_hashes'] == 0 for x in summary)
(ROOT / 'analysis/q4_property_preflight.json').write_text(json.dumps(result, indent=2,
                                                             sort_keys=True) + '\n')
print(json.dumps(result, sort_keys=True))
