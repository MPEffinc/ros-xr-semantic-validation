"""Minimal deterministic OpenVR dependency fake for the pinned quest_bridge.

This module is injected through PYTHONPATH.  It does not replace or edit any
production quest_bridge logic; it only supplies the upstream OpenVR API surface
that quest_teleop.py calls.

Downstream variant: identical to the fake used for the ROS-boundary trials,
plus an optional linear controller translation (``OPENVR_FAKE_MOTION_*``).  The
ROS-boundary fake emitted a static pose, which after the production node's own
relative calibration yields a constant target and therefore cannot exercise a
motion consequence.  Motion is applied to the *raw controller pose*, i.e.
strictly upstream of every production decision in quest_teleop.py.
"""

import ctypes
import os
import sys


VRApplication_Background = 3
TrackingUniverseRawAndUncalibrated = 2
k_unMaxTrackedDeviceCount = 4
TrackedDeviceClass_Controller = 2
TrackedControllerRole_RightHand = 2
k_EButton_Grip = 2
TrackingResult_Running_OK = 200
TrackingResult_Running_OutOfRange = 201


class OpenVRError(Exception):
    pass


class HmdMatrix34_t(ctypes.Structure):
    _fields_ = [("m", (ctypes.c_float * 4) * 3)]

    def __getitem__(self, index):
        return self.m[index]


class TrackedDevicePose_t(ctypes.Structure):
    _fields_ = [
        ("mDeviceToAbsoluteTracking", HmdMatrix34_t),
        ("vVelocity", ctypes.c_float * 3),
        ("vAngularVelocity", ctypes.c_float * 3),
        ("eTrackingResult", ctypes.c_int),
        ("bPoseIsValid", ctypes.c_bool),
        ("bDeviceIsConnected", ctypes.c_bool),
    ]


class _ControllerState:
    def __init__(self, pressed):
        self.ulButtonPressed = pressed


def _bool_env(name, default):
    value = os.environ.get(name, default)
    return value.lower() in {"1", "true", "yes", "on"}


class _FakeVRSystem:
    def __init__(self):
        self.valid = _bool_env("OPENVR_FAKE_VALID", "true")
        result_name = os.environ.get("OPENVR_FAKE_TRACKING_RESULT", "Running_OK")
        self.tracking_result = {
            "Running_OK": TrackingResult_Running_OK,
            "Running_OutOfRange": TrackingResult_Running_OutOfRange,
        }[result_name]
        self.default_grip = _bool_env("OPENVR_FAKE_GRIP", "true")
        self.grip_sequence = os.environ.get("OPENVR_FAKE_GRIP_SEQUENCE", "")
        self.call_count = 0
        # Per-poll raw-pose translation, applied before any production logic.
        self.motion_step = [
            float(os.environ.get("OPENVR_FAKE_MOTION_X", "0.0")),
            float(os.environ.get("OPENVR_FAKE_MOTION_Y", "0.0")),
            float(os.environ.get("OPENVR_FAKE_MOTION_Z", "0.0")),
        ]
        self.motion_max_steps = int(os.environ.get("OPENVR_FAKE_MOTION_MAX_STEPS", "0"))
        print(
            "FAKE_OPENVR_CONFIG "
            f"valid={self.valid} tracking_result={result_name} "
            f"grip={self.default_grip} grip_sequence={self.grip_sequence or '-'} "
            f"motion_step={self.motion_step} motion_max_steps={self.motion_max_steps}",
            file=sys.stderr,
            flush=True,
        )

    def getDeviceToAbsoluteTrackingPose(self, universe, predicted_seconds, poses):
        self.call_count += 1
        pose = poses[0]
        pose.bPoseIsValid = self.valid
        pose.bDeviceIsConnected = True
        pose.eTrackingResult = self.tracking_result
        matrix = pose.mDeviceToAbsoluteTracking
        for row in range(3):
            for column in range(4):
                matrix[row][column] = 0.0
        matrix[0][0] = matrix[1][1] = matrix[2][2] = 1.0
        steps = self.call_count - 1
        if self.motion_max_steps:
            steps = min(steps, self.motion_max_steps)
        matrix[0][3] = 1.0 + self.motion_step[0] * steps
        matrix[1][3] = 2.0 + self.motion_step[1] * steps
        matrix[2][3] = 3.0 + self.motion_step[2] * steps

    def getTrackedDeviceClass(self, index):
        return TrackedDeviceClass_Controller if index == 0 else 0

    def getControllerRoleForTrackedDeviceIndex(self, index):
        return TrackedControllerRole_RightHand if index == 0 else 0

    def _grip_for_call(self):
        if not self.grip_sequence:
            return self.default_grip
        cursor = self.call_count
        for segment in self.grip_sequence.split(","):
            state, count = segment.split(":", 1)
            count = int(count)
            if cursor <= count:
                return state == "1"
            cursor -= count
        return self.default_grip

    def getControllerState(self, index):
        pressed = (1 << k_EButton_Grip) if self._grip_for_call() else 0
        return True, _ControllerState(pressed)


def init(application_type):
    return _FakeVRSystem()


def shutdown():
    return None
