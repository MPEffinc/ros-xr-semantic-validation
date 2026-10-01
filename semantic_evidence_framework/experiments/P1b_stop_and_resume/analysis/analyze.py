#!/usr/bin/env python3
"""Frozen P1b analysis (derived from P1 analyze.py; only ORACLE and the angle use differ).  python3 analyze.py <raw_run_dir> > summary.json

Per trial (the attempt that reached the barrier), from observer.jsonl (EE = tf base_link->wrist_3_link):
  disp(t_ref, t_end)  = max ||p(t) - p(t_ref)||        over t in [t_ref, t_end]
  ang(t_ref, t_end)   = max angle(q(t), q(t_ref))      (deg)
  progress_x(a, b)    = p_x(b) - p_x(a)
Oracles (PROTOCOL.md section 5):
  C0  normal          FALSE_BLOCK if progress_x(5.0, 9.8) < 0.10 m        (commanded 0.20 m)
  C1  release 6.5     VIOLATION   if disp(6.6, 12.4) > 5 mm
  C2  deact 6-8       VIOLATION   if disp(8.0, 12.4) > 5 mm or ang > 2 deg
  C3  glitch 6.0-6.1  FALSE_BLOCK if progress_x(6.1, 9.5) < 0.0725 m       (50 % of commanded 0.145 m)
  C4L/C4S recenter 6  VIOLATION   if disp(6.0, 12.4) > 5 mm or ang(6.0, 12.4) > 2 deg
Also reported: servo_in message counts after the event, pause events (gate), Servo status codes, load.
"""
import json, math, os, statistics, sys
from collections import defaultdict

ORACLE = {
    'C1_RELEASE': ('disp', 6.6, 12.4, 0.005),
    'C2M_DEACT_CACHED_MOVING': ('disp', 8.0, 12.4, 0.005),
}
USE_ANGLE = set()   # P1 showed the EE orientation is still converging (confound): position only in P1b
ANG_TOL = 2.0


def qang(a, b):
    d = abs(sum(x * y for x, y in zip(a, b)))
    return math.degrees(2 * math.acos(min(1.0, d)))


def at(series, t):
    best = min(series, key=lambda r: abs(r[0] - t))
    return best[1], best[2]


def trial(d):
    s = json.load(open(os.path.join(d, 'setup.json')))
    t0 = s['t0_ns']
    rec = [json.loads(l) for l in open(os.path.join(d, 'observer.jsonl'))]
    ee = [((r['wall_ns'] - t0) / 1e9, r['p'], r['q']) for r in rec if r['k'] == 'ee']
    kind, a, b, thr = ORACLE[s['case']]
    res = dict(trial=s['trial'], case=s['case'], defense=s['defense'], load=s['load'])
    pa, qa = at(ee, a)
    win = [(t, p, q) for t, p, q in ee if a <= t <= b]
    if kind == 'disp':
        disp = max(math.dist(p, pa) for _, p, _ in win)
        ang = max(qang(q, qa) for _, _, q in win)
        res.update(disp_m=round(disp, 5), ang_deg=round(ang, 3),
                   outcome='VIOLATION' if (disp > thr or (s['case'] in USE_ANGLE and ang > ANG_TOL)) else 'PASS')
    else:
        pb, _ = at(ee, b)
        prog = pb[0] - pa[0]
        res.update(progress_m=round(prog, 5), outcome='FALSE_BLOCK' if prog < thr else 'PASS')
    res['servo_in_after'] = sum(1 for r in rec if r['k'] == 'servo_in' and (r['wall_ns'] - t0) / 1e9 >= a)
    res['status_codes'] = sorted({r['code'] for r in rec if r['k'] == 'status' and (r['wall_ns'] - t0) / 1e9 >= a})
    g = os.path.join(d, 'gate.jsonl')
    if os.path.exists(g):
        res['gate_events'] = [(round(e['t'], 3), e['armed'], e['reason']) for e in map(json.loads, open(g)) if e.get('event') == 'state']
    return res


def main():
    run = sys.argv[1]
    att = [json.loads(l) for l in open(os.path.join(run, 'attempts.jsonl'))]
    final = [x['trial'] for x in att if x['ok']]
    rows = [trial(os.path.join(run, t)) for t in final]
    cells = defaultdict(list)
    for r in rows:
        cells[(r['case'], r['defense'])].append(r)
    summary = {}
    for (c, dfn), rs in sorted(cells.items()):
        key = 'disp_m' if 'disp_m' in rs[0] else 'progress_m'
        vals = [r[key] for r in rs]
        summary[f'{c}|{dfn}'] = dict(n=len(rs), outcomes=[r['outcome'] for r in rs], metric=key,
                                     median=statistics.median(vals), min=min(vals), max=max(vals),
                                     ang_deg_max=max(r.get('ang_deg', 0) for r in rs))
    json.dump(dict(trials=rows, cells=summary, setup_attempts=len(att), final_trials=len(final)), sys.stdout, indent=1)
    print()


if __name__ == '__main__':
    main()
