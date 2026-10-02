#!/usr/bin/env python3
"""POST-HOC decomposition of the frozen F1 linkage data (F1 files untouched). For every should_block command:
which F1 policy blocked it, and whether command freshness alone (age<=200 ms, t_gen<=t_arr+5 ms) explains the block.
Also reports totals INCLUDING boundary commands. Usage: f1_posthoc_decomposition.py <F1 raw linkage_formal dir>"""
import bisect, glob, json, sys
from collections import defaultdict
MAX_AGE, FUT, BND = 0.200, 0.005, 0.020
def L(p): return [json.loads(l) for l in open(p) if l.strip()]
agg = defaultdict(lambda: defaultdict(int))
for d in sorted(glob.glob(sys.argv[1] + '/K*_r*')):
    case = json.load(open(d + '/setup.json'))['case']
    sa = [x for x in L(d + '/sa_main.jsonl') if 'isActive' in x]; st = [x['wall'] for x in sa]; sv = [x['isActive'] for x in sa]
    tr = [st[i] for i in range(1, len(sa)) if sv[i] != sv[i - 1]]
    def near(t):
        i = bisect.bisect_left(st, t); j = min([k for k in (i - 1, i) if 0 <= k < len(st)], key=lambda k: abs(st[k] - t)); return sv[j]
    def between(a, b):
        return any(sv[k] == 0 for k in range(bisect.bisect_right(st, a), bisect.bisect_left(st, b)))
    def bnd(t):
        k = bisect.bisect_left(tr, t); return any(abs(tr[m] - t) <= BND for m in (k - 1, k) if 0 <= m < len(tr))
    for g in L(d + '/gate.jsonl'):
        tg, ta = g['t_gen'], g['t_arr']; age = ta - tg
        fresh = age <= MAX_AGE and tg <= ta + FUT
        reasons = [r for r, c in (('gen_inactive', near(tg) == 0), ('arr_inactive', near(ta) == 0),
                                  ('mid_inactive', between(tg, ta)), ('stale', age > MAX_AGE)) if c]
        sb = bool(reasons); b = bnd(tg) or bnd(ta)
        a = agg[case]; tag = 'bnd' if b else 'nb'
        a[f'{tag}_n'] += 1
        if sb:
            a[f'{tag}_should_block'] += 1
            for p in ('C_ARRIVAL', 'C_INTERVAL', 'D_STREAM', 'B0'):
                a[f'{tag}_pass_{p}'] += g['dec'][p]
            a[f'{tag}_pass_FRESH_ONLY'] += fresh
            a[f'{tag}_pass_FRESH_AND_C_ARRIVAL'] += fresh and g['dec']['C_ARRIVAL']
            if g['dec']['C_INTERVAL'] is False:
                a[f'{tag}_cint_block_explained_by_freshness'] += (not fresh)
            key = '+'.join(sorted(reasons)); a[f'{tag}_reason:{key}'] += 1
        else:
            a[f'{tag}_should_admit'] += 1
            a[f'{tag}_falseblock_C_INTERVAL'] += (not g['dec']['C_INTERVAL'])
json.dump({k: dict(v) for k, v in agg.items()}, sys.stdout, indent=1); print()
