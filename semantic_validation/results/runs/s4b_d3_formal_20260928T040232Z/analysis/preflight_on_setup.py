#!/usr/bin/env python3
"""Software preflight of the frozen D3 formal scorer on Q6 SETUP raw.

Labelled SOFTWARE_PREFLIGHT_ON_QUALIFICATION_RAW_NOT_FORMAL: these ten Q6 cells
are never counted as formal repetitions or pooled with formal outcomes.
"""
import json
from pathlib import Path

import d3_formal_audit as f

CELLS = [('b0', 'b0', 'full'), ('shim', 'shim', 'full'), ('b1', 'b1', 'native'), ('b1', 'b1', 'full'),
         ('b2', 'b2', 'native'), ('b2', 'b2', 'full'), ('b2', 'b2c', 'native'), ('b2', 'b2c', 'full'),
         ('b3', 'b3', 'native'), ('b3', 'b3', 'full')]
out = []
for mode, baseline, regime in CELLS:
    name = f'docker_{baseline}_{regime}_cp16d3setup01'
    row = dict(trial_id=name, repetition='0', baseline=baseline, regime=regime, mode=mode)
    out.append(f.audit_trial(row, f.Q6 / 'raw' / name))
result = dict(label='SOFTWARE_PREFLIGHT_ON_QUALIFICATION_RAW_NOT_FORMAL', cells=out,
              formal_trials_counted=0)
(Path(__file__).resolve().parent / 'preflight_on_setup.json').write_text(
    json.dumps(result, indent=2, sort_keys=True) + '\n')
for x in out:
    print(x['trial_id'], x['comparison_status'], x['policy_status'], x.get('policy_violations'))
