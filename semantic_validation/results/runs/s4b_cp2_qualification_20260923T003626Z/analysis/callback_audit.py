"""Audit exact publisher-to-Servo callback joins without timing proximity."""
import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return [json.loads(line) for line in path.read_text().splitlines() if line]


def key_bridge(record):
    p = record['payload']
    h = p['header']
    t = p['twist']
    return (h['stamp']['sec'], h['stamp']['nanosec'], h['frame_id'],
            *(t['linear'][a] for a in 'xyz'), *(t['angular'][a] for a in 'xyz'))


def key_humble(record):
    return (record['stamp_sec'], record['stamp_nanosec'], record['frame_id'],
            *record['linear'], *record['angular'])


def key_pose_pub(record):
    p = record['payload']
    h = p['header']
    q = p['pose']
    return (h['stamp']['sec'], h['stamp']['nanosec'], h['frame_id'],
            *(q['position'][a] for a in 'xyz'), *(q['orientation'][a] for a in 'xyzw'))


def key_jazzy(record):
    return (record['stamp_sec'], record['stamp_nanosec'], record['frame_id'],
            *record['position'], *record['orientation'])


def audit(stack, trial, stage, cbfile, pubkey, cbkey):
    root = ROOT / 'raw' / trial
    pubs = [r for r in read(root / 'lineage.jsonl')
            if r.get('kind') == 'publish' and r.get('stage') == stage]
    callbacks = read(root / cbfile)
    pub_index = defaultdict(list)
    cb_index = Counter(cbkey(r) for r in callbacks)
    for record in pubs:
        pub_index[pubkey(record)].append(record)
    unique = sum(len(pub_index[k]) == 1 and cb_index[k] == 1 for k in pub_index)
    source_parents = sum('sample_id' in json.dumps(r.get('parent', {})) for r in pubs)
    neutral_parents = len(pubs) - source_parents
    return dict(stack=stack, trial=trial, publications=len(pubs), callbacks=len(callbacks),
                unique_exact_field_joins=unique,
                unmatched_publications=sum(len(v) for k, v in pub_index.items() if cb_index[k] != 1),
                unmatched_callbacks=sum(n for k, n in cb_index.items() if k not in pub_index),
                source_parent_publications=source_parents, original_neutral_publications=neutral_parents,
                exact_boundary='original Servo-input publication -> Servo input callback',
                beyond_callback='UNKNOWN: per-input internal selection/controller output/Gazebo consequence not identified')


if __name__ == '__main__':
    results = [
        audit('Docker', 'docker_shim_payload01', 'bridge_servo_input',
              'servo_callback_payload.jsonl', key_bridge, key_humble),
        audit('OpenVR', 'openvr_shim_overlay01', 'production_pose',
              'servo_callback_overlay.jsonl', key_pose_pub, key_jazzy),
    ]
    out = ROOT / 'analysis' / 'callback_metrics.json'
    out.write_text(json.dumps(results, indent=2) + '\n')
    for row in results:
        print(row['stack'], row['unique_exact_field_joins'], row['publications'],
              row['callbacks'], row['unmatched_publications'], row['unmatched_callbacks'])
