#!/usr/bin/env python3
"""TEST-ONLY assertions over the host-check outputs (times in s after each case's T0). Prints a JSON summary."""
import json, sys
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation as R
root = Path(sys.argv[1]); EE_P = np.array([0.45, 0.01, 0.31]); EE_Q = R.from_quat([0.0499, 0.7413, 0.0526, 0.6672])
def load(p): return [json.loads(l) for l in open(p)] if p.exists() else []
def case(name):
    d = root / name; t0 = int((d / "t0_ns").read_text()) / 1e9
    arm = load(d / "arm.jsonl"); world = load(d / "world.jsonl")
    for a in arm: a["t"] = a["wall_ns"] / 1e9 - t0
    return arm, world
def ev(arm, e): return [a for a in arm if a["event"] == e]
def first_target_ok(a):
    pe = np.linalg.norm(np.array(a["p"]) - EE_P) * 1000; re = np.degrees((R.from_quat(a["q"]) * EE_Q.inv()).magnitude()); return pe, re
def order_ok(arm, world):
    """each first_target_published precedes the following unpause call; no Servo input while HELD."""
    out = []
    for f in ev(arm, "first_target_published"):
        un = [a for a in arm if a["event"] == "pause_call" and a["data"] is False and a["t"] >= f["t"]]
        out.append(bool(un) and un[0]["t"] - f["t"] >= 0.035)
    return all(out) and bool(out)
S = {}
arm, world = case("B1_T1")
ints = ev(arm, "interrupt"); sin = [w for w in world if w["k"] == "servo_in"]
S["B1_T1_probe_trace"] = {
    "engages": [round(a["t"], 3) for a in ev(arm, "b1_engage")], "interrupts": [(round(a["t"], 3), a["reason"]) for a in ints],
    "servo_in_after_6.05": sum(1 for w in sin if w["t"] > 6.05), "await_fresh_press": [round(a["t"], 3) for a in ev(arm, "b1_await_fresh_press")],
    "order_ok": order_ok(arm, world)}
S["B1_T1_probe_trace"]["pass"] = (len(S["B1_T1_probe_trace"]["engages"]) == 1 and S["B1_T1_probe_trace"]["servo_in_after_6.05"] == 0
                                  and any(5.95 <= t <= 6.1 for t, _ in S["B1_T1_probe_trace"]["interrupts"]) and S["B1_T1_probe_trace"]["order_ok"])
arm, world = case("B1_T2"); sin = [w for w in world if w["k"] == "servo_in"]
eng = ev(arm, "b1_engage"); ft = ev(arm, "first_target_published")
S["B1_T2_I2"] = {"engages": [round(a["t"], 3) for a in eng], "interrupts": [(round(a["t"], 3), a["reason"]) for a in ev(arm, "interrupt")],
                 "servo_in_6.05_to_8.8": sum(1 for w in sin if 6.05 < w["t"] < 8.8),
                 "first_target_err_mm_deg": [tuple(round(x, 4) for x in first_target_ok(f)) for f in ft[1:]], "order_ok": order_ok(arm, world),
                 "servo_in_after_9": sum(1 for w in sin if w["t"] > 9)}
x = S["B1_T2_I2"]; x["pass"] = (len(eng) == 2 and 8.8 <= eng[1]["t"] <= 9.1 and x["servo_in_6.05_to_8.8"] == 0 and x["order_ok"]
                                and all(e[0] < 1e-3 and e[1] < 1e-3 for e in x["first_target_err_mm_deg"]) and x["servo_in_after_9"] > 50)
arm, world = case("B1_T3"); sin = [w for w in world if w["k"] == "servo_in"]; eng = ev(arm, "b1_engage")
S["B1_T3_N1_blip"] = {"engages": [round(a["t"], 3) for a in eng], "interrupts": [(round(a["t"], 3), a["reason"]) for a in ev(arm, "interrupt")],
                      "servo_in_after_11.1": sum(1 for w in sin if w["t"] > 11.1), "order_ok": order_ok(arm, world)}
x = S["B1_T3_N1_blip"]; x["pass"] = (len(eng) == 2 and 7.5 <= eng[1]["t"] <= 7.8 and x["servo_in_after_11.1"] == 0 and x["order_ok"]
                                     and any(11.0 <= t <= 11.1 for t, _ in x["interrupts"]))
for name, lo, hi in (("C1_F3", 7.95, 8.1), ("C1_SIL", 5.05, 5.2)):
    arm, world = case(name); sin = [w for w in world if w["k"] == "servo_in"]; ra = ev(arm, "c1_readmit"); ft = ev(arm, "first_target_published")
    ints = ev(arm, "interrupt")
    x = {"interrupts": [(round(a["t"], 3), a["reason"]) for a in ints], "readmits": [round(a["t"], 3) for a in ra],
         "first_target_err_mm_deg": [tuple(round(v, 4) for v in first_target_ok(f)) for f in ft[1:]], "order_ok": order_ok(arm, world),
         "raw_jump_mm_at_readmit": [round(float(np.linalg.norm(np.array(a["first_p"]) - np.array(a["ee_p"])) * 1000), 2) for a in ra]}
    if name == "C1_F3":
        x["servo_in_in_window_8.05_9.5"] = sum(1 for w in sin if 8.05 < w["t"] < 9.5)
        x["pass"] = (any(lo <= t <= hi and r == "evidence_not_ok" for t, r in x["interrupts"]) and x["servo_in_in_window_8.05_9.5"] == 0
                     and any(9.55 <= t <= 9.8 for t in x["readmits"]) and x["order_ok"] and all(e[0] < 1e-3 and e[1] < 1e-3 for e in x["first_target_err_mm_deg"]))
    else:
        x["pass"] = (any(lo <= t <= hi and r == "command_silence" for t, r in x["interrupts"]) and any(5.25 <= t <= 5.5 for t in x["readmits"]) and x["order_ok"])
    S[name] = x
m = json.loads((root / "rebase_math.json").read_text()); S["rebase_math"] = m
S["all_pass"] = all(v.get("pass") for v in S.values() if isinstance(v, dict))
print(json.dumps(S, indent=1))
