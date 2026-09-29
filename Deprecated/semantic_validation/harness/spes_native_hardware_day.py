#!/usr/bin/env python3
"""Start/status/collect/stop the Quest hardware workflow with upstream ROS publisher."""
from __future__ import annotations
import argparse,json,os,re,shlex,subprocess,time
from datetime import datetime,timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]; DEFAULT_STATE=Path('/tmp/spes_native_hardware_day_state')
def run(cmd,**kw): return subprocess.run(cmd,text=True,capture_output=True,**kw)
def remote(host,script): return run(['ssh','-o','BatchMode=yes',host,'bash','-lc',shlex.quote(script)])
def load(state): return json.loads((state/'state.json').read_text())
def docker(args): return run(['sg','docker','-c',' '.join(shlex.quote(x) for x in ['docker',*args])])
def start(a):
    if not re.fullmatch(r'[A-Za-z0-9_.-]+',a.run_id): raise SystemExit('invalid run id')
    out=ROOT/'semantic_validation/results/runs'/a.run_id
    if out.exists(): raise SystemExit(f'refusing to overwrite {out}')
    if (a.state_dir/'state.json').exists(): raise SystemExit(f'active state already exists: {a.state_dir}')
    out.mkdir(parents=True); a.state_dir.mkdir(parents=True,exist_ok=True)
    pi_dir=f'/home/cclab/spes_logs/{a.run_id}'
    sink_executable='/home/cclab/ros2_ws/install/semantic_robot_endpoint/lib/semantic_robot_endpoint/semantic_robot_sink'
    script=f'''set -e
test ! -e {shlex.quote(pi_dir)}
mkdir -p {shlex.quote(pi_dir)}
test -x {shlex.quote(sink_executable)}
nohup bash -lc {shlex.quote('source /opt/ros/humble/setup.bash; source ~/ros2_ws/install/setup.bash; export ROS_DOMAIN_ID='+a.domain+'; export RMW_IMPLEMENTATION=rmw_fastrtps_cpp; export ROS_LOCALHOST_ONLY=0; exec '+sink_executable+' --ros-args -p pose_topic:=/robot_target_pose -p log_dir:='+pi_dir+' -p tf_topic:=/tf_unused')} > {shlex.quote(pi_dir+'/console.log')} 2>&1 </dev/null &
echo $! > {shlex.quote(pi_dir+'/sink.pid')}
sleep 1
kill -0 $(cat {shlex.quote(pi_dir+'/sink.pid')})'''
    rr=remote(a.pi_host,script)
    if rr.returncode: raise SystemExit('Pi sink start failed: '+rr.stderr)
    name='spes-native-'+re.sub('[^a-zA-Z0-9_.-]','-',a.run_id).lower()
    cmd=['run','-d','--rm','--name',name,'--network','host','--cap-drop','ALL','--security-opt','no-new-privileges',
         '--user',f'{os.getuid()}:{os.getgid()}','-e',f'RUN_ID={a.run_id}','-e',f'PRODUCTION_PORT={a.production_port}',
         '-e',f'SIDEBAND_PORT={a.sideband_port}','-e',f'ROS_DOMAIN_ID={a.domain}','-e','RMW_IMPLEMENTATION=rmw_fastrtps_cpp','-e','ROS_LOCALHOST_ONLY=0',
         '-v',f'{ROOT}:/repo:ro','-v',f'{out}:/out',a.image,'bash','/repo/semantic_validation/harness/spes_native_hardware_container.sh']
    dr=docker(cmd)
    if dr.returncode:
        remote(a.pi_host,f'kill -TERM $(cat {shlex.quote(pi_dir+"/sink.pid")}) 2>/dev/null || true')
        raise SystemExit('container start failed: '+dr.stderr)
    state={'run_id':a.run_id,'run_dir':str(out),'container':name,'pi_host':a.pi_host,'pi_dir':pi_dir,'production_port':a.production_port,
           'sideband_port':a.sideband_port,'domain':a.domain,'target_commit':run(['git','-C',str(ROOT/'semantic_validation/targets/spes_teleop'),'rev-parse','HEAD']).stdout.strip(),
           'started_utc':datetime.now(timezone.utc).isoformat(),'quest_hardware_used':False,'robot_or_driver_used':False}
    (a.state_dir/'state.json').write_text(json.dumps(state,indent=2)+'\n')
    for _ in range(100):
        p=run(['curl','-sk','--max-time','1',f'https://127.0.0.1:{a.production_port}/']); s=run(['curl','-sk','--max-time','1',f'https://127.0.0.1:{a.sideband_port}/health'])
        if p.returncode==s.returncode==0: break
        time.sleep(.1)
    else: raise SystemExit('services failed readiness')
    print(json.dumps({**state,'status':'RUNNING','quest_url':f'https://HOST:{a.production_port}/','sideband_url':f'wss://HOST:{a.sideband_port}/experiment'},indent=2)); return 0
