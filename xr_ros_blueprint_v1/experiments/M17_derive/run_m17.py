#!/usr/bin/env python3
"""M17 runner (R28). Executes a `git archive` snapshot of the freeze commit (M17_derive), builds m17_msgs once from it
(run_snapshot/<sha>/m17b), verifies the snapshot hash list before every trial.
  run_m17.py <sha> one <out> <tid> <arm> <cond>  |  run_m17.py <sha> schedule <out> <schedule.csv>"""
import csv, hashlib, json, shlex, subprocess, sys, time
from pathlib import Path
HERE = Path(__file__).resolve().parent; REPO = HERE.parents[2]; SUB = "xr_ros_blueprint_v1/experiments"; IMAGE = 'm3-ordering-mux:v1'
def docker(a, timeout):
    # named containers are killed on timeout so that no trial container outlives its slot
    name = f"m17_{int(time.time() * 1000)}" if a and a[0] == 'run' else None
    if name: a = [a[0], '--name', name, *a[1:]]
    try: return subprocess.run(['sg', 'docker', '-c', shlex.join(['docker', *a])], capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        subprocess.run(['sg', 'docker', '-c', shlex.join(['docker', 'kill', name])], capture_output=True, text=True)
        return subprocess.CompletedProcess(a, 124, "", "timeout_killed")
def snapshot(sha):
    root = HERE / "run_snapshot" / sha
    if not root.exists():
        root.mkdir(parents=True)
        a = subprocess.run(["git", "-C", str(REPO), "archive", sha, f"{SUB}/M17_derive"], capture_output=True, check=True)
        subprocess.run(["tar", "-x", "-C", str(root)], input=a.stdout, check=True)
    base = root / SUB / "M17_derive"; b = root / "m17b"
    if not (b / "install").exists():
        b.mkdir(exist_ok=True); b.chmod(0o777)
        r = docker(['run', '--rm', '--network', 'none', '-v', f'{base}/src:/src:ro', '-v', f'{b}:/b', IMAGE, 'bash', '-c',
                    'source /opt/ros/jazzy/setup.bash; cd /b && colcon build --base-paths /src > /b/colcon.log 2>&1; tail -2 /b/colcon.log; chown -R 1000:1000 /b'], 1200)
        (root / "m17b_build.log").write_text(r.stdout + r.stderr)
    return base, b
def verify(base, required=True):
    fl = base / "FREEZE_SHA256.txt"
    if not fl.exists():
        if required: raise SystemExit("no FREEZE list")
        return False
    for line in fl.read_text().splitlines():
        h, f = line.split(None, 1); p = base / f.strip()
        if p.exists() and hashlib.sha256(p.read_bytes()).hexdigest() != h: raise SystemExit(f"hash mismatch {f}")
    return True
def run(base, b, out, tid, arm, cond, required=True):
    verified = verify(base, required)
    d = Path(out).resolve() / tid; d.mkdir(parents=True, exist_ok=False); d.chmod(0o777)
    a = ['run', '--rm', '--network', 'none', '-e', f'ARM={arm}', '-e', f'COND={cond}', '-e', f'TRIAL={tid}',
         '-v', f'{base}:/m17:ro', '-v', f'{b}:/m17b:ro', '-v', f'{d}:/results', IMAGE, 'bash', '/m17/harness/trial_m17.sh']
    t = time.time(); r = docker(a, 300)
    docker(['run', '--rm', '--network', 'none', '-v', f'{d}:/results', IMAGE, 'chown', '-R', '1000:1000', '/results'], 60)
    (d / 'runner.json').write_text(json.dumps({"rc": r.returncode, "wall_s": round(time.time() - t, 1), "arm": arm, "cond": cond,
        "snapshot": str(base), "snapshot_hash_verified": verified, "host_load": open('/proc/loadavg').read().split()[:3], "stderr_tail": r.stderr[-1500:]}) + "\n")
    print(tid, arm, cond, 'rc', r.returncode, round(time.time() - t, 1), flush=True); return d
def invalid(base, d, arm, cond):
    r = docker(['run', '--rm', '--network', 'none', '-v', f'{base}:/m17:ro', '-v', f'{d}:/t:ro', IMAGE, 'python3', '/m17/analysis/analyze_m17.py', 'trial', '/t', arm, cond], 120)
    try: return json.loads(r.stdout).get("invalid", ["analysis_failed"])
    except ValueError: return ["analysis_failed"]
if __name__ == '__main__':
    sha = sys.argv[1]; base, b = snapshot(sha)
    if sys.argv[2] == 'one': run(base, b, *sys.argv[3:7], required=False); sys.exit(0)
    verify(base); out = Path(sys.argv[3]).resolve(); log = open(out.parent / (out.name + ".campaign.log"), "a", buffering=1)
    for row in csv.DictReader(open(sys.argv[4])):
        for k in range(3):
            tid = row["trial_id"] + ("" if k == 0 else f"_rerun{k}")
            d = run(base, b, out, tid, row["arm"], row["cond"]); inv = invalid(base, d, row["arm"], row["cond"])
            log.write(json.dumps({"wall": time.time(), "seq": row["seq"], "attempt": tid, "invalid": inv, "snapshot": sha}) + "\n")
            if not inv: break
