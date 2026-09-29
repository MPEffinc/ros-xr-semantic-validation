"""OpenVR I_FULL task property for the official TLOracle/Reelay (not a monitor).

The official generated ROSMonitoring filter sends each received envelope to the
official oracle; this module only maps the envelope to the pre-registered task
predicate (shared ovr_policy.OvrPolicy, identical to B1/B3). One envelope exists
per acquired sample (pose-bearing or state-only), so the recovery state machine
sees every real source sample exactly once. Calibration envelopes are never
source samples and are always allowed.
"""
import hashlib
import json
import os
import time

from d1_contract import canonical
from ovr_policy import OvrPolicy

PROPERTY = '{safe}'
predicates = {'safe': True, 'time': 0}
_event_index = 0
_policy = OvrPolicy()


def abstract_message(message):
    global _event_index
    now = time.monotonic_ns()
    envelope = json.loads(message['data'])
    kind = envelope.get('kind')
    origin = envelope.get('selected_origin') or {}
    if kind == 'calibration':
        safe, reason, sample_id = True, 'CALIBRATION_NOT_A_SOURCE_SAMPLE', None
    else:
        safe, reason = _policy.sample(origin, now, envelope.get('acquired_projection'), envelope.get('ingestion_monotonic_ns'))
        sample_id = origin.get('sample_id')
    predicates['safe'] = bool(safe)
    _event_index += 1
    predicates['time'] = _event_index
    log_path = os.environ.get('XR_D3_PROPERTY_LOG')
    if log_path:
        with open(log_path, 'a', encoding='utf-8') as handle:
            handle.write(json.dumps(dict(
                monotonic_ns=now, regime='full', envelope_kind=kind,
                monitor_event_id=envelope.get('envelope_monotonic_ns'), sample_id=sample_id,
                payload_sha256=hashlib.sha256(canonical(envelope.get('original_payload')).encode()).hexdigest(),
                safe=bool(safe), reason=reason, teleop=bool(origin.get('grip')) if kind != 'calibration' else None,
                rearm_armed_after=_policy.armed, rearm_events=_policy.rearm.events[-3:]), sort_keys=True) + '\n')
    return predicates
