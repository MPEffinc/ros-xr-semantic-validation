"""No-Gazebo C-ID component test of the GENUINE official monitor + TLOracle path.

Bound envelopes (capture-time reference) go through the generated monitor and
official oracle with the C-ID property branch. Checks official property safe
and reason, official status decision and guarded receipt for each event.
"""
import copy
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

from cid_binding import binding_hash, projection
from d1_contract import canonical, make_envelope

os.environ.update(CASE_ID='CID', INFO_REGIME='full')
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


def event(sid, x_bound, x_cmd, teleop, receipt, drop=None):
    msg = ReceivedPoseStates()
    msg.header.stamp = node.get_clock().now().to_msg()
    msg.header.frame_id = 'unity_world'
    msg.tracked, msg.teleop_enable = True, teleop
    msg.pose.position.x, msg.pose.position.y, msg.pose.position.z = x_cmd, .2, .3
    msg.pose.orientation.w = 1.0
    msg.grip_value = 1.0 if teleop else 0.0
    now = time.monotonic_ns()
    stamp = now - 1_000_000
    native = {'isTracked': True}
    meta = dict(sample_id=sid, generation_id=1, source_timestamp_ns=stamp, native_state=native,
                binding_sha256=binding_hash(sid, 1, stamp, native,
                                            projection(True, [x_bound, .2, .3], [0, 0, 0, 1], teleop, 1. if teleop else 0.)),
                receiver_receipt_monotonic_ns=receipt)
    if drop:
        meta.pop(drop)
    return make_envelope(message_to_ordereddict(msg), meta, now)


# (label, sid, x_bound, x_cmd, teleop, receipt_key, drop, expected_safe, expected_reason)
SEQ = [('valid', 'docker:40', .35, .35, True, 'r40', None, True, 'ARMED_VALID'),
       ('cached_repeat_same_ingestion', 'docker:40', .35, .35, True, 'r40', None, True, 'ARMED_VALID'),
       ('mismatch', 'docker:41', .35, .65, True, 'r41', None, False, 'STATE_COMMAND_MISMATCH'),
       ('missing_id', None, .35, .35, True, 'r42', 'sample_id', False, 'MISSING_SOURCE_EVENT_ID'),
       ('missing_generation', 'docker:43', .35, .35, True, 'r43', 'generation_id', False, 'MISSING_REQUIRED_FIELD'),
       ('duplicate_id_new_ingestion', 'docker:40', .35, .35, True, 'r44', None, False, 'DUPLICATE_SOURCE_EVENT_ID'),
       ('valid_but_latched', 'docker:45', .35, .35, True, 'r45', None, False, None),
       ('release_neutral', 'docker:46', .35, .35, False, 'r46', None, True, None)]
rclpy.init()
node = Node('cid_official_monitor_preflight')
source = node.create_publisher(String, '/s4b/d1/envelope_mon', 20)
received = []
node.create_subscription(String, '/s4b/d1/envelope', lambda m: received.append(m.data), 20)
result = dict(cases=[], official_revision='d03aa5b44e29b76c0e108a098817bdf5aa98e322')
try:
    oracle = start('oracle', ['python3', '-u', '/official/oracle/TLOracle/oracle.py', '--online', '--discrete',
                              '--property', 'd3_tloracle_property', '--port', '18841'])
    monitor = start('monitor', ['ros2', 'run', 'monitor', 'd3_full_guard'])
    if not spin_until(lambda: source.get_subscription_count() >= 1 and
                      node.get_publishers_info_by_topic('/s4b/d1/envelope') and
                      any(r.get('status') == 'started' for r in read_rows(status_path)), 15):
        raise RuntimeError('official monitor/oracle DDS ACK missing')
    keys = {}
    for n, (label, sid, xb, xc, teleop, rkey, drop, exp, reason) in enumerate(SEQ):
        receipt = keys.setdefault(rkey, time.monotonic_ns())
        before = len(received)
        source.publish(String(data=canonical(event(sid, xb, xc, teleop, receipt, drop))))
        spin_until(lambda: len([r for r in read_rows(status_path) if r.get('status') == 'event']) >= n + 1, 3)
        spin_until(lambda: len(received) > before, .05)
        prop = [r for r in read_rows(root / 'property.jsonl') if r.get('event_kind') != 'tick'][n]
        stat = [r for r in read_rows(status_path) if r.get('status') == 'event'][n]
        fwd = len(received) > before
        ok = (prop['safe'] is exp and fwd is exp and stat.get('decision') == ('forwarded' if exp else 'blocked')
              and (reason is None or prop['reason'] == reason))
        result['cases'].append(dict(label=label, expected_safe=exp, property_safe=prop['safe'], reason=prop['reason'],
                                    official_decision=stat.get('decision'), guarded_receipt=fwd, ok=ok))
        time.sleep(.05)
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
print(json.dumps({k: result.get(k) for k in ('status', 'error')}))
print(json.dumps([(c['label'], c['ok'], c['reason'], c['official_decision']) for c in result['cases']]))
if result['status'] != 'PASS_COMPONENT_PREFLIGHT':
    raise SystemExit(1)
