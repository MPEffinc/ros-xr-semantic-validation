"""XRROS-S4-1.0.0 D4-L post-gate delivery delay and capture length.

D4-L keeps the fresh per-sample stamp (stamp == creation time) and delays
DELIVERY after the B1 source decision by a registered FIFO delay. Capture lasts
the base fixture (4.8 s) plus the registered delay plus 2 s, identical across
arms at that delay. Ticks stay at 50 Hz for the whole capture. With no
XR_DELIVERY_DELAY the values reproduce the qualified 6 s / 300-tick runtime.
"""
import os

DELAYS = {'L000': 0, 'L050': 50_000_000, 'L150': 150_000_000,
          'L350': 350_000_000, 'L750': 750_000_000}
BASE_FIXTURE_NS = 4_800_000_000
TICK_NS = 20_000_000


def delay_ns():
    name = os.environ.get('XR_DELIVERY_DELAY')
    return 0 if name is None else DELAYS[name]


def capture_ns():
    if os.environ.get('XR_DELIVERY_DELAY') is None:
        return 6_000_000_000
    return BASE_FIXTURE_NS + delay_ns() + 2_000_000_000


def tick_count():
    return capture_ns() // TICK_NS
