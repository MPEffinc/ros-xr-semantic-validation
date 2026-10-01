#!/usr/bin/env python3
"""POST-HOC diagnostics for P1, written after the frozen analysis was run.

These do NOT replace the frozen outcomes in p1_summary.json. They separate:
  (1) command level: target jump at the app output vs Servo input, and how many commands were forwarded
      after the event;
  (2) the orientation-settling confound: EE rotation rate before each event;
  (3) the Servo singularity emergency-stop count per trial (servo.log);
  (4) C1 timing: Servo output after release and the EE x trajectory.
"""
import glob, json, math, os, sys
R = sys.argv[1]
def qang(a, b): return math.degrees(2 * math.acos(min(1, abs(sum(x * y for x, y in zip(a, b))))))
EV = {'C1_RELEASE': 6.5, 'C2_DEACT_CACHED': 8.0, 'C3_TRACK_GLITCH': 6.0, 'C4L_RECENTER': 6.0, 'C4S_RECENTER': 6.0, 'C0_NORMAL': 5.0}
out = []
for d in sorted(glob.glob(R + '/*/')):
    if not os.path.exists(d + 'done.json'): continue
    s = json.load(open(d + 'setup.json')); t0 = s['t0_ns']; c = s['case']; ev = EV[c]
    rec = [json.loads(l) for l in open(d + 'observer.jsonl')]
    T = lambda r: (r['wall_ns'] - t0) / 1e9
    si = [(T(r), r['p'], r['q']) for r in rec if r['k'] == 'servo_in']
    app = [(T(r), r['p'], r['q']) for r in rec if r['k'] == 'app']
    ee = [(T(r), r['p'], r['q']) for r in rec if r['k'] == 'ee']
    src = si if not app else app
    pre = [x for x in src if (5.5 <= x[0] < 6.0 if c == 'C2_DEACT_CACHED' else ev - 0.5 <= x[0] < ev - 0.02)]
    post = [x for x in src if x[0] >= ev]
    row = dict(trial=s['trial'], case=c, defense=s['defense'])
    if pre and post:
        row['cmd_jump_pos_m'] = round(max(math.dist(x[1], pre[-1][1]) for x in post), 4)
        row['cmd_jump_rot_deg'] = round(max(qang(x[2], pre[-1][2]) for x in post), 2)
    row['forwarded_after_event'] = sum(1 for x in si if x[0] >= ev)
    near = lambda t: min(ee, key=lambda e: abs(e[0] - t))
    row['ee_rot_rate_deg_s_before_event'] = round(qang(near(ev)[2], near(ev - 1.0)[2]) / 1.0, 2)
    row['singularity_estops'] = sum('emergency stop' in l for l in open(d + 'servo.log', errors='ignore'))
    row['servo_out_after_event'] = sum(1 for r in rec if r['k'] == 'servo_out' and T(r) >= ev)
    if c == 'C1_RELEASE':
        row['ee_x'] = {str(t): round(near(t)[1][0], 4) for t in (6.5, 6.6, 6.8, 7.0, 7.5)}
        row['last_target_x'] = round(si[-1][1][0], 4)
    out.append(row)
json.dump(out, sys.stdout, indent=1); print()
