#!/usr/bin/env python3
"""M39 analysis (R03 §6, §7, §9). Pure function of the trial directories; no tuning on outcomes.
  analyze_m39.py trial <trial_dir>            -> JSON of one trial (all measures, flags, timeline)
  analyze_m39.py qual <trial_dir>             -> R03 §10.3 qualification verdict for a B0 normal run (N0 / QF)
  analyze_m39.py campaign <raw_dir> <schedule.csv> <out.json>  -> per-trial + per-cell summary
Times are seconds after T0 (wall clock, CLOCK_REALTIME). EE = tf base_link->wrist_3_link."""
import bisect, csv, json, math, sys
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation as R

ARM_J = ["shoulder_pan_joint", "shoulder_lift_joint", "elbow_joint", "wrist_1_joint", "wrist_2_joint", "wrist_3_joint"]
MASK_CODES = {1, 2, 3, 5, 6}
T_ON, T_END, END, SCALE = 6.0, 7.5, 15.5, 0.5
CHECK = [9.4, 10.9, 12.4, 14.9]
POS_TOL, ROT_TOL, STOP_TRAVEL, STOP_SPEED = 5.0, 2.0, 5.0, 0.01


def jl(p):
    out = []
    if not Path(p).exists(): return out
    for l in open(p):
        try: out.append(json.loads(l))
        except ValueError: pass
    return out


class Trial:
    def __init__(self, d):
        self.d = Path(d)
        self.setup = (jl(self.d / "setup.json") or [{}])[0]
        self.runner = (jl(self.d / "runner.json") or [{}])[0]
        self.t0 = self.setup.get("t0")
        self.sc = (jl(self.d / "scenario.json") or [{}])[0]
        if self.t0 is None: return
        t0 = self.t0
        obs = jl(self.d / "observer.jsonl")
        for r in obs: r["t"] = r["wall_ns"] / 1e9 - t0
        self.obs = obs
        self.ee = [r for r in obs if r["k"] == "ee"]; self.ee_t = [r["t"] for r in self.ee]
        self.js = [r for r in obs if r["k"] == "joints"]
        self.status = [r for r in obs if r["k"] == "status"]
        self.servo_in = [r for r in obs if r["k"] == "servo_in"]
        self.app = [r for r in obs if r["k"] == "app"]
        self.traj = [r for r in obs if r["k"] == "traj"]
        self.clock = [r for r in obs if r["k"] == "clock"]
        self.feed = jl(self.d / "feeder.jsonl")
        for r in self.feed: r["t"] = r["wall"] - t0
        self.feed_t = [r["t"] for r in self.feed]
        self.sched = jl(self.d / "sched.jsonl")
        for r in self.sched:
            if "ret" in r: r["t"] = r["ret"] - t0
        self.arm = jl(self.d / "arm.jsonl")
        for r in self.arm: r["t"] = r["wall_ns"] / 1e9 - t0
        self.col = [r for r in jl(self.d / "collector.jsonl") if r.get("name") == "python3.12"]
        for r in self.col: r["t"] = r["wall"] - t0

    # ---- samplers (latest sample at or before t)
    def ee_at(self, t):
        i = bisect.bisect_right(self.ee_t, t) - 1
        if i < 0: return None
        r = self.ee[i]; return np.array(r["p"]), R.from_quat(r["q"])

    def hand_at(self, t):
        i = bisect.bisect_right(self.feed_t, t) - 1
        if i < 0: return None
        r = self.feed[i]; return np.array(r["p"]), R.from_quat(r["q"])

    def grip_at(self, t):
        i = bisect.bisect_right(self.feed_t, t) - 1
        return self.feed[max(i, 0)]["grip"]

    def joint_speed(self, a, b):
        m = 0.0
        for r in self.js:
            if a <= r["t"] <= b and r.get("vel"):
                v = dict(zip(r["names"], r["vel"])); m = max(m, max(abs(v[j]) for j in ARM_J if j in v))
        return m

    def ee_range(self, a, b, ref):
        m = 0.0; mr = 0.0
        for r in self.ee:
            if a <= r["t"] <= b:
                m = max(m, float(np.linalg.norm(np.array(r["p"]) - ref[0]) * 1000))
                mr = max(mr, math.degrees((R.from_quat(r["q"]) * ref[1].inv()).magnitude()))
        return m, mr


def ang(Ra, Rb): return math.degrees((Ra * Rb.inv()).magnitude())


REF_PATH = Path(__file__).resolve().parent.parent / "preflight" / "ref_increments.json"


