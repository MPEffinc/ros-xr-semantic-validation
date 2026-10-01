#!/usr/bin/env python3
import csv, os, random
CELLS = [('C1_RELEASE', 'B0'), ('C1_RELEASE', 'PAUSE'), ('C1_RELEASE', 'HOLD'),
         ('C2M_DEACT_CACHED_MOVING', 'B0'), ('C2M_DEACT_CACHED_MOVING', 'REARM_V'), ('C2M_DEACT_CACHED_MOVING', 'REARM_C')]
rng = random.Random(20261002); rows = []; o = 1
for rep in (1, 2, 3):
    b = list(CELLS); rng.shuffle(b)
    for c, d in b: rows.append(dict(order=o, trial_id=f'{c}__{d}__r{rep}', case=c, defense=d, rep=rep)); o += 1
with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'schedule.csv'), 'w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
print(len(rows))
