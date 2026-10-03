#!/usr/bin/env python3
"""POST-HOC (written 2026-10-03 after R04; not part of the frozen analysis). Recomputes, from the same raw data, the
M39 judgments under the ORIGINAL pre-flight criteria (R03 at commit e3e3778, before any Gazebo run) and under the
FINAL frozen criteria (R03 at 467c223), one criterion at a time, plus a Servo status-4 timing table.
The frozen analysis module is imported unchanged (FREEZE_SHA256.txt); original variants are re-implemented here.
  sensitivity_m39.py <m39_dir> <out.json>"""
import json, math, sys
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation as R
M = Path(sys.argv[1]); sys.path.insert(0, str(M / "analysis"))
import analyze_m39 as A  # frozen

POS, ROT = A.POS_TOL, A.ROT_TOL


def feeder_increments(T):
    """ORIGINAL (e3e3778) mapping increments: EE increment vs 0.5*Δh (feeder hand position) and body rotation vs
    Q(a)^-1 Q(b) (feeder hand orientation)."""
    out = []
    for a, b in zip(A.CHECK[:-1], A.CHECK[1:]):
        ea, eb, ha, hb = T.ee_at(a), T.ee_at(b), T.hand_at(a), T.hand_at(b)
        dp = float(np.linalg.norm((eb[0] - ea[0]) - A.SCALE * (hb[0] - ha[0])) * 1000)
        dr = A.ang(ea[1].inv() * eb[1], ha[1].inv() * hb[1])
        out.append({"a": a, "b": b, "pos_err_mm": round(dp, 2), "rot_err_deg": round(dr, 3), "pass": dp <= POS and dr <= ROT})
    return out


def settled_original(T, t):
    """ORIGINAL settled check: EE vs engage-referenced feeder mapping p_e + 0.5(h - h_e), R_e Q_e^-1 Q."""
    ref = A.engage_ref(T)
    if ref is None: return None
    te, e0, h0 = ref; e, h = T.ee_at(t), T.hand_at(t)
    p = e0[0] + A.SCALE * (h[0] - h0[0]); Rx = e0[1] * (h0[1].inv() * h[1])
    return float(np.linalg.norm(e[0] - p) * 1000), A.ang(e[1], Rx)


def l3_latency(T):
    ea = T.ee_at(9.45); u = np.array(T.sc.get("u", [1, 0, 0]), float)
    for r in T.ee:
        if 9.5 <= r["t"] <= 11.0 and float(np.dot(np.array(r["p"]) - ea[0], u)) >= 0.002: return r["t"] - 9.5
    return None


def status4_table(T, res):
    s4 = [r["t"] for r in T.status if r["code"] == 4]
    def cnt(a, b): return sum(1 for t in s4 if a <= t <= b)
    w = {}
    if res.get("t_on") is not None and res.get("t_end") is not None:
        w["P_stop[t_on+0.1,t_end]"] = cnt(res["t_on"] + 0.1, res["t_end"])
    for e in (res.get("P_resume") or {}).get("events", []):
        w[f"P_resume[{e['t_r']},+0.3]"] = cnt(e["t_r"], e["t_r"] + 0.3)
    w["increments[9.4,14.9]"] = cnt(9.4, 14.9); w["settled[5.5,5.7]"] = cnt(5.5, 5.7)
    w["L3[9.5,11.0]"] = cnt(9.5, 11.0)
    # contiguous spans (status samples ~50 Hz; gap > 0.1 s splits a span)
    spans = []
    for t in s4:
        if spans and t - spans[-1][1] <= 0.1: spans[-1][1] = t
        else: spans.append([t, t])
    return {"count_after_engage": sum(1 for t in s4 if t >= 2.0), "spans": [[round(a, 3), round(b, 3)] for a, b in spans][:8], "per_window": w,
            "other_codes": sorted({r["code"] for r in T.status if r["code"] not in (0, 4)})}