def target_at(T, t):
    """Latest Servo-input target at or before t (p, R)."""
    c = [r for r in T.servo_in if r["t"] <= t]
    return (np.array(c[-1]["p"]), R.from_quat(c[-1]["q"])) if c else None


def target_increments(T):
    """Increments of the Servo-input targets between checkpoints (used to build the frozen reference from the B0 N0
    qualification run: the unmodified app's own command increments for the scripted hand motion)."""
    out = []
    for a, b in zip(CHECK[:-1], CHECK[1:]):
        ta, tb = target_at(T, a), target_at(T, b)
        out.append({"a": a, "b": b, "dp": list(tb[0] - ta[0]), "drot_q": list((ta[1].inv() * tb[1]).as_quat())})
    return out


def increments(T, ref=None):
    """R03 §6 mapping increments: EE increments between checkpoints vs the reference increments of the unmodified
    app's commands for the same hand motion (ref; default: the frozen preflight/ref_increments.json)."""
    if ref is None:
        ref = json.loads(REF_PATH.read_text())["increments"] if REF_PATH.exists() else None
    out = []
    for k, (a, b) in enumerate(zip(CHECK[:-1], CHECK[1:])):
        ea, eb = T.ee_at(a), T.ee_at(b)
        if None in (ea, eb) or ref is None: out.append(None); continue
        dp_exp = np.array(ref[k]["dp"]); dR_exp = R.from_quat(ref[k]["drot_q"])
        dp_err = float(np.linalg.norm((eb[0] - ea[0]) - dp_exp) * 1000)
        r_err = ang(ea[1].inv() * eb[1], dR_exp)
        out.append({"a": a, "b": b, "pos_err_mm": round(dp_err, 2), "rot_err_deg": round(r_err, 3),
                    "ee_dp_mm": round(float(np.linalg.norm(eb[0] - ea[0]) * 1000), 2),
                    "ee_drot_deg": round(math.degrees((ea[1].inv() * eb[1]).magnitude()), 3),
                    "pass": dp_err <= POS_TOL and r_err <= ROT_TOL})
    return out


def engage_ref(T):
    """First Servo input after the scripted press at 2.0 = engage; reference EE and hand at that time."""
    first = next((r for r in T.servo_in if r["t"] >= 1.9), None)
    if first is None: return None
    return first["t"], T.ee_at(first["t"]), T.hand_at(first["t"])


def settled_err(T, t, ref=None):
    """Tracking at a settled time: measured EE vs the latest Servo-input target."""
    e, g = T.ee_at(t), target_at(T, t)
    if e is None or g is None: return None
    return float(np.linalg.norm(e[0] - g[0]) * 1000), ang(e[1], g[1])


def statuses(T, a, b):
    return sorted({r["code"] for r in T.status if a <= r["t"] <= b})


def s4(T, a, b):
    return sum(1 for r in T.status if a <= r["t"] <= b and r["code"] == 4)


def mask_events(T, a, b):
    ev = [(round(r["t"], 3), r["code"]) for r in T.status if a <= r["t"] <= b and r["code"] in MASK_CODES]
    return ev


def app_rate(T, arm, a=3.0, b=5.9):
    src = T.app if arm == "C1" else T.servo_in
    n = sum(1 for r in src if a <= r["t"] <= b); return n / (b - a)


def gaps(ts, a, b):
    ts = [t for t in ts if a <= t <= b]
    return max((y - x for x, y in zip(ts, ts[1:])), default=float("inf"))


def invalid_flags(T, arm, cond):
    f = []
    if T.t0 is None or T.runner.get("rc", 1) != 0: f.append(f"setup_rc_{T.runner.get('rc')}_{T.setup.get('setup')}")
    if T.t0 is None: return f
    foc = [r for r in T.col if r["focused"] and r["t"] <= 2.0]
    if not foc: f.append("app_client_not_focused_by_2.0")
    if gaps(T.ee_t, 1.5, END - 0.05) > 0.1: f.append("ee_gap")
    if gaps([r["t"] for r in T.js], 1.5, END - 0.05) > 0.1: f.append("joint_state_gap")
    if gaps(T.feed_t, 0.0, END) > 0.1: f.append("feeder_gap")
    if cond.startswith("I"):
        ok = len(T.sched) >= 2 and all(r.get("res") == 0 and abs(r["ret"] - r["target"]) <= 0.005 for r in T.sched[:2])
        if not ok: f.append("sched_bad")
    if app_rate(T, arm) < 15: f.append("app_rate_below_15Hz")
    return f


