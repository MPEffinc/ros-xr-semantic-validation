"""Recorder and acknowledged common start for B0/shim qualification only."""
import json
import os
import time
from pathlib import Path
from resource_sampler import snapshot

import rclpy
from controller_manager_msgs.srv import ListControllers
from geometry_msgs.msg import PoseStamped, TwistStamped
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from rosidl_runtime_py.convert import message_to_ordereddict
from sensor_msgs.msg import JointState
from std_msgs.msg import Float64MultiArray, String
from std_srvs.srv import Trigger
from trajectory_msgs.msg import JointTrajectory

root = Path(os.environ['TRIAL_ROOT'])
stack = os.environ['STACK']
mode = os.environ['MODE']
regime = os.environ['INFO_REGIME']
names = ['shoulder_pan_joint', 'shoulder_lift_joint', 'elbow_joint',
         'wrist_1_joint', 'wrist_2_joint', 'wrist_3_joint']
expected = [0, -1.57, 1.57, 0, 1.57, 0] if stack == 'docker' else [0, 0, 1.4232, .243, 4.6863, 1.6315]
events = (root / 'events.jsonl').open('a', buffering=1)
topics_out = (root / 'topics.jsonl').open('a', buffering=1)

def event(kind, **details):
    events.write(json.dumps(dict(kind=kind, monotonic_ns=time.monotonic_ns(), **details), sort_keys=True) + '\n')

rclpy.init()
node = Node('cp1_recorder')
samples = []
topics = [('/joint_states', JointState)]
if stack == 'docker':
    from teleop_bridge_msgs.msg import ReceivedPoseStates, TargetTwistStates
    topics += [('/received_pose_states', ReceivedPoseStates),
               ('/target_twist_states', TargetTwistStates),
               ('/servo_node/delta_twist_cmds', TwistStamped),
               ('/joint_group_velocity_controller/commands', Float64MultiArray)]
    if mode == 'b2':
        from std_msgs.msg import String
        carrier = String if regime == 'full' else ReceivedPoseStates
        carrier_root = '/s4b/d1/envelope' if regime == 'full' else '/s4b/d1/native_input'
        topics += [(carrier_root, carrier), (carrier_root + '_mon', carrier)]
    edges = [x for x, _ in topics[1:]]
    topics += [('/s4b/d3/common_tick', String)]
    if mode == 'b2':
        topics += [('/s4b/d3/tick_mon', String),
                   ('/s4b/d3/tick', String)]
    controller_name = 'joint_group_velocity_controller'
    servo_service = '/servo_node/start_servo'
else:
    from control_msgs.msg import JointTrajectoryControllerState
    topics += [('/servo_node/pose_target_cmds', PoseStamped),
               ('/ur5_arm_controller/joint_trajectory', JointTrajectory),
               ('/ur5_arm_controller/controller_state', JointTrajectoryControllerState)]
    edges = ['/servo_node/pose_target_cmds', '/ur5_arm_controller/joint_trajectory']
    controller_name = 'ur5_arm_controller'
    servo_service = '/servo_node/pause_servo'

def callback(topic, msg):
    now = time.monotonic_ns()
    data = message_to_ordereddict(msg)
    topics_out.write(json.dumps(dict(topic=topic, monotonic_ns=now, payload=data), sort_keys=True) + '\n')
    if topic == '/joint_states':
        try:
            indices = [msg.name.index(name) for name in names]
            samples.append((now, [msg.position[i] for i in indices],
                            [msg.velocity[i] for i in indices],
                            msg.header.stamp.sec * 1_000_000_000 + msg.header.stamp.nanosec))
        except (ValueError, IndexError):
            pass

for name, msg_type in topics:
    node.create_subscription(msg_type, name, lambda msg, topic=name: callback(topic, msg), qos_profile_sensor_data)

event('clock', boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
      time_namespace=os.readlink('/proc/self/ns/time'), clock='CLOCK_MONOTONIC')
probe_boot = Path('/proc/sys/kernel/random/boot_id').read_text().strip()
probe_time_namespace = os.readlink('/proc/self/ns/time')

def participant_clocks():
    required = ['gazebo', 'clock', 'rsp', 'servo', 'sender', 'resources', 'recorder', 'tick']
    if mode == 'b0': required += ['receiver', 'mapper', 'bridge']
    else: required += ['observed']
    if mode == 'b2': required += ['oracle', 'monitor']
    if mode in ('b1', 'b3') or (mode == 'b2' and os.environ.get('COMPOSED') == '1'): required += ['stop_adapter']
    if mode == 'b1': required += ['source_gate']
    records = {}
    for label in required:
        path = root / f'participant_clock_{label}.json'
        if not path.exists(): return None
        try: record = json.loads(path.read_text())
        except json.JSONDecodeError: return None
        if (record.get('boot_id') != probe_boot or
            record.get('time_namespace') != probe_time_namespace or
            record.get('clock') != 'CLOCK_MONOTONIC'): return None
        records[label] = record
    return records

