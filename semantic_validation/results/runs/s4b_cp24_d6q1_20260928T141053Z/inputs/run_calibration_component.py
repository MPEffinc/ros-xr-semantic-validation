#!/usr/bin/env python3
"""Run one trial-owned, non-Gazebo official-monitor component test."""
import argparse
import json
import shlex
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
Q1 = ROOT.parent / 's4b_cp11_d3q1_20260927T071000Z'
Q3 = ROOT.parent / 's4b_cp5b_measurement_20260923T054101Z'
parser = argparse.ArgumentParser()
parser.add_argument('--regime', choices=('native', 'full'), required=True)
parser.add_argument('--scenario', choices=('positive', 'absent_oracle',
                                           'absent_guarded_subscriber'), required=True)
parser.add_argument('--attempt', default='setup01')
args = parser.parse_args()
result = ROOT / 'preflight' / ('official_' + args.regime + '_' + args.scenario + '_' + args.attempt)
result.mkdir(parents=True, exist_ok=False)
result.chmod(0o777)
domain = 191 + ('native', 'full').index(args.regime) * 3 + (
    'positive', 'absent_oracle', 'absent_guarded_subscriber').index(args.scenario)
inner = ('source /opt/ros/humble/setup.bash; '
         'source /home/noah/ws_moveit/install/setup.bash; '
         'source /monitor_ws/install/setup.bash; '
         'export PYTHONPATH=/code:/d1deps:$PYTHONPATH; '
         'python3 /code/q4_calibration_component.py --regime ' + args.regime +
         ' --scenario ' + args.scenario)
docker = ['docker', 'run', '--rm', '--network', 'none', '--cap-drop', 'ALL',
          '--security-opt', 'no-new-privileges', '--user', '1000:1000',
          '-e', f'ROS_DOMAIN_ID={domain}', '-e', 'ROS_LOCALHOST_ONLY=1',
          '-v', f'{ROOT}/inputs:/code:ro', '-v', f'{result}:/results',
          '-v', '/tmp/rosmonitoring_s4a_20260922:/official:ro',
          '-v', f'{Q1}/monitor_ws/install:/monitor_ws/install:ro',
          '-v', f'{Q3}/deps:/d1deps:ro',
          '-v', '/tmp/s4closure_docker_install:/home/noah/ws_moveit/install:ro',
          '-v', '/tmp/s4closure_docker_build:/home/noah/ws_moveit/build:ro',
          's4b-rosmonitoring-humble:20260922', 'bash', '-c', inner]
command = ['sg', 'docker', '-c', shlex.join(docker)]
(result / 'command.json').write_text(json.dumps(command) + '\n')
with (result / 'run.stdout').open('w') as stdout, (result / 'run.stderr').open('w') as stderr:
    rc = subprocess.run(command, stdout=stdout, stderr=stderr, timeout=90).returncode
(result / 'exit.json').write_text(json.dumps({'exit_code': rc, 'domain': domain}) + '\n')
print(json.dumps({'regime': args.regime, 'scenario': args.scenario,
                  'exit_code': rc, 'result': str(result)}, sort_keys=True))
raise SystemExit(rc)
