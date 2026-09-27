#!/usr/bin/env python3
"""Prospectively checked CP9 D2 setup audit; never edits CP7/CP8 results.

The copied CP7 analyzer still supplies unchanged D2 motion/resource/clock and
official oracle association checks. This layer adds the new pre-spin DDS and
actual mapper-cache parent invariants. It does not score formal policy.
"""
import csv
import json
from pathlib import Path

import d2_qualification_audit as prior

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / 'raw'


def monitor_call_audit(trial):
    lineage = prior.rows(trial / 'lineage.jsonl')
    match = [r for r in lineage if r.get('kind') == 'pre_spin_monitor_dds_match']
    returns = [r for r in lineage if r.get('kind') == 'monitor_input_publish_call_return']
    publishes = [r for r in lineage if r.get('stage') in
                 ('receiver_envelope', 'receiver_native_monitor_input')]
    issues = []
    if len(match) != 1 or not (trial / 'monitor_dds_match.ready').exists():
        issues.append('MISSING_PRE_SPIN_MONITOR_DDS_MATCH')
    if match and any(p['monotonic_ns'] <= match[0]['monotonic_ns'] for p in publishes):
        issues.append('RECEIVER_PUBLISHED_BEFORE_DDS_MATCH')
    if len(returns) != len(publishes):
        issues.append('PUBLISH_CALL_RETURN_COUNT_MISMATCH')
    if any(r.get('dds_subscription_count_after', 0) < 1 for r in returns):
        issues.append('PUBLISH_RETURN_WITHOUT_SUBSCRIBER_MATCH')
    ids = ({r['monitor_event_id'] for r in publishes} if any('monitor_event_id' in r for r in publishes)
           else {r['command_id'] for r in publishes})
    return_ids = ({r['monitor_event_id'] for r in returns} if any('monitor_event_id' in r for r in returns)
                  else {r['monitor_input_id'] for r in returns})
    if ids != return_ids:
        issues.append('PUBLISH_CALL_RETURN_ID_SET_MISMATCH')
    return dict(status='PASS' if not issues else 'BLOCKED_MEASUREMENT',
                issues=issues, pre_spin_dds_match=match[0] if match else None,
                original_publish_attempts=len(publishes),
                publish_call_returns=len(returns))


def mapper_cache_audit(trial, baseline):
    lineage = prior.rows(trial / 'lineage.jsonl')
    applied = None
    applied_events = 0
    rejected = []
    errors = []
    source_parent_unknown_nonzero = []
    cached_after_reject = []
    rejected_since_apply = False
    for row in lineage:
        kind = row.get('kind')
        if kind == 'mapper_applied_after_original_callback':
            applied = row.get('exact_parent')
            applied_events += 1
            rejected_since_apply = False
        elif kind == 'b3_mapper_verdict' and row.get('verdict') is False:
            origin = prior.source_origin(row.get('source_origin'))
            rejected.append(origin.get('sample_id') if origin else None)
            rejected_since_apply = True
        elif kind == 'publish' and row.get('stage') == 'mapper':
            parent = row.get('parent')
            if parent != applied:
                errors.append({'command_id': row['command_id'],
                               'issue': 'PARENT_NOT_LAST_ORIGINAL_CALLBACK_APPLIED'})
            twist = row.get('payload', {}).get('twist', {})
            nonzero = any(abs(twist.get(group, {}).get(axis, 0)) > 1e-6
                          for group in ('linear', 'angular') for axis in 'xyz')
            if nonzero and prior.source_origin(parent) is None:
                source_parent_unknown_nonzero.append(row['command_id'])
            if nonzero and rejected_since_apply:
                cached_after_reject.append({'command_id': row['command_id'],
                                            'last_applied_source':
                                            (prior.source_origin(parent) or {}).get('sample_id')})
            if baseline == 'b3' and nonzero:
                origin = prior.source_origin(parent) or {}
                if origin.get('sample_id') in rejected:
                    errors.append({'command_id': row['command_id'],
                                   'issue': 'REJECTED_SOURCE_FALSE_PARENT'})
    if baseline == 'b3' and set(rejected) != {f'docker:{i}' for i in range(56, 76)}:
        errors.append({'issue': 'REJECTED_SOURCE_COVERAGE'})
    if source_parent_unknown_nonzero:
        errors.append({'issue': 'NONZERO_COMMAND_WITH_UNKNOWN_SOURCE_PARENT',
                       'commands': source_parent_unknown_nonzero})
    if applied_events == 0:
        errors.append({'issue': 'NO_ORIGINAL_MAPPER_APPLY_OBSERVED'})
    return dict(status='PASS' if not errors else 'BLOCKED_MEASUREMENT',
                errors=errors[:100], applied_events=applied_events,
                rejected_source_ids=sorted(set(rejected)),
                cached_nonzero_after_reject=cached_after_reject)


def main():
    with (ROOT / 'qualification_schedule.csv').open() as stream:
        schedule = list(csv.DictReader(stream))
    assert len(schedule) == 10
    results = []
    for cell in schedule:
        result = prior.inspect(cell)
        trial = RAW / result['trial']
        if trial.exists() and result['status'] != 'NOT_RUN':
            if cell['baseline'] != 'b0':
                mapper = mapper_cache_audit(trial, cell['baseline'])
                result['mapper_cache'] = mapper
                if mapper['status'] != 'PASS':
                    result['reasons'].append('MAPPER_CACHED_SOURCE_PARENT_INCOMPLETE')
            if cell['baseline'] in ('b2', 'b2c'):
                monitor_call = monitor_call_audit(trial)
                result['monitor_publish_call'] = monitor_call
                if monitor_call['status'] != 'PASS':
                    result['reasons'].append('MONITOR_DDS_MATCH_OR_PUBLISH_RETURN_INCOMPLETE')
            if result['reasons']:
                result['status'] = 'BLOCKED_MEASUREMENT'
        results.append(result)
    b0, shim = (f'docker_{mode}_full_cp9d2setup01' for mode in ('b0', 'shim'))
    paired = prior.pair.summarize(b0, shim, 120) if (RAW / b0).exists() and (RAW / shim).exists() else None
    complete = all(r['status'] == 'MEASUREMENT_QUALIFIED' for r in results)
    output = dict(status='D2_SETUP_COMPLETE' if complete and paired and paired['status'] == 'PASS'
                  else 'D2_FORMAL_BLOCKED', setup_cells=results,
                  b0_shim_equivalence=paired,
                  policy_verdict='NOT_SCORED_BY_SETUP_AUDIT', formal_trials='NOT_STARTED',
                  source_to_specific_joint_parent='UNKNOWN')
    (ROOT / 'analysis/cp9_qualification_summary.json').write_text(
        json.dumps(output, indent=2, sort_keys=True) + '\n')
    print(json.dumps({'status': output['status'],
                      'cells': [(r['cell'], r['status'], r.get('reasons', [])) for r in results]},
                     sort_keys=True))


if __name__ == '__main__':
    main()
