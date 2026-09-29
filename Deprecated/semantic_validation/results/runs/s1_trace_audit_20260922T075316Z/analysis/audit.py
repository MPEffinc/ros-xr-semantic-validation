#!/usr/bin/env python3
"""Read-only S1 audit of committed raw files; no ROS/Docker/runtime API use."""
import datetime as dt, hashlib, json, math, re, sqlite3, struct
from collections import Counter
from pathlib import Path

ROOT=Path(__file__).resolve().parents[5]
R=ROOT/'semantic_validation/results/runs'

def jl(p): return [json.loads(x) for x in Path(p).read_text().splitlines() if x.strip()]
class C:
 def __init__(s,b):
  s.b=memoryview(b);s.p=4;s.base=4;s.e='<' if b[1]==1 else '>'
 def a(s,n):s.p+=(-(s.p-s.base))%n
 def u(s,f,n,a=None):s.a(a or n);v=struct.unpack_from(s.e+f,s.b,s.p)[0];s.p+=n;return v
 def i32(s):return s.u('i',4)
 def u32(s):return s.u('I',4)
 def f64(s):return s.u('d',8)
 def f32(s):return s.u('f',4)
 def b1(s):return bool(s.u('B',1,1))
 def st(s):
  n=s.u32();v=bytes(s.b[s.p:s.p+n]);s.p+=n;return v[:-1].decode(errors='replace') if v[-1:]==b'\0' else v.decode(errors='replace')
 def h(s):return (s.i32(),s.u32(),s.st())
 def pose(s):return [s.f64() for _ in range(7)]
 def twist(s):return [s.f64() for _ in range(6)]
 def arrstr(s):return [s.st() for _ in range(s.u32())]
 def arrf(s):return [s.f64() for _ in range(s.u32())]
def dec_received(b):
 c=C(b);h=c.h();tracked=c.b1();p=c.pose();c.b1();c.pose();grip=c.f32();c.f32();fl=[c.b1() for _ in range(8)]
 return {'h':h,'tracked':tracked,'x':p[0],'teleop':fl[7]}
def dec_target(b):
 c=C(b);h=c.h();tw=c.twist();c.u('b',1,1);fl=[c.b1() for _ in range(6)]
 return {'h':h,'twist':tw,'tracked':fl[1]}
def dec_tw(b):c=C(b);return {'h':c.h(),'twist':c.twist()}
def dec_joint(b):
 c=C(b);return {'h':c.h(),'name':c.arrstr(),'position':c.arrf(),'velocity':c.arrf(),'effort':c.arrf()}
def dec_pose(b):
 c=C(b);h=c.h();return {'h':h,'pose':c.pose()}
def bag(p, decoders):
 con=sqlite3.connect('file:'+str(p)+'?mode=ro',uri=True); topics=dict(con.execute('select id,name from topics'))
 out={n:[] for n in topics.values()}
 for tid,t,b in con.execute('select topic_id,timestamp,data from messages order by timestamp'):
  n=topics[tid];out[n].append((t,decoders[n](b) if n in decoders else None))
 return out
