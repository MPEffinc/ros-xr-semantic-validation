"""Run only the frozen D5 formal schedule in new trial-owned Gazebo-only containers.

The container image, read-only mounts, environment and /code are identical to
the qualified D5Q2 setup runner (run_owned.py at freeze 247d4d2), except for the
formal output directory, container-name prefix and repetition trial IDs.

Finite setup-retry rule (XRROS-S4-1.0.0 section 7: at most two setup-only
retries per cell with identical parameters): a retry is allowed ONLY when an
attempt ended without a start barrier (no barrier.json), i.e. before any source
sample, tick or outcome was produced. Retry IDs are <trial_id>_setup02 and
<trial_id>_setup03. An attempt that reached the barrier is the formal trial,
whatever its outcome or exit status; it is never retried or replaced.
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
RUNS = ROOT.parent
Q = RUNS / 's4b_cp22_d5q2_20260928T132939Z'
PROFILES = {'F100': 100_000_000, 'F250': 250_000_000, 'F500': 500_000_000}
Q3 = RUNS / 's4b_cp5b_measurement_20260923T054101Z'
Q1 = RUNS / 's4b_cp11_d3q1_20260927T071000Z'
IMAGE = 's4b-rosmonitoring-humble:20260922'
SRC = REPO / 'semantic_validation/targets/docker_teleop/ros_backend1.1'
ATTEMPT_SUFFIXES = ('', '_setup02', '_setup03')


def execute(argv, label, trial, timeout=240):
    with (ROOT / 'commands.jsonl').open('a') as file:
        file.write(json.dumps(dict(time_ns=time.time_ns(), trial=trial.name,
                                   argv=argv), sort_keys=True) + '\n')
    with (trial / (label + '.stdout')).open('w') as stdout, \
            (trial / (label + '.stderr')).open('w') as stderr:
        try:
            return subprocess.run(argv, stdout=stdout, stderr=stderr,
                                  timeout=timeout).returncode
        except subprocess.TimeoutExpired:
            stderr.write(f'\nRUNNER_TIMEOUT_{timeout}s\n')
            return 124


def docker(argv, label, trial, timeout=240):
    return execute(['sg', 'docker', '-c', shlex.join(['docker', *argv])],
                   label, trial, timeout)


def attempt(row, attempt_name):
    trial = ROOT / 'raw' / attempt_name
    trial.mkdir(parents=True, exist_ok=False)
    trial.chmod(0o777)  # Only this newly created trial directory for container UID.
    name = 's4d5f_' + attempt_name
    mode, regime, composed = row['mode'], row['regime'], row['composed']
    mounts = [f'{Q}/inputs:/code:ro', f'{Q}/analysis:/analysis:ro', f'{trial}:/results',
              '/tmp/rosmonitoring_s4a_20260922:/official:ro',
              f'{Q1}/monitor_ws/install:/monitor_ws/install:ro',
              f'{Q3}/deps:/d1deps:ro',
              f'{SRC}/src:/home/noah/ws_moveit/src:ro',
              f'{SRC}/simulation:/home/noah/ws_moveit/simulation:ro',
              '/tmp/s4closure_docker_install:/home/noah/ws_moveit/install:ro',
              '/tmp/s4closure_docker_build:/home/noah/ws_moveit/build:ro']
    argv = ['run', '-d', '--name', name, '--network', 'none', '--cap-drop', 'ALL',
            '--security-opt', 'no-new-privileges', '--entrypoint', 'sleep',
            '-e', 'ROS_DOMAIN_ID=181', '-e', 'ROS_LOCALHOST_ONLY=1',
            '-e', 'STACK=docker', '-e', f'MODE={mode}',
            '-e', f'INFO_REGIME={regime}', '-e', f'COMPOSED={composed}',
            '-e', 'STOP_DIAG=0', '-e', 'CASE_ID=D5',
            '-e', 'AGE_CONDITION=A000', '-e', f"XR_REARM_POLICY={row['rearm']}",
            '-e', 'XR_FRESHNESS_NS=250000000']
    for mount in mounts:
        argv += ['-v', mount]
    argv += ['--user', '1000:1000', '-e', 'HOME=/home/noah', IMAGE, 'infinity']
    created = False
    try:
        rc = docker(argv, 'create', trial)
        if rc:
            (trial / 'exit.json').write_text(json.dumps({'create_exit': rc}) + '\n')
            return rc
        created = True
        docker(['inspect', name], 'environment', trial)
        rc = docker(['exec', name, 'bash', '/code/launch.sh'], 'launch', trial)
        (trial / 'exit.json').write_text(json.dumps({'launch_exit': rc}) + '\n')
        return rc
    finally:
        if created:
            docker(['stop', '--time', '3', name], 'stop', trial, 20)
            # Preserve the stopped, trial-owned container for inspection.


def run(row):
    """Return (final_rc, reached_barrier, attempt_names)."""
    names = []
    for suffix in ATTEMPT_SUFFIXES:
        attempt_name = row['trial_id'] + suffix
        names.append(attempt_name)
        rc = attempt(row, attempt_name)
        reached = (ROOT / 'raw' / attempt_name / 'barrier.json').exists()
        with (ROOT / 'attempts.jsonl').open('a') as file:
            file.write(json.dumps(dict(order=int(row['order']), trial_id=row['trial_id'],
                                       attempt=attempt_name, exit=rc,
                                       reached_start_barrier=reached,
                                       time_ns=time.time_ns()), sort_keys=True) + '\n')
        if reached or rc == 0:
            return rc, reached, names
        # Pre-barrier setup failure only: no outcome exists; a retry is allowed.
    return rc, False, names


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--start', type=int, required=True)
    parser.add_argument('--end', type=int, required=True)
    args = parser.parse_args()
    with (ROOT / 'schedule.csv').open(newline='') as file:
        schedule = list(csv.DictReader(file))
    assert len(schedule) == 50
    assert [int(x['order']) for x in schedule] == list(range(1, 51))
    assert all(x['case'] == 'D5' and int(x['seed']) == 20260922 for x in schedule)
    assert 1 <= args.start <= args.end <= 50
    consecutive_post_barrier_failures = 0
    for row in schedule[args.start - 1:args.end]:
        print('START', row['order'], row['trial_id'], flush=True)
        rc, reached, names = run(row)
        print('END', row['order'], row['trial_id'], rc, 'barrier' if reached else 'no-barrier',
              ','.join(names), flush=True)
        if not reached:
            # Setup retries exhausted: stop for investigation, keep later rows NOT_RUN.
            raise SystemExit(f'SETUP_RETRIES_EXHAUSTED {row["trial_id"]}')
        consecutive_post_barrier_failures = consecutive_post_barrier_failures + 1 if rc else 0
        if consecutive_post_barrier_failures >= 2:
            # Retained as formal trials; stop so a systematic cause is inspected.
            raise SystemExit(f'TWO_CONSECUTIVE_POST_BARRIER_NONZERO {row["trial_id"]}')


if __name__ == '__main__':
    main()
