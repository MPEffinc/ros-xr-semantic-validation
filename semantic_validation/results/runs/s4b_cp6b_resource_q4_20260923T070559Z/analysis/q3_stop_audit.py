"""Read-only Docker ordinary-stop diagnostic; never a D1 policy trial."""
import json
from pathlib import Path

JOINTS = ('shoulder_pan_joint', 'shoulder_lift_joint', 'elbow_joint',
          'wrist_1_joint', 'wrist_2_joint', 'wrist_3_joint')


def rows(path):
    return [json.loads(x) for x in path.read_text().splitlines() if x] if path.exists() else []


def nonzero(payload):
    return any(abs(value) > 1e-6 for value in payload.get('data', []))


def audit(root):
    events = rows(root / 'events.jsonl')
    adapter = rows(root / 'stop_adapter.jsonl')
    topics = rows(root / 'topics.jsonl')
    trigger = next((x['trigger_ns'] for x in events
                    if x.get('kind') == 'qualification_stop_trigger'), None)
    if trigger is None:
        return dict(status='UNKNOWN', reason='NO_QUALIFICATION_STOP_TRIGGER')
    requests = [x for x in adapter if x.get('kind') == 'stop_request'
                and x.get('source') == 'QUALIFICATION_STOP']
    replies = [x for x in adapter if x.get('kind') == 'stop_reply'
               and x.get('source') == 'QUALIFICATION_STOP']
    zeros = [x for x in adapter if x.get('kind') == 'controller_zero'
             and x.get('source') == 'QUALIFICATION_STOP']
    controller = [x for x in topics if
                  x.get('topic') == '/joint_group_velocity_controller/commands']
    nonzeros = [x for x in controller if nonzero(x['payload'])]
    joints = []
    for row in topics:
        if row.get('topic') != '/joint_states':
            continue
        payload = row['payload']
        try:
            indices = [payload['name'].index(joint) for joint in JOINTS]
            joints.append((row['monotonic_ns'],
                           [payload['position'][i] for i in indices],
                           [payload['velocity'][i] for i in indices]))
        except (ValueError, IndexError):
            continue
    pre = [x for x in joints if trigger - 100_000_000 <= x[0] < trigger]
    moving_at_trigger = (bool(pre) and
                         any(abs(v) >= .001 for row in pre for v in row[2]) and
                         any(trigger - 100_000_000 <= x['monotonic_ns'] < trigger
                             for x in nonzeros))
    settled_ns = None
    for end in joints:
        if end[0] < trigger + 500_000_000:
            continue
        window = [x for x in joints if end[0] - 500_000_000 <= x[0] <= end[0]]
        if len(window) < 3 or window[-1][0] - window[0][0] < 450_000_000:
            continue
        speed = max(abs(v) for x in window for v in x[2])
        drift = max(max(x[1][i] for x in window) - min(x[1][i] for x in window)
                    for i in range(6))
        if speed < .001 and drift < .0001:
            settled_ns = end[0]
            break
    request_ms = ((requests[0]['monotonic_ns'] - trigger) / 1e6) if requests else None
    reply_ms = ((replies[0]['monotonic_ns'] - trigger) / 1e6) if replies else None
    last_new = max((x['monotonic_ns'] for x in nonzeros if x['monotonic_ns'] >= trigger),
                   default=None)
    last_new_ms = ((last_new - trigger) / 1e6) if last_new is not None else None
    settled_ms = ((settled_ns - trigger) / 1e6) if settled_ns is not None else None
    post_joints = [x for x in joints if trigger <= x[0] <= trigger + 1_000_000_000]
    displacement = (max(abs(x[1][i] - post_joints[0][1][i])
                        for x in post_joints for i in range(6))
                    if len(post_joints) >= 2 else None)
    complete = bool(requests and replies and zeros and joints and controller)
    passed = (complete and moving_at_trigger and 0 <= request_ms <= 50 and
              (last_new_ms is None or last_new_ms <= 300) and
              settled_ms is not None and settled_ms <= 1000)
    return dict(status='PASS_STOP_SETUP' if passed else 'BLOCKED_INTEGRATION',
                trigger_ns=trigger, moving_at_trigger=moving_at_trigger,
                pre_trigger_joint_samples=len(pre), stop_request_ms=request_ms,
                stop_reply_ms=reply_ms, controller_zero_records=len(zeros),
                post_trigger_nonzero_controller_records=sum(x['monotonic_ns'] >= trigger for x in nonzeros),
                last_post_trigger_nonzero_ms=last_new_ms,
                first_settled_window_end_ms=settled_ms,
                post_trigger_1s_joint_displacement_rad=displacement,
                source='QUALIFICATION_STOP_NOT_POLICY_VERDICT',
                individual_source_to_joint_parent='UNKNOWN')


if __name__ == '__main__':
    import sys
    result = audit(Path(sys.argv[1]))
    Path(sys.argv[2]).write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
