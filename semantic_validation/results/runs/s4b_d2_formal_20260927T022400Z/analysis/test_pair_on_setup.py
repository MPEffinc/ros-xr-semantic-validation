#!/usr/bin/env python3
"""Preflight the D2 schedule/trajectory pair code on CP9 setup, not formal."""
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

shim = dict(trial_id='docker_shim_full_cp9d2setup01',baseline='shim',mode='shim',
            regime='full',repetition='1',attempt_id='cp9d2setup01')
arm = dict(trial_id='docker_b2_full_cp9d2setup01',baseline='b2',mode='b2',
           regime='full',repetition='1',attempt_id='cp9d2setup01')
by_id = {r['trial_id']: formal.audit_trial(r) for r in (shim,arm)}
result = formal.pair_comparison(shim,arm,by_id)
assert result['status'] == 'PASS_SCHEDULE', result
assert result['pre_fault_allowed_path'] != 'UNKNOWN_MISSING_JOINT_SAMPLE', result
assert result['post_fault_final_joint_difference_is_policy_outcome_not_pair_gate'] is True
out = dict(classification='SOFTWARE_PREFLIGHT_ON_CP9_SETUP_NOT_FORMAL', pair=result)
(FORMAL_ROOT/'analysis/preflight_pair_on_setup.json').write_text(
    json.dumps(out,indent=2,sort_keys=True)+'\n')
print(json.dumps({k:v for k,v in result.items() if k not in ('pair',)},sort_keys=True))
