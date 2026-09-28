"""Read-only pre-Gazebo Q6 official-path and frozen-input preflight."""
import csv
import hashlib
import json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
repo = root.parents[3]
q3 = root.parent / 's4b_cp13_d3q3_20260928T013003Z'
results = []
issues = []
q5 = root.parent / 's4b_cp15_d3q5_20260928T030624Z'
for regime in ('native', 'full'):
    for scenario in ('positive', 'absent_oracle', 'absent_guarded_subscriber'):
        suffix = 'setup01'
        cell = q5 / 'preflight' / f'official_{regime}_{scenario}_{suffix}'
        summary = json.loads((cell / 'summary.json').read_text())
        exit_record = json.loads((cell / 'exit.json').read_text())
        attempts = summary.get('attempts', [])
        okay = (summary.get('status') == 'PASS_COMPONENT_PREFLIGHT' and
                summary.get('official_revision') == 'd03aa5b44e29b76c0e108a098817bdf5aa98e322' and
                exit_record['exit_code'] == 0 and len(attempts) >= 1 and
                ((scenario == 'positive') == (summary.get('selected_attempt') is not None)))
        property_count = len((cell / 'property.jsonl').read_text().splitlines()) if (cell / 'property.jsonl').exists() else 0
        lineage = [json.loads(line) for line in (cell / 'lineage.jsonl').read_text().splitlines() if line]
        receipt_count = sum(row.get('kind') == 'monitor_output_received' for row in lineage)
        if scenario == 'positive':
            okay &= property_count == 1 and receipt_count == 1 and attempts[-1]['result']['ok'] is True
        elif scenario == 'absent_oracle':
            okay &= property_count == 0 and attempts[0]['result']['ok'] is False
        else:
            okay &= property_count == 1 and receipt_count == 0 and attempts[0]['result']['ok'] is False
        results.append(dict(regime=regime, scenario=scenario, path=str(cell.relative_to(repo)),
                            property_count=property_count, guarded_receipts=receipt_count,
                            selected_attempt=summary.get('selected_attempt'), pass_preflight=bool(okay)))
        if not okay:
            issues.append(f'OFFICIAL_COMPONENT_{regime}_{scenario}')
for name in ('q4_calibration_component.py', 'source_path_readiness.py', 'd1_contract.py'):
    if hashlib.sha256((root / 'inputs' / name).read_bytes()).hexdigest() != hashlib.sha256(
            (q5 / 'inputs' / name).read_bytes()).hexdigest():
        issues.append(f'REUSED_OFFICIAL_COMPONENT_CODE_CHANGED_{name}')
if hashlib.sha256((root / 'inputs/libservo_payload_humble.so').read_bytes()).hexdigest() != '53dfeef34bede747b1c6427d6ea3e1cbf8db969475e7b8906bc62a8fecf0672f':
    issues.append('SERVO_OBSERVER_BINARY_HASH_MISMATCH')
if not (root / 'inputs/d1_rosmonitoring.yaml').is_file():
    issues.append('MONITOR_CONFIGURATION_ASSET_MISSING')
probe_path = root / 'preflight/asset_probe/exit.json'
probe = json.loads(probe_path.read_text()) if probe_path.exists() else {}
if probe.get('exit_code') != 0 or probe.get('observer_binary_loaded') is not True:
    issues.append('TRIAL_OWNED_CONTAINER_SERVO_OBSERVER_ASSET_NOT_LOADED')
schedule = list(csv.DictReader((root / 'qualification_schedule.csv').open()))
expected = [('b0', 'full'), ('shim', 'full'), ('b1', 'native'), ('b1', 'full'),
            ('b2', 'native'), ('b2', 'full'), ('b2c', 'native'), ('b2c', 'full'),
            ('b3', 'native'), ('b3', 'full')]
if [(row['mode'], row['regime']) for row in schedule] != expected or any(
        row['trial_id'] != f"docker_{row['mode']}_{row['regime']}_cp16d3setup01"
        for row in schedule):
    issues.append('SCHEDULE_MISMATCH')
for name in ('d1_sender.py', 'd3_tloracle_property.py'):
    if hashlib.sha256((root / 'inputs' / name).read_bytes()).hexdigest() != hashlib.sha256(
            (q3 / 'inputs' / name).read_bytes()).hexdigest():
        issues.append(f'FROZEN_FIXTURE_OR_POLICY_CHANGED_{name}')
policy = repo / 'semantic_validation/results/S4_EXISTING_DEFENSE_PROTOCOL.md'
if hashlib.sha256(policy.read_bytes()).hexdigest() != '3a40337121f8d687dc68036ff2ffc85a1bc6eda275a700ba7d9e8119cd322969':
    issues.append('RESEARCH_PROTOCOL_HASH_MISMATCH')
if (root / 'raw').exists() and any((root / 'raw').iterdir()):
    issues.append('Q6_GAZEBO_RAN_BEFORE_FREEZE')
result = dict(status='PASS_PREFREEZE' if not issues else 'BLOCKED_PREFREEZE',
              issues=issues, official_components=results, setup_cells=len(schedule),
              gazebo_trial_count=0)
(root / 'analysis/q6_preflight_summary.json').write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
print(json.dumps(result, sort_keys=True))
raise SystemExit(0 if not issues else 1)
