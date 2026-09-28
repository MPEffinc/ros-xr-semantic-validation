"""OpenVR recorder and acknowledged common start barrier (observation only).

Readiness (protocol section 7, W1/W2 gate), all required before one barrier:
  * >= .5 s of named /joint_states with increasing stamps; six arm joints within
    .0001 rad of the fixed OpenVR neutral fixture, speed < .001 rad/s, drift < .0001;
  * production.ready (source held at index zero), resource sampler ready, and a
    participant clock record for every required process on one boot/time namespace;
  * DDS publisher/subscriber matches on every production -> Servo -> controller edge
    (and, for B2, on the envelope -> official monitor -> stripper edges);
  * active joint_state_broadcaster and ur5_arm_controller; successful Servo pose
    command-type reply; stop adapter ready (B1/B2-composed/B3);
  * B2: one calibration envelope acknowledged end-to-end through the genuine official
    path (property row + official forwarded currently_true status + guarded receipt).
Then barrier = now + 1 s; capture 12 s. No sleep substitutes for the ACK.
"""
import json
import os
import time
from pathlib import Path

import rclpy
from control_msgs.msg import JointTrajectoryControllerState
from controller_manager_msgs.srv import ListControllers
from geometry_msgs.msg import PoseStamped
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from rosidl_runtime_py.convert import message_to_ordereddict
from sensor_msgs.msg import JointState
from std_msgs.msg import String
from trajectory_msgs.msg import JointTrajectory

root = Path(os.environ['TRIAL_ROOT'])
MODE = os.environ['MODE']
COMPOSED = os.environ.get('COMPOSED') == '1'
CMON = os.environ.get('CMON_FAULT', '')
NAMES = ['shoulder_pan_joint', 'shoulder_lift_joint', 'elbow_joint', 'wrist_1_joint', 'wrist_2_joint', 'wrist_3_joint']
EXPECTED = [0, 0, 1.4232, .243, 4.6863, 1.6315]
CAPTURE_NS = int(os.environ.get('XR_CAPTURE_NS', '12000000000'))
events = (root / 'events.jsonl').open('a', buffering=1)
topics_out = (root / 'topics.jsonl').open('a', buffering=1)


def event(kind, **details):
    events.write(json.dumps(dict(kind=kind, monotonic_ns=time.monotonic_ns(), **details), sort_keys=True) + '\n')


def rows(path):
    try:
        return [json.loads(x) for x in Path(path).read_text().splitlines() if x.strip()] if Path(path).exists() else []
    except json.JSONDecodeError:
        return None


rclpy.init()
node = Node('cp1_recorder')
samples = []
topics = [('/joint_states', JointState), ('/servo_node/pose_target_cmds', PoseStamped),
          ('/ur5_arm_controller/joint_trajectory', JointTrajectory),
          ('/ur5_arm_controller/controller_state', JointTrajectoryControllerState)]
if MODE == 'b2':
    topics += [('/s4b/ovr/envelope_mon', String), ('/s4b/ovr/envelope', String)]


def callback(topic, msg):
    now = time.monotonic_ns()
    topics_out.write(json.dumps(dict(topic=topic, monotonic_ns=now, payload=message_to_ordereddict(msg)), sort_keys=True) + '\n')
    if topic == '/joint_states':
        try:
            idx = [msg.name.index(n) for n in NAMES]
            samples.append((now, [msg.position[i] for i in idx], [msg.velocity[i] for i in idx],
                            msg.header.stamp.sec * 1_000_000_000 + msg.header.stamp.nanosec))
        except (ValueError, IndexError):
            pass


for name, msg_type in topics:
    node.create_subscription(msg_type, name, lambda msg, topic=name: callback(topic, msg), qos_profile_sensor_data)
probe_boot = Path('/proc/sys/kernel/random/boot_id').read_text().strip()
probe_ns = os.readlink('/proc/self/ns/time')
event('clock', boot_id=probe_boot, time_namespace=probe_ns, clock='CLOCK_MONOTONIC')


