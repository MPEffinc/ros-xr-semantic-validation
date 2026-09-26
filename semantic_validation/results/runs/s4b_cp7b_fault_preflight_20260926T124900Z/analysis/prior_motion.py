#!/usr/bin/env python3
"""Historical D1 joint-velocity feasibility check, never D2/D3 qualification."""
import argparse
import glob
import json
import math
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument('--raw-root', type=Path, required=True)
ap.add_argument('--out', type=Path, required=True)
args = ap.parse_args()
results = []
for folder in sorted(glob.glob(str(args.raw_root / 'docker_d1_r*_shim_full'))):
    root = Path(folder)
    start = json.loads((root / 'barrier.json').read_text())['start_monotonic_ns']
    samples = []
    for line in (root / 'topics.jsonl').open():
        row = json.loads(line)
        if row.get('topic') != '/joint_states':
            continue
        relative_ms = (row['monotonic_ns'] - start) / 1e6
        if abs(relative_ms - 2800) > 60:
            continue
        values = [abs(v) for v in row['payload']['velocity']
                  if isinstance(v, (int, float)) and math.isfinite(v)]
        if values:
            samples.append((relative_ms, max(values)))
    results.append(dict(trial=root.name, source='HISTORICAL_D1_SHIM_ONLY',
                        target_fault_offset_ms=2800, joint_samples=len(samples),
                        nearest_sample_delta_ms=min((abs(t - 2800) for t, _ in samples),
                                                    default=None),
                        max_abs_joint_velocity_rad_s=max((v for _, v in samples),
                                                         default=None)))
args.out.write_text(json.dumps(results, indent=2, sort_keys=True) + '\n')
print(json.dumps({'historical_trials': len(results),
                  'all_have_motion_near_target': all(r['max_abs_joint_velocity_rad_s']
                                                     and r['max_abs_joint_velocity_rad_s'] > .001
                                                     for r in results),
                  'D2_D3_runtime_motion': 'UNKNOWN'}, sort_keys=True))
