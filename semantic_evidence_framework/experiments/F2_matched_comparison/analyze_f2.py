#!/usr/bin/env python3
"""Frozen F2 scoring (PROTOCOL_F2.md §4). Usage: analyze_f2.py <raw_dir> > f2_summary.json
Truth = runtime-applied inactive windows [ret_off, call_on] from sched.jsonl (persistent libmonado connection).
Each delivered command gets categories:
  stale (age>200ms), dup (not the first arrival of its seq), ooo (seq < max seq already arrived),
  end_inactive (t_gen or t_arr inside a window), mid_only (window overlaps (t_gen,t_arr) but endpoints active).
S_endpoint = stale|dup|ooo|end_inactive ; S_lifetime = S_endpoint|mid_only.
boundary = t_gen or t_arr within 20 ms of any window edge (call times); excluded from the main counts, reported.
M4 (windows of 5-40 ms) is additionally reported per window."""
import glob, json, os, sys
from collections import defaultdict
ARMS = ['B0', 'FRESH', 'ARR', 'GEN_ARR', 'INTERVAL', 'ORD', 'ARR_ORD', 'GEN_ARR_ORD', 'INTERVAL_ORD']
MAX_AGE, BND = 0.200, 0.020
L = lambda p: [json.loads(l) for l in open(p) if l.strip()] if os.path.exists(p) else []


def windows(d):
    s = [x for x in L(d + '/sched.jsonl') if 'kind' in x]
    return [(s[i]['ret'], s[i + 1]['call'], s[i]['call'], s[i + 1]['ret']) for i in range(0, len(s) - 1, 2)]


def main():
    agg = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
    m4 = defaultdict(lambda: defaultdict(int)); outage_fb = defaultdict(lambda: defaultdict(int)); dts = defaultdict(list)
    runs = []
    for d in sorted(glob.glob(sys.argv[1] + '/*_r*')):
        st = json.load(open(d + '/setup.json')); case = st['case']; t0 = st['t0']
        W = windows(d); edges = [e for w in W for e in (w[2], w[1])]
        outs = L(d + '/outage.jsonl'); O = [(outs[i]['stop'], outs[i + 1]['cont']) for i in range(0, len(outs) - 1, 2)]
        col = [x for x in L(d + '/collector.jsonl') if x.get('name') == 'sa_main']
        inside = lambda t: any(a <= t <= b for a, b, _, _ in W)
        overlap = lambda g, r: any(a < r and b > g for a, b, _, _ in W)
        near_edge = lambda t: any(abs(t - e) <= BND for e in edges)
        seen, maxseq = set(), -1
        G = L(d + '/gate.jsonl'); runs.append(dict(run=os.path.basename(d), case=case, n=len(G), windows=len(W), load=st['load']))
        for g in G:
            tg, ta, s = g['t_gen'], g['t_arr'], g['seq']
            cat = set()
            if ta - tg > MAX_AGE: cat.add('stale')
            if s in seen: cat.add('dup')
            if s < maxseq: cat.add('ooo')
            seen.add(s); maxseq = max(maxseq, s)
            if inside(tg) or inside(ta): cat.add('end_inactive')
            elif overlap(tg, ta): cat.add('mid_only')
            s_end = bool(cat - {'mid_only'}); s_life = bool(cat)
            bnd = near_edge(tg) or near_edge(ta)
            for arm in ARMS:
                adm = g['dec'][arm]; a = agg[case][arm]
                if bnd:
                    a['boundary'] += 1; a['boundary_admitted'] += adm
                    if s_life: a['boundary_should_block_life'] += 1; a['boundary_pass_life'] += adm
                    continue
                for defn, sb in (('end', s_end), ('life', s_life)):
                    if sb:
                        a[f'should_block_{defn}'] += 1; a[f'pass_{defn}'] += adm
                    else:
                        a[f'should_admit_{defn}'] += 1; a[f'false_block_{defn}'] += (not adm)
                        if any(x <= ta <= y + 0.05 for x, y in O): outage_fb[case][arm] += (not adm)
                for c in cat:
                    a[f'cat_{c}_n'] += 1; a[f'cat_{c}_pass'] += adm
                dts[arm].append(g['dt_ns'][arm])
        if case == 'M4':
            for (a_, b_, c_off, c_on) in W:
                dur = round((b_ - a_) * 1e3); key = f'{dur}ms'
                m4[key]['windows'] += 1
                m4[key]['collector_saw'] += any(a_ - 0.001 <= x['wall'] <= b_ + 0.006 and not (x['io'] and not x['inputs_blocked']) for x in col)
                life = [g for g in G if g['t_gen'] < b_ and g['t_arr'] > a_]
                m4[key]['cmds_overlapping'] += len(life)
                for arm in ARMS:
                    m4[key][f'pass_{arm}'] += sum(g['dec'][arm] for g in life)
    lat = {a: dict(p50_us=round(sorted(v)[len(v) // 2] / 1e3, 1), p95_us=round(sorted(v)[int(0.95 * (len(v) - 1))] / 1e3, 1)) for a, v in dts.items()}
    json.dump(dict(runs=runs, cases={c: {a: dict(v) for a, v in d.items()} for c, d in agg.items()},
                   m4_per_window={k: dict(v) for k, v in m4.items()}, outage_false_blocks={c: dict(v) for c, v in outage_fb.items()},
                   decision_latency=lat), sys.stdout, indent=1)
    print()


if __name__ == '__main__':
    main()
