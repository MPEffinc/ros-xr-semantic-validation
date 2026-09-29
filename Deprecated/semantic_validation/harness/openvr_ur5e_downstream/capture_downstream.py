#!/usr/bin/env python3
"""Capture the OpenVR UR5e downstream boundary during one trial.

Records, for a bounded window:
  * the production node's own ROS output   (/servo_node/pose_target_cmds)
  * MoveIt Servo's status                  (/servo_node/status)
  * Servo's outgoing controller command    (/ur5_arm_controller/joint_trajectory)
  * the simulated robot's joint feedback   (/joint_states)

It performs no gating and no interpretation; it only writes what arrived.
"""
import argparse
import json
import time

import rclpy
from geometry_msgs.msg import PoseStamped
from sensor_msgs.msg import JointState
from std_msgs.msg import Int8
from trajectory_msgs.msg import JointTrajectory


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--duration", type=float, default=12.0)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    rclpy.init()
    node = rclpy.create_node("openvr_downstream_capture")
    start = time.monotonic()
    poses, statuses, trajectories, joints = [], [], [], []

    def on_pose(msg):
        poses.append({
            "monotonic": time.monotonic() - start,
            "stamp_sec": msg.header.stamp.sec,
            "stamp_nanosec": msg.header.stamp.nanosec,
            "frame_id": msg.header.frame_id,
            "position": [msg.pose.position.x, msg.pose.position.y, msg.pose.position.z],
            "orientation": [msg.pose.orientation.x, msg.pose.orientation.y,
                            msg.pose.orientation.z, msg.pose.orientation.w],
        })

    def on_status(msg):
        statuses.append({"monotonic": time.monotonic() - start, "code": int(msg.data)})

    def on_traj(msg):
        point = msg.points[0] if msg.points else None
        trajectories.append({
            "monotonic": time.monotonic() - start,
            "joint_names": list(msg.joint_names),
            "positions": list(point.positions) if point else [],
            "velocities": list(point.velocities) if point else [],
        })

    def on_joints(msg):
        joints.append({
            "monotonic": time.monotonic() - start,
            "stamp_sec": msg.header.stamp.sec,
            "stamp_nanosec": msg.header.stamp.nanosec,
            "name": list(msg.name),
            "position": list(msg.position),
            "velocity": list(msg.velocity),
        })

    node.create_subscription(PoseStamped, "/servo_node/pose_target_cmds", on_pose, 200)
    node.create_subscription(Int8, "/servo_node/status", on_status, 200)
    node.create_subscription(JointTrajectory, "/ur5_arm_controller/joint_trajectory", on_traj, 200)
    node.create_subscription(JointState, "/joint_states", on_joints, 200)

    while time.monotonic() - start < args.duration:
        rclpy.spin_once(node, timeout_sec=0.02)

    with open(args.out, "w") as handle:
        json.dump({
            "duration_s": args.duration,
            "pose_target_cmds": poses,
            "servo_status": statuses,
            "arm_controller_joint_trajectory": trajectories,
            "joint_states": joints,
        }, handle, sort_keys=True)

    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()
