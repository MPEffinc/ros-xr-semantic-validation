"""No-ROS replay of Q4 observation log on preserved Q3 native events."""
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
Q3 = ROOT.parent / 's4b_cp5b_measurement_20260923T054101Z'
sys.path.insert(0, str(ROOT / 'inputs'))
import d1_tloracle_property as prop
from q4_measurement_audit import native_binding

os.environ['INFO_REGIME'] = 'native'
summaries = []
with tempfile.TemporaryDirectory(prefix='xr_q4_native_join_') as temp:
    for name in ('docker_b2_native_q3b2nsetup01', 'docker_b2c_native_q3b2cnsetup01'):
        source = Q3 / 'raw' / name
        root = Path(temp) / name
        root.mkdir()
        for item in ('lineage.jsonl', 'monitor_native_status.jsonl'):
            shutil.copy2(source / item, root / item)
        os.environ['XR_D1_PROPERTY_LOG'] = str(root / 'property.jsonl')
        for line in (source / 'monitor_native_events.jsonl').read_text().splitlines():
            if line:
                prop.abstract_message(json.loads(line))
        first = native_binding(root)
        assert not first['ambiguous'] and first['source_bound_joins'] == 372
        assert first['exact_unique_joins'] == first['property_rows'] == first['status_rows']
        with (root / 'property.jsonl').open('a') as file:
            file.write((root / 'property.jsonl').read_text().splitlines()[0] + '\n')
        duplicate = native_binding(root)
        assert duplicate['exact_unique_joins'] == first['exact_unique_joins'] - 1
        assert duplicate['ambiguous']
        summaries.append(dict(trial=name, exact_unique=first['exact_unique_joins'],
                              source_bound=first['source_bound_joins'],
                              property_events=first['property_rows'],
                              initial_missing=len(first['missing']),
                              duplicate_refused=len(duplicate['ambiguous'])))
del os.environ['XR_D1_PROPERTY_LOG']
result = dict(status='PASS_HOST_ONLY_REPLAY', trials=summaries,
              caveat='Property regenerated offline; actual Q4 monitor/oracle runtime not established')
(ROOT / 'analysis/q4_native_binding_preflight.json').write_text(json.dumps(result, indent=2,
                                                                   sort_keys=True) + '\n')
print(json.dumps(result, sort_keys=True))
