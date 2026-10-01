#!/usr/bin/env python3
"""Generate the frozen P1 scenarios (times in s from P1_T0_NS; end 12.5 s).
Common: grip pressed at 0.5 s (rising edge = initial engage), hand still until 5.0 s so the arm
settles at the app's absolute engage target (S5 #10 behaviour, not under test)."""
import json, os
D = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'scenarios')
END = 99.0
def sc(**kw):
    base = dict(hand_velocity=[], invalid=[], grip_reported=[[0.5, END]], grip_truth=[[0.5, END]], inactive=[], recenters=[])
    base.update(kw); return base
S = {
 'C0_NORMAL':      sc(hand_velocity=[[5.0, 9.0, [0.10, 0, 0]]]),
 'C1_RELEASE':     sc(hand_velocity=[[5.0, 7.0, [0.40, 0, 0]]], grip_reported=[[0.5, 6.5]], grip_truth=[[0.5, 6.5]]),
 'C2_DEACT_CACHED':sc(hand_velocity=[[5.0, 8.0, [0.10, 0, 0]]], invalid=[[6.0, 8.0]], inactive=[[6.0, 8.0]],
                      grip_reported=[[0.5, END]], grip_truth=[[0.5, 6.0]]),
 'C3_TRACK_GLITCH':sc(hand_velocity=[[5.0, 9.0, [0.10, 0, 0]]], invalid=[[6.0, 6.1]]),
 'C4L_RECENTER':   sc(recenters=[{'t': 6.0, 'd': [0.30, 0.0, 0.10], 'yaw_deg': 30.0}]),
 'C4S_RECENTER':   sc(recenters=[{'t': 6.0, 'd': [0.03, 0.0, 0.0], 'yaw_deg': 0.0}]),
 'C5_FAST_LEGIT':  sc(hand_velocity=[[6.0, 6.1, [3.0, 0, 0]]]),   # host-only
}
os.makedirs(D, exist_ok=True)
for k, v in S.items():
    json.dump(v, open(os.path.join(D, k + '.json'), 'w'), indent=1, sort_keys=True)
print(sorted(S))
