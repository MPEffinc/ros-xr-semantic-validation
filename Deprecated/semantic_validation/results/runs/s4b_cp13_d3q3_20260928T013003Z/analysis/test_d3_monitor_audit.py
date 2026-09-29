"""Historical positive/negative controls for exact B2 source-event joins."""
from pathlib import Path
from d3_monitor_audit import audit

ROOT = Path(__file__).resolve().parents[5]
RESULTS = ROOT / 'semantic_validation/results/runs'
valid = RESULTS / 's4b_cp9_d2q3_20260927T020700Z/raw'
invalid = RESULTS / 's4b_d2_formal_20260927T022400Z/raw'
for regime in ('full', 'native'):
    result = audit(valid / f'docker_b2_{regime}_cp9d2setup01', regime)
    assert result['status'] == 'PASS', result['issues'][:3]
for name, regime in [('docker_b2_native_d2r01', 'native'),
                     ('docker_b2_full_d2r01', 'full')]:
    result = audit(invalid / name, regime)
    assert result['status'] == 'BLOCKED_MEASUREMENT', name
print('D3Q2_OFFICIAL_MONITOR_SOURCE_JOIN_POSITIVE_NEGATIVE_PASS')
