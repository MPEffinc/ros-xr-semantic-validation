#!/usr/bin/env python3
"""EXPLORATORY (post-hoc, not part of the frozen decision rules).
(1) When does PC exceed max(eps, r) in N0/B0? (2) PE = PD's forward model of known modifiers, seeded from the
final executable command (Servo output) instead of /joint_states; same flag/bound/stale stop.
Usage: n1_exploratory.py <formal_dir> <analysis.json> <out.json>"""
import glob, json, os, sys
import numpy as np
sys.path.insert(0, '/scripts')
import n1_analyze as A
from ur5_fk import fk
formal, ana, out = sys.argv[1:4]; r_nom = {float(k): v for k, v in json.load(open(ana))['r_nom'].items()}
res = {'pc_excess_times_N0_B0': {}, 'PE': {}}
for f in sorted(glob.glob(os.path.join(formal, '*_s*.jsonl'))):
    name = os.path.basename(f)[:-6]; cond = name.split('_s')[0]; d = A.load(f)
    if cond == 'N0':
        rows = A.evaluate(d, cond, 'B0', 0.25, r_nom[0.25])
        res['pc_excess_times_N0_B0'][name] = [round(r[1], 2) for r in rows if r[0] == 'PC' and not r[3] and r[2] > max(A.EPS, r[4])]
    for h in (0.25, 0.5):
        for lv in ('B0', 'B2'):
            mis = 0.0; es = []; fz = 0; n = 0
            for t, u in zip(d['op'].t, d['op'].v):
                pa = A.actual(d, t + h)
                if pa is None: continue
                rt = A.robot_time(lv, t); tq, q = d['js'].at(rt); tc, cmd = d['so'].at(rt)
                if q is None or cmd is None: continue
                n += 1
                if t - tq > A.STALE_STOP: fz += 1; continue
                base = fk(cmd[0])[0]
                p = A.pd_forward(d, cond, base, tc, t, h)
                _, code = d['st'].at(rt); _, fw = d['filt'].at(rt); _, fsa = d['sa'].at(rt)
                flagged = bool((code or 0) != 0 or (fw and fw[1]) or fsa)
                r = r_nom[h] + (A.V_INT * h if flagged else 0.0)
                e = float(np.linalg.norm(p - pa)); es.append(e)
                if e > max(A.EPS, r): mis += A.DT
            res['PE'].setdefault(f'h{h}_{lv}', {})[name] = dict(misleading_s=mis, mean=float(np.mean(es)), max=float(np.max(es)), freeze=fz / max(1, n))
json.dump(res, open(out, 'w'), indent=1)
import statistics as st
for key, v in res['PE'].items():
    by = {}
    for name, m in v.items(): by.setdefault(name.split('_s')[0], []).append(m)
    print(key, ' '.join(f"{c}:{st.median(x['misleading_s'] for x in L):.2f}({sum(x['misleading_s']>0.1 for x in L)})" for c, L in by.items()))
print('PC>bound times N0/B0:', {k: v[:12] for k, v in res['pc_excess_times_N0_B0'].items()})
