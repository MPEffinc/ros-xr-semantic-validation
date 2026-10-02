#!/usr/bin/env python3
"""Frozen F3 analysis (PROTOCOL_F3.md §4). Usage: analyze_f3.py <raw_dir>"""
import glob, json, math, os, sys
L = lambda p: [json.loads(l) for l in open(p) if l.strip()] if os.path.exists(p) else []
rows = []
for d in sorted(glob.glob(sys.argv[1] + '/*_r*')):
    s = json.load(open(d + '/setup.json')); t0 = s['t0']
    sc = L(d + '/sched.jsonl'); off, on = sc[0]['ret'], sc[1]['call']
    obs = L(d + '/observer.jsonl')
    si = [r['wall_ns'] / 1e9 for r in obs if r['k'] == 'servo_in']
    ee = [(r['wall_ns'] / 1e9, r['p']) for r in obs if r['k'] == 'ee']
    near = lambda t: min(ee, key=lambda e: abs(e[0] - t))[1]
    g = L(d + '/gate.jsonl')
    app_t = [x['t_recv'] for x in g] if g else si          # app output: gate input (GATED) or Servo input (B0)
    pre = [t for t in app_t if t0 + 2.5 <= t < off - 0.02]
    row = dict(trial=os.path.basename(d), arm=s['arm'], load=s['load'],
               app_cmds_total=len(app_t), app_rate_hz_pre=round(len(pre) / (off - 0.02 - t0 - 2.5), 1),
               app_cmds_in_window=sum(off + 0.02 <= t <= on - 0.02 for t in app_t),
               servo_in_in_window=sum(off + 0.02 <= t <= on - 0.02 for t in si),
               servo_in_boundary=sum((off - 0.02 <= t < off + 0.02) or (on - 0.02 < t <= on + 0.02) for t in si),
               ee_disp_window_mm=round(max(math.dist(near(t), near(off)) for t, _ in ee if off <= t <= on) * 1e3, 2),
               ee_jump_after_resume_mm=round(max(math.dist(near(t), near(on)) for t, _ in ee if on <= t <= on + 1.0) * 1e3, 2))
    if g:
        adm_pre = [x for x in g if t0 + 2.5 <= x['t_recv'] < off - 0.02]
        row.update(gate_false_block_pre=sum(not x['admit'] for x in adm_pre), gate_n_pre=len(adm_pre),
                   gate_admitted_in_window=sum(x['admit'] and off + 0.02 <= x['t_recv'] <= on - 0.02 for x in g),
                   stamp_minus_recv_ms_med=round(sorted((x['stamp'] - x['t_recv']) * 1e3 for x in g)[len(g) // 2], 2))
    rows.append(row)
json.dump(rows, sys.stdout, indent=1); print()
