#!/usr/bin/env python3
"""Offline, causal evaluation of predictors P0/PA/PB/PC/PD on formal N1 logs (docs/02 §4–5, configs/protocol.yaml).

Usage (inside n1sim, numpy available):
  n1_analyze.py <formal_dir> <out_json> [--ablations]
Every predictor at tick t uses only information that would be available at t:
operator inputs up to t (operator side), and robot-side information (state, post-filter twist, Servo output,
Servo status, filter/SA flags) with age per stale level B0/B1/B2.
"""
import bisect, glob, json, os, sys
import numpy as np
sys.path.insert(0, '/scripts'); from ur5_fk import fk

H_LIST = [0.25, 0.5]; DT = 0.02
STALE = {'B0': ('delay', 0.0), 'B1': ('delay', 0.3), 'B2': ('outage', (4.0, 5.0))}
STALE_STOP = 0.2; V_INT = 0.10; EPS = 0.02
KNOWN = dict(delay={'A': 0.15, 'AC': 0.15, 'AD': 0.15, 'ACDF': 0.15}, xmax_rel=0.15, gamma=2.0,
             alpha=0.4, goal_rel=np.array([-0.03, 0.0, 0.0]), sa_win=(4.0, 9.0))
FILT = {'C', 'AC', 'CDF', 'ACDF'}; SA = {'F', 'CDF', 'ACDF'}

class Series:
    def __init__(s, ts, vals): s.t = list(ts); s.v = vals
    def at(s, t):  # latest sample with time <= t
        i = bisect.bisect_right(s.t, t) - 1
        return (s.t[i], s.v[i]) if i >= 0 else (None, None)

def load(path):
    L = [json.loads(l) for l in open(path)]
    meta = [x for x in L if x['kind'] == 'meta'][0]; t0 = meta['t']
    def ser(kind, f):
        xs = [x for x in L if x['kind'] == kind]
        return Series([x['t'] - t0 for x in xs], [f(x) for x in xs])
    d = dict(meta=meta, home=np.array(meta['home_ee']),
             js=ser('js', lambda x: np.array(x['q'])), op=ser('op', lambda x: np.array(x['v'])),
             filt=ser('after_filter', lambda x: (np.array(x['v']), x['active'])),
             sa=ser('after_sa', lambda x: x['active']),
             so=ser('servo_out', lambda x: (np.array(x['q']), np.array(x['dq']) if x['dq'] else np.zeros(6))),
             st=ser('status', lambda x: x['code']))
    d['pjs'] = Series(d['js'].t, [fk(q)[0] for q in d['js'].v])
    return d

def actual(d, t):
    T = d['pjs'].t; i = bisect.bisect_left(T, t)
    if i <= 0 or i >= len(T): return None
    a, b = T[i - 1], T[i]; w = (t - a) / (b - a) if b > a else 0
    return (1 - w) * d['pjs'].v[i - 1] + w * d['pjs'].v[i]

def robot_time(level, t):
    """Latest robot-side information time available at display time t."""
    kind, p = STALE[level]
    if kind == 'delay': return t - p
    return min(t, p[0]) if p[0] <= t < p[1] else t

def op_integral(d, a, b):
    """∫ u_op over (a, b] using 50 Hz ticks."""
    s = np.zeros(3)
    for tt, v in zip(d['op'].t, d['op'].v):
        if a < tt <= b: s += v * DT
    return s

def pd_forward(d, cond, p0, ts, t, h):
    """PD: forward-simulate known modifiers (delay, SA law, CBF law) from p0 at ts to t+h."""
    delay = KNOWN['delay'].get(cond, 0.0); p = p0.copy(); home = d['home']; tau = ts
    while tau < t + h - 1e-9:
        tin = min(tau - delay, t)            # input that reaches the robot at tau (held after t)
        _, u = d['op'].at(tin); u = np.zeros(3) if u is None else u.copy()
        if cond in SA and KNOWN['sa_win'][0] <= tau < KNOWN['sa_win'][1]:
            g = home + KNOWN['goal_rel']; u = (1 - KNOWN['alpha']) * u + KNOWN['alpha'] * np.clip(g - p, -0.1, 0.1)
        if cond in FILT:
            bound = KNOWN['gamma'] * (home[0] + KNOWN['xmax_rel'] - p[0]); u[0] = min(u[0], bound)
        p = p + u * DT; tau += DT
    return p

def evaluate(d, cond, level, h, r_nom, ablate=None):
    ab = ablate or set()
    rows = []; p0_acc = d['home'].copy()
    for t, u in zip(d['op'].t, d['op'].v):
        p0_acc = p0_acc + u * DT
        pa = actual(d, t + h)
        if pa is None: continue
        rt = robot_time(level, t)
        tq, q = d['js'].at(rt)
        if q is None: continue
        base = fk(q)[0]; age = t - tq
        preds = {}
        preds['P0'] = p0_acc + u * h
        preds['PA'] = base + op_integral(d, tq, t) + u * h
        _, fw = d['filt'].at(rt); w = fw[0] if fw else np.zeros(3)
        preds['PB'] = base + w * (t + h - tq)
        tc, cmd = d['so'].at(rt)
        _, code = d['st'].at(rt); flag_f = fw[1] if fw else False; _, flag_sa = d['sa'].at(rt)
        flagged = bool((code or 0) != 0 or flag_f or flag_sa)
        if 'no_intervention_flag' in ab: flagged = False
        r = r_nom + (V_INT * h if flagged else 0.0)
        if 'no_bound' in ab: r = 0.0
        frozen = age > STALE_STOP and 'no_stale_stop' not in ab
        if cmd is not None and 'no_final_command' not in ab:
            preds['PC'] = fk(cmd[0] + cmd[1] * (t + h - tc))[0]
        else:
            preds['PC'] = base + w * (t + h - tq)
        dab = ab & {'no_delay_model', 'no_sa_model', 'no_filter_model'}
        cond_pd = cond
        if dab:
            cond_pd = cond  # handled by overriding KNOWN below
        preds['PD'] = pd_forward_ablate(d, cond, base, tq, t, h, dab)
        for k, p in preds.items():
            e = float(np.linalg.norm(p - pa))
            bounded = k in ('PC', 'PD')
            fr = frozen and bounded
            rr = r if bounded else 0.0
            rows.append((k, t, e, fr, rr, flagged))
    return rows

