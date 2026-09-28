"""Diagnostic only: plain single-threaded subscriber on the envelope topic (arrival times)."""
import json, os, time
from pathlib import Path
import rclpy
from rclpy.node import Node
from std_msgs.msg import String
out = Path(os.environ['TRIAL_ROOT'], 'diag_sub.jsonl').open('a', buffering=1)
rclpy.init()
n = Node('diag_sub')
n.create_subscription(String, '/s4b/ovr/envelope_mon', lambda m: out.write(json.dumps(dict(t=time.monotonic_ns(), k=json.loads(m.data)['envelope_monotonic_ns'])) + '\n'), 1000)
rclpy.spin(n)
