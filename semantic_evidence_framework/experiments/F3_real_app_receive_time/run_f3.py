#!/usr/bin/env python3
"""F3 runner: --smoke (one GATED trial, excluded) or --formal (B0/GATED x 3, interleaved B0,GATED,GATED,B0,B0,GATED)."""
import json, shlex, subprocess, sys, time
from pathlib import Path
HERE = Path(__file__).resolve().parent; OUT = Path(sys.argv[2]); OUT.mkdir(parents=True, exist_ok=True)
WS = '/home/cclab/ros_xr_evidence/semantic_evidence_framework/experiments/P1_openvr_evidence/ws/install'
sched = [('SMOKE', 'GATED')] if sys.argv[1] == '--smoke' else [(f'{a}_r{i}', a) for i, a in enumerate(['B0', 'GATED', 'GATED', 'B0', 'B0', 'GATED'], 1)]
for tid, arm in sched:
    d = OUT / tid; d.mkdir(exist_ok=False); d.chmod(0o777)
    cmd = ['run', '--rm', '--network', 'none', '-e', f'ARM={arm}', '-e', f'TRIAL={tid}', '-v', f'{HERE}:/f3:ro', '-v', f'{d}:/results',
           '-v', f'{WS}:/ws/install:ro', 'f3-xrizer-bgpump:0989a7f-v3', 'bash', '/f3/harness/trial_f3.sh']
    t = time.time(); r = subprocess.run(['sg', 'docker', '-c', shlex.join(['docker', *cmd])], capture_output=True, text=True, timeout=600)
    (d / 'runner.json').write_text(json.dumps({"rc": r.returncode, "wall_s": round(time.time() - t, 1), "stderr_tail": r.stderr[-1500:]}) + "\n"); print(tid, r.returncode, flush=True)