def status(a):
    s=load(a.state_dir); d=docker(['inspect','-f','{{.State.Running}}',s['container']]); rr=remote(s['pi_host'],f'''p=$(cat {shlex.quote(s['pi_dir']+'/sink.pid')}); kill -0 "$p"; tr '\\0' ' ' </proc/$p/cmdline | grep -q semantic_robot_sink''')
    result={'run_id':s['run_id'],'container_running':d.stdout.strip()=='true','pi_sink_running':rr.returncode==0}
    result['status']='RUNNING' if all((result['container_running'],result['pi_sink_running'])) else 'INCOMPLETE'; print(json.dumps(result)); return 0 if result['status']=='RUNNING' else 1
def stop(a):
    s=load(a.state_dir); docker(['stop','--time','10',s['container']]); rr=remote(s['pi_host'],f'''p=$(cat {shlex.quote(s['pi_dir']+'/sink.pid')}); tr '\\0' ' ' </proc/$p/cmdline | grep -q semantic_robot_sink; kill -TERM "$p"; for i in $(seq 1 100); do kill -0 "$p" 2>/dev/null || exit 0; sleep .1; done; exit 3''')
    if rr.returncode: raise SystemExit('Pi clean stop failed: '+rr.stderr)
    (a.state_dir/'stopped').write_text(datetime.now(timezone.utc).isoformat()+'\n'); print(json.dumps({'run_id':s['run_id'],'status':'STOPPED'})); return 0
def collect(a):
    s=load(a.state_dir); out=Path(s['run_dir']); dest=out/'pi_sink.jsonl'
    if dest.exists(): raise SystemExit(f'refusing to overwrite {dest}')
    rr=remote(s['pi_host'],f'cat {shlex.quote(s["pi_dir"])}/*.jsonl');
    if rr.returncode: raise SystemExit('Pi collect failed: '+rr.stderr)
    dest.write_text(rr.stdout); ros=[json.loads(x) for x in (out/'native_ros_observer.jsonl').read_text().splitlines() if x]; pi=[json.loads(x) for x in rr.stdout.splitlines() if x]
    by={(x['header_stamp']['sec'],x['header_stamp']['nanosec']):x for x in pi}; matched=sum((x['header_stamp']['sec'],x['header_stamp']['nanosec']) in by for x in ros)
    summary={'run_id':s['run_id'],'target_commit':s['target_commit'],'native_ros_observed':len(ros),'pi_received':len(pi),'stamp_matched':matched,'result':'PASS' if len(ros)==len(pi)==matched and len(ros)>0 else 'FAIL','evidence':'E2_BOUNDARY_LIMITED_REPLAY','consequence':'PI_RECEIVED','quest_hardware_used':False,'robot_or_driver_used':False}
    (out/'hardware_day_summary.json').write_text(json.dumps(summary,indent=2)+'\n'); print(json.dumps(summary,indent=2)); return 0 if summary['result']=='PASS' else 1
def main():
    p=argparse.ArgumentParser(); p.add_argument('action',choices=['start','status','stop','collect']); p.add_argument('--run-id'); p.add_argument('--state-dir',type=Path,default=DEFAULT_STATE); p.add_argument('--pi-host',default='rosxr'); p.add_argument('--image',default='ros-xr-humble:local'); p.add_argument('--production-port',type=int,default=4443); p.add_argument('--sideband-port',type=int,default=4444); p.add_argument('--domain',default='74'); a=p.parse_args()
    if a.action=='start' and not a.run_id: p.error('--run-id required for start')
    return {'start':start,'status':status,'stop':stop,'collect':collect}[a.action](a)
if __name__=='__main__': raise SystemExit(main())
