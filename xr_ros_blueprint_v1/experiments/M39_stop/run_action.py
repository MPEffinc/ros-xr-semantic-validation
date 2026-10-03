#!/usr/bin/env python3
"""R10 1B-V runner: standalone JTC action trials (Gazebo + JTC only). run_action.py one <out> <tid> <DECEL|HOLD> <v> <override 0|1>
| run_action.py schedule <out> schedule_action.csv"""
import csv, json, shlex, subprocess, sys, time
from pathlib import Path
HERE = Path(__file__).resolve().parent; PILOT = HERE.parent / "M39_pilot"
WS = '/home/cclab/ros_xr_evidence/semantic_evidence_framework/experiments/P1_openvr_evidence/ws/install'
IMAGE = 'f3-xrizer-bgpump:0989a7f-v3'; Q = "-2.865212 -0.02629 -1.853711 -1.261592 -2.865212 -1.571593"
def run(out, tid, cfg, v, ovr):
    d = Path(out).resolve() / tid; d.mkdir(parents=True, exist_ok=False); d.chmod(0o777)
    a = ['run', '--rm', '--network', 'none', '-e', f'CFG={cfg}', '-e', f'V={v}', '-e', f'OVERRIDE={ovr}', '-e', f'QSTART={Q}',
         '-v', f'{PILOT}:/m39:ro', '-v', f'{HERE}:/m39s:ro', '-v', f'{d}:/results', '-v', f'{WS}:/ws/install:ro', IMAGE, 'bash', '/m39s/jtc_action/trial_action.sh']
    t = time.time(); r = subprocess.run(['sg', 'docker', '-c', shlex.join(['docker', *a])], capture_output=True, text=True, timeout=600)
    (d / 'runner.json').write_text(json.dumps({"rc": r.returncode, "wall_s": round(time.time() - t, 1), "cfg": cfg, "v": v, "override": ovr,
        "host_load": open('/proc/loadavg').read().split()[:3], "stderr_tail": r.stderr[-1500:]}) + "\n")
    print(tid, cfg, v, ovr, 'rc', r.returncode, round(time.time() - t, 1), flush=True)
if __name__ == '__main__':
    if sys.argv[1] == 'one': run(*sys.argv[2:7]); sys.exit(0)
    for row in csv.DictReader(open(sys.argv[3])): run(sys.argv[2], row["trial_id"], row["cfg"], row["v"], row["override"])