def trial(d, arm, cond):
    T = A.Trial(d); res = A.analyze(d, arm, cond)
    out = {"trial": Path(d).name, "arm": arm, "cond": cond, "invalid": res["invalid"]}
    if res["invalid"]: return out
    inc_final = res["increments"]; inc_orig = feeder_increments(T)
    out["inc_final_ok"] = all(x and x["pass"] for x in inc_final); out["inc_orig_ok"] = all(x["pass"] for x in inc_orig)
    out["inc_orig"] = inc_orig
    s57 = A.settled_err(T, 5.7); s59 = A.settled_err(T, 5.9); o59 = settled_original(T, 5.9); o57 = settled_original(T, 5.7)
    out["settled"] = {"final_5.7_vs_target": s57, "time_only_5.9_vs_target": s59, "ref_only_5.7_vs_feeder": o57, "original_5.9_vs_feeder": o59}
    lat = l3_latency(T); out["L3_latency_s"] = None if lat is None else round(lat, 3)
    if cond == "N0":
        fi = res["Normal"]["false_interrupts"] == 0
        ok = lambda s: s is not None and s[0] <= POS and s[1] <= ROT
        out["Normal"] = {"final": res["Normal"]["pass"],
                         "only_settled_time_5.9": fi and ok(s59) and out["inc_final_ok"],
                         "only_reference_feeder": fi and ok(o57) and out["inc_orig_ok"],
                         "original_all": fi and ok(o59) and out["inc_orig_ok"]}
    if "Live" in res:
        L = res["Live"]; l1 = L["readmit_after_press_s"] is not None and L["readmit_after_press_s"] <= 1.0
        l3_05 = lat is not None and lat <= 0.5; l3_10 = lat is not None and lat <= 1.0
        out["Live"] = {"final": L["pass"], "only_L3_0.5": l1 and l3_05 and out["inc_final_ok"],
                       "only_reference_feeder": l1 and l3_10 and out["inc_orig_ok"],
                       "original_all": l1 and l3_05 and out["inc_orig_ok"],
                       "L1": l1, "L3_0.5": l3_05, "L3_1.0": l3_10}
    out["status4"] = status4_table(T, res)
    return out


def qual_strict(d):
    """ORIGINAL qualification: any status != 0 from engage to END disqualifies; settled 5.9 vs feeder mapping;
    rotation rate in [5.0, 5.9]; increments vs feeder."""
    T = A.Trial(d); ref = A.engage_ref(T); st = A.statuses(T, ref[0] if ref else 2.0, A.END)
    e0, e1 = T.ee_at(5.0), T.ee_at(5.9); rate = A.ang(e1[1], e0[1]) / 0.9
    so = settled_original(T, 5.9); inc = feeder_increments(T)
    return {"run": Path(d).name, "statuses": st, "rot_rate_5.0_5.9": round(rate, 4), "settled_orig_5.9": [round(x, 2) for x in so],
            "inc_feeder_ok": all(x["pass"] for x in inc), "inc_feeder": inc,
            "strict_status_ok": set(st) <= {0}, "pass_original": set(st) <= {0} and rate <= 0.5 and so[0] <= POS and so[1] <= ROT and all(x["pass"] for x in inc),
            "final_qual": A.qual(d)["pass"]}


if __name__ == "__main__":
    import csv
    rows = list(csv.DictReader(open(M / "schedule.csv")))
    trials = []
    for row in rows:
        for d in sorted((M / "raw" / "formal").glob(row["trial_id"] + "*")):
            trials.append(trial(d, row["arm"], row["cond"]))
    qual = [qual_strict(M / "raw/preflight/qual" / n) for n in ("c1_sol2_mz_N0", "c5_sol4_mx_N0", "c5_sol4_mx_QF")]
    json.dump({"posthoc": True, "trials": trials, "qualification_original": qual}, open(sys.argv[2], "w"), indent=1, default=float)
    print("ok", len(trials))
