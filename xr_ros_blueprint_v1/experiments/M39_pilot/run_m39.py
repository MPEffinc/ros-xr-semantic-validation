#!/usr/bin/env python3
"""M39 runner: one fresh container per trial, sequential.
  run_m39.py one <out_dir> <trial_id> <arm> <cond> <scen_dir> "<q1..q6>"
  run_m39.py schedule <out_dir> <schedule.csv> <scen_dir> "<q1..q6>" [first_row]
Writes <out_dir>/<trial_id>/ (all container outputs) + runner.json (rc, wall time, host loadavg before/after)."""
import csv, json, shlex, subprocess, sys, time
from pathlib import Path
HERE = Path(__file__).resolve().parent
WS = '/home/cclab/ros_xr_evidence/semantic_evidence_framework/experiments/P1_openvr_evidence/ws/install'
IMAGE = 'f3-xrizer-bgpump:0989a7f-v3'


def run(out, tid, arm, cond, scen_dir, q):
    d = Path(out).resolve() / tid; d.mkdir(parents=True, exist_ok=False); d.chmod(0o777)
    sc = json.loads((Path(scen_dir) / f"{cond}.json").read_text())
    rel = Path(scen_dir).resolve().relative_to(HERE)
    env = {'ARM': arm, 'COND': cond, 'TRIAL': tid, 'QSTART': q, 'SCEN': f'/m39/{rel}/{cond}.json', 'SCHED': sc['sched'], 'END': str(sc['end'])}
    cmd = ['run', '--rm', '--network', 'none']
    for k, v in env.items(): cmd += ['-e', f'{k}={v}']
    cmd += ['-v', f'{HERE}:/m39:ro', '-v', f'{d}:/results', '-v', f'{WS}:/ws/install:ro', IMAGE, 'bash', '/m39/harness/trial.sh']
    la0 = open('/proc/loadavg').read().split()[:3]; t = time.time()
    r = subprocess.run(['sg', 'docker', '-c', shlex.join(['docker', *cmd])], capture_output=True, text=True, timeout=900)
    (d / 'runner.json').write_text(json.dumps({"rc": r.returncode, "wall_s": round(time.time() - t, 1), "t_start": t, "arm": arm,
                                               "cond": cond, "host_load_before": la0, "host_load_after": open('/proc/loadavg').read().split()[:3],
                                               "stderr_tail": r.stderr[-1500:]}) + "\n")
    print(tid, arm, cond, 'rc', r.returncode, round(time.time() - t, 1), flush=True)
    return r.returncode


if __name__ == '__main__':
    if sys.argv[1] == 'one':
        sys.exit(run(*sys.argv[2:8]))
    out, sched, scen, q = sys.argv[2:6]; first = int(sys.argv[6]) if len(sys.argv) > 6 else 0
    rows = list(csv.DictReader(open(sched)))
    for row in rows[first:]:
        run(out, row['trial_id'], row['arm'], row['cond'], scen, q)
