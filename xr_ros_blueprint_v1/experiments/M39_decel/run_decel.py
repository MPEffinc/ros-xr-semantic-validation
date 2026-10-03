#!/usr/bin/env python3
"""M39_decel runner: one fresh container per trial (frozen M39_pilot harness at /m39 ro; this dir at /m39d ro).
  run_decel.py one <out_dir> <trial_id> <arm> <cond> <stock|instr>
  run_decel.py schedule <out_dir> <schedule.csv>          (columns seq,trial_id,arm,cond,variant; invalid-only reruns <= 2)"""
import csv, json, shlex, subprocess, sys, time
from pathlib import Path
HERE = Path(__file__).resolve().parent; PILOT = HERE.parent / "M39_pilot"
WS = '/home/cclab/ros_xr_evidence/semantic_evidence_framework/experiments/P1_openvr_evidence/ws/install'
IMAGE = 'f3-xrizer-bgpump:0989a7f-v3'; Q = "-2.865212 -0.02629 -1.853711 -1.261592 -2.865212 -1.571593"
def docker(a, timeout): return subprocess.run(['sg', 'docker', '-c', shlex.join(['docker', *a])], capture_output=True, text=True, timeout=timeout)
def run(out, tid, arm, cond, variant):
    d = Path(out).resolve() / tid; d.mkdir(parents=True, exist_ok=False); d.chmod(0o777)
    sc = json.loads((PILOT / "scenarios/axis_mx" / f"{cond}.json").read_text())
    env = {'ARM': arm, 'COND': cond, 'TRIAL': tid, 'QSTART': Q, 'SCEN': f'/m39/scenarios/axis_mx/{cond}.json', 'SCHED': sc['sched'],
           'END': str(sc['end']), 'SERVO_VARIANT': variant}
    a = ['run', '--rm', '--network', 'none']
    for k, v in env.items(): a += ['-e', f'{k}={v}']
    a += ['-v', f'{PILOT}:/m39:ro', '-v', f'{HERE}:/m39d:ro', '-v', f'{d}:/results', '-v', f'{WS}:/ws/install:ro', IMAGE, 'bash', '/m39d/harness/trial_decel.sh']
    la0 = open('/proc/loadavg').read().split()[:3]; t = time.time(); r = docker(a, 900)
    (d / 'runner.json').write_text(json.dumps({"rc": r.returncode, "wall_s": round(time.time() - t, 1), "t_start": t, "arm": arm, "cond": cond,
        "variant": variant, "host_load_before": la0, "host_load_after": open('/proc/loadavg').read().split()[:3], "stderr_tail": r.stderr[-1500:]}) + "\n")
    print(tid, arm, cond, variant, 'rc', r.returncode, round(time.time() - t, 1), flush=True); return d
def invalid(d):
    r = docker(['run', '--rm', '--network', 'none', '-v', f'{PILOT}:/m39:ro', '-v', f'{d}:/t:ro', IMAGE, 'python3', '/m39/analysis/analyze_m39.py', 'trial', '/t'], 300)
    try: inv = json.loads(r.stdout).get("invalid", ["analysis_failed"])
    except ValueError: inv = ["analysis_failed"]
    sl = d / "servo_scale.jsonl"
    v = json.loads((d / "servo_variant.json").read_text()).get("servo_variant") if (d / "servo_variant.json").exists() else None
    if v == "instr" and (not sl.exists() or sl.stat().st_size == 0): inv = inv + ["servo_scale_log_missing"]
    return inv
if __name__ == '__main__':
    if sys.argv[1] == 'one': run(*sys.argv[2:7]); sys.exit(0)
    out = Path(sys.argv[2]).resolve(); log = open(out.parent / (out.name + ".campaign.log"), "a", buffering=1)
    for row in csv.DictReader(open(sys.argv[3])):
        for k in range(3):
            tid = row["trial_id"] + ("" if k == 0 else f"_rerun{k}")
            d = run(out, tid, row["arm"], row["cond"], row["variant"]); inv = invalid(d)
            log.write(json.dumps({"wall": time.time(), "seq": row["seq"], "attempt": tid, "invalid": inv}) + "\n")
            if not inv: break
