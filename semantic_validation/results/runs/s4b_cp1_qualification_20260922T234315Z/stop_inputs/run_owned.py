"""Launch only named closure-owned containers; record exact commands and exits."""
import argparse
import json
import os
import shlex
import subprocess
import time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
REPO=ROOT.parents[3]
parser=argparse.ArgumentParser()
parser.add_argument('stack',choices=['docker','openvr'])
parser.add_argument('mode',choices=['hold_fast'])
parser.add_argument('--attempt',default='01')
args=parser.parse_args()
trial=ROOT/'raw'/f'{args.stack}_{args.mode}_{args.attempt}'
trial.mkdir(exist_ok=False)
trial.chmod(0o777)  # Only the new trial output directory; container UID mapping.
name=f's4cp1_{args.stack}_{args.mode}_{args.attempt}'
def run(argv, label, timeout=240):
    with (ROOT/'commands.jsonl').open('a') as f:
        f.write(json.dumps({'time_ns':time.time_ns(),'argv':argv,'trial':trial.name})+'\n')
    result=subprocess.run(argv,stdout=(trial/(label+'.stdout')).open('w'),stderr=(trial/(label+'.stderr')).open('w'),timeout=timeout)
    return result.returncode
def docker(argv,label,timeout=240):
    return run(['sg','docker','-c',shlex.join(['docker',*argv])],label,timeout)
mounts=[f'{ROOT}/inputs:/code:ro',f'{trial}:/results']
if args.stack=='docker':
    src=REPO/'semantic_validation/targets/docker_teleop/ros_backend1.1'
    mounts += [f'{src}/src:/home/noah/ws_moveit/src:ro',f'{src}/simulation:/home/noah/ws_moveit/simulation:ro',
      '/tmp/s4closure_docker_install:/home/noah/ws_moveit/install:ro','/tmp/s4closure_docker_build:/home/noah/ws_moveit/build:ro']
    if args.mode=='health':
        mounts += [str(ROOT/'inputs/official_monitor_generated.py')+':/official_monitor.py:ro']
    image='s4b-rosmonitoring-humble:20260922'
else:
    mounts += [f'{REPO}/semantic_validation/targets/openvr_ur5e_jazzy:/ws_src:ro',
       f'{REPO}/semantic_validation/harness/openvr_ur5e_downstream:/harness:ro',
       '/tmp/s4closure_openvr_install:/ws/install:ro','/tmp/s4closure_openvr_build:/ws/build:ro']
    image='s4b-rosmonitoring-jazzy:20260922'
argv=['run','-d','--name',name,'--network','none','--cap-drop','ALL','--security-opt','no-new-privileges',
      '--entrypoint','sleep','-e','ROS_DOMAIN_ID=181','-e','ROS_LOCALHOST_ONLY=1','-e',f'STACK={args.stack}','-e',f'MODE={args.mode}']
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
