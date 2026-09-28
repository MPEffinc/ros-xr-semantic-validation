"""Prospective D3 property for genuine ROSMonitoring/TLOracle.

The official generated monitor remains the sole B2 ROS filter. This oracle
property evaluates bound source events and separately identified 50 Hz ticks.
It does not publish a control command or impersonate a source sample.
"""
import hashlib
import json
import os
import time

from d1_contract import canonical, d1_allow
from d3_silence import SourceSilence

PROPERTY = '{safe}'
predicates = {'safe': True, 'time': 0}
_event_index = 0
_source = SourceSilence()


def abstract_message(message):
    global _event_index
    now = time.monotonic_ns()
    regime = os.environ.get('INFO_REGIME', 'full')
    parsed = None
    if 'data' in message:
        parsed = json.loads(message['data'])
    is_tick = isinstance(parsed, dict) and parsed.get('kind') == 'health_tick'
    event_id = sample_id = tick_id = None
    receipt_ns = None
    if is_tick:
        tick_id = parsed['tick_id']
        state = _source.tick(now)
        if regime == 'full':
            safe = state['state'] != 'SOURCE_SILENCE'
            reason = state['state']
        else:
            safe = True
            reason = 'UNOBSERVABLE_SOURCE_RECEIPT_I_NATIVE'
        sample_id = state['last_sample_id']
        digest = hashlib.sha256(canonical(parsed).encode()).hexdigest()
    elif regime == 'full':
        envelope = parsed
        event_id = envelope['envelope_monotonic_ns']
        origin = envelope['selected_origin']
        fields = envelope['original_payload']
        digest = hashlib.sha256(canonical(fields).encode()).hexdigest()
        sample_id = origin.get('sample_id')
        receipt_ns = origin.get('receiver_receipt_monotonic_ns')
        if origin.get('origin') == 'ORIGINAL_NEUTRAL':
            safe, reason = True, 'ORIGINAL_NEUTRAL'
        else:
            safe, reason = d1_allow(origin.get('native_state'),
                                    bool(fields['teleop_enable']),
                                    origin.get('source_timestamp_ns'), now,
                                    origin.get('generation_id'))
            if safe is None:
                safe = False
            if sample_id is not None and receipt_ns is not None:
                _source.receive(sample_id, receipt_ns,
                                bool(fields['teleop_enable']),
                                bool((origin.get('native_state') or {}).get('isTracked')),
                                origin.get('generation_id'))
    else:
        fields = {key: value for key, value in message.items()
                  if key not in ('time', 'topic')}
        digest = hashlib.sha256(canonical(fields).encode()).hexdigest()
        safe = not fields.get('teleop_enable', False) or bool(fields.get('tracked', False))
        reason = 'NATIVE_WIRE_ONLY_UNOBSERVABLE_SOURCE_RECEIPT'

    predicates['safe'] = bool(safe)
    _event_index += 1
    predicates['time'] = _event_index
    log_path = os.environ.get('XR_D3_PROPERTY_LOG')
    if log_path:
        with open(log_path, 'a', encoding='utf-8') as handle:
            handle.write(json.dumps(dict(monotonic_ns=now, regime=regime,
                event_kind='tick' if is_tick else 'source_or_original_output',
                tick_id=tick_id, monitor_event_id=event_id,
                payload_sha256=digest, sample_id=sample_id,
                receiver_receipt_monotonic_ns=receipt_ns,
                source_timeout_trigger_ns=(_source.tick(now).get('trigger_ns')
                                           if is_tick else None),
                safe=bool(safe), reason=reason), sort_keys=True) + '\n')
    return predicates
