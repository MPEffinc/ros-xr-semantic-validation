#!/usr/bin/env python3
"""M3_ordering analysis (R18): R03 P_stop (frozen analyze_m39, B1 semantics), EE travel after onset and after the
injection time, controller-topic trajectories after the first hold (Servo multi-point vs 1-point holds), whether the
injected pre-stop trajectory reached the controller topic, and the last trajectory the controller received in the window.
  analyze_ord.py trial <dir> <arm> <cond> | set <out.json> <schedule.csv> <raw_dir>"""
import csv, json, sys
from pathlib import Path
sys.path.insert(0, "/m39/analysis"); import analyze_m39 as A
def jl(p): return [json.loads(l) for l in open(p)] if Path(p).exists() else []
def trial(d, arm, cond):
    d = Path(d); T = A.Trial(d); res = A.analyze(d, "B1", "I3"); out = {"trial": d.name, "arm": arm, "cond": cond, "invalid": res["invalid"]}
    if res["invalid"] or T.t0 is None: return out
    t_on, t_end = res["t_on"], res["t_end"]
    holds = [r for r in T.arm if r["event"] == "hold" and r["t"] >= t_on - 0.05]; fh = holds[0]["t"] if holds else None
    ctl = [r for r in T.traj if t_on <= r["t"] <= t_end]
    servo_after = [r for r in ctl if fh is not None and r["t"] > fh and r["n"] > 1]
    inj = (jl(d / "injector.jsonl") or [None])[0]
    reached = None; trav_after_inj = None
    if inj:
        ti = inj["t"]; st = int(round(inj["stamp"] * 1e9))
        reached = any(r["t"] >= ti - 0.002 and r["stamp_ns"] == st for r in T.traj)
        e = T.ee_at(ti); trav_after_inj, _ = T.ee_range(ti, t_end, e)
    last = ctl[-1] if ctl else None
    sel = [r for r in T.arm if r["event"].startswith("mux_select")]
    out.update(P_stop=res["P_stop"], first_hold_t=fh, holds=len(holds), servo_traj_on_controller_after_first_hold=len(servo_after),
               servo_after_times=[round(r["t"] - t_on, 4) for r in servo_after][:5], injected=inj is not None, injected_t_after_onset=round(inj["t"] - t_on, 4) if inj else None,
               injected_reached_controller=reached, ee_travel_after_injection_mm=None if trav_after_inj is None else round(trav_after_inj, 2),
               last_controller_traj={"t_after_onset": round(last["t"] - t_on, 4), "points": last["n"]} if last else None,
               pause_ack=[round(r["t"] - t_on, 4) for r in T.arm if r["event"] == "pause_ack"][:2], mux_select=[(r["event"], round(r["t"] - t_on, 4)) for r in sel][:2])
    return out
if __name__ == "__main__":
    if sys.argv[1] == "trial": print(json.dumps(trial(*sys.argv[2:5]), indent=1, default=str))
    else:
        out, sched, raw = sys.argv[2], sys.argv[3], Path(sys.argv[4]); res = []
        for row in csv.DictReader(open(sched)):
            for d in sorted(raw.glob(row["trial_id"] + "*")): res.append(trial(d, row["arm"], row["cond"]))
        json.dump(res, open(out, "w"), indent=1, default=str); print(len(res))
