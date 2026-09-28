"""No-Gazebo D4 component test of the GENUINE official monitor + TLOracle path.

Envelopes carrying registered source ages go through the generated monitor and
the official oracle with the D4 property dependency (d1_contract freshness from
XR_FRESHNESS_NS). Checks official property safe, official status decision and
guarded receipt per event. Not a B2 efficacy result.
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

from d1_contract import FRESHNESS_NS, canonical, make_envelope

parser = argparse.ArgumentParser()
parser.add_argument('--regime', choices=('native', 'full'), required=True)
args = parser.parse_args()
root = Path(os.environ['TRIAL_ROOT'])
root.mkdir(parents=True, exist_ok=True)
os.environ['INFO_REGIME'] = args.regime
os.environ['XR_D3_PROPERTY_LOG'] = str(root / 'property.jsonl')
status_path = root / ('monitor_full_status.jsonl' if args.regime == 'full' else 'monitor_native_status.jsonl')
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
    out, err = (root / f'{label}.stdout').open('w'), (root / f'{label}.stderr').open('w')
    process = subprocess.Popen(argv, stdout=out, stderr=err, start_new_session=True, env=os.environ.copy())
    children.append((process, out, err))
    return process


def spin_until(predicate, seconds=5):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        rclpy.spin_once(node, timeout_sec=.01)
        if predicate():
            return True
    return False


rclpy.init()
node = Node('d4_official_monitor_freshness_preflight')
source = node.create_publisher(source_type, source_root + '_mon', 20)
tick_pub = node.create_publisher(String, '/s4b/d3/tick_mon', 20)
received = []
node.create_subscription(source_type, source_root,
                         lambda msg: received.append(message_to_ordereddict(msg)), 20)
node.create_subscription(String, '/s4b/d3/tick', lambda msg: None, 20)
F = FRESHNESS_NS
# (label, age_ns or special, teleop, expected_safe)
CASES = [('fresh_age_0', 0, True, True), ('fresh_below_F', F - 20_000_000, True, True),
         ('stale_above_F', F + 30_000_000, True, False), ('future_plus_1s', -1_000_000_000, True, False),
         ('historical_epoch_1p0', 'H', True, False), ('ungripped_stale', F + 30_000_000, False, True),
         ('original_neutral', None, False, True)]
result = dict(regime=args.regime, freshness_ns=F, monitor_id=monitor_id,
              official_revision='d03aa5b44e29b76c0e108a098817bdf5aa98e322', cases=[])
try:
    oracle = start('oracle', ['python3', '-u', '/official/oracle/TLOracle/oracle.py', '--online',
                              '--discrete', '--property', 'd3_tloracle_property', '--port', port])
    monitor = start('monitor', ['ros2', 'run', 'monitor', monitor_id])
    if not spin_until(lambda: source.get_subscription_count() >= 1 and
                      node.get_publishers_info_by_topic(source_root) and
                      any(r.get('status') == 'started' for r in read_rows(status_path)) and
                      oracle.poll() is None and monitor.poll() is None, 15):
        raise RuntimeError('official monitor/oracle DDS ACK missing')
    for n, (label, age, teleop, expect) in enumerate(CASES):
        msg = ReceivedPoseStates()
        msg.header.stamp = node.get_clock().now().to_msg()  # new ROS stamp: must NOT be used for age
        msg.header.frame_id = 'unity_world'
        msg.source = 'stale_timeout' if age is None else 'd4_component'
        msg.tracked = age is not None
        msg.teleop_enable = teleop
        fields = message_to_ordereddict(msg)
        before = len(received)
        now = time.monotonic_ns()
        if args.regime == 'full':
            if age is None:
                selected = {'origin': 'ORIGINAL_NEUTRAL', 'reason': 'stale_timeout'}
            else:
                stamp_ns = 1_000_000_000 if age == 'H' else now - age
                selected = {'sample_id': f'component:{n}', 'generation_id': 1,
                            'source_timestamp_ns': stamp_ns, 'receiver_receipt_monotonic_ns': now,
                            'native_state': {'isTracked': True}}
            source.publish(String(data=canonical(make_envelope(fields, selected, now))))
        else:
            source.publish(msg)
        spin_until(lambda: len([r for r in read_rows(status_path) if r.get('status') == 'event'
                                and r.get('interface') != '/s4b/d3/tick']) >= n + 1, 5)
        spin_until(lambda: len(received) > before, .5)
        props = [r for r in read_rows(root / 'property.jsonl') if r.get('event_kind') != 'tick']
        stats = [r for r in read_rows(status_path) if r.get('status') == 'event'
                 and r.get('interface') != '/s4b/d3/tick']
        prop, stat = props[n], stats[n]
        forwarded = len(received) > before
        if args.regime == 'native':
            expect = True   # I_NATIVE: no source time available; wire-only predicate
        ok = (prop['safe'] is expect and stat.get('decision') == ('forwarded' if expect else 'blocked')
              and forwarded is expect)
        result['cases'].append(dict(label=label, expected_safe=expect, property_safe=prop['safe'],
                                    reason=prop['reason'], official_decision=stat.get('decision'),
                                    verdict_raw=stat.get('verdict_raw'), guarded_receipt=forwarded, ok=ok))
    result['status'] = ('PASS_COMPONENT_PREFLIGHT' if all(c['ok'] for c in result['cases'])
                        else 'FAIL_COMPONENT_PREFLIGHT')
except Exception as error:  # noqa: BLE001 retained as evidence
    result.update(status='FAIL_COMPONENT_PREFLIGHT', error=repr(error))
finally:
    for process, out, err in reversed(children):
        if process.poll() is None:
            os.killpg(process.pid, signal.SIGTERM)
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
        out.close()
        err.close()
    node.destroy_node()
    rclpy.shutdown()
    (root / 'summary.json').write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
print(json.dumps({k: result.get(k) for k in ('regime', 'freshness_ns', 'status', 'error')}))
print(json.dumps([(c['label'], c['ok'], c['reason'], c['official_decision']) for c in result['cases']]))
if result['status'] != 'PASS_COMPONENT_PREFLIGHT':
    raise SystemExit(1)
