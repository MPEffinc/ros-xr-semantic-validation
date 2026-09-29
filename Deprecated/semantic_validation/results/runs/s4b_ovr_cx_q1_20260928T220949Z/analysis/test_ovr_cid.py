#!/usr/bin/env python3
"""No-Gazebo OpenVR C-ID regressions (run in the Jazzy image with /code and /harness)."""
import importlib
import os
import sys
import tempfile
import unittest

sys.path.insert(0, '/code')
os.environ.setdefault('TRIAL_ROOT', tempfile.mkdtemp())
os.environ['CASE_ID'] = 'CID'
os.environ['OVR_CASE'] = 'NONE'
import openvr  # noqa: E402
import ovr_policy  # noqa: E402


def run(kind):
    os.environ['OVR_CID_KIND'] = kind
    importlib.reload(openvr)
    vr = openvr.init(openvr.VRApplication_Background)
    pol = ovr_policy.OvrPolicy('R_EXPLICIT', 250_000_000)
    out = []
    for i in range(600):
        poses = (openvr.TrackedDevicePose_t * openvr.k_unMaxTrackedDeviceCount)()
        vr.getDeviceToAbsoluteTrackingPose(openvr.TrackingUniverseRawAndUncalibrated, 0, poses)
        meta = openvr.CURRENT
        acquired = openvr.ovr_projection([[float(poses[0].mDeviceToAbsoluteTracking[r][c]) for c in range(4)] for r in range(3)], meta['grip'])
        allowed, reason = pol.sample(meta, meta['source_timestamp_ns'] + 1_000_000, acquired, 10 ** 9 + i)
        out.append((allowed, reason, meta['sample_id'], meta['grip']))
    return out


class Cid(unittest.TestCase):
    def test_bound_uninjected_positive_control(self):
        # MISMATCH run up to the injection is the bound positive control (every sample bound and admitted).
        out = run('MISMATCH')
        self.assertTrue(all(o[0] and o[1] in ('ARMED_VALID', 'INTENTIONAL_UNGRIPPED_NEUTRAL') for o in out[:150]))

    def test_mismatch(self):
        out = run('MISMATCH')
        self.assertTrue(all(o[0] for o in out[:150]))
        self.assertEqual(out[150][:2], (False, 'STATE_COMMAND_MISMATCH'))
        self.assertTrue(all(not o[0] and o[1] in ('DISARMED_DWELL', 'DISARMED_HELD_GRIP') for o in out[151:500]))

    def test_duplicate(self):
        out = run('DUPLICATE_ID')
        self.assertEqual(out[150][2], 'openvr:140')
        self.assertEqual(out[150][:2], (False, 'DUPLICATE_SOURCE_EVENT_ID'))
        self.assertTrue(all(o[0] for o in out[:150]))
        self.assertTrue(all(not o[0] for o in out[151:500]))


if __name__ == '__main__':
    unittest.main(verbosity=2)
