"""Pre-fault allowed-path joint comparison, not a per-source causal join."""


def joint_at_source_index(root, index, rows, arm_names):
    sent = rows(root / 'sent.jsonl')
    if len(sent) <= index or sent[index].get('index') != index:
        return None
    target_ns = sent[index]['sample_ns']
    candidates = []
    for record in rows(root / 'topics.jsonl'):
        if record.get('topic') != '/joint_states':
            continue
        payload = record['payload']
        try:
            positions = [payload['position'][payload['name'].index(name)]
                         for name in arm_names]
        except (ValueError, IndexError, KeyError):
            continue
        candidates.append((abs(record['monotonic_ns'] - target_ns),
                           record['monotonic_ns'], positions))
    if not candidates:
        return None
    distance, observed_ns, positions = min(candidates)
    return dict(source_index=index, source_ns=target_ns,
                joint_observed_ns=observed_ns,
                joint_sample_offset_ms=distance / 1e6,
                positions_rad=positions)
