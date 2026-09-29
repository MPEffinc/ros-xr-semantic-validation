#!/usr/bin/env python3
"""Drive the frozen D5 setup inspect() over the D5Q2 schedule (no B0/shim rows).

d5_setup_audit.main() assumes a B0/shim row; the frozen inspect() criteria are
used unchanged here. The D5Q1 B0/shim pair (PASS) is the equivalence control.
"""
import csv
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import d5_setup_audit as audit  # noqa: E402

ROOT = HERE.parent
cells = []
for row in csv.DictReader((ROOT / 'qualification_schedule.csv').open()):
    attempts = [ROOT / 'raw' / (row['trial_id'] + s) for s in ('', '_setup02', '_setup03')
                if (ROOT / 'raw' / (row['trial_id'] + s)).exists()]
    chosen = next((r for r in attempts if (r / 'barrier.json').exists()), None)
    out = (audit.inspect(chosen, row['baseline'], row['regime'], True) if chosen else
           dict(trial=row['trial_id'], status='BLOCKED_MEASUREMENT' if attempts else 'NOT_RUN'))
    out['attempts'] = [r.name for r in attempts]
    cells.append(out)
ok = all(c['status'] == 'MEASUREMENT_QUALIFIED' for c in cells)
result = dict(status='D5Q2_TARGETED_CELLS_QUALIFIED' if ok else 'D5Q2_INCOMPLETE', cells=cells,
              equivalence_control='D5Q1 B0/shim pair PASS (0.051625 ms, 0.004841 rad), code path unchanged')
(HERE / 'd5_setup_summary.json').write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
print(result['status'])
for c in cells:
    print(' ', c['trial'], c['status'], c.get('issues'), round((c.get('motion') or {}).get('max_excursion_rad') or 0, 4))
