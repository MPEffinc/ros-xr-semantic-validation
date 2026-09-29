#!/usr/bin/env python3
"""Offline analysis of S2 DB3 bags.  It never invokes ROS or Docker."""
import json, math, sqlite3, struct, sys
from pathlib import Path

class CDR:
    def __init__(self,b):
        self.b=memoryview(b); self.base=4; self.p=4
        if bytes(self.b[:4]) not in (b'\x00\x01\x00\x00',b'\x00\x00\x00\x00'): raise ValueError(bytes(self.b[:4]).hex())
        self.end='<' if self.b[1]==1 else '>'
    def align(self,n): self.p+= (-(self.p-self.base))%n
    def u(self,f,n,a=None): self.align(a or n);x=struct.unpack_from(self.end+f,self.b,self.p)[0];self.p+=n;return x
    def i8(self): return self.u('b',1,1)
    def u8(self): return self.u('B',1,1)
    def boolean(self): return bool(self.u8())
    def i32(self): return self.u('i',4)
    def u32(self): return self.u('I',4)
    def f32(self): return self.u('f',4)
    def f64(self): return self.u('d',8)
    def string(self):
        n=self.u32();s=bytes(self.b[self.p:self.p+n]);self.p+=n
        return s[:-1].decode(errors='replace') if n and s[-1]==0 else s.decode(errors='replace')
    def header(self): return {'sec':self.i32(),'nanosec':self.u32(),'frame':self.string()}
    def pose(self): return [self.f64() for _ in range(7)]
    def twist(self): return [self.f64() for _ in range(6)]
    def strings(self): return [self.string() for _ in range(self.u32())]
    def floats(self): return [self.f64() for _ in range(self.u32())]

def received(b):
    c=CDR(b);h=c.header();tracked=c.boolean();pose=c.pose();c.boolean();c.pose();c.f32();c.f32();flags=[c.boolean() for _ in range(8)]
    return {'h':h,'tracked':tracked,'x':pose[0],'teleop':flags[7]}
def target(b):
    c=CDR(b);h=c.header();tw=c.twist();c.i8();flags=[c.boolean() for _ in range(6)]
    return {'h':h,'twist':tw,'tracked':flags[1]}
def twist(b):
    c=CDR(b);return {'h':c.header(),'twist':c.twist()}
def joint(b):
    c=CDR(b);return {'h':c.header(),'name':c.strings(),'position':c.floats(),'velocity':c.floats(),'effort':c.floats()}
def norm(v): return math.sqrt(sum(x*x for x in v))

def mat(a,b): return [[sum(a[i][k]*b[k][j] for k in range(4)) for j in range(4)] for i in range(4)]
def tf(x=0,y=0,z=0,r=0,p=0,w=0):
    cr,sr,cp,sp,cy,sy=math.cos(r),math.sin(r),math.cos(p),math.sin(p),math.cos(w),math.sin(w)
    return [[cy*cp,cy*sp*sr-sy*cr,cy*sp*cr+sy*sr,x],[sy*cp,sy*sp*sr+cy*cr,sy*sp*cr-cy*sr,y],[-sp,cp*sr,cp*cr,z],[0,0,0,1]]
def fk(q):
    chain=[tf(w=math.pi),tf(z=.1625),tf(w=q['shoulder_pan_joint']),tf(r=1.570796327),tf(w=q['shoulder_lift_joint']),tf(x=-.425),tf(w=q['elbow_joint']),tf(x=-.3922,z=.1333),tf(w=q['wrist_1_joint']),tf(y=-.0997,z=-2.044881182297852e-11,r=1.570796327),tf(w=q['wrist_2_joint']),tf(y=.0996,z=-2.042830148012698e-11,r=1.570796326589793,p=math.pi,w=math.pi),tf(w=q['wrist_3_joint']),tf(r=math.pi),tf(p=-math.pi/2,w=-math.pi/2),tf(r=math.pi/2,w=math.pi/2),tf(z=.011),tf(z=.1455)]
    a=tf()
    for b in chain:a=mat(a,b)
    return [a[0][3],a[1][3],a[2][3]]

DEC={'/received_pose_states':received,'/target_twist_states':target,'/servo_node/delta_twist_cmds':twist,'/joint_states':joint}
def load(db):
    con=sqlite3.connect('file:'+str(db)+'?mode=ro',uri=True); topics={i:n for i,n,_ in con.execute('select id,name,type from topics')};rows={n:[] for n in topics.values()}
    for tid,ts,b in con.execute('select topic_id,timestamp,data from messages order by timestamp'):
        n=topics[tid];rows[n].append((ts,DEC[n](b) if n in DEC else None))
    return rows
def runs(rec):
    out=[]
    for ts,x in rec:
        sig=(x['tracked'],round(x['x'],3),x['teleop'])
        if not out or out[-1]['signature']!=sig:out.append({'start_ns':ts,'end_ns':ts,'n':1,'signature':sig})
        else:out[-1]['end_ns']=ts;out[-1]['n']+=1
    return out
