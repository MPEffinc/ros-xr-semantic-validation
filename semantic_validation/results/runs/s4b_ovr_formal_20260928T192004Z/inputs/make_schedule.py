#!/usr/bin/env python3
"""Generate the scoped OpenVR W0-W5 formal schedule once (seed 20260922).

Per repetition the case blocks are shuffled, then the arms within each block.
Primary arms: B0, shim, B1, B2-native, B2-composed, B3 (I_FULL). B2-ST-composed is a
separately named diagnostic (NOT ROSMonitoring). R_AUTO blocks carry only the
policy-dependent defense arms (B0/shim are policy-independent; paired with the
repetition's R_EXPLICIT shim). Scoped omissions are listed in the freeze.
"""
import csv
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SEED = 20260922
B0, SHIM, B1, B2, B2C, B3, B2STC = (('b0', 'b0', 0, 0), ('shim', 'shim', 0, 0), ('b1', 'b1', 0, 0), ('b2', 'b2', 0, 0),
                                    ('b2c', 'b2', 1, 0), ('b3', 'b3', 0, 0), ('b2stc', 'b2', 1, 1))
BLOCKS = [('W0', 'R_EXPLICIT', [B0, SHIM]),
          ('W1', 'R_EXPLICIT', [B0, SHIM, B1, B2, B2C, B3, B2STC]),
          ('W2', 'R_EXPLICIT', [B0, SHIM, B1, B2, B2C, B3]),
          ('W3', 'R_EXPLICIT', [B0, SHIM, B1, B2C, B3]),
          ('W4', 'R_EXPLICIT', [B0, SHIM, B1, B2, B2C, B3, B2STC]),
          ('W4', 'R_AUTO', [B1, B2C, B3, B2STC]),
          ('W5', 'R_EXPLICIT', [B0, SHIM, B1, B2C, B3, B2STC]),
          ('W5', 'R_AUTO', [B1, B2C, B3, B2STC])]


def main():
    rng = random.Random(SEED)
    rows = []
    for rep in range(1, 6):
        blocks = BLOCKS.copy()
        rng.shuffle(blocks)
        for case, rearm, arms in blocks:
            arms = arms.copy()
            rng.shuffle(arms)
            for baseline, mode, composed, st in arms:
                rows.append(dict(order=len(rows) + 1, case_family='OVR', repetition=rep, case=case, rearm=rearm,
                                 baseline=baseline, mode=mode, composed=composed, st=st,
                                 trial_id=f'openvr_{baseline}_full_{case}_{rearm}_ovrr{rep:02d}', seed=SEED))
    assert len(rows) == 205 and len({r['trial_id'] for r in rows}) == 205
    with (ROOT / 'schedule.csv').open('w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator='\n')
        w.writeheader()
        w.writerows(rows)


if __name__ == '__main__':
    main()
