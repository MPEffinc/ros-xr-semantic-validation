"""Independent OpenVR stop/re-arm analysis from CP1 JSONL topic callbacks."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NAMES = ('shoulder_pan_joint', 'shoulder_lift_joint', 'elbow_joint',
         'wrist_1_joint', 'wrist_2_joint', 'wrist_3_joint')


def rows(path):
    return [json.loads(line) for line in path.read_text().splitlines() if line]


def analyze(trial):
    raw = ROOT / 'raw' / trial
    events = rows(raw / 'events.jsonl')
    topics = rows(raw / 'topics.jsonl')
    trigger = next(x['monotonic_ns'] for x in events if x['kind'] == 'external_stop_request')
    phase = {x['name']: x['monotonic_ns'] for x in events if x['kind'] == 'phase_start'}
    phase_end = {x['name']: x['monotonic_ns'] for x in events if x['kind'] == 'phase_end'}
    joints = []
    for record in topics:
        if record['topic'] != '/joint_states':
            continue
        payload = record['payload']
        try:
            idx = [payload['name'].index(n) for n in NAMES]
            joints.append((record['monotonic_ns'],
                           [payload['position'][i] for i in idx],
                           [payload['velocity'][i] for i in idx]))
        except (ValueError, IndexError):
            continue
    assert joints

    def excursion(start, end):
        segment = [x for x in joints if start <= x[0] <= end]
        if len(segment) < 2:
            return None
        return max(abs(x[1][i] - segment[0][1][i]) for x in segment for i in range(6))

    settled_end = None
    for j, end in enumerate(joints):
        if end[0] < trigger + 500_000_000:
            continue
        start = end[0] - 500_000_000
        segment = [x for x in joints if start <= x[0] <= end[0]]
        if len(segment) < 3 or segment[-1][0] - segment[0][0] < 450_000_000:
            continue
        speed = max(abs(v) for x in segment for v in x[2])
        drift = max(max(x[1][i] for x in segment) - min(x[1][i] for x in segment)
                    for i in range(6))
        if speed < .001 and drift < .0001:
            settled_end = end[0]
            break

    trajectories = [x for x in topics if x['topic'] == '/ur5_arm_controller/joint_trajectory']
    states = [x for x in topics if x['topic'] == '/ur5_arm_controller/controller_state']
    active = excursion(phase['active'], phase_end['active'])
    post_one = excursion(trigger, trigger + 1_000_000_000)
    new_ref = excursion(phase['new_reference'], phase_end['new_reference'])
    result = dict(trial=trial, exit=json.loads((raw / 'exit.json').read_text()),
                  active_excursion_rad=active, post_trigger_1s_displacement_rad=post_one,
                  first_settled_window_end_ms=None if settled_end is None else (settled_end-trigger)/1e6,
                  hold_requests=sum(x['kind'] == 'controller_hold_request' for x in events),
                  controller_state_records=len(states),
                  trajectories_pre_trigger=sum(x['monotonic_ns'] < trigger for x in trajectories),
                  trajectories_post_trigger_1s=sum(trigger <= x['monotonic_ns'] <= trigger+1_000_000_000
                                                    for x in trajectories),
                  new_reference_excursion_rad=new_ref,
                  qualified_stop=(settled_end is not None and settled_end-trigger <= 1_000_000_000))
    return result


if __name__ == '__main__':
    result = analyze('openvr_hold_fast_03')
    (ROOT / 'analysis' / 'stop_metrics.json').write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
    print(json.dumps(result, indent=2, sort_keys=True))
