#!/usr/bin/env python3
"""SUPPLEMENTARY (post-outcome, separately labelled) correction of three OpenVR
formal-scorer defects found after the run. The frozen primary result in
formal_summary.json is NOT modified; this writes supplementary_summary.json.

S1  R_AUTO recovered-delivery denominator: the frozen R7 delivery rule counted
    polls 225-499 including the registered released polls 240-249, on which the
    original never publishes by design, so >= 99% was unreachable. Supplementary:
    only grip polls after re-arm are eligible.
S2  R_AUTO re-arm poll: the registered rule is time-based (500 ms continuously
    valid), but the frozen scorer fixed poll 225. With 50 Hz timer jitter the
    500 ms dwell can first be met at poll 226. Supplementary: the expected re-arm
    poll is the first grip poll i >= 200 with src[i] - src[200] >= 500 ms - 1 ms
    band; the next poll is also accepted when the dwell at the first is within the
    +-1 ms band. The R7 not-admitted rule then starts at the expected poll.
S3  R1 pre-fault joint path: when the repetition's shim itself deviates from B0
    at slot 149 by > .02 rad while the arm is within .02 rad of B0, the frozen
    R1_PREFAULT_JOINT_PATH violation is a control anomaly, not a defense outcome.
All other primary rules and all validity decisions are unchanged.
"""
import csv
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
import ovr_formal_audit as f  # noqa: E402

BAND_NS = 1_000_000


def expected_auto_poll(src):
    for i in range(200, 240):
        if src[i] - src[200] >= 500_000_000 - BAND_NS:
            near = abs((src[i] - src[200]) - 500_000_000) <= BAND_NS
            return i, near
    return None, False


def main():
    primary = json.loads((HERE / 'formal_summary.json').read_text())
    schedule = {r['trial_id']: r for r in csv.DictReader((ROOT / 'schedule.csv').open())}
    trials = []
    changes = []
    for t in primary['trials']:
        t = json.loads(json.dumps(t))
        if t.get('comparison_status') != 'VALID_FORMAL_TRIAL' or t['arm'] not in f.DEFENSES or t['case'] not in ('W4', 'W5'):
            trials.append(t)
            continue
        root = f.RAW / t['attempt']
        v = set(t['policy_violations'])
        before = set(v)
        if t['rearm'] == 'R_AUTO':
            src = f.source_times(root)
            dec = f.decisions(root, t['arm'])
            dlv = f.delivered(root, t['arm'])
            grip = {i for i in range(600) if f._grip(root, i)}
            exp, near = expected_auto_poll(src)
            ok_polls = {exp, exp + 1} if near else {exp}
            first = t.get('first_admitted_grip_after_fault')
            if first in ok_polls:
                v.discard('R7_REARM_NOT_AT_REGISTERED_POLL')
            start = first if first in ok_polls else exp
            after = [i for i in range(start, 500)]
            bad = [i for i in after if not dec.get(i) or not all(d['admitted'] for d in dec[i])]
            if not bad:
                v.discard('R7_RECOVERED_VALID_SAMPLE_NOT_ADMITTED')
            eligible = [i for i in after if i in grip]
            if eligible and len(dlv & set(eligible)) / len(eligible) >= .99:
                v.discard('R7_RECOVERED_DELIVERY_BELOW_99PCT')
            t['supplementary_expected_auto_rearm_poll'] = exp
        if 'R1_PREFAULT_JOINT_PATH_OVER_0_02RAD_VS_SHIM' in v:
            rep, case = t['repetition'], t['case']
            b0 = f.RAW / f'openvr_b0_full_{case}_R_EXPLICIT_ovrr{rep:02d}'
            shim = f.RAW / f'openvr_shim_full_{case}_R_EXPLICIT_ovrr{rep:02d}'

            def at(r, i):
                s = f.source_times(r)
                js = f.joints(r)
                return min(js, key=lambda x: abs(x[0] - s[i]))[1]
            d = lambda x, y: max(abs(p - q) for p, q in zip(x, y))
            shim_b0 = d(at(shim, 149), at(b0, 149))
            arm_b0 = d(at(root, 149), at(b0, 149))
            t['supplementary_slot149_shim_vs_b0_rad'] = shim_b0
            t['supplementary_slot149_arm_vs_b0_rad'] = arm_b0
            if shim_b0 > .02 and arm_b0 <= .02:
                v.discard('R1_PREFAULT_JOINT_PATH_OVER_0_02RAD_VS_SHIM')
                t.setdefault('supplementary_notes', []).append('R1_JOINT_PATH_CONTROL_ANOMALY_SHIM_DEVIATED_FROM_B0')
        if v != before:
            t['primary_policy_status'] = t['policy_status']
            t['primary_policy_violations'] = t['policy_violations']
            t['policy_violations'] = sorted(v)
            t['violation_attribution'] = {k: a for k, a in t['violation_attribution'].items() if k in v}
            t['attribution_classes'] = sorted(set(t['violation_attribution'].values()))
            t['policy_status'] = 'FAIL_POLICY' if v else 'PASS_POLICY'
            changes.append(dict(trial=t['trial_id'], removed=sorted(before - v), primary=t['primary_policy_status'],
                                supplementary=t['policy_status']))
        trials.append(t)
    from collections import Counter
    out = dict(label='SUPPLEMENTARY_POST_OUTCOME_SCORER_DEFECT_CORRECTION_NOT_PRIMARY', corrections=['S1', 'S2', 'S3'],
               changed_trials=changes,
               policy_counts=dict(sorted(Counter(f"{t['arm']}|{t['case']}|{t['rearm']}|{t['policy_status']}" for t in trials).items())),
               trials=trials)
    (HERE / 'supplementary_summary.json').write_text(json.dumps(out, indent=2, sort_keys=True) + '\n')
    print('changed', len(changes))
    for c in changes:
        print(' ', c['trial'], c['removed'], c['primary'], '->', c['supplementary'])


if __name__ == '__main__':
    main()
