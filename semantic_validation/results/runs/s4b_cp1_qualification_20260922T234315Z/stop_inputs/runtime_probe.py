"""ROS recorder/readiness barrier and externally scripted stop qualification."""
import json
import os
import socket
import time
from pathlib import Path
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from rosidl_runtime_py.convert import message_to_ordereddict
from sensor_msgs.msg import JointState
from geometry_msgs.msg import TwistStamped, PoseStamped
from std_msgs.msg import Float64MultiArray
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint
from control_msgs.msg import JointTrajectoryControllerState
from std_srvs.srv import SetBool, Trigger

ROOT=Path(os.environ['TRIAL_ROOT'])
STACK=os.environ['STACK']
MODE=os.environ['MODE']
NAMES=['shoulder_pan_joint','shoulder_lift_joint','elbow_joint','wrist_1_joint','wrist_2_joint','wrist_3_joint']
EXPECTED=[0,-1.57,1.57,0,1.57,0] if STACK=='docker' else [0,0,1.4232,.243,4.6863,1.6315]
raw=(ROOT/'topics.jsonl').open('a',buffering=1)
events=(ROOT/'events.jsonl').open('a',buffering=1)
def event(kind,**kw):
    events.write(json.dumps(dict(kind=kind,monotonic_ns=time.monotonic_ns(),**kw),sort_keys=True)+'\n')
def phase(name,teleop=True,tracked=True,x=.2,z=0,generation=1):
    data=dict(name=name,teleop=teleop,tracked=tracked,x=x,z=z,generation=generation)
    tmp=ROOT/'phase.tmp'
    tmp.write_text(json.dumps(data))
    tmp.replace(ROOT/'phase.json')
    return data

rclpy.init()
node=Node('closure_recorder')
samples=[]
def callback(topic,msg):
    now=time.monotonic_ns()
    raw.write(json.dumps(dict(topic=topic,monotonic_ns=now,payload=message_to_ordereddict(msg)),sort_keys=True)+'\n')
    if topic=='/joint_states':
        try:
            idx=[list(msg.name).index(n) for n in NAMES]
            samples.append((now,[msg.position[i] for i in idx],[msg.velocity[i] for i in idx],msg.header.stamp.sec*10**9+msg.header.stamp.nanosec))
        except (ValueError,IndexError):
            pass
topics=[('/joint_states',JointState)]
if STACK=='docker':
    from teleop_bridge_msgs.msg import ReceivedPoseStates, TargetTwistStates
    topics += [('/received_pose_states',ReceivedPoseStates),('/target_twist_states',TargetTwistStates),
        ('/servo_node/delta_twist_cmds',TwistStamped),('/joint_group_velocity_controller/commands',Float64MultiArray)]
else:
    topics += [('/servo_node/pose_target_cmds',PoseStamped),('/ur5_arm_controller/joint_trajectory',JointTrajectory),('/ur5_arm_controller/controller_state',JointTrajectoryControllerState)]
for topic,typ in topics:
    node.create_subscription(typ,topic,lambda msg,t=topic:callback(t,msg),qos_profile_sensor_data)
event('clock',boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
    time_namespace=os.readlink('/proc/self/ns/time'),clock='CLOCK_MONOTONIC')
def spin(seconds):
    end=time.monotonic()+seconds
    while time.monotonic()<end:
        rclpy.spin_once(node,timeout_sec=.005)

def call_service(typ,name,request):
    client=node.create_client(typ,name)
    if not client.wait_for_service(timeout_sec=3):
        raise RuntimeError('BLOCKED_STOP_API '+name)
    event('service_request',name=name,request=str(request))
    future=client.call_async(request)
    deadline=time.monotonic()+3
    while not future.done() and time.monotonic()<deadline: spin(.005)
    if not future.done(): raise RuntimeError('service response timeout '+name)
    response=future.result()
    event('service_reply',name=name,response=str(response))
    if not response.success: raise RuntimeError('negative service reply '+name)
    return response

