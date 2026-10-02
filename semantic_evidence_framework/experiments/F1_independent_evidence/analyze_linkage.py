#!/usr/bin/env python3
"""Frozen F1 linkage scoring (PROTOCOL_LINKAGE.md §5). Usage: analyze_linkage.py <raw_dir> > summary.json"""
import bisect, glob, json, os, statistics, sys
from collections import defaultdict
POL = ['B0', 'D_DIRECT', 'D_STREAM', 'C_ARRIVAL', 'C_INTERVAL', 'C_ANY']
BOUND_S, MAX_AGE = 0.020, 0.200


def load(p):
    return [json.loads(l) for l in open(p) if l.strip()]


def run(d):
    s = json.load(open(d + '/setup.json')); t0 = s['t0']
    sa = [x for x in load(d + '/sa_main.jsonl') if 'isActive' in x]
    st, sv = [x['wall'] for x in sa], [x['isActive'] for x in sa]
    trans = [st[i] for i in range(1, len(sa)) if sv[i] != sv[i - 1]]

    def inactive(t):
        i = bisect.bisect_left(st, t)
        cands = [j for j in (i - 1, i) if 0 <= j < len(st)]
        j = min(cands, key=lambda j: abs(st[j] - t))
        return sv[j] == 0

    def inactive_between(a, b):
        i, j = bisect.bisect_right(st, a), bisect.bisect_left(st, b)
        return any(sv[k] == 0 for k in range(i, j))

    def boundary(t):
        k = bisect.bisect_left(trans, t)
        return any(abs(trans[m] - t) <= BOUND_S for m in (k - 1, k) if 0 <= m < len(trans))

    out = []
    for g in load(d + '/gate.jsonl'):
        tg, ta = g['t_gen'], g['t_arr']
        sb = inactive(tg) or inactive(ta) or inactive_between(tg, ta) or (ta - tg) > MAX_AGE
        out.append(dict(seq=g['seq'], tg=tg - t0, ta=ta - t0, boundary=boundary(tg) or boundary(ta), should_block=sb,
                        dec=g['dec'], dt=g['dt_ns']))
    # evidence latency: io action call -> first matching state seen by the runtime path (collector) and by the app
    acts = load(d + '/actions.jsonl') if os.path.exists(d + '/actions.jsonl') else []
    col = [x for x in load(d + '/collector.jsonl') if x.get('name') == 'sa_main'] if os.path.exists(d + '/collector.jsonl') else []
    lat = []
    for a in acts:
        if a['action'] not in ('io_off_call', 'io_on_call'):
            continue
        want = 0 if a['action'] == 'io_off_call' else 1
        tc = next((x['wall'] for x in col if x['wall'] >= a['wall'] and int(x['io'] and not x['inputs_blocked']) == want), None)
        ts = next((x['wall'] for x in sa if x['wall'] >= a['wall'] and x['isActive'] == want), None)
        lat.append(dict(action=a['action'], collector_ms=None if tc is None else round((tc - a['wall']) * 1e3, 2),
                        app_ms=None if ts is None else round((ts - a['wall']) * 1e3, 2)))
    return s, out, trans, lat


def main():
    raw = sys.argv[1]
    per_case = defaultdict(lambda: {p: defaultdict(int) for p in POL})
    dt_all = defaultdict(list); runs = []
    for d in sorted(glob.glob(raw + '/K*_r*')):
        s, rows, trans, lat_ev = run(d)
        runs.append(dict(run=os.path.basename(d), case=s['case'], n=len(rows), load=s['load'],
                         transitions=[round(t - s['t0'], 3) for t in trans], evidence_latency=lat_ev))
        for r in rows:
            for p in POL:
                c = per_case[s['case']][p]
                adm = r['dec'][p]
                if r['boundary']:
                    c['boundary'] += 1; c['boundary_admitted'] += adm; continue
                if r['should_block']:
                    c['should_block'] += 1; c['dangerous_pass'] += adm
                else:
                    c['should_admit'] += 1; c['false_block'] += (not adm)
                    if s['case'] == 'K5a' and 5.0 <= r['ta'] < 6.2:
                        c['false_block_in_outage_window'] += (not adm)
                dt_all[p].append(r['dt'][p])
    lat = {p: dict(p50_us=round(statistics.median(v) / 1e3, 1), p95_us=round(sorted(v)[int(0.95 * (len(v) - 1))] / 1e3, 1))
           for p, v in dt_all.items()}
    json.dump(dict(runs=runs, cases={k: {p: dict(v) for p, v in d.items()} for k, d in per_case.items()},
                   gate_decision_latency=lat), sys.stdout, indent=1)
    print()


if __name__ == '__main__':
    main()
