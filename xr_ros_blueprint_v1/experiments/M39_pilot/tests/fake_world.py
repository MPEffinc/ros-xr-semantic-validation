#!/usr/bin/env python3
"""TEST-ONLY stand-in for Servo/JTC/Gazebo: /servo_node/pause_servo service (logged), static tf base_link->wrist_3_link
at the pose given in env M39_FAKE_EE ("x y z qx qy qz qw"), /joint_states at 100 Hz with zero velocity, and logs of
everything published to /servo_node/pose_target_cmds and /ur5_arm_controller/joint_trajectory.  Args: <out.jsonl> <end_s>"""
import json, os, sys, time
import rclpy
from geometry_msgs.msg import PoseStamped, TransformStamped
from sensor_msgs.msg import JointState
from std_srvs.srv import SetBool
from trajectory_msgs.msg import JointTrajectory
from tf2_ros.static_transform_broadcaster import StaticTransformBroadcaster
out = open(sys.argv[1], "w", buffering=1); end = float(sys.argv[2]); t0 = int(os.environ["P1_T0_NS"]) / 1e9
def w(k, **kw): out.write(json.dumps({"k": k, "t": time.time() - t0, **kw}) + "\n")
rclpy.init(); n = rclpy.create_node("fake_world"); paused = {"v": False}
def srv(req, resp):
    w("pause", data=req.data); paused["v"] = req.data; resp.success = True; resp.message = "ok"; return resp
n.create_service(SetBool, "/servo_node/pause_servo", srv)
n.create_subscription(PoseStamped, "/servo_node/pose_target_cmds", lambda m: w("servo_in", paused=paused["v"], p=[m.pose.position.x, m.pose.position.y, m.pose.position.z],
                      q=[m.pose.orientation.x, m.pose.orientation.y, m.pose.orientation.z, m.pose.orientation.w]), 100)
n.create_subscription(JointTrajectory, "/ur5_arm_controller/joint_trajectory", lambda m: w("jtc", n=len(m.points)), 100)
js = n.create_publisher(JointState, "/joint_states", 10)
J = ["shoulder_pan_joint", "shoulder_lift_joint", "elbow_joint", "wrist_1_joint", "wrist_2_joint", "wrist_3_joint"]
def pub_js():
    m = JointState(); m.header.stamp = n.get_clock().now().to_msg(); m.name = J; m.position = [0.1] * 6; m.velocity = [0.0] * 6; js.publish(m)
    if time.time() - t0 > end: raise SystemExit(0)
n.create_timer(0.01, pub_js)
e = [float(x) for x in os.environ["M39_FAKE_EE"].split()]
tb = StaticTransformBroadcaster(n); tf = TransformStamped(); tf.header.frame_id = "base_link"; tf.child_frame_id = "wrist_3_link"
tf.transform.translation.x, tf.transform.translation.y, tf.transform.translation.z = e[:3]
tf.transform.rotation.x, tf.transform.rotation.y, tf.transform.rotation.z, tf.transform.rotation.w = e[3:]
tb.sendTransform(tf)
try: rclpy.spin(n)
except SystemExit: pass
