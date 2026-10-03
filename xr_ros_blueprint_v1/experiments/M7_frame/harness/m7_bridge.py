#!/usr/bin/env python3
"""M7 bridge (deployment republisher; fault injection in the window 6.0-7.5 s after T0):
  PASS     forward unchanged
  DELAY    hold each message 80 ms (sim) then forward unchanged (header.stamp and represented_at kept)   (age < TAU)
  RESTAMP  drop incoming in the window and republish the last pre-window message at 20 Hz with header.stamp = now
           (represented_at, pose, seq kept)                                                        (cache/restamp)
Labels each output (fresh / delayed / restamped) in its log. Args: <log> <mode> <end_s>   env P1_T0_NS"""
import json, os, sys, time, collections
import rclpy
from rclpy.parameter import Parameter
from m7_msgs.msg import RepresentedPose
LOG, MODE, END = sys.argv[1], sys.argv[2], float(sys.argv[3]); W0, W1, D = 6.0, 7.5, 0.080; T0 = int(os.environ["P1_T0_NS"]) / 1e9
rclpy.init(); n = rclpy.create_node("m7_bridge", parameter_overrides=[Parameter("use_sim_time", value=True)])
pub = n.create_publisher(RepresentedPose, "/m7/bridged", 50); out = open(LOG, "w", buffering=1)
st = {"last": None, "q": collections.deque(), "ct": 0.0, "bid": 0}
def rel(): return time.time() - T0
def emit(m, label, restamp):
    o = RepresentedPose(); o.header.frame_id = m.header.frame_id; o.header.stamp = n.get_clock().now().to_msg() if restamp else m.header.stamp
    o.represented_at = m.represented_at; o.represented_frame = m.represented_frame; o.pose = m.pose; o.seq = m.seq
    pub.publish(o); st["bid"] += 1
    out.write(json.dumps({"t": rel(), "label": label, "seq": m.seq, "out_stamp": o.header.stamp.sec + o.header.stamp.nanosec * 1e-9}) + "\n")
def on_msg(m):
    w = W0 <= rel() < W1
    if MODE == "DELAY" and w: st["q"].append((n.get_clock().now().nanoseconds / 1e9 + D, m)); return
    if MODE == "RESTAMP" and w: return
    st["last"] = m; emit(m, "fresh", False)
def tick():
    now = n.get_clock().now().nanoseconds / 1e9
    while st["q"] and st["q"][0][0] <= now:
        _, m = st["q"].popleft(); st["last"] = m; emit(m, "delayed", False)
    if MODE == "RESTAMP" and W0 <= rel() < W1 and st["last"] is not None and time.time() - st["ct"] >= 0.05:
        st["ct"] = time.time(); emit(st["last"], "restamped", True)
    if rel() > END: raise SystemExit(0)
n.create_subscription(RepresentedPose, "/m7/represented", on_msg, 50); n.create_timer(0.005, tick)
try: rclpy.spin(n)
except (SystemExit, KeyboardInterrupt, rclpy.executors.ExternalShutdownException): pass
