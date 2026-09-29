"""Recalculate CP1 B0/shim pairs from retained source and ROS JSONL only."""
import hashlib
import json
import math
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / 'raw'
NAMES = ('shoulder_pan_joint', 'shoulder_lift_joint', 'elbow_joint',
         'wrist_1_joint', 'wrist_2_joint', 'wrist_3_joint')
PAIRS = (('docker_b0_02', 'docker_shim_01', 120),
         ('openvr_b0_01', 'openvr_shim_01', 600),
         ('openvr_b0_02', 'openvr_shim_02', 600))


def rows(path):
    return [json.loads(line) for line in path.read_text().splitlines() if line]


def trial(name, expected):
    root = RAW / name
    stack = name.split('_')[0]
    events = rows(root / 'events.jsonl')
    source = rows(root / ('sent.jsonl' if stack == 'docker' else 'source.jsonl'))
    captured = source[:expected]
    assert [x['index'] for x in captured] == list(range(expected)), name
    topics = rows(root / 'topics.jsonl')
    start = next(x['start_monotonic_ns'] for x in events if x['kind'] == 'barrier_release')
    ack = next(x for x in events if x['kind'] == 'readiness_ack')
    clock = next(x for x in events if x['kind'] == 'clock')
    joints = []
    for record in topics:
        if record['topic'] != '/joint_states':
            continue
        payload = record['payload']
        try:
            positions = {n: payload['position'][payload['name'].index(n)] for n in NAMES}
            velocities = {n: payload['velocity'][payload['name'].index(n)] for n in NAMES}
        except (ValueError, IndexError):
            continue
        joints.append(dict(t=record['monotonic_ns'], pos=positions, vel=velocities))
    assert joints, name
    from_start = [x for x in joints if x['t'] >= start]
    baseline = min(joints, key=lambda x: abs(x['t'] - start))['pos']
    excursion = max(abs(x['pos'][n] - baseline[n]) for x in from_start for n in NAMES)
    active_output = ('/joint_group_velocity_controller/commands' if stack == 'docker'
                     else '/ur5_arm_controller/joint_trajectory')
    output_count = sum(x['topic'] == active_output and x['monotonic_ns'] >= start for x in topics)
    fixture = []
    for row in captured:
        if stack == 'docker':
            wire = json.loads(row['wire'])
            wire.pop('timestamp', None)
            wire['_qualification'].pop('source_timestamp_ns', None)
            fixture.append(wire)
        else:
            fixture.append({k: v for k, v in row.items()
                            if k not in ('source_timestamp_ns', 'scheduled_ns')})
    fixture_hash = hashlib.sha256(json.dumps(fixture, sort_keys=True,
                                             separators=(',', ':')).encode()).hexdigest()
    result = dict(name=name, exit=json.loads((root / 'exit.json').read_text()),
                  boot_id=clock['boot_id'], time_namespace=clock['time_namespace'],
                  source_records_total=len(source), source_records_core=len(captured),
                  fixture_sha256=fixture_hash, start_ns=start,
                  actual_offsets_ms=[(x['sample_ns' if stack == 'docker' else 'source_timestamp_ns'] - start) / 1e6
                                     for x in captured],
                  initial_position_error_rad=ack['position_error'],
                  initial_max_velocity_rad_s=ack['speed'], initial_drift_rad=ack['drift'],
                  recorder_joint_window=ack['joint_samples'], controller_states=ack['controllers'],
                  graph=ack['graph'], joint_samples=len(joints),
                  max_joint_excursion_rad=excursion, active_controller_output_records=output_count,
                  final_joint_position_rad=from_start[-1]['pos'])
    return result


def summarize(first, second, expected):
    a, b = trial(first, expected), trial(second, expected)
    differences = [abs(x-y) for x, y in zip(a['actual_offsets_ms'], b['actual_offsets_ms'])]
    joint_difference = {n: abs(a['final_joint_position_rad'][n] - b['final_joint_position_rad'][n])
                        for n in NAMES}
    same_input = a['fixture_sha256'] == b['fixture_sha256']
    clock_ok = a['boot_id'] == b['boot_id'] and a['time_namespace'] == b['time_namespace']
    # Frozen policy: >5 ms invalidates a matched source-trajectory pair;
    # final-joint error <=.02 rad and positive control >.01 rad.
    qualified = (same_input and clock_ok and max(differences) <= 5
                 and max(joint_difference.values()) <= .02
                 and min(a['max_joint_excursion_rad'], b['max_joint_excursion_rad']) > .01
                 and a['exit']['launch_exit'] == b['exit']['launch_exit'] == 0)
    return dict(pair=[first, second], status='PASS' if qualified else 'INVALID_COMPARISON',
                same_fixture=same_input, same_clock_namespace=clock_ok,
                max_source_offset_difference_ms=max(differences),
                median_source_offset_difference_ms=statistics.median(differences),
                source_offsets_over_5ms=sum(x > 5 for x in differences),
                max_final_joint_difference_rad=max(joint_difference.values()),
                final_joint_difference_rad=joint_difference,
                trials=[{k: v for k, v in row.items() if k != 'actual_offsets_ms'} for row in (a, b)])


if __name__ == '__main__':
    report = [summarize(*pair) for pair in PAIRS]
    target = ROOT / 'analysis' / 'pair_metrics.json'
    target.write_text(json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + '\n')
    for pair in report:
        print(pair['pair'], pair['status'], pair['max_source_offset_difference_ms'],
              pair['max_final_joint_difference_rad'], pair['same_fixture'])
