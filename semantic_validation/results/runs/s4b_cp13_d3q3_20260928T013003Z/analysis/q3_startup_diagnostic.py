#!/usr/bin/env python3
"""Post-freeze diagnosis only; never changes Q3's frozen setup verdict."""
import json
from pathlib import Path

from d3_monitor_audit import canonical_hash, rows

ROOT = Path(__file__).resolve().parents[1] / 'raw'
names = ('docker_b2_native_cp13d3setup01', 'docker_b2_full_cp13d3setup01',
         'docker_b2c_native_cp13d3setup01', 'docker_b2c_full_cp13d3setup01')
result = []
for name in names:
    path = ROOT / name
    regime = 'full' if '_full_' in name else 'native'
    stage = 'receiver_envelope' if regime == 'full' else 'receiver_native_monitor_input'
    lineage = rows(path / 'lineage.jsonl')
    pubs = [r for r in lineage if r.get('stage') == stage]
    props = [r for r in rows(path / 'property.jsonl') if r.get('event_kind') != 'tick']
    status = [r for r in rows(path / f'monitor_{regime}_status.jsonl')
              if r.get('status') == 'event' and r.get('interface') != '/s4b/d3/tick']
    outputs = [r for r in lineage if r.get('kind') == 'monitor_output_received' and r.get('regime') == regime]
    key = ((lambda r: r['monitor_event_id']) if regime == 'full'
           else (lambda r: r['payload_sha256']))
    p_ids = {key(r) for r in pubs}
    prop_ids = {key(r) for r in props}
    out_ids = {key(r) for r in outputs}
    status_ids = ({json.loads(r['event']['data'])['envelope_monotonic_ns'] for r in status}
                  if regime == 'full' else {canonical_hash(r['payload']) for r in status})
    missing = [r for r in pubs if key(r) not in prop_ids]
    barrier = json.loads((path / 'barrier.json').read_text())['start_monotonic_ns']
    match = json.loads((path / 'monitor_dds_match.ready').read_text())['dds_match_monotonic_ns']
    capture = next(r['monotonic_ns'] for r in rows(path / 'events.jsonl') if r.get('kind') == 'capture_end')
    result.append({
        'trial': name, 'original_publications': len(pubs), 'property_events': len(props),
        'official_status_events': len(status), 'guarded_receipts': len(outputs),
        'missing_property_count': len(missing), 'missing_status_count': len(p_ids-status_ids),
        'missing_guarded_count': len(p_ids-out_ids),
        'first_original_to_first_property_ms': round((props[0]['monotonic_ns']-pubs[0]['monotonic_ns'])/1e6, 3),
        'missing_before_barrier': sum(r['monotonic_ns'] < barrier for r in missing),
        'missing_after_barrier': sum(r['monotonic_ns'] >= barrier for r in missing),
        'missing_before_first_property': sum(r['monotonic_ns'] < props[0]['monotonic_ns'] for r in missing),
        'missing_after_capture': sum(r['monotonic_ns'] > capture for r in missing),
        'all_missing_after_dds_match': all(r['monotonic_ns'] >= match for r in missing),
        'first_missing_rel_barrier_ms': round((missing[0]['monotonic_ns']-barrier)/1e6, 3) if missing else None,
        'last_missing_rel_barrier_ms': round((missing[-1]['monotonic_ns']-barrier)/1e6, 3) if missing else None,
        'missing_event_ids': [key(r) for r in missing],
        'evidence_boundary': 'receiver publish invocation; DDS delivery and monitor callback absent/UNKNOWN for missing events',
    })
print(json.dumps(result, indent=2, sort_keys=True))
