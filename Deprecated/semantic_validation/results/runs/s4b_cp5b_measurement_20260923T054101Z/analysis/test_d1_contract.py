"""Offline CP2-record-backed transport test; not a B0-B3 runtime result."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[3]
sys.path.insert(0, str(ROOT / 'inputs'))
from d1_contract import d1_allow, make_envelope, verify_transport

prior = REPO / 'semantic_validation/results/runs/s4b_cp2_qualification_20260923T003626Z/raw/docker_shim_payload01/lineage.jsonl'
rows = [json.loads(line) for line in prior.read_text().splitlines() if line]
receiver = [r for r in rows if r.get('kind') == 'publish' and r.get('stage') == 'receiver']
source = [r for r in receiver if 'sample_id' in r.get('parent', {})]
neutral = [r for r in receiver if r.get('parent', {}).get('origin') == 'ORIGINAL_NEUTRAL']
assert source and neutral
for record in receiver:
    envelope = make_envelope(record['payload'], record['parent'], record['monotonic_ns'])
    assert verify_transport(json.loads(json.dumps(envelope))) == record['payload']
    assert envelope['selected_origin'] == record['parent']
tampered = make_envelope(source[0]['payload'], source[0]['parent'], source[0]['monotonic_ns'])
tampered['original_payload']['tracked'] = not tampered['original_payload']['tracked']
try:
    verify_transport(tampered)
except ValueError:
    pass
else:
    raise AssertionError('tamper passed transport hash')
full = source[0]['parent']
result = d1_allow(full['native_state'], True, full['source_timestamp_ns'],
                  full['source_timestamp_ns'] + 1_000_000, full['generation_id'])
assert result == (True, 'VALID_D1'), result
assert d1_allow(None, True, None, full['source_timestamp_ns'], None) == (None, 'UNOBSERVABLE')
summary = dict(receiver_publications=len(receiver), source_parents=len(source),
               original_neutral_parents=len(neutral), transport_roundtrips=len(receiver),
               tamper_detected=True, full_valid_d1='VALID_D1', native_missing='UNOBSERVABLE',
               evidence_level='OFFLINE_CP2_RECORDED_FIELDS_NOT_RUNTIME')
(ROOT / 'analysis/d1_contract_offline.json').write_text(json.dumps(summary, indent=2) + '\n')
print(json.dumps(summary, sort_keys=True))
