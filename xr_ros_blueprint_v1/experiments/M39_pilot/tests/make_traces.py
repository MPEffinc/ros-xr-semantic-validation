#!/usr/bin/env python3
"""TEST-ONLY: build the deterministic inputs of the host checks.
  T1  recorded pre-flight probe (raw/preflight/probe_detect): app-tick valid/grip + recorded collector
  T2  synthetic I2: pose invalid + IO off 6.0-7.5 with grip held, release 8.5-8.8, press 8.8
  T3  synthetic N1: release 6.0-7.5 (valid, evidence ok), then a 20 ms IO-off blip at 11.01 with grip held
Synthetic collector lines are written at 5 ms with src_t0 = 0. Args: <probe_dir> <out_dir>"""
import json, sys
from pathlib import Path
pd, out = Path(sys.argv[1]), Path(sys.argv[2]); out.mkdir(parents=True, exist_ok=True)
T0p = json.loads((pd / "done.json").read_text())["t0"]
with open(out / "T1_trace.jsonl", "w") as f:
    for l in open(pd / "probe.jsonl"):
        r = json.loads(l); rt = r["right"]
        if rt is None: continue
        f.write(json.dumps({"t": r["wall"] - T0p, "valid": rt["valid"], "grip": rt["grip"], "p": [rt["x"], 1.0, -0.3]}) + "\n")
(out / "T1_src_t0").write_text(repr(T0p))
(out / "T1_collector.jsonl").write_text((pd / "collector.jsonl").read_text())
def inside(iv, t): return any(a <= t < b for a, b in iv)
def synth(name, invalid, grip, io_off, end=16.0):
    with open(out / f"{name}_trace.jsonl", "w") as f:
        t = -3.0
        while t < end:
            v = not inside(invalid, t)
            f.write(json.dumps({"t": round(t, 3), "valid": v, "grip": inside(grip, t), "p": [0.2 + 0.02 * max(0, t - 9.5), 1.0, -0.3]}) + "\n"); t += 0.01
    with open(out / f"{name}_collector.jsonl", "w") as f:
        t = -3.0; seq = 0
        while t < end:
            io = 0 if inside(io_off, t) else 1
            f.write(json.dumps({"seq": seq, "wall": round(t, 4), "client": 2, "name": "python3.12", "flags": 15 if io else 7,
                                "focused": 1, "visible": 1, "active": 1, "io": io, "inputs_blocked": 0}) + "\n"); t += 0.005; seq += 1
    (out / f"{name}_src_t0").write_text("0.0")
synth("T2", invalid=[[6.0, 7.5]], grip=[[2.0, 8.5], [8.8, 99]], io_off=[[6.0, 7.5]])
synth("T3", invalid=[], grip=[[2.0, 6.0], [7.5, 99]], io_off=[[11.01, 11.03]])
print("ok")
