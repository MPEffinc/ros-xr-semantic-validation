"""B2 I_FULL lossless stripper after the official generated ROSMonitoring filter.

Receives the monitor's forwarded /s4b/ovr/envelope (std_msgs/String), verifies
lossless transport only (schema + payload hash; never validity/age/re-arm), logs
the guarded receipt, and republishes a pose-bearing envelope's original
PoseStamped to Servo's original input topic. State-only and calibration
envelopes produce no Servo input. No policy decision is made here.
"""
import json
import os
import time
from pathlib import Path

import rclpy
from geometry_msgs.msg import PoseStamped
from rclpy.node import Node
from rosidl_runtime_py.set_message import set_message_fields
from std_msgs.msg import String

from d1_contract import payload_hash
from trace import bind, log


class Stripper(Node):
    def __init__(self):
        super().__init__('ovr_lossless_stripper')
        self.pose = self.create_publisher(PoseStamped, '/servo_node/pose_target_cmds', 10)
        self.create_subscription(String, '/s4b/ovr/envelope', self.on_envelope, 20)
        Path(os.environ['TRIAL_ROOT'], 'ovr_nodes.ready').write_text('stripper constructed\n')

    def on_envelope(self, msg):
        now = time.monotonic_ns()
        env = json.loads(msg.data)
        if env.get('schema') != 'XRROS-S4-1.0.0/ovr-envelope-v1':
            log('stripper_transport_error', reason='SCHEMA')
            return
        payload = env.get('original_payload')
        if payload is not None and payload_hash(payload) != env.get('original_payload_sha256'):
            log('stripper_transport_error', reason='PAYLOAD_HASH', monitor_event_id=env.get('envelope_monotonic_ns'))
            return
        origin = env.get('selected_origin') or {}
        log('monitor_output_received', regime='full', envelope_kind=env.get('kind'),
            monitor_event_id=env['envelope_monotonic_ns'], sample_id=origin.get('sample_id'),
            original_payload_sha256=env.get('original_payload_sha256'), receipt_monotonic_ns=now)
        if env.get('kind') != 'pose':
            return
        out = PoseStamped()
        set_message_fields(out, payload)
        bind('stripper_servo_input', out, dict(monitor_event_id=env['envelope_monotonic_ns'],
                                                sample_id=origin.get('sample_id'), index=origin.get('index')))
        self.pose.publish(out)


def main():
    rclpy.init()
    node = Stripper()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()


if __name__ == '__main__':
    main()
