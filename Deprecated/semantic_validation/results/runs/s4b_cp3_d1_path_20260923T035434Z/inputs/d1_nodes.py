"""D1 trial-owned original-class wrappers; no vendor checkout edits.

B2 serialization/stripping makes no policy decision. B3's sole decision is in
the original Mapper callback override, not a ROS relay. This is setup code;
no run is a formal comparison until the whole configuration is frozen.
"""
import json
import os
import time
from pathlib import Path

import rclpy
from rclpy.executors import SingleThreadedExecutor
from rclpy.node import Node
from rosidl_runtime_py.convert import message_to_ordereddict
from rosidl_runtime_py.set_message import set_message_fields
from std_msgs.msg import String
from teleop_bridge_msgs.msg import ReceivedPoseStates

from receiver.quest_controller_receiver import QuestControllerReceiver
from teleop_bridge.mapping.hand_pose_mapper import ReceivedPoseToTargetTwist
from teleop_bridge.servo_bridge.servo_command_bridge import TargetTwistToServoCmd
from d1_contract import canonical, d1_allow, make_envelope, verify_transport
from trace import Publisher, bind, consume, digest, EDGES, log

MODE = os.environ['MODE']
REGIME = os.environ['INFO_REGIME']


class Receiver(QuestControllerReceiver):
    def __init__(self):
        self.state_origins = {}
        self.selected = None
        super().__init__()
        original_pub = self.pub
        if MODE == 'b2':
            if REGIME == 'full':
                target = self.create_publisher(String, '/s4b/d1/envelope_mon', 20)
            else:
                target = self.create_publisher(ReceivedPoseStates, '/s4b/d1/native_input_mon', 20)
            self.pub = D1MonitorPublisher(original_pub, target, lambda: self.selected)
        else:
            self.pub = Publisher(original_pub, 'receiver', lambda: self.selected)

    def _parse_payload(self, payload, *args, **kwargs):
        state = super()._parse_payload(payload, *args, **kwargs)
        self.state_origins[id(state)] = (state, payload.get('_qualification'))
        return state

    def _store_payload(self, payload):
        log('source_received', metadata=payload.get('_qualification'), original_payload=payload)
        return super()._store_payload(payload)

    def _make_msg(self, state, stamp):
        entry = self.state_origins.get(id(state))
        self.selected = (entry[1] if entry and entry[0] is state else
                         {'origin': 'ORIGINAL_NEUTRAL', 'reason': state['source']})
        return super()._make_msg(state, stamp)


class D1MonitorPublisher:
    def __init__(self, original, target, parent):
        self.original, self.target, self.parent = original, target, parent

    def publish(self, msg):
        fields = message_to_ordereddict(msg)
        selected = self.parent()
        if REGIME == 'full':
            envelope = make_envelope(fields, selected, time.monotonic_ns())
            log('publish', stage='receiver_envelope', selected_origin=selected,
                original_payload_sha256=envelope['original_payload_sha256'])
            self.target.publish(String(data=canonical(envelope)))
        else:
            bind('receiver_native_monitor_input', msg, selected)
            self.target.publish(msg)
        assert message_to_ordereddict(msg) == fields

    def __getattr__(self, name):
        return getattr(self.original, name)


class Stripper(Node):
    def __init__(self):
        super().__init__('d1_lossless_stripper')
        self.pub = self.create_publisher(ReceivedPoseStates, '/received_pose_states', 20)
        if REGIME == 'full':
            self.create_subscription(String, '/s4b/d1/envelope', self.on_full, 20)
        else:
            self.create_subscription(ReceivedPoseStates, '/s4b/d1/native_input', self.on_native, 20)

    def on_full(self, wire):
        envelope = json.loads(wire.data)
        fields = verify_transport(envelope)
        msg = ReceivedPoseStates()
        set_message_fields(msg, fields)
        assert message_to_ordereddict(msg) == fields
        bind('stripper_restored', msg, envelope['selected_origin'])
        self.pub.publish(msg)

    def on_native(self, msg):
        parent = consume('stripper_native_input', msg)
        if parent is None:
            log('stripper_unjoined', payload_sha256=digest(msg))
            return
        # The exact input edge was consumed; replace only this in-process
        # observation registry entry so Mapper sees one unique restored edge.
        edge_list = EDGES[digest(msg)]
        edge_list.remove(parent)
        bind('stripper_restored', msg, parent['parent'])
        self.pub.publish(msg)


class Mapper(ReceivedPoseToTargetTwist):
    def __init__(self):
        self.selected = None
        super().__init__()
        self.pub = Publisher(self.pub, 'mapper', lambda: self.selected)

    def _on_pose_states(self, msg):
        self.selected = consume('mapper', msg)
        if MODE == 'b3':
            origin = self.selected['parent'] if self.selected else None
            if REGIME == 'full' and origin and 'sample_id' in origin:
                verdict, reason = d1_allow(origin.get('native_state'), bool(msg.teleop_enable),
                                           origin.get('source_timestamp_ns'), time.monotonic_ns(),
                                           origin.get('generation_id'))
            elif REGIME == 'native':
                verdict = not msg.teleop_enable or bool(msg.tracked)
                reason = 'NATIVE_WIRE_ONLY_UNOBSERVABLE_TIME_GENERATION'
            else:
                verdict, reason = True, 'ORIGINAL_NEUTRAL'
            log('b3_mapper_verdict', verdict=verdict, reason=reason,
                source_origin=origin, payload_sha256=digest(msg))
            if verdict is not True:
                return
        return super()._on_pose_states(msg)


class Bridge(TargetTwistToServoCmd):
    def __init__(self):
        self.selected = None
        super().__init__()
        self._pub = Publisher(self._pub, 'bridge_servo_input', lambda: self.selected)

    def _on_input(self, msg):
        self.selected = consume('bridge', msg)
        return super()._on_input(msg)


rclpy.init()
nodes = [Receiver(), Mapper(), Bridge()]
if MODE == 'b2':
    nodes.append(Stripper())
executor = SingleThreadedExecutor()
for node in nodes:
    executor.add_node(node)
Path(os.environ['TRIAL_ROOT'], 'd1_nodes.ready').write_text(json.dumps({
    'mode': MODE, 'regime': REGIME, 'nodes': [node.get_name() for node in nodes],
    'monotonic_ns': time.monotonic_ns(),
    'boot_id': Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
    'time_namespace': os.readlink('/proc/self/ns/time')}))
try:
    executor.spin()
finally:
    executor.shutdown()
    for node in nodes:
        node.destroy_node()
