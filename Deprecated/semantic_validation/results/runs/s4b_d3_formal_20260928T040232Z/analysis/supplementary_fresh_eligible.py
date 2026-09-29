#!/usr/bin/env python3
"""SUPPLEMENTARY post-freeze analysis; does NOT replace formal_summary.json.

Post-freeze finding: the frozen `eligible_verdicts` counts every verdict on a
message parented to docker:36..55, including a cached repeat of docker:55 that
is re-evaluated AFTER the local silence trigger, when its source age already
exceeds F250. XRROS-S4-1.0.0 section 8 defines normal input as valid and
FRESH inside the steady active phase. This script recounts false rejections
only among verdicts evaluated before the arm's local trigger with source age
<= 250 ms, and reports the late verdicts separately. All other frozen
criteria and classifications are taken unchanged from formal_summary.json.
"""
import json
from pathlib import Path

import d3_formal_audit as f

ROOT = Path(__file__).resolve().parents[1]


def sample(origin):
    return f.source_origin(origin) or {}


def recount(trial):
    root = f.RAW / trial['attempt']
    lineage = f.rows(root / 'lineage.jsonl')
    t_local = trial['local_silence_trigger_ns']
    fresh, late = {}, []
    if trial['arm'] == 'b3':
        for x in lineage:
            if x.get('kind') != 'b3_mapper_verdict' or x.get('event_kind') is not None:
                continue
            o = sample(x.get('source_origin'))
            if o.get('sample_id') not in f.ELIGIBLE:
                continue
            age = x['monotonic_ns'] - o['source_timestamp_ns']
            if x['monotonic_ns'] < t_local and age <= f.LIMIT_NS:
                fresh.setdefault(o['sample_id'], []).append(x.get('verdict') is True)
            else:
                late.append(dict(sample_id=o['sample_id'], verdict=x.get('verdict'),
                                 reason=x.get('reason'), age_ms=age / 1e6,
                                 after_trigger_ms=(x['monotonic_ns'] - t_local) / 1e6))
    else:
        return None  # only B3 re-evaluates cached repeats against wall age at the consumer
    complete = set(fresh) == f.ELIGIBLE
    return dict(fresh_eligible_coverage_complete=complete,
                fresh_false_reject_count=sum(not all(v) for v in fresh.values()) if complete else None,
                late_or_stale_cached_verdicts=late)


def main():
    summary = json.loads((ROOT / 'analysis/formal_summary.json').read_text())
    out = []
    for t in summary['trials']:
        if t.get('comparison_status') != 'VALID_FORMAL_TRIAL' or t['arm'] != 'b3':
            continue
        r = recount(t)
        violations = [v for v in t['policy_violations'] if v != 'NORMAL_ACTIVE_FALSE_REJECTION']
        if r['fresh_false_reject_count']:
            violations.append('NORMAL_ACTIVE_FALSE_REJECTION')
        supplementary = ('PASS_POLICY' if not violations else
                         t['policy_status'] if t['policy_status'] == 'UNOBSERVABLE' else 'FAIL_POLICY')
        out.append(dict(trial_id=t['trial_id'], regime=t['regime'],
                        frozen_policy_status=t['policy_status'],
                        frozen_active_false_reject_count=t['active_false_reject_count'],
                        supplementary_policy_status=supplementary,
                        supplementary_policy_violations=sorted(violations), **r))
    result = dict(label='SUPPLEMENTARY_POST_FREEZE_NOT_PRIMARY',
                  primary_result='analysis/formal_summary.json (unchanged, frozen analyzer)',
                  rule='false rejection counted only for eligible verdicts before local trigger with age <= 250 ms',
                  b3_trials=out)
    (ROOT / 'analysis/supplementary_fresh_eligible.json').write_text(
        json.dumps(result, indent=2, sort_keys=True) + '\n')
    for x in out:
        print(x['trial_id'], x['frozen_policy_status'], '->', x['supplementary_policy_status'],
              len(x['late_or_stale_cached_verdicts']))


if __name__ == '__main__':
    main()
