#!/usr/bin/env python3
"""Record every message on a PoseStamped topic with wall receive time. Args: <topic> <out.jsonl> <seconds>"""
import json, sys, time, rclpy
from geometry_msgs.msg import PoseStamped
rclpy.init(); n = rclpy.create_node('f1_cmd_recorder'); out = open(sys.argv[2], 'w', buffering=1); end = time.time() + float(sys.argv[3])
n.create_subscription(PoseStamped, sys.argv[1], lambda m: out.write(json.dumps({"wall": time.time(), "stamp_ns": m.header.stamp.sec * 10**9 + m.header.stamp.nanosec, "p": [m.pose.position.x, m.pose.position.y, m.pose.position.z]}) + "\n"), 100)
while time.time() < end: rclpy.spin_once(n, timeout_sec=0.05)
