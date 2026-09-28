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
from monitor_readiness import record_monitor_match
from d1_contract import canonical, d1_allow, make_envelope, verify_transport
from mapper_lineage_state import MapperLineageState
from d3_silence import SourceSilence
from trace import Publisher, bind, consume, digest, EDGES, log
from source_payload_hash import source_payload_sha256
from post_capture_lifecycle import capture_has_ended
from source_path_readiness import exact_ack, full_guarded_receipt_fields

MODE = os.environ['MODE']
REGIME = os.environ['INFO_REGIME']


class Receiver(QuestControllerReceiver):
    def __init__(self):
        self.post_capture_quiesced = False
        self.source_path_ready = MODE != 'b2'
        # D5: observation of the ORIGINAL receiver's own TCP accept/drop events.
        # It is attached only to the in-process selected origin (I_FULL envelope /
        # B3 parent); the native ROS message is unchanged.
        self.connection_state = {'index': 0, 'open': False}
        self.state_origins = {}
        self.receipt_by_sample_id = {}
        self.selected = None
        super().__init__()
        original_pub = self.pub
        if MODE == 'b2':
            if REGIME == 'full':
                target = self.create_publisher(String, '/s4b/d1/envelope_mon', 20)
            else:
                target = self.create_publisher(ReceivedPoseStates, '/s4b/d1/native_input_mon', 20)
            # Only the post-filter Stripper may publish to the Mapper input.
            self.destroy_publisher(original_pub)
            self.pub = D1MonitorPublisher(target, lambda: self.selected)
        else:
            self.pub = Publisher(original_pub, 'receiver', lambda: self.selected)

    def _publish_loop(self):
        # Q4: do not emit original pre-barrier neutrals until the actual
        # official source input -> oracle -> guarded subscriber path ACKs.
        if not self.source_path_ready:
            return
        # Prospective trial lifecycle, strictly after the fixed D3 outcome
        # capture. Never inspect XR state or suppress an already published event.
        if capture_has_ended(os.environ['TRIAL_ROOT']):
            if not self.post_capture_quiesced:
                self.post_capture_quiesced = True
                log('post_capture_receiver_quiesced',
                    capture_end_marker=str(Path(os.environ['TRIAL_ROOT']) / 'capture_end.ready'))
                Path(os.environ['TRIAL_ROOT'], 'receiver_quiesced.ready').write_text(
                    str(time.monotonic_ns()) + '\n')
            return
        return super()._publish_loop()

    def _set_client(self, client_sock, sender_label):
        result = super()._set_client(client_sock, sender_label)
        self.connection_state = {'index': self.connection_state['index'] + 1, 'open': True}
        log('receiver_connection', event='accepted', **self.connection_state)
        return result

    def _drop_client(self, reason):
        had_client = self._client_sock is not None
        result = super()._drop_client(reason)
        if had_client:
            self.connection_state = {'index': self.connection_state['index'], 'open': False}
            log('receiver_connection', event='dropped', reason=reason, **self.connection_state)
        return result

    def _parse_payload(self, payload, *args, **kwargs):
        state = super()._parse_payload(payload, *args, **kwargs)
        self.state_origins[id(state)] = (state, payload.get('_qualification'))
        return state

    def _store_payload(self, payload):
        metadata = payload.get('_qualification') or {}
        sample_id = metadata.get('sample_id')
        receipt_ns = time.monotonic_ns()
        if sample_id is not None:
            self.receipt_by_sample_id[sample_id] = receipt_ns
        log('source_received', metadata=payload.get('_qualification'), original_payload=payload,
            receiver_receipt_monotonic_ns=receipt_ns)
        result = super()._store_payload(payload)
        if sample_id is not None:
            log('original_receiver_source_stored', sample_id=sample_id,
                receiver_receipt_monotonic_ns=receipt_ns,
                receiver_cache_monotonic_ns=int(self._last_packet_time_monotonic * 1_000_000_000),
                payload_sha256=source_payload_sha256(payload))
        return result

    def _make_msg(self, state, stamp):
        entry = self.state_origins.get(id(state))
        if entry and entry[0] is state and entry[1] is not None:
            self.selected = dict(entry[1])
            self.selected['receiver_receipt_monotonic_ns'] = self.receipt_by_sample_id.get(
                self.selected.get('sample_id'))
        else:
            self.selected = {'origin': 'ORIGINAL_NEUTRAL', 'reason': state['source']}
        if os.environ.get('CASE_ID') == 'D5':
            self.selected['receiver_connection'] = dict(self.connection_state)
        return super()._make_msg(state, stamp)