def js_stats(js):
    if not js:return None
    names=js[0]['name'];p0=js[0]['position'];p1=js[-1]['position'];delta=[b-a for a,b in zip(p0,p1)]
    arm=['shoulder_pan_joint','shoulder_lift_joint','elbow_joint','wrist_1_joint','wrist_2_joint','wrist_3_joint']; idx=[names.index(n) for n in arm if n in names]
    guarded=js[min(6,len(js)-1):]
    velocities=[abs(row['velocity'][i]) for row in guarded for i in idx if len(row['velocity'])>i]
    q0=dict(zip(names,p0));q1=dict(zip(names,p1));e0=fk(q0);e1=fk(q1);ed=[b-a for a,b in zip(e0,e1)]
    return {'samples':len(js),'first_header_stamp':js[0]['h'],'last_header_stamp':js[-1]['h'],'max_abs_joint_delta_rad':max(map(abs,delta),default=0.0),'max_abs_arm_velocity_rad_s':max([abs(row['velocity'][i]) for row in js for i in idx if len(row['velocity'])>i],default=0.0),'guarded_after_six_samples_max_abs_arm_velocity_rad_s':max(velocities,default=0.0),'joint_delta_rad':dict(zip(names,delta)),'hande_end_delta_m':ed,'hande_end_displacement_m':norm(ed)}
def section(rows,label,a,b,sig):
    def cut(topic,pad=0):return [x for t,x in rows.get(topic,[]) if a-pad<=t<=b+pad]
    r=cut('/received_pose_states');t=cut('/target_twist_states');s=cut('/servo_node/delta_twist_cmds');j=cut('/joint_states')
    return {'label':label,'signature':sig,'bag_storage_start_ns':a,'bag_storage_end_ns':b,'duration_s':(b-a)/1e9,'receiver_count':len(r),'receiver_header_stamp_distinct':len({(x['h']['sec'],x['h']['nanosec']) for x in r}),'target_count':len(t),'target_nonzero_count':sum(norm(x['twist'])>1e-12 for x in t),'target_max_twist_norm':max([norm(x['twist']) for x in t],default=0.0),'servo_count':len(s),'servo_nonzero_count':sum(norm(x['twist'])>1e-12 for x in s),'servo_max_twist_norm':max([norm(x['twist']) for x in s],default=0.0),'joint':js_stats(j)}
def label_sequence(name,rr):
    sigs=[x['signature'] for x in rr]
    if name=='primary':
        wanted=[('D1_REFERENCE',(True,.1,True)),('D1_ACTIVE',(True,.35,True)),('D2_TRACKING_FALSE',(False,.35,True)),('D3_STALL_NEUTRAL',(False,.0,False)),('D4_FRESH_REFERENCE',(True,.12,True)),('D4_FRESH_ACTIVE',(True,.37,True)),('D4_OLD_REFERENCE',(True,.16,True)),('D4_OLD_ACTIVE',(True,.41,True)),('D5_RECONNECT_REFERENCE',(True,.24,True)),('D5_RECONNECT_ACTIVE',(True,.5,True))]
    elif name=='d4':
        wanted=[('D4_OLD_REFERENCE',(True,.2,True)),('D4_OLD_ACTIVE',(True,.35,True)),('D4_RESET_NEUTRAL',(False,.0,False)),('D4_FRESH_REFERENCE',(True,.5,True)),('D4_FRESH_ACTIVE',(True,.35,True))]
    else:
        wanted=[('D5_FIRST_REFERENCE',(True,.2,True)),('D5_FIRST_ACTIVE',(True,.35,True)),('D5_DISCONNECTED_NEUTRAL',(False,.0,False)),('D5_RECONNECT_REFERENCE',(True,.5,True)),('D5_RECONNECT_ACTIVE',(True,.35,True))]
    next_index=0;out=[]
    for label,sig in wanted:
        for i in range(next_index,len(rr)):
            if rr[i]['signature']==sig:
                out.append((label,rr[i]));next_index=i+1;break
    return out
def analyze(name,path):
    rows=load(path);rr=runs(rows['/received_pose_states']);sections=[section(rows,label,x['start_ns'],x['end_ns'],x['signature']) for label,x in label_sequence(name,rr)]
    first_active=next((x['start_ns'] for x in rr if x['signature'][0] and x['signature'][2]),None)
    idle=None
    if first_active:
        a=min(t for t,x in rows['/joint_states']);idle=section(rows,'PRE_FIRST_TRACKED_IDLE',a,first_active,(False,0.0,False))
    return {'bag':str(path),'metadata_present':path.with_name('metadata.yaml').exists(),'topic_counts':{k:len(v) for k,v in rows.items()},'receiver_runs':rr,'pre_first_tracked_idle':idle,'sections':sections,'clock_note':'Phases are selected by receiver values and bag storage ordering. Input sender wall/monotonic stamps are retained separately and are not used here to compute latency or directly join clocks.'}
def main():
    root=Path(sys.argv[1]);out=Path(sys.argv[2]);result={'primary':analyze('primary',root/'bags/s2_docker_bag/s2_docker_bag_0.db3'),'d4_timestamp_pair':analyze('d4',root/'runtime_d4/bags/d4_timestamp_pair/d4_timestamp_pair_0.db3'),'d5_reconnect':analyze('d5',root/'runtime_d5/bags/d5_reconnect/d5_reconnect_0.db3')}
    out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
if __name__=='__main__':main()