# Acknowledgment uses actual received samples, not a fixed startup sleep.
deadline=time.monotonic()+25
ready=False
error=drift=velocity=None
while time.monotonic()<deadline:
    spin(.02)
    window=[s for s in samples if s[0]>=time.monotonic_ns()-600_000_000]
    if len(window)<3 or window[-1][0]-window[0][0]<500_000_000:
        continue
    error=max(abs(p-e) for p,e in zip(window[-1][1],EXPECTED))
    drift=max(max(s[1][i] for s in window)-min(s[1][i] for s in window) for i in range(6))
    velocity=max(abs(v) for s in window for v in s[2])
    stamps=len(set(s[3] for s in window))
    ready=error<.0001 and drift<.0001 and velocity<.001 and stamps>=3
    if ready:
        break
event('recorder_readiness',ready=ready,window_samples=len(window),
      position_error=error if window else None,drift=drift if window else None,
      velocity=velocity if window else None, expected=EXPECTED, observed=samples[-1][1] if samples else None)
if not ready:
    event('BLOCKED_INITIAL_CONDITION')
    raise SystemExit(12)
# Require real DDS matches for production -> Servo -> controller before release.
for topic in ('/servo_node/pose_target_cmds','/ur5_arm_controller/joint_trajectory'):
    pubs=node.get_publishers_info_by_topic(topic)
    subs=node.get_subscriptions_info_by_topic(topic)
    event('graph_ack',topic=topic,publishers=[x.node_name for x in pubs],subscribers=[x.node_name for x in subs])
    if len(pubs)<1 or len(subs)<2:
        raise SystemExit('BLOCKED_GRAPH_ACK '+topic)
ROOT.joinpath('recorder.ready').write_text('READY\n')
while not ROOT.joinpath('production.ready').exists():
    spin(.02)
    if time.monotonic()>deadline+20:
        raise SystemExit('production readiness timeout')
phase('idle',teleop=False)
event('barrier_release')
ROOT.joinpath('barrier.json').write_text(json.dumps({'monotonic_ns':time.monotonic_ns()}))

sock=socket.create_connection(('127.0.0.1',5005),timeout=3) if STACK=='docker' else None
source=(ROOT/'sent.jsonl').open('a',buffering=1)
seq=0
def segment(name,seconds,teleop=True,tracked=True,x=.2,z=0,send=True,generation=1):
    global seq,sock
    data=phase(name,teleop,tracked,x,z,generation)
    event('phase_start',**data)
    start=time.monotonic()
    next_send=start
    while time.monotonic()-start<seconds:
        now=time.monotonic()
        if STACK=='docker' and send and now>=next_send:
            if sock is None:
                sock=socket.create_connection(('127.0.0.1',5005),timeout=3)
                event('sender_reconnected',phase=name,generation=generation)
            metadata=dict(sample_id=f'docker:{seq}',generation_id=generation,source_timestamp_ns=time.monotonic_ns(),native_state={'isTracked':tracked},phase=name)
            hand={'isTracked':tracked,'pos':{'x':x,'y':.2,'z':.3},'rot':{'x':0.,'y':0.,'z':0.,'w':1.}}
            payload={'timestamp':metadata['source_timestamp_ns']/1e9,'right_hand':hand,
                'left_hand':{'isTracked':True,'pos':{'x':.2,'y':.2,'z':.3},'rot':{'x':0.,'y':0.,'z':0.,'w':1.}},
                'controls':{'right_teleop_enable':teleop,'teleop_enable':teleop,'grip_value':1. if teleop else 0.,'source':'closure_synthetic'},'_qualification':metadata}
            wire=json.dumps(payload,separators=(',',':'))+'\n'
            source.write(json.dumps({'sent_monotonic_ns':time.monotonic_ns(),'wire':wire})+'\n')
            try: sock.sendall(wire.encode())
            except (BrokenPipeError,ConnectionResetError):
                event('sender_peer_closed',phase=name,generation=generation)
                sock.close();sock=socket.create_connection(('127.0.0.1',5005),timeout=3)
                event('sender_reconnected',phase=name,generation=generation)
                sock.sendall(wire.encode())
            seq+=1
            next_send+=.05
        spin(.005)
    event('phase_end',name=name)

