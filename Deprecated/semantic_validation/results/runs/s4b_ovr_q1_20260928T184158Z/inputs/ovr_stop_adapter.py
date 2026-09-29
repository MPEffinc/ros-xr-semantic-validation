"""Common OpenVR stop/hold (and defense-decided resume) integration; no XR predicate.

Identical contract for B1, B2-composed and B3. It never reads pose, validity,
source age, generation or recovery metadata; it only forwards each defense's own
explicit decisions:
  * a rejection (or official monitor health unknown/error) while running -> stop;
  * a missing verdict heartbeat for 250 ms while running -> stop (common watchdog);
  * the defense's first allowed grip-pressed source decision while stopped (which
    the defense only emits after its own re-arm) -> resume.
Stop = the CP1-qualified OPENVR_PAUSE_HOLD_FAST form: /servo_node/pause_servo
(std_srvs/SetBool true) then five measured-current-position JointTrajectory holds
(10 ms point duration, ~20 ms apart), revoking the controller's pending trajectory.
Never an absolute zero pose. Resume = pause_servo false.
"""
import json
import os
import time
from pathlib import Path

import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import JointState
from std_srvs.srv import SetBool
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint

root = Path(os.environ['TRIAL_ROOT'])
mode = os.environ['MODE']
NAMES = ['shoulder_pan_joint', 'shoulder_lift_joint', 'elbow_joint', 'wrist_1_joint', 'wrist_2_joint', 'wrist_3_joint']
if mode == 'b1':
    verdict_path = root / 'gate_verdict.jsonl'
elif mode == 'b3':
    verdict_path = root / 'lineage.jsonl'
elif mode == 'b2':
    verdict_path = root / 'monitor_full_status.jsonl'
else:
    raise SystemExit('stop adapter is only for B1/B2-composed/B3')
CAPTURE_NS = int(os.environ.get('XR_CAPTURE_NS', '12000000000'))

events = (root / 'stop_adapter.jsonl').open('a', buffering=1)


def emit(kind, **fields):
    events.write(json.dumps(dict(kind=kind, monotonic_ns=time.monotonic_ns(), **fields), sort_keys=True) + '\n')


rclpy.init()
node = Node('ovr_common_stop_adapter')
hold_pub = node.create_publisher(JointTrajectory, '/ur5_arm_controller/joint_trajectory', 10)
pause = node.create_client(SetBool, '/servo_node/pause_servo')
latest = {}


def on_joints(msg):
    try:
        latest['positions'] = [msg.position[msg.name.index(n)] for n in NAMES]
    except (ValueError, IndexError):
        pass


node.create_subscription(JointState, '/joint_states', on_joints, qos_profile_sensor_data)
deadline = time.monotonic() + 60
while time.monotonic() < deadline:
    rclpy.spin_once(node, timeout_sec=.01)
    if pause.wait_for_service(timeout_sec=.01) and hold_pub.get_subscription_count() >= 1 and 'positions' in latest:
        break
else:
    emit('readiness_failed', pause_available=pause.service_is_ready(), controller_subscribers=hold_pub.get_subscription_count())
    raise SystemExit(12)
emit('ready', verdict_source=mode, verdict_path=str(verdict_path))
(root / 'stop_adapter.ready').write_text('pause service, controller subscription and joint state matched\n')
while not (root / 'barrier.json').exists():
    rclpy.spin_once(node, timeout_sec=.01)
start_ns = json.loads((root / 'barrier.json').read_text())['start_monotonic_ns']
while time.monotonic_ns() < start_ns:
    rclpy.spin_once(node, timeout_sec=.001)
end_ns = start_ns + CAPTURE_NS


def call_pause(value, source):
    kind = 'stop' if value else 'resume'
    emit(kind + '_request', source=source)
    request = SetBool.Request()
    request.data = value
    future = pause.call_async(request)
    limit = time.monotonic() + 3
    while not future.done() and time.monotonic() < limit:
        rclpy.spin_once(node, timeout_sec=.005)
    ok = future.done() and future.result() is not None and future.result().success
    emit(kind + ('_reply' if ok else '_failed'), source=source, reply=str(future.result()) if future.done() else None)
    return ok


def hold(source):
    positions = list(latest['positions'])
    for index in range(5):
        msg = JointTrajectory()
        msg.joint_names = NAMES
        point = JointTrajectoryPoint()
        point.positions = positions
        point.velocities = [0.] * 6
        point.time_from_start.nanosec = 10_000_000
        msg.points = [point]
        hold_pub.publish(msg)
        emit('controller_hold', source=source, hold_index=index, positions=positions, duration_ns=10_000_000)
        limit = time.monotonic() + .02
        while time.monotonic() < limit:
            rclpy.spin_once(node, timeout_sec=.002)


def decision(row):
    """(is_event, allowed, grip_source_event) from the defense's own record."""
    if mode == 'b1':
        return True, row.get('allowed') is not False, bool(row.get('teleop'))
    if mode == 'b3':
        if row.get('kind') != 'b3_publish_check':
            return False, None, False
        return True, row.get('verdict') is True, bool(row.get('teleop'))
    if row.get('status') != 'event':
        return False, None, False
    try:
        env = json.loads(row['event']['data'])
    except (KeyError, TypeError, ValueError):
        return False, None, False
    if env.get('kind') == 'calibration':
        return False, None, False
    allowed = row.get('verdict_raw') not in ('unknown', 'error', 'currently_false') and row.get('decision') == 'forwarded'
    return True, allowed, bool((env.get('selected_origin') or {}).get('grip'))


def trigger_name(row, allowed):
    if mode != 'b2':
        return f'{mode.upper()}_POLICY_REJECT'
    return 'B2_MONITOR_HEALTH' if row.get('verdict_raw') in ('unknown', 'error') else 'B2_ORACLE_POLICY_REJECT'


running, cursor, last_event_ns = True, 0, time.monotonic_ns()
while time.monotonic_ns() < end_ns:
    rclpy.spin_once(node, timeout_sec=.005)
    fresh = []
    if verdict_path.exists():
        with verdict_path.open() as stream:
            stream.seek(cursor)
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
        is_event, allowed, grip = decision(row)
        if not is_event:
            continue
        last_event_ns = time.monotonic_ns()
        if running and allowed is False:
            source = trigger_name(row, allowed)
            emit('verdict_trigger', source=source, verdict=row)
            if call_pause(True, source):
                hold(source)
                running = False
        elif (not running) and allowed and grip:
            emit('resume_trigger', source='DEFENSE_ALLOWED_GRIP_AFTER_REARM', verdict=row)
            if call_pause(False, 'DEFENSE_REARM'):
                running = True
    if running and time.monotonic_ns() - last_event_ns > 250_000_000:
        source = f'{mode.upper()}_VERDICT_HEARTBEAT_MISSING'
        emit('health_trigger', source=source)
        if call_pause(True, source):
            hold(source)
            running = False
emit('capture_complete', running=running)
(root / 'stop_adapter.stopped').write_text('continuous mode complete\n')
while True:
    rclpy.spin_once(node, timeout_sec=.1)
