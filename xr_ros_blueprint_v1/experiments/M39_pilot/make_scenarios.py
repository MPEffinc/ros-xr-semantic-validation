#!/usr/bin/env python3
"""Generate the M39 input scripts for one translation axis u (tracking space; the app maps tracking xyz -> base_link
xyz with scale 0.5). Times are seconds after T0. Shared by every arm.
  grip press 2.0 (engage) | A: 3.0-5.0 translate 0.04 m/s (8 cm) | quiet 5.0-6.0 (settle; pre-event window)
  event window 6.0-7.5 | W: 6.25-7.25 translate 0.07 m/s (7 cm) + rotate 0.2 rad/s about hand-local y (0.2 rad)
  C: 9.5-10.5 translate 0.04 (4 cm) | D: 11.0-12.0 rotate 0.2 rad/s about hand-local x | E: 12.5-13.5 translate 0.04
  + rotate -0.2 rad/s about hand-local x | end 15.5
  N0 none | N1 grip released 6.0-7.5 | I1 runtime IO off 6.0-7.5, grip held | I2 = I1 + release 8.5-8.8, press 8.8
  I3 = I1 but W translation replaced by 5.75-6.2167 at 0.15 m/s (7 cm; onset 0.25 s into it)
  QF = I3 input without the deactivation (qualification of the fast normal trajectory only)
Usage: make_scenarios.py <axis label e.g. -z> <out_dir>"""
import json, sys
from pathlib import Path
AX = {'+x': [1, 0, 0], '-x': [-1, 0, 0], '+y': [0, 1, 0], '-y': [0, -1, 0], '+z': [0, 0, 1], '-z': [0, 0, -1]}
u = AX[sys.argv[1]]; out = Path(sys.argv[2]); out.mkdir(parents=True, exist_ok=True)
END = 15.5
ROT = [[6.25, 7.25, 0.2, 'y'], [11.0, 12.0, 0.2, 'x'], [12.5, 13.5, -0.2, 'x']]
TR = [[3.0, 5.0, 0.04], [6.25, 7.25, 0.07], [9.5, 10.5, 0.04], [12.5, 13.5, 0.04]]
TR_FAST = [[3.0, 5.0, 0.04], [5.75, 5.75 + 0.07 / 0.15, 0.15], [9.5, 10.5, 0.04], [12.5, 13.5, 0.04]]
G = [[2.0, END + 1]]
S = {
    'N0': dict(grip=G, trans=TR, sched=""),
    'N1': dict(grip=[[2.0, 6.0], [7.5, END + 1]], trans=TR, sched=""),
    'I1': dict(grip=G, trans=TR, sched="6.000 7.500"),
    'I2': dict(grip=[[2.0, 8.5], [8.8, END + 1]], trans=TR, sched="6.000 7.500"),
    'I3': dict(grip=G, trans=TR_FAST, sched="6.000 7.500"),
    'QF': dict(grip=G, trans=TR_FAST, sched=""),
}
for k, v in S.items():
    sc = {"duration": END + 0.5, "u": u, "grip": v['grip'], "trans": v['trans'], "rot": ROT, "sched": v['sched'], "end": END}
    (out / f"{k}.json").write_text(json.dumps(sc) + "\n")
print(out)
