#!/usr/bin/env python3
import json, math, sqlite3, struct, sys
from pathlib import Path

class CDR:
    def __init__(self, b):
        self.b=memoryview(b); self.base=4; self.p=4
        if bytes(self.b[:4]) not in (b'\x00\x01\x00\x00',b'\x00\x00\x00\x00'):
            raise ValueError(bytes(self.b[:4]).hex())
        self.end = '<' if self.b[1] == 1 else '>'
    def align(self,n): self.p += (-(self.p-self.base)) % n
    def unpack(self,fmt,n,align=None):
        self.align(align or n); x=struct.unpack_from(self.end+fmt,self.b,self.p)[0]; self.p+=n; return x
    def i8(self): return self.unpack('b',1,1)
    def u8(self): return self.unpack('B',1,1)
    def boolean(self): return bool(self.u8())
    def i32(self): return self.unpack('i',4)
    def u32(self): return self.unpack('I',4)
    def f32(self): return self.unpack('f',4)
    def f64(self): return self.unpack('d',8)
    def string(self):
        n=self.u32(); s=bytes(self.b[self.p:self.p+n]); self.p+=n
        return s[:-1].decode(errors='replace') if n and s[-1]==0 else s.decode(errors='replace')
    def header(self): return {'sec':self.i32(),'nanosec':self.u32(),'frame':self.string()}
    def pose(self): return [self.f64() for _ in range(7)]
    def twist(self): return [self.f64() for _ in range(6)]
    def string_array(self): return [self.string() for _ in range(self.u32())]
    def f64_array(self): return [self.f64() for _ in range(self.u32())]

def received(b):
    c=CDR(b); h=c.header(); tracked=c.boolean(); pose=c.pose(); workspace_valid=c.boolean(); workspace_pose=c.pose()
    grip=c.f32(); trigger=c.f32()
    flags=[c.boolean() for _ in range(8)]
    source=c.string(); control_mode=c.string(); attachment=c.boolean(); mapping=c.string(); adjustment=c.boolean(); offset_valid=c.boolean(); offset=c.pose(); mode_switch=c.boolean()
    sticks=[c.f32() for _ in range(6)]
    return {'h':h,'tracked':tracked,'x':pose[0],'y':pose[1],'z':pose[2], 'grip':grip,'teleop':flags[7], 'source':source,'control_mode':control_mode}

def target(b):
    c=CDR(b); h=c.header(); tw=c.twist(); gripper=c.i8(); flags=[c.boolean() for _ in range(6)]
    return {'h':h,'twist':tw,'gripper':gripper,'tracked':flags[1]}

def twist_stamped(b):
    c=CDR(b); return {'h':c.header(),'twist':c.twist()}

def joint(b):
    c=CDR(b); return {'h':c.header(),'name':c.string_array(),'position':c.f64_array(),'velocity':c.f64_array(),'effort':c.f64_array()}

def intervals(rows,key):
    out=[]
    for ts,x in rows:
        v=key(x)
        if not out or out[-1][2] != v: out.append([ts,ts,v,1])
        else: out[-1][1]=ts; out[-1][3]+=1
    return out

def stats(xs):
    if not xs: return None
    return {'n':len(xs),'min':min(xs),'max':max(xs),'mean':sum(xs)/len(xs),'rms':math.sqrt(sum(x*x for x in xs)/len(xs))}

def mm(a,b):
    return [[sum(a[i][k]*b[k][j] for k in range(4)) for j in range(4)] for i in range(4)]

def tf(x=0,y=0,z=0,r=0,p=0,w=0):
    cr,sr,cp,sp,cy,sy=math.cos(r),math.sin(r),math.cos(p),math.sin(p),math.cos(w),math.sin(w)
    return [[cy*cp,cy*sp*sr-sy*cr,cy*sp*cr+sy*sr,x],
            [sy*cp,sy*sp*sr+cy*cr,sy*sp*cr-cy*sr,y],
            [-sp,cp*sr,cp*cr,z],[0,0,0,1]]

def fk(q, hande_end=True):
    """FK from the pinned generated UnityApp ur5e.urdf (same calibrated arm geometry)."""
    chain=[tf(w=math.pi),tf(z=.1625),tf(w=q['shoulder_pan_joint']),
           tf(r=1.570796327),tf(w=q['shoulder_lift_joint']),
           tf(x=-.425),tf(w=q['elbow_joint']),
           tf(x=-.3922,z=.1333),tf(w=q['wrist_1_joint']),
           tf(y=-.0997,z=-2.044881182297852e-11,r=1.570796327),tf(w=q['wrist_2_joint']),
           tf(y=.0996,z=-2.042830148012698e-11,r=1.570796326589793,p=math.pi,w=math.pi),tf(w=q['wrist_3_joint']),
           tf(r=math.pi),tf(p=-math.pi/2,w=-math.pi/2),tf(r=math.pi/2,w=math.pi/2)]
    if hande_end: chain += [tf(z=.011),tf(z=.1455)]
    a=tf()
    for b in chain: a=mm(a,b)
    return [a[0][3],a[1][3],a[2][3]]

