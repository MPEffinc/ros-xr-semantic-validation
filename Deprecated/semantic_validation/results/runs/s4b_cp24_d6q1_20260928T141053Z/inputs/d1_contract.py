"""XRROS-S4-1.0.0 D1 transport and policy primitives, not a new defense.

The serializer carries one original ROS message and the metadata bound in the
receiver's in-process selected source state. It never makes an allow decision.
"""
import hashlib
import json
import os

# D4Q1: one registered freshness profile per trial (F100/F250/F500), set by the
# trial owner; identical for B1, the B2 oracle property and B3. Default F250.
FRESHNESS_NS = int(os.environ.get('XR_FRESHNESS_NS', '250000000'))


def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(',', ':'), allow_nan=False)


def payload_hash(ros_fields):
    return hashlib.sha256(canonical(ros_fields).encode()).hexdigest()


def make_envelope(ros_fields, selected, created_ns):
    if selected is None:
        raise ValueError('selected source origin missing')
    return dict(schema='XRROS-S4-1.0.0/d1-envelope-v1',
                original_type='teleop_bridge_msgs/msg/ReceivedPoseStates',
                original_payload=ros_fields,
                original_payload_sha256=payload_hash(ros_fields),
                selected_origin=selected,
                envelope_monotonic_ns=int(created_ns),
                outer_clock='CLOCK_MONOTONIC',
                nested_header_clock='ROS_TIME')


def verify_transport(envelope):
    """Check lossless transport only; never inspect validity/age/recovery."""
    if envelope.get('schema') != 'XRROS-S4-1.0.0/d1-envelope-v1':
        raise ValueError('unexpected envelope schema')
    fields = envelope['original_payload']
    if payload_hash(fields) != envelope['original_payload_sha256']:
        raise ValueError('ROS payload transport hash mismatch')
    return fields


def source_fields(selected):
    """Select native metadata only if bound to the same receiver state object."""
    if selected is None or selected.get('origin') == 'ORIGINAL_NEUTRAL':
        return None
    return selected


def d1_allow(native_state, teleop, source_ns, now_ns, generation, expected_generation=1,
             freshness_ns=None):
    """D1 predicate with the trial's registered freshness profile; R_EXPLICIT; no recovery."""
    if freshness_ns is None:
        freshness_ns = FRESHNESS_NS
    if native_state is None or source_ns is None or generation is None:
        return None, 'UNOBSERVABLE'
    if not teleop:
        return True, 'INTENTIONAL_UNGRIPPED_NEUTRAL'
    if not native_state.get('isTracked', False):
        return False, 'INVALID_TRACKING'
    if generation != expected_generation:
        return False, 'OLD_GENERATION'
    age = now_ns - source_ns
    if age < -5_000_000:
        return False, 'FUTURE_TIME'
    if age > freshness_ns:
        return False, 'STALE_SOURCE'
    return True, 'VALID_D1'
