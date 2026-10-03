#!/usr/bin/env python3
"""M12_receiver analysis (R16). Ground truth per gate record (hidden from the gate), from the producer send log on the
same container clock:
  neutral      the receiver published its neutral state (B1 flag; B0: source ends with 'stale_timeout'/'startup')
  stale_gap    non-neutral, and the producer sent nothing in the 100 ms before the record (cache republish)
  stale_dup    non-neutral, and the latest packet sent before the record was a duplicate resend of an older packet
  fresh        otherwise
Motion admission = gate 'admit' on non-neutral records. Invalid: setup/rc, no producer or gate records, producer gap
> 100 ms outside designed gaps/reconnect. analyze_r.py trial <dir> <cond> | set <out.json> <schedule.csv> <raw_dir>"""
import bisect, csv, json, sys
from pathlib import Path
def jl(p): return [json.loads(l) for l in open(p)] if Path(p).exists() else []
def trial(d, cond):
    d = Path(d); out = {"trial": d.name, "cond": cond}; inv = []
    setup = (jl(d / "setup.json") or [{}])[0]; runner = (jl(d / "runner.json") or [{}])[0]
    if setup.get("setup") != "ok" or runner.get("rc", 1) != 0: inv.append("setup_or_rc")
    P = jl(d / "producer.jsonl"); G = jl(d / "gate.jsonl"); sc = json.loads((d / "scenario.json").read_text()) if (d / "scenario.json").exists() else {}
    if not P or not G: inv.append("logs_missing")
    out["invalid"] = inv; out["arm"] = runner.get("arm")
    if inv: return out
    t0 = setup["t0"]; pt = [p["wall"] - t0 for p in P]
    allowed = list(sc.get("gaps", [])) + ([sc["reconnect"]] if sc.get("reconnect") else [])
    gaps = [(a, b) for a, b in zip(pt, pt[1:]) if b - a > 0.1 and not any(x - 0.05 <= a and b <= y + 0.2 for x, y in allowed)]
    if gaps: out["invalid"] = inv + ["producer_gap"]; out["gaps"] = gaps[:3]; return out
    cls = {}; rows = []
    for g in G:
        t = g["t"]
        if t < pt[0] - 0.2 or t > pt[-1] + 0.5: continue          # before the first / after the last packet
        neutral = g["neutral"] if g.get("neutral") is not None else (str(g["source"]).endswith("stale_timeout") or str(g["source"]).endswith("startup"))
        i = bisect.bisect_right(pt, t) - 1
        if neutral: truth = "neutral"
        elif i < 0 or t - pt[i] > 0.1: truth = "stale_gap"
        elif P[i]["dup"]: truth = "stale_dup"
        else: truth = "fresh"
        c = cls.setdefault(truth, {"n": 0, "admitted": 0, "admitted_failopen": 0})
        c["n"] += 1; c["admitted"] += int(g["admit"]); c["admitted_failopen"] += int(g["admit_failopen"])
        rows.append((truth, g))
    out["classes"] = cls
    out["why"] = {}
    for truth, g in rows: out["why"].setdefault(truth, {}).setdefault(g["why"], 0); out["why"][truth][g["why"]] += 1
    out["provenance"] = sorted({g.get("provenance") for _, g in rows})
    out["producer_rate_hz"] = round(sum(1 for x in pt if 2.0 <= x <= 4.9) / 2.9, 1)
    return out
if __name__ == "__main__":
    if sys.argv[1] == "trial": print(json.dumps(trial(sys.argv[2], sys.argv[3]), indent=1, default=str))
    else:
        out, sched, raw = sys.argv[2], sys.argv[3], Path(sys.argv[4]); res = []
        for row in csv.DictReader(open(sched)):
            for d in sorted(raw.glob(row["trial_id"] + "*")): res.append(trial(d, row["cond"]))
        json.dump(res, open(out, "w"), indent=1, default=str); print(len(res))
