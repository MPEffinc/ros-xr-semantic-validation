#!/usr/bin/env python3
"""Generate the scoped Docker C-ID formal schedule once (seed 20260922).

Per repetition, the four registered binding-fault kinds are shuffled, then 6
arms within each kind block: B0, shim, and B1/B2-native/B2-composed/B3 I_FULL.
I_NATIVE is NOT_RUN (UNOBSERVABLE by construction; setup evidence in C-ID Q1).
Old generation is the reused D5 formal evidence (not a C-ID trial).
"""
import csv
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SEED = 20260922
KINDS = ['MISSING_FIELD', 'MISSING_ID', 'DUPLICATE_ID', 'MISMATCH']
ARMS = [('b0', 0), ('shim', 0), ('b1', 0), ('b2', 0), ('b2', 1), ('b3', 0)]


def main():
    rng = random.Random(SEED)
    rows = []
    for repeat in range(1, 6):
        kinds = KINDS.copy()
        rng.shuffle(kinds)
        for kind in kinds:
            arms = ARMS.copy()
            rng.shuffle(arms)
            for mode, composed in arms:
                baseline = 'b2c' if composed else mode
                rows.append(dict(order=len(rows) + 1, case='CID', repetition=repeat, kind=kind, mode=mode,
                                 baseline=baseline, regime='full', composed=composed,
                                 trial_id=f'docker_{baseline}_full_{kind}_cidr{repeat:02d}', seed=SEED))
    assert len(rows) == 120 and len({r['trial_id'] for r in rows}) == 120
    with (ROOT / 'schedule.csv').open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)


if __name__ == '__main__':
    main()
