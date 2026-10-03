#!/usr/bin/env python3
"""M7 admitted-delay bridge (R24). Same as the frozen M7_frame/harness/m7_bridge.py except the DELAY value:
  PASS   forward unchanged
  DELAY  hold each message D = 30 ms (sim) in the window 6.0-7.5 s after T0, then forward unchanged
         (header.stamp and represented_at kept). D is chosen so that baseline stamp age (R17 DYN max 41 ms) + D stays
         below TAU = 100 ms with >= 25 ms margin.
Labels each output (fresh / delayed). Args: <log> <mode> <end_s>   env P1_T0_NS"""
import json, os, sys, time, collections
import rclpy
from rclpy.parameter import Parameter
from m7_msgs.msg import RepresentedPose
LOG, MODE, END = sys.argv[1], sys.argv[2], float(sys.argv[3]); W0, W1, D = 6.0, 7.5, 0.030; T0 = int(os.environ["P1_T0_NS"]) / 1e9
rclpy.init(); n = rclpy.create_node("m7_bridge", parameter_overrides=[Parameter("use_sim_time", value=True)])
pub = n.create_publisher(RepresentedPose, "/m7/bridged", 50); out = open(LOG, "w", buffering=1)
st = {"q": collections.deque()}
def rel(): return time.time() - T0
def emit(m, label):
    o = RepresentedPose(); o.header = m.header; o.represented_at = m.represented_at; o.represented_frame = m.represented_frame
    o.pose = m.pose; o.seq = m.seq; pub.publish(o)
    out.write(json.dumps({"t": rel(), "label": label, "seq": m.seq, "out_stamp": o.header.stamp.sec + o.header.stamp.nanosec * 1e-9,
                          "sim_now": n.get_clock().now().nanoseconds / 1e9}) + "\n")
def on_msg(m):
    if MODE == "DELAY" and W0 <= rel() < W1: st["q"].append((n.get_clock().now().nanoseconds / 1e9 + D, m)); return
    emit(m, "fresh")
def tick():
    now = n.get_clock().now().nanoseconds / 1e9
    while st["q"] and st["q"][0][0] <= now: emit(st["q"].popleft()[1], "delayed")
    if rel() > END: raise SystemExit(0)
n.create_subscription(RepresentedPose, "/m7/represented", on_msg, 50); n.create_timer(0.002, tick)
try: rclpy.spin(n)
except (SystemExit, KeyboardInterrupt, rclpy.executors.ExternalShutdownException): pass
