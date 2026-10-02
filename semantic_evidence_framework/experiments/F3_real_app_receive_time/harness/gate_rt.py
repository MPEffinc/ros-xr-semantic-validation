#!/usr/bin/env python3
"""F3 receive-time-state gate (the only claim admissible for this app, results/F2_TIMESTAMP_REVIEW.md).
Admit a command iff, at the gate's own receive time, the latest runtime evidence for the bound client is <= 50 ms old
and shows FOCUSED and IO_ACTIVE and not INPUTS_BLOCKED. The command stamp is NOT used for the decision; it is logged.
Args: <fifo> <out.jsonl> <t0> <bound_client_name> <end_s>"""
import json, sys, threading, time
import rclpy
from geometry_msgs.msg import PoseStamped
FIFO, OUT, T0, BOUND, END = sys.argv[1], sys.argv[2], float(sys.argv[3]), sys.argv[4], float(sys.argv[5])
EV_FRESH = 0.050
latest = {'t': None, 'ok': False, 'flags': None}; lock = threading.Lock()
def reader():
    with open(FIFO) as f:
        for line in f:
            try: d = json.loads(line)
            except ValueError: continue
            if d.get('name') != BOUND: continue
            ok = bool(d['focused']) and bool(d['io']) and not bool(d['inputs_blocked'])
            with lock: latest.update(t=d['wall'], ok=ok, flags=d['flags'])
threading.Thread(target=reader, daemon=True).start()
rclpy.init(); node = rclpy.create_node('f3_gate')
pub = node.create_publisher(PoseStamped, '/servo_node/pose_target_cmds', 10); out = open(OUT, 'w', buffering=1)
def on_cmd(m):
    r = time.time()
    with lock: t, ok, fl = latest['t'], latest['ok'], latest['flags']
    adm = t is not None and (r - t) <= EV_FRESH and ok
    if adm: pub.publish(m)
    out.write(json.dumps({"t_recv": r, "stamp": m.header.stamp.sec + m.header.stamp.nanosec * 1e-9, "ev_age": None if t is None else r - t,
                          "ev_ok": ok, "flags": fl, "admit": adm, "p": [m.pose.position.x, m.pose.position.y, m.pose.position.z]}) + "\n")
node.create_subscription(PoseStamped, '/f3/app_cmd', on_cmd, 10)
while time.time() - T0 < END: rclpy.spin_once(node, timeout_sec=0.01)