def nsiso(x):return int(dt.datetime.fromisoformat(x.replace('Z','+00:00')).timestamp()*1e9)
def norms(xs):return [math.sqrt(sum(v*v for v in x)) for x in xs]
def p_picknik():
 sb=jl(R/'hw_picknik_native_20260917T074600Z/sideband_final.jsonl');ros=jl(R/'hw_picknik_native_20260917T074600Z/ros_observer.jsonl');tr=[]
 for side in ('left','right'):
  a=sorted([x for x in sb if x.get('event_type')=='raw_sample' and x.get('side')==side],key=lambda x:(x['wall_unix_ms'],x.get('unity_frame',0)))
  seen=False;cur=None
  for x in a:
   valid=x.get('input_present') and x.get('game_object_present') and x.get('is_tracked') and (int(x.get('tracking_state',0))&3)==3
   if valid:
    if cur: cur['recovery']=x;tr.append(cur);cur=None
    seen=True
   elif seen:
    if cur is None:cur={'side':side,'samples':[]}
    cur['samples'].append(x)
  if cur:cur['recovery']=None;tr.append(cur)
 out=[]
 for z in tr:
  ss=z['samples'];a=int(ss[0]['wall_unix_ms'])*1000000;b=int(ss[-1]['wall_unix_ms'])*1000000; side=z['side'];rr=[x for x in ros if (x.get('child_frame_id')==side+'_controller_odom' or x.get('topic')=='/'+side+'_controller_odom') and a<=int(x.get('ros_stamp_ns',-1))<=b]
  od=[x for x in rr if x.get('event_type')=='ros_receive_odometry'];tf=[x for x in rr if x.get('event_type')=='ros_receive_tf'];st=sorted({int(x['ros_stamp_ns']) for x in rr});trans={tuple(x.get('position',[]))+tuple(x.get('orientation',[])) for x in rr}
  inval=any(not x.get('application_focused',True) or x.get('application_paused',False) or not x.get('xr_display_running',True) for x in ss)
  cls='INVALID_FOCUS_OR_XR_SESSION' if inval else ('HW_PICKNIK_UNTRACKED_ROS_CONTINUES' if len(od)>=2 and len(tf)>=2 and len(st)>=2 else 'HW_PICKNIK_NO_DOWNSTREAM_DURING_LOSS' if not od and not tf else 'HW_PICKNIK_PARTIAL_DOWNSTREAM_OBSERVATION')
  out.append({'side':side,'start_ns':a,'end_ns':b,'duration_s':(b-a)/1e9,'reacquired':bool(z['recovery']),'focus_pause_xr_interruption':inval,'odom':len(od),'tf':len(tf),'stamp_progression_ns':st[-1]-st[0] if len(st)>1 else 0,'distinct_transform':len(trans),'classification':cls})
 return {'raw_sideband_records':len(sb),'raw_ros_records':len(ros),'intervals':out,'counts':Counter(x['classification'] for x in out)}
def p_spes():
 sb=jl(R/'hw_spes_native_20260917T081300Z/experiment_sideband.jsonl');ro=jl(R/'hw_spes_native_20260917T081300Z/native_ros_observer.jsonl');pi=jl(R/'hw_spes_native_20260917T081300Z/pi_sink.jsonl')
 # headers are named header_stamp_ns in current sink logs; discover exact field conservatively
 def stamp(x):
  h=x.get('header_stamp');return int(h['sec'])*1000000000+int(h['nanosec']) if isinstance(h,dict) and 'sec' in h else None
 rs=[stamp(x) for x in ro if stamp(x) is not None]; ps=[stamp(x) for x in pi if stamp(x) is not None]
 return {'sideband_total':len(sb),'selected_controller':sum(x.get('selected_source')=='CONTROLLER' for x in sb),'emulated_true':sum(x.get('controller_emulated_position') is True for x in sb),'hw_emulated_continues':sum(x.get('classification')=='HW_EMULATED_CONTINUES' for x in sb),'ros_records':len(ro),'ros_stamp_field':'header_stamp.sec/nanosec','ros_unique_stamps':len(set(rs)),'pi_records':len(pi),'pi_stamp_field':'header_stamp.sec/nanosec','pi_contains_ros_unique':len(set(rs)&set(ps)),'pi_extra_records':len(pi)-len(set(rs)&set(ps)),'causal_one_to_one':'UNKNOWN: no shared per-message source event identifier or clock-join field was found'}
def q2(name):
 db=R/(f'hw_quest2ros2_{name}_20260917T0'+('93000Z' if name=='cdr' else '94000Z'))/'bag/bag_0.db3'
 rows=bag(db,{})
 # decode target only after identifying it
 target=[n for n in rows if 'target_frame' in n]
 if target:
  rows=bag(db,{target[0]:dec_pose})
 poses=[n for n in rows if 'right_hand_pose' in n];inputs=[n for n in rows if 'right_hand_inputs' in n]
 gaps=[]
 if poses:
  ts=[x[0] for x in rows[poses[0]]];gaps=[(b-a)/1e9 for a,b in zip(ts,ts[1:]) if b-a>500_000_000]
 vals=[x[1]['pose'][:3] for x in rows[target[0]] if x[1]] if target else []
 return {'topics':{k:len(v) for k,v in rows.items()},'right_pose_count':sum(len(rows[x]) for x in poses),'right_input_count':sum(len(rows[x]) for x in inputs),'target_count':sum(len(rows[x]) for x in target),'distinct_target_positions':len({tuple(round(y,9) for y in x) for x in vals}),'pose_gaps_s':gaps,'raw_tracking_state_present':False,'phase_marker_present':False}
