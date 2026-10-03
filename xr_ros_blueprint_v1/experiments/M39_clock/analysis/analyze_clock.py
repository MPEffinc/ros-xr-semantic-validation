#!/usr/bin/env python3
"""M39_clock analysis (R06). Reuses the frozen M39 analysis (analysis/analyze_m39.py, imported unchanged, arm
semantics of B0) for the inherited R03 measures, and adds clock-domain and Servo-timeout measures.
  analyze_clock.py trial <trial_dir> [arm_label]
  analyze_clock.py set <out.json> <dir> [<dir> ...]       (directory label taken from its runner.json/setup.json)
Clock: sim time from the observer's /clock samples (wall_ns, sim_ns), linearly interpolated at each reception."""
import bisect, json, sys
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation as R
PILOT = Path("/m39") if Path("/m39/analysis").exists() else Path(__file__).resolve().parents[2] / "M39_pilot"
sys.path.insert(0, str(PILOT / "analysis")); sys.path.insert(0, str(PILOT / "harness"))
import analyze_m39 as A  # frozen
import ur5_kin as K

CLOCK_MED_MS, CLOCK_MAX_MS = 50.0, 200.0
TIMEOUT_S = 0.5            # ur_servo.yaml incoming_command_timeout (sim time)


def sim_at(T, t):
    c = T.clock
    if len(c) < 2: return None
    ts = [r["t"] for r in c]; i = min(max(bisect.bisect_right(ts, t) - 1, 0), len(c) - 2)
    a, b = c[i], c[i + 1]; f = (t - a["t"]) / (b["t"] - a["t"]) if b["t"] > a["t"] else 0.0
    return (a["sim_ns"] + f * (b["sim_ns"] - a["sim_ns"])) / 1e9


def clock_match(T):
    off = []
    for r in T.servo_in:
        if r["t"] < 1.9: continue
        s = sim_at(T, r["t"])
        if s is not None: off.append((r["stamp_ns"] / 1e9 - s) * 1000)
    if not off: return {"n": 0, "ok": False}
    a = np.abs(off)
    return {"n": len(off), "median_offset_ms": round(float(np.median(off)), 2), "max_abs_offset_ms": round(float(a.max()), 2),
            "ok": bool(np.median(a) <= CLOCK_MED_MS and a.max() <= CLOCK_MAX_MS)}


def timeout_measures(T, t_on, t_end):
    """After the last Servo input before t_end: does Servo stop publishing trajectories (pose timeout + smoothHalt)?"""
    cmd = [r for r in T.servo_in if r["t"] < t_end]
    if not cmd: return None
    last = cmd[-1]; tl = last["t"]
    tr = [r for r in T.traj if tl < r["t"] <= t_end]
    out = {"t_last_cmd": round(tl, 4), "servo_traj_after_last_cmd": len(tr)}
    if tr:
        stop = tr[-1]["t"]; quiet = t_end - stop
        out.update(t_last_traj=round(stop, 4), quiet_before_t_end_s=round(quiet, 3))
        fired = quiet >= 0.2
        out["timeout_fired"] = fired
        s_last_stamp = last["stamp_ns"] / 1e9; s_stop = sim_at(T, stop)
        out["stop_minus_last_cmd_wall_s"] = round(stop - tl, 3)
        out["stop_minus_last_stamp_sim_s"] = None if s_stop is None else round(s_stop - s_last_stamp, 3)
        p0 = tr[-1].get("pos0") or []
        if len(p0) == 6:
            names = tr[-1]["names"]; q = [p0[names.index(j)] for j in A.ARM_J]
            p_cmd, _, _ = K.fk(q); e_on = T.ee_at(t_on)
            out["last_jtc_target_ee_vs_ee_at_onset_mm"] = round(float(np.linalg.norm(p_cmd - e_on[0]) * 1000), 2)
            e_end = T.ee_at(t_end); out["ee_at_t_end_vs_last_jtc_target_mm"] = round(float(np.linalg.norm(p_cmd - e_end[0]) * 1000), 2)
    else:
        out["timeout_fired"] = None   # Servo output had already stopped before the last command (not expected)
    # trajectories published during the deactivation window at all
    out["servo_traj_in_window"] = sum(1 for r in T.traj if t_on <= r["t"] <= t_end)
    out["servo_traj_last_0.5s_of_window"] = sum(1 for r in T.traj if t_end - 0.5 <= r["t"] <= t_end)
    return out


def analyze(d, label=None):
    T = A.Trial(d); cond = T.setup.get("cond") or T.runner.get("cond")
    label = label or T.setup.get("arm") or T.runner.get("arm")
    res = A.analyze(d, "B0", cond)        # inherited R03 measures with B0 semantics (no arm component)
    res["arm_label"] = label
    if T.t0 is None: return res
    cm = clock_match(T); res["clock_match"] = cm
    if label == "B0_CLOCK" and not cm["ok"]: res["invalid"] = res["invalid"] + ["clock_not_matched"]
    if cond != "N0" and res.get("t_on") is not None:
        res["timeout"] = timeout_measures(T, res["t_on"], res["t_end"])
    res["servo_traj_total"] = len(T.traj)
    return res


if __name__ == "__main__":
    if sys.argv[1] == "trial":
        print(json.dumps(analyze(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None), indent=1, default=str))
    elif sys.argv[1] == "set":
        out = [analyze(d) for d in sys.argv[3:]]
        json.dump(out, open(sys.argv[2], "w"), indent=1, default=str); print(len(out))
