"""Launch only named OpenVR Q1-owned Gazebo containers; record exact commands and exits.

Trial-owned container, network none, all capabilities dropped, no-new-privileges,
ROS domain 181, read-only code/vendor/overlay/monitor/dependency mounts.
"""
import argparse
import json
import shlex
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[3]
IMAGE = 's4b-rosmonitoring-jazzy:20260922'
Q1 = ROOT.parent / 's4b_ovr_q1_20260928T184158Z'
parser = argparse.ArgumentParser()
parser.add_argument('mode', choices=['b0', 'shim', 'b1', 'b2', 'b3'])
parser.add_argument('--case', required=True, choices=['W0', 'W1', 'W2', 'W3', 'W4', 'W5', 'NONE'])
parser.add_argument('--composed', action='store_true')
parser.add_argument('--st', action='store_true', help='diagnostic B2-ST monitor executor variant')
parser.add_argument('--rearm', default='R_EXPLICIT', choices=['R_EXPLICIT', 'R_AUTO'])
parser.add_argument('--attempt', required=True)
parser.add_argument('--cid-kind', default='NONE', choices=['NONE', 'DUPLICATE_ID', 'MISMATCH'])
parser.add_argument('--fault', default='NONE', choices=['NONE', 'ORACLE_ABSENT', 'ORACLE_DISCONNECT', 'ORACLE_NONRESPONSIVE', 'B1_GATE_FAIL', 'B3_GATE_FAIL'])
parser.add_argument('--prefix', default='s4ovrcxq1_')
args = parser.parse_args()
if args.composed and args.mode != 'b2':
    parser.error('--composed is only a B2 variant')
if args.st and args.mode != 'b2':
    parser.error('--st is only a B2 diagnostic variant')
variant = ('b2st' if args.st else 'b2') + ('c' if args.composed else '') if args.mode == 'b2' else args.mode
tag = args.cid_kind if args.cid_kind != 'NONE' else args.fault
trial_id = f'openvr_{variant}_full_{tag}_{args.attempt}'
trial = ROOT / 'raw' / trial_id
trial.mkdir(parents=True, exist_ok=False)
trial.chmod(0o777)  # only the new trial output directory
name = args.prefix + trial_id


def run(argv, label, timeout=300):
    with (ROOT / 'commands.jsonl').open('a') as f:
        f.write(json.dumps({'time_ns': time.time_ns(), 'argv': argv, 'trial': trial.name}) + '\n')
    with (trial / (label + '.stdout')).open('w') as out, (trial / (label + '.stderr')).open('w') as err:
        try:
            return subprocess.run(argv, stdout=out, stderr=err, timeout=timeout).returncode
        except subprocess.TimeoutExpired:
            err.write(f'\nRUNNER_TIMEOUT_{timeout}s\n')
            return 124


def docker(argv, label, timeout=300):
    return run(['sg', 'docker', '-c', shlex.join(['docker', *argv])], label, timeout)


mounts = [f'{ROOT}/inputs:/code:ro', f'{ROOT}/analysis:/analysis:ro', f'{trial}:/results',
          '/tmp/rosmonitoring_s4a_20260922:/official:ro',
          f'{Q1}/monitor_build/monitor_ws/install:/monitor_ws/install:ro',   # frozen OpenVR Q1 build
          f'{Q1}/deps:/ovrdeps:ro',
          f'{REPO}/semantic_validation/targets/openvr_ur5e_jazzy:/ws_src:ro',
          f'{REPO}/semantic_validation/harness/openvr_ur5e_downstream:/harness:ro',
          '/tmp/s4closure_openvr_install:/ws/install:ro', '/tmp/s4closure_openvr_build:/ws/build:ro',
          '/tmp/s4cp2_servo_ws/install:/observer/install:ro']
argv = ['run', '-d', '--name', name, '--network', 'none', '--cap-drop', 'ALL', '--security-opt', 'no-new-privileges',
        '--entrypoint', 'sleep', '--user', '1000:1000', '-e', 'HOME=/tmp',
        '-e', 'ROS_DOMAIN_ID=181', '-e', 'ROS_LOCALHOST_ONLY=1', '-e', 'STACK=openvr', '-e', f'MODE={args.mode}',
        '-e', 'INFO_REGIME=full', '-e', f'COMPOSED={int(args.composed)}', '-e', f"B2_EXECUTOR={'ST' if args.st else 'OFFICIAL'}", '-e', f'OVR_CASE={args.case}',
        '-e', f'XR_REARM_POLICY={args.rearm}', '-e', 'XR_FRESHNESS_NS=250000000', '-e', 'XR_CAPTURE_NS=12000000000']
if args.cid_kind != 'NONE':
    argv += ['-e', 'CASE_ID=CID', '-e', f'OVR_CID_KIND={args.cid_kind}']
if args.fault != 'NONE':
    offset = 2_910_000_000 if args.fault.startswith('ORACLE_') else 3_010_000_000
    argv += ['-e', f'CMON_FAULT={args.fault}', '-e', f'CMON_FAULT_OFFSET_NS={offset}']
for mount in mounts:
    argv += ['-v', mount]
argv += [IMAGE, 'infinity']
created = False
try:
    rc = docker(argv, 'create')
    if rc:
        (trial / 'exit.json').write_text(json.dumps({'create_exit': rc}) + '\n')
        raise SystemExit(0)
    created = True
    docker(['inspect', name], 'environment')
    rc = docker(['exec', name, 'bash', '/code/ovr_launch.sh'], 'launch', 300)
    (trial / 'exit.json').write_text(json.dumps({'launch_exit': rc}) + '\n')
finally:
    if created:
        docker(['stop', '--time', '3', name], 'stop', 20)
        # Keep the stopped trial-owned container for inspection; nothing else touched.
