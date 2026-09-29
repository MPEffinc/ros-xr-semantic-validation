"""No-Gazebo D3 oracle-property regression using exact source IDs and ticks."""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'inputs'))
from d1_contract import canonical, make_envelope
import d3_tloracle_property as prop
from d3_silence import SourceSilence


def event(sample_id, receipt_ns, teleop=True, neutral=False):
    fields = {'teleop_enable': teleop, 'tracked': not neutral}
    origin = ({'origin': 'ORIGINAL_NEUTRAL', 'reason': 'stale_timeout'} if neutral else
              {'sample_id': sample_id, 'generation_id': 1,
               'source_timestamp_ns': receipt_ns,
               'receiver_receipt_monotonic_ns': receipt_ns,
               'native_state': {'isTracked': True}})
    return {'data': canonical(make_envelope(fields, origin, receipt_ns + 1)),
            'topic': '/s4b/d1/envelope'}


def tick(index):
    return {'data': json.dumps({'kind': 'health_tick', 'tick_id': f'tick:{index}',
                                 'source_sample_id': None}),
            'topic': '/s4b/d3/tick'}


def run():
    os.environ['INFO_REGIME'] = 'full'
    prop._source = SourceSilence()
    now = [1_000_000_000]
    prop.time.monotonic_ns = lambda: now[0]
    assert prop.abstract_message(event('docker:55', now[0]))['safe']
    now[0] += 200_000_000
    assert prop.abstract_message(event('docker:55', 1_000_000_000))['safe']
    now[0] = 1_250_000_000
    assert prop.abstract_message(tick(1))['safe']
    now[0] = 1_260_000_000
    assert not prop.abstract_message(tick(2))['safe']
    assert prop._source.last_sample_id == 'docker:55'
    assert prop._source.last_receipt_ns == 1_000_000_000
    now[0] = 1_280_000_000
    assert prop.abstract_message(event(None, now[0], teleop=False, neutral=True))['safe']
    assert not prop.abstract_message(tick(3))['safe']
    now[0] = 2_000_000_000
    assert prop.abstract_message(event('docker:76', now[0], teleop=False))['safe']
    now[0] = 2_300_000_000
    assert prop.abstract_message(tick(4))['safe']
    os.environ['INFO_REGIME'] = 'native'
    prop._source = SourceSilence()
    assert prop.abstract_message({'teleop_enable': True, 'tracked': True,
                                  'topic': '/s4b/d1/native_input'})['safe']
    assert prop.abstract_message(tick(5))['safe']
    assert prop._source.last_sample_id is None
    print('D3_PROPERTY_FULL_NATIVE_TICK_REGRESSION_PASS')


if __name__ == '__main__':
    run()
