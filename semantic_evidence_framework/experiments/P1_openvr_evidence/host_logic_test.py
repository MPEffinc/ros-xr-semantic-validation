#!/usr/bin/env python3
"""Host-only (no ROS) replay of every P1 scenario through every gate at 100 Hz.
Reports, per (scenario, gate): armed fraction in the evaluation window and the event list.
Deterministic; it is the broad-coverage layer.  Gazebo trials cover the control-path consequences."""
import json, os, sys
H = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'harness'); sys.path.insert(0, H)
import openvr as fake
from gate_core import Gate, I_FULL
WIN = {'C0_NORMAL': (5.0, 9.5), 'C1_RELEASE': (6.6, 12.0), 'C2_DEACT_CACHED': (8.0, 12.0), 'C3_TRACK_GLITCH': (6.1, 9.5),
       'C4L_RECENTER': (6.0, 12.0), 'C4S_RECENTER': (6.0, 12.0), 'C5_FAST_LEGIT': (6.0, 9.0)}
# expected armed state in the window under the declared policy (True = must stay armed, False = must be disarmed)
EXPECT = {'C0_NORMAL': True, 'C1_RELEASE': False, 'C2_DEACT_CACHED': False, 'C3_TRACK_GLITCH': True,
          'C4L_RECENTER': None, 'C4S_RECENTER': None, 'C5_FAST_LEGIT': True}
out = {}
for case in WIN:
    sc = fake.Scenario(os.path.join(os.path.dirname(H), 'scenarios', case + '.json'), 0)
    for d in ['PAUSE', 'REARM_V', 'REARM_C', 'JUMP', 'EPOCH_G']:
        g = Gate(d); a, b = WIN[case]; n = arm = 0
        for i in range(0, 1250):
            t = i / 100
            R, p = sc.raw_pose(t); _, _, ep, _ = sc.frame(t)
            obs = dict(t=t, valid=sc.valid(t), grip=sc.grip_reported(t), raw=p, R=R,
                       active=sc.active(t) if d in I_FULL else None, epoch=ep if d in I_FULL else None)
            armed, _ = g.step(obs)
            if a <= t < b: n += 1; arm += armed
        frac = arm / n
        exp = EXPECT[case]
        verdict = 'n/a' if exp is None else ('OK' if (frac == 1.0 if exp else frac == 0.0) else ('FALSE_BLOCK' if exp else 'RESIDUAL_PERMISSION'))
        out[f'{case}|{d}'] = dict(armed_fraction=round(frac, 3), verdict=verdict, events=g.events)
json.dump(out, sys.stdout, indent=1); print()
