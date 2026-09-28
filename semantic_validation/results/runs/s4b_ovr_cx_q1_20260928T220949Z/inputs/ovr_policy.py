"""XRROS-S4-1.0.0 OpenVR validity + invalidation/recovery predicate (pure logic, no ROS).

One implementation is shared by the B1 source gate, the official B2 TLOracle
property and the B3 publish-point check, so each receives the identical policy.
OpenVR validity (section 5): bDeviceIsConnected=true, bPoseIsValid=true,
eTrackingResult=200 (Running_OK), grip pressed. Result=201, invalid,
disconnected or unavailable required state is forbidden. Freshness F250,
future time and R_EXPLICIT/R_AUTO re-arm are the shared d5_rearm.Rearm rules.
"""
import os

from d5_rearm import Rearm

RUNNING_OK = 200


class OvrPolicy:
    def __init__(self, policy=None, freshness_ns=None):
        policy = policy or os.environ.get('XR_REARM_POLICY', 'R_EXPLICIT')
        freshness_ns = freshness_ns or int(os.environ.get('XR_FRESHNESS_NS', '250000000'))
        self.rearm = Rearm(policy, freshness_ns)
        self.cid = None
        if os.environ.get('CASE_ID') == 'CID':
            from cid_binding import Ingestion
            self.cid = Ingestion()

    @property
    def armed(self):
        return self.rearm.armed

    def sample(self, meta, now_ns, acquired=None, ingestion_key=None):
        """(allowed, reason) for one acquired sample; call once per real source sample.

        C-ID (CASE_ID=CID): first the ordinary binding check (cid_binding.check) of the
        bound metadata against the command projection actually acquired, then duplicate
        detection on new ingestion (key = this acquisition), exactly as in Docker C-ID;
        a failure latches DISARMED (R_EXPLICIT) like any invalidation.
        """
        native = (meta or {}).get('native_state') or {}
        if self.cid is not None:
            from cid_binding import check
            ok, reason = check(meta, acquired)
            if ok:
                ok, reason = self.cid.observe((meta or {}).get('sample_id'), ingestion_key)
            if not ok:
                self.rearm._fault(now_ns, reason)
                return (not bool((meta or {}).get('grip'))), reason
        pose_valid = native.get('bPoseIsValid')
        connected = native.get('bDeviceIsConnected')
        result = native.get('eTrackingResult')
        grip = bool((meta or {}).get('grip'))
        if pose_valid is None or connected is None or result is None:
            tracked = None
        else:
            tracked = bool(pose_valid) and result == RUNNING_OK
        allowed, reason = self.rearm.sample((meta or {}).get('generation_id'), grip, tracked,
                                            (meta or {}).get('source_timestamp_ns'), now_ns,
                                            None if connected is None else bool(connected))
        if reason == 'INVALID_TRACKING' and pose_valid and result != RUNNING_OK:
            reason = 'TRACKING_RESULT_NOT_RUNNING_OK'
        return allowed, reason
