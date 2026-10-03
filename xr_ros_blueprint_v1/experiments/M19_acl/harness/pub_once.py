#!/usr/bin/env python3
"""M19 payload publisher. Publishes the fixed payload (one JointTrajectory point: start pose + 0.20 rad on
shoulder_pan_joint, time_from_start 1.0 s, stamp 0) on <topic> under the enclave given by the environment, after waiting
up to 5 s for a matched subscription. Logs the publisher-creation result, matched subscriber count and publish result.
The publish API result alone is never used as evidence of delivery (the observer/controller trace is).
Args: <topic> <log> <node_name>"""
import json, sys, time
import rclpy
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint
TOPIC, LOG, NAME = sys.argv[1:4]; out = open(LOG, "w", buffering=1)
J = ["shoulder_pan_joint", "shoulder_lift_joint", "elbow_joint", "wrist_1_joint", "wrist_2_joint", "wrist_3_joint"]
Q0 = [-2.865212, -0.02629, -1.853711, -1.261592, -2.865212, -1.571593]; PAYLOAD = [Q0[0] + 0.20] + Q0[1:]
def log(**k): k["wall"] = time.time(); out.write(json.dumps(k) + "\n")
try:
    rclpy.init(); n = rclpy.create_node(NAME, start_parameter_services=False, enable_rosout=False)
except Exception as e:
    log(k="node_failed", err=repr(e)[:400]); sys.exit(2)
try:
    pub = n.create_publisher(JointTrajectory, TOPIC, 10)
except Exception as e:
    log(k="create_publisher_failed", topic=TOPIC, err=repr(e)[:400]); sys.exit(3)
log(k="create_publisher_ok", topic=TOPIC)
t = time.time()
while pub.get_subscription_count() == 0 and time.time() - t < 5.0: rclpy.spin_once(n, timeout_sec=0.05)
m = JointTrajectory(); m.joint_names = J; p = JointTrajectoryPoint(); p.positions = PAYLOAD; p.time_from_start.sec = 1; m.points = [p]
try:
    pub.publish(m); log(k="published", topic=TOPIC, matched=pub.get_subscription_count(), payload=PAYLOAD)
except Exception as e:
    log(k="publish_failed", err=repr(e)[:400])
t = time.time()
while time.time() - t < 1.0: rclpy.spin_once(n, timeout_sec=0.05)