def onset_end(T, cond):
    if cond.startswith("I"):
        off = next((r for r in T.sched if r.get("kind") == "off"), None); on = next((r for r in T.sched if r.get("kind") == "on"), None)
        return (off["t"] if off else None), (on["t"] if on else None)
    if cond == "N1":
        rel = next((r["t"] for i, r in enumerate(T.feed) if i and T.feed[i - 1]["grip"] and not r["grip"] and r["t"] > 5), None)
        prs = next((r["t"] for i, r in enumerate(T.feed) if i and not T.feed[i - 1]["grip"] and r["grip"] and r["t"] > 7), None)
        return rel, prs
    return None, None


def fresh_press(T, cond):
    """Ground truth (judging only): a press after a release seen while IO active, after the primary onset."""
    if cond == "N1": return onset_end(T, cond)[1]
    if cond == "I2":
        return next((r["t"] for i, r in enumerate(T.feed) if i and not T.feed[i - 1]["grip"] and r["grip"] and r["t"] > 8.0), None)
    return None


def resume_events(T, arm, cond, t_on, t_end, t_fp):
    """B0: first Servo input after each gap that started inside the interruption; B1/C1: first_target_published."""
    ev = []
    if arm == "B0":
        prev = None
        for r in T.servo_in:
            if r["t"] < t_on: prev = r["t"]; continue
            if prev is not None and r["t"] - prev > 0.15: ev.append(r["t"])
            prev = r["t"]
    else:
        ev = [r["t"] for r in T.arm if r["event"] == "first_target_published" and r["t"] > t_on]
    return ev


def p_resume(T, t_r):
    first = next((r for r in T.servo_in if r["t"] >= t_r - 1e-4), None)
    e = T.ee_at(first["t"] if first else t_r)
    if first is None or e is None: return None
    j_mm = float(np.linalg.norm(np.array(first["p"]) - e[0]) * 1000); j_deg = ang(R.from_quat(first["q"]), e[1])
    trav, _ = T.ee_range(t_r, t_r + 0.3, e)
    h0, h1 = T.hand_at(t_r - 0.05), T.hand_at(t_r + 0.3)
    hand_mm = float(np.linalg.norm(h1[0] - h0[0]) * 1000)
    ok = j_mm <= POS_TOL and j_deg <= ROT_TOL and trav <= SCALE * hand_mm + POS_TOL
    return {"t_r": round(t_r, 3), "target_vs_ee_mm": round(j_mm, 2), "target_vs_ee_deg": round(j_deg, 3),
            "ee_travel_300ms_mm": round(trav, 2), "allowed_mm": round(SCALE * hand_mm + POS_TOL, 2), "pass": ok}