def spin(seconds=.01):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        rclpy.spin_once(node, timeout_sec=.005)

def graph():
    return {name: dict(publishers=[x.node_name for x in node.get_publishers_info_by_topic(name)],
                       subscriptions=[x.node_name for x in node.get_subscriptions_info_by_topic(name)])
            for name, _ in topics}

def controller_states():
    client = node.create_client(ListControllers, '/controller_manager/list_controllers')
    if not client.wait_for_service(timeout_sec=.1):
        return {}
    future = client.call_async(ListControllers.Request())
    deadline = time.monotonic() + 2
    while not future.done() and time.monotonic() < deadline:
        spin(.01)
    if not future.done() or future.result() is None:
        return {}
    return {item.name: item.state for item in future.result().controller}

deadline = time.monotonic() + 45
ready = False
last = {}
while time.monotonic() < deadline:
    spin(.03)
    window = [s for s in samples if s[0] >= time.monotonic_ns() - 650_000_000]
    if len(window) < 3 or window[-1][0] - window[0][0] < 500_000_000:
        continue
    position_error = max(abs(p - e) for p, e in zip(window[-1][1], expected))
    drift = max(max(s[1][i] for s in window) - min(s[1][i] for s in window) for i in range(6))
    speed = max(abs(v) for s in window for v in s[2])
    increasing = all(a[3] < b[3] for a, b in zip(window, window[1:]))
    if position_error >= .0001 or drift >= .0001 or speed >= .001 or not increasing:
        continue
    if not (root / 'production.ready').exists():
        continue
    if stack == 'docker' and not (root / 'sender.ready').exists():
        continue
    if stack == 'docker' and mode != 'b0' and not (root / 'd1_nodes.ready').exists():
        continue
    if stack == 'docker' and not (root / 'd3_tick.ready').exists():
        continue
    if stack == 'docker' and mode == 'b1' and not (root / 'd3_source_gate.ready').exists():
        continue
    if not (root / 'resource_sampler.ready').exists():
        continue
    clocks = participant_clocks()
    if clocks is None:
        continue
    resource_path = root / 'resource_samples.jsonl'
    if not resource_path.exists():
        continue
    try:
        resource_rows = [json.loads(line) for line in resource_path.read_text().splitlines() if line]
        recent_resources = next(row for row in reversed(resource_rows) if row.get('kind') == 'sample')
    except (json.JSONDecodeError, StopIteration):
        continue
    if not all(recent_resources['targets'].get(label, {}).get('status') == 'OBSERVED'
               for label in clocks):
        continue
    if (mode in ('b1', 'b3') or (mode == 'b2' and os.environ.get('COMPOSED') == '1')) and not (root / 'stop_adapter.ready').exists():
        continue
    monitor_events = []
    monitor_dds_match = None
    if mode == 'b2':
        marker = root / 'monitor_dds_match.ready'
        if not marker.exists():
            continue
        try:
            monitor_dds_match = json.loads(marker.read_text())
        except json.JSONDecodeError:
            continue
        if monitor_dds_match.get('monitor_subscription_count', 0) < 1:
            continue
    if mode == 'b2':
        status_file = root / ('monitor_full_status.jsonl' if regime == 'full' else 'monitor_native_status.jsonl')
        if not status_file.exists():
            continue
        try:
            monitor_events = [json.loads(line) for line in status_file.read_text().splitlines() if line]
        except json.JSONDecodeError:
            continue
        if not any(row.get('status') == 'started' for row in monitor_events):
            continue
        if not any(row.get('status') == 'event' and row.get('decision') == 'forwarded'
                   and row.get('verdict_raw') == 'currently_true' for row in monitor_events):
            continue
    current_graph = graph()
    graph_ok = all(len(current_graph[name]['publishers']) >= 1 and
                   len(current_graph[name]['subscriptions']) >= 2 for name in edges)
    graph_ok &= len(current_graph['/joint_states']['publishers']) >= 1
    if stack == 'docker':
        tick_graph = current_graph['/s4b/d3/common_tick']
        graph_ok &= set(tick_graph['publishers']) == {'d3_common_health_tick'}
        graph_ok &= 'cp1_recorder' in tick_graph['subscriptions']
        if mode == 'b3':
            graph_ok &= 'hand_pose_mapper' in tick_graph['subscriptions']
    if stack == 'docker' and mode == 'b2':
        carrier_root = '/s4b/d1/envelope' if regime == 'full' else '/s4b/d1/native_input'
        guard = 'd3_full_guard' if regime == 'full' else 'd3_native_guard'
        graph_ok &= set(current_graph['/received_pose_states']['publishers']) == {'d1_lossless_stripper'}
        graph_ok &= set(current_graph[carrier_root]['publishers']) == {guard}
        graph_ok &= set(current_graph[carrier_root + '_mon']['publishers']) == {'quest_controller_receiver'}
        graph_ok &= set(current_graph['/s4b/d3/tick_mon']['publishers']) == {'d3_common_health_tick'}
        graph_ok &= guard in current_graph['/s4b/d3/tick_mon']['subscriptions']
        graph_ok &= set(current_graph['/s4b/d3/tick']['publishers']) == {guard}
        graph_ok &= 'cp1_recorder' in current_graph['/s4b/d3/tick']['subscriptions']
    services = {name: types for name, types in node.get_service_names_and_types()}
    service_ok = servo_service in services
    if not (graph_ok and service_ok):
        continue
    states = controller_states()
    if states.get('joint_state_broadcaster') != 'active' or states.get(controller_name) != 'active':
        continue
    if stack == 'openvr' and 'success=True' not in (root / 'servo_mode.txt').read_text():
        continue
    last = dict(position_error=position_error, drift=drift, speed=speed,
                joint_samples=len(window), increasing_stamps=increasing,
                monitor_dds_match=monitor_dds_match,
                graph=current_graph, controllers=states, servo_service=servo_service,
                participant_clocks=clocks,
                monitor_oracle_positive_events=sum(row.get('status') == 'event' and
                    row.get('verdict_raw') == 'currently_true' for row in monitor_events))
    ready = True
    break

