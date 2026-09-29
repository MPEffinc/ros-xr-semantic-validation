#!/usr/bin/env python3
"""SUPPLEMENTARY post-freeze analysis; does NOT replace formal_summary.json.

Post-freeze finding: the frozen scorer expects a rejection only when EVERY
evaluation of a sample is over budget. Where cached republications reach the
threshold, a strict (> F) defense can reject copies whose source age lies
inside the registered +/-1 ms clock-uncertainty band. XRROS-S4-1.0.0 section 5
defines such straddling ages as UNKNOWN. This script reclassifies a trial as
UNKNOWN_BOUNDARY_STRADDLE when its first rejection (the stop cause) lies in that
band and no decision before the stop was clearly over budget; it also
re-evaluates, per decision, any trial whose clearly over-budget decisions the
frozen sample-level rule ignored. All other trials keep their frozen status.
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import d4_formal_audit as f  # noqa: E402
from d4_age import PROFILES, expected  # noqa: E402

ROOT = HERE.parent


def main():
    summary = json.loads((ROOT / 'analysis/formal_summary.json').read_text())
    changed = []
    for t in summary['trials']:
        if t.get('comparison_status') != 'VALID_FORMAL_TRIAL' or t['regime'] != 'full' \
                or t['arm'] not in f.DEFENSES or t.get('expected_rejection'):
            continue
        root = f.RAW / t['attempt']
        lineage = f.rows(root / 'lineage.jsonl')
        sent = {f'docker:{r["index"]}': r for r in f.rows(root / 'sent.jsonl')}
        dec = sorted(f.decisions(root, t['arm'], 'full', lineage, sent), key=lambda x: x['t'])
        F = PROFILES[t['profile']]
        rejects = [d for d in dec if not d['allowed']]
        clear = [d for d in dec if expected(d['source_age_ns'], F) is False]
        if not rejects and not clear:
            continue
        request = (t.get('neutralization') or {}).get('request_ns')
        first = rejects[0] if rejects else None
        band_first = first is not None and expected(first['source_age_ns'], F) is None
        clear_before_stop = [d for d in clear if request is None or d['t'] <= request]
        if band_first and not clear_before_stop:
            status = 'UNKNOWN_BOUNDARY_STRADDLE'
        elif clear and not rejects:
            status = 'FAIL_POLICY'  # clearly over-budget input admitted
        else:
            status = t['policy_status']
        changed.append(dict(trial_id=t['trial_id'], condition=t['condition'], profile=t['profile'], arm=t['arm'],
                            frozen_policy_status=t['policy_status'], frozen_violations=t['policy_violations'],
                            supplementary_policy_status=status, rejections=len(rejects),
                            first_rejection_source_age_ms=None if first is None else first['source_age_ns'] / 1e6,
                            clearly_over_budget_decisions=len(clear),
                            clearly_over_budget_before_stop=len(clear_before_stop),
                            stop_request_after_first_rejection_ms=(None if request is None or first is None
                                                                   else (request - first['t']) / 1e6)))
    out = dict(label='SUPPLEMENTARY_POST_FREEZE_NOT_PRIMARY',
               primary_result='analysis/formal_summary.json (unchanged, frozen analyzer)',
               rule=('per-decision expectation; a stop whose cause is a rejection inside the registered '
                     '+/-1 ms uncertainty band, with no clearly over-budget decision before it, is UNKNOWN'),
               affected_trials=changed)
    (ROOT / 'analysis/supplementary_boundary_band.json').write_text(json.dumps(out, indent=2, sort_keys=True) + '\n')
    for c in changed:
        print(c['trial_id'], c['frozen_policy_status'], '->', c['supplementary_policy_status'],
              c['rejections'], c['first_rejection_source_age_ms'])


if __name__ == '__main__':
    main()
