"""Generic health interlock for qualification: official monitor unknown -> Servo stop + zero controller.

No payload validity, source age, generation, or recovery policy is evaluated here.
"""
import json,time
from pathlib import Path
import rclpy
from rclpy.node import Node
from std_msgs.msg import Float64MultiArray
from std_srvs.srv import Trigger
from teleop_bridge_msgs.msg import ReceivedPoseStates
root=Path('/results')
status=root/'rosmonitoring/humble/edge_logs_03/custom_status.jsonl'
log=(root/'health.jsonl').open('a',buffering=1)
def emit(kind,**kw):log.write(json.dumps(dict(kind=kind,monotonic_ns=time.monotonic_ns(),**kw))+'\n')
rclpy.init(); node=Node('closure_health_stop')
pub=node.create_publisher(ReceivedPoseStates,'/s4b_custom_mon',10)
zero_pub=node.create_publisher(Float64MultiArray,'/joint_group_velocity_controller/commands',10)
stop=node.create_client(Trigger,'/servo_node/stop_servo')
def spin():rclpy.spin_once(node,timeout_sec=.005)
deadline=time.monotonic()+120
while not (root/'health.trigger').exists() and time.monotonic()<deadline:spin()
if time.monotonic()>=deadline:raise SystemExit('no health trigger')
while pub.get_subscription_count()<1 and time.monotonic()<deadline:spin()
if pub.get_subscription_count()<1:raise SystemExit('official monitor subscriber not ready')
msg=ReceivedPoseStates(); msg.tracked=True; msg.source='health_qualification'
pub.publish(msg); emit('monitor_stimulus',tracked=True)
seen=set(); matched=None
while time.monotonic()<deadline:
    spin()
    if not status.exists():continue
    for line in status.read_text().splitlines():
        if line in seen:continue
        seen.add(line)
        row=json.loads(line)
        if row.get('status')=='event' and row.get('verdict_raw') in ('unknown','error'):
            matched=row;break
    if matched:break
if matched is None:raise SystemExit('no official monitor unknown event')
emit('monitor_health_event',status=matched['status'],verdict_raw=matched['verdict_raw'],decision=matched.get('decision'))
if not stop.wait_for_service(timeout_sec=3):raise SystemExit('stop service unavailable')
emit('health_stop_request');future=stop.call_async(Trigger.Request())
while not future.done() and time.monotonic()<deadline:spin()
if not future.done() or not future.result().success:raise SystemExit('stop service failed')
emit('health_stop_reply',response=str(future.result()))
while zero_pub.get_subscription_count()<1 and time.monotonic()<deadline:spin()
zero=Float64MultiArray();zero.data=[0.]*6;zero_pub.publish(zero)
emit('health_controller_zero_request',values=list(zero.data))
(root/'health.stopped').write_text('stop+zero requested after official monitor unknown\n')
node.destroy_node();rclpy.shutdown()
