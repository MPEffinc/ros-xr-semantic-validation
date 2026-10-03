#!/usr/bin/env python3
"""M12_receiver runner (R16). Executes a `git archive` snapshot of the freeze commit (run_snapshot/<sha>/), builds the
workspace ONCE from it plus the pinned upstream (/home/cclab/ros_xr/Deprecated/.../docker_teleop @64cbdde, read-only;
HEAD verified), and before every trial verifies the snapshot hash list and the build hash file.
  run_r.py <sha> one <out_dir> <trial_id> <arm> <cond>   |   run_r.py <sha> schedule <out_dir> <schedule.csv>"""
import csv, hashlib, json, shlex, subprocess, sys, time
from pathlib import Path
HERE = Path(__file__).resolve().parent; REPO = HERE.parents[2]
DT = "/home/cclab/ros_xr/Deprecated/semantic_validation/targets/docker_teleop"; DT_SHA = "64cbdde88bc52c6a80d37f994752e50f95ba537e"
IMAGE = "docker-teleop-humble:local"; SUB = "xr_ros_blueprint_v1/experiments/M12_receiver"
def docker(a, timeout): return subprocess.run(['sg', 'docker', '-c', shlex.join(['docker', *a])], capture_output=True, text=True, timeout=timeout)
def snapshot(sha):
    root = HERE / "run_snapshot" / sha; base = root / SUB
    if not base.exists():
        root.mkdir(parents=True, exist_ok=True)
        a = subprocess.run(["git", "-C", str(REPO), "archive", sha, SUB], capture_output=True, check=True)
        subprocess.run(["tar", "-x", "-C", str(root)], input=a.stdout, check=True)
    return root, base
def verify(root, base, required=True):
    head = subprocess.run(["git", "-C", DT, "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    dirty = subprocess.run(["git", "-C", DT, "status", "--porcelain"], capture_output=True, text=True).stdout.strip()
    if head != DT_SHA or dirty: raise SystemExit(f"upstream not at {DT_SHA} or dirty")
    fl = base / "FREEZE_SHA256.txt"
    if not fl.exists():
        if required: raise SystemExit("no FREEZE list in snapshot")
        return False
    for line in fl.read_text().splitlines():
        h, f = line.split(None, 1); p = base / f.strip()
        if p.exists() and hashlib.sha256(p.read_bytes()).hexdigest() != h: raise SystemExit(f"hash mismatch {f}")
    return True
def build(root, base):
    b = root / "build"
    if not (b / "BUILD_SHA256.txt").exists():
        b.mkdir(exist_ok=True); b.chmod(0o777)
        r = docker(['run', '--rm', '--network', 'none', '--entrypoint', 'bash', '-v', f'{DT}:/dt:ro', '-v', f'{base}:/m12r:ro', '-v', f'{b}:/build',
                    IMAGE, '/m12r/harness/build_ws.sh'], 1800)
        (root / "build.log").write_text(r.stdout + r.stderr)
        if not (b / "BUILD_SHA256.txt").exists(): raise SystemExit("build failed")
    return b
def run(root, base, b, out, tid, arm, cond, required=True):
    verified = verify(root, base, required)
    d = Path(out).resolve() / tid; d.mkdir(parents=True, exist_ok=False); d.chmod(0o777)
    sc = json.loads((base / "scenarios" / f"{cond}.json").read_text())
    a = ['run', '--rm', '--network', 'none', '--entrypoint', 'bash', '-e', f'ARM={arm}', '-e', f'COND={cond}', '-e', f'SCEN=/m12r/scenarios/{cond}.json',
         '-e', f'END={sc["end"]}', '-v', f'{base}:/m12r:ro', '-v', f'{b}:/build:ro', '-v', f'{d}:/results', IMAGE, '/m12r/harness/trial_r.sh']
    t = time.time(); r = docker(a, 600)
    (d / 'runner.json').write_text(json.dumps({"rc": r.returncode, "wall_s": round(time.time() - t, 1), "arm": arm, "cond": cond, "snapshot": str(base),
        "snapshot_hash_verified": verified, "build_sha": (b / "BUILD_SHA256.txt").read_text(), "host_load": open('/proc/loadavg').read().split()[:3],
        "stderr_tail": r.stderr[-1500:]}) + "\n")
    print(tid, arm, cond, 'rc', r.returncode, round(time.time() - t, 1), flush=True); return d
def invalid(base, b, d, cond):
    r = docker(['run', '--rm', '--network', 'none', '--entrypoint', 'python3', '-v', f'{base}:/m12r:ro', '-v', f'{d}:/t:ro', IMAGE,
                '/m12r/analysis/analyze_r.py', 'trial', '/t', cond], 300)
    try: return json.loads(r.stdout).get("invalid", ["analysis_failed"])
    except ValueError: return ["analysis_failed"]
if __name__ == '__main__':
    sha = sys.argv[1]; root, base = snapshot(sha); b = build(root, base)
    if sys.argv[2] == 'one': run(root, base, b, *sys.argv[3:7], required=False); sys.exit(0)
    verify(root, base); out = Path(sys.argv[3]).resolve(); log = open(out.parent / (out.name + ".campaign.log"), "a", buffering=1)
    for row in csv.DictReader(open(sys.argv[4])):
        for k in range(3):
            tid = row["trial_id"] + ("" if k == 0 else f"_rerun{k}")
            d = run(root, base, b, out, tid, row["arm"], row["cond"]); inv = invalid(base, b, d, row["cond"])
            log.write(json.dumps({"wall": time.time(), "seq": row["seq"], "attempt": tid, "invalid": inv, "snapshot": sha}) + "\n")
            if not inv: break
