#!/usr/bin/env python3
"""S4-A read-only inspection, not a defense implementation or runtime trial."""
import hashlib
import json
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
S2 = ROOT / 'semantic_validation/results/runs/s2_docker_baseline_20260922T080640Z'
S3 = ROOT / 'semantic_validation/results/runs/s3_openvr_baseline_20260922T083841Z'
OUT = Path(__file__).resolve().parent
inputs = set()
result = {'scope': 'offline inspection only', 's2': {}, 's3': {}}
for folder in (S2, S3):
    inputs.update(p for p in folder.rglob('*') if p.is_file())
for db in sorted(S2.rglob('*.db3')):
    with sqlite3.connect(db.as_uri() + '?mode=ro', uri=True) as con:
        rows = con.execute('SELECT topics.name, topics.type, COUNT(messages.id) FROM topics LEFT JOIN messages ON topics.id=messages.topic_id GROUP BY topics.id').fetchall()
    result['s2'][str(db.relative_to(ROOT))] = rows
for log in sorted(S2.rglob('transmitted*.jsonl')):
    records = [json.loads(line) for line in log.read_text().splitlines()]
    markers = [r for r in records if r.get('record_type') == 'marker']
    result['s2'][str(log.relative_to(ROOT))] = {'records': len(records), 'markers': markers}
for trial in ('W0', 'W1', 'W2', 'W3'):
    data = json.loads((S3 / trial / f'{trial}_downstream.json').read_text())
    poses = data['pose_target_cmds']
    result['s3'][trial] = {
        'poses': len(poses), 'trajectories': len(data['arm_controller_joint_trajectory']),
        'joints': len(data['joint_states']), 'servo_status': len(data['servo_status']),
        'first_pose': poses[0] if poses else None, 'last_pose': poses[-1] if poses else None,
    }
targets = ROOT / 'semantic_validation/targets'
inputs.update((targets / 'docker_teleop/ros_backend1.1/src').rglob('*.py'))
inputs.update((targets / 'docker_teleop/ros_backend1.1/src').rglob('*.msg'))
inputs.add(targets / 'docker_teleop/UnityApp/Assets/Scripts/HandPoseSender.cs')
inputs.add(targets / 'openvr_ur5e_jazzy/src/quest_bridge/quest_bridge/quest_teleop.py')
inputs.add(targets / 'docker_teleop/ros_backend1.1/src/ur_hande_description/config/initial_positions.yaml')
inputs.add(targets / 'docker_teleop/ros_backend1.1/src/servo_test_config/config/servo_gz.yaml')
inputs.add(targets / 'openvr_ur5e_jazzy/src/ur5_description/urdf/initial_positions.yaml')
inputs.add(targets / 'openvr_ur5e_jazzy/src/ur5_moveit_config/config/ur_servo.yaml')
inputs.update((ROOT / 'semantic_validation/harness/openvr_ur5e_downstream').glob('*'))
inputs = sorted(p for p in inputs if p.is_file())
manifest = [{'path': str(p.relative_to(ROOT)), 'bytes': p.stat().st_size,
             'sha256': hashlib.sha256(p.read_bytes()).hexdigest()} for p in inputs]
(OUT / 'existing_review.json').write_text(json.dumps(result, indent=2) + '\n')
(OUT / 'input_inventory.json').write_text(json.dumps(manifest, indent=2) + '\n')
(OUT.parent / 'input_manifest.sha256').write_text(''.join(f"{r['sha256']}  {r['path']}\n" for r in manifest))
print(json.dumps({'hashed_files': len(manifest), 's2_bags': len(list(S2.rglob('*.db3'))), 's3_counts': {k: {n:v for n,v in val.items() if n in ('poses','trajectories','joints','servo_status')} for k,val in result['s3'].items()}}, indent=2))
