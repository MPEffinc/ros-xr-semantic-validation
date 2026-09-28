"""XRROS-S4-1.0.0 C-ID source state/command binding contract (ordinary checks, no ROS).

REFERENCE: at source capture, the sender binds the source-event ID, generation,
original stamp, native state and the INTENDED command projection into
`binding_sha256`, carried unmodified in `_qualification`.
CHECK: a defense recomputes the command projection from the command payload it
is about to forward (B1: the outgoing wire; B2/B3: the ROS message fields the
original receiver produced), combines it with the metadata's ID/generation/
stamp/state and compares with the reference. The reference is never
regenerated from the downstream payload.

Projection = the fields the original receiver copies from wire to ROS command:
right-hand tracked, pose position/orientation, teleop_enable, grip_value.
"""
import hashlib
import json

REQUIRED = ('sample_id', 'generation_id', 'source_timestamp_ns', 'native_state', 'binding_sha256')


def _canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(',', ':'), allow_nan=False)


def projection(tracked, pos, rot, teleop, grip):
    return dict(tracked=bool(tracked), pos=[float(v) for v in pos], rot=[float(v) for v in rot],
                teleop=bool(teleop), grip=round(float(grip), 6))


def projection_from_wire(payload):
    hand, controls = payload['right_hand'], payload['controls']
    return projection(hand['isTracked'], [hand['pos'][a] for a in 'xyz'], [hand['rot'][a] for a in 'xyzw'],
                      controls.get('right_teleop_enable', controls.get('teleop_enable')), controls['grip_value'])


def projection_from_ros_fields(fields):
    pose = fields['pose']
    return projection(fields['tracked'], [pose['position'][a] for a in 'xyz'],
                      [pose['orientation'][a] for a in 'xyzw'], fields['teleop_enable'], fields['grip_value'])


def binding_hash(sample_id, generation_id, stamp_ns, native_state, proj):
    return hashlib.sha256(_canonical(dict(sample_id=sample_id, generation_id=generation_id,
                                          source_timestamp_ns=stamp_ns, native_state=native_state,
                                          command=proj)).encode()).hexdigest()


def check(meta, proj):
    """(ok, reason) for one source event; meta is the bound metadata, proj the checked command."""
    if meta is None:
        return False, 'UNBOUND_REQUIRED_STATE'
    missing = [k for k in REQUIRED if meta.get(k) is None]
    if 'sample_id' in missing:
        return False, 'MISSING_SOURCE_EVENT_ID'
    if missing:
        return False, 'MISSING_REQUIRED_FIELD'
    if binding_hash(meta['sample_id'], meta['generation_id'], meta['source_timestamp_ns'],
                    meta['native_state'], proj) != meta['binding_sha256']:
        return False, 'STATE_COMMAND_MISMATCH'
    return True, 'BOUND'


class Ingestion:
    """Duplicate detection on NEW source-event ingestion only.

    `key` identifies one ingestion (B1: the sample's own creation; B2/B3: the
    ORIGINAL receiver's receipt time). Re-evaluating the same ingestion (cached
    republication of an accepted sample) is not a duplicate; a previously
    ingested source-event ID arriving in a DIFFERENT ingestion is.
    """
    def __init__(self):
        self.first_key = {}

    def observe(self, sample_id, key):
        if sample_id is None or key is None:
            return False, 'MISSING_SOURCE_EVENT_ID' if sample_id is None else 'MISSING_INGESTION_KEY'
        first = self.first_key.setdefault(sample_id, key)
        return (True, 'NEW_OR_CACHED') if first == key else (False, 'DUPLICATE_SOURCE_EVENT_ID')
