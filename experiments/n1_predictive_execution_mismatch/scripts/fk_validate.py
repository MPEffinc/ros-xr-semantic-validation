#!/usr/bin/env python3
"""Compare ur5_fk.fk(joint_states) with TF base_link->wrist_3_link (robot_state_publisher) at the same instant."""
import sys, rclpy, numpy as np
from rclpy.node import Node
from sensor_msgs.msg import JointState
from tf2_ros import Buffer, TransformListener
sys.path.insert(0, '/scripts'); from ur5_fk import fk, ARM
rclpy.init(); n = Node('fkval', parameter_overrides=[rclpy.parameter.Parameter('use_sim_time', value=True)])
buf = Buffer(); TransformListener(buf, n); st = {}
def cb(m):
    d = dict(zip(m.name, m.position))
    if all(j in d for j in ARM): st['q'] = [d[j] for j in ARM]; st['t'] = m.header.stamp
n.create_subscription(JointState, '/joint_states', cb, 10)
errs = []
for _ in range(400):
    rclpy.spin_once(n, timeout_sec=0.05)
    if 'q' in st:
        try:
            tr = buf.lookup_transform('base_link', 'wrist_3_link', st['t'])
            t = tr.transform.translation; p, _ = fk(st['q']); errs.append(np.linalg.norm(p - [t.x, t.y, t.z]))
        except Exception: pass
    if len(errs) >= 20: break
print('samples', len(errs), 'max_err_m', max(errs) if errs else None, 'last_q', st.get('q'))
