#!/usr/bin/env python3
"""Record every boundary of one P1 trial (no gating, no interpretation).

  /p1/app_cmd                 app output (gate arms only)
  /servo_node/pose_target_cmds  Servo input
  /servo_node/status          Servo status code
  /ur5_arm_controller/joint_trajectory  Servo output
  /joint_states               plant feedback
  tf base_link -> P1_EE_FRAME  end-effector pose, polled at 100 Hz
Timestamps: wall_ns (CLOCK_REALTIME, same clock as the scenario P1_T0_NS).
"""
import json
import os
import sys
import time

import rclpy
from geometry_msgs.msg import PoseStamped
from moveit_msgs.msg import ServoStatus
from sensor_msgs.msg import JointState
from trajectory_msgs.msg import JointTrajectory
import tf2_ros


def main():
    out, end_t = sys.argv[1], float(sys.argv[2])
    t0 = int(os.environ["P1_T0_NS"])
    ee = os.environ.get("P1_EE_FRAME", "wrist_3_link")
    rclpy.init()
    node = rclpy.create_node("p1_observer")
    f = open(out, "w", buffering=1)

    def w(kind, **kw):
        f.write(json.dumps({"k": kind, "wall_ns": time.time_ns(), **kw}) + "\n")

    def pose_cb(kind):
        return lambda m: w(kind, p=[m.pose.position.x, m.pose.position.y, m.pose.position.z],
                           q=[m.pose.orientation.x, m.pose.orientation.y, m.pose.orientation.z, m.pose.orientation.w],
                           stamp_ns=m.header.stamp.sec * 10**9 + m.header.stamp.nanosec)

    node.create_subscription(PoseStamped, "/p1/app_cmd", pose_cb("app"), 50)
    node.create_subscription(PoseStamped, "/servo_node/pose_target_cmds", pose_cb("servo_in"), 50)
    node.create_subscription(ServoStatus, "/servo_node/status", lambda m: w("status", code=int(m.code)), 50)
    node.create_subscription(JointTrajectory, "/ur5_arm_controller/joint_trajectory",
                             lambda m: w("servo_out", n=len(m.points),
                                         v=list(m.points[0].velocities) if m.points else []), 50)
    node.create_subscription(JointState, "/joint_states",
                             lambda m: w("joints", names=list(m.name), pos=list(m.position)), 50)
    buf = tf2_ros.Buffer()
    tf2_ros.TransformListener(buf, node)

    def poll_tf():
        try:
            tr = buf.lookup_transform("base_link", ee, rclpy.time.Time())
            t = tr.transform.translation
            r = tr.transform.rotation
            w("ee", p=[t.x, t.y, t.z], q=[r.x, r.y, r.z, r.w],
              stamp_ns=tr.header.stamp.sec * 10**9 + tr.header.stamp.nanosec)
        except Exception as e:  # noqa: BLE001
            w("ee_err", err=type(e).__name__)
        if (time.time_ns() - t0) / 1e9 > end_t:
            raise SystemExit(0)

    node.create_timer(0.01, poll_tf)
    try:
        rclpy.spin(node)
    except SystemExit:
        pass
    w("end")


if __name__ == "__main__":
    main()
