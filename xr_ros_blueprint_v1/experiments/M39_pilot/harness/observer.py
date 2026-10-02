#!/usr/bin/env python3
"""M39 observer (extends F3 observer.py; no gating, no interpretation). Records, with wall_ns (CLOCK_REALTIME) and
mono_ns (CLOCK_MONOTONIC) at reception:
  /m39/app_cmd (C1 only: app output)  /servo_node/pose_target_cmds (Servo input)  /servo_node/status
  /ur5_arm_controller/joint_trajectory (Servo output AND holds; first point kept)  /joint_states (pos, vel, sim stamp)
  /clock (sim time, 10 Hz decimated)  tf base_link -> wrist_3_link at 100 Hz (latest; sim stamp kept)
Args: <out.jsonl> <end_s>   env P1_T0_NS"""
import json, os, sys, time
import rclpy
from geometry_msgs.msg import PoseStamped
from moveit_msgs.msg import ServoStatus
from rosgraph_msgs.msg import Clock
from sensor_msgs.msg import JointState
from trajectory_msgs.msg import JointTrajectory
import tf2_ros


def main():
    out, end_t = sys.argv[1], float(sys.argv[2]); t0 = int(os.environ["P1_T0_NS"])
    rclpy.init(); node = rclpy.create_node("m39_observer"); f = open(out, "w", buffering=1)
    def w(kind, **kw):
        f.write(json.dumps({"k": kind, "wall_ns": time.time_ns(), "mono_ns": time.monotonic_ns(), **kw}) + "\n")
    def st(h): return h.stamp.sec * 10**9 + h.stamp.nanosec
    def pose_cb(kind):
        return lambda m: w(kind, p=[m.pose.position.x, m.pose.position.y, m.pose.position.z],
                           q=[m.pose.orientation.x, m.pose.orientation.y, m.pose.orientation.z, m.pose.orientation.w],
                           stamp_ns=st(m.header), frame=m.header.frame_id)
    node.create_subscription(PoseStamped, "/m39/app_cmd", pose_cb("app"), 100)
    node.create_subscription(PoseStamped, "/servo_node/pose_target_cmds", pose_cb("servo_in"), 100)
    node.create_subscription(ServoStatus, "/servo_node/status", lambda m: w("status", code=int(m.code)), 100)
    def traj(m):
        p0 = m.points[0] if m.points else None
        w("traj", n=len(m.points), stamp_ns=st(m.header), names=list(m.joint_names),
          pos0=list(p0.positions) if p0 else [], vel0=list(p0.velocities) if p0 else [],
          tfs0_ns=(p0.time_from_start.sec * 10**9 + p0.time_from_start.nanosec) if p0 else None)
    node.create_subscription(JointTrajectory, "/ur5_arm_controller/joint_trajectory", traj, 100)
    node.create_subscription(JointState, "/joint_states",
                             lambda m: w("joints", names=list(m.name), pos=list(m.position), vel=list(m.velocity), stamp_ns=st(m.header)), 100)
    cnt = {"c": 0}
    def clk(m):
        cnt["c"] += 1
        if cnt["c"] % 10 == 0: w("clock", sim_ns=m.clock.sec * 10**9 + m.clock.nanosec)
    node.create_subscription(Clock, "/clock", clk, 10)
    buf = tf2_ros.Buffer(); tf2_ros.TransformListener(buf, node)
    def poll_tf():
        try:
            tr = buf.lookup_transform("base_link", "wrist_3_link", rclpy.time.Time())
            t, r = tr.transform.translation, tr.transform.rotation
            w("ee", p=[t.x, t.y, t.z], q=[r.x, r.y, r.z, r.w], stamp_ns=st(tr.header))
        except Exception as e:  # noqa: BLE001
            w("ee_err", err=type(e).__name__)
        if (time.time_ns() - t0) / 1e9 > end_t: raise SystemExit(0)
    node.create_timer(0.01, poll_tf)
    try: rclpy.spin(node)
    except SystemExit: pass
    w("end")


if __name__ == "__main__":
    main()
