#!/usr/bin/env python3
"""No-Gazebo regressions of the W0-W5 fake schedule and the shared OvrPolicy.

Run inside the Jazzy image with /code (inputs) and /harness mounted, because the
scheduled fake reuses the S3 fake at /harness/openvr.py.
"""
import importlib
import os
import sys
import tempfile
import unittest

sys.path.insert(0, '/code')
os.environ.setdefault('TRIAL_ROOT', tempfile.mkdtemp())
import openvr  # noqa: E402  the scheduled fake
from ovr_policy import OvrPolicy  # noqa: E402

PERIOD = 20_000_000


def run(case, policy='R_EXPLICIT'):
    """Poll the fake 600 times on a synthetic 50 Hz clock; return per-index decisions."""
    os.environ['OVR_CASE'] = case
    importlib.reload(openvr)
    vr = openvr.init(openvr.VRApplication_Background)
    pol = OvrPolicy(policy, 250_000_000)
    out = []
    for i in range(600):
        poses = (openvr.TrackedDevicePose_t * openvr.k_unMaxTrackedDeviceCount)()
        vr.getDeviceToAbsoluteTrackingPose(openvr.TrackingUniverseRawAndUncalibrated, 0, poses)
        meta = dict(openvr.CURRENT)
        t = 10 ** 12 + i * PERIOD
        meta['source_timestamp_ns'] = t
        allowed, reason = pol.sample(meta, t + 1_000_000)
        _, state = vr.getControllerState(0)
        grip = bool(state.ulButtonPressed & (1 << openvr.k_EButton_Grip))
        out.append(dict(i=i, phase=meta['phase'], grip=meta['grip'], api_grip=grip, allowed=allowed, reason=reason,
                        valid=meta['native_state']['bPoseIsValid'], conn=meta['native_state']['bDeviceIsConnected'],
                        result=meta['native_state']['eTrackingResult'], gen=meta['generation_id'],
                        z=poses[0].mDeviceToAbsoluteTracking[2][3]))
    return out


class Schedule(unittest.TestCase):
    def test_indices_and_grip_consistency(self):
        for case in ('W0', 'W1', 'W2', 'W3', 'W4', 'W5'):
            out = run(case)
            self.assertEqual([o['i'] for o in out], list(range(600)))
            self.assertTrue(all(o['grip'] == o['api_grip'] for o in out))

    def test_w1_shape(self):
        out = run('W1')
        self.assertTrue(all(not o['grip'] for o in out[:50]) and all(o['grip'] for o in out[50:500]))
        self.assertAlmostEqual(out[399]['z'], 3.3, places=5)
        self.assertTrue(all(o['allowed'] for o in out))

    def test_w2_w3_block_every_grip_sample(self):
        for case, reason in (('W2', 'TRACKING_RESULT_NOT_RUNNING_OK'), ('W3', 'INVALID_TRACKING')):
            out = run(case)
            grip = [o for o in out if o['grip']]
            self.assertTrue(grip and not any(o['allowed'] for o in grip))
            self.assertEqual(out[50]['reason'], reason)
            self.assertTrue(all(o['allowed'] for o in out if not o['grip']))   # ungripped neutral passes

    def test_w4_explicit(self):
        out = run('W4', 'R_EXPLICIT')
        self.assertTrue(all(o['allowed'] for o in out[:150]))
        self.assertTrue(not any(o['allowed'] for o in out[150:240]))          # invalid, then held grip
        self.assertTrue(all(o['allowed'] for o in out[240:250]))              # released: neutral
        self.assertEqual(out[250]['reason'], 'R_EXPLICIT_REARMED_ON_RISING_EDGE')
        self.assertTrue(all(o['allowed'] for o in out[250:]))

    def test_w4_auto(self):
        out = run('W4', 'R_AUTO')
        self.assertTrue(not any(o['allowed'] for o in out[150:225]))
        self.assertEqual(out[225]['reason'], 'R_AUTO_REARMED')
        self.assertTrue(all(o['allowed'] for o in out[225:]))

    def test_w5_disconnect_generation(self):
        out = run('W5', 'R_EXPLICIT')
        self.assertEqual(out[150]['reason'], 'DISCONNECTED')
        self.assertEqual((out[150]['conn'], out[150]['valid'], out[150]['result']), (False, False, 1))
        self.assertEqual({o['gen'] for o in out[200:]}, {2})
        self.assertEqual(out[250]['reason'], 'R_EXPLICIT_REARMED_ON_RISING_EDGE')

    def test_unbound_state_rejected(self):
        pol = OvrPolicy('R_EXPLICIT', 250_000_000)
        self.assertEqual(pol.sample(dict(grip=True, generation_id=1, source_timestamp_ns=1, native_state={}), 2),
                         (False, 'UNBOUND_REQUIRED_STATE'))

    def test_stale_rejected(self):
        pol = OvrPolicy('R_EXPLICIT', 250_000_000)
        meta = dict(grip=True, generation_id=1, source_timestamp_ns=0,
                    native_state=dict(bPoseIsValid=True, bDeviceIsConnected=True, eTrackingResult=200))
        self.assertEqual(pol.sample(meta, 251_000_000), (False, 'STALE_SOURCE'))


if __name__ == '__main__':
    unittest.main(verbosity=2)