def analyze(d, arm=None, cond=None, own_ref=False):
    T = Trial(d)
    own_ref = target_increments(T) if own_ref else None
    arm = arm or T.setup.get("arm") or T.runner.get("arm"); cond = cond or T.setup.get("cond") or T.runner.get("cond")
    res = {"trial": Path(d).name, "arm": arm, "cond": cond}
    inv = invalid_flags(T, arm, cond); res["invalid"] = inv
    if T.t0 is None: return res
    res["load_setup"] = T.setup.get("load"); res["host_load_before"] = T.runner.get("host_load_before")
    res["app_rate_hz"] = round(app_rate(T, arm), 2)
    cg = [y - x for x, y in zip([r["t"] for r in T.col], [r["t"] for r in T.col][1:])]
    res["collector_max_gap_ms"] = round(max(cg) * 1000, 1) if cg else None
    if len(T.clock) > 2:
        c0, c1 = T.clock[0], T.clock[-1]; res["rtf"] = round((c1["sim_ns"] - c0["sim_ns"]) / 1e9 / (c1["t"] - c0["t"]), 3)
    ref = engage_ref(T); res["engage_t"] = round(ref[0], 3) if ref else None
    # masking
    m_from = 2.0 if cond == "N0" else T_ON - 0.5
    res["mask_events"] = mask_events(T, m_from, END)[:20]; res["masked"] = bool(res["mask_events"])
    res["status_codes_all"] = statuses(T, 0, END)
    res["decel_collision"] = sum(1 for r in T.status if r["code"] == 4 and r["t"] >= 2.0)
    # arm events
    ints = [r for r in T.arm if r["event"] == "interrupt" and r["reason"] != "startup"]
    res["arm_interrupts"] = [(round(r["t"], 3), r["reason"]) for r in ints]
    res["holds"] = sum(1 for r in T.arm if r["event"] == "hold" and r["t"] > 1.0)
    res["actives"] = [round(r["t"], 3) for r in T.arm if r["event"] == "active"]
    se = settled_err(T, 5.7)
    res["settled_5.7"] = [round(x, 3) for x in se] if se else None
    res["increments"] = increments(T, own_ref)
    inc_ok = all(x and x["pass"] for x in res["increments"])
    # Normal
    if cond == "N0":
        fi = [r for r in ints if ref and r["t"] > ref[0] + 0.5]
        s_ok = res["settled_5.7"] is not None and res["settled_5.7"][0] <= POS_TOL and res["settled_5.7"][1] <= ROT_TOL
        res["Normal"] = {"false_interrupts": len(fi), "settled_ok": s_ok, "increments_ok": inc_ok,
                         "pass": len(fi) == 0 and s_ok and inc_ok and ref is not None}
    else:
        fi = [r for r in ints if ref and ref[0] + 0.5 < r["t"] < T_ON - 0.02]
        res["pre_event_false_interrupts"] = len(fi)
    t_on, t_end = onset_end(T, cond); t_fp = fresh_press(T, cond)
    res["t_on"], res["t_end"], res["t_fp"] = t_on, t_end, t_fp
    if cond != "N0" and t_on is not None and t_end is not None:
        e_ref = T.ee_at(t_on + 0.1)
        s1, s1r = T.ee_range(t_on + 0.1, t_end, e_ref)
        tot, _ = T.ee_range(t_on, t_end, T.ee_at(t_on))
        s2 = T.joint_speed(t_on + 0.3, t_end)
        det = next((r["t"] for r in ints if r["t"] >= t_on - 0.05), None)
        res["P_stop"] = {"travel_after_100ms_mm": round(s1, 2), "travel_after_onset_mm": round(tot, 2),
                         "max_joint_speed_after_300ms": round(s2, 4), "arm_detect_delay_ms": round((det - t_on) * 1000, 1) if det else None,
                         "masked": bool(mask_events(T, t_on, t_end)), "status4": s4(T, t_on, t_end),
                         "pass": s1 <= STOP_TRAVEL and s2 <= STOP_SPEED}
        rs = resume_events(T, arm, cond, t_on, t_end, t_fp)
        pr = [p_resume(T, t) for t in rs]; pr = [x for x in pr if x]
        res["P_resume"] = {"events": pr, "evaluable": bool(pr), "pass": (all(x["pass"] for x in pr) if pr else None),
                           "masked": any(mask_events(T, x["t_r"], x["t_r"] + 0.3) for x in pr),
                           "status4": sum(s4(T, x["t_r"], x["t_r"] + 0.3) for x in pr)}
        if cond in ("I1", "I2", "I3"):
            lim = t_fp if t_fp else END
            if arm == "B0":
                adm = [r["t"] for r in T.servo_in if t_on < r["t"] < lim]
            else:
                adm = [t for t in res["actives"] if t_on < t < lim]
            phys, physr = T.ee_range(t_end, lim, T.ee_at(t_end))
            res["P_rearm"] = {"admissions_before_fresh_press": len(adm), "first_admission": round(adm[0], 3) if adm else None,
                              "ee_disp_before_press_mm": round(phys, 2), "ee_rot_before_press_deg": round(physr, 3),
                              "physical_hold": phys <= POS_TOL and physr <= ROT_TOL, "pass": len(adm) == 0,
                              "masked": bool(mask_events(T, t_end, lim))}
        if cond in ("N1", "I2"):
            if arm == "B0":
                l1 = next((r["t"] for r in T.servo_in if r["t"] >= t_fp - 0.01), None)
            else:
                l1 = next((t for t in res["actives"] if t >= t_fp - 0.01), None)
            ea = T.ee_at(9.45); lat = None
            u = np.array(T.sc.get("u", [1, 0, 0]), float)
            for r in T.ee:
                if 9.5 <= r["t"] <= 11.0 and ea is not None and float(np.dot(np.array(r["p"]) - ea[0], u)) >= 0.002:
                    lat = r["t"] - 9.5; break
            L1 = l1 is not None and l1 - t_fp <= 1.0; L3 = lat is not None and lat <= 1.0
            res["Live"] = {"readmit_after_press_s": round(l1 - t_fp, 3) if l1 else None, "response_latency_s": round(lat, 3) if lat else None,
                           "increments_ok": inc_ok, "pass": L1 and L3 and inc_ok,
                           "masked": bool(mask_events(T, t_fp, END))}
    # timeline
    tl = {}
    if t_on is not None:
        col_off = next((r["t"] for r in T.col if r["t"] >= t_on - 0.01 and not r["io"]), None) if cond.startswith("I") else None
        tl = {"onset": t_on, "collector_saw": col_off,
              "arm_decision": next((r["t"] for r in ints if r["t"] >= t_on - 0.05), None),
              "pause_ack": next((r["t"] for r in T.arm if r["event"] == "pause_ack" and r.get("data") is True and r["t"] >= t_on - 0.05), None),
              "first_hold": next((r["t"] for r in T.arm if r["event"] == "hold" and r["t"] >= t_on - 0.05), None),
              "held": next((r["t"] for r in T.arm if r["event"] == "held" and r["t"] >= t_on - 0.05), None),
              "last_servo_in_before_end": max((r["t"] for r in T.servo_in if r["t"] < (t_end or END)), default=None)}
        tl = {k: (round(v, 4) if isinstance(v, float) else v) for k, v in tl.items()}
    res["timeline"] = tl
    return res


