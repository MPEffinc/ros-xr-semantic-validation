#!/usr/bin/env python3
"""Annotated heatmap (SVG) of median misleading duration per condition x predictor (h = 0.25 s), panels B0 and B2.
Sequential single-hue blue ramp (dataviz reference palette); zero cells use the recessive near-surface step.
Usage: make_figures.py results/summary_all.csv figures/misleading_heatmap.svg"""
import csv, math, sys
R = list(csv.DictReader(open(sys.argv[1]))); out = sys.argv[2]
CONDS = ['N0', 'A', 'C', 'D', 'E', 'F', 'AC', 'AD', 'CDF', 'ACDF']; PRED = ['P0', 'PA', 'PB', 'PC', 'PD']
LAB = {'P0': 'P0 naive', 'PA': 'PA state+input', 'PB': 'PB post-filter', 'PC': 'PC final cmd+bound', 'PD': 'PD known-pipeline model'}
RAMP = ['#f0efec', '#cde2fb', '#9ec5f4', '#6da7ec', '#3987e5', '#256abf', '#184f95', '#0d366b']
BINS = [0.0, 0.1, 0.25, 0.5, 1.0, 2.0, 5.0]           # seconds (upper edges); last bin > 5 s
def color(v):
    if v <= 1e-9: return RAMP[0], '#52514e'
    for i, b in enumerate(BINS[1:], 1):
        if v <= b: return RAMP[i], ('#0b0b0b' if i <= 3 else '#ffffff')
    return RAMP[-1], '#ffffff'
cw, ch, left, top = 62, 30, 178, 80; gap = 2
panels = [('h0.25_B0', 'B0 fresh feedback'), ('h0.25_B2', 'B2 feedback outage 4–5 s')]
W = left + len(CONDS) * cw + 20; Hp = len(PRED) * ch + 60; H = top + Hp * 2 + 70
s = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="system-ui, sans-serif">',
     '<style>.bg{fill:#fcfcfb}.ink{fill:#0b0b0b}.sec{fill:#52514e}.mut{fill:#898781}'
     '.zero{fill:#f0efec}.zt{fill:#52514e}'
     '@media (prefers-color-scheme: dark){.bg{fill:#1a1a19}.ink{fill:#ffffff}.sec{fill:#c3c2b7}.zero{fill:#383835}.zt{fill:#c3c2b7}}</style>',
     f'<rect class="bg" width="{W}" height="{H}"/>',
     f'<text class="ink" x="16" y="26" font-size="15" font-weight="600">Misleading display time per 10 s trial (median of 5 seeds, horizon 0.25 s)</text>',
     f'<text class="sec" x="16" y="44" font-size="12">Seconds with prediction error above max(2 cm, displayed bound) while the display was not frozen.</text>',
     f'<text class="sec" x="16" y="59" font-size="12">UR5 Gazebo + ros2_control + MoveIt Servo (upstream); synthetic operator and predictors.</text>']
for pi, (key, title) in enumerate(panels):
    y0 = top + pi * Hp
    s.append(f'<text class="ink" x="16" y="{y0 + 14}" font-size="13" font-weight="600">{title}</text>')
    for ci, c in enumerate(CONDS):
        s.append(f'<text class="sec" x="{left + ci * cw + cw / 2}" y="{y0 + 32}" font-size="11" text-anchor="middle">{c}</text>')
    for ri, p in enumerate(PRED):
        y = y0 + 40 + ri * ch
        s.append(f'<text class="sec" x="{left - 8}" y="{y + ch / 2 + 4}" font-size="11" text-anchor="end">{LAB[p]}</text>')
        for ci, c in enumerate(CONDS):
            r = [x for x in R if x['eval'] == key and x['cond'] == c and x['pred'] == p][0]
            v = float(r['misleading_s']); fill, ink = color(v); x = left + ci * cw
            zc = ' class="zero"' if v <= 1e-9 else f' fill="{fill}"'
            s.append(f'<rect x="{x + gap / 2}" y="{y + gap / 2}" width="{cw - gap}" height="{ch - gap}" rx="4"{zc}>'
                     f'<title>{c} / {p} / {title}: {v:.2f} s misleading; seeds &gt;0.1 s: {r["misleading_seeds"]}/5</title></rect>')
            tc = ' class="zt"' if v <= 1e-9 else f' fill="{ink}"'
            s.append(f'<text x="{x + cw / 2}" y="{y + ch / 2 + 4}" font-size="11" text-anchor="middle"{tc}>{v:.2f}</text>')
ly = H - 40
s.append(f'<text class="sec" x="16" y="{ly + 12}" font-size="11">seconds:</text>')
labels = ['0', '≤0.1', '≤0.25', '≤0.5', '≤1', '≤2', '≤5', '&gt;5']
for i, (c, l) in enumerate(zip(RAMP, labels)):
    zc = 'class="zero"' if i == 0 else f'fill="{c}"'
    s.append(f'<rect x="{80 + i * 60}" y="{ly}" width="56" height="16" rx="4" {zc}/>'
             f'<text class="sec" x="{80 + i * 60 + 28}" y="{ly + 30}" font-size="10" text-anchor="middle">{l}</text>')
s.append('</svg>'); open(out, 'w').write('\n'.join(s)); print('wrote', out)
