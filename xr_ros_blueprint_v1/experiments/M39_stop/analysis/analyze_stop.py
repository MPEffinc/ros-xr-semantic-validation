#!/usr/bin/env python3
"""M39_stop analysis (R10). Inherits R03 measures (frozen analyze_m39) and R09 window measures (analyze_decel), and adds
stop measures. Times are s after T0. Onset t_on = mnd_sched return of the IO-off call (injection effective time).
  analyze_stop.py trial <dir> <arm> <cond>
  analyze_stop.py set <out.json> <schedule.csv> <raw_dir>"""
import csv, json, sys
from pathlib import Path
import numpy as np
PILOT = Path("/m39") if Path("/m39/analysis").exists() else Path(__file__).resolve().parents[2] / "M39_pilot"
DECEL = Path("/m39d") if Path("/m39d/analysis").exists() else Path(__file__).resolve().parents[2] / "M39_decel"
sys.path.insert(0, str(PILOT / "analysis")); sys.path.insert(0, str(DECEL / "analysis")); sys.path.insert(0, str(PILOT / "harness"))
import analyze_m39 as A      # frozen
import analyze_decel as D    # frozen with R09
import ur5_kin as K

A_MAX = 3.0
P_DECEL_TOL_MM, P_DECEL_TIME_TOL_S = 2.0, 0.3


def ee_speed_series(T, a, b):
    pts = [(r["t"], np.array(r["p"])) for r in T.ee if a <= r["t"] <= b]
    return [((t0 + t1) / 2, float(np.linalg.norm(p1 - p0) / (t1 - t0))) for (t0, p0), (t1, p1) in zip(pts, pts[1:]) if t1 - t0 > 0.005]


def predicted_decel_ee_mm(q, v):
    """EE distance between measured joint state and the JTC-formula hold position (constant deceleration A_MAX)."""
    hold = [p + (1 if w >= 0 else -1) * w * w / (2 * A_MAX) for p, w in zip(q, v)]
    return float(np.linalg.norm(K.fk(hold)[0] - K.fk(q)[0]) * 1000), max(abs(w) for w in v) / A_MAX


def trial(d, arm, cond):
    T = A.Trial(d); dec = D.trial(d, "B0" if arm == "B0_CLOCK" else "B1", cond.rstrip("h") if cond.startswith("I") else "N0")
    out = {"trial": Path(d).name, "arm": arm, "cond": cond, "invalid": dec["invalid"], "variant": dec.get("variant")}
    if dec["invalid"]: return out
    res = A.analyze(d, "B0", "I3" if cond.startswith("I") else "N0")
    out["app_rate_hz"] = res["app_rate_hz"]; out["rtf"] = res.get("rtf"); out["status_codes_all"] = res["status_codes_all"]
    out["mask_events"] = res["mask_events"]; out["masked"] = res["masked"]
    trig = next((r for r in T.arm if r["event"] == "trigger"), None)
    out["arm_trigger_t"] = round(trig["t"], 4) if trig else None
    out["windows"] = dec.get("windows"); out["monitor_running"] = dec.get("monitor_running")
    if cond.startswith("I"):
        t_on, t_end = res["t_on"], res["t_end"]
        tot, _ = T.ee_range(t_on, t_end, T.ee_at(t_on)); s1, _ = T.ee_range(t_on + 0.1, t_end, T.ee_at(t_on + 0.1))
        s2 = T.joint_speed(t_on + 0.3, t_end)
        still = D.standstill_time(T, t_on, t_end)
        sp = ee_speed_series(T, t_on + 0.1, t_end)
        holds = [r for r in T.arm if r["event"] == "hold" and r["t"] >= t_on - 0.05]
        first_hold = holds[0]["t"] if holds else None
        servo_after_hold = sum(1 for r in T.traj if first_hold is not None and r["t"] > first_hold
                               and not any(0 <= r["t"] - h["t"] < 0.005 for h in holds))
        stop = {"t_on": round(t_on, 4), "ee_travel_after_onset_mm": round(tot, 2), "ee_travel_after_onset_0.1_mm": round(s1, 2),
                "max_joint_speed_after_0.3": round(s2, 4), "standstill_t_after_onset_s": None if still is None else round(still - t_on, 3),
                "ee_speed_max_after_0.1_mm_s": round(max(v for _, v in sp) * 1000, 2) if sp else None,
                "P_stop_R03": s1 <= A.STOP_TRAVEL and s2 <= A.STOP_SPEED, "first_hold_t": None if first_hold is None else round(first_hold, 4),
                "hold_messages": len(holds), "servo_traj_after_first_hold": servo_after_hold}
        if arm == "DECEL_TOPIC" and holds and holds[0].get("velocities"):
            pd, pt = predicted_decel_ee_mm(holds[0]["positions"], holds[0]["velocities"])
            trav, _ = T.ee_range(first_hold, t_end, T.ee_at(first_hold))
            stop.update(decel_pred_ee_mm=round(pd, 3), decel_pred_t_stop_s=round(pt, 4), ee_travel_after_decel_cmd_mm=round(trav, 2),
                        P_decel=trav <= pd + P_DECEL_TOL_MM and still is not None and (still - first_hold) <= pt + P_DECEL_TIME_TOL_S)
        if arm == "B0_CLOCK":
            lt = max((r["t"] for r in T.traj if t_on <= r["t"] <= t_end), default=None)
            stop["last_servo_traj_in_window"] = None if lt is None else round(lt, 4)
        out["stop"] = stop
    else:
        out["false_trigger"] = trig is not None
        out["settled_5.7"] = res.get("settled_5.7"); out["increments"] = res.get("increments")
        out["lag_fast_seg_mm"] = D.target_ee_gap(T, 5.8, 6.6).get("mean_mm")
    return out


if __name__ == "__main__":
    if sys.argv[1] == "trial": print(json.dumps(trial(*sys.argv[2:5]), indent=1, default=str))
    elif sys.argv[1] == "set":
        out, sched, raw = sys.argv[2], sys.argv[3], Path(sys.argv[4]); res = []
        for row in csv.DictReader(open(sched)):
            for d in sorted(raw.glob(row["trial_id"] + "*")): res.append(trial(d, row["arm"], row["cond"]))
        json.dump(res, open(out, "w"), indent=1, default=str); print(len(res))
