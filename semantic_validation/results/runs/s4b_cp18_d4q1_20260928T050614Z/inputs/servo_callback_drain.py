"""Observation-only exact source-parent bridge publication to Servo callback drain.

Do not equate publication with callback or callback with controller/joint output.
The already frozen scored window ends before this lifecycle gate is used.
D4Q1: joins the recorded per-sample source stamp, which D4 decouples from
the creation time sample_ns (identical to Q6 whenever the two are equal).
"""
import json
from collections import Counter
from pathlib import Path


def rows(path):
    path = Path(path)
    if not path.exists():
        return None
    try:
        return [json.loads(line) for line in path.read_text().splitlines() if line]
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None


def source_origin(parent):
    while isinstance(parent, dict):
        if parent.get('sample_id') is not None:
            return parent
        parent = parent.get('parent')
    return None


def pub_key(row):
    payload = row['payload']
    header, twist = payload['header'], payload['twist']
    return (header['stamp']['sec'], header['stamp']['nanosec'], header['frame_id'],
            *(twist['linear'][axis] for axis in 'xyz'),
            *(twist['angular'][axis] for axis in 'xyz'))


def callback_key(row):
    return (row['stamp_sec'], row['stamp_nanosec'], row['frame_id'],
            *row['linear'], *row['angular'])


def audit(root):
    root = Path(root)
    lineage = rows(root / 'lineage.jsonl')
    callbacks = rows(root / 'servo_callback_payload.jsonl')
    sent = rows(root / 'sent.jsonl')
    if lineage is None or callbacks is None or sent is None:
        return dict(status='PENDING', reason='MISSING_OR_PARTIAL_LOG')
    sent_by_id = {f'docker:{row["index"]}': row for row in sent if row.get('sent')}
    pubs = [row for row in lineage if row.get('kind') == 'publish' and
            row.get('stage') == 'bridge_servo_input' and source_origin(row.get('parent'))]
    pub_counts = Counter(pub_key(row) for row in pubs)
    callback_counts = Counter(callback_key(row) for row in callbacks)
    missing = []
    for pub in pubs:
        origin = source_origin(pub['parent'])
        sample_id = origin['sample_id']
        matched = sent_by_id.get(sample_id)
        if (pub_counts[pub_key(pub)] != 1 or callback_counts[pub_key(pub)] != 1 or
                matched is None or matched.get('source_timestamp_ns', matched.get('sample_ns')) !=
                origin.get('source_timestamp_ns')):
            missing.append({'command_id': pub['command_id'], 'sample_id': sample_id,
                            'publish_monotonic_ns': pub['monotonic_ns'],
                            'exact_callback_count': callback_counts[pub_key(pub)],
                            'publication_key_count': pub_counts[pub_key(pub)]})
    return dict(status='PASS' if pubs and not missing else 'PENDING',
                source_parent_publications=len(pubs), exact_joins=len(pubs)-len(missing),
                missing=missing[:20], missing_count=len(missing),
                specific_controller_or_joint_parent='UNKNOWN')
