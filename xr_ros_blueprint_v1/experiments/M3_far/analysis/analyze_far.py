#!/usr/bin/env python3
"""M3_far analysis (R25). Frozen analyze_ord.trial (R18) plus, for the injected distant trajectory:
  - target difference: EE distance between EE(captured_t) (the pose the arm had when the captured trajectory was
    produced) and EE(injection time), and the max joint difference between the injected last point and the measured
    joints at injection;
  - controller acceptance evidence: whether the injected trajectory reached the controller topic (from analyze_ord),
    whether the controller log reports a rejection after the injection time, the last trajectory in the window;
  - actual motion: max EE travel after the injection (to the window end) and the EE travel after onset (P_stop).
  analyze_far.py trial <dir> <arm> <cond> | set <out.json> <schedule.csv> <raw_dir>"""
import csv, json, sys
from pathlib import Path
import numpy as np
sys.path.insert(0, "/m3o/analysis"); import analyze_ord as O
A = O.A
def trial(d, arm, cond):
    out = O.trial(d, arm, cond)
    if out["invalid"] or not out.get("injected"): return out
    d = Path(d); T = A.Trial(d); inj = O.jl(d / "injector.jsonl")[0]; ti = inj["t"]
    e_c, e_i = T.ee_at(inj["captured_t"]), T.ee_at(ti)
    js = [r for r in T.js if r["t"] <= ti]; jd = None
    if js:
        cur = dict(zip(js[-1]["names"], js[-1]["pos"])); jd = max(abs(p - cur[nm]) for nm, p in zip(inj["names"], inj["last_pos"]))
    log = (d / "controller.log").read_text(errors="ignore") if (d / "controller.log").exists() else ""
    rej = [l.strip()[-200:] for l in log.splitlines() if "past" in l.lower() or "reject" in l.lower() or "invalid" in l.lower()]
    out.update(captured_t=round(inj["captured_t"], 4), injected_age_s=round(inj["sim_now"] - inj["stamp"], 4), injected_last_tfs=inj["last_tfs"],
               injected_end_vs_now_s=round(inj["stamp"] + inj["last_tfs"] - inj["sim_now"], 4),
               target_diff_ee_mm=None if (e_c is None or e_i is None) else round(float(np.linalg.norm(e_c[0] - e_i[0]) * 1000), 2),
               target_diff_joint_max_rad=None if jd is None else round(jd, 4), controller_log_rejections=rej[:3])
    return out
if __name__ == "__main__":
    if sys.argv[1] == "trial": print(json.dumps(trial(*sys.argv[2:5]), indent=1, default=str))
    else:
        out, sched, raw = sys.argv[2], sys.argv[3], Path(sys.argv[4]); res = []
        for row in csv.DictReader(open(sched)):
            for d in sorted(raw.glob(row["trial_id"] + "*")): res.append(trial(d, row["arm"], row["cond"]))
        json.dump(res, open(out, "w"), indent=1, default=str); print(len(res))
