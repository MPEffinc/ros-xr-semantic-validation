#!/usr/bin/env python3
"""Trial-owned, no-Gazebo neutral path test for the genuine generated monitor.

This is a component preflight, not an original-receiver or defense result.
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

from d1_contract import canonical, make_envelope, payload_hash

parser = argparse.ArgumentParser()
parser.add_argument('--regime', choices=('native', 'full'), required=True)
args = parser.parse_args()
root = Path(os.environ['TRIAL_ROOT'])
root.mkdir(parents=True, exist_ok=True)
os.environ['XR_D1_PROPERTY_LOG'] = str(root / 'property.jsonl')
status_file = root / ('monitor_full_status.jsonl' if args.regime == 'full'
                      else 'monitor_native_status.jsonl')
input_topic = '/s4b/d1/envelope_mon' if args.regime == 'full' else '/s4b/d1/native_input_mon'
output_topic = '/s4b/d1/envelope' if args.regime == 'full' else '/s4b/d1/native_input'
wire_type = String if args.regime == 'full' else ReceivedPoseStates
monitor_id = 'd1_full_guard' if args.regime == 'full' else 'd1_native_guard'
port = '18841' if args.regime == 'full' else '18842'
children = []

def start(name, argv):
    stdout = (root / f'{name}.stdout').open('w')
    stderr = (root / f'{name}.stderr').open('w')
    process = subprocess.Popen(argv, stdout=stdout, stderr=stderr,
                               start_new_session=True, env=os.environ.copy())
    children.append((process, stdout, stderr))
    return process

def rows(path):
    if not path.exists():
        return []
    try:
        return [json.loads(line) for line in path.read_text().splitlines() if line]
    except json.JSONDecodeError:
        return []

rclpy.init()
node = Node('cp8_monitor_path_preflight')
pub = node.create_publisher(wire_type, input_topic, 20)
received = []
def on_output(message):
    if args.regime == 'full':
        fields = json.loads(message.data)['original_payload']
    else:
        fields = message_to_ordereddict(message)
    received.append({'monotonic_ns': time.monotonic_ns(),
                     'payload_sha256': payload_hash(fields)})
node.create_subscription(wire_type, output_topic, on_output, 20)
attempted = []
result = {'regime': args.regime, 'input_topic': input_topic,
          'output_topic': output_topic, 'phases': []}
try:
    oracle = start('oracle', ['python3', '-u', '/official/oracle/TLOracle/oracle.py',
                              '--online', '--discrete', '--property',
                              'd1_tloracle_property', '--port', port])
    monitor = start('monitor', ['ros2', 'run', 'monitor', monitor_id])
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        rclpy.spin_once(node, timeout_sec=.01)
        started = any(row.get('status') == 'started' for row in rows(status_file))
        subscribers = pub.get_subscription_count()
        output_publishers = node.get_publishers_info_by_topic(output_topic)
        if started and subscribers >= 1 and output_publishers:
            result['dds_ack'] = {'monotonic_ns': time.monotonic_ns(),
                                 'input_subscription_count': subscribers,
                                 'output_publishers': [x.node_name for x in output_publishers]}
            break
        if oracle.poll() is not None or monitor.poll() is not None:
            raise RuntimeError('oracle or monitor exited before DDS ACK')
    else:
        raise RuntimeError('official monitor DDS ACK timeout')

    for phase in ('before_barrier', 'after_barrier'):
        first = len(received)
        phase_attempted = []
        for i in range(10):
            message = ReceivedPoseStates()
            message.header.stamp = node.get_clock().now().to_msg()
            message.header.frame_id = 'unity_world'
            message.source = 'stale_timeout'
            message.tracked = False
            message.teleop_enable = False
            fields = message_to_ordereddict(message)
            digest = payload_hash(fields)
            selected = {'origin': 'ORIGINAL_NEUTRAL',
                        'phase': phase, 'index': i}
            if args.regime == 'full':
                envelope = make_envelope(fields, selected, time.monotonic_ns())
                pub.publish(String(data=canonical(envelope)))
            else:
                pub.publish(message)
            row = {'phase': phase, 'index': i, 'monotonic_ns': time.monotonic_ns(),
                   'payload_sha256': digest,
                   'dds_subscription_count': pub.get_subscription_count()}
            attempted.append(row)
            phase_attempted.append(row)
            rclpy.spin_once(node, timeout_sec=.01)
        deadline = time.monotonic() + 5
        while len(received) - first < 10 and time.monotonic() < deadline:
            rclpy.spin_once(node, timeout_sec=.01)
        result['phases'].append({'phase': phase, 'attempted': len(phase_attempted),
                                 'received': len(received) - first})
        if len(received) - first != 10:
            raise AssertionError(f'{phase}: output receipt {len(received)-first}/10')
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        rclpy.spin_once(node, timeout_sec=.01)
        properties = rows(root / 'property.jsonl')
        statuses = [r for r in rows(status_file) if r.get('status') == 'event']
        if len(properties) >= 20 and len(statuses) >= 20:
            break
    properties = rows(root / 'property.jsonl')
    statuses = [r for r in rows(status_file) if r.get('status') == 'event']
    result.update(attempted=attempted, received=received,
                  property_count=len(properties), status_count=len(statuses),
                  property_safe_count=sum(r.get('safe') is True for r in properties),
                  forwarded_count=sum(r.get('decision') == 'forwarded' for r in statuses))
    if (len(received), len(properties), len(statuses), result['property_safe_count'],
            result['forwarded_count']) != (20, 20, 20, 20, 20):
        raise AssertionError('full neutral monitor/oracle/receipt association failed')
    if sorted(x['payload_sha256'] for x in attempted) != sorted(x['payload_sha256'] for x in received):
        raise AssertionError('neutral payload receipt set differs from attempted set')
    result['status'] = 'PASS_COMPONENT_PREFLIGHT'
except Exception as error:
    result['status'] = 'FAIL_COMPONENT_PREFLIGHT'
    result['error'] = repr(error)
finally:
    for process, stdout, stderr in reversed(children):
        if process.poll() is None:
            os.killpg(process.pid, signal.SIGTERM)
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait(timeout=3)
        stdout.close()
        stderr.close()
    node.destroy_node()
    rclpy.shutdown()
    (root / 'summary.json').write_text(json.dumps(result, indent=2, sort_keys=True))
print(json.dumps({'status': result['status'], 'regime': args.regime,
                  'phases': result['phases'], 'property_count': result.get('property_count')},
                 sort_keys=True))
if result['status'] != 'PASS_COMPONENT_PREFLIGHT':
    raise SystemExit(1)
