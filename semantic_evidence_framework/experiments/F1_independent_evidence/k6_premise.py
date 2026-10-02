#!/usr/bin/env python3
"""K6 (pre-registered): runtime edge rule across an inactive interval, and ALVR's edge-only forwarding replayed on
the app-visible state (forward current only when changedSinceLastSync; interaction.rs L919-950)."""
import glob, json, sys
for d in sorted(glob.glob(sys.argv[1] + '/K6_r*')):
    t0 = json.load(open(d + '/setup.json'))['t0']
    sa = [json.loads(l) for l in open(d + '/sa_main.jsonl') if '"isActive"' in l]
    trans, prev, fwd, forwarded = [], None, None, []
    for x in sa:
        k = (x['isActive'], x['current'], x['changed'])
        if k != prev: trans.append((round(x['wall'] - t0, 3), *k))
        prev = k
        if x['changed']:
            fwd = x['current']; forwarded.append((round(x['wall'] - t0, 3), fwd))
    last = sa[-1]
    print(json.dumps({"run": d.split('/')[-1], "app_visible_transitions(t,isActive,current,changed)": trans,
                      "alvr_forwarded_edges": forwarded, "forwarded_state_at_end": fwd,
                      "true_runtime_state_at_end": {"isActive": last['isActive'], "current": last['current']},
                      "physical_grip": "held 1-6 s, released at 6.0 s (inside inactive window 5-7 s)"}))
