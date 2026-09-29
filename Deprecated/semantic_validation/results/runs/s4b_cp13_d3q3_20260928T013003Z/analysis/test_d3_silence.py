"""No-Gazebo regression for the preregistered D3 receipt-silence clock."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'inputs'))
from d3_silence import SourceSilence, LIMIT_NS


def run():
    s = SourceSilence()
    assert s.tick(100)['state'] == 'UNOBSERVABLE'
    assert s.receive('docker:55', 1_000_000_000, True, True, 1)
    before = s.tick(1_000_000_000 + LIMIT_NS)
    assert before['state'] == 'FRESH' and before['age_ns'] == LIMIT_NS
    for tick in range(1_000_000_000, 1_250_000_000, 20_000_000):
        assert s.tick(tick)['last_sample_id'] == 'docker:55'
    assert not s.receive('docker:55', 1_240_000_000, True, True, 1)
    assert s.tick(1_250_000_001)['state'] == 'SOURCE_SILENCE'
    assert s.tick(1_500_000_000)['last_receipt_ns'] == 1_000_000_000
    assert s.genuine_receipt_count == 1 and s.duplicate_count == 1
    # Identical payload may be an independent source sample: identity wins.
    assert s.receive('docker:76', 2_000_000_000, False, True, 1)
    assert s.tick(2_500_000_000)['state'] == 'NO_ACTIVE_CONTROL'
    assert s.receive('docker:77', 2_550_000_000, True, True, 2)
    assert s.tick(2_560_000_000)['state'] == 'FRESH'
    assert s.generation_id == 2 and s.genuine_receipt_count == 3
    try:
        s.receive('docker:78', 2_540_000_000, True, True, 2)
        raise AssertionError('nonmonotonic receipt was accepted')
    except ValueError:
        pass
    assert s.last_sample_id == 'docker:77'
    print('D3_SOURCE_SILENCE_12_ASSERTIONS_PASS')


if __name__ == '__main__':
    run()
