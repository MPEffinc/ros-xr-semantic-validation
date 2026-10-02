#!/usr/bin/env python3
"""Offline pre-flight: for every IK solution of the app's fixed engage pose (0.4, 0, 0.3, robot_home_rot) and every
candidate translation axis, sweep the union workspace every arm can command in the frozen scripts
(d in [-0.005, 0.125] m along the axis; EE orientation H*Ry(a)*Rx(b), a,b in [0, 0.2] rad, body frame) by IK
continuation from the start solution, and report max cond(J), min distance to the wrist (|sin q5|) singularity and
branch continuity. Neutral: uses only the normal-trajectory workspace, no interruption outcome. Writes JSON to stdout."""
import json, sys, itertools
import numpy as np
from scipy.spatial.transform import Rotation as R
sys.path.insert(0, sys.argv[1] if len(sys.argv) > 1 else '/m39/harness')
import ur5_kin as K
H = R.from_euler('xyz', [0, 1.57, 0]); P = np.array([0.4, 0, 0.3]); Q0 = [0, 0, 1.4232, 0.243, 4.6863, 1.6315]
def wrap(q): return (np.asarray(q) + np.pi) % (2 * np.pi) - np.pi
rng = np.random.default_rng(0); sols = []
for k in range(3000):
    q, ok = K.ik(P, H.as_matrix(), rng.uniform(-np.pi, np.pi, 6) if k else Q0)
    if ok:
        q = wrap(q)
        if not any(np.allclose(q, s, atol=1e-3) for s in sols): sols.append(q)
AXES = {'+x': (1, 0, 0), '-x': (-1, 0, 0), '+y': (0, 1, 0), '-y': (0, -1, 0), '+z': (0, 0, 1), '-z': (0, 0, -1)}
D = np.linspace(-0.005, 0.125, 27); A = np.linspace(0, 0.2, 5)
res = []
for si, s in enumerate(sols):
    setup = float(np.abs(wrap(np.array(s) - wrap(Q0))).max())
    for name, u in AXES.items():
        worst, minw, maxjump, fail = 0.0, 9.0, 0.0, False
        for a, b in itertools.product(A, A):
            Rt = (H * R.from_euler('y', a) * R.from_euler('x', b)).as_matrix(); q = np.array(s)
            for d in D:
                qn, ok = K.ik(P + d * np.array(u), Rt, q)
                if not ok: fail = True; break
                maxjump = max(maxjump, float(np.abs(qn - q).max())); q = qn
                worst = max(worst, K.cond(q)); minw = min(minw, abs(np.sin(q[4])))
            if fail: break
        res.append({"sol": si, "q": np.round(s, 4).tolist(), "setup_max_dq": round(setup, 3), "axis": name, "ik_fail": fail,
                    "max_cond": round(worst, 2), "min_abs_sin_q5": round(minw, 3), "max_step_dq": round(maxjump, 3)})
json.dump({"solutions": [np.round(s, 4).tolist() for s in sols], "cond_start": [round(K.cond(s), 2) for s in sols], "rows": res}, sys.stdout, indent=1)
