#!/usr/bin/env python3
"""P1b scenarios. C1 identical to P1. C2M = P1's C2 with the hand moving continuously +0.10 m/s
from 5.0 to 11.0 s, so that after the resume at 8.0 s the arm is commanded to move. In P1 a stationary
hand let Servo's singularity stop mask the consequence."""
import json, os
D = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'scenarios'); END = 99.0
def sc(**kw):
    b = dict(hand_velocity=[], invalid=[], grip_reported=[[0.5, END]], grip_truth=[[0.5, END]], inactive=[], recenters=[]); b.update(kw); return b
S = {'C1_RELEASE': sc(hand_velocity=[[5.0, 7.0, [0.40, 0, 0]]], grip_reported=[[0.5, 6.5]], grip_truth=[[0.5, 6.5]]),
     'C2M_DEACT_CACHED_MOVING': sc(hand_velocity=[[5.0, 11.0, [0.10, 0, 0]]], invalid=[[6.0, 8.0]], inactive=[[6.0, 8.0]],
                                   grip_reported=[[0.5, END]], grip_truth=[[0.5, 6.0]])}
os.makedirs(D, exist_ok=True)
for k, v in S.items(): json.dump(v, open(os.path.join(D, k + '.json'), 'w'), indent=1, sort_keys=True)
print(sorted(S))
