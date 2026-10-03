#!/usr/bin/env python3
"""M12 analysis (R11). Command-level: every message the gate received (gate.jsonl, joined to bridge.jsonl by bid) is
classified by GROUND TRUTH (never available to the gates):
  stale_delay / stale_cache / stale_keepalive   bridge-injected (bridge.jsonl label)
  stale_source   bridge forwarded an app message, but the synthetic source (feeder) had sent NO packet within the
                 SRC_FRESH = 0.100 s before the bridge received it (source stall; runtime kept its latest pose)
  fresh          otherwise
Outcome per class: admitted / total. A0 also gets 'servo_effective' = admitted and stamp age < 0.5 s (Servo's own
incoming_command_timeout), derived from the stamp age at the gate.
  analyze_m12.py trial <dir> [arm] [cond]
  analyze_m12.py set <out.json> <schedule.csv> <raw_dir>"""
import bisect, csv, json, sys
from pathlib import Path
import numpy as np
PILOT = Path("/m39") if Path("/m39/analysis").exists() else Path(__file__).resolve().parents[2] / "M39_pilot"
sys.path.insert(0, str(PILOT / "analysis"))
import analyze_m39 as A  # frozen (Trial, invalid flags)

SRC_FRESH, W0, W1, SERVO_TIMEOUT = 0.100, 6.0, 7.6, 0.5


def trial(d, arm=None, cond=None):
    d = Path(d); T = A.Trial(d); arm = arm or T.runner.get("arm"); cond = cond or T.runner.get("cond")
    out = {"trial": d.name, "arm": arm, "cond": cond}
    if T.t0 is None:
        out["invalid"] = [f"setup_{T.setup.get('setup')}"]; return out
    gate = A.jl(d / "gate.jsonl"); br = {r["bid"]: r for r in A.jl(d / "bridge.jsonl")}
    feed_t = [r["t"] for r in T.feed]
    inv = [f for f in A.invalid_flags(T, "B0", cond if cond == "INACT_CACHE" else "N0") if f != "app_rate_below_15Hz"]
    if cond == "INACT_CACHE":
        inv = [f for f in A.invalid_flags(T, "B0", "I1") if f != "app_rate_below_15Hz"]
    fresh_pre = [r for r in br.values() if r["label"] == "fresh" and 3.0 <= r["t"] <= 5.9]
    rate = len(fresh_pre) / 2.9; out["app_rate_hz"] = round(rate, 2)
    if rate < 15: inv.append("app_rate_below_15Hz")
    if not gate or not br: inv.append("chain_logs_missing")
    if cond != "SRC_STALL": inv = [f for f in inv if f != "feeder_gap"]
    else:  # the designed stall is the only allowed feeder gap
        g = [(a, b) for a, b in zip(feed_t, feed_t[1:]) if b - a > 0.1 and not (5.9 <= a and b <= 7.7)]
        inv = [f for f in inv if f != "feeder_gap"] + (["feeder_gap_outside_stall"] if g else [])
    out["invalid"] = inv
    rows = []
    for g in gate:
        b = br.get(g["bid"]);
        if b is None: continue
        if b["label"] != "fresh": truth = b["label"]
        else:
            i = bisect.bisect_right(feed_t, b["t"]) - 1
            truth = "stale_source" if (i < 0 or b["t"] - feed_t[i] > SRC_FRESH) else "fresh"
        rows.append(dict(g, truth=truth, bridge_t=b["t"], frame=b["frame"]))
    cls = {}
    for r in rows:
        c = cls.setdefault(r["truth"], {"n": 0, "admitted": 0, "n_window": 0, "admitted_window": 0, "servo_effective": 0})
        c["n"] += 1; c["admitted"] += int(r["admit"]); w = W0 <= r["t"] <= W1
        c["n_window"] += int(w); c["admitted_window"] += int(r["admit"] and w)
        c["servo_effective"] += int(r["admit"] and r["stamp_age"] < SERVO_TIMEOUT)
    out["classes"] = cls
    stale = [r for r in rows if r["truth"] != "fresh"]; fresh = [r for r in rows if r["truth"] == "fresh"]
    out["stale_total"] = len(stale); out["stale_admitted"] = sum(r["admit"] for r in stale)
    out["stale_servo_effective"] = sum(1 for r in stale if r["admit"] and r["stamp_age"] < SERVO_TIMEOUT)
    out["fresh_total"] = len(fresh); out["fresh_blocked"] = sum(1 for r in fresh if not r["admit"])
    out["fresh_blocked_window"] = sum(1 for r in fresh if not r["admit"] and W0 <= r["t"] <= W1)
    out["block_reasons"] = {}
    for r in rows:
        if not r["admit"]: out["block_reasons"][r["why"]] = out["block_reasons"].get(r["why"], 0) + 1
    pre = [r for r in rows if 3.0 <= r["t"] <= 5.9 and r["truth"] == "fresh"]
    out["pre_stamp_age_ms"] = [round(float(np.percentile([r["stamp_age"] for r in pre], q)) * 1000, 1) for q in (50, 95, 100)] if pre else None
    acq = [r["acq_age"] for r in pre if "acq_age" in r]
    out["pre_acq_age_ms"] = [round(float(np.percentile(acq, q)) * 1000, 1) for q in (50, 95, 100)] if acq else None
    win = [r for r in rows if W0 <= r["t"] <= W1]
    # descriptive only: consecutive identical pose content inside the window (a value-change heuristic would flag these)
    same = sum(1 for x, y in zip(win, win[1:]) if br[x["bid"]].get("p") == br[y["bid"]].get("p"))
    out["window_msgs"] = len(win); out["window_identical_consecutive"] = same
    return out


if __name__ == "__main__":
    if sys.argv[1] == "trial": print(json.dumps(trial(*sys.argv[2:5]), indent=1, default=str))
    elif sys.argv[1] == "set":
        out, sched, raw = sys.argv[2], sys.argv[3], Path(sys.argv[4]); res = []
        for row in csv.DictReader(open(sched)):
            for d in sorted(raw.glob(row["trial_id"] + "*")): res.append(trial(d, row["arm"], row["cond"]))
        json.dump(res, open(out, "w"), indent=1, default=str); print(len(res))
