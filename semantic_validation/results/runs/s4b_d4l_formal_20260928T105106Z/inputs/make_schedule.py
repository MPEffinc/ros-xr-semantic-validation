#!/usr/bin/env python3
"""Generate the reduced (scoped) Docker D4-L formal schedule once.

Seed 20260922. Per repetition the five delay blocks are shuffled, then arms
within each block. Selection (see S4B_CP21_D4L_FORMAL_FREEZE.md):
  * every delay: B0, shim, B1 I_FULL (runtime profile-invariant; run at F250);
  * B2-native / B2-composed / B3 I_FULL at seven delay/profile cells;
  * I_NATIVE B1/B2/B2c/B3 at L750 only (freshness unobservable by construction).
All other registered combinations are NOT_RUN (monotone inference or scoped).
"""
import csv
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SEED = 20260922
DELAYS = ['L000', 'L050', 'L150', 'L350', 'L750']
FULL_CELLS = {'L000': ['F100'], 'L050': ['F100'], 'L150': ['F100', 'F250'],
              'L350': ['F250', 'F500'], 'L750': ['F500']}


def block(delay):
    arms = [('b0', 'full', 0, 'F250', 0), ('shim', 'full', 0, 'F250', 0), ('b1', 'full', 0, 'F250', 0)]
    for profile in FULL_CELLS[delay]:
        arms += [('b2', 'full', 0, profile, 1), ('b2', 'full', 1, profile, 1), ('b3', 'full', 0, profile, 1)]
    if delay == 'L750':
        arms += [('b1', 'native', 0, 'F250', 0), ('b2', 'native', 0, 'F250', 0),
                 ('b2', 'native', 1, 'F250', 0), ('b3', 'native', 0, 'F250', 0)]
    return arms


def main():
    rng = random.Random(SEED)
    rows = []
    for repeat in range(1, 6):
        delays = DELAYS.copy()
        rng.shuffle(delays)
        for delay in delays:
            arms = block(delay)
            rng.shuffle(arms)
            for mode, regime, composed, profile, applies in arms:
                baseline = 'b2c' if composed else mode
                rows.append(dict(order=len(rows) + 1, case='D4L', repetition=repeat, condition='A000',
                                 delay=delay, profile=profile, profile_applies=applies, mode=mode,
                                 baseline=baseline, regime=regime, composed=composed,
                                 trial_id=f'docker_{baseline}_{regime}_{delay}_{profile}_d4lr{repeat:02d}',
                                 seed=SEED))
    assert len(rows) == 200 and len({r['trial_id'] for r in rows}) == 200
    with (ROOT / 'schedule.csv').open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)


if __name__ == '__main__':
    main()
