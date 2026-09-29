#!/usr/bin/env python3
"""Generate the complete preregistered Docker D4 formal schedule once.

Seed 20260922 (XRROS-S4-1.0.0 section 8). Per repetition, the seven registered
source-timestamp conditions are shuffled, then the 18 arms are shuffled within
each condition block. Profile-independent arms (B0, shim, and every I_NATIVE
arm, whose predicates have no source-time input) run once per condition with
the default F250 environment and profile_applies=0. D4Q1/D4Q2 setup cells are
not formal repetitions.
"""
import csv
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SEED = 20260922
CONDITIONS = ['A000', 'A050', 'A150', 'A350', 'A750', 'H1P0', 'FUT1S']
ARMS = [('b0', 'full', 0, 'F250', 0), ('shim', 'full', 0, 'F250', 0)]
ARMS += [(m, 'native', c, 'F250', 0) for m, c in (('b1', 0), ('b2', 0), ('b2', 1), ('b3', 0))]
ARMS += [(m, 'full', c, p, 1) for m, c in (('b1', 0), ('b2', 0), ('b2', 1), ('b3', 0))
         for p in ('F100', 'F250', 'F500')]


def main():
    rng = random.Random(SEED)
    rows = []
    for repeat in range(1, 6):
        conditions = CONDITIONS.copy()
        rng.shuffle(conditions)
        for condition in conditions:
            arms = ARMS.copy()
            rng.shuffle(arms)
            for mode, regime, composed, profile, applies in arms:
                baseline = 'b2c' if composed else mode
                rows.append(dict(order=len(rows) + 1, case='D4', repetition=repeat, condition=condition,
                                 profile=profile, profile_applies=applies, mode=mode, baseline=baseline,
                                 regime=regime, composed=composed,
                                 trial_id=f'docker_{baseline}_{regime}_{condition}_{profile}_d4r{repeat:02d}',
                                 seed=SEED))
    assert len(rows) == 630 and len({r['trial_id'] for r in rows}) == 630
    with (ROOT / 'schedule.csv').open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)


if __name__ == '__main__':
    main()
