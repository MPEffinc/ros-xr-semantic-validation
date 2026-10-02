#!/usr/bin/env python3
"""TEST-ONLY deterministic check of C1's re-basing against the app's command semantics (quest_teleop.py: position =
anchor + 0.5*(hand - hand_at_engage) in base axes; rotation = R_anchor * (Q_engage^-1 * Q_hand)).
Expected after a resume at t_r with the arm held at E: p = E.p + 0.5*(h(t) - h(t_r)), R = E.R * Q(t_r)^-1 * Q(t)
(exactly what a fresh re-anchor to the measured EE would give, i.e. B1's mapping).
Compares C1's decomposition with two plausible alternatives: full SE(3) left product (Delta*T) and right correction."""
import json, sys
import numpy as np
from scipy.spatial.transform import Rotation as R
sys.path.insert(0, "/m39/arms"); sys.path.insert(0, "/m39/harness")
H = R.from_euler('xyz', [0, 1.57, 0]); A = np.array([0.4, 0, 0.3]); u = np.array([0, 0, -1.0])
def hand(t):  # translation along u; rotation about local y during [6.25,7.25), about local x during [11,12), [12.5,13.5)
    d = 0.04 * np.clip(t - 3, 0, 2) + 0.07 * np.clip(t - 6.25, 0, 1) + 0.04 * np.clip(t - 9.5, 0, 1) + 0.04 * np.clip(t - 12.5, 0, 1)
    q = R.from_rotvec([0, 0.2 * np.clip(t - 6.25, 0, 1), 0]) * R.from_rotvec([0.2 * np.clip(t - 11, 0, 1), 0, 0]) * R.from_rotvec([-0.2 * np.clip(t - 12.5, 0, 1), 0, 0])
    return np.array([0.2, 1.0, -0.3]) + d * u, q
he, qe = hand(2.0)
def app(t):  # original app, engaged at 2.0, offset retained through the interruption (B0 / C1 input)
    h, q = hand(t); return A + 0.5 * (h - he), H * (qe.inv() * q)
E_p, E_R = app(6.0)            # arm held at the pre-interruption target
t_r = 7.6; F_p, F_R = app(t_r)  # first command after re-admission
def expected(t):
    h, q = hand(t); hr, qr = hand(t_r); return E_p + 0.5 * (h - hr), E_R * (qr.inv() * q)
dp = E_p - F_p; C = E_R * F_R.inv()
variants = {
    "c1_decomposed": lambda p, Rm: (p + dp, C * Rm),
    "full_se3_left": lambda p, Rm: (E_R.apply(F_R.inv().apply(p - F_p)) + E_p, C * Rm),
    "right_correction": lambda p, Rm: (p + dp, Rm * (F_R.inv() * E_R)),
}
res = {"jump_at_resume_mm": float(np.linalg.norm(F_p - E_p) * 1000), "jump_at_resume_deg": float(np.degrees((F_R * E_R.inv()).magnitude()))}
for k, f in variants.items():
    ep, er = 0.0, 0.0
    for t in np.linspace(t_r, 15.0, 300):
        p, Rm = f(*app(t)); xp, xR = expected(t)
        ep = max(ep, float(np.linalg.norm(p - xp) * 1000)); er = max(er, float(np.degrees((Rm * xR.inv()).magnitude())))
    res[k] = {"max_pos_err_mm": round(ep, 6), "max_rot_err_deg": round(er, 6)}
from c1_transition import Rebase  # the code under test
rb = Rebase({"p": list(E_p), "q": list(E_R.as_quat())}, {"p": list(F_p), "q": list(F_R.as_quat())})
ep, er = 0.0, 0.0
for t in np.linspace(t_r, 15.0, 300):
    p, Rm = app(t); p2, q2 = rb.apply(list(p), list(Rm.as_quat())); xp, xR = expected(t)
    ep = max(ep, float(np.linalg.norm(np.array(p2) - xp) * 1000)); er = max(er, float(np.degrees((R.from_quat(q2) * xR.inv()).magnitude())))
res["c1_code"] = {"max_pos_err_mm": round(ep, 6), "max_rot_err_deg": round(er, 6)}
res["pass"] = res["c1_code"]["max_pos_err_mm"] < 1e-3 and res["c1_code"]["max_rot_err_deg"] < 1e-3
print(json.dumps(res, indent=1))