segment('idle',1,teleop=False)
segment('reference',.8)
segment('active',1,x=.35,z=.10)
if MODE in ('b0','shim'):
    segment('tail',2,teleop=False)
elif MODE=='stall':
    segment('sender_stall',1.5,x=.35,send=False)
    sock.close();sock=None
    segment('recovered_release',.6,teleop=False,x=.35,generation=2)
    segment('new_reference',.8,x=.35,generation=2)
    segment('resumed',1,x=.50,generation=2)
    segment('tail',1,teleop=False)
else:
    event('native_tracking_gate_request' if STACK=='docker' and MODE=='stop' else 'external_stop_request',reason='OPERATOR_QUALIFICATION')
    # Native Docker gate and external Servo pause are different cases.
    if STACK=='docker' and MODE=='stop':
        segment('tracking_false',1.5,tracked=False,x=.35)
    elif STACK=='docker' and MODE=='health':
        ROOT.joinpath('health.trigger').write_text('official monitor health qualification\n')
        event('health_trigger')
        segment('health_wait',1.5,x=.35)
        event('health_adapter_observed',stopped=ROOT.joinpath('health.stopped').exists())
        if not ROOT.joinpath('health.stopped').exists():
            raise RuntimeError('health interlock did not stop')
    elif STACK=='docker':
        call_service(Trigger,'/servo_node/stop_servo',Trigger.Request())
        if MODE=='hold':
            hold_pub=node.create_publisher(Float64MultiArray,'/joint_group_velocity_controller/commands',10)
            until=time.monotonic()+3
            while hold_pub.get_subscription_count()==0 and time.monotonic()<until: spin(.005)
            zero=Float64MultiArray(); zero.data=[0.]*6
            hold_pub.publish(zero)
            event('controller_zero_request',values=zero.data.tolist())
        segment('stopped_input_continues',1.5,x=.35)
    else:
        req=SetBool.Request(); req.data=True
        call_service(SetBool,'/servo_node/pause_servo',req)
        if MODE=='hold_fast':
            hold_pub=node.create_publisher(JointTrajectory,'/ur5_arm_controller/joint_trajectory',10)
            until=time.monotonic()+3
            while hold_pub.get_subscription_count()==0 and time.monotonic()<until: spin(.005)
            hold=JointTrajectory(); hold.joint_names=NAMES
            point=JointTrajectoryPoint(); point.positions=samples[-1][1]; point.velocities=[0.]*6
            point.time_from_start.nanosec=10_000_000; hold.points=[point]
            for hold_index in range(5):
                hold.header.stamp=node.get_clock().now().to_msg()
                hold_pub.publish(hold)
                event('controller_hold_request',hold_index=hold_index,positions=point.positions.tolist(),duration_ns=10_000_000)
                spin(.02)
        segment('paused_input_continues',1.5,z=.15)
    segment('recovered_release',.6,teleop=False,x=.35,z=.15,generation=2)
    if STACK=='openvr':
        req=SetBool.Request(); req.data=False
        call_service(SetBool,'/servo_node/pause_servo',req)
    elif MODE in ('external','hold','health'):
        call_service(Trigger,'/servo_node/start_servo',Trigger.Request())
    segment('new_reference',.8,x=.35,z=.15,generation=2)
    segment('resumed',1,x=.50,z=.25,generation=2)
    segment('tail',1,teleop=False)
if sock: sock.close()
event('complete')
node.destroy_node()
rclpy.shutdown()
