#!/usr/bin/env python3
"""Read-only reanalysis of the PRIOR_INTERNAL PickNik real-Quest capture (2026-09-17).

Input (tracked in git, unchanged): Deprecated/semantic_validation/results/runs/
hw_picknik_native_20260917T074600Z/{ros_observer.jsonl, sideband_final.jsonl}.
Questions:
  Q1 binding: do /left_controller_odom messages carry the right controller's
     child_frame_id or pose (message reuse + async serialization, audit A3)?
  Q2 focus:  while the Unity app reported application_focused=False (and
     is_tracked=False), did ROS keep receiving fresh-stamped poses, and were they frozen?
Both clocks compared are the Quest's (sideband wall_unix_ms, ROS header stamp from
DateTime.UtcNow), so no host/Quest offset is involved in Q2.
"""
import collections, json, sys
run = sys.argv[1]
ros = [json.loads(l) for l in open(f'{run}/ros_observer.jsonl')]
sb = [json.loads(l) for l in open(f'{run}/sideband_final.jsonl')]
odom = [r for r in ros if r.get('event_type') == 'ros_receive_odometry']
tf = [r for r in ros if r.get('event_type') == 'ros_receive_tf']
out = {}
c = collections.Counter((r['topic'], r['child_frame_id']) for r in odom)
out['odom_topic_x_child_frame'] = {f'{k[0]}|{k[1]}': v for k, v in sorted(c.items())}
out['tf_child_frame'] = dict(collections.Counter(r['child_frame_id'] for r in tf))
L = [r for r in odom if r['topic'] == '/left_controller_odom']
right_by_stamp = {r['ros_stamp_ns']: r for r in odom if r['topic'] == '/right_controller_odom'}
out['left_msgs'] = len(L)
out['left_with_child_frame_right'] = sum(r['child_frame_id'] == 'right_controller_odom' for r in L)
out['left_equal_stamp_and_position_to_a_right_msg'] = sum(
    1 for r in L if r['ros_stamp_ns'] in right_by_stamp and right_by_stamp[r['ros_stamp_ns']]['position'] == r['position'])
# Q2
foc = sorted((d['wall_unix_ms'], d['application_focused']) for d in sb if d['event_type'] == 'application_focus')
iv, start = [], None
for t, f in foc:
    if not f and start is None:
        start = t
    elif f and start is not None:
        iv.append((start, t)); start = None
tt = [d for d in sb if d['event_type'] == 'tracking_transition']
def tracked(side, t):
    s = None
    for d in tt:
        if d['side'] == side and d['wall_unix_ms'] <= t:
            s = d['is_tracked']
    return s
first_ros_ms = min(r['ros_stamp_ns'] for r in odom) // 1_000_000
rows = []
for a, b in iv:
    if b <= first_ros_ms:
        rows.append(dict(start_ms=a, end_ms=b, note='before ROS observer saw first message')); continue
    row = dict(start_ms=a, end_ms=b, dur_ms=b - a)
    for topic, side in (('/left_controller_odom', 'left'), ('/right_controller_odom', 'right')):
        m = [r for r in odom if r['topic'] == topic and a <= r['ros_stamp_ns'] // 1_000_000 < b]
        row[topic] = dict(n=len(m), rate_hz=round(len(m) / ((b - a) / 1000), 1),
                          distinct_positions=len({tuple(r['position']) for r in m}),
                          unity_is_tracked_at_start=tracked(side, a))
    rows.append(row)
out['unfocused_intervals'] = rows
json.dump(out, sys.stdout, indent=1)
print()
