#!/usr/bin/env python3
"""TEST-ONLY: replay recorded app commands (F3 observer 'servo_in' lines) to /m39/app_cmd at their original offsets
from <src_t0>, re-timed to P1_T0_NS. Optional drop window [a,b) (s after T0) to create command silence.
Args: <observer.jsonl> <src_t0> [drop_a drop_b]"""
import json, os, sys, time
import rclpy
from geometry_msgs.msg import PoseStamped
src, st0 = sys.argv[1], float(sys.argv[2]); drop = (float(sys.argv[3]), float(sys.argv[4])) if len(sys.argv) > 4 else None
t0 = int(os.environ["P1_T0_NS"]) / 1e9
rows = [json.loads(l) for l in open(src)]; rows = [r for r in rows if r["k"] == "servo_in"]
rclpy.init(); n = rclpy.create_node("replay_cmds"); pub = n.create_publisher(PoseStamped, "/m39/app_cmd", 10); time.sleep(1.0)
for r in rows:
    rel = r["wall_ns"] / 1e9 - st0
    if drop and drop[0] <= rel < drop[1]: continue
    d = t0 + rel - time.time()
    if d > 0: time.sleep(d)
    m = PoseStamped(); m.header.frame_id = "base_link"; m.header.stamp = n.get_clock().now().to_msg()
    m.pose.position.x, m.pose.position.y, m.pose.position.z = r["p"]
    m.pose.orientation.x, m.pose.orientation.y, m.pose.orientation.z, m.pose.orientation.w = r["q"]
    pub.publish(m)
