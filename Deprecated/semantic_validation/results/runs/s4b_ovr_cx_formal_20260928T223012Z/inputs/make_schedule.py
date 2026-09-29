#!/usr/bin/env python3
"""Generate the scoped OpenVR C-ID/C-MON formal schedule once (seed 20260922).

Per repetition the 20 qualified C-X cells are shuffled (C-ID MISMATCH and
DUPLICATE_ID x {B0, shim, B1, B2-composed, B3, B2-ST-composed}; C-MON {B0, shim,
B2-composed x ABSENT/DISCONNECT/NONRESPONSIVE, B2-native x DISCONNECT, B1 and B3
gate crash}). B2-ST is a separately named diagnostic, not ROSMonitoring.
"""
import csv
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SEED = 20260922
ARMS = {'b0': ('b0', 0, 0), 'shim': ('shim', 0, 0), 'b1': ('b1', 0, 0), 'b2': ('b2', 0, 0), 'b2c': ('b2', 1, 0),
        'b3': ('b3', 0, 0), 'b2stc': ('b2', 1, 1)}
CELLS = [(a, k, 'NONE', 'CID') for k in ('MISMATCH', 'DUPLICATE_ID') for a in ('b0', 'shim', 'b1', 'b2c', 'b3', 'b2stc')]
CELLS += [('b0', 'NONE', 'NONE', 'CMON'), ('shim', 'NONE', 'NONE', 'CMON')]
CELLS += [('b2c', 'NONE', f, 'CMON') for f in ('ORACLE_ABSENT', 'ORACLE_DISCONNECT', 'ORACLE_NONRESPONSIVE')]
CELLS += [('b2', 'NONE', 'ORACLE_DISCONNECT', 'CMON'), ('b1', 'NONE', 'B1_GATE_FAIL', 'CMON'), ('b3', 'NONE', 'B3_GATE_FAIL', 'CMON')]


def main():
    rng = random.Random(SEED)
    rows = []
    for rep in range(1, 6):
        cells = CELLS.copy()
        rng.shuffle(cells)
        for arm, kind, fault, fam in cells:
            mode, composed, st = ARMS[arm]
            tag = kind if kind != 'NONE' else fault
            rows.append(dict(order=len(rows) + 1, family=fam, repetition=rep, baseline=arm, mode=mode, composed=composed, st=st,
                             cid_kind=kind, fault=fault,
                             expect_motion=0 if (arm == 'b2c' and fault == 'ORACLE_ABSENT') else 1,
                             trial_id=f'openvr_{arm}_full_{tag}_cxr{rep:02d}', seed=SEED))
    assert len(rows) == 100 and len({r['trial_id'] for r in rows}) == 100
    with (ROOT / 'schedule.csv').open('w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator='\n')
        w.writeheader()
        w.writerows(rows)


if __name__ == '__main__':
    main()