class D1MonitorPublisher:
    def __init__(self, target, parent):
        self.target, self.parent = target, parent

    def publish(self, msg):
        fields = message_to_ordereddict(msg)
        selected = self.parent()
        subscription_count = self.target.get_subscription_count()
        if REGIME == 'full':
            envelope = make_envelope(fields, selected, time.monotonic_ns())
            event_id = envelope['envelope_monotonic_ns']
            log('publish', stage='receiver_envelope', selected_origin=selected,
                monitor_event_id=event_id,
                original_payload_sha256=envelope['original_payload_sha256'],
                dds_subscription_count_before=subscription_count)
            self.target.publish(String(data=canonical(envelope)))
            log('monitor_input_publish_call_return', monitor_event_id=event_id,
                dds_subscription_count_after=self.target.get_subscription_count())
        else:
            edge = bind('receiver_native_monitor_input', msg, selected)
            log('monitor_input_publish_call_enter', monitor_input_id=edge['command_id'],
                dds_subscription_count_before=subscription_count)
            self.target.publish(msg)
            log('monitor_input_publish_call_return', monitor_input_id=edge['command_id'],
                dds_subscription_count_after=self.target.get_subscription_count())
        assert message_to_ordereddict(msg) == fields

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
        log('monitor_output_received', **full_guarded_receipt_fields(envelope))
        fields = verify_transport(envelope)
        msg = ReceivedPoseStates()
        set_message_fields(msg, fields)
        assert message_to_ordereddict(msg) == fields
        bind('stripper_restored', msg, dict(envelope['selected_origin'],
             monitor_event_id=envelope['envelope_monotonic_ns']))
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
        log('monitor_output_received', regime='native',
            payload_sha256=digest(msg), monitor_input_id=parent['command_id'])
        bind('stripper_restored', msg, dict(parent['parent'],
             monitor_input_id=parent['command_id']) if isinstance(parent['parent'], dict) else parent['parent'])
        self.pub.publish(msg)