def pd_forward_ablate(d, cond, p0, ts, t, h, dab):
    saved = dict(KNOWN); c = cond
    try:
        if 'no_delay_model' in dab: KNOWN['delay'] = {}
        if 'no_sa_model' in dab and c in SA: SA_ = SA - {c}; return _pd_with_sets(d, c, p0, ts, t, h, SA_, FILT)
        if 'no_filter_model' in dab and c in FILT: F_ = FILT - {c}; return _pd_with_sets(d, c, p0, ts, t, h, SA, F_)
        return pd_forward(d, c, p0, ts, t, h)
    finally:
        KNOWN.clear(); KNOWN.update(saved)

def _pd_with_sets(d, c, p0, ts, t, h, sa_set, f_set):
    global SA, FILT
    s0, f0 = SA, FILT; SA, FILT = sa_set, f_set
    try: return pd_forward(d, c, p0, ts, t, h)
    finally: SA, FILT = s0, f0

def onsets(d):
    """Intervention onset times: first tick of filter-active, SA-active, or Servo status != 0 episodes."""
    out = []
    for ser, f in ((d['filt'], lambda v: v[1]), (d['sa'], lambda v: v), (d['st'], lambda v: v != 0)):
        prev = False
        for t, v in zip(ser.t, ser.v):
            cur = bool(f(v))
            if cur and not prev and t >= 0: out.append(t)
            prev = cur
    return sorted(out)

def summarize(rows, d, level):
    ons = onsets(d); res = {}
    for k in ('P0', 'PA', 'PB', 'PC', 'PD'):
        R = [r for r in rows if r[0] == k]
        disp = [r for r in R if not r[3]]
        es = np.array([r[2] for r in disp]) if disp else np.array([np.nan])
        mis = sum(1 for r in disp if r[2] > max(EPS, r[4])) * DT
        post = [r[2] for r in disp if any(o <= r[1] < o + 0.5 for o in ons)]
        stale = [r[2] for r in disp if 4.0 <= r[1] < 5.0] if level == 'B2' else []
        res[k] = dict(mean=float(np.nanmean(es)), p95=float(np.nanpercentile(es, 95)), max=float(np.nanmax(es)),
                      misleading_s=mis, freeze_ratio=(len(R) - len(disp)) / max(1, len(R)),
                      post_intervention_mean=float(np.mean(post)) if post else None,
                      stale_window_mean=float(np.mean(stale)) if stale else None,
                      max_excess_over_bound=float(max((r[2] - r[4] for r in disp), default=0.0)))
    return res

def trial_facts(d, cond):
    m = d['meta']; codes = d['st'].v
    x_int = d['home'][0] + sum(v[0] * DT for v in d['op'].v)
    x_fin = d['pjs'].v[-1][0]
    return dict(valid=bool(m['reset_residual_rad'] < 0.01 and len(d['op'].v) >= 480 and len(d['so'].v) >= 300),
                reset_residual=m['reset_residual_rad'], n_op=len(d['op'].v), n_servo_out=len(d['so'].v),
                halt=bool(any(c == 5 for c in codes)), final_x_err=float(abs(x_fin - x_int)),
                interrupted=bool(any(c == 5 for c in codes) or abs(x_fin - x_int) > 0.05),
                status_counts={str(c): codes.count(c) for c in set(codes)}, onsets=onsets(d))

def main():
    fdir, out = sys.argv[1], sys.argv[2]; do_ab = '--ablations' in sys.argv
    files = sorted(glob.glob(os.path.join(fdir, '*_s*.jsonl')))
    data = {os.path.basename(f)[:-6]: load(f) for f in files}
    # r_nom: p95 of PC error in N0/B0, all seeds, per horizon (frozen rule)
    r_nom = {}
    for h in H_LIST:
        es = []
        for name, d in data.items():
            if name.split('_s')[0] == 'N0':
                es += [r[2] for r in evaluate(d, 'N0', 'B0', h, 0.0) if r[0] == 'PC' and not r[3]]
        r_nom[h] = float(np.percentile(es, 95))
    result = dict(r_nom=r_nom, trials={})
    for name, d in data.items():
        cond = name.split('_s')[0]; tr = dict(facts=trial_facts(d, cond), eval={})
        for h in H_LIST:
            for lv in STALE:
                tr['eval'][f'h{h}_{lv}'] = summarize(evaluate(d, cond, lv, h, r_nom[h]), d, lv)
                if do_ab and h == 0.25:
                    for ab in ('no_stale_stop', 'no_bound', 'no_intervention_flag', 'no_final_command',
                               'no_delay_model', 'no_sa_model', 'no_filter_model'):
                        tr['eval'][f'h{h}_{lv}_{ab}'] = summarize(evaluate(d, cond, lv, h, r_nom[h], {ab}), d, lv)
        result['trials'][name] = tr
        print('done', name, flush=True)
    json.dump(result, open(out, 'w'), indent=1)

if __name__ == '__main__':
    main()
