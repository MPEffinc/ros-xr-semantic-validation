#!/usr/bin/env python3
"""Smoke summary: Servo status codes per second and EE x-range of one trial log."""
import json, collections, sys
sys.path.insert(0, '/scripts'); from ur5_fk import fk
L = [json.loads(l) for l in open(sys.argv[1])]
m = [x for x in L if x['kind'] == 'meta'][0]; t0 = m['t']
b = collections.defaultdict(collections.Counter)
for x in L:
    if x['kind'] == 'status' and x['t'] >= t0: b[int((x['t'] - t0) // 1)][x['code']] += 1
print({k: dict(v) for k, v in sorted(b.items())})
xs = [fk(x['q'])[0] - m['home_ee'] for x in L if x['kind'] == 'js' and x['t'] >= t0]
print('rel min', [round(min(v[i] for v in xs), 3) for i in range(3)], 'rel max', [round(max(v[i] for v in xs), 3) for i in range(3)], 'home', [round(v, 3) for v in m['home_ee']])