class Mapper(ReceivedPoseToTargetTwist):
    def __init__(self):
        self.lineage = MapperLineageState()
        super().__init__()
        self.pub = Publisher(self.pub, 'mapper', self.lineage.timer_parent)
        if MODE == 'b3':
            self.rearm = None
            if os.environ.get('CASE_ID') == 'D5' and REGIME == 'full':
                from d5_rearm import Rearm
                self.rearm = Rearm(os.environ['XR_REARM_POLICY'])
                self.rearm_logged = 0
            self.silence = SourceSilence()
            self.silence_fired = False
            self.tick_subscription = self.create_subscription(
                String, '/s4b/d3/common_tick', self._on_d3_tick, 20)

    def _on_d3_tick(self, wire):
        tick = json.loads(wire.data)
        if tick.get('kind') != 'health_tick':
            return
        state = self.silence.tick(time.monotonic_ns())
        log('b3_silence_tick', tick_id=tick['tick_id'], state=state,
            info_regime=REGIME)
        if state['state'] == 'SOURCE_SILENCE' and not self.silence_fired:
            self.silence_fired = True
            log('b3_mapper_verdict', event_kind='health_tick',
                tick_id=tick['tick_id'], verdict=False,
                reason='SOURCE_SILENCE',
                parent_sample_id=state['last_sample_id'],
                trigger_monotonic_ns=state['trigger_ns'])

    def _on_pose_states(self, msg):
        candidate = consume('mapper', msg)
        self.lineage.observe(candidate)
        if MODE == 'b3':
            origin = candidate['parent'] if candidate else None
            if (REGIME == 'full' and origin and origin.get('sample_id') is not None
                    and origin.get('receiver_receipt_monotonic_ns') is not None):
                new_source = self.silence.receive(
                    origin['sample_id'], origin['receiver_receipt_monotonic_ns'],
                    bool(msg.teleop_enable),
                    bool((origin.get('native_state') or {}).get('isTracked')),
                    origin.get('generation_id'))
                if new_source:
                    log('b3_real_source_selected', sample_id=origin['sample_id'],
                        receiver_receipt_monotonic_ns=origin['receiver_receipt_monotonic_ns'],
                        info_regime=REGIME)
            if self.rearm is not None and origin is not None:
                now = time.monotonic_ns()
                connection = origin.get('receiver_connection') or {}
                if 'sample_id' in origin:
                    verdict, reason = self.rearm.sample(
                        origin.get('generation_id'), bool(msg.teleop_enable),
                        (origin.get('native_state') or {}).get('isTracked'),
                        origin.get('source_timestamp_ns'), now, connection.get('open'))
                else:
                    # D5Q2: only a drop of an ACCEPTED connection (index >= 1) is a
                    # disconnect; the pre-connection startup neutral is not.
                    if (connection.get('open') is False and connection.get('index', 0) >= 1
                            and self.rearm.armed):
                        self.rearm.disconnect(now)
                    verdict, reason = True, 'ORIGINAL_NEUTRAL'
                for event in self.rearm.events[self.rearm_logged:]:
                    # D5Q2: event keys renamed so they cannot collide with log()'s own.
                    log('b3_rearm_event', info_regime=REGIME,
                        **{('event_' + k if k in ('kind', 'monotonic_ns') else k): v for k, v in event.items()})
                self.rearm_logged = len(self.rearm.events)
            elif REGIME == 'full' and origin and 'sample_id' in origin:
                verdict, reason = d1_allow(origin.get('native_state'), bool(msg.teleop_enable),
                                           origin.get('source_timestamp_ns'), time.monotonic_ns(),
                                           origin.get('generation_id'))
            elif REGIME == 'native':
                verdict = not msg.teleop_enable or bool(msg.tracked)
                reason = 'NATIVE_WIRE_ONLY_UNOBSERVABLE_TIME_GENERATION'
            else:
                verdict, reason = True, 'ORIGINAL_NEUTRAL'
            log('b3_mapper_verdict', verdict=verdict, reason=reason, teleop=bool(msg.teleop_enable),
                source_origin=origin, payload_sha256=digest(msg))
            if verdict is not True:
                self.lineage.reject(candidate)
                return
        result = super()._on_pose_states(msg)
        applied_snapshot = {'last_rx_time': self._last_rx_time,
                            'tracked': self._tracked,
                            'have_target': self._have_target,
                            'teleop_enabled': self._teleop_enable,
                            'position_session_active': self._position_session_active,
                            'position_recenter_pending': self._position_recenter_pending}
        self.lineage.apply_after_original_callback(candidate, applied_snapshot)
        log('mapper_applied_after_original_callback', exact_parent=candidate,
            state=applied_snapshot, payload_sha256=digest(msg))
        return result


class Bridge(TargetTwistToServoCmd):
    def __init__(self):
        self.selected = None
        self.post_capture_quiesced = False
        super().__init__()
        self._pub = Publisher(self._pub, 'bridge_servo_input', lambda: self.selected)

    def _on_input(self, msg):
        self.selected = consume('bridge', msg)
        return super()._on_input(msg)

    def _publish_loop(self):
        # Q5: only after the immutable six-second scored window. Drain
        # already-published source-parent commands before container teardown.
        if capture_has_ended(os.environ['TRIAL_ROOT']):
            if not self.post_capture_quiesced:
                self.post_capture_quiesced = True
                log('post_capture_bridge_quiesced',
                    capture_end_marker=str(Path(os.environ['TRIAL_ROOT']) / 'capture_end.ready'))
                Path(os.environ['TRIAL_ROOT'], 'bridge_quiesced.ready').write_text(
                    str(time.monotonic_ns()) + '\n')
            return
        return super()._publish_loop()


rclpy.init()
nodes = [Receiver(), Mapper(), Bridge()]
if MODE == 'b2':
    nodes.append(Stripper())
executor = SingleThreadedExecutor()
for node in nodes:
    executor.add_node(node)
