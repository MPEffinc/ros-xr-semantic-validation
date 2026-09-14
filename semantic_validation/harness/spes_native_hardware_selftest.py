#!/usr/bin/env python3
"""Quest-free wire self-test for an already-started native hardware-day workflow."""
import argparse,json,ssl,time
from pathlib import Path
from websocket import create_connection

def main():
    p=argparse.ArgumentParser(); p.add_argument('--run-id',required=True); p.add_argument('--production-port',type=int,required=True); p.add_argument('--sideband-port',type=int,required=True); p.add_argument('--output',type=Path,required=True); p.add_argument('--count',type=int,default=10); a=p.parse_args()
    if a.output.exists(): raise SystemExit(f'refusing to overwrite {a.output}')
    opts={'cert_reqs':ssl.CERT_NONE,'check_hostname':False}
    side=create_connection(f'wss://127.0.0.1:{a.sideband_port}/experiment',timeout=5,sslopt=opts)
    hello=json.loads(side.recv());
    if hello.get('run_id')!=a.run_id: raise RuntimeError(f'run id mismatch: {hello}')
    prod=create_connection(f'wss://127.0.0.1:{a.production_port}/ws',timeout=5,sslopt=opts)
    records=[]
    try:
        for i in range(1,a.count+1):
            trial_id=f'{a.run_id}:SELFTEST:{i:03d}'
            side.send(json.dumps({'type':'experiment_event','data':{'schema':'spes-quest-operator-v1','event_type':'selftest_packet','test':'SELFTEST','trial':i,'trial_id':trial_id,'control_packet_index':i}}))
            packet={'position':{'x':0.0,'y':round((i-1)*.02,9),'z':0.0},'orientation':{'x':0.0,'y':0.0,'z':0.0,'w':1.0},'move':True,'gripper':'open','scale':1.0,'device':'VR','message':'QUEST_FREE_HARDWARE_DAY_SELFTEST'}
            prod.send(json.dumps({'type':'pose','data':packet}))
            deadline=time.monotonic()+3; ack=None
            while time.monotonic()<deadline:
                msg=json.loads(side.recv())
                if msg.get('type')=='server_ack' and msg.get('server_update_index',0)>=i: ack=msg; break
            if ack is None: raise RuntimeError(f'no native ROS ack for {trial_id}')
            records.append({'run_id':a.run_id,'trial_id':trial_id,'control_packet_index':i,'native_ros_ack_index':ack['server_update_index'],'ros_header_stamp':ack['ros_header_stamp']})
            time.sleep(.08)
    finally: prod.close(); side.close()
    result={'run_id':a.run_id,'result':'PASS','count':len(records),'trials':records,'quest_hardware_used':False,'robot_or_driver_used':False}
    a.output.write_text(json.dumps(result,indent=2)+'\n'); print(json.dumps({'run_id':a.run_id,'result':'PASS','count':len(records)})); return 0
if __name__=='__main__': raise SystemExit(main())
