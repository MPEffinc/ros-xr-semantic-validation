#!/usr/bin/env python3
"""M7_admit analysis (R24). Frozen analyze_m7.trial (R17) for validity, H/F errors and blocks, plus a separate split for
messages the bridge labelled `delayed`: admitted / blocked by reason, their converter age (now - header.stamp) and
H/F errors of the admitted delayed messages; normal age of fresh messages.
  analyze_m7a.py trial <dir> <cond> | set <out.json> <schedule.csv> <raw_dir>"""
import csv, json, sys
from pathlib import Path
import numpy as np
sys.path.insert(0, "/m7/analysis"); import analyze_m7 as M
from frame_script import offset
def trial(d, cond):
    base = M.trial(d, "DYN_DELAY" if cond == "DYN_ADELAY" else cond); base["cond"] = cond
    if base["invalid"]: return base
    d = Path(d); C = M.jl(d / "converter.jsonl"); TF = M.jl(d / "tf_frame.jsonl")
    BR = {(b["seq"], round(b["out_stamp"], 6)): b["label"] for b in M.jl(d / "bridge.jsonl")}
    ts = next((x["sim"] for x in TF if x["k"] == "t_start"), None)
    dl = {"n": 0, "admitted": 0, "blocked": {}, "age_s": [], "eH": [], "eF": []}; fresh_age = []
    for c in C:
        lab = BR.get((c["seq"], round(c["header_stamp"], 6)), "fresh"); age = c["now"] - c["header_stamp"]
        if lab != "delayed": fresh_age.append(age); continue
        dl["n"] += 1; dl["age_s"].append(age)
        if not c["admit"]: dl["blocked"][c["why"]] = dl["blocked"].get(c["why"], 0) + 1; continue
        dl["admitted"] += 1; p, pF = np.array(c["p_out"]), np.array(c["p_F"])
        dl["eH"].append(float(np.linalg.norm(p - pF - np.array(offset(c["represented_at"], True, ts))) * 1000))
        dl["eF"].append(float(np.linalg.norm(p - pF - np.array(offset(c["now"], True, ts))) * 1000))
    q = lambda v: {"min": round(min(v), 4), "median": round(float(np.median(v)), 4), "max": round(max(v), 4)} if v else {"n": 0}
    base["delayed"] = {"n": dl["n"], "admitted": dl["admitted"], "blocked": dl["blocked"], "age_s": q(dl["age_s"]),
                       "err_hold_mm": M.stats(dl["eH"]), "err_follow_mm": M.stats(dl["eF"])}
    base["fresh_age_s"] = q(fresh_age); base["bridge_delayed_out"] = sum(1 for v in BR.values() if v == "delayed")
    return base
if __name__ == "__main__":
    if sys.argv[1] == "trial": print(json.dumps(trial(sys.argv[2], sys.argv[3]), indent=1, default=str))
    else:
        out, sched, raw = sys.argv[2], sys.argv[3], Path(sys.argv[4]); res = []
        for row in csv.DictReader(open(sched)):
            for d in sorted(raw.glob(row["trial_id"] + "*")): res.append(trial(d, row["cond"]))
        json.dump(res, open(out, "w"), indent=1, default=str); print(len(res))
