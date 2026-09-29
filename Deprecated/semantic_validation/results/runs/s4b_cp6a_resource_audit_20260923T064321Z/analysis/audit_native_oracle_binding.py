"""Read-only native-message exact-hash association; no metadata to the monitor."""
import json
from collections import Counter, defaultdict
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1].parent /
                       's4b_cp5b_measurement_20260923T054101Z' / 'inputs'))
from d1_contract import payload_hash

ROOT = Path(__file__).resolve().parents[1]
Q3 = ROOT.parent / 's4b_cp5b_measurement_20260923T054101Z'


def rows(path):
    return [json.loads(x) for x in path.read_text().splitlines() if x]


def source_origin(parent):
    while isinstance(parent, dict):
        if 'sample_id' in parent:
            return parent
        parent = parent.get('parent')
    return None


def audit(trial):
    lineage = rows(trial / 'lineage.jsonl')
    property_rows = rows(trial / 'property.jsonl')
    status = [x for x in rows(trial / 'monitor_native_status.jsonl')
              if x.get('status') != 'started']
    published = [x for x in lineage if x.get('stage') == 'receiver_native_monitor_input']
    downstream = [x for x in lineage if x.get('kind') == 'monitor_output_received'
                  and x.get('regime') == 'native']
    by_pub = defaultdict(list)
    by_status = defaultdict(list)
    by_down = defaultdict(list)
    for row in published:
        by_pub[row['payload_sha256']].append(row)
    for row in status:
        by_status[payload_hash(row['payload'])].append(row)
    for row in downstream:
        by_down[row['payload_sha256']].append(row)
    joined = []
    ambiguous = []
    missing = []
    for digest, items in by_pub.items():
        statuses = by_status.get(digest, [])
        outputs = by_down.get(digest, [])
        if len(items) != 1 or len(statuses) != 1 or len(outputs) != 1:
            (ambiguous if max(len(items), len(statuses), len(outputs)) > 1 else missing).append(
                dict(hash=digest, publications=len(items), monitor_status=len(statuses),
                     downstream_receipts=len(outputs)))
            continue
        pub, monitor, out = items[0], statuses[0], outputs[0]
        origin = source_origin(pub.get('parent'))
        joined.append(dict(hash=digest, command_id=pub['command_id'],
                           sample_id=None if origin is None else origin['sample_id'],
                           generation_id=None if origin is None else origin['generation_id'],
                           source_state=None if origin is None else origin['native_state'],
                           monitor_verdict=monitor['verdict'],
                           pub_ns=pub['monotonic_ns'], oracle_ns=None,
                           receipt_ns=out['monotonic_ns'],
                           native_fields=pub['payload']))
    status_only = set(by_status) - set(by_pub)
    downstream_only = set(by_down) - set(by_pub)
    duplicate_payloads = {h: count for h, count in Counter(
        x['payload_sha256'] for x in published).items() if count > 1}
    return dict(trial=trial.name, input_publications=len(published),
                oracle_events=len(property_rows), monitor_status_events=len(status),
                downstream_receipts=len(downstream),
                unique_exact_hash_joins=len(joined),
                source_bound_joins=sum(x['sample_id'] is not None for x in joined),
                original_neutral_joins=sum(x['sample_id'] is None for x in joined),
                ambiguous=ambiguous, missing=missing,
                status_only_hashes=sorted(status_only),
                downstream_only_hashes=sorted(downstream_only),
                duplicate_payload_hash_counts=duplicate_payloads,
                I_NATIVE_defense_visible_fields='original ReceivedPoseStates only; no source ID, age or generation',
                oracle_property_exact_source_join='UNKNOWN: property log hash does not equal official status event or payload hash; source ID not in native wire',
                conclusion='STATUS_PAYLOAD_EXACT_OBSERVATION_ONLY_FOR_MATCHED_EVENTS',
                joined=joined)


if __name__ == '__main__':
    names = ('docker_b2_native_q3b2nsetup01', 'docker_b2c_native_q3b2cnsetup01')
    results = [audit(Q3 / 'raw' / name) for name in names]
    (ROOT / 'analysis/q3_native_oracle_binding.json').write_text(
        json.dumps(results, indent=2, sort_keys=True) + '\n')
    for row in results:
        print(row['trial'], row['conclusion'], row['input_publications'],
              row['oracle_events'], row['monitor_status_events'], row['downstream_receipts'],
              row['unique_exact_hash_joins'], len(row['ambiguous']), len(row['missing']))
