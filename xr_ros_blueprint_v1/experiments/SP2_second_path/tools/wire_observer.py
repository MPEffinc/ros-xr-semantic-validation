#!/usr/bin/env python3
"""SP2 smoke observer: records what the REAL PickNik frontend puts on the ROS wire (via ROS-TCP-Endpoint):
/right_controller_odom (pose), /right_grip_button_state (Bool level), /right_grip_button_event (Empty press edge),
/left_controller_odom, /tf message count. wall_ns at reception. Args: <out.jsonl> <dur_s>"""
import json, sys, time
import rclpy
from nav_msgs.msg import Odometry
from std_msgs.msg import Bool, Empty
from tf2_msgs.msg import TFMessage
out = open(sys.argv[1], "w", buffering=1); dur = float(sys.argv[2])
rclpy.init(); n = rclpy.create_node("sp2_wire_observer")
def w(k, **kw): out.write(json.dumps({"k": k, "wall": time.time(), **kw}) + "\n")
def odom(k):
    return lambda m: w(k, child=m.child_frame_id, stamp=m.header.stamp.sec + m.header.stamp.nanosec * 1e-9,
                       p=[m.pose.pose.position.x, m.pose.pose.position.y, m.pose.pose.position.z],
                       q=[m.pose.pose.orientation.x, m.pose.pose.orientation.y, m.pose.pose.orientation.z, m.pose.pose.orientation.w])
n.create_subscription(Odometry, "/right_controller_odom", odom("r_odom"), 100)
n.create_subscription(Odometry, "/left_controller_odom", odom("l_odom"), 100)
n.create_subscription(Bool, "/right_grip_button_state", lambda m: w("r_grip_state", v=bool(m.data)), 100)
n.create_subscription(Empty, "/right_grip_button_event", lambda m: w("r_grip_event"), 100)
n.create_subscription(Bool, "/right_trigger_button_state", lambda m: w("r_trig_state", v=bool(m.data)), 100)
n.create_subscription(TFMessage, "/tf", lambda m: w("tf", child=[t.child_frame_id for t in m.transforms]), 100)
t0 = time.time()
while time.time() - t0 < dur: rclpy.spin_once(n, timeout_sec=0.05)
