"""D1-specific XRROS-S4-1.0.0 property for official TLOracle/Reelay.

Not a monitor implementation. The official ROSMonitoring filter sends each
received event to the official oracle; this module only maps that event to the
pre-registered task predicate. I_NATIVE incompleteness is logged separately.
"""
import json
import os
import time

from d1_contract import d1_allow

PROPERTY = '{safe}'
predicates = {'safe': True, 'time': 0}
_event_index = 0


def abstract_message(message):
    global _event_index
    now = time.monotonic_ns()
    regime = os.environ.get('INFO_REGIME', 'full')
    if regime == 'full':
        envelope = json.loads(message['data'])
        origin = envelope['selected_origin']
        fields = envelope['original_payload']
        if origin.get('origin') == 'ORIGINAL_NEUTRAL':
            allowed, reason = True, 'ORIGINAL_NEUTRAL'
        else:
            allowed, reason = d1_allow(origin.get('native_state'),
                                       bool(fields['teleop_enable']),
                                       origin.get('source_timestamp_ns'), now,
                                       origin.get('generation_id'))
            if allowed is None:
                allowed = False
        sample_id = origin.get('sample_id')
    else:
        fields = message
        sample_id = None
        # I_NATIVE has no validated generation/source-age; no full-policy PASS.
        allowed = not fields.get('teleop_enable', False) or bool(fields.get('tracked', False))
        reason = 'NATIVE_WIRE_ONLY_UNOBSERVABLE_TIME_GENERATION'
    predicates['safe'] = bool(allowed)
    # This current-event property has no timed operator. Reelay discrete
    # requires a strictly increasing logical event index; decision age above
    # still uses CLOCK_MONOTONIC, never this index or ROS wall time.
    _event_index += 1
    predicates['time'] = _event_index
    log_path = os.environ.get('XR_D1_PROPERTY_LOG')
    if log_path:
        with open(log_path, 'a', encoding='utf-8') as handle:
            handle.write(json.dumps(dict(monotonic_ns=now, regime=regime,
                                         sample_id=sample_id, safe=bool(allowed),
                                         reason=reason), sort_keys=True) + '\n')
    return predicates
