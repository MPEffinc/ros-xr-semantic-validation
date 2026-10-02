#!/usr/bin/env python3
"""POST-HOC (written after the frozen F3 analysis): command-level resume jump at Servo input, EE motion before the window,
and Servo singularity e-stop counts after resume (masking confound)."""
import glob, json, math, os, sys
for d in sorted(glob.glob(sys.argv[1] + '/*_r*')):
    t0 = json.load(open(d + '/setup.json'))['t0']; sc = [json.loads(l) for l in open(d + '/sched.jsonl')]
    off, on = sc[0]['ret'], sc[1]['call']
    obs = [json.loads(l) for l in open(d + '/observer.jsonl')]
    si = [(r['wall_ns'] / 1e9, r['p']) for r in obs if r['k'] == 'servo_in']
    ee = [(r['wall_ns'] / 1e9, r['p']) for r in obs if r['k'] == 'ee']
    before = [p for t, p in si if t < off][-1]; after = [p for t, p in si if t > on][0]
    near = lambda t: min(ee, key=lambda e: abs(e[0] - t))[1]
    estop_after = sum(1 for r in obs if r['k'] == 'status' and r['code'] == 2 and r['wall_ns'] / 1e9 > on)
    print(json.dumps(dict(trial=os.path.basename(d), cmd_jump_at_resume_mm=round(math.dist(before, after) * 1e3, 1),
                          ee_progress_4_to_7_5_mm=round((near(t0 + 7.5)[0] - near(t0 + 4.0)[0]) * 1e3, 1),
                          servo_halt_for_singularity_status_after_resume=estop_after)))
