#!/usr/bin/env python3
"""UPSTREAM-stack probe: does the on-wire size/rate of teleop-style ROS 2 messages depend on content?

Publishes geometry_msgs/PoseArray (N poses, like xr_teleop/ee_poses) and sensor_msgs/JointState (M joints,
like finger_joints / joint_states) at a fixed rate, with *random* values that change every message.
Content is synthetic on purpose: the question is an implementation property (CDR/RTPS size and timing),
not task data. Usage: ros_flow_size_probe.py <rate_hz> <seconds> <n_poses> <n_joints>
"""
import random, sys, time
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import PoseArray, Pose
from sensor_msgs.msg import JointState

rate, secs, n_p, n_j = float(sys.argv[1]), float(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4])
rclpy.init(); node = Node('xf_probe')
pa = node.create_publisher(PoseArray, 'xr_teleop/ee_poses', 10)
js = node.create_publisher(JointState, 'xr_teleop/finger_joints', 10)
names = [f'joint_{i}' for i in range(n_j)]
t_end = time.monotonic() + secs; period = 1.0 / rate; nxt = time.monotonic()
while time.monotonic() < t_end:
    now = node.get_clock().now().to_msg()
    m = PoseArray(); m.header.stamp = now; m.header.frame_id = 'world'
    for _ in range(n_p):
        p = Pose(); p.position.x, p.position.y, p.position.z = (random.uniform(-1, 1) for _ in range(3))
        p.orientation.w = random.random(); m.poses.append(p)
    pa.publish(m)
    j = JointState(); j.header.stamp = now; j.name = names; j.position = [random.uniform(-3, 3) for _ in names]
    js.publish(j)
    nxt += period; time.sleep(max(0.0, nxt - time.monotonic()))
rclpy.shutdown()
