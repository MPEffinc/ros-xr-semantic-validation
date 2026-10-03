#!/usr/bin/env python3
"""R10 1B-V analysis: standalone JTC action cancel (Gazebo + JTC only). analyze_action.py <out.json> <dir> ..."""
import json, sys
from pathlib import Path
import numpy as np
sys.path.insert(0, "/m39/harness"); import ur5_kin as K
A_MAX = 3.0
def jl(p): return [json.loads(l) for l in open(p)] if Path(p).exists() else []
res = []
for d in sys.argv[2:]:
    d = Path(d); L = jl(d / "action.jsonl"); r = {"trial": d.name, "runner": (jl(d / "runner.json") or [{}])[0], "setup": (jl(d / "setup.json") or [{}])[0],
                                                 "param": (d / "param_decel.txt").read_text() if (d / "param_decel.txt").exists() else None}
    cr = next((x for x in L if x["k"] == "cancel_request"), None); cresp = next((x for x in L if x["k"] == "cancel_response"), None)
    if cr is None: r["invalid"] = ["no_cancel"]; res.append(r); continue
    t0 = cr["wall"]; ee = [(x["wall"] - t0, np.array(x["p"])) for x in L if x["k"] == "ee"]
    js = [(x["wall"] - t0, x["v"]) for x in L if x["k"] == "js"]
    e0 = next(p for t, p in reversed(ee) if t <= 0)
    trav = max(float(np.linalg.norm(p - e0) * 1000) for t, p in ee if t >= 0)
    still = None; s = None
    for t, v in js:
        if t < 0: continue
        if max(abs(x) for x in v) <= 0.01:
            s = t if s is None else s
            if t - s >= 0.1: still = s; break
        else: s = None
    q, v = np.array(cr["q"]), np.array(cr["v"])
    hold = q + np.sign(v) * v * v / (2 * A_MAX)
    r.update(cancel_return_code=cresp and cresp["return_code"], cancel_resp_delay_s=cresp and round(cresp["wall"] - t0, 4),
             max_joint_speed_at_request=round(float(np.abs(v).max()), 4), ee_travel_after_request_mm=round(trav, 2),
             standstill_after_request_s=still and round(still, 3), pred_decel_ee_mm=round(float(np.linalg.norm(K.fk(hold)[0] - K.fk(q)[0]) * 1000), 3),
             pred_decel_t_stop_s=round(float(np.abs(v).max() / A_MAX), 4), override=next((x for x in L if x["k"] == "override_topic_traj"), None) is not None,
             jtc_log=(d / "jtc_log_excerpt.txt").read_text()[-600:] if (d / "jtc_log_excerpt.txt").exists() else None)
    if r["override"]:
        tov = next(x for x in L if x["k"] == "override_topic_traj")["wall"] - t0
        pov = next(p for t, p in reversed(ee) if t <= tov); r["ee_motion_after_override_mm"] = round(max(float(np.linalg.norm(p - pov) * 1000) for t, p in ee if t >= tov), 2)
    res.append(r)
json.dump(res, open(sys.argv[1], "w"), indent=1, default=str); print(len(res))
