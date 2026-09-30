"""Forward kinematics of the pinned UR5 (openvr_ur5e_jazzy@170dad5, ur5_robot.urdf.xacro).
Joint origins/axes extracted from the xacro-expanded URDF (all rpy = 0): base_link -> wrist_3_link.
Validated against TF in docs/02_simulation_setup.md."""
import numpy as np
ARM = ['shoulder_pan_joint', 'shoulder_lift_joint', 'elbow_joint', 'wrist_1_joint', 'wrist_2_joint', 'wrist_3_joint']
_CHAIN = [  # (origin xyz, axis)
    ((0, 0, 0.089159), (0, 0, 1)),
    ((0, 0.13585, 0), (0, 1, 0)),
    ((0, -0.1197, 0.425), (0, 1, 0)),
    ((0, 0, 0.39225), (0, 1, 0)),
    ((0, 0.093, 0), (0, 0, 1)),
    ((0, 0, 0.09465), (0, 1, 0)),
]
def _rot(axis, q):
    x, y, z = axis; c, s = np.cos(q), np.sin(q); C = 1 - c
    return np.array([[c + x*x*C, x*y*C - z*s, x*z*C + y*s],
                     [y*x*C + z*s, c + y*y*C, y*z*C - x*s],
                     [z*x*C - y*s, z*y*C + x*s, c + z*z*C]])
def fk(q):
    """q: 6 joint angles in ARM order -> (position (3,), rotation (3,3)) of wrist_3_link in base_link."""
    R = np.eye(3); p = np.zeros(3)
    for (o, a), qi in zip(_CHAIN, q):
        p = p + R @ np.array(o, float); R = R @ _rot(a, qi)
    return p, R
