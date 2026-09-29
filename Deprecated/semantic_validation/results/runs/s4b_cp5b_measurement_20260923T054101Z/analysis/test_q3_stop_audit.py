"""Non-Gazebo regression for ordinary-stop scoring boundaries."""
import json
import tempfile
from pathlib import Path
from q3_stop_audit import JOINTS, audit


def write(path, records):
    path.write_text(''.join(json.dumps(row) + '\n' for row in records))


with tempfile.TemporaryDirectory(prefix='s4b_q3_stop_') as folder:
    root = Path(folder)
    t0 = 2_000_000_000
    write(root / 'events.jsonl', [dict(kind='qualification_stop_trigger', trigger_ns=t0)])
    write(root / 'stop_adapter.jsonl', [
        dict(kind='stop_request', source='QUALIFICATION_STOP', monotonic_ns=t0 + 10_000_000),
        dict(kind='stop_reply', source='QUALIFICATION_STOP', monotonic_ns=t0 + 20_000_000),
        dict(kind='controller_zero', source='QUALIFICATION_STOP', monotonic_ns=t0 + 21_000_000)])
    topics = [dict(topic='/joint_group_velocity_controller/commands',
                   monotonic_ns=t0 - 40_000_000, payload={'data': [0.1] + [0.] * 5})]
    for ms in range(-90, 1101, 10):
        moving = ms < 300
        topics.append(dict(topic='/joint_states', monotonic_ns=t0 + ms * 1_000_000,
                           payload={'name': JOINTS,
                                    'position': [0.0001 * (ms + 90) if moving else .039] + [0.] * 5,
                                    'velocity': [.01 if moving else 0.] + [0.] * 5}))
    write(root / 'topics.jsonl', topics)
    positive = audit(root)
    assert positive['status'] == 'PASS_STOP_SETUP', positive
    assert positive['first_settled_window_end_ms'] <= 1000
    topics[0]['payload']['data'] = [0.] * 6
    write(root / 'topics.jsonl', topics)
    assert audit(root)['status'] == 'BLOCKED_INTEGRATION'
    print(json.dumps(dict(status='PASS_NON_GAZEBO_PREFLIGHT',
                          moving_stop_pass=True, already_stopped_not_pass=True,
                          caveat='Synthetic stop log only, no Gazebo runtime'), sort_keys=True))
