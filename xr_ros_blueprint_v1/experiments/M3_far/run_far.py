#!/usr/bin/env python3
"""M3_far runner (R25). Executes a `git archive` snapshot of the freeze commit (M39_pilot + M3_ordering + M3_far) and
verifies all three hash lists before every trial. Image m3-ordering-mux:v1 (trial image + ros-jazzy-topic-tools 1.3.4) for both arms.
  run_far.py <sha> one <out> <tid> <arm CUR|MUX> LATE  |  run_far.py <sha> schedule <out> <schedule.csv>"""
import csv, hashlib, json, shlex, subprocess, sys, time
from pathlib import Path
HERE = Path(__file__).resolve().parent; REPO = HERE.parents[2]; SUB = "xr_ros_blueprint_v1/experiments"
WS = '/home/cclab/ros_xr_evidence/semantic_evidence_framework/experiments/P1_openvr_evidence/ws/install'
IMAGE = 'm3-ordering-mux:v1'; Q = "-2.865212 -0.02629 -1.853711 -1.261592 -2.865212 -1.571593"
def docker(a, timeout): return subprocess.run(['sg', 'docker', '-c', shlex.join(['docker', *a])], capture_output=True, text=True, timeout=timeout)
def snapshot(sha):
    root = HERE / "run_snapshot" / sha
    if not root.exists():
        root.mkdir(parents=True)
        a = subprocess.run(["git", "-C", str(REPO), "archive", sha, f"{SUB}/M39_pilot", f"{SUB}/M3_ordering", f"{SUB}/M3_far"], capture_output=True, check=True)
        subprocess.run(["tar", "-x", "-C", str(root)], input=a.stdout, check=True)
    return root / SUB
def verify(base, required=True):
    if not (base / "M3_far/FREEZE_SHA256.txt").exists():
        if required: raise SystemExit("no FREEZE list")
        return False
    for exp in ("M3_far", "M3_ordering", "M39_pilot"):
        for line in (base / exp / "FREEZE_SHA256.txt").read_text().splitlines():
            h, f = line.split(None, 1); p = base / exp / f.strip()
            if p.exists() and hashlib.sha256(p.read_bytes()).hexdigest() != h: raise SystemExit(f"hash mismatch {exp}/{f}")
    return True
def run(base, out, tid, arm, cond, required=True):
    verified = verify(base, required)
    d = Path(out).resolve() / tid; d.mkdir(parents=True, exist_ok=False); d.chmod(0o777)
    sc = json.loads((base / "M3_ordering/scenarios/I3.json").read_text())
    env = {'ARM': arm, 'COND': cond, 'TRIAL': tid, 'QSTART': Q, 'SCEN': '/m3o/scenarios/I3.json', 'SCHED': sc['sched'], 'END': str(sc['end'])}
    a = ['run', '--rm', '--network', 'none']
    for k, v in env.items(): a += ['-e', f'{k}={v}']
    a += ['-v', f'{base}/M39_pilot:/m39:ro', '-v', f'{base}/M3_ordering:/m3o:ro', '-v', f'{base}/M3_far:/m3f:ro', '-v', f'{d}:/results', '-v', f'{WS}:/ws/install:ro', IMAGE, 'bash', '/m3f/harness/trial_far.sh']
    t = time.time(); r = docker(a, 900)
    (d / 'runner.json').write_text(json.dumps({"rc": r.returncode, "wall_s": round(time.time() - t, 1), "arm": arm, "cond": cond, "snapshot": str(base),
        "snapshot_hash_verified": verified, "host_load": open('/proc/loadavg').read().split()[:3], "stderr_tail": r.stderr[-1500:]}) + "\n")
    print(tid, arm, cond, 'rc', r.returncode, round(time.time() - t, 1), flush=True); return d
def invalid(base, d, arm, cond):
    r = docker(['run', '--rm', '--network', 'none', '-v', f'{base}/M39_pilot:/m39:ro', '-v', f'{base}/M3_ordering:/m3o:ro', '-v', f'{base}/M3_far:/m3f:ro', '-v', f'{d}:/t:ro', IMAGE,
                'python3', '/m3f/analysis/analyze_far.py', 'trial', '/t', arm, cond], 300)
    try: return json.loads(r.stdout).get("invalid", ["analysis_failed"])
    except ValueError: return ["analysis_failed"]
if __name__ == '__main__':
    sha = sys.argv[1]; base = snapshot(sha)
    if sys.argv[2] == 'one': run(base, *sys.argv[3:7], required=False); sys.exit(0)
    verify(base); out = Path(sys.argv[3]).resolve(); log = open(out.parent / (out.name + ".campaign.log"), "a", buffering=1)
    for row in csv.DictReader(open(sys.argv[4])):
        for k in range(3):
            tid = row["trial_id"] + ("" if k == 0 else f"_rerun{k}")
            d = run(base, out, tid, row["arm"], row["cond"]); inv = invalid(base, d, row["arm"], row["cond"])
            log.write(json.dumps({"wall": time.time(), "seq": row["seq"], "attempt": tid, "invalid": inv, "snapshot": sha}) + "\n")
            if not inv: break
