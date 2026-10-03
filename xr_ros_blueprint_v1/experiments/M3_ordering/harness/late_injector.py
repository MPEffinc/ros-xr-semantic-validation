#!/usr/bin/env python3
"""M3_ordering late pre-stop trajectory (condition LATE): keeps the last Servo trajectory seen on the Servo output path
BEFORE the onset (t < 6.0 s after T0) and re-publishes it unchanged ONCE at onset + 0.150 s on the SAME path Servo uses
(CUR: /ur5_arm_controller/joint_trajectory; MUX: /m3/servo_out), modelling a delayed in-flight pre-stop message.
Args: <servo_out_topic> <log> <end_s>   env P1_T0_NS"""
import json, os, sys, time
import rclpy
from trajectory_msgs.msg import JointTrajectory
TOPIC, LOG, END = sys.argv[1], sys.argv[2], float(sys.argv[3]); T0 = int(os.environ["P1_T0_NS"]) / 1e9; ON, DLY = 6.0, 0.150
rclpy.init(); n = rclpy.create_node("m3_late_injector"); pub = n.create_publisher(JointTrajectory, TOPIC, 10); out = open(LOG, "w", buffering=1)
st = {"last": None, "sent": False}
def cb(m):
    if time.time() - T0 < ON and len(m.points) > 1: st["last"] = m   # Servo trajectories (holds are 1-point)
def tick():
    t = time.time() - T0
    if not st["sent"] and t >= ON + DLY and st["last"] is not None:
        pub.publish(st["last"]); st["sent"] = True
        out.write(json.dumps({"t": t, "k": "injected", "points": len(st["last"].points), "stamp": st["last"].header.stamp.sec + st["last"].header.stamp.nanosec * 1e-9}) + "\n")
    if t > END: raise SystemExit(0)
n.create_subscription(JointTrajectory, TOPIC, cb, 50); n.create_timer(0.002, tick)
try: rclpy.spin(n)
except (SystemExit, KeyboardInterrupt, rclpy.executors.ExternalShutdownException): pass
