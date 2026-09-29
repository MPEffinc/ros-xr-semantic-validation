"""Read-only audit of every CP3 D1 setup attempt; never score as formal trials."""
import json
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CALLBACK_AUDIT_PATH = ROOT.parent / "s4b_cp2_qualification_20260923T003626Z" / "analysis" / "callback_audit.py"
spec = importlib.util.spec_from_file_location("cp2_callback_audit", CALLBACK_AUDIT_PATH)
callback_audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(callback_audit)
callback_audit.ROOT = ROOT
NAMES = ('shoulder_pan_joint', 'shoulder_lift_joint', 'elbow_joint',
         'wrist_1_joint', 'wrist_2_joint', 'wrist_3_joint')


def read(path):
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def audit(root):
    events = read(root / 'events.jsonl')
    source = read(root / 'sent.jsonl')
    lineage = read(root / 'lineage.jsonl')
    topics = read(root / 'topics.jsonl')
    callback = read(root / 'servo_callback_payload.jsonl')
    status = read(root / ('monitor_full_status.jsonl' if '_full_' in root.name
                          else 'monitor_native_status.jsonl'))
    verdict = read(root / 'property.jsonl')
    exact = callback_audit.audit('Docker', root.name, 'bridge_servo_input', 'servo_callback_payload.jsonl', callback_audit.key_bridge, callback_audit.key_humble)
    barrier = next((x['start_monotonic_ns'] for x in events
                    if x.get('kind') == 'barrier_release'), None)
    joints = []
    for row in topics:
        if row.get('topic') != '/joint_states':
            continue
        payload = row['payload']
        try:
            positions = {name: payload['position'][payload['name'].index(name)]
                         for name in NAMES}
        except (ValueError, IndexError):
            continue
        joints.append((row['monotonic_ns'], positions))
    excursion = None
    if joints and barrier is not None:
        baseline = min(joints, key=lambda x: abs(x[0] - barrier))[1]
        post = [position for t, position in joints if t >= barrier]
        if post:
            excursion = max(abs(position[name] - baseline[name])
                            for position in post for name in NAMES)
    expected = list(range(120))
    return dict(trial=root.name,
                exit=json.loads((root / 'exit.json').read_text()),
                source_count=len(source),
                complete_source=[row.get('index') for row in source] == expected,
                barrier_released=barrier is not None,
                readiness_ack=any(x.get('kind') == 'readiness_ack' for x in events),
                lineage_by_stage={stage: sum(row.get('stage') == stage for row in lineage)
                                  for stage in sorted({row.get('stage') for row in lineage if row.get('stage') is not None})},
                servo_callback_records=len(callback),
                exact_publication_to_callback=exact,
                official_monitor_status_records=len(status),
                official_oracle_property_records=len(verdict),
                controller_output_records=sum(row.get('topic') == '/joint_group_velocity_controller/commands'
                                              for row in topics),
                controller_output_post_barrier=sum(row.get('topic') == '/joint_group_velocity_controller/commands' and barrier is not None and row.get('monotonic_ns', 0) >= barrier for row in topics),
                joint_state_records=len(joints),
                max_joint_excursion_rad=excursion,
                positive_control_complete=(len(source) == 120 and
                                           [row.get('index') for row in source] == expected and
                                           barrier is not None and
                                           json.loads((root / 'exit.json').read_text()).get('launch_exit') == 0 and
                                           excursion is not None and excursion > .01))


if __name__ == '__main__':
    report = [audit(path) for path in sorted((ROOT / 'raw').glob('docker_*'))]
    (ROOT / 'analysis' / 'd1_setup_metrics.json').write_text(
        json.dumps(report, indent=2, sort_keys=True) + '\n')
    for row in report:
        print(row['trial'], row['exit']['launch_exit'], row['source_count'],
              row['positive_control_complete'], row['max_joint_excursion_rad'])
