"""No-Gazebo genuine ROSMonitoring+oracle+guarded-subscriber probe.

Each invocation owns a fresh /results directory and one ROS domain. It does
not run a receiver, Servo, Gazebo, controller or physical robot.
"""
import argparse
import json
import os
import signal
import subprocess
import time
from pathlib import Path

import rclpy
from rclpy.node import Node
from rosidl_runtime_py.convert import message_to_ordereddict
from std_msgs.msg import String
from teleop_bridge_msgs.msg import ReceivedPoseStates

from d1_contract import canonical, make_envelope
from source_path_readiness import canonical_hash, exact_ack, read_rows

parser = argparse.ArgumentParser()
parser.add_argument('--regime', choices=('native', 'full'), required=True)
parser.add_argument('--scenario', choices=('positive', 'absent_oracle', 'absent_guarded_subscriber'),
                    required=True)
args = parser.parse_args()
root = Path('/results')
root.mkdir(parents=True, exist_ok=True)
os.environ['INFO_REGIME'] = args.regime
os.environ['XR_D3_PROPERTY_LOG'] = str(root / 'property.jsonl')
source_root = '/s4b/d1/envelope' if args.regime == 'full' else '/s4b/d1/native_input'
source_type = String if args.regime == 'full' else ReceivedPoseStates
monitor_id = 'd3_full_guard' if args.regime == 'full' else 'd3_native_guard'
port = '18841' if args.regime == 'full' else '18842'
status_path = root / ('monitor_full_status.jsonl' if args.regime == 'full'
                      else 'monitor_native_status.jsonl')
children = []
result = {'regime': args.regime, 'scenario': args.scenario,
          'official_revision': 'd03aa5b44e29b76c0e108a098817bdf5aa98e322',
          'source_path': source_root + '_mon', 'guarded_path': source_root}


def start(label, argv):
    stdout = (root / (label + '.stdout')).open('w')
    stderr = (root / (label + '.stderr')).open('w')
    proc = subprocess.Popen(argv, stdout=stdout, stderr=stderr,
                            start_new_session=True, env=os.environ.copy())
    children.append((proc, stdout, stderr))
    return proc


def spin_until(node, predicate, seconds):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        rclpy.spin_once(node, timeout_sec=.01)
        if predicate():
            return True
    return False


def log(kind, **fields):
    with (root / 'lineage.jsonl').open('a') as stream:
        stream.write(json.dumps(dict(kind=kind, monotonic_ns=time.monotonic_ns(),
                                     **fields), sort_keys=True) + '\n')


rclpy.init()
node = Node('q4_source_path_component')
publisher = node.create_publisher(source_type, source_root + '_mon', 20)
if args.scenario != 'absent_guarded_subscriber':
    def received(msg):
        if args.regime == 'full':
            envelope = json.loads(msg.data)
            log('monitor_output_received', regime='full',
                monitor_event_id=envelope['envelope_monotonic_ns'],
                original_payload_sha256=envelope['original_payload_sha256'])
        else:
            log('monitor_output_received', regime='native',
                payload_sha256=canonical_hash(message_to_ordereddict(msg)))
    node.create_subscription(source_type, source_root, received, 20)

try:
    if args.scenario != 'absent_oracle':
        start('oracle', ['python3', '-u', '/official/oracle/TLOracle/oracle.py',
                         '--online', '--discrete', '--property',
                         'd3_tloracle_property', '--port', port])
    start('monitor', ['ros2', 'run', 'monitor', monitor_id])
    def ready():
        status, problem = read_rows(status_path)
        return (not problem and publisher.get_subscription_count() >= 1 and
                any(x.get('status') == 'started' for x in status))
    if not spin_until(node, ready, 15):
        raise RuntimeError('official generated monitor did not report DDS match+started')
    result['dds_match_monotonic_ns'] = time.monotonic_ns()
    attempts = []
    selected = None
    limit = 8 if args.scenario == 'positive' else 1
    for index in range(1, limit + 1):
        msg = ReceivedPoseStates()
        msg.header.stamp = node.get_clock().now().to_msg()
        msg.header.frame_id = 'unity_world'
        msg.source = 'readiness_calibration'
        msg.tracked = False
        msg.teleop_enable = False
        fields = message_to_ordereddict(msg)
        created = time.monotonic_ns()
        if args.regime == 'full':
            envelope = make_envelope(fields, {'origin': 'ORIGINAL_NEUTRAL',
                                              'reason': 'readiness_calibration'}, created)
            key = envelope['envelope_monotonic_ns']
            wire = String(data=canonical(envelope))
        else:
            key = canonical_hash(fields)
            wire = msg
        record = dict(attempt=index, key=key, regime=args.regime,
                      created_monotonic_ns=created, native_payload=fields,
                      source_sample=False, control_input=False)
        with (root / 'calibration.jsonl').open('a') as stream:
            stream.write(json.dumps(record, sort_keys=True) + '\n')
        log('source_path_calibration_attempt', **record)
        publisher.publish(wire)
        log('source_path_calibration_publish_return', attempt=index, key=key,
            dds_subscription_count=publisher.get_subscription_count())
        limit_time = time.monotonic() + .45
        observed = {'ok': False, 'reason': 'NOT_OBSERVED'}
        while time.monotonic() < limit_time:
            rclpy.spin_once(node, timeout_sec=.01)
            observed = exact_ack(root, args.regime, record)
            if observed['ok']:
                selected = index
                break
        attempts.append(dict(attempt=index, key=key, result=observed))
        if selected is not None:
            break
    result['attempts'] = attempts
    result['selected_attempt'] = selected
    expected = args.scenario == 'positive'
    result['status'] = 'PASS_COMPONENT_PREFLIGHT' if bool(selected) == expected else 'FAIL_COMPONENT_PREFLIGHT'
    if args.scenario == 'absent_guarded_subscriber':
        result['negative_boundary'] = 'NO_GUARDED_SUBSCRIBER_RECEIPT'
    elif args.scenario == 'absent_oracle':
        result['negative_boundary'] = 'NO_ORACLE_PROPERTY_DECISION'
except Exception as exc:
    result['status'] = 'FAIL_COMPONENT_PREFLIGHT'
    result['error'] = repr(exc)
finally:
    for proc, stdout, stderr in reversed(children):
        if proc.poll() is None:
            os.killpg(proc.pid, signal.SIGTERM)
            try:
                proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                os.killpg(proc.pid, signal.SIGKILL)
                proc.wait(timeout=3)
        stdout.close()
        stderr.close()
    node.destroy_node()
    rclpy.shutdown()
    (root / 'summary.json').write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
print(json.dumps({key: result.get(key) for key in
                  ('regime', 'scenario', 'status', 'selected_attempt', 'error')}, sort_keys=True))
if result['status'] != 'PASS_COMPONENT_PREFLIGHT':
    raise SystemExit(1)
