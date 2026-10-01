#!/usr/bin/env python3
"""Host runner for P1: one fresh container per trial, sequential, --network none.

  python3 run_pilot.py --schedule schedule.csv --out ../../results/raw/P1/<run_id> [--start N --end M]
  python3 run_pilot.py --smoke C0_NORMAL B0 --out ...
Setup-retry rule: a trial whose setup.json does not report "ok" (no barrier) is retried up to 2
times with identical parameters; a trial that reached the barrier is final, whatever its outcome.
"""
import argparse, csv, json, os, shlex, subprocess, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
IMAGE = 'openvr-jazzy-sim:local'
TARGET = '/home/cclab/ros_xr/Deprecated/semantic_validation/targets/openvr_ur5e_jazzy'


def docker(argv, timeout=300):
    return subprocess.run(['sg', 'docker', '-c', shlex.join(['docker', *argv])], capture_output=True, text=True, timeout=timeout)


def attempt(out, trial_id, case, defense):
    d = out / trial_id
    d.mkdir(parents=True, exist_ok=False)
    d.chmod(0o777)
    name = 'p1_' + trial_id.lower()
    env = ['-e', f'P1_CASE={case}', '-e', f'P1_DEFENSE={defense}', '-e', f'P1_TRIAL={trial_id}', '-e', 'HOME=/tmp']
    if defense == 'D_TO':
        env += ['-e', 'P1_SERVO_TIMEOUT=0.1']
    mounts = [f'{HERE}/harness:/p1/harness:ro', f'{HERE}/scenarios:/p1/scenarios:ro', f'{d}:/results',
              f'{HERE}/ws/install:/ws/install:ro', f'{TARGET}:/ws_src:ro']
    argv = ['run', '--rm', '--name', name, '--network', 'none', '--cap-drop', 'ALL', '--security-opt',
            'no-new-privileges', '--user', '1000:1000', *env]
    for m in mounts:
        argv += ['-v', m]
    argv += [IMAGE, 'bash', '/p1/harness/trial.sh']
    t = time.time()
    r = docker(argv, timeout=400)
    (d / 'runner.json').write_text(json.dumps(dict(rc=r.returncode, wall_s=round(time.time() - t, 1),
                                                   stderr_tail=r.stderr[-2000:], argv=argv)) + '\n')
    try:
        return json.loads((d / 'setup.json').read_text()).get('setup') == 'ok' and (d / 'done.json').exists()
    except FileNotFoundError:
        return False


def run(out, trial_id, case, defense):
    for s in ('', '_setup02', '_setup03'):
        ok = attempt(out, trial_id + s, case, defense)
        with (out / 'attempts.jsonl').open('a') as f:
            f.write(json.dumps(dict(trial=trial_id + s, case=case, defense=defense, ok=ok, time_ns=time.time_ns())) + '\n')
        if ok:
            return True
    return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--schedule'); ap.add_argument('--out', required=True)
    ap.add_argument('--start', type=int, default=1); ap.add_argument('--end', type=int, default=10**6)
    ap.add_argument('--smoke', nargs=2)
    a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    if a.smoke:
        print('SMOKE', run(out, 'SMOKE_' + a.smoke[0] + '_' + a.smoke[1], *a.smoke), flush=True); return
    rows = list(csv.DictReader(open(a.schedule)))
    for r in rows[a.start - 1:a.end]:
        print('START', r['order'], r['trial_id'], flush=True)
        ok = run(out, r['trial_id'], r['case'], r['defense'])
        print('END', r['order'], r['trial_id'], 'ok' if ok else 'SETUP_EXHAUSTED', flush=True)
        if not ok:
            raise SystemExit('SETUP_RETRIES_EXHAUSTED ' + r['trial_id'])


if __name__ == '__main__':
    main()
