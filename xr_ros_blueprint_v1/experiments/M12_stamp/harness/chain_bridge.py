#!/usr/bin/env python3
"""M12 chain bridge = a generic deployment republisher between the app and the gate (/m12/app_cmd -> /m12/bridge_out).
Normal: forwards every app message unchanged (header.stamp and frame_id preserved), so a stamp-age check gets its
best case. Fault injection inside the window [W0, W1) (s after T0), selected by MODE:
  PASS         no fault
  DELAY        each message held DELAY_S (sim clock) then forwarded unchanged  -> truth: stale (transport delay)
  CACHE        incoming messages dropped; the last pre-window message republished at 20 Hz with header.stamp = now
               (content and frame_id unchanged)                              -> truth: stale (cache republish)
  KEEPALIVE    if no app message for > 0.1 s, the last message is republished every 50 ms with header.stamp = now
               (as latest-wins republishers do)                                -> truth: stale
Every output gets '|bid=N' appended to frame_id (output id for the ground-truth join; gates must not use it) and a
log line {bid, t, label, src_stamp, out_stamp, frame}. Clock: node clock (use_sim_time true). Args: <log> <mode> <end_s>"""
import json, os, sys, time, collections
import rclpy
from rclpy.parameter import Parameter
from geometry_msgs.msg import PoseStamped
LOG, MODE, END = sys.argv[1], sys.argv[2], float(sys.argv[3]); W0, W1, DELAY_S = 6.0, 7.5, 0.25
T0 = int(os.environ["P1_T0_NS"]) / 1e9
rclpy.init(); n = rclpy.create_node("m12_chain_bridge", parameter_overrides=[Parameter("use_sim_time", value=True)])
pub = n.create_publisher(PoseStamped, "/m12/bridge_out", 50); out = open(LOG, "w", buffering=1)
st = {"bid": 0, "last": None, "last_rx": None, "q": collections.deque(), "cache_t": 0.0}
def rel(): return time.time() - T0
def emit(m, label, restamp):
    o = PoseStamped(); o.pose = m.pose; o.header.frame_id = m.header.frame_id
    o.header.stamp = n.get_clock().now().to_msg() if restamp else m.header.stamp
    st["bid"] += 1; o.header.frame_id = "%s|bid=%d" % (m.header.frame_id, st["bid"]); pub.publish(o)
    out.write(json.dumps({"bid": st["bid"], "t": rel(), "label": label, "src_stamp": m.header.stamp.sec + m.header.stamp.nanosec * 1e-9,
                          "out_stamp": o.header.stamp.sec + o.header.stamp.nanosec * 1e-9, "frame": m.header.frame_id,
                          "p": [m.pose.position.x, m.pose.position.y, m.pose.position.z]}) + "\n")
def inwin(): return W0 <= rel() < W1
def on_msg(m):
    st["last_rx"] = time.time()
    if MODE == "DELAY" and inwin():
        st["q"].append((n.get_clock().now().nanoseconds / 1e9 + DELAY_S, m)); return
    if MODE == "CACHE" and inwin():
        return
    st["last"] = m; emit(m, "fresh", False)
def tick():
    now_s = n.get_clock().now().nanoseconds / 1e9
    while st["q"] and st["q"][0][0] <= now_s:
        _, m = st["q"].popleft(); st["last"] = m; emit(m, "stale_delay", False)
    if MODE == "CACHE" and inwin() and st["last"] is not None and time.time() - st["cache_t"] >= 0.05:
        st["cache_t"] = time.time(); emit(st["last"], "stale_cache", True)
    if MODE == "KEEPALIVE" and st["last"] is not None and st["last_rx"] is not None and time.time() - st["last_rx"] > 0.1 \
            and time.time() - st["cache_t"] >= 0.05:
        st["cache_t"] = time.time(); emit(st["last"], "stale_keepalive", True)
    if rel() > END: raise SystemExit(0)
n.create_subscription(PoseStamped, "/m12/app_cmd", on_msg, 50); n.create_timer(0.005, tick)
try: rclpy.spin(n)
except (SystemExit, KeyboardInterrupt, rclpy.executors.ExternalShutdownException): pass
