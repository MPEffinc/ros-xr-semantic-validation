#!/usr/bin/env python3
"""R03 §7/§8 campaign driver: runs schedule rows in order; after each trial, the frozen analysis (in the trial image)
checks ONLY the instrumentation-invalid flags; an invalid trial is rerun in the same slot (<id>_rerun1, _rerun2), at
most twice. Every attempt is kept. Outcomes are never inspected here.
  run_campaign.py <out_dir> <schedule.csv> <scen_dir> "<q1..q6>" [first_seq]"""
import csv, json, shlex, subprocess, sys, time
from pathlib import Path
from run_m39 import run, HERE, IMAGE
out, sched, scen, q = sys.argv[1:5]; first = int(sys.argv[5]) if len(sys.argv) > 5 else 1
out = Path(out).resolve(); log = open(out.parent / (out.name + ".campaign.log"), "a", buffering=1)
def invalid(d):
    rel = d.relative_to(HERE)
    cmd = ['run', '--rm', '--network', 'none', '-v', f'{HERE}:/m39:ro', IMAGE, 'python3', '/m39/analysis/analyze_m39.py', 'trial', f'/m39/{rel}']
    r = subprocess.run(['sg', 'docker', '-c', shlex.join(['docker', *cmd])], capture_output=True, text=True, timeout=300)
    try: return json.loads(r.stdout).get("invalid", ["analysis_failed"])
    except ValueError: return ["analysis_failed"]
for row in csv.DictReader(open(sched)):
    if int(row["seq"]) < first: continue
    for k in range(3):
        tid = row["trial_id"] + ("" if k == 0 else f"_rerun{k}")
        rc = run(out, tid, row["arm"], row["cond"], scen, q)
        inv = invalid(out / tid)
        log.write(json.dumps({"wall": time.time(), "seq": row["seq"], "attempt": tid, "rc": rc, "invalid": inv}) + "\n")
        if not inv: break
