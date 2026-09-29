"""Original QuestTeleop (unchanged) with the registered B0/shim/B1/B2/B3 integration.

The original node object, its 50 Hz timer object and its callback are used as-is.
The timer is held until the acknowledged barrier in every arm (fixture schedule
only). For every arm except B0 the SAME timer's callback is wrapped (the rclpy
executor reads ``timer.callback`` at each expiry, so period and phase are the
original timer's):
  shim  observation only: exact lineage of each production publication.
  b1    source gate after fake-API acquisition, before production pose use: the
        gate acquires once, decides with the shared OvrPolicy, and only an allowed
        acquisition is handed (replayed, not re-polled) to the original callback.
        A blocked sample never reaches the original logic; the decision row is the
        stop adapter's verdict input (separately logged neutralization).
  b3    publish-point check in the original callback (reviewed local overlay
        placement): the original logic runs; immediately before target publish the
        shared OvrPolicy decision for the same acquired sample allows/blocks it.
  b2    I_FULL lossless envelope: each poll yields exactly one envelope carrying the
        acquired sample's bound native state (pose-bearing if the original published
        a PoseStamped in that callback, else state-only) on /s4b/ovr/envelope_mon; the
        official generated monitor filters it; ovr_nodes.py strips it back to the
        original PoseStamped for Servo. No policy decision here.
No vendor file is edited.
"""
import ctypes
import json
import os
import time
from pathlib import Path

import openvr
import rclpy
from quest_bridge.quest_teleop import QuestTeleop

root = Path(os.environ['TRIAL_ROOT'])
MODE = os.environ['MODE']
rclpy.init()
node = QuestTeleop()
node.timer.cancel()

