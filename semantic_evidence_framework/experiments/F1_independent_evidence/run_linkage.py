#!/usr/bin/env python3
"""Host runner: 9 cases x 3 runs, rep-major, shuffled within each rep (seed 20261002). --smoke runs K1 once (excluded)."""
import json, random, shlex, subprocess, sys, time
from pathlib import Path
HERE = Path(__file__).resolve().parent
OUT = Path(sys.argv[2]); OUT.mkdir(parents=True, exist_ok=True)
CASES = ['K1', 'K2', 'K3a', 'K3b', 'K3c', 'K4', 'K5a', 'K5b', 'K6']
sched = [('SMOKE', 'K1', 0)] if sys.argv[1] == '--smoke' else []
if sys.argv[1] == '--formal':
    rng = random.Random(20261002)
    for rep in (1, 2, 3):
        b = list(CASES); rng.shuffle(b); sched += [(f'{c}_r{rep}', c, rep) for c in b]
for tid, case, rep in sched:
    d = OUT / tid; d.mkdir(exist_ok=False); d.chmod(0o777)
    cmd = ['run', '--rm', '--network', 'none', '-e', f'CASE={case}', '-e', f'RUN={rep}', '-v', f'{HERE}:/f1:ro', '-v', f'{d}:/results',
           'f1-monado-main:045931d', 'bash', '/f1/harness/run_case.sh']
    t = time.time(); r = subprocess.run(['sg', 'docker', '-c', shlex.join(['docker', *cmd])], capture_output=True, text=True, timeout=120)
    (d / 'runner.json').write_text(json.dumps({"rc": r.returncode, "wall_s": round(time.time() - t, 1), "stderr_tail": r.stderr[-1500:]}) + "\n")
    print(tid, r.returncode, flush=True)
