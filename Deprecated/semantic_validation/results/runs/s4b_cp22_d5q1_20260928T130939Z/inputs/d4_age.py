"""XRROS-S4-1.0.0 D4 source-timestamp conditions and freshness profiles.

Every real source sample gets its own creation time ``sample_ns`` (host
CLOCK_MONOTONIC) and its own stamped ``source_timestamp_ns``. The stamp is
derived per sample, never reused across a phase, EXCEPT for the explicitly
registered historical epoch anomaly, whose stamp is the literal value 1.0 s.
"""
import os

# condition id -> (kind, value)
CONDITIONS = {
    'A000': ('age_offset_ns', 0),
    'A050': ('age_offset_ns', 50_000_000),
    'A150': ('age_offset_ns', 150_000_000),
    'A350': ('age_offset_ns', 350_000_000),
    'A750': ('age_offset_ns', 750_000_000),
    'H1P0': ('historical_epoch_value_s', 1.0),   # NOT an ordinary 1.0 s age offset
    'FUT1S': ('future_offset_ns', 1_000_000_000),  # +1 s clock-contract violation
}
PROFILES = {'F100': 100_000_000, 'F250': 250_000_000, 'F500': 500_000_000}
FUTURE_TOLERANCE_NS = 5_000_000     # [-5 ms, 0] allowed as measurement tolerance
CLOCK_UNCERTAINTY_NS = 1_000_000    # verified common-clock uncertainty bound


def stamp(condition, sample_ns):
    kind, value = CONDITIONS[condition]
    if kind == 'age_offset_ns':
        return int(sample_ns) - value
    if kind == 'future_offset_ns':
        return int(sample_ns) + value
    return int(round(value * 1_000_000_000))  # literal historical epoch value 1.0 s


def expected(age_ns, freshness_ns):
    """Registered policy for a teleop-true sample: True accept, False reject, None UNKNOWN."""
    u = CLOCK_UNCERTAINTY_NS
    low = -FUTURE_TOLERANCE_NS
    if abs(age_ns - freshness_ns) <= u or abs(age_ns - low) <= u:
        return None  # straddles a boundary within clock uncertainty
    return low <= age_ns <= freshness_ns


def condition_from_env():
    condition = os.environ['AGE_CONDITION']
    assert condition in CONDITIONS, condition
    return condition