def lag(T, a, b):
    L = []
    for r in T.servo_in:
        if a <= r["t"] <= b:
            e = T.ee_at(r["t"])
            if e is not None: L.append(float(np.linalg.norm(np.array(r["p"]) - e[0]) * 1000))
    return float(np.mean(L)) if L else None


def qual(d):
    """R03 §10.3 (revised before freeze, see §10.3): statuses {1,2,3,5,6} must be absent after engage; status 4 is
    allowed only if the tracking lag in the same-speed segment with status 4 (A, 3.2-5.0 s) exceeds the lag in a
    status-4-free same-speed segment (C, 9.7-10.5 s) by <= 1.0 mm (and C itself must be status-4-free)."""
    T = Trial(d); r = analyze(d, "B0", T.setup.get("cond"), own_ref=True)
    ss = (jl(Path(d) / "setup_start.json") or [{}])[0]
    e0, e1 = T.ee_at(5.0), T.ee_at(5.7)
    rate = ang(e1[1], e0[1]) / 0.7 if e0 and e1 else None
    ref = engage_ref(T); se = r.get("settled_5.7"); st = statuses(T, ref[0] if ref else 2.0, END)
    hard = [c for c in st if c in MASK_CODES]
    s4_A = any(x["code"] == 4 for x in T.status if 3.2 <= x["t"] <= 5.0); s4_C = any(x["code"] == 4 for x in T.status if 9.7 <= x["t"] <= 10.5)
    lagA, lagC = lag(T, 3.2, 5.0), lag(T, 9.7, 10.5)
    s4_ok = (4 not in st) or (not s4_C and lagA is not None and lagC is not None and lagA - lagC <= 1.0)
    ok = (not r["invalid"] and ss.get("qualified") and not hard and s4_ok
          and rate is not None and rate <= 0.5 and se and se[0] <= POS_TOL and se[1] <= ROT_TOL
          and all(x and x["pass"] for x in r["increments"]) and r["app_rate_hz"] >= 15)
    s4_times = [x["t"] for x in T.status if x["code"] == 4 and x["t"] >= 2.0]
    return {"trial": r["trial"], "setup_start": {k: ss.get(k) for k in ("ee_pos_err_mm", "ee_rot_err_deg", "qualified")},
            "statuses_after_engage": st, "status4_span": [round(min(s4_times), 3), round(max(s4_times), 3)] if s4_times else None,
            "status4_count": len(s4_times), "lag_A_mm": lagA, "lag_C_mm": lagC, "status4_ok": s4_ok,
            "rot_rate_5.0_5.7_deg_s": rate, "settled_5.7": se,
            "increments_vs_own_targets": r["increments"], "app_rate_hz": r["app_rate_hz"], "invalid": r["invalid"],
            "rtf": r.get("rtf"), "pass": bool(ok)}


if __name__ == "__main__":
    if sys.argv[1] == "trial": print(json.dumps(analyze(sys.argv[2]), indent=1, default=str))
    elif sys.argv[1] == "qual": print(json.dumps(qual(sys.argv[2]), indent=1, default=str))
    elif sys.argv[1] == "ref":   # build the frozen reference increments from a qualified B0 N0 run
        T = Trial(sys.argv[2]); print(json.dumps({"source": Path(sys.argv[2]).name, "checkpoints": CHECK, "increments": target_increments(T)}, indent=1))
    elif sys.argv[1] == "campaign":
        raw, sched, out = Path(sys.argv[2]), sys.argv[3], sys.argv[4]
        rows = list(csv.DictReader(open(sched))); trials = []
        for row in rows:
            for d in sorted(raw.glob(row["trial_id"] + "*")):
                a = analyze(d, row["arm"], row["cond"]); a["slot"] = row["trial_id"]; a["attempt_dir"] = d.name; trials.append(a)
        json.dump({"trials": trials}, open(out, "w"), indent=1, default=str); print(out, len(trials))
