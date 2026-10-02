#!/usr/bin/env python3
"""UR5 (P1 workspace ur5_description, xacro-expanded) forward kinematics, Jacobian and numerical IK for
base_link -> wrist_3_link.  Joint origins/axes are copied from the expanded URDF (all origin rpy = 0).
Used only for the M39 pre-flight start-configuration search and offline path checks; the run itself
uses tf from the simulator.  Condition number = cond(J) of the 6x6 geometric Jacobian (linear rows in m,
angular rows in rad), the quantity MoveIt Servo 2.12.4 compares against lower/hard singularity thresholds."""
import numpy as np
from scipy.spatial.transform import Rotation as R

JOINTS = ["shoulder_pan_joint", "shoulder_lift_joint", "elbow_joint", "wrist_1_joint", "wrist_2_joint", "wrist_3_joint"]
# (origin xyz in parent, axis in child) from ur5.urdf (xacro of ur5_robot.urdf.xacro)
CHAIN = [((0, 0, 0.089159), (0, 0, 1)), ((0, 0.13585, 0), (0, 1, 0)), ((0, -0.1197, 0.425), (0, 1, 0)),
         ((0, 0, 0.39225), (0, 1, 0)), ((0, 0.093, 0), (0, 0, 1)), ((0, 0, 0.09465), (0, 1, 0))]
LIMIT = 6.28319


def fk(q, upto=6):
    """Return (p, Rm, frames) with frames = [(joint origin, joint axis in base)] for the Jacobian."""
    T = np.eye(4); frames = []
    for i in range(upto):
        o, a = CHAIN[i]
        Tj = np.eye(4); Tj[:3, 3] = o
        T = T @ Tj
        ax = T[:3, :3] @ np.array(a, float)
        frames.append((T[:3, 3].copy(), ax))
        Rj = np.eye(4); Rj[:3, :3] = R.from_rotvec(np.array(a, float) * q[i]).as_matrix()
        T = T @ Rj
    return T[:3, 3].copy(), T[:3, :3].copy(), frames


def jacobian(q):
    p, _, frames = fk(q)
    J = np.zeros((6, 6))
    for i, (o, ax) in enumerate(frames):
        J[:3, i] = np.cross(ax, p - o); J[3:, i] = ax
    return J


def cond(q):
    s = np.linalg.svd(jacobian(q), compute_uv=False)
    return float(s[0] / s[-1]) if s[-1] > 1e-12 else float("inf")


def pose_err(q, p_t, R_t):
    p, Rm, _ = fk(q)
    e_rot = R.from_matrix(R_t @ Rm.T).as_rotvec()
    return np.concatenate([p_t - p, e_rot])


def ik(p_t, R_t, seed, iters=400, lam=0.02):
    q = np.array(seed, float)
    for _ in range(iters):
        e = pose_err(q, p_t, R_t)
        if np.linalg.norm(e[:3]) < 1e-6 and np.linalg.norm(e[3:]) < 1e-6:
            return q, True
        J = jacobian(q)
        dq = J.T @ np.linalg.solve(J @ J.T + lam ** 2 * np.eye(6), e)
        q = q + np.clip(dq, -0.2, 0.2)
    e = pose_err(q, p_t, R_t)
    return q, bool(np.linalg.norm(e[:3]) < 1e-5 and np.linalg.norm(e[3:]) < 1e-5)
