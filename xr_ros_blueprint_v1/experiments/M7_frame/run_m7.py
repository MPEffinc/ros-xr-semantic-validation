#!/usr/bin/env python3
"""M7_frame runner (R17). Executes a `git archive` snapshot of the freeze commit (M39_pilot + M7_frame), builds m7_msgs
once from it (run_snapshot/<sha>/m7b), verifies the snapshot hash list before every trial.
  run_m7.py <sha> one <out> <tid> <arm> <cond>  |  run_m7.py <sha> schedule <out> <schedule.csv>"""
import csv, hashlib, json, shlex, subprocess, sys, time
from pathlib import Path
HERE = Path(__file__).resolve().parent; REPO = HERE.parents[2]; SUB = "xr_ros_blueprint_v1/experiments"
WS = '/home/cclab/ros_xr_evidence/semantic_evidence_framework/experiments/P1_openvr_evidence/ws/install'
IMAGE = 'f3-xrizer-bgpump:0989a7f-v3'; Q = "-2.865212 -0.02629 -1.853711 -1.261592 -2.865212 -1.571593"
COND = {"STATIC": ("0", "PASS"), "DYN": ("1", "PASS"), "DYN_DELAY": ("1", "DELAY"), "DYN_RESTAMP": ("1", "RESTAMP")}
def docker(a, timeout): return subprocess.run(['sg', 'docker', '-c', shlex.join(['docker', *a])], capture_output=True, text=True, timeout=timeout)
def snapshot(sha):
    root = HERE / "run_snapshot" / sha
    if not root.exists():
        root.mkdir(parents=True)
        a = subprocess.run(["git", "-C", str(REPO), "archive", sha, f"{SUB}/M39_pilot", f"{SUB}/M7_frame"], capture_output=True, check=True)
        subprocess.run(["tar", "-x", "-C", str(root)], input=a.stdout, check=True)
    b = root / "m7b"
    if not (b / "install").exists():
        b.mkdir(exist_ok=True); b.chmod(0o777)
        r = docker(['run', '--rm', '--network', 'none', '-v', f'{root}/{SUB}/M7_frame/src:/src:ro', '-v', f'{b}:/b', IMAGE, 'bash', '-c',
                    'source /opt/ros/jazzy/setup.bash; cd /b && colcon build --base-paths /src > /b/colcon.log 2>&1; tail -2 /b/colcon.log'], 1200)
        (root / "m7b_build.log").write_text(r.stdout + r.stderr)
    return root, root / SUB
def verify(base, required=True):
    fl = base / "M7_frame/FREEZE_SHA256.txt"
    if not fl.exists():
        if required: raise SystemExit("no FREEZE list")
        return False
    for exp in ("M7_frame", "M39_pilot"):
        for line in (base / exp / "FREEZE_SHA256.txt").read_text().splitlines():
            h, f = line.split(None, 1); p = base / exp / f.strip()
            if p.exists() and hashlib.sha256(p.read_bytes()).hexdigest() != h: raise SystemExit(f"hash mismatch {exp}/{f}")
    return True
def run(root, base, out, tid, arm, cond, required=True):
    verified = verify(base, required); dyn, bridge = COND[cond]
    d = Path(out).resolve() / tid; d.mkdir(parents=True, exist_ok=False); d.chmod(0o777)
    env = {'ARM': arm, 'COND': cond, 'TRIAL': tid, 'QSTART': Q, 'SCEN': '/m39/scenarios/axis_mx/N0.json', 'SCHED': '', 'END': '15.5', 'DYN': dyn, 'BRIDGE': bridge}
    a = ['run', '--rm', '--network', 'none']
    for k, v in env.items(): a += ['-e', f'{k}={v}']
    a += ['-v', f'{base}/M39_pilot:/m39:ro', '-v', f'{base}/M7_frame:/m7:ro', '-v', f'{root}/m7b:/m7b:ro', '-v', f'{d}:/results', '-v', f'{WS}:/ws/install:ro', IMAGE, 'bash', '/m7/harness/trial_m7.sh']
    t = time.time(); r = docker(a, 900)
    (d / 'runner.json').write_text(json.dumps({"rc": r.returncode, "wall_s": round(time.time() - t, 1), "arm": arm, "cond": cond, "dyn": dyn, "bridge": bridge,
        "snapshot": str(base), "snapshot_hash_verified": verified, "host_load": open('/proc/loadavg').read().split()[:3], "stderr_tail": r.stderr[-1500:]}) + "\n")
    print(tid, arm, cond, 'rc', r.returncode, round(time.time() - t, 1), flush=True); return d
def invalid(root, base, d, cond):
    r = docker(['run', '--rm', '--network', 'none', '-v', f'{base}/M39_pilot:/m39:ro', '-v', f'{base}/M7_frame:/m7:ro', '-v', f'{d}:/t:ro', IMAGE,
                'python3', '/m7/analysis/analyze_m7.py', 'trial', '/t', cond], 300)
    try: return json.loads(r.stdout).get("invalid", ["analysis_failed"])
    except ValueError: return ["analysis_failed"]
if __name__ == '__main__':
    sha = sys.argv[1]; root, base = snapshot(sha)
    if sys.argv[2] == 'one': run(root, base, *sys.argv[3:7], required=False); sys.exit(0)
    verify(base); out = Path(sys.argv[3]).resolve(); log = open(out.parent / (out.name + ".campaign.log"), "a", buffering=1)
    for row in csv.DictReader(open(sys.argv[4])):
        for k in range(3):
            tid = row["trial_id"] + ("" if k == 0 else f"_rerun{k}")
            d = run(root, base, out, tid, row["arm"], row["cond"]); inv = invalid(root, base, d, row["cond"])
            log.write(json.dumps({"wall": time.time(), "seq": row["seq"], "attempt": tid, "invalid": inv, "snapshot": sha}) + "\n")
            if not inv: break
