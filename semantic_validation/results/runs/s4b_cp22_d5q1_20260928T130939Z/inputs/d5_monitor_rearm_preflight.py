"""No-Gazebo D5 component test of the GENUINE official monitor + TLOracle path.

A D5-shaped envelope sequence at 50 ms spacing goes through the generated
monitor and official oracle with the D5 re-arm property: valid gen-1 active,
receiver-dropped (connection open=false) cached copy, gen-2 held grip,
gen-1 replay, continued gen-2 held grip, release, rising edge. Checks official
property safe, official status decision and guarded receipt per event.
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

parser = argparse.ArgumentParser()
parser.add_argument('--policy', choices=('R_EXPLICIT', 'R_AUTO'), required=True)
args = parser.parse_args()
os.environ['XR_REARM_POLICY'] = args.policy
os.environ['CASE_ID'] = 'D5'
os.environ['INFO_REGIME'] = 'full'
root = Path(os.environ['TRIAL_ROOT'])
root.mkdir(parents=True, exist_ok=True)
os.environ['XR_D3_PROPERTY_LOG'] = str(root / 'property.jsonl')
status_path = root / 'monitor_full_status.jsonl'
children = []


def read_rows(path):
    try:
        return [json.loads(x) for x in path.read_text().splitlines() if x] if path.exists() else []
    except json.JSONDecodeError:
        return []


def start(label, argv):
    out, err = (root / f'{label}.stdout').open('w'), (root / f'{label}.stderr').open('w')
    proc = subprocess.Popen(argv, stdout=out, stderr=err, start_new_session=True, env=os.environ.copy())
    children.append((proc, out, err))
    return proc


def spin_until(pred, seconds=5):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        rclpy.spin_once(node, timeout_sec=.005)
        if pred():
            return True
    return False


# (label, generation, teleop, connection_open, expected_safe[policy])
SEQ = ([('gen1_active', 1, True, True, True)] +
       [('gen1_cached_after_drop', 1, True, False, False)] +
       [('gen2_held', 2, True, True, False)] * 2 +
       [('gen1_replay', 1, True, True, False)] +
       [('gen2_held_dwell', 2, True, True, False)] * 10 +     # 0..450 ms after replay
       [('gen2_held_dwell_boundary', 2, True, True, None)] +  # ~500 ms: jitter-sensitive, unscored
       [('gen2_held_after_dwell', 2, True, True, 'AUTO')] * 2 +
       [('gen2_release', 2, False, True, True)] * 3 +
       [('gen2_rising_edge', 2, True, True, True)] +
       [('gen2_armed', 2, True, True, True)] * 2)
rclpy.init()
node = Node('d5_official_monitor_rearm_preflight')
source = node.create_publisher(String, '/s4b/d1/envelope_mon', 20)
received = []
node.create_subscription(String, '/s4b/d1/envelope', lambda m: received.append(json.loads(m.data)), 20)
result = dict(policy=args.policy, cases=[], official_revision='d03aa5b44e29b76c0e108a098817bdf5aa98e322')
try:
    oracle = start('oracle', ['python3', '-u', '/official/oracle/TLOracle/oracle.py', '--online', '--discrete',
                              '--property', 'd3_tloracle_property', '--port', '18841'])
    monitor = start('monitor', ['ros2', 'run', 'monitor', 'd3_full_guard'])
    if not spin_until(lambda: source.get_subscription_count() >= 1 and
                      node.get_publishers_info_by_topic('/s4b/d1/envelope') and
                      any(r.get('status') == 'started' for r in read_rows(status_path)), 15):
        raise RuntimeError('official monitor/oracle DDS ACK missing')
    t0 = time.monotonic_ns()
    for n, (label, gen, teleop, open_, exp) in enumerate(SEQ):
        due = t0 + n * 50_000_000
        while time.monotonic_ns() < due:
            rclpy.spin_once(node, timeout_sec=.001)
        if exp == 'AUTO':
            exp = args.policy == 'R_AUTO'
        if args.policy == 'R_AUTO' and label in ('gen2_rising_edge', 'gen2_armed'):
            exp = True
        msg = ReceivedPoseStates()
        msg.header.stamp = node.get_clock().now().to_msg()
        msg.header.frame_id = 'unity_world'
        msg.source = 'd5_component'
        msg.tracked = True
        msg.teleop_enable = teleop
        now = time.monotonic_ns()
        selected = {'sample_id': f'component:{n}', 'generation_id': gen, 'source_timestamp_ns': now,
                    'receiver_receipt_monotonic_ns': now, 'native_state': {'isTracked': True},
                    'receiver_connection': {'index': 1 if gen == 1 else 2, 'open': open_}}
        before = len(received)
        source.publish(String(data=canonical(make_envelope(message_to_ordereddict(msg), selected, now))))
        spin_until(lambda: len([r for r in read_rows(status_path) if r.get('status') == 'event']) >= n + 1, 3)
        spin_until(lambda: len(received) > before, .03)
        prop = [r for r in read_rows(root / 'property.jsonl') if r.get('event_kind') != 'tick'][n]
        stat = [r for r in read_rows(status_path) if r.get('status') == 'event'][n]
        fwd = len(received) > before
        ok = True if exp is None else (prop['safe'] is exp and fwd is exp and
                                        stat.get('decision') == ('forwarded' if exp else 'blocked'))
        result['cases'].append(dict(n=n, label=label, expected_safe=exp, property_safe=prop['safe'],
                                    reason=prop['reason'], official_decision=stat.get('decision'),
                                    guarded_receipt=fwd, ok=ok))
    result['status'] = 'PASS_COMPONENT_PREFLIGHT' if all(c['ok'] for c in result['cases']) else 'FAIL_COMPONENT_PREFLIGHT'
except Exception as error:  # noqa: BLE001 retained as evidence
    result.update(status='FAIL_COMPONENT_PREFLIGHT', error=repr(error))
finally:
    for proc, out, err in reversed(children):
        if proc.poll() is None:
            os.killpg(proc.pid, signal.SIGTERM)
            try:
                proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                os.killpg(proc.pid, signal.SIGKILL)
        out.close()
        err.close()
    node.destroy_node()
    rclpy.shutdown()
    (root / 'summary.json').write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
print(json.dumps({k: result.get(k) for k in ('policy', 'status', 'error')}))
print(json.dumps([(c['label'], c['ok'], c['reason'], c['official_decision']) for c in result['cases']]))
if result['status'] != 'PASS_COMPONENT_PREFLIGHT':
    raise SystemExit(1)
