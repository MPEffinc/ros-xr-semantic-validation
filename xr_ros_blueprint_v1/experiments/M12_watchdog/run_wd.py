#!/usr/bin/env python3
"""M12_watchdog runner (R15). Executes an immutable snapshot of the freeze commit: `git archive <sha>` of M39_pilot,
M12_stamp and M12_watchdog into run_snapshot/<sha>/ (ignored). Before EVERY trial the snapshot files are checked against
the FREEZE hash lists contained in the snapshot itself; a mismatch aborts the campaign.
  run_wd.py <freeze_sha> one <out_dir> <trial_id> <arm> <cond>
  run_wd.py <freeze_sha> schedule <out_dir> <schedule.csv>
Arms: S0 = original runtime image + gate A2; S1 = receive-watchdog runtime (M12_RX_WATCHDOG_MS=100) + gate A2;
      S2 = patched runtime with receive evidence file only (no watchdog) + gate A2S."""
import csv, hashlib, json, shlex, subprocess, sys, time
from pathlib import Path
HERE = Path(__file__).resolve().parent; REPO = HERE.parents[2]
WS = '/home/cclab/ros_xr_evidence/semantic_evidence_framework/experiments/P1_openvr_evidence/ws/install'
Q = "-2.865212 -0.02629 -1.853711 -1.261592 -2.865212 -1.571593"
ARMS = {"S0": ("f3-xrizer-bgpump:0989a7f-v3", {}, "A2"),
        "S1": ("m12-monado-rxwd:045931d-v1", {"M12_RX_WATCHDOG_MS": "100"}, "A2"),
        "S2": ("m12-monado-rxwd:045931d-v1", {"M12_RX_EVIDENCE": "/tmp/m12_rx.txt"}, "A2S")}
COND_FOR_ANALYSIS = {"N_MOVE": "N_MOVE", "N_STILL": "N_STILL", "STALL15": "SRC_STALL", "STALL5": "SRC_STALL_LONG"}
SUB = "xr_ros_blueprint_v1/experiments"
def snapshot(sha):
    d = HERE / "run_snapshot" / sha
    if not d.exists():
        d.mkdir(parents=True)
        a = subprocess.run(["git", "-C", str(REPO), "archive", sha, f"{SUB}/M39_pilot", f"{SUB}/M12_stamp", f"{SUB}/M12_watchdog"], capture_output=True, check=True)
        subprocess.run(["tar", "-x", "-C", str(d)], input=a.stdout, check=True)
    return d / SUB
def verify(base, required=True):
    if not (base / "M12_watchdog/FREEZE_SHA256.txt").exists():
        if required: raise SystemExit("no FREEZE_SHA256.txt in snapshot: formal runs need a frozen commit")
        return False
    for exp, lst in (("M12_watchdog", "FREEZE_SHA256.txt"), ("M12_stamp", "FREEZE_SHA256.txt"), ("M39_pilot", "FREEZE_SHA256.txt")):
        for line in (base / exp / lst).read_text().splitlines():
            h, f = line.split(None, 1); f = f.strip()
            p = (base / exp / f) if not f.startswith(("R1", "R0")) else None
            if p is None or not p.exists(): continue
            if hashlib.sha256(p.read_bytes()).hexdigest() != h: raise SystemExit(f"snapshot hash mismatch: {exp}/{f}")
    return True
def docker(a, timeout): return subprocess.run(['sg', 'docker', '-c', shlex.join(['docker', *a])], capture_output=True, text=True, timeout=timeout)
def run(base, out, tid, arm, cond, required=True):
    verified = verify(base, required)
    image, env_x, gate = ARMS[arm]
    d = Path(out).resolve() / tid; d.mkdir(parents=True, exist_ok=False); d.chmod(0o777)
    sc = json.loads((base / "M12_watchdog/scenarios" / f"{cond}.json").read_text())
    env = {'ARM': arm, 'GATE': gate, 'COND': cond, 'TRIAL': tid, 'QSTART': Q, 'SCEN': f'/m12w/scenarios/{cond}.json', 'SCHED': sc['sched'],
           'END': str(sc['end']), 'BRIDGE': 'PASS', **env_x}
    a = ['run', '--rm', '--network', 'none']
    for k, v in env.items(): a += ['-e', f'{k}={v}']
    a += ['-v', f'{base}/M39_pilot:/m39:ro', '-v', f'{base}/M12_stamp:/m12:ro', '-v', f'{base}/M12_watchdog:/m12w:ro', '-v', f'{d}:/results',
          '-v', f'{WS}:/ws/install:ro', image, 'bash', '/m12w/harness/trial_wd.sh']
    la0 = open('/proc/loadavg').read().split()[:3]; t = time.time(); r = docker(a, 900)
    (d / 'runner.json').write_text(json.dumps({"rc": r.returncode, "wall_s": round(time.time() - t, 1), "t_start": t, "arm": arm, "cond": cond,
        "image": image, "env": env_x, "gate": gate, "snapshot": str(base), "snapshot_hash_verified": verified, "host_load_before": la0, "stderr_tail": r.stderr[-1500:]}) + "\n")
    print(tid, arm, cond, 'rc', r.returncode, round(time.time() - t, 1), flush=True); return d
def invalid(base, d, cond):
    r = docker(['run', '--rm', '--network', 'none', '-v', f'{base}/M39_pilot:/m39:ro', '-v', f'{base}/M12_stamp:/m12:ro', '-v', f'{base}/M12_watchdog:/m12w:ro',
                '-v', f'{d}:/t:ro', 'f3-xrizer-bgpump:0989a7f-v3', 'python3', '/m12w/analysis/analyze_wd.py', 'trial', '/t', cond], 300)
    try: return json.loads(r.stdout).get("invalid", ["analysis_failed"])
    except ValueError: return ["analysis_failed"]
if __name__ == '__main__':
    sha = sys.argv[1]; base = snapshot(sha)
    if sys.argv[2] == 'one': run(base, *sys.argv[3:7], required=False); sys.exit(0)
    verify(base)
    out = Path(sys.argv[3]).resolve(); log = open(out.parent / (out.name + ".campaign.log"), "a", buffering=1)
    for row in csv.DictReader(open(sys.argv[4])):
        for k in range(3):
            tid = row["trial_id"] + ("" if k == 0 else f"_rerun{k}")
            d = run(base, out, tid, row["arm"], row["cond"]); inv = invalid(base, d, row["cond"])
            log.write(json.dumps({"wall": time.time(), "seq": row["seq"], "attempt": tid, "invalid": inv, "snapshot": sha}) + "\n")
            if not inv: break