def docker(p):
 rows=bag(p,{'/received_pose_states':dec_received,'/target_twist_states':dec_target,'/servo_node/delta_twist_cmds':dec_tw,'/joint_states':dec_joint})
 rec=rows['/received_pose_states'];tar=rows['/target_twist_states'];srv=rows['/servo_node/delta_twist_cmds'];js=rows['/joint_states']
 sig=Counter((x['tracked'],round(x['x'],2),x['teleop']) for _,x in rec); nonzero=sum(any(abs(q)>1e-12 for q in x['twist']) for _,x in srv)
 return {'topic_counts':{k:len(v) for k,v in rows.items()},'receiver_signatures':{str(k):v for k,v in sig.items()},'target_nonzero':sum(any(abs(q)>1e-12 for q in x['twist']) for _,x in tar),'servo_nonzero':nonzero,'joint_samples':len(js)}
def docker_actual():
 p=R/'hw_docker_native_20260917T071824Z/hw_dt_t02/bag/bag_0.db3'; rows=bag(p,{'/received_pose_states':dec_received,'/target_twist_states':dec_target,'/servo_node/delta_twist_cmds':dec_tw,'/joint_states':dec_joint})
 a=nsiso('2026-09-17T07:33:35.417Z');b=nsiso('2026-09-17T07:33:40.414Z')
 def sel(v):
  return [x for x in v if x[1] and a<=int(x[1]['h'][0])*1000000000+int(x[1]['h'][1])<=b]
 rec=sel(rows['/received_pose_states']);srv=sel(rows['/servo_node/delta_twist_cmds']);j=[x for x in rows['/joint_states'] if a<=x[0]<=b]
 log=(R/'hw_docker_native_20260917T071824Z/quest_system_tracking_t02.log').read_text(errors='replace'); events=re.findall(r'09-17 16:33:(\d\d\.\d+) .*?tracking: (POSITION|ORIENTATION)',log)
 hs=[int(x['h'][0])*1000000000+int(x['h'][1]) for _,x in rows['/received_pose_states']]
 bs=[t for t,_ in rows['/received_pose_states']]
 base=j[0][1]['position'] if j else []; joint_delta=max([abs(v-base[i]) for _,x in j for i,v in enumerate(x['position'])] or [0])
 return {'all':docker(p),'received_header_ns_range':[min(hs),max(hs)],'received_bag_ns_range':[min(bs),max(bs)],'window':{'received':len(rec),'tracked_true':sum(x['tracked'] for _,x in rec),'teleop_true':sum(x['teleop'] for _,x in rec),'servo':len(srv),'servo_nonzero':sum(any(abs(q)>1e-12 for q in x['twist']) for _,x in srv),'joint':len(j),'max_abs_delta_from_first_joint_sample':joint_delta},'system_log_16_33_events':events,'app_tracking_field_in_window':'tracked true for every decoded received message; this is not a system/OpenXR semantic equivalence'}
def openvr():
 root=R/'openvr_ur5e_downstream_20260914T065659Z';o={}
 for p in sorted(root.glob('W*_downstream.json')):
  x=json.loads(p.read_text());j=x['joint_states'];base=dict(zip(j[0]['name'],j[0]['position'])) if j else {};exc=max([abs(v-base[n]) for z in j for n,v in zip(z['name'],z['position']) if n in base] or [0]);vel=max([abs(v) for z in j for v in z.get('velocity',[])] or [0]);po=x['pose_target_cmds'];tr=x['arm_controller_joint_trajectory'];o[p.stem.split('_')[0]]={'ros_poses':len(po),'servo_trajectory':len(tr),'joint_samples':len(j),'max_excursion':exc,'max_velocity':vel,'first_last_pose':([po[0],po[-1]] if po else None)}
 return o
out={'picknik':p_picknik(),'spes':p_spes(),'quest2ros2_cdr':q2('cdr'),'quest2ros2_visibility':q2('visibility'),'docker_synthetic':docker(R/'docker_teleop_e2e_20260914/bag/docker_teleop_e2e_bag_0.db3'),'docker_actual':docker_actual(),'openvr':openvr()}
print(json.dumps(out,indent=2,default=lambda x:dict(x)))
