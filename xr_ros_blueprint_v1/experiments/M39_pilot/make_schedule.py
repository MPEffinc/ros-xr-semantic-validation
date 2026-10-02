#!/usr/bin/env python3
"""R03 §8 schedule: 3 repetition blocks; condition order shuffled per block (random.Random(39 + rep)); arm order within
(condition, rep) = rotation of [B0, B1, C1] by (cond_index + rep) % 3. Writes schedule.csv."""
import csv, random
ARMS = ["B0", "B1", "C1"]; CONDS = ["N0", "N1", "I1", "I2", "I3"]
rows = []; n = 0
for rep in (1, 2, 3):
    order = CONDS[:]; random.Random(39 + rep).shuffle(order)
    for c in order:
        k = (CONDS.index(c) + rep) % 3; arms = ARMS[k:] + ARMS[:k]
        for a in arms:
            n += 1; rows.append({"seq": n, "trial_id": f"T{n:02d}_{a}_{c}_r{rep}", "arm": a, "cond": c, "rep": rep})
with open("schedule.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n"); w.writeheader(); w.writerows(rows)
print(len(rows))