if not ready:
    event('readiness_failed', samples=len(samples), graph=graph(), controllers=controller_states())
    raise SystemExit(12)

if stack == 'docker':
    client = node.create_client(Trigger, servo_service)
    future = client.call_async(Trigger.Request())
    deadline = time.monotonic() + 3
    while not future.done() and time.monotonic() < deadline:
        spin(.01)
    if not future.done() or not future.result().success:
        event('servo_start_failed')
        raise SystemExit(13)
    last['servo_start_reply'] = str(future.result())

event('readiness_ack', **last)
(root / 'recorder.ready').write_text('subscription matches, joint window, controllers and Servo acknowledged\n')
start_ns = time.monotonic_ns() + 1_000_000_000
(root / 'barrier.json').write_text(json.dumps(dict(release_monotonic_ns=time.monotonic_ns(),
                                                  start_monotonic_ns=start_ns, source_index=0)))
event('barrier_release', start_monotonic_ns=start_ns)
end_ns = start_ns + (6_000_000_000 if stack == 'docker' else 12_000_000_000)
stop_triggered = False
while time.monotonic_ns() < end_ns:
    spin(.01)
    if os.environ.get('STOP_DIAG') == '1' and not stop_triggered and time.monotonic_ns() >= start_ns + 2_250_000_000:
        trigger_ns = time.monotonic_ns()
        (root / 'qualification_stop_trigger.json').write_text(json.dumps(dict(
            kind='QUALIFICATION_STOP', monotonic_ns=trigger_ns,
            reason='ordinary_stop_actuation_test_not_source_policy')))
        event('qualification_stop_trigger', trigger_ns=trigger_ns)
        stop_triggered = True
boundary_before_ns = time.monotonic_ns()
boundary_targets = snapshot(root, {})
boundary_after_ns = time.monotonic_ns()
(root / 'resource_capture_boundary.json').write_text(json.dumps(dict(
    kind='resource_capture_boundary', clock='CLOCK_MONOTONIC',
    boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
    time_namespace=os.readlink('/proc/self/ns/time'),
    acquisition_start_ns=boundary_before_ns,
    acquisition_end_ns=boundary_after_ns,
    targets=boundary_targets), sort_keys=True) + '\n')
event('capture_end', sent_records=sum(1 for _ in (root / 'sent.jsonl').open()) if (root / 'sent.jsonl').exists() else None,
      source_records=sum(1 for _ in (root / 'source.jsonl').open()) if (root / 'source.jsonl').exists() else None)
(root / 'capture_end.ready').write_text(str(time.monotonic_ns()) + '\n')
sent = [json.loads(line) for line in (root / 'sent.jsonl').read_text().splitlines()] if (root / 'sent.jsonl').exists() else []
if len(sent) != 120 or [row['index'] for row in sent] != list(range(120)) or not (root / 'sender.done').exists():
    event('source_incomplete', sent_records=len(sent), expected=120,
          sender_done=(root / 'sender.done').exists())
    raise SystemExit(14)
real = [row for row in sent if row.get('sent')]
silent = [row['index'] for row in sent if row.get('reason') == 'INTENTIONAL_NO_SOURCE_BYTES']
if (len(real) != 100 or silent != list(range(56, 76)) or
        any(json.loads(row['wire'])['_qualification']['sample_id'] != f"docker:{row['index']}"
            for row in real)):
    event('d3_source_schedule_invalid', actual_real=len(real), silent_indices=silent)
    raise SystemExit(15)
tick_path = root / 'd3_ticks.jsonl'
ticks = [json.loads(line) for line in tick_path.read_text().splitlines()] if tick_path.exists() else []
if (not (root / 'd3_tick.done').exists() or len(ticks) != 300 or
        [row['index'] for row in ticks] != list(range(300)) or
        any(row.get('source_sample_id') is not None for row in ticks)):
    event('d3_tick_incomplete', tick_count=len(ticks))
    raise SystemExit(16)
node.destroy_node()
rclpy.shutdown()
