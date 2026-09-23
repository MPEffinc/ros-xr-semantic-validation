"""Prospective Q4 resource and native B2 association audit; no scoring policy."""
import json
from collections import defaultdict
from pathlib import Path

from q3_measurement_audit import audit as q3_audit, rows, source_origin, distribution
from lifecycle_resource_audit import trial as lifecycle_trial

ROOT = Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0, str(ROOT / 'inputs'))
from d1_contract import payload_hash


def native_binding(root):
    lineage = rows(root / 'lineage.jsonl')
    pubs = [x for x in lineage if x.get('stage') == 'receiver_native_monitor_input']
    outputs = [x for x in lineage if x.get('kind') == 'monitor_output_received'
               and x.get('regime') == 'native']
    props = rows(root / 'property.jsonl')
    statuses = [x for x in rows(root / 'monitor_native_status.jsonl')
                if x.get('status') == 'event']
    groups = []
    for seq, fn in ((pubs, lambda x: x['payload_sha256']),
                    (props, lambda x: x['payload_sha256']),
                    (statuses, lambda x: payload_hash(x['payload'])),
                    (outputs, lambda x: x['payload_sha256'])):
        by_hash = defaultdict(list)
        for item in seq:
            by_hash[fn(item)].append(item)
        groups.append(by_hash)
    joined, ambiguous, missing = [], [], []
    for digest, publications in groups[0].items():
        candidates = [g.get(digest, []) for g in groups]
        if any(len(c) != 1 for c in candidates):
            (ambiguous if any(len(c) > 1 for c in candidates) else missing).append(
                dict(hash=digest, counts=[len(c) for c in candidates]))
            continue
        pub, prop, status, output = (c[0] for c in candidates)
        origin = source_origin(pub.get('parent'))
        if bool(prop['safe']) != bool(status['verdict']):
            ambiguous.append(dict(hash=digest, reason='PROPERTY_STATUS_VERDICT_MISMATCH'))
            continue
        joined.append(dict(hash=digest, sample_id=None if origin is None else origin['sample_id'],
                           phase=None if origin is None else origin.get('phase'),
                           command_id=pub['command_id'], oracle_safe=prop['safe'],
                           publish_ns=pub['monotonic_ns'], decision_ns=prop['monotonic_ns'],
                           downstream_receipt_ns=output['monotonic_ns']))
    active = [x for x in joined if x['phase'] == 'active']
    return dict(publications=len(pubs), property_rows=len(props), status_rows=len(statuses),
                receipts=len(outputs), exact_unique_joins=len(joined),
                source_bound_joins=sum(x['sample_id'] is not None for x in joined),
                active_decision_after_publication_ms=distribution(
                    [(x['decision_ns']-x['publish_ns'])/1e6 for x in active]),
                ambiguous=ambiguous, missing=missing,
                internal_monitor_forward_ns=None,
                native_age_generation_visibility='UNOBSERVABLE_TO_DEFENSE',
                joined=joined)


def audit(root):
    result = q3_audit(root)
    result['resources']['q3_sender_cpu_not_used_for_q4'] = result['resources']['per_label'].get('sender')
    result['resources']['q4_sender_lifecycle'] = lifecycle_trial(root)
    if result['resources']['q4_sender_lifecycle']['status'] != 'PASS':
        result['resources']['status'] = 'UNKNOWN_Q4_SENDER_LIFECYCLE'
    if (root / 'monitor_native_status.jsonl').exists():
        result['native_b2_exact_binding'] = native_binding(root)
    return result


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('trial')
    parser.add_argument('output')
    args = parser.parse_args()
    Path(args.output).write_text(json.dumps(audit(Path(args.trial)), indent=2,
                                          sort_keys=True) + '\n')
