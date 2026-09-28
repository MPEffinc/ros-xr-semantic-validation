#!/usr/bin/env python3
"""Generate the scoped Docker C-MON formal schedule once (seed 20260922).

Per repetition, the 12 qualified C-MON Q3 cells are shuffled:
B0 and shim (no fault); B2-native and B2-composed I_FULL x {ORACLE_ABSENT,
ORACLE_DISCONNECT, ORACLE_NONRESPONSIVE}; B2-native and B2-composed I_NATIVE x
ORACLE_DISCONNECT; B1 and B3 I_FULL gate-process failure. The other registered
cells are NOT_RUN (scoped; see the design report).
"""
import csv
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SEED = 20260922
CELLS = [('b0', 'b0', 0, 'full', 'NONE'), ('shim', 'shim', 0, 'full', 'NONE')]
for fault in ('ORACLE_ABSENT', 'ORACLE_DISCONNECT', 'ORACLE_NONRESPONSIVE'):
    CELLS += [('b2', 'b2', 0, 'full', fault), ('b2c', 'b2', 1, 'full', fault)]
CELLS += [('b2', 'b2', 0, 'native', 'ORACLE_DISCONNECT'), ('b2c', 'b2', 1, 'native', 'ORACLE_DISCONNECT'),
          ('b1', 'b1', 0, 'full', 'B1_GATE_FAIL'), ('b3', 'b3', 0, 'full', 'B3_GATE_FAIL')]


def main():
    rng = random.Random(SEED)
    rows = []
    for repeat in range(1, 6):
        cells = CELLS.copy()
        rng.shuffle(cells)
        for baseline, mode, composed, regime, fault in cells:
            rows.append(dict(order=len(rows) + 1, case='CMON', repetition=repeat, fault=fault, mode=mode,
                             baseline=baseline, regime=regime, composed=composed,
                             expect_motion=0 if (baseline == 'b2c' and fault == 'ORACLE_ABSENT') else 1,
                             trial_id=f'docker_{baseline}_{regime}_{fault}_cmonr{repeat:02d}', seed=SEED))
    assert len(rows) == 60 and len({r['trial_id'] for r in rows}) == 60
    with (ROOT / 'schedule.csv').open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)


if __name__ == '__main__':
    main()
