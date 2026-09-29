"""Run only the frozen OpenVR W0-W5 formal schedule in new trial-owned Gazebo containers.

Image, read-only mounts (/code, /analysis, monitor install, trial-local deps are the
frozen OpenVR Q1 ones), environment and launch are identical to the qualified Q1
runner (run_owned.py at freeze 92240c6) except output directory, container-name
prefix and repetition trial IDs.

Setup-retry rule (XRROS-S4-1.0.0 section 7): a retry (<id>_setup02/_setup03,
identical parameters) ONLY when an attempt ended without a start barrier. An
attempt that reached the barrier is the formal trial, whatever its outcome.
"""
import argparse
import csv
import json
import shlex
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[3]
Q = ROOT.parent / 's4b_ovr_q1_20260928T184158Z'
IMAGE = 's4b-rosmonitoring-jazzy:20260922'
SUFFIXES = ('', '_setup02', '_setup03')


def execute(argv, label, trial, timeout=300):
    with (ROOT / 'commands.jsonl').open('a') as f:
        f.write(json.dumps(dict(time_ns=time.time_ns(), trial=trial.name, argv=argv), sort_keys=True) + '\n')
    with (trial / (label + '.stdout')).open('w') as out, (trial / (label + '.stderr')).open('w') as err:
        try:
            return subprocess.run(argv, stdout=out, stderr=err, timeout=timeout).returncode
        except subprocess.TimeoutExpired:
            err.write(f'\nRUNNER_TIMEOUT_{timeout}s\n')
            return 124


def docker(argv, label, trial, timeout=300):
    return execute(['sg', 'docker', '-c', shlex.join(['docker', *argv])], label, trial, timeout)


def attempt(row, name):
    trial = ROOT / 'raw' / name
    trial.mkdir(parents=True, exist_ok=False)
    trial.chmod(0o777)
    cname = 's4ovrf_' + name
    mounts = [f'{Q}/inputs:/code:ro', f'{Q}/analysis:/analysis:ro', f'{trial}:/results',
              '/tmp/rosmonitoring_s4a_20260922:/official:ro',
              f'{Q}/monitor_build/monitor_ws/install:/monitor_ws/install:ro', f'{Q}/deps:/ovrdeps:ro',
              f'{REPO}/semantic_validation/targets/openvr_ur5e_jazzy:/ws_src:ro',
              f'{REPO}/semantic_validation/harness/openvr_ur5e_downstream:/harness:ro',
              '/tmp/s4closure_openvr_install:/ws/install:ro', '/tmp/s4closure_openvr_build:/ws/build:ro',
              '/tmp/s4cp2_servo_ws/install:/observer/install:ro']
    argv = ['run', '-d', '--name', cname, '--network', 'none', '--cap-drop', 'ALL', '--security-opt', 'no-new-privileges',
            '--entrypoint', 'sleep', '--user', '1000:1000', '-e', 'HOME=/tmp',
            '-e', 'ROS_DOMAIN_ID=181', '-e', 'ROS_LOCALHOST_ONLY=1', '-e', 'STACK=openvr', '-e', f"MODE={row['mode']}",
            '-e', 'INFO_REGIME=full', '-e', f"COMPOSED={row['composed']}",
            '-e', f"B2_EXECUTOR={'ST' if row['st'] == '1' else 'OFFICIAL'}",
            '-e', f"OVR_CASE={row['case']}", '-e', f"XR_REARM_POLICY={row['rearm']}",
            '-e', 'XR_FRESHNESS_NS=250000000', '-e', 'XR_CAPTURE_NS=12000000000']
    for m in mounts:
        argv += ['-v', m]
    argv += [IMAGE, 'infinity']
    created = False
    try:
        rc = docker(argv, 'create', trial)
        if rc:
            (trial / 'exit.json').write_text(json.dumps({'create_exit': rc}) + '\n')
            return rc
        created = True
        docker(['inspect', cname], 'environment', trial)
        rc = docker(['exec', cname, 'bash', '/code/ovr_launch.sh'], 'launch', trial)
        (trial / 'exit.json').write_text(json.dumps({'launch_exit': rc}) + '\n')
        return rc
    finally:
        if created:
            docker(['stop', '--time', '3', cname], 'stop', trial, 20)


def run(row):
    names = []
    rc = None
    for s in SUFFIXES:
        name = row['trial_id'] + s
        names.append(name)
        rc = attempt(row, name)
        reached = (ROOT / 'raw' / name / 'barrier.json').exists()
        with (ROOT / 'attempts.jsonl').open('a') as f:
            f.write(json.dumps(dict(order=int(row['order']), trial_id=row['trial_id'], attempt=name, exit=rc,
                                    reached_start_barrier=reached, time_ns=time.time_ns()), sort_keys=True) + '\n')
        if reached:
            return rc, True, names
    return rc, False, names


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--start', type=int, required=True)
    ap.add_argument('--end', type=int, required=True)
    a = ap.parse_args()
    schedule = list(csv.DictReader((ROOT / 'schedule.csv').open()))
    assert len(schedule) == 205 and [int(x['order']) for x in schedule] == list(range(1, 206))
    assert all(x['case_family'] == 'OVR' and int(x['seed']) == 20260922 for x in schedule)
    consecutive = 0
    for row in schedule[a.start - 1:a.end]:
        print('START', row['order'], row['trial_id'], flush=True)
        rc, reached, names = run(row)
        print('END', row['order'], row['trial_id'], rc, 'barrier' if reached else 'no-barrier', ','.join(names), flush=True)
        if not reached:
            raise SystemExit(f'SETUP_RETRIES_EXHAUSTED {row["trial_id"]}')
        consecutive = consecutive + 1 if rc else 0
        if consecutive >= 2:
            raise SystemExit(f'TWO_CONSECUTIVE_POST_BARRIER_NONZERO {row["trial_id"]}')


if __name__ == '__main__':
    main()