def spin(seconds=.01):
    limit = time.monotonic() + seconds
    while time.monotonic() < limit:
        rclpy.spin_once(node, timeout_sec=.005)


def graph():
    return {name: dict(publishers=sorted(x.node_name for x in node.get_publishers_info_by_topic(name)),
                       subscriptions=sorted(x.node_name for x in node.get_subscriptions_info_by_topic(name)))
            for name, _ in topics}


def controller_states():
    client = node.create_client(ListControllers, '/controller_manager/list_controllers')
    if not client.wait_for_service(timeout_sec=.1):
        return {}
    future = client.call_async(ListControllers.Request())
    limit = time.monotonic() + 2
    while not future.done() and time.monotonic() < limit:
        spin(.01)
    if not future.done() or future.result() is None:
        return {}
    return {item.name: item.state for item in future.result().controller}


def required_labels():
    labels = ['gazebo', 'servo', 'production', 'recorder', 'resources']
    if MODE == 'b2':
        labels += ['monitor', 'stripper'] + ([] if CMON == 'ORACLE_ABSENT' else ['oracle'])
    if MODE in ('b1', 'b3') or (MODE == 'b2' and COMPOSED):
        labels += ['stop_adapter']
    if CMON:
        labels += ['fault']
    return labels


def participant_clocks():
    records = {}
    for label in required_labels():
        record = rows(root / f'participant_clock_{label}.json')
        if not record:
            return None
        record = record[0]
        if record.get('boot_id') != probe_boot or record.get('time_namespace') != probe_ns or record.get('clock') != 'CLOCK_MONOTONIC':
            return None
        records[label] = record
    return records


def calibration_ack():
    """Latest calibration attempt observed at every official-path boundary (B2 only)."""
    attempts = rows(root / 'calibration.jsonl') or []
    for attempt in reversed(attempts):
        key = attempt['key']
        props = [p for p in rows(root / 'property.jsonl') or [] if p.get('monitor_event_id') == key]
        statuses = []
        for s in rows(root / 'monitor_full_status.jsonl') or []:
            if s.get('status') == 'event':
                try:
                    if json.loads(s['event']['data'])['envelope_monotonic_ns'] == key:
                        statuses.append(s)
                except (KeyError, TypeError, ValueError):
                    pass
        receipts = [r for r in rows(root / 'lineage.jsonl') or [] if r.get('kind') == 'monitor_output_received'
                    and r.get('monitor_event_id') == key]
        if CMON == 'ORACLE_ABSENT':
            ok = (len(props) == 0 and len(statuses) == 1 and statuses[0].get('verdict_raw') == 'unknown'
                  and statuses[0].get('decision') == 'forwarded' and len(receipts) == 1)
        else:
            ok = (len(props) == 1 and props[0].get('safe') is True and len(statuses) == 1 and
                  statuses[0].get('verdict_raw') == 'currently_true' and statuses[0].get('decision') == 'forwarded'
                  and len(receipts) == 1)
        if ok:
            return dict(attempt=attempt['attempt'], key=key, property_count=len(props),
                        official_verdict_raw=statuses[0].get('verdict_raw'),
                        guarded_receipt_monotonic_ns=receipts[0]['monotonic_ns'])
    return None


