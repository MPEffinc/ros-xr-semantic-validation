"""No-Gazebo official monitor+oracle source/tick component test, not B2 efficacy."""
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

parser = argparse.ArgumentParser()
parser.add_argument('--regime', choices=('native', 'full'), required=True)
args = parser.parse_args()
root = Path(os.environ['TRIAL_ROOT'])
root.mkdir(parents=True, exist_ok=True)
os.environ['INFO_REGIME'] = args.regime
os.environ['XR_D3_PROPERTY_LOG'] = str(root / 'property.jsonl')
status_path = root / ('monitor_full_status.jsonl' if args.regime == 'full'
                      else 'monitor_native_status.jsonl')
source_type = String if args.regime == 'full' else ReceivedPoseStates
source_root = '/s4b/d1/envelope' if args.regime == 'full' else '/s4b/d1/native_input'
monitor_id = 'd3_full_guard' if args.regime == 'full' else 'd3_native_guard'
port = '18841' if args.regime == 'full' else '18842'
children = []


def read_rows(path):
    if not path.exists():
        return []
    try:
        return [json.loads(line) for line in path.read_text().splitlines() if line]
    except json.JSONDecodeError:
        return []


def start(label, argv):
    stdout = (root / f'{label}.stdout').open('w')
    stderr = (root / f'{label}.stderr').open('w')
    process = subprocess.Popen(argv, stdout=stdout, stderr=stderr,
                               start_new_session=True, env=os.environ.copy())
    children.append((process, stdout, stderr))
    return process


def spin_until(predicate, seconds=5):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        rclpy.spin_once(node, timeout_sec=.01)
        if predicate():
            return True
    return False


rclpy.init()
node = Node('d3_official_monitor_tick_preflight')
source = node.create_publisher(source_type, source_root + '_mon', 20)
tick_pub = node.create_publisher(String, '/s4b/d3/tick_mon', 20)
source_out = []
tick_out = []
node.create_subscription(source_type, source_root,
    lambda msg: source_out.append((time.monotonic_ns(), message_to_ordereddict(msg))), 20)
node.create_subscription(String, '/s4b/d3/tick',
    lambda msg: tick_out.append((time.monotonic_ns(), json.loads(msg.data))), 20)
result = {'regime': args.regime, 'monitor_id': monitor_id,
          'official_revision': 'd03aa5b44e29b76c0e108a098817bdf5aa98e322'}
