"""Common 50 Hz health clock, not a source sample or defense predicate."""
import json
import os
import time
from pathlib import Path

import rclpy
from rclpy.node import Node
from std_msgs.msg import String

root = Path(os.environ['TRIAL_ROOT'])
mode = os.environ['MODE']
rclpy.init()
node = Node('d3_common_health_tick')
common = node.create_publisher(String, '/s4b/d3/common_tick', 20)
monitored = node.create_publisher(String, '/s4b/d3/tick_mon', 20)
deadline = time.monotonic() + 20
if mode == 'b2':
    while monitored.get_subscription_count() < 1 and time.monotonic() < deadline:
        rclpy.spin_once(node, timeout_sec=.01)
    if monitored.get_subscription_count() < 1:
        raise RuntimeError('official monitor tick subscription DDS ACK missing')
if mode == 'b3':
    while common.get_subscription_count() < 1 and time.monotonic() < deadline:
        rclpy.spin_once(node, timeout_sec=.01)
    if common.get_subscription_count() < 1:
        raise RuntimeError('B3 controller-side tick subscription DDS ACK missing')
(root / 'd3_tick.ready').write_text(json.dumps({
    'monotonic_ns': time.monotonic_ns(),
    'common_subscribers': common.get_subscription_count(),
    'official_monitor_subscribers': monitored.get_subscription_count(),
    'boot_id': Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
    'time_namespace': os.readlink('/proc/self/ns/time')}) + '\n')
while not (root / 'barrier.json').exists():
    rclpy.spin_once(node, timeout_sec=.005)
start_ns = json.loads((root / 'barrier.json').read_text())['start_monotonic_ns']
with (root / 'd3_ticks.jsonl').open('a', buffering=1) as output:
    from d4l_timing import tick_count
    for index in range(tick_count()):  # D4-L: 50 Hz for the whole registered capture
        deadline_ns = start_ns + index * 20_000_000
        while time.monotonic_ns() < deadline_ns:
            rclpy.spin_once(node, timeout_sec=.001)
        now_ns = time.monotonic_ns()
        record = {'kind': 'health_tick', 'tick_id': f'tick:{index}',
                  'index': index, 'scheduled_ns': deadline_ns,
                  'tick_monotonic_ns': now_ns,
                  'source_sample_id': None, 'source_receipt_ns': None,
                  'clock': 'CLOCK_MONOTONIC'}
        message = String(data=json.dumps(record, sort_keys=True, separators=(',', ':')))
        common.publish(message)
        if mode == 'b2':
            monitored.publish(message)
        output.write(json.dumps({**record,
            'common_subscribers': common.get_subscription_count(),
            'official_monitor_subscribers': monitored.get_subscription_count()},
            sort_keys=True) + '\n')
(root / 'd3_tick.done').write_text(f'{tick_count()} common ticks published; no source samples created\n')
# Remain observable until the trial owner stops the container; exiting here
# would fail the existing required-child lifecycle check after capture end.
while True:
    rclpy.spin_once(node, timeout_sec=.1)
node.destroy_node()
rclpy.shutdown()
