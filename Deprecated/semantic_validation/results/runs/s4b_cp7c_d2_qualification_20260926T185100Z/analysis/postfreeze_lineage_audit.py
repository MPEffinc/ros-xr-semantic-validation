#!/usr/bin/env python3
"""Read-only post-freeze D2 B3 parent-label audit; never relabels commands."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TRIAL = ROOT / 'raw/docker_b3_native_cp7d2setup01'
rows = [json.loads(line) for line in (TRIAL / 'lineage.jsonl').open()]
last_accepted = None
last_rejected = None
rejected = []
suspect = []
for row in rows:
    if row.get('kind') == 'b3_mapper_verdict':
        origin = row.get('source_origin') or {}
        sample = origin.get('sample_id')
        if row.get('verdict') is True:
            last_accepted = sample
            last_rejected = None
        elif sample:
            last_rejected = sample
            rejected.append(sample)
    elif row.get('kind') == 'publish' and row.get('stage') == 'mapper' and last_rejected:
        parent = (row.get('parent') or {}).get('parent') or {}
        labelled = parent.get('sample_id')
        payload = row.get('payload') or {}
        twist = payload.get('twist') or {}
        values = list((twist.get('linear') or {}).values()) + list((twist.get('angular') or {}).values())
        nonzero = any(abs(float(v)) > 1e-9 for v in values)
        if labelled == last_rejected and nonzero:
            suspect.append({'command_id': row['command_id'],
                            'labelled_rejected_sample': labelled,
                            'last_accepted_sample': last_accepted,
                            'payload_sha256': row['payload_sha256'],
                            'tracked_in_output': payload.get('tracked'),
                            'monotonic_ns': row['monotonic_ns']})
result = {'trial': TRIAL.name,
          'rejected_source_ids': list(dict.fromkeys(rejected)),
          'suspect_nonzero_mapper_publications': suspect,
          'interpretation': 'OBSERVATION_PARENT_INVALID_AFTER_REJECT; actual command parent UNKNOWN'}
print(json.dumps(result, indent=2, sort_keys=True))
