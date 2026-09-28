#!/usr/bin/env python3
"""Generate the scoped Docker D6 formal schedule once (seed 20260922).

Per repetition, 10 arms shuffled: B0, shim (policy-independent; run with the
R_EXPLICIT environment, which they ignore) and B1/B2-native/B2-composed/B3
I_FULL x R_EXPLICIT/R_AUTO. I_NATIVE arms are NOT_RUN in the formal campaign
(UNOBSERVABLE by construction; run once in D6Q1 setup).
"""
import csv
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SEED = 20260922
ARMS = [('b0', 0, 'R_EXPLICIT', 0), ('shim', 0, 'R_EXPLICIT', 0)]
ARMS += [(m, c, p, 1) for p in ('R_EXPLICIT', 'R_AUTO') for m, c in (('b1', 0), ('b2', 0), ('b2', 1), ('b3', 0))]


def main():
    rng = random.Random(SEED)
    rows = []
    for repeat in range(1, 6):
        arms = ARMS.copy()
        rng.shuffle(arms)
        for mode, composed, policy, applies in arms:
            baseline = 'b2c' if composed else mode
            rows.append(dict(order=len(rows) + 1, case='D6', repetition=repeat, rearm=policy,
                             policy_applies=applies, mode=mode, baseline=baseline, regime='full',
                             composed=composed, trial_id=f'docker_{baseline}_full_{policy}_d6r{repeat:02d}',
                             seed=SEED))
    assert len(rows) == 50 and len({r['trial_id'] for r in rows}) == 50
    with (ROOT / 'schedule.csv').open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)


if __name__ == '__main__':
    main()