if MODE != 'b0':
    from rosidl_runtime_py.convert import message_to_ordereddict
    from std_msgs.msg import String

    from d1_contract import canonical, payload_hash
    from ovr_policy import OvrPolicy
    from trace import Publisher, bind, log

    fake = node.vr
    original_callback = node.timer.callback
    state = dict(cached=None, decision=None, published=False, acquired=None, ingestion_ns=None)

    def acquisition(poses):
        """C-ID transport: the raw pose actually acquired (same poll) and this acquisition's time."""
        rows_ = [[float(poses[0].mDeviceToAbsoluteTracking[r][c]) for c in range(4)] for r in range(3)]
        state['acquired'] = openvr.ovr_projection(rows_, (openvr.CURRENT or {}).get('grip'))
        state['ingestion_ns'] = time.monotonic_ns()
    policy = OvrPolicy() if MODE in ('b1', 'b3') else None
    gate_log = (root / 'gate_verdict.jsonl').open('a', buffering=1) if MODE == 'b1' else None
    b1_failed = root / 'b1_gate_failed'
    b3_failed = root / 'b3_check_failed'

    class Proxy:
        """Passthrough of the fake API; for B1 it replays the gate's single acquisition."""

        def getDeviceToAbsoluteTrackingPose(self, universe, predicted_seconds, poses):
            if state['cached'] is not None:
                ctypes.memmove(ctypes.addressof(poses), ctypes.addressof(state['cached']), ctypes.sizeof(poses))
                return
            fake.getDeviceToAbsoluteTrackingPose(universe, predicted_seconds, poses)
            acquisition(poses)
            if MODE == 'b3':
                meta = openvr.CURRENT
                now = time.monotonic_ns()
                if b3_failed.exists():          # C-MON gate-crash model: no verdict, pass-through
                    state['decision'] = (True, 'B3_CHECK_FAILED_NO_DECISION')
                    return
                allowed, reason = policy.sample(meta, now, state['acquired'], state['ingestion_ns'])
                state['decision'] = (allowed, reason)
                log('b3_publish_check', sample_id=meta['sample_id'], index=meta['index'], verdict=bool(allowed),
                    reason=reason, teleop=bool(meta['grip']), source_timestamp_ns=meta['source_timestamp_ns'],
                    generation_id=meta['generation_id'], native_state=meta['native_state'], decision_monotonic_ns=now)

        def __getattr__(self, name):
            return getattr(fake, name)

    node.vr = Proxy()

    if MODE == 'b2':
        envelope_pub = node.create_publisher(String, '/s4b/ovr/envelope_mon', 20)
        node.destroy_publisher(node.publisher_)

        def envelope(kind, payload, meta, created_ns):
            return dict(schema='XRROS-S4-1.0.0/ovr-envelope-v1', kind=kind,
                        original_type='geometry_msgs/msg/PoseStamped' if payload is not None else None,
                        original_payload=payload,
                        original_payload_sha256=None if payload is None else payload_hash(payload),
                        selected_origin=meta, envelope_monotonic_ns=int(created_ns),
                        acquired_projection=state['acquired'] if kind != 'calibration' else None,
                        ingestion_monotonic_ns=state['ingestion_ns'] if kind != 'calibration' else None,
                        outer_clock='CLOCK_MONOTONIC', nested_header_clock='ROS_TIME')

        def send(kind, payload, meta):
            now = time.monotonic_ns()
            env = envelope(kind, payload, meta, now)
            text = canonical(env)
            log('publish', stage='production_envelope', envelope_kind=kind, monitor_event_id=env['envelope_monotonic_ns'],
                sample_id=None if meta is None else meta.get('sample_id'), original_payload_sha256=env['original_payload_sha256'],
                selected_origin=meta)
            envelope_pub.publish(String(data=text))
            return env

        class EnvelopePublisher:
            def publish(self, msg):
                fields = message_to_ordereddict(msg)
                send('pose', json.loads(json.dumps(fields)), openvr.CURRENT)
                state['published'] = True

        node.publisher_ = EnvelopePublisher()
    elif MODE == 'b3':
        class CheckedPublisher:
            def __init__(self, original):
                self.original = original

            def publish(self, msg):
                allowed, reason = state['decision'] or (False, 'NO_DECISION_FOR_SAMPLE')
                meta = openvr.CURRENT
                if allowed:
                    bind('production_pose', msg, meta)
                    self.original.publish(msg)
                else:
                    log('b3_blocked_publish', sample_id=meta['sample_id'], reason=reason,
                        payload=message_to_ordereddict(msg))

        node.publisher_ = CheckedPublisher(node.publisher_)
    else:
        node.publisher_ = Publisher(node.publisher_, 'production_pose', lambda: openvr.CURRENT)

    def wrapped():
        state['published'] = False
        state['decision'] = None
        if MODE == 'b1':
            poses = (openvr.TrackedDevicePose_t * openvr.k_unMaxTrackedDeviceCount)()
            fake.getDeviceToAbsoluteTrackingPose(openvr.TrackingUniverseRawAndUncalibrated, 0, poses)
            acquisition(poses)
            meta = openvr.CURRENT
            now = time.monotonic_ns()
            if b1_failed.exists():              # C-MON gate-crash model: no verdict, pass-through
                allowed, reason = True, 'B1_GATE_FAILED_NO_DECISION'
            else:
                allowed, reason = policy.sample(meta, now, state['acquired'], state['ingestion_ns'])
                gate_log.write(json.dumps(dict(index=meta['index'], sample_id=meta['sample_id'],
                                               decision_monotonic_ns=now, allowed=bool(allowed), reason=reason,
                                               teleop=bool(meta['grip']), source_timestamp_ns=meta['source_timestamp_ns'],
                                               generation_id=meta['generation_id'], native_state=meta['native_state']),
                                          sort_keys=True) + '\n')
            if not allowed:
                return                          # the original logic never sees this sample
            state['cached'] = poses
            try:
                original_callback()
            finally:
                state['cached'] = None
            return
        original_callback()
        if MODE == 'b2' and not state['published']:
            send('state', None, openvr.CURRENT)

    node.timer.callback = wrapped

    if MODE == 'b2':
        # Pre-barrier source-path calibration (never a source sample): repeated until the
        # recorder acknowledges one attempt end-to-end through the official monitor.
        attempt = 0
        last = 0.0
        calibration = (root / 'calibration.jsonl').open('a', buffering=1)

root.joinpath('production.ready').write_text('publisher constructed; spin held at source index zero\n')
while not root.joinpath('barrier.json').exists():
    if MODE == 'b2' and not root.joinpath('calibration.ack').exists() and envelope_pub.get_subscription_count() >= 1 \
            and time.monotonic() - last >= 1.0:
        attempt += 1
        last = time.monotonic()
        env = send('calibration', None, dict(calibration_attempt=attempt))
        calibration.write(json.dumps(dict(attempt=attempt, key=env['envelope_monotonic_ns'],
                                          created_monotonic_ns=env['envelope_monotonic_ns']), sort_keys=True) + '\n')
    time.sleep(.005)
start_ns = json.loads(root.joinpath('barrier.json').read_text())['start_monotonic_ns']
while time.monotonic_ns() < start_ns:
    time.sleep(min(.001, max(0, (start_ns - time.monotonic_ns()) / 1e9)))
node.timer.reset()
try:
    rclpy.spin(node)
finally:
    node.destroy_node()
