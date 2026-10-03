#!/usr/bin/env python3
"""M17 analysis (R28). Joins gate decisions with the harness truth log by cmd_id (truth is never read by the gates).
  normal: admitted / total (false blocks = blocked normal); forged: admitted / total (by condition);
  forged_equivalent (deviation <= 1 mm from the honest target): reported separately;
  block reasons; decision latency (median / p95 / max ms); commands without a decision.
Invalid: setup failure, fewer than 300 commands, a gate with no decisions.
  analyze_m17.py trial <dir> <arm> <cond> | set <out.json> <schedule.csv> <raw_dir>"""
import csv, json, sys
from pathlib import Path
import numpy as np
def jl(p): return [json.loads(l) for l in open(p) if l.strip()] if Path(p).exists() else []
def trial(d, arm, cond):
    d = Path(d); S = (jl(d / "setup.json") or [{}])[0]; T = {x["cmd_id"]: x for x in jl(d / "truth.jsonl")}; G = {x["cmd_id"]: x for x in jl(d / "gate.jsonl")}
    out = {"trial": d.name, "arm": arm, "cond": cond, "invalid": []}
    if S.get("setup") != "ok": out["invalid"].append("setup")
    if len(T) < 300: out["invalid"].append("few_commands")
    if not G: out["invalid"].append("no_decisions")
    if out["invalid"]: return out
    cls = {}; why = {}; lat = []
    for i, t in T.items():
        g = G.get(i); c = cls.setdefault(t["label"], {"n": 0, "admitted": 0, "undecided": 0})
        c["n"] += 1
        if g is None: c["undecided"] += 1; continue
        c["admitted"] += g["admit"]; lat.append(g["latency_ms"])
        if not g["admit"]: why[f'{t["label"]}:{g["why"]}'] = why.get(f'{t["label"]}:{g["why"]}', 0) + 1
    out.update(classes=cls, blocked=why, latency_ms={"median": round(float(np.median(lat)), 3), "p95": round(float(np.percentile(lat, 95)), 3), "max": round(float(max(lat)), 3)},
               commands=len(T), decisions=len(G), forged_dev_mm={"min": round(min(t["dev_m"] for t in T.values() if t["label"] != "normal") * 1000, 2),
                                                                 "max": round(max(t["dev_m"] for t in T.values() if t["label"] != "normal") * 1000, 2)} if any(t["label"] != "normal" for t in T.values()) else None)
    return out
if __name__ == "__main__":
    if sys.argv[1] == "trial": print(json.dumps(trial(*sys.argv[2:5]), indent=1))
    else:
        out, sched, raw = sys.argv[2], sys.argv[3], Path(sys.argv[4]); res = []
        for row in csv.DictReader(open(sched)):
            for d in sorted(raw.glob(row["trial_id"] + "*")): res.append(trial(d, row["arm"], row["cond"]))
        json.dump(res, open(out, "w"), indent=1); print(len(res))
