#!/usr/bin/env python3
"""M7_frame analysis (R17). Ground truth from the scripted frame function (harness/frame_script.offset with the logged
t_start), never from tf or the app:
  semantic H (hold the world target the input expressed at its representation time): truth = p_F + offset(represented_at)
  semantic F (follow the moving frame now):                                          truth = p_F + offset(now at conversion)
Per admitted converter record: error_H, error_F = |p_out - truth|. Adapter check: |(p_w - p_F) - offset(stamp)|.
Counts: blocked by reason; fault-free conditions -> blocks are false blocks. Descriptive: restamped messages whose
represented_at age exceeds TAU (what a representation-time age check would block).
  analyze_m7.py trial <dir> <cond> | set <out.json> <schedule.csv> <raw_dir>"""
import csv, json, math, sys
from pathlib import Path
import numpy as np
sys.path.insert(0, "/m7/harness"); sys.path.insert(0, "/m39/analysis")
from frame_script import offset
import analyze_m39 as A
TAU, W0, W1 = 0.100, 6.0, 7.5
def jl(p): return [json.loads(l) for l in open(p)] if Path(p).exists() else []
def stats(v): return {"n": len(v), "median": round(float(np.median(v)), 3), "p95": round(float(np.percentile(v, 95)), 3), "max": round(float(max(v)), 3)} if v else {"n": 0}
def trial(d, cond):
    d = Path(d); T = A.Trial(d); out = {"trial": d.name, "cond": cond}
    inv = [f for f in A.invalid_flags(T, "B0", "N0")] if T.t0 is not None else ["setup"]
    TF = jl(d / "tf_frame.jsonl"); C = jl(d / "converter.jsonl"); AD = jl(d / "adapter.jsonl"); BR = {(b["seq"], round(b["out_stamp"], 6)): b["label"] for b in jl(d / "bridge.jsonl")}
    if not TF or not C: inv.append("logs_missing")
    out["invalid"] = inv; out["arm"] = T.runner.get("arm")
    if inv: return out
    dyn = cond != "STATIC"; ts = next((x["sim"] for x in TF if x["k"] == "t_start"), None)
    eH, eF, eHw, eFw, blocked, ra_old = [], [], [], [], {}, 0
    for c in C:
        lab = BR.get((c["seq"], round(c["header_stamp"], 6)), "fresh")
        if lab == "restamped" and c["now"] - c["represented_at"] > TAU: ra_old += 1
        if not c["admit"]:
            blocked.setdefault((lab, c["why"]), 0); blocked[(lab, c["why"])] += 1; continue
        p, pF = np.array(c["p_out"]), np.array(c["p_F"])
        tH = pF + np.array(offset(c["represented_at"], dyn, ts)); tF = pF + np.array(offset(c["now"], dyn, ts))
        a, b = float(np.linalg.norm(p - tH) * 1000), float(np.linalg.norm(p - tF) * 1000)
        eH.append(a); eF.append(b)
        if W0 <= c["t"] <= W1: eHw.append(a); eFw.append(b)
    ad = [float(np.linalg.norm(np.array(x["p_w"]) - np.array(x["p_F"]) - np.array(offset(x["stamp"], dyn, ts))) * 1000) for x in AD if x.get("repr")]
    out.update(t_start=ts, err_hold_mm=stats(eH), err_follow_mm=stats(eF), err_hold_window_mm=stats(eHw), err_follow_window_mm=stats(eFw),
               blocked={f"{k[0]}:{k[1]}": v for k, v in blocked.items()}, admitted=len(eH), records=len(C),
               adapter_repr_err_mm=stats(ad), adapter_failed=sum(1 for x in AD if not x.get("repr")),
               restamped_with_old_represented_at=ra_old, wait_s_p95=round(float(np.percentile([c.get("wait_s", 0) for c in C if c["admit"]], 95)), 4) if eH else None)
    return out
if __name__ == "__main__":
    if sys.argv[1] == "trial": print(json.dumps(trial(sys.argv[2], sys.argv[3]), indent=1, default=str))
    else:
        out, sched, raw = sys.argv[2], sys.argv[3], Path(sys.argv[4]); res = []
        for row in csv.DictReader(open(sched)):
            for d in sorted(raw.glob(row["trial_id"] + "*")): res.append(trial(d, row["cond"]))
        json.dump(res, open(out, "w"), indent=1, default=str); print(len(res))