def main():
    db=Path(sys.argv[1]); out=Path(sys.argv[2])
    con=sqlite3.connect('file:'+str(db)+'?mode=ro',uri=True)
    topics={i:(n,t) for i,n,t in con.execute('select id,name,type from topics')}
    dec={'/joint_states':joint,'/received_pose_states':received,'/target_twist_states':target,'/servo_node/delta_twist_cmds':twist_stamped}
    rows={n:[] for _,(n,_) in topics.items()}
    for tid,ts,data in con.execute('select topic_id,timestamp,data from messages order by timestamp'):
        n,_=topics[tid]; rows[n].append((ts,dec[n](data)))
    t0=min(v[0][0] for v in rows.values() if v)
    def rel(ts): return (ts-t0)/1e9
    rec_runs=intervals(rows['/received_pose_states'],lambda x:(x['tracked'],round(x['x'],3),x['teleop']))
    tar_runs=intervals(rows['/target_twist_states'],lambda x:(x['tracked'],round(math.sqrt(sum(q*q for q in x['twist'])),6)))
    srv_runs=intervals(rows['/servo_node/delta_twist_cmds'],lambda x:round(math.sqrt(sum(q*q for q in x['twist'])),6))
    phase_windows=[]
    for a,b,v,n in rec_runs:
        tracked,x,teleop=v; phase='OTHER'
        if tracked and abs(x-.1)<.01: phase='D1_REFERENCE'
        elif tracked and abs(x-.35)<.01: phase='D1_ACTIVE'
        elif not tracked and abs(x-.35)<.01: phase='D2_TRACKED_FALSE'
        elif not tracked and abs(x)<.01 and not teleop: phase='NEUTRAL'
        elif tracked and abs(x-.45)<.01: phase='D4_OLD_SOURCE_TIME'
        elif tracked and abs(x-.55)<.01: phase='D5_SECOND_CLIENT'
        phase_windows.append({'phase':phase,'start':rel(a),'end':rel(b),'n':n,'signature':v})
    merged=[]
    for w in phase_windows:
        if merged and merged[-1]['phase']==w['phase'] and w['start']-merged[-1]['end']<.08:
            merged[-1]['end']=w['end']; merged[-1]['n']+=w['n']
        else: merged.append(w.copy())
    phase_stats={}
    neutral_index=0
    for w in merged:
        if w['phase']=='NEUTRAL':
            w['phase']=['PRE_TRIAL_NEUTRAL','D3_STALL_NEUTRAL','D4_TO_D5_NEUTRAL','POST_D5_NEUTRAL'][min(neutral_index,3)]
            neutral_index += 1
    for w in merged:
        if w['phase']=='OTHER': continue
        js=[x for ts,x in rows['/joint_states'] if w['start'] <= rel(ts) <= w['end']+.03]
        if not js: phase_stats.setdefault(w['phase'],[]).append({'window':w,'joint':None}); continue
        names=js[0]['name']; p0=js[0]['position']; p1=js[-1]['position']; delta=[b-a for a,b in zip(p0,p1)]
        vel={name:stats([z['velocity'][i] for z in js if len(z['velocity'])>i]) for i,name in enumerate(names)}
        arm_names=['shoulder_pan_joint','shoulder_lift_joint','elbow_joint','wrist_1_joint','wrist_2_joint','wrist_3_joint']
        q0=dict(zip(names,p0)); q1=dict(zip(names,p1)); ee0=fk(q0); ee1=fk(q1); eed=[b-a for a,b in zip(ee0,ee1)]
        guarded=js[min(6,len(js)-1):]
        guarded_arm_vel=[abs(z['velocity'][names.index(name)]) for z in guarded for name in arm_names]
        phase_stats.setdefault(w['phase'],[]).append({'window':w,'joint':{'samples':len(js),'first_ros_stamp':js[0]['h'],'last_ros_stamp':js[-1]['h'],'names':names,'position_before':p0,'position_after':p1,'delta':delta,'velocity':vel,'max_abs_delta':max(map(abs,delta),default=0.0),'guarded_after_six_samples_arm_max_abs_velocity':max(guarded_arm_vel,default=0.0),'hande_end_before':ee0,'hande_end_after':ee1,'hande_end_delta':eed,'hande_end_displacement':math.sqrt(sum(x*x for x in eed))}})
    result={'db':str(db),'bag_t0_ns':t0,'topic_counts':{k:len(v) for k,v in rows.items()},'receiver_intervals':merged,'target_intervals':[{'start':rel(a),'end':rel(b),'value':v,'n':n} for a,b,v,n in tar_runs], 'servo_intervals':[{'start':rel(a),'end':rel(b),'value':v,'n':n} for a,b,v,n in srv_runs], 'phase_joint_stats':phase_stats}
    out.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))

if __name__=='__main__': main()
