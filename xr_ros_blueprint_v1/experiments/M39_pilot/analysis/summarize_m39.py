#!/usr/bin/env python3
"""Aggregate the frozen per-trial analysis (analyze_m39.py campaign output) into per-cell counts (R03 §9).
Only counting; no measure or threshold is computed here. Per slot the first valid attempt is used; invalid attempts
are listed. Also evaluates the R03 §7 extension rule (disagreement among the 3 valid reps of a cell).
  summarize_m39.py <campaign.json> <out.json>"""
import json, sys
from collections import defaultdict
C = json.load(open(sys.argv[1]))["trials"]
slots = defaultdict(list)
for t in C: slots[t["slot"]].append(t)
used, invalid_attempts = [], []
for s, ts in slots.items():
    ts.sort(key=lambda t: t["attempt_dir"])
    for t in ts:
        if t["invalid"]: invalid_attempts.append({"attempt": t["attempt_dir"], "invalid": t["invalid"]})
    v = [t for t in ts if not t["invalid"]]
    used.append(v[0] if v else dict(ts[-1], slot_invalid=True))
def outcome(t, k):
    x = t.get(k)
    if k == "Normal" and t["cond"] != "N0": return None
    if x is None: return None
    if k == "P_resume": return "NE" if not x["evaluable"] else ("pass" if x["pass"] else "fail")
    return "pass" if x["pass"] else "fail"
POL = ["Normal", "P_stop", "P_resume", "Live", "P_rearm"]
cells = defaultdict(list)
for t in used: cells[(t["arm"], t["cond"])].append(t)
table = {}
for (a, c), ts in sorted(cells.items()):
    row = {"n_slots": len(ts), "n_valid": sum(1 for t in ts if not t.get("slot_invalid")), "masked": sum(1 for t in ts if t.get("masked"))}
    disagree = []
    for k in POL:
        o = [outcome(t, k) for t in ts if not t.get("slot_invalid")]
        if all(x is None for x in o): continue
        row[k] = {v: o.count(v) for v in ("pass", "fail", "NE") if o.count(v)}
        if len({x for x in o if x}) > 1: disagree.append(k)
        mk = [t[k].get("masked") for t in ts if t.get(k) and isinstance(t[k], dict) and "masked" in t[k]]
        if any(mk): row[k]["masked"] = sum(1 for m in mk if m)
    if len({t.get("masked") for t in ts}) > 1: disagree.append("masked")
    row["extension_required"] = disagree
    row["partial_contract_all_pass"] = all(outcome(t, k) in (None, "pass", "NE") for t in ts for k in ["Normal", "P_stop", "P_resume", "Live"])
    row["full_contract_all_pass"] = row["partial_contract_all_pass"] and all(outcome(t, "P_rearm") in (None, "pass") for t in ts)
    table[f"{a}/{c}"] = row
json.dump({"cells": table, "invalid_attempts": invalid_attempts, "n_attempts": len(C), "n_slots": len(slots)}, open(sys.argv[2], "w"), indent=1)
print(json.dumps(table, indent=1))
