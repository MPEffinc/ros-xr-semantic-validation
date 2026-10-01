#!/usr/bin/env python3
"""Frozen P1 schedule: 18 cells x 3 repetitions = 54 Gazebo trials, rep-major blocks, shuffled
within each block with seed 20261001."""
import csv, os, random
CELLS = [('C0_NORMAL', 'B0'),
         ('C1_RELEASE', 'B0'), ('C1_RELEASE', 'D_TO'), ('C1_RELEASE', 'PAUSE'),
         ('C2_DEACT_CACHED', 'B0'), ('C2_DEACT_CACHED', 'REARM_V'), ('C2_DEACT_CACHED', 'REARM_C'),
         ('C3_TRACK_GLITCH', 'B0'), ('C3_TRACK_GLITCH', 'REARM_V'), ('C3_TRACK_GLITCH', 'REARM_C'),
         ('C4L_RECENTER', 'B0'), ('C4L_RECENTER', 'JUMP'), ('C4L_RECENTER', 'EPOCH_G'), ('C4L_RECENTER', 'EPOCH_A'),
         ('C4S_RECENTER', 'B0'), ('C4S_RECENTER', 'JUMP'), ('C4S_RECENTER', 'EPOCH_G'), ('C4S_RECENTER', 'EPOCH_A')]
REPS = 3
rng = random.Random(20261001)
rows, order = [], 1
for rep in range(1, REPS + 1):
    block = list(CELLS); rng.shuffle(block)
    for case, dfn in block:
        rows.append(dict(order=order, trial_id=f'{case}__{dfn}__r{rep}', case=case, defense=dfn, rep=rep)); order += 1
p = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'schedule.csv')
with open(p, 'w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
print(len(rows))