deadline = time.monotonic() + 90
ready = False
last = {}
while time.monotonic() < deadline:
    spin(.03)
    window = [s for s in samples if s[0] >= time.monotonic_ns() - 650_000_000]
    if len(window) < 3 or window[-1][0] - window[0][0] < 500_000_000:
        continue
    position_error = max(abs(p - e) for p, e in zip(window[-1][1], EXPECTED))
    drift = max(max(s[1][i] for s in window) - min(s[1][i] for s in window) for i in range(6))
    speed = max(abs(v) for s in window for v in s[2])
    increasing = all(a[3] < b[3] for a, b in zip(window, window[1:]))
    if position_error >= .0001 or drift >= .0001 or speed >= .001 or not increasing:
        continue
    if not (root / 'production.ready').exists() or not (root / 'resource_sampler.ready').exists():
        continue
    if (root / 'source.jsonl').exists() and (root / 'source.jsonl').stat().st_size:
        continue  # source index zero until the barrier
    if (MODE in ('b1', 'b3') or (MODE == 'b2' and COMPOSED)) and not (root / 'stop_adapter.ready').exists():
        continue
    if MODE == 'b2' and not (root / 'ovr_nodes.ready').exists():
        continue
    clocks = participant_clocks()
    if clocks is None:
        continue
    res = rows(root / 'resource_samples.jsonl')
    recent = next((r for r in reversed(res or []) if r.get('kind') == 'sample'), None)
    if recent is None or not all(recent['targets'].get(label, {}).get('status') == 'OBSERVED' for label in clocks):
        continue
    g = graph()
    pose_pub = ['ovr_lossless_stripper'] if MODE == 'b2' else ['quest_teleop_node']
    ok = g['/servo_node/pose_target_cmds']['publishers'] == pose_pub
    ok &= {'servo_node', 'cp1_recorder'} <= set(g['/servo_node/pose_target_cmds']['subscriptions'])
    ok &= 'servo_node' in g['/ur5_arm_controller/joint_trajectory']['publishers']
    ok &= {'ur5_arm_controller', 'cp1_recorder'} <= set(g['/ur5_arm_controller/joint_trajectory']['subscriptions'])
    ok &= len(g['/joint_states']['publishers']) >= 1
    if MODE == 'b2':
        ok &= g['/s4b/ovr/envelope_mon']['publishers'] == ['quest_teleop_node']
        ok &= 'ovr_full_guard' in g['/s4b/ovr/envelope_mon']['subscriptions']
        ok &= g['/s4b/ovr/envelope']['publishers'] == ['ovr_full_guard']
        ok &= 'ovr_lossless_stripper' in g['/s4b/ovr/envelope']['subscriptions']
    if not ok:
        continue
    services = dict(node.get_service_names_and_types())
    if '/servo_node/pause_servo' not in services:
        continue
    states = controller_states()
    if states.get('joint_state_broadcaster') != 'active' or states.get('ur5_arm_controller') != 'active':
        continue
    if 'success=True' not in (root / 'servo_mode.txt').read_text():
        continue
    cal = None
    if MODE == 'b2':
        cal = calibration_ack()
        if cal is None:
            continue
        (root / 'calibration.ack').write_text(json.dumps(cal, sort_keys=True) + '\n')
    last = dict(position_error=position_error, drift=drift, speed=speed, joint_samples=len(window),
                increasing_stamps=increasing, graph=g, controllers=states, participant_clocks=clocks,
                source_path_calibration=cal, servo_mode=(root / 'servo_mode.txt').read_text().strip()[-200:])
    ready = True
    break

if not ready:
    event('readiness_failed', samples=len(samples), graph=graph(), controllers=controller_states(),
          clocks_ok=participant_clocks() is not None)
    raise SystemExit(12)
event('readiness_ack', **last)
(root / 'recorder.ready').write_text('ACK complete\n')
start_ns = time.monotonic_ns() + 1_000_000_000
(root / 'barrier.json').write_text(json.dumps(dict(release_monotonic_ns=time.monotonic_ns(),
                                                  start_monotonic_ns=start_ns, source_index=0)))
event('barrier_release', start_monotonic_ns=start_ns)
end_ns = start_ns + CAPTURE_NS
while time.monotonic_ns() < end_ns:
    spin(.01)
(root / 'capture_end.ready').write_text('capture ended\n')
event('capture_end', source_records=sum(1 for _ in (root / 'source.jsonl').open()) if (root / 'source.jsonl').exists() else None)
node.destroy_node()
rclpy.shutdown()
