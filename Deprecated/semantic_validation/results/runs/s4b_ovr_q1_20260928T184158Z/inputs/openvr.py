"""Scheduled fake OpenVR API for the XRROS-S4-1.0.0 W0-W5 fixtures (fake only).

It reuses the S3 fake dependency surface (/harness/openvr.py) and replaces only
the per-poll pose/state schedule. Nothing here makes a validity decision; the
original quest_teleop.py consumes the fake exactly as it would the real API.

Index = poll number since the acknowledged barrier (50 Hz, 600 polls = 12 s).
Common shape (protocol section 7): raw reference (1,2,3), identity rotation,
z advances .001 per ramp poll.
  W0 idle (grip never pressed), valid.
  W1 0-49 idle | 50-99 reference | 100-399 ramp (300 steps) | 400-499 final
     hold | 500-599 tail (released).
  W2 = W1 with eTrackingResult=201 (Running_OutOfRange) on every poll.
  W3 = W1 with bPoseIsValid=false on every poll.
  W4 0-49 idle | 50-99 reference | 100-149 ramp (50 steps) | 150-199 invalid
     (bPoseIsValid=false, grip held, pose held) | 200-239 recovered, grip held |
     240-249 released (.2 s) | 250-259 press, new reference at unchanged pose
     (.2 s, separates the fresh reference from later motion) | 260-359 ramp
     (100 steps) | 360-499 hold | 500-599 tail.
  W5 = W4 timing with a disconnect instead of validity loss at 150-199
     (bDeviceIsConnected=false, bPoseIsValid=false, eTrackingResult=1
     Uninitialized, declared fake values) and harness connection generation 2
     from poll 200. The generation ID is harness instrumentation, not native.
  NONE = W1 (used by C-ID/C-MON coverage).
The harness sample time is instrumentation, never claimed as a native field
(the tested pose struct has no per-sample timestamp).
"""
import importlib.util
import json
import os
import time
from pathlib import Path

spec = importlib.util.spec_from_file_location('s3_fake', '/harness/openvr.py')
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)
for _name in dir(base):
    if not _name.startswith('__'):
        globals()[_name] = getattr(base, _name)

CASE = os.environ.get('OVR_CASE', 'W1')
CURRENT = None
TrackingResult_Uninitialized = 1


def schedule(case, index):
    """(phase, grip, valid, connected, result, z, generation) for one poll index."""
    valid, connected, result, generation = True, True, TrackingResult_Running_OK, 1
    if case == 'W0':
        return 'idle', False, valid, connected, result, 0.0, generation
    if case in ('W1', 'W2', 'W3', 'NONE'):
        if index < 50:
            phase, grip, z = 'idle', False, 0.0
        elif index < 100:
            phase, grip, z = 'reference', True, 0.0
        elif index < 400:
            phase, grip, z = 'ramp', True, .001 * (index - 99)
        elif index < 500:
            phase, grip, z = 'hold', True, .3
        else:
            phase, grip, z = 'tail', False, .3
        if case == 'W2':
            result = TrackingResult_Running_OutOfRange
        if case == 'W3':
            valid = False
        return phase, grip, valid, connected, result, z, generation
    if case not in ('W4', 'W5'):
        raise ValueError(case)
    if index < 50:
        phase, grip, z = 'idle', False, 0.0
    elif index < 100:
        phase, grip, z = 'reference', True, 0.0
    elif index < 150:
        phase, grip, z = 'ramp', True, .001 * (index - 99)
    elif index < 200:
        phase, grip, z = ('invalid' if case == 'W4' else 'disconnected'), True, .05
        if case == 'W4':
            valid = False
        else:
            valid, connected, result = False, False, TrackingResult_Uninitialized
    elif index < 240:
        phase, grip, z = 'recovered_held', True, .05
    elif index < 250:
        phase, grip, z = 'released', False, .05
    elif index < 260:
        phase, grip, z = 'new_reference', True, .05
    elif index < 360:
        phase, grip, z = 'resumed_ramp', True, .05 + .001 * (index - 259)
    elif index < 500:
        phase, grip, z = 'hold', True, .15
    else:
        phase, grip, z = 'tail', False, .15
    if case == 'W5' and index >= 200:
        generation = 2
    return phase, grip, valid, connected, result, z, generation


class Scheduled(base._FakeVRSystem):
    def getDeviceToAbsoluteTrackingPose(self, universe, predicted_seconds, poses):
        global CURRENT
        index = self.call_count
        phase, grip, valid, connected, result, z, generation = schedule(CASE, index)
        self.valid = valid
        self.tracking_result = result
        self.default_grip = grip
        self.motion_step = [0, 0, 0]
        super().getDeviceToAbsoluteTrackingPose(universe, predicted_seconds, poses)
        poses[0].bDeviceIsConnected = connected
        poses[0].mDeviceToAbsoluteTracking[2][3] = 3.0 + z
        now = time.monotonic_ns()
        CURRENT = dict(sample_id=f'openvr:{index}', generation_id=generation, source_timestamp_ns=now,
                       phase=phase, index=index, case=CASE,
                       native_state=dict(bPoseIsValid=bool(poses[0].bPoseIsValid),
                                         bDeviceIsConnected=bool(poses[0].bDeviceIsConnected),
                                         eTrackingResult=int(poses[0].eTrackingResult)),
                       matrix=[[float(poses[0].mDeviceToAbsoluteTracking[r][c]) for c in range(4)] for r in range(3)],
                       grip=grip)
        with Path(os.environ['TRIAL_ROOT'], 'source.jsonl').open('a') as f:
            f.write(json.dumps(CURRENT, sort_keys=True) + '\n')

    def getControllerState(self, index):
        # The grip of the most recent acquisition (same sample as the pose).
        pressed = (1 << k_EButton_Grip) if (CURRENT or {}).get('grip') else 0
        return True, base._ControllerState(pressed)


def init(application_type):
    return Scheduled()
