"""Run only the frozen D2 schedule in new trial-owned Gazebo-only containers."""
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
Q3 = RUNS / 's4b_cp5b_measurement_20260923T054101Z'
Q9 = RUNS / 's4b_cp9_d2q3_20260927T020700Z'
IMAGE = 's4b-rosmonitoring-humble:20260922'
SRC = REPO / 'semantic_validation/targets/docker_teleop/ros_backend1.1'


def execute(argv, label, trial, timeout=240):
    with (ROOT / 'commands.jsonl').open('a') as file:
        file.write(json.dumps(dict(time_ns=time.time_ns(), trial=trial.name,
                                   argv=argv), sort_keys=True) + '\n')
    with (trial / (label + '.stdout')).open('w') as stdout, \
            (trial / (label + '.stderr')).open('w') as stderr:
        return subprocess.run(argv, stdout=stdout, stderr=stderr,
                              timeout=timeout).returncode


def docker(argv, label, trial, timeout=240):
    return execute(['sg', 'docker', '-c', shlex.join(['docker', *argv])],
                   label, trial, timeout)


def run(row):
    trial = ROOT / 'raw' / row['trial_id']
    trial.mkdir(parents=True, exist_ok=False)
    trial.chmod(0o777)  # Only this newly created trial directory for container UID.
    name = 's4d2f_' + row['trial_id']
    mode, regime, composed = row['mode'], row['regime'], row['composed']
    mounts = [f'{Q9}/inputs:/code:ro', f'{trial}:/results',
              '/tmp/rosmonitoring_s4a_20260922:/official:ro',
              f'{Q3}/monitor_ws/install:/monitor_ws/install:ro',
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
            '-e', 'STOP_DIAG=0', '-e', 'CASE_ID=D2', '--user', '1000:1000', '-e', 'HOME=/home/noah']
    for mount in mounts:
        argv += ['-v', mount]
    argv += [IMAGE, 'infinity']
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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--start', type=int, required=True)
    parser.add_argument('--end', type=int, required=True)
    args = parser.parse_args()
    with (ROOT / 'schedule.csv').open(newline='') as file:
        schedule = list(csv.DictReader(file))
    assert len(schedule) == 50
    assert [int(x['order']) for x in schedule] == list(range(1, 51))
    assert 1 <= args.start <= args.end <= 50
    for row in schedule[args.start - 1:args.end]:
        print('START', row['order'], row['trial_id'], flush=True)
        rc = run(row)
        print('END', row['order'], row['trial_id'], rc, flush=True)
        if rc:
            raise SystemExit(rc)  # Preserve failure; inspect before deciding setup retry.


if __name__ == '__main__':
    main()
