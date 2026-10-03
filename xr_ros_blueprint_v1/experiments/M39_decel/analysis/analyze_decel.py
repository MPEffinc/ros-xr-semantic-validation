#!/usr/bin/env python3
"""M39_decel analysis (R09). Uses the frozen M39 analysis (analyze_m39.py, imported unchanged) for the R03 measures
and adds Servo collision-scale/self-distance measures from the logging-only Servo build (servo_scale.jsonl):
  'cm'    collision-monitor cycle (10 Hz): scale computed, self-collision distance, collision flags
  'apply' Servo control cycle that processes a command: the scale value used in getNextJointState
  'cm_start'/'cm_stop' monitor thread start/stop (pause_servo stops the monitor; the scale is then not recomputed)
  analyze_decel.py trial <dir> [arm] [cond]
  analyze_decel.py probe <out.json> <dir> ...      (instrumentation-effect comparison, normal runs)
  analyze_decel.py set <out.json> <schedule.csv> <raw_dir>"""
import csv, json, math, sys
from pathlib import Path
import numpy as np
PILOT = Path("/m39") if Path("/m39/analysis").exists() else Path(__file__).resolve().parents[2] / "M39_pilot"
sys.path.insert(0, str(PILOT / "analysis"))
import analyze_m39 as A  # frozen


def load_scale(T):
    rows = A.jl(T.d / "servo_scale.jsonl")
    for r in rows: r["t"] = r["wall_ns"] / 1e9 - T.t0
    return rows


def win_stats(rows, a, b):
    cm = [r for r in rows if r["k"] == "cm" and a <= r["t"] <= b]
    ap = [r for r in rows if r["k"] == "apply" and a <= r["t"] <= b]
    out = {"cm_n": len(cm), "apply_n": len(ap)}
    if cm:
        sd = [r["self_d"] for r in cm]
        out.update(cm_scale_min=round(min(r["scale"] for r in cm), 4), cm_scale_mean=round(float(np.mean([r["scale"] for r in cm])), 4),
                   self_d_min_mm=round(min(sd) * 1000, 3), self_d_mean_mm=round(float(np.mean(sd)) * 1000, 3))
    if ap:
        s = [r["scale"] for r in ap]
        out.update(apply_scale_min=round(min(s), 4), apply_scale_mean=round(float(np.mean(s)), 4),
                   apply_frac_below_1=round(sum(1 for x in s if x < 1) / len(s), 3), apply_frac_below_0_9=round(sum(1 for x in s if x < 0.9) / len(s), 3))
    return out


def monitor_running_spans(rows, end):
    """Intervals in which the collision monitor thread was running (from cm_start/cm_stop)."""
    spans, cur = [], None
    for r in rows:
        if r["k"] == "cm_start" and cur is None: cur = r["t"]
        if r["k"] == "cm_stop" and cur is not None: spans.append([round(cur, 3), round(r["t"], 3)]); cur = None
    if cur is not None: spans.append([round(cur, 3), round(end, 3)])
    return spans


def ee_speed_max(T, a, b):
    pts = [(r["t"], np.array(r["p"])) for r in T.ee if a <= r["t"] <= b]
    v = [float(np.linalg.norm(p1 - p0) / (t1 - t0)) for (t0, p0), (t1, p1) in zip(pts, pts[1:]) if t1 - t0 > 0.005]
    return round(max(v) * 1000, 2) if v else None


def target_ee_gap(T, a, b):
    g = []
    for r in T.servo_in:
        if a <= r["t"] <= b:
            e = T.ee_at(r["t"])
            if e is not None: g.append(float(np.linalg.norm(np.array(r["p"]) - e[0]) * 1000))
    return {"n": len(g), "mean_mm": round(float(np.mean(g)), 2), "max_mm": round(float(max(g)), 2)} if g else {"n": 0}


def standstill_time(T, t_from, t_to, thr=0.01, hold=0.1):
    """First time after t_from at which the max arm joint speed stays <= thr for hold seconds."""
    js = [(r["t"], max(abs(v) for n, v in zip(r["names"], r["vel"]) if n in A.ARM_J)) for r in T.js if t_from <= r["t"] <= t_to and r.get("vel")]
    start = None
    for t, v in js:
        if v <= thr:
            if start is None: start = t
            if t - start >= hold: return round(start, 4)
        else: start = None
    return None


