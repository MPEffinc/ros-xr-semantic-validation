#!/usr/bin/env python3
"""M39_clock runner (R06): one fresh container per trial, sequential; schedule_clock.csv; invalid-only reruns (<= 2).
Mounts the frozen M39_pilot read-only at /m39 (harness, scenarios, analysis) and this directory at /m39c.
  run_clock.py <out_dir> [first_seq]"""
import csv, json, shlex, subprocess, sys, time
from pathlib import Path
HERE = Path(__file__).resolve().parent; PILOT = HERE.parent / "M39_pilot"
WS = '/home/cclab/ros_xr_evidence/semantic_evidence_framework/experiments/P1_openvr_evidence/ws/install'
IMAGE = 'f3-xrizer-bgpump:0989a7f-v3'; Q = "-2.865212 -0.02629 -1.853711 -1.261592 -2.865212 -1.571593"
def docker(args, timeout):
    return subprocess.run(['sg', 'docker', '-c', shlex.join(['docker', *args])], capture_output=True, text=True, timeout=timeout)
def run(out, tid, arm, cond):
    d = out / tid; d.mkdir(parents=True, exist_ok=False); d.chmod(0o777)
    sc = json.loads((PILOT / "scenarios/axis_mx" / f"{cond}.json").read_text())
    env = {'ARM': arm, 'COND': cond, 'TRIAL': tid, 'QSTART': Q, 'SCEN': f'/m39/scenarios/axis_mx/{cond}.json', 'SCHED': sc['sched'], 'END': str(sc['end'])}
    a = ['run', '--rm', '--network', 'none']
    for k, v in env.items(): a += ['-e', f'{k}={v}']
    a += ['-v', f'{PILOT}:/m39:ro', '-v', f'{HERE}:/m39c:ro', '-v', f'{d}:/results', '-v', f'{WS}:/ws/install:ro', IMAGE, 'bash', '/m39c/harness/trial_clock.sh']
    la0 = open('/proc/loadavg').read().split()[:3]; t = time.time(); r = docker(a, 900)
    (d / 'runner.json').write_text(json.dumps({"rc": r.returncode, "wall_s": round(time.time() - t, 1), "t_start": t, "arm": arm, "cond": cond,
        "host_load_before": la0, "host_load_after": open('/proc/loadavg').read().split()[:3], "stderr_tail": r.stderr[-1500:]}) + "\n")
    print(tid, arm, cond, 'rc', r.returncode, round(time.time() - t, 1), flush=True)
def invalid(d):
    r = docker(['run', '--rm', '--network', 'none', '-v', f'{PILOT}:/m39:ro', '-v', f'{HERE}:/m39c:ro', IMAGE, 'python3',
                '/m39c/analysis/analyze_clock.py', 'trial', f'/m39c/{d.relative_to(HERE)}'], 300)
    try: return json.loads(r.stdout).get("invalid", ["analysis_failed"])
    except ValueError: return ["analysis_failed"]
if __name__ == '__main__':
    out = Path(sys.argv[1]).resolve(); first = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    log = open(out.parent / (out.name + ".campaign.log"), "a", buffering=1)
    for row in csv.DictReader(open(HERE / "schedule_clock.csv")):
        if int(row["seq"]) < first: continue
        for k in range(3):
            tid = row["trial_id"] + ("" if k == 0 else f"_rerun{k}")
            run(out, tid, row["arm"], row["cond"]); inv = invalid(out / tid)
            log.write(json.dumps({"wall": time.time(), "seq": row["seq"], "attempt": tid, "invalid": inv}) + "\n")
            if not inv: break
