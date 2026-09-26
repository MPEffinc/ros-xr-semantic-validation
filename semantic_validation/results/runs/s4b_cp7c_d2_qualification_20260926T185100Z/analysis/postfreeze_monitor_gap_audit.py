#!/usr/bin/env python3
"""Read-only audit of B2 D2 original-publish to property/status gaps."""
import hashlib
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / 'raw'

def rows(path):
    return [json.loads(line) for line in path.open()] if path.exists() else []

def canonical_hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()

out = {}
for name in ('docker_b2_native_cp7d2setup01', 'docker_b2_full_cp7d2setup01',
             'docker_b2c_native_cp7d2setup01', 'docker_b2c_full_cp7d2setup01'):
    trial = ROOT / name
    full = '_full_' in name
    lineage = rows(trial / 'lineage.jsonl')
    props = rows(trial / 'property.jsonl')
    status = [r for r in rows(trial / ('monitor_full_status.jsonl' if full else 'monitor_native_status.jsonl'))
              if r.get('status') == 'event']
    barrier = json.loads((trial / 'barrier.json').read_text())['release_monotonic_ns']
    stage = 'receiver_envelope' if full else 'receiver_native_monitor_input'
    pubs = [r for r in lineage if r.get('stage') == stage]
    if full:
        pub_key = lambda r: r['monitor_event_id']
        prop_key = lambda r: r['monitor_event_id']
        status_key = lambda r: json.loads(r['event']['data'])['envelope_monotonic_ns']
    else:
        pub_key = lambda r: r['payload_sha256']
        prop_key = lambda r: r['payload_sha256']
        status_key = lambda r: canonical_hash(r['payload'])
    pc, qc, sc = (Counter(key(x) for x in seq)
                  for key, seq in ((pub_key, pubs), (prop_key, props), (status_key, status)))
    missing = []
    for pub in pubs:
        key = pub_key(pub)
        if pc[key] != 1 or qc[key] != 1 or sc[key] != 1:
            missing.append({'key': key, 'publish_ns': pub['monotonic_ns'],
                            'relative_to_barrier_ms': round((pub['monotonic_ns'] - barrier) / 1e6, 3),
                            'publication_count': pc[key], 'property_count': qc[key],
                            'status_count': sc[key],
                            'selected_origin': pub.get('selected_origin') if full else None})
    out[name] = {'original_publications': len(pubs), 'property_rows': len(props),
                 'status_rows': len(status), 'unmatched_publications': missing,
                 'unmatched_before_barrier': sum(x['publish_ns'] < barrier for x in missing),
                 'unmatched_after_barrier': sum(x['publish_ns'] >= barrier for x in missing)}
print(json.dumps(out, indent=2, sort_keys=True))
