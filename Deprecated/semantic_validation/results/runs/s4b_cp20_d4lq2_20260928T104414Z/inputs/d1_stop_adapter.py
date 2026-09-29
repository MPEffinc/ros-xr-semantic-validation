"""Ordinary stop-only integration from a gate/monitor verdict; no XR predicate.

This adapter never reads pose, validity, source age, generation or recovery
metadata. It is not ROSMonitoring and cannot generate a policy verdict.
"""
import json
import os
import time
from pathlib import Path

import rclpy
from rclpy.node import Node
from std_msgs.msg import Float64MultiArray
from std_srvs.srv import Trigger

root = Path(os.environ['TRIAL_ROOT'])
mode = os.environ['MODE']
regime = os.environ['INFO_REGIME']
if mode == 'b1':
    verdict_path = root / 'gate_verdict.jsonl'
elif mode == 'b3':
    verdict_path = root / 'lineage.jsonl'
elif mode == 'b2':
    verdict_path = root / ('monitor_full_status.jsonl' if regime == 'full'
                           else 'monitor_native_status.jsonl')
else:
    raise SystemExit('stop adapter is only for B1/B2-composed/B3')

events = (root / 'stop_adapter.jsonl').open('a', buffering=1)
def emit(kind, **fields):
    events.write(json.dumps(dict(kind=kind, monotonic_ns=time.monotonic_ns(),
                                 **fields), sort_keys=True) + '\n')

rclpy.init()
node = Node('d1_common_stop_adapter')
zero = node.create_publisher(Float64MultiArray,
                             '/joint_group_velocity_controller/commands', 10)
stop = node.create_client(Trigger, '/servo_node/stop_servo')
deadline = time.monotonic() + 45
while time.monotonic() < deadline:
    rclpy.spin_once(node, timeout_sec=.01)
    if stop.wait_for_service(timeout_sec=.01) and zero.get_subscription_count() >= 1:
        break
else:
    emit('readiness_failed', stop_available=stop.service_is_ready(),
         controller_subscribers=zero.get_subscription_count())
    raise SystemExit(12)

emit('ready', verdict_source=mode, verdict_path=str(verdict_path))
(root / 'stop_adapter.ready').write_text('service/controller DDS matches; awaiting barrier\n')
while not (root / 'barrier.json').exists():
    rclpy.spin_once(node, timeout_sec=.01)
start_ns = json.loads((root / 'barrier.json').read_text())['start_monotonic_ns']
while time.monotonic_ns() < start_ns:
    rclpy.spin_once(node, timeout_sec=.001)

last_event_ns = time.monotonic_ns()
cursor = 0
trigger = None
from d4l_timing import capture_ns
capture_end_ns = start_ns + capture_ns()  # D4-L: registered capture length (6 s default)
while time.monotonic_ns() < capture_end_ns and trigger is None:
    rclpy.spin_once(node, timeout_sec=.005)
    qualification_trigger = root / 'qualification_stop_trigger.json'
    if os.environ.get('STOP_DIAG') == '1' and qualification_trigger.exists():
        trigger = 'QUALIFICATION_STOP'
        emit('qualification_trigger', record=json.loads(qualification_trigger.read_text()))
        break
    if verdict_path.exists():
        with verdict_path.open() as stream:
            stream.seek(cursor)
            fresh = []
            while True:
                line = stream.readline()
                if not line or not line.endswith('\n'):
                    break
                cursor = stream.tell()
                fresh.append(line)
        for line in fresh:
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if mode == 'b1':
                last_event_ns = time.monotonic_ns()
                if row.get('allowed') is False:
                    trigger = 'B1_POLICY_REJECT'
            elif mode == 'b3' and row.get('kind') == 'b3_mapper_verdict':
                last_event_ns = time.monotonic_ns()
                if row.get('verdict') is False:
                    trigger = 'B3_POLICY_REJECT'
            elif mode == 'b2' and row.get('status') == 'event':
                last_event_ns = time.monotonic_ns()
                verdict = row.get('verdict_raw')
                if verdict in ('unknown', 'error'):
                    trigger = 'B2_MONITOR_HEALTH'
                elif verdict == 'currently_false':
                    trigger = 'B2_ORACLE_POLICY_REJECT'
            if trigger is not None:
                emit('verdict_trigger', source=trigger, verdict=row)
                break
    if time.monotonic_ns() - last_event_ns > 250_000_000:
        trigger = f'{mode.upper()}_VERDICT_HEARTBEAT_MISSING'
        emit('health_trigger', source=trigger)

if trigger is not None:
    emit('stop_request', source=trigger)
    future = stop.call_async(Trigger.Request())
    reply_deadline = time.monotonic() + 3
    while not future.done() and time.monotonic() < reply_deadline:
        rclpy.spin_once(node, timeout_sec=.005)
    if not future.done() or not future.result().success:
        emit('stop_failed', source=trigger)
        raise SystemExit(13)
    emit('stop_reply', source=trigger, reply=str(future.result()))
    msg = Float64MultiArray(data=[0.] * 6)
    zero.publish(msg)
    emit('controller_zero', source=trigger, values=list(msg.data))
    (root / 'stop_adapter.stopped').write_text(trigger + '\n')
else:
    emit('healthy_capture_complete')
while True:
    rclpy.spin_once(node, timeout_sec=.1)
