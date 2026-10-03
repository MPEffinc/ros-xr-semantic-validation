#!/usr/bin/env python3
"""M19 runner (R27). Executes a `git archive` snapshot of the freeze commit (M19_acl), creates the two keystores once per
snapshot (run_snapshot/<sha>/keys, ignored, never printed), verifies the snapshot hash list before every trial.
  run_acl.py <sha> one <out> <tid> <deploy> <check>  |  run_acl.py <sha> schedule <out> <schedule.csv>"""
import csv, hashlib, json, shlex, subprocess, sys, time
from pathlib import Path
HERE = Path(__file__).resolve().parent; REPO = HERE.parents[2]; SUB = "xr_ros_blueprint_v1/experiments"; IMAGE = 'm3-ordering-mux:v1'
def docker(a, timeout):
    # named containers are killed on timeout so that no trial container outlives its slot
    name = f"m19_{int(time.time() * 1000)}" if a and a[0] == 'run' else None
    if name: a = [a[0], '--name', name, *a[1:]]
    try: return subprocess.run(['sg', 'docker', '-c', shlex.join(['docker', *a])], capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        subprocess.run(['sg', 'docker', '-c', shlex.join(['docker', 'kill', name])], capture_output=True, text=True)
        return subprocess.CompletedProcess(a, 124, "", "timeout_killed")
def snapshot(sha):
    root = HERE / "run_snapshot" / sha
    if not root.exists():
        root.mkdir(parents=True)
        a = subprocess.run(["git", "-C", str(REPO), "archive", sha, f"{SUB}/M19_acl"], capture_output=True, check=True)
        subprocess.run(["tar", "-x", "-C", str(root)], input=a.stdout, check=True)
    base = root / SUB / "M19_acl"; keys = root / "keys"
    if not (keys / "D_RESTRICT" / "app_permissions.sha16").exists():
        keys.mkdir(exist_ok=True)
        r = docker(['run', '--rm', '--network', 'none', '-v', f'{base}:/m19:ro', '-v', f'{keys}:/keys', IMAGE, 'bash', '/m19/harness/keys.sh'], 600)
        (root / "keys_build.log").write_text(r.stdout[-2000:] + r.stderr[-2000:])
        if "keys_ok" not in r.stdout: raise SystemExit("key generation failed; see keys_build.log")
    return base, keys
def verify(base, required=True):
    fl = base / "FREEZE_SHA256.txt"
    if not fl.exists():
        if required: raise SystemExit("no FREEZE list")
        return False
    for line in fl.read_text().splitlines():
        h, f = line.split(None, 1); p = base / f.strip()
        if p.exists() and hashlib.sha256(p.read_bytes()).hexdigest() != h: raise SystemExit(f"hash mismatch {f}")
    return True
def run(base, keys, out, tid, deploy, check, required=True):
    verified = verify(base, required)
    d = Path(out).resolve() / tid; d.mkdir(parents=True, exist_ok=False); d.chmod(0o777)
    a = ['run', '--rm', '--network', 'none', '-e', f'DEPLOY={deploy}', '-e', f'CHECK={check}', '-e', f'TRIAL={tid}',
         '-v', f'{base}:/m19:ro', '-v', f'{keys}:/keys:ro', '-v', f'{d}:/results', IMAGE, 'bash', '/m19/harness/trial_acl.sh']
    t = time.time(); r = docker(a, 300)
    docker(['run', '--rm', '--network', 'none', '-v', f'{d}:/results', IMAGE, 'chown', '-R', '1000:1000', '/results'], 60)
    (d / 'runner.json').write_text(json.dumps({"rc": r.returncode, "wall_s": round(time.time() - t, 1), "deploy": deploy, "check": check,
        "snapshot": str(base), "snapshot_hash_verified": verified, "host_load": open('/proc/loadavg').read().split()[:3], "stderr_tail": r.stderr[-1500:]}) + "\n")
    print(tid, deploy, check, 'rc', r.returncode, round(time.time() - t, 1), flush=True); return d
def invalid(base, d, deploy, check):
    r = docker(['run', '--rm', '--network', 'none', '-v', f'{base}:/m19:ro', '-v', f'{d}:/t:ro', IMAGE, 'python3', '/m19/analysis/analyze_acl.py', 'trial', '/t', deploy, check], 120)
    try: return json.loads(r.stdout).get("invalid", ["analysis_failed"])
    except ValueError: return ["analysis_failed"]
if __name__ == '__main__':
    sha = sys.argv[1]; base, keys = snapshot(sha)
    if sys.argv[2] == 'one': run(base, keys, *sys.argv[3:7], required=False); sys.exit(0)
    verify(base); out = Path(sys.argv[3]).resolve(); log = open(out.parent / (out.name + ".campaign.log"), "a", buffering=1)
    for row in csv.DictReader(open(sys.argv[4])):
        for k in range(3):
            tid = row["trial_id"] + ("" if k == 0 else f"_rerun{k}")
            d = run(base, keys, out, tid, row["deploy"], row["check"]); inv = invalid(base, d, row["deploy"], row["check"])
            log.write(json.dumps({"wall": time.time(), "seq": row["seq"], "attempt": tid, "invalid": inv, "snapshot": sha}) + "\n")
            if not inv: break