try:
    oracle = start('oracle', ['python3', '-u', '/official/oracle/TLOracle/oracle.py',
                              '--online', '--discrete', '--property',
                              'd3_tloracle_property', '--port', port])
    monitor = start('monitor', ['ros2', 'run', 'monitor', monitor_id])

    def ready():
        statuses = read_rows(status_path)
        return (source.get_subscription_count() >= 1 and
                tick_pub.get_subscription_count() >= 1 and
                node.get_publishers_info_by_topic(source_root) and
                node.get_publishers_info_by_topic('/s4b/d3/tick') and
                any(row.get('status') == 'started' for row in statuses) and
                oracle.poll() is None and monitor.poll() is None)

    if not spin_until(ready, 15):
        raise RuntimeError('official source+tick monitor/oracle DDS ACK missing')
    result['dds_ack'] = {'source_subscriptions': source.get_subscription_count(),
                         'tick_subscriptions': tick_pub.get_subscription_count(),
                         'monotonic_ns': time.monotonic_ns()}

    def send_source(sample_id, active, neutral=False):
        msg = ReceivedPoseStates()
        msg.header.stamp = node.get_clock().now().to_msg()
        msg.header.frame_id = 'unity_world'
        msg.source = 'stale_timeout' if neutral else 'cp11_component'
        msg.tracked = not neutral
        msg.teleop_enable = active
        fields = message_to_ordereddict(msg)
        now_ns = None
        if args.regime == 'full':
            now_ns = time.monotonic_ns()
            selected = ({'origin': 'ORIGINAL_NEUTRAL', 'reason': 'stale_timeout'}
                        if neutral else {'sample_id': sample_id, 'generation_id': 1,
                                         'source_timestamp_ns': now_ns,
                                         'receiver_receipt_monotonic_ns': now_ns,
                                         'native_state': {'isTracked': True}})
            envelope = make_envelope(fields, selected, now_ns + 1)
            source.publish(String(data=canonical(envelope)))
        else:
            source.publish(msg)
        return fields, now_ns

    active_fields, active_receipt_ns = send_source('component:55', True)
    if not spin_until(lambda: len(source_out) >= 1):
        raise AssertionError('active source not forwarded')
    # Repeated cached publication has the same source ID/receipt time.
    if args.regime == 'full':
        repeated = dict(active_fields)
        selected = {'sample_id': 'component:55', 'generation_id': 1,
                    'source_timestamp_ns': active_receipt_ns,
                    'receiver_receipt_monotonic_ns': active_receipt_ns,
                    'native_state': {'isTracked': True}}
        source.publish(String(data=canonical(make_envelope(repeated, selected,
                                                           time.monotonic_ns()))))
        if not spin_until(lambda: len(source_out) >= 2):
            raise AssertionError('repeated active source not forwarded')
    neutral_fields, _ = send_source(None, False, neutral=True)
    expected_source_receipts = 3 if args.regime == 'full' else 2
    if not spin_until(lambda: len(source_out) >= expected_source_receipts):
        raise AssertionError('original neutral not forwarded')

    sent_ticks = []
    tick_start_ns = time.monotonic_ns()
    for index in range(30):
        scheduled_ns = tick_start_ns + index * 20_000_000
        while time.monotonic_ns() < scheduled_ns:
            rclpy.spin_once(node, timeout_sec=.001)
        tick = {'kind': 'health_tick', 'tick_id': f'tick:{index}',
                'tick_monotonic_ns': time.monotonic_ns(),
                'source_sample_id': None, 'source_receipt_ns': None}
        tick_pub.publish(String(data=json.dumps(tick, sort_keys=True)))
        sent_ticks.append(tick)
        rclpy.spin_once(node, timeout_sec=.001)
    if not spin_until(lambda: len([row for row in read_rows(root / 'property.jsonl')
                                   if row.get('event_kind') == 'tick']) >= 30 and
                      len([row for row in read_rows(status_path)
                           if row.get('status') == 'event' and
                           (row.get('event') or {}).get('topic') == '/s4b/d3/tick']) >= 30):
        raise AssertionError('not all 30 tick property/status events observed')

    properties = read_rows(root / 'property.jsonl')
    status_rows = read_rows(status_path)
    tick_properties = [row for row in properties if row.get('event_kind') == 'tick']
    tick_status = [row for row in status_rows if row.get('status') == 'event' and
                   (row.get('event') or {}).get('topic') == '/s4b/d3/tick']
    source_properties = [row for row in properties
                         if row.get('event_kind') == 'source_or_original_output']
    assert len(tick_properties) == 30 and len(tick_status) == 30
    assert {row['tick_id'] for row in tick_properties} == {row['tick_id'] for row in sent_ticks}
    assert len(source_properties) == expected_source_receipts
    assert all(row['safe'] is True for row in source_properties)
    blocked = [row for row in tick_status if row.get('decision') == 'blocked']
    if args.regime == 'full':
        assert blocked and any(row['safe'] is False for row in tick_properties)
        assert len(tick_out) == 30 - len(blocked)
    else:
        assert not blocked and len(tick_out) == 30
        assert all(row['reason'] == 'UNOBSERVABLE_SOURCE_RECEIPT_I_NATIVE'
                   for row in tick_properties)
    result.update(status='PASS_COMPONENT_PREFLIGHT', source_receipts=len(source_out),
                  source_property_rows=len(source_properties),
                  tick_sent=len(sent_ticks), tick_property_rows=len(tick_properties),
                  tick_status_rows=len(tick_status), tick_blocked=len(blocked),
                  tick_forwarded=len(tick_out),
                  source_sample_count=1 if args.regime == 'full' else 'UNOBSERVABLE')
except Exception as error:
    result.update(status='FAIL_COMPONENT_PREFLIGHT', error=repr(error))
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
    (root / 'summary.json').write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
print(json.dumps({key: result.get(key) for key in ('regime', 'status', 'error',
    'source_receipts', 'tick_sent', 'tick_blocked', 'tick_forwarded')}, sort_keys=True))
if result['status'] != 'PASS_COMPONENT_PREFLIGHT':
    raise SystemExit(1)
