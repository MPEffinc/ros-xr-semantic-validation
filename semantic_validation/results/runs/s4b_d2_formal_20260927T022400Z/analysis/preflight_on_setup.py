#!/usr/bin/env python3
"""Exercise the prospective scorer on CP9 setup raw; NEVER a formal result."""
import json
from pathlib import Path
import formal_audit as formal

FORMAL_ROOT = Path(__file__).resolve().parents[1]
Q9 = FORMAL_ROOT.parent / 's4b_cp9_d2q3_20260927T020700Z'
formal.ROOT = Q9
formal.qualified.ROOT = Q9
formal.qualified.RAW = Q9 / 'raw'
formal.qualified.prior.ROOT = Q9
formal.qualified.prior.pair.ROOT = Q9
formal.qualified.prior.pair.RAW = Q9 / 'raw'

results = []
for baseline, regime in [('b0','full'),('shim','full'),('b1','native'),('b1','full'),
                         ('b2','native'),('b2','full'),('b2c','native'),('b2c','full'),
                         ('b3','native'),('b3','full')]:
    mode = 'b2' if baseline == 'b2c' else baseline
    trial = f'docker_{baseline}_{regime}_cp9d2setup01'
    result = formal.audit_trial(dict(trial_id=trial, baseline=baseline,
                                     regime=regime, mode=mode,
                                     repetition='1', attempt_id='cp9d2setup01'))
    results.append(dict(trial_id=trial,
                        comparison_status=result['comparison_status'],
                        policy_status=result['policy_status'],
                        reasons=result.get('setup_reasons', result.get('policy_violations', [])),
                        evidence_error=result.get('evidence_error')))
output = dict(classification='SOFTWARE_PREFLIGHT_ON_QUALIFICATION_RAW_NOT_FORMAL',
              cp9_setup_result_commit='a189694c94e058877e3555e45e64f0f75f2b9fc5',
              trials=results)
(FORMAL_ROOT / 'analysis/preflight_on_setup.json').write_text(
    json.dumps(output, indent=2, sort_keys=True) + '\n')
print(json.dumps(output, sort_keys=True))
