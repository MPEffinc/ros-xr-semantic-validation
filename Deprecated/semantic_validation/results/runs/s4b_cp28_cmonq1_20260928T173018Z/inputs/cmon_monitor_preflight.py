"""No-Gazebo C-MON component test of the GENUINE official monitor + TLOracle path.

Scenarios (--fault): HEALTHY (positive control), ORACLE_ABSENT (oracle never
started), ORACLE_DISCONNECT (SIGKILL mid-traffic), ORACLE_NONRESPONSIVE (SIGSTOP
mid-traffic). Bound, valid envelopes are published at 20 Hz throughout. For each
event: official status decision/verdict_raw, oracle_error statuses, guarded
receipt and publish-to-receipt latency. Measures the native behavior; it does not
presume fail-open.
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

from cid_binding import binding_hash, projection
from d1_contract import canonical, make_envelope

ap = argparse.ArgumentParser()
ap.add_argument('--fault', required=True, choices=['HEALTHY', 'ORACLE_ABSENT', 'ORACLE_DISCONNECT', 'ORACLE_NONRESPONSIVE'])
args = ap.parse_args()
os.environ.update(CASE_ID='CID', INFO_REGIME='full')
root = Path(os.environ['TRIAL_ROOT'])
root.mkdir(parents=True, exist_ok=True)
os.environ['XR_D3_PROPERTY_LOG'] = str(root / 'property.jsonl')
status_path = root / 'monitor_full_status.jsonl'
children = []
N, FAULT_AT = 40, 20


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


rclpy.init()
node = Node('cmon_official_monitor_preflight')
source = node.create_publisher(String, '/s4b/d1/envelope_mon', 20)
received = {}
node.create_subscription(String, '/s4b/d1/envelope',
                         lambda m: received.setdefault(json.loads(m.data)['envelope_monotonic_ns'], time.monotonic_ns()), 20)
result = dict(fault=args.fault, official_revision='d03aa5b44e29b76c0e108a098817bdf5aa98e322')
try:
    oracle = None
    if args.fault != 'ORACLE_ABSENT':
        oracle = start('oracle', ['python3', '-u', '/official/oracle/TLOracle/oracle.py', '--online', '--discrete',
                                  '--property', 'd3_tloracle_property', '--port', '18841'])
        time.sleep(1.0)
    monitor = start('monitor', ['ros2', 'run', 'monitor', 'd3_full_guard'])
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline and not (source.get_subscription_count() >= 1 and
                                               node.get_publishers_info_by_topic('/s4b/d1/envelope') and
                                               any(r.get('status') == 'started' for r in read_rows(status_path))):
        rclpy.spin_once(node, timeout_sec=.01)
    sent = []
    injected_ns = None
    t0 = time.monotonic_ns()
    for n in range(N):
        due = t0 + n * 50_000_000
        while time.monotonic_ns() < due:
            rclpy.spin_once(node, timeout_sec=.001)
        if n == FAULT_AT and args.fault in ('ORACLE_DISCONNECT', 'ORACLE_NONRESPONSIVE'):
            os.kill(oracle.pid, signal.SIGKILL if args.fault == 'ORACLE_DISCONNECT' else signal.SIGSTOP)
            injected_ns = time.monotonic_ns()
        msg = ReceivedPoseStates()
        msg.header.frame_id = 'unity_world'
        msg.tracked = msg.teleop_enable = True
        msg.pose.position.x, msg.pose.position.y, msg.pose.position.z = .35, .2, .3
        msg.pose.orientation.w, msg.grip_value = 1.0, 1.0
        now = time.monotonic_ns()
        sid = f'docker:{n}'
        meta = dict(sample_id=sid, generation_id=1, source_timestamp_ns=now, native_state={'isTracked': True},
                    receiver_receipt_monotonic_ns=now,
                    binding_sha256=binding_hash(sid, 1, now, {'isTracked': True},
                                                projection(True, [.35, .2, .3], [0, 0, 0, 1], True, 1.0)))
        env = make_envelope(message_to_ordereddict(msg), meta, now)
        source.publish(String(data=canonical(env)))
        sent.append(env['envelope_monotonic_ns'])
    end = time.monotonic() + 3
    while time.monotonic() < end:
        rclpy.spin_once(node, timeout_sec=.01)
    statuses = read_rows(status_path)
    events = {}
    for s in statuses:
        if s.get('status') == 'event':
            events[json.loads(s['event']['data'])['envelope_monotonic_ns']] = s
    per = []
    for n, key in enumerate(sent):
        st = events.get(key)
        per.append(dict(n=n, phase='pre' if n < FAULT_AT else 'post', status=None if st is None else st.get('decision'),
                        verdict_raw=None if st is None else st.get('verdict_raw'), received=key in received,
                        latency_ms=None if key not in received else (received[key] - key) / 1e6))
    pre = [p for p in per if p['phase'] == 'pre']
    post = [p for p in per if p['phase'] == 'post']
    result.update(injected_monotonic_ns=injected_ns, events=per,
                  oracle_error_statuses=sum(1 for s in statuses if s.get('status') == 'oracle_error'),
                  oracle_error_examples=[s.get('error') for s in statuses if s.get('status') == 'oracle_error'][:3],
                  pre=dict(forwarded=sum(p['status'] == 'forwarded' for p in pre),
                           verdicts=sorted({str(p['verdict_raw']) for p in pre}), received=sum(p['received'] for p in pre)),
                  post=dict(forwarded=sum(p['status'] == 'forwarded' for p in post), blocked=sum(p['status'] == 'blocked' for p in post),
                            no_status=sum(p['status'] is None for p in post),
                            verdicts=sorted({str(p['verdict_raw']) for p in post}), received=sum(p['received'] for p in post),
                            max_latency_ms=max((p['latency_ms'] for p in post if p['latency_ms'] is not None), default=None)),
                  monitor_log_could_not_connect='could not connect to oracle' in (root / 'monitor.stderr').read_text()
                  + (root / 'monitor.stdout').read_text())
    healthy_ok = (all(p['status'] == 'forwarded' and p['received'] for p in per[:FAULT_AT]) and
                  result['pre']['verdicts'] == (['currently_true'] if args.fault != 'ORACLE_ABSENT' else ['unknown']))
    result['status'] = 'MEASURED' if healthy_ok else 'PRE_FAULT_PATH_NOT_AS_EXPECTED'
except Exception as error:  # noqa: BLE001 retained as evidence
    result.update(status='FAILED', error=repr(error))
finally:
    for proc, out, err in reversed(children):
        if proc.poll() is None:
            try:
                os.killpg(proc.pid, signal.SIGCONT)
                os.killpg(proc.pid, signal.SIGTERM)
                proc.wait(timeout=3)
            except (subprocess.TimeoutExpired, ProcessLookupError):
                try:
                    os.killpg(proc.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
        out.close()
        err.close()
    node.destroy_node()
    rclpy.shutdown()
    (root / 'summary.json').write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
print(json.dumps({k: result.get(k) for k in ('fault', 'status', 'error', 'pre', 'post', 'oracle_error_statuses',
                                              'oracle_error_examples', 'monitor_log_could_not_connect')}))