if MODE == 'b2':
    # Construction alone is not readiness. Keep Receiver's original timer
    # unspun until the actual generated monitor subscription is DDS-matched.
    root = Path(os.environ['TRIAL_ROOT'])
    status_file = root / ('monitor_full_status.jsonl' if REGIME == 'full'
                          else 'monitor_native_status.jsonl')
    output_topic = '/s4b/d1/envelope' if REGIME == 'full' else '/s4b/d1/native_input'
    deadline = time.monotonic() + 20.0
    match = None
    while time.monotonic() < deadline:
        target = nodes[0].pub.target
        subscribed = target.get_subscription_count()
        output_publishers = nodes[-1].get_publishers_info_by_topic(output_topic)
        started = False
        if status_file.exists():
            with status_file.open() as stream:
                first = stream.readline()
            if first:
                try:
                    started = json.loads(first).get('status') == 'started'
                except json.JSONDecodeError:
                    pass
        if subscribed >= 1 and output_publishers and started:
            match = {'dds_match_monotonic_ns': time.monotonic_ns(),
                     'monitor_subscription_count': subscribed,
                     'output_publishers': [item.node_name for item in output_publishers],
                     'official_started_status': started,
                     'receiver_timer_processed_before_match': False}
            break
        time.sleep(.01)
    if match is None:
        raise RuntimeError('official monitor DDS match absent before receiver timer')
    record_monitor_match(root, match, log)
    receiver = nodes[0]
    calibration_path = root / 'calibration.jsonl'
    acknowledged = None
    # At most twelve *logged* non-control pre-barrier attempts, each separated
    # by 250 ms of actual executor processing. Lost attempts stay in the raw.
    for attempt in range(1, 13):
        neutral = receiver._neutral_state(source='readiness_calibration')
        msg = receiver._make_msg(neutral, receiver.get_clock().now().to_msg())
        payload = message_to_ordereddict(msg)
        origin = {'origin': 'ORIGINAL_NEUTRAL', 'reason': 'readiness_calibration'}
        created_ns = time.monotonic_ns()
        if REGIME == 'full':
            envelope = make_envelope(payload, origin, created_ns)
            key = envelope['envelope_monotonic_ns']
        else:
            key = digest(msg)
        record = {'attempt': attempt, 'regime': REGIME, 'key': key,
                  'created_monotonic_ns': created_ns,
                  'native_payload': payload,
                  'source_sample': False, 'control_input': False}
        with calibration_path.open('a') as stream:
            stream.write(json.dumps(record, sort_keys=True) + '\n')
        # Record every attempt before DDS publish. Even a lost attempt remains.
        log('source_path_calibration_attempt', **record)
        if REGIME == 'full':
            receiver.pub.target.publish(String(data=canonical(envelope)))
        else:
            bind('calibration_monitor_input', msg, origin)
            receiver.pub.target.publish(msg)
        log('source_path_calibration_publish_return', attempt=attempt, key=key,
            dds_subscription_count=receiver.pub.target.get_subscription_count())
        until = time.monotonic() + .25
        result = {'ok': False, 'reason': 'NO_EXACT_ACK_BEFORE_ATTEMPT_DEADLINE', 'key': key}
        while time.monotonic() < until:
            executor.spin_once(timeout_sec=.02)
            result = exact_ack(root, REGIME, record)
            if result['ok']:
                acknowledged = {'attempt': attempt, 'key': key,
                                'ack_monotonic_ns': time.monotonic_ns(),
                                'boundary': result}
                break
        with (root / 'calibration_verdicts.jsonl').open('a') as stream:
            stream.write(json.dumps({'attempt': attempt, 'key': key,
                                     'result': result,
                                     'verdict_monotonic_ns': time.monotonic_ns()},
                                    sort_keys=True) + '\n')
        if acknowledged:
            break
    if acknowledged is None:
        raise RuntimeError('actual official source path never acknowledged calibration neutral')
    (root / 'source_path_calibration.ready').write_text(json.dumps(acknowledged, sort_keys=True))
    log('source_path_calibration_ack', **acknowledged)
    receiver.source_path_ready = True
    log('receiver_timer_release', key=acknowledged['key'])
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
