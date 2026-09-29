"""Exact source-ID local invalid observation for D2, never time-nearest join."""


def local_invalid_observation(root, mode, fault_sample_ns, rows):
    if mode == 'b1':
        return fault_sample_ns  # The source-side gate acts on the generated sample.
    observed = [r['monotonic_ns'] for r in rows(root / 'lineage.jsonl')
                if r.get('kind') == 'source_received' and
                (r.get('metadata') or {}).get('sample_id') == 'docker:56']
    return min(observed) if observed else None
