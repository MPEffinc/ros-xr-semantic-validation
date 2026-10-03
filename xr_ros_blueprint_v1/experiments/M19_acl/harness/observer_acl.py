#!/usr/bin/env python3
"""M19 observer (trusted enclave /m19/observer). Logs every message on the controller topic and on the app input topic
(DDS delivery to a permitted reader), the JTC controller_state reference, and /joint_states (mock hardware follows the
commanded positions). Args: <log> <duration_s>"""
import json, sys, time
import rclpy
from trajectory_msgs.msg import JointTrajectory
from sensor_msgs.msg import JointState
from control_msgs.msg import JointTrajectoryControllerState
LOG, DUR = sys.argv[1], float(sys.argv[2]); out = open(LOG, "w", buffering=1)
rclpy.init(); n = rclpy.create_node("m19_observer")
def w(**k): k["wall"] = time.time(); out.write(json.dumps(k) + "\n")
n.create_subscription(JointTrajectory, "/ur5_arm_controller/joint_trajectory", lambda m: w(k="ctl_topic", pos=list(m.points[0].positions) if m.points else []), 10)
n.create_subscription(JointTrajectory, "/m19/app_cmd", lambda m: w(k="app_topic", pos=list(m.points[0].positions) if m.points else []), 10)
n.create_subscription(JointState, "/joint_states", lambda m: w(k="js", names=list(m.name), pos=list(m.position)), 10)
n.create_subscription(JointTrajectoryControllerState, "/ur5_arm_controller/controller_state",
                      lambda m: w(k="ref", names=list(m.joint_names), pos=list(m.reference.positions)), 10)
w(k="start"); t = time.time()
while time.time() - t < DUR: rclpy.spin_once(n, timeout_sec=0.05)
w(k="end")