def trial(d, arm=None, cond=None):
    T = A.Trial(d); arm = arm or T.setup.get("arm"); cond = cond or T.setup.get("cond")
    res = A.analyze(d, arm, cond)
    rows = load_scale(T); out = {"trial": Path(d).name, "arm": arm, "cond": cond, "invalid": res["invalid"],
                                 "variant": (A.jl(Path(d) / "servo_variant.json") or [{}])[0].get("servo_variant")}
    if res["invalid"] or T.t0 is None: return out
    out["R03"] = {k: res.get(k) for k in ("P_stop", "P_resume", "Live", "P_rearm", "Normal", "masked", "status_codes_all")}
    out["monitor_running"] = monitor_running_spans(rows, A.END)
    W = {"pre[5.5,6.0]": (5.5, 6.0), "increments[9.4,14.9]": (9.4, 14.9), "L3[9.5,11.0]": (9.5, 11.0), "all[2.0,15.5]": (2.0, A.END)}
    t_on, t_end = res.get("t_on"), res.get("t_end")
    if t_on is not None and t_end is not None: W["stop[t_on+0.1,t_end]"] = (t_on + 0.1, t_end)
    for e in (res.get("P_resume") or {}).get("events", []): W[f"resume[{e['t_r']},+0.3]"] = (e["t_r"], e["t_r"] + 0.3)
    out["windows"] = {k: dict(win_stats(rows, a, b), ee_speed_max_mm_s=ee_speed_max(T, a, b), target_ee=target_ee_gap(T, a, b)) for k, (a, b) in W.items()}
    if t_on is not None and t_end is not None:
        ints = [r for r in T.arm if r["event"] == "interrupt" and r["reason"] != "startup" and r["t"] >= t_on - 0.05]
        def first(ev, **kw):
            return next((round(r["t"], 4) for r in T.arm if r["event"] == ev and r["t"] >= t_on - 0.05 and all(r.get(k) == v for k, v in kw.items())), None)
        col = next((round(r["t"], 4) for r in T.col if r["t"] >= t_on - 0.01 and not r["io"]), None) if cond.startswith("I") else None
        last_traj = max((r["t"] for r in T.traj if t_on <= r["t"] <= t_end and r.get("tfs0_ns") != 20_000_000), default=None)
        out["latency_chain"] = {"onset": round(t_on, 4), "collector_saw": col, "arm_decision": round(ints[0]["t"], 4) if ints else None,
                                "pause_call": first("pause_call", data=True), "pause_ack": first("pause_ack", data=True), "first_hold": first("hold"),
                                "last_servo_traj_in_window": None if last_traj is None else round(last_traj, 4),
                                "standstill(<=0.01rad/s for 0.1s)": standstill_time(T, t_on, t_end)}
    return out


def probe(dirs):
    res = []
    for d in dirs:
        T = A.Trial(d); a = A.analyze(d, "B0", "N0"); tr = [r["t"] for r in T.traj if 2.5 <= r["t"] <= 15.0]
        dt = np.diff(tr) * 1000 if len(tr) > 2 else np.array([np.nan])
        cg = np.diff([r["t"] for r in T.col]) * 1000
        lag = lambda x, y: target_ee_gap(T, x, y).get("mean_mm")
        res.append({"trial": Path(d).name, "variant": (A.jl(Path(d) / "servo_variant.json") or [{}])[0].get("servo_variant"), "invalid": a["invalid"],
                    "servo_out_period_ms": {"median": round(float(np.median(dt)), 2), "p95": round(float(np.percentile(dt, 95)), 2), "max": round(float(dt.max()), 2), "n": len(tr)},
                    "app_rate_hz": a["app_rate_hz"], "collector_max_gap_ms": round(float(cg.max()), 1), "rtf": a.get("rtf"),
                    "lag_A_mm": lag(3.2, 5.0), "lag_C_mm": lag(9.7, 10.5), "lag_E_mm": lag(12.7, 13.5),
                    "Normal": a.get("Normal"), "increments": a["increments"], "load_before": T.runner.get("host_load_before")})
    return res


if __name__ == "__main__":
    if sys.argv[1] == "trial": print(json.dumps(trial(*sys.argv[2:5]), indent=1, default=str))
    elif sys.argv[1] == "probe": json.dump(probe(sys.argv[3:]), open(sys.argv[2], "w"), indent=1, default=str)
    elif sys.argv[1] == "set":
        out, sched, raw = sys.argv[2], sys.argv[3], Path(sys.argv[4]); res = []
        for row in csv.DictReader(open(sched)):
            for d in sorted(raw.glob(row["trial_id"] + "*")): res.append(trial(d, row["arm"], row["cond"]))
        json.dump(res, open(out, "w"), indent=1, default=str); print(len(res))
