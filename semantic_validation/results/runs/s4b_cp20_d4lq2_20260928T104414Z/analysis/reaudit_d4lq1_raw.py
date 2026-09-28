#!/usr/bin/env python3
"""D4LQ2: re-audit the RETAINED D4LQ1 setup raw with the idle-time reconnect rule.

Runtime is unchanged between D4LQ1 and D4LQ2, so no Gazebo cell is repeated.
The D4LQ1 frozen verdicts (5/15) stay immutable; this is a separately
versioned determination written to analysis/d4l_setup_summary_q2.json.
"""
import csv
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import d4_setup_audit as audit  # noqa: E402  D4LQ2 analyzer

Q1 = HERE.parents[1] / 's4b_cp20_d4lq1_20260928T053735Z'
schedule = list(csv.DictReader((Q1 / 'qualification_schedule.csv').open()))
cells = []
for row in schedule:
    root = Q1 / 'raw' / row['trial_id']
    cells.append(audit.inspect(root, row['baseline'], row['regime'], row['condition'],
                               row['expect_motion'] == '1', row['delay']))
pairs = []
for delay in ('L750', 'L000'):
    b0 = Q1 / 'raw' / f'docker_b0_full_{delay}_F250_d4lq1s01'
    shim = Q1 / 'raw' / f'docker_shim_full_{delay}_F250_d4lq1s01'
    pairs.append(dict(delay=delay, **audit.pair(b0, shim, 'A000')))
ok = all(c['status'] == 'MEASUREMENT_QUALIFIED' for c in cells) and all(p['status'] == 'PASS' for p in pairs)
out = dict(label='D4LQ2_REAUDIT_OF_RETAINED_D4LQ1_RAW', status='D4L_SETUP_COMPLETE' if ok else 'D4L_SETUP_INCOMPLETE',
           cells=cells, b0_shim_equivalence=pairs, d4lq1_frozen_verdict='5/15 (immutable)')
(HERE / 'd4l_setup_summary_q2.json').write_text(json.dumps(out, indent=2, sort_keys=True) + '\n')
print(out['status'])
for c in cells:
    print(' ', c['trial'], c['status'], c.get('issues'), c.get('sender_reconnects'))
for p in pairs:
    print(' pair', p['delay'], p['status'], p['max_source_index_time_difference_ms'], p['max_final_joint_difference_rad'])
