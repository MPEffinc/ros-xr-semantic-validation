#!/usr/bin/env python3
"""M3_far late pre-stop trajectory with a distant target (R25). Keeps the last multi-point Servo trajectory seen on the
Servo output path with receive time t < CAPTURE = 4.0 s after T0 (onset - 2.0 s, inside the qualified I3 motion), and
re-publishes it ONCE at onset + 0.150 s on the same path Servo uses (CUR: /ur5_arm_controller/joint_trajectory;
MUX: /m3/servo_out) with points and time_from_start unchanged and header.stamp = 0 ("start now"). This models a late
pre-stop message from a writer that uses start-immediately semantics. (With its original stamp the message ends in the
past and JTC 4.42.1 rejects it; see R25 pre-flight.) Logs capture time, original stamp, number of points, last
time_from_start and the last point's joint positions.
Args: <servo_out_topic> <log> <end_s>   env P1_T0_NS"""
import json, os, sys, time
import rclpy
from rclpy.parameter import Parameter
from trajectory_msgs.msg import JointTrajectory
TOPIC, LOG, END = sys.argv[1], sys.argv[2], float(sys.argv[3]); T0 = int(os.environ["P1_T0_NS"]) / 1e9; ON, DLY, CAPTURE = 6.0, 0.150, 4.0
rclpy.init(); n = rclpy.create_node("m3_far_injector", parameter_overrides=[Parameter("use_sim_time", value=True)]); pub = n.create_publisher(JointTrajectory, TOPIC, 10); out = open(LOG, "w", buffering=1)
st = {"last": None, "tc": None, "sent": False}
def cb(m):
    t = time.time() - T0
    if t < CAPTURE and len(m.points) > 1: st["last"], st["tc"] = m, t
def tick():
    t = time.time() - T0
    if not st["sent"] and t >= ON + DLY and st["last"] is not None:
        m = st["last"]; orig = m.header.stamp.sec + m.header.stamp.nanosec * 1e-9
        m.header.stamp.sec, m.header.stamp.nanosec = 0, 0; pub.publish(m); st["sent"] = True; lp = m.points[-1]
        out.write(json.dumps({"t": t, "k": "injected", "captured_t": st["tc"], "points": len(m.points),
                              "stamp": 0.0, "orig_stamp": orig, "sim_now": n.get_clock().now().nanoseconds / 1e9,
                              "last_tfs": lp.time_from_start.sec + lp.time_from_start.nanosec * 1e-9, "names": list(m.joint_names),
                              "last_pos": list(lp.positions)}) + "\n")
    if t > END: raise SystemExit(0)
n.create_subscription(JointTrajectory, TOPIC, cb, 50); n.create_timer(0.002, tick)
try: rclpy.spin(n)
except (SystemExit, KeyboardInterrupt, rclpy.executors.ExternalShutdownException): pass
