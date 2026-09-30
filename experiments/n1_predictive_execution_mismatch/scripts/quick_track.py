#!/usr/bin/env python3
"""Smoke: EE displacement (actual) vs integrated operator command over time for one trial log."""
import json, sys
sys.path.insert(0, '/scripts'); from ur5_fk import fk
import numpy as np
L = [json.loads(l) for l in open(sys.argv[1])]
m = [x for x in L if x['kind'] == 'meta'][0]; t0 = m['t']; home = np.array(m['home_ee'])
js = [(x['t'] - t0, fk(x['q'])[0] - home) for x in L if x['kind'] == 'js' and x['t'] >= t0]
op = [(x['t'] - t0, np.array(x['v'])) for x in L if x['kind'] == 'op']
so = [(x['t'] - t0, fk(x['q'])[0] - home) for x in L if x['kind'] == 'servo_out' and x['t'] >= t0]
integ = np.zeros(3); k = 0
for T in np.arange(0, 11, 0.5):
    while k < len(op) and op[k][0] <= T: integ = integ + op[k][1] * 0.02; k += 1
    a = min(js, key=lambda z: abs(z[0] - T))[1]; s = min(so, key=lambda z: abs(z[0] - T))[1] if so else None
    print(f"t={T:4.1f} cmd_int={np.round(integ,3)} actual={np.round(a,3)} servo_cmd={np.round(s,3) if s is not None else None}")
