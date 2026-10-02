#!/usr/bin/env python3
"""M39 deployment-level start setup, identical for every arm (before the app/runtime start): drive the JTC to the
pre-flight start configuration with one trajectory, then verify settle and the EE pose against the app's fixed engage
pose (0.4, 0, 0.3, robot_home_rot = euler xyz (0, 1.57, 0)) by tf. Writes one JSON result line. Exit 0 = qualified.
Args: <out.json> <q1..q6> [duration_s]"""
import json, sys, time
import numpy as np
import rclpy
from builtin_interfaces.msg import Duration
from scipy.spatial.transform import Rotation as R
from sensor_msgs.msg import JointState
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint
import tf2_ros
J = ["shoulder_pan_joint", "shoulder_lift_joint", "elbow_joint", "wrist_1_joint", "wrist_2_joint", "wrist_3_joint"]
out = sys.argv[1]; qt = [float(x) for x in sys.argv[2:8]]; dur = float(sys.argv[8]) if len(sys.argv) > 8 else 6.0
rclpy.init(); node = rclpy.create_node("m39_setup"); js = {}
node.create_subscription(JointState, "/joint_states", lambda m: js.update(q=dict(zip(m.name, m.position)), v=dict(zip(m.name, m.velocity)), t=time.time()), 10)
pub = node.create_publisher(JointTrajectory, "/ur5_arm_controller/joint_trajectory", 10)
buf = tf2_ros.Buffer(); tf2_ros.TransformListener(buf, node)
def spin(s):
    e = time.time() + s
    while time.time() < e: rclpy.spin_once(node, timeout_sec=0.01)
t_start = time.time()
while "q" not in js and time.time() - t_start < 30: spin(0.1)
while pub.get_subscription_count() == 0 and time.time() - t_start < 30: spin(0.1)
q_init = [js["q"][j] for j in J]
tr = JointTrajectory(); tr.joint_names = J
pt = JointTrajectoryPoint(); pt.positions = qt; pt.velocities = [0.0] * 6
pt.time_from_start = Duration(sec=int(dur), nanosec=int((dur % 1) * 1e9)); tr.points = [pt]
pub.publish(tr); t_cmd = time.time()
res = {"q_init": q_init, "q_target": qt, "t_cmd": t_cmd}
ok = False
while time.time() - t_cmd < dur * 3 + 10:
    spin(0.1)
    q = [js["q"][j] for j in J]; v = [abs(js["v"].get(j, 0.0)) for j in J]
    if max(abs(a - b) for a, b in zip(q, qt)) < 1e-3 and max(v) < 1e-3:
        ok = True; break
spin(1.0)  # settle
q = [js["q"][j] for j in J]; v = [js["v"].get(j, 0.0) for j in J]
try:
    tf = buf.lookup_transform("base_link", "wrist_3_link", rclpy.time.Time())
    p = [tf.transform.translation.x, tf.transform.translation.y, tf.transform.translation.z]
    qq = [tf.transform.rotation.x, tf.transform.rotation.y, tf.transform.rotation.z, tf.transform.rotation.w]
    pe = float(np.linalg.norm(np.array(p) - [0.4, 0, 0.3])) * 1000
    re = float(np.degrees((R.from_quat(qq) * R.from_euler('xyz', [0, 1.57, 0]).inv()).magnitude()))
except Exception as e:  # noqa: BLE001
    p = qq = None; pe = re = None; res["tf_err"] = type(e).__name__
qual = bool(ok and pe is not None and pe <= 2.0 and re <= 1.0 and max(abs(x) for x in v) < 1e-3)
res.update(q_final=q, v_final=v, ee_p=p, ee_q=qq, ee_pos_err_mm=pe, ee_rot_err_deg=re, reached=ok, qualified=qual,
           t_done=time.time(), load=open("/proc/loadavg").read().split()[:3])
open(out, "w").write(json.dumps(res) + "\n"); sys.exit(0 if qual else 4)
