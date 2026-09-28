#!/usr/bin/env python3
"""Generate the complete preregistered Docker D3 formal schedule once.

Seed 20260922 (XRROS-S4-1.0.0 section 8) shuffles the ten comparison arms
within each of five repetitions. Q6 setup cells are NOT formal repetitions.
"""
import csv
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SEED = 20260922
ARMS = [
    ('b0', 'full', 0), ('shim', 'full', 0),
    ('b1', 'native', 0), ('b1', 'full', 0),
    ('b2', 'native', 0), ('b2', 'full', 0),
    ('b2', 'native', 1), ('b2', 'full', 1),
    ('b3', 'native', 0), ('b3', 'full', 0),
]


def main():
    rng = random.Random(SEED)
    rows = []
    for repeat in range(1, 6):
        arms = ARMS.copy()
        rng.shuffle(arms)
        for mode, regime, composed in arms:
            baseline = 'b2c' if composed else mode
            attempt_id = f'd3r{repeat:02d}'
            rows.append(dict(order=len(rows)+1, case='D3', repetition=repeat,
                             mode=mode, baseline=baseline, regime=regime,
                             composed=composed, attempt_id=attempt_id,
                             trial_id=f'docker_{baseline}_{regime}_{attempt_id}',
                             seed=SEED))
    assert len(rows) == 50 and len({r['trial_id'] for r in rows}) == 50
    with (ROOT / 'schedule.csv').open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)


if __name__ == '__main__':
    main()
