"""Static scope check only; runtime stop actuation still needs Gazebo evidence."""
import json
from pathlib import Path

source = (Path(__file__).resolve().parents[1] / 'inputs/d1_stop_adapter.py').read_text()
for forbidden in ('d1_allow', 'native_state', 'source_timestamp_ns',
                  'generation_id', 'isTracked', 'trackingState'):
    assert forbidden not in source, forbidden
assert "os.environ.get('STOP_DIAG') == '1'" in source
assert "trigger = 'QUALIFICATION_STOP'" in source
assert "stop.call_async(Trigger.Request())" in source
assert "zero.publish(msg)" in source
print(json.dumps(dict(status='PASS_STATIC_PREFLIGHT',
                      independent_xr_policy_absent=True,
                      diagnostic_request_guarded=True,
                      caveat='No actual stop request/service/controller/joint result'), sort_keys=True))
