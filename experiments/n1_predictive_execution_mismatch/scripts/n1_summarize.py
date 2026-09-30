#!/usr/bin/env python3
"""Aggregate results/raw/analysis.json into results/summary_*.csv and a markdown table (median over seeds)."""
import csv, json, statistics as st, sys
A = json.load(open(sys.argv[1])); out = sys.argv[2]
CONDS = ['N0', 'A', 'C', 'D', 'E', 'F', 'AC', 'AD', 'CDF', 'ACDF']; PRED = ['P0', 'PA', 'PB', 'PC', 'PD']
def trials(c): return {k: v for k, v in A['trials'].items() if k.split('_s')[0] == c}
rows = []
for key in sorted({k for t in A['trials'].values() for k in t['eval']}):
    for c in CONDS:
        T = trials(c); valid = [t for t in T.values() if t['facts']['valid']]
        for p in PRED:
            vals = [t['eval'][key][p] for t in valid if key in t['eval']]
            if not vals: continue
            med = lambda f: st.median([v[f] for v in vals if v[f] is not None]) if any(v[f] is not None for v in vals) else None
            rows.append(dict(eval=key, cond=c, pred=p, n_valid=len(vals), mean_e=med('mean'), p95_e=med('p95'), max_e=med('max'),
                             misleading_s=med('misleading_s'), misleading_seeds=sum(1 for v in vals if v['misleading_s'] > 0.1),
                             freeze=med('freeze_ratio'), post_int=med('post_intervention_mean'), stale_win=med('stale_window_mean'),
                             excess=med('max_excess_over_bound')))
with open(out + '_all.csv', 'w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
facts = []
for c in CONDS:
    T = trials(c)
    facts.append(dict(cond=c, n=len(T), valid=sum(t['facts']['valid'] for t in T.values()),
                      reset_res_max=max(t['facts']['reset_residual'] for t in T.values()),
                      halt=sum(t['facts']['halt'] for t in T.values()), interrupted=sum(t['facts']['interrupted'] for t in T.values()),
                      final_x_err_med=st.median(t['facts']['final_x_err'] for t in T.values())))
with open(out + '_trials.csv', 'w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=list(facts[0])); w.writeheader(); w.writerows(facts)
print('r_nom', A['r_nom']); print('rows', len(rows))
