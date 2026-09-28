"""No-Gazebo regression for Q1's dict-hash crash and false success exit."""
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'inputs'))
from source_payload_hash import source_payload_sha256
from receiver_coverage import check_receiver_coverage

payload = {'right_hand': {'isTracked': True}, 'timestamp': 1.25,
           '_qualification': {'sample_id': 'docker:0'}}
before = json.dumps(payload, sort_keys=True)
expected = hashlib.sha256(json.dumps(payload, sort_keys=True,
                                     separators=(',', ':'), allow_nan=False).encode()).hexdigest()
assert source_payload_sha256(payload) == expected
assert json.dumps(payload, sort_keys=True) == before
assert source_payload_sha256(dict(reversed(list(payload.items())))) == expected
try:
    source_payload_sha256('not a source dict')
except TypeError:
    pass
else:
    raise AssertionError('non-dict source accepted')

sent = [{'index': index, 'sent': index not in range(56, 76)} for index in range(120)]
real = [f'docker:{row["index"]}' for row in sent if row['sent']]
complete = ([{'kind': 'source_received', 'metadata': {'sample_id': sid}} for sid in real] +
            [{'kind': 'original_receiver_source_stored', 'sample_id': sid} for sid in real])
assert check_receiver_coverage(sent, complete)['ok']
assert not check_receiver_coverage(sent, complete[:-1])['ok']
assert not check_receiver_coverage(sent, complete[:-100])['ok']

q1 = ROOT.parent / 's4b_cp11_d3q1_20260927T071000Z/raw/docker_shim_full_cp11d3setup01'
historical = [json.loads(line) for line in (q1 / 'lineage.jsonl').read_text().splitlines() if line]
frozen_sent = [json.loads(line) for line in (q1 / 'sent.jsonl').read_text().splitlines() if line]
negative = check_receiver_coverage(frozen_sent, historical)
assert not negative['ok'] and negative['seen_count'] == 1 and negative['stored_count'] == 0
print('D3Q2_DICT_HASH_AND_EXACT_RECEIVER_COVERAGE_REGRESSION_PASS')
