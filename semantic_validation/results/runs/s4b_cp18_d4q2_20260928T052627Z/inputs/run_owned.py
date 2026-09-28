"""Launch only named D4Q2-owned containers; record exact commands and exits.

Identical to the Q6 runner except D4 condition/profile env, naming and prefix.
"""
import argparse
import json
import os
import shlex
import subprocess
import time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
REPO=ROOT.parents[3]
Q3=ROOT.parent/'s4b_cp5b_measurement_20260923T054101Z'
Q1=ROOT.parent/'s4b_cp11_d3q1_20260927T071000Z'
parser=argparse.ArgumentParser()
parser.add_argument('stack',choices=['docker'])
parser.add_argument('mode',choices=['b0','shim','b1','b2','b3'])
parser.add_argument('--regime',choices=['native','full'],default='full')
parser.add_argument('--attempt',default='01')
parser.add_argument('--composed',action='store_true')
parser.add_argument('--stop-diagnostic',action='store_true')
parser.add_argument('--condition',required=True,choices=['A000','A050','A150','A350','A750','H1P0','FUT1S'])
parser.add_argument('--profile',required=True,choices=['F100','F250','F500'])
args=parser.parse_args()
if args.composed and args.mode != 'b2': parser.error('--composed is only a B2 variant')
if args.stop_diagnostic and args.mode not in ('b1','b3') and not (args.mode == 'b2' and args.composed):
    parser.error('--stop-diagnostic requires B1, B3, or B2-composed')
variant='b2c' if args.composed else args.mode
trial=ROOT/'raw'/f'{args.stack}_{variant}_{args.regime}_{args.condition}_{args.profile}_{args.attempt}'
trial.mkdir(parents=True, exist_ok=False)
trial.chmod(0o777)  # Only the new trial output directory; container UID mapping.
name=f's4cp18d4q2_{args.stack}_{variant}_{args.regime}_{args.condition}_{args.profile}_{args.attempt}'
def run(argv, label, timeout=240):
    with (ROOT/'commands.jsonl').open('a') as f:
        f.write(json.dumps({'time_ns':time.time_ns(),'argv':argv,'trial':trial.name})+'\n')
    result=subprocess.run(argv,stdout=(trial/(label+'.stdout')).open('w'),stderr=(trial/(label+'.stderr')).open('w'),timeout=timeout)
    return result.returncode
def docker(argv,label,timeout=240):
    return run(['sg','docker','-c',shlex.join(['docker',*argv])],label,timeout)
mounts=[f'{ROOT}/inputs:/code:ro',f'{ROOT}/analysis:/analysis:ro',f'{trial}:/results',
        '/tmp/rosmonitoring_s4a_20260922:/official:ro',
        f'{Q1}/monitor_ws/install:/monitor_ws/install:ro',
        f'{Q3}/deps:/d1deps:ro']
if args.stack=='docker':
    src=REPO/'semantic_validation/targets/docker_teleop/ros_backend1.1'
    mounts += [f'{src}/src:/home/noah/ws_moveit/src:ro',f'{src}/simulation:/home/noah/ws_moveit/simulation:ro',
      '/tmp/s4closure_docker_install:/home/noah/ws_moveit/install:ro','/tmp/s4closure_docker_build:/home/noah/ws_moveit/build:ro']
    image='s4b-rosmonitoring-humble:20260922'
else:
    mounts += [f'{REPO}/semantic_validation/targets/openvr_ur5e_jazzy:/ws_src:ro',
       f'{REPO}/semantic_validation/harness/openvr_ur5e_downstream:/harness:ro',
       '/tmp/s4closure_openvr_install:/ws/install:ro','/tmp/s4closure_openvr_build:/ws/build:ro',
       '/tmp/s4cp2_servo_ws/install:/observer/install:ro']
    image='s4b-rosmonitoring-jazzy:20260922'
argv=['run','-d','--name',name,'--network','none','--cap-drop','ALL','--security-opt','no-new-privileges',
      '--entrypoint','sleep','-e','ROS_DOMAIN_ID=181','-e','ROS_LOCALHOST_ONLY=1','-e',f'STACK={args.stack}','-e',f'MODE={args.mode}','-e',f'INFO_REGIME={args.regime}']
argv += ['-e',f'COMPOSED={int(args.composed)}']
argv += ['-e',f'STOP_DIAG={int(args.stop_diagnostic)}']
argv += ['-e','CASE_ID=D4','-e',f'AGE_CONDITION={args.condition}',
         '-e',f"XR_FRESHNESS_NS={ {'F100':100_000_000,'F250':250_000_000,'F500':500_000_000}[args.profile] }"]
for mount in mounts: argv+=['-v',mount]
if args.stack=='docker': argv+=['--user','1000:1000','-e','HOME=/home/noah']
argv += [image,'infinity']
if docker(argv,'create'):
    raise SystemExit(1)
try:
    docker(['inspect',name],'environment')
    rc=docker(['exec',name,'bash','/code/launch.sh'],'launch',240)
    (trial/'exit.json').write_text(json.dumps({'launch_exit':rc}))
finally:
    docker(['stop','--time','3',name],'stop',20)
    # Keep stopped container for inspection; no pre-existing process touched.
