#!/usr/bin/env python3
"""R10 1B: standalone JTC action verification (NOT an XR end-to-end path). Sends one FollowJointTrajectory goal that
moves the EE along base -x at V m/s (joint path by IK continuation from the start configuration, 20 ms points), cancels
it T_CANCEL s after acceptance, then records joint states and EE (tf) for 2 s. Optional: OVERRIDE=1 publishes one topic
trajectory 0.3 s after the cancel response to observe whether it replaces the stop. Args: <out.jsonl> <v_mps> [override]"""
import json, sys, time
import numpy as np
import rclpy
from rclpy.action import ActionClient
from builtin_interfaces.msg import Duration
from control_msgs.action import FollowJointTrajectory
from scipy.spatial.transform import Rotation as R
from sensor_msgs.msg import JointState
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint
import tf2_ros
sys.path.insert(0, "/m39/harness"); import ur5_kin as K
OUT, V = sys.argv[1], float(sys.argv[2]); OVR = len(sys.argv) > 3 and sys.argv[3] == "1"; T_CANCEL, DIST, DT = 0.6, 0.10, 0.02
J = ["shoulder_pan_joint", "shoulder_lift_joint", "elbow_joint", "wrist_1_joint", "wrist_2_joint", "wrist_3_joint"]
f = open(OUT, "w", buffering=1)
def w(k, **kw): f.write(json.dumps({"k": k, "wall": time.time(), **kw}) + "\n")
rclpy.init(); n = rclpy.create_node("r10_action_cancel"); js = {}
def on_js(m):
    d = dict(zip(m.name, m.position)); v = dict(zip(m.name, m.velocity))
    if all(j in d for j in J): js.update(q=[d[j] for j in J], v=[v.get(j, 0.0) for j in J]); w("js", q=js["q"], v=js["v"])
n.create_subscription(JointState, "/joint_states", on_js, 100)
buf = tf2_ros.Buffer(); tf2_ros.TransformListener(buf, n)
def ee():
    try:
        t = buf.lookup_transform("base_link", "wrist_3_link", rclpy.time.Time()).transform.translation; return [t.x, t.y, t.z]
    except Exception: return None
n.create_timer(0.01, lambda: (lambda p: p and w("ee", p=p))(ee()))
ac = ActionClient(n, FollowJointTrajectory, "/ur5_arm_controller/follow_joint_trajectory")
pub = n.create_publisher(JointTrajectory, "/ur5_arm_controller/joint_trajectory", 10)
def spin(s):
    e = time.time() + s
    while time.time() < e: rclpy.spin_once(n, timeout_sec=0.005)
spin(2.0)
while "q" not in js: spin(0.1)
ac.wait_for_server(timeout_sec=20)
q = np.array(js["q"]); p0, R0, _ = K.fk(q); pts = []; steps = int(round(DIST / V / DT))
for k in range(1, steps + 1):
    q, ok = K.ik(p0 + np.array([-V * k * DT, 0, 0]), R0, q); pts.append(q.copy())
traj = JointTrajectory(); traj.joint_names = J
for k, qq in enumerate(pts):
    pt = JointTrajectoryPoint(); pt.positions = [float(x) for x in qq]
    nxt = pts[min(k + 1, len(pts) - 1)]; prv = pts[max(k - 1, 0)]
    pt.velocities = [0.0] * 6 if k == len(pts) - 1 else [float(x) for x in (nxt - prv) / (2 * DT if 0 < k else DT)]
    ns = int((k + 1) * DT * 1e9); pt.time_from_start = Duration(sec=ns // 10**9, nanosec=ns % 10**9); traj.points.append(pt)
goal = FollowJointTrajectory.Goal(); goal.trajectory = traj
w("goal_send", v=V, points=len(pts), dist=DIST)
fut = ac.send_goal_async(goal)
while not fut.done(): spin(0.002)
gh = fut.result(); w("goal_response", accepted=bool(gh.accepted))
t_acc = time.time(); spin(T_CANCEL)
w("cancel_request", q=js["q"], v=js["v"], ee=ee())
cf = gh.cancel_goal_async()
while not cf.done(): spin(0.001)
cr = cf.result(); w("cancel_response", return_code=int(cr.return_code), goals_canceling=len(cr.goals_canceling))
if OVR:
    spin(0.3); tr = JointTrajectory(); tr.joint_names = J; pt = JointTrajectoryPoint()
    qq, ok = K.ik(K.fk(np.array(js["q"]))[0] + np.array([-0.03, 0, 0]), R0, np.array(js["q"]))
    pt.positions = [float(x) for x in qq]; pt.time_from_start = Duration(sec=1, nanosec=0); tr.points = [pt]
    pub.publish(tr); w("override_topic_traj", target_dx=-0.03)
spin(2.0); w("end")
