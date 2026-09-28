"""B0-shim: original classes, no policy changes, composed single-thread executor."""
import rclpy
from rclpy.executors import SingleThreadedExecutor
from receiver.quest_controller_receiver import QuestControllerReceiver
from teleop_bridge.mapping.hand_pose_mapper import ReceivedPoseToTargetTwist as HandPoseMapper
from teleop_bridge.servo_bridge.servo_command_bridge import TargetTwistToServoCmd as ServoCommandBridge
from trace import Publisher, consume, log

class Receiver(QuestControllerReceiver):
    def __init__(self):
        self.state_origins = {}
        self.selected = None
        super().__init__()
        self.pub = Publisher(self.pub, 'receiver', lambda: self.selected)
    def _parse_payload(self, payload, *args, **kw):
        state = super()._parse_payload(payload, *args, **kw)
        # Keep object itself alive: Python id reuse cannot cause a false join.
        self.state_origins[id(state)] = (state, payload.get('_qualification'))
        return state
    def _store_payload(self, payload):
        log('source_received', metadata=payload.get('_qualification'), original_payload=payload)
        return super()._store_payload(payload)
    def _make_msg(self, state, stamp):
        entry = self.state_origins.get(id(state))
        self.selected = entry[1] if entry and entry[0] is state else {'origin':'ORIGINAL_NEUTRAL','reason':state['source']}
        return super()._make_msg(state, stamp)

class Mapper(HandPoseMapper):
    def __init__(self):
        self.selected = None
        super().__init__()
        self.pub = Publisher(self.pub, 'mapper', lambda:self.selected)
    def _on_pose_states(self, msg):
        self.selected = consume('mapper', msg)
        return super()._on_pose_states(msg)

class Bridge(ServoCommandBridge):
    def __init__(self):
        self.selected = None
        super().__init__()
        self._pub = Publisher(self._pub, 'bridge_servo_input', lambda:self.selected)
    def _on_input(self, msg):
        self.selected = consume('bridge', msg)
        return super()._on_input(msg)

rclpy.init()
nodes = [Receiver(),Mapper(),Bridge()]
executor = SingleThreadedExecutor()
for node in nodes:
    executor.add_node(node)
try:
    executor.spin()
finally:
    executor.shutdown()
    for node in nodes:
        node.destroy_node()
