"""Time-scripted fake of the OpenVR API surface used by quest_teleop.py.

Injected through PYTHONPATH; the pinned quest_teleop.py is not modified.
Every process that imports this module (the production app, an evidence gate)
sees the SAME scripted state, because state is a pure function of wall-clock
time since P1_T0_NS.  This emulates a SteamVR/ALVR source on the ROS side
only. It does not reproduce a real runtime or headset transition.

Scenario JSON (env P1_SCENARIO):
  hand_velocity: [[t0, t1, [vx, vy, vz]], ...]   hand motion in the pre-recenter raw frame (m/s)
  invalid:       [[t0, t1], ...]                 bPoseIsValid == False   (ALVR: any missing motion)
  grip_reported: [[t0, t1], ...]                 grip level SteamVR reports (may be cached)
  grip_truth:    [[t0, t1], ...]                 operator's physical grip (oracle only)
  inactive:      [[t0, t1], ...]                 OpenXR action inactive / focus lost (I_FULL only)
  recenters:     [{"t": s, "d": [x, y, z], "yaw_deg": a}, ...]  driver-frame change at t

Standard API fields reproduce what the ALVR path delivers (I_ALVR):
  bPoseIsValid, bDeviceIsConnected == bPoseIsValid, eTrackingResult == Running_OK when valid.
xr_evidence() is NOT part of OpenVR. It models evidence a middleware COULD forward
(I_FULL: action activity, recenter epoch + change time + transform).
"""
import ctypes
import json
import math
import os
import time

VRApplication_Background = 3
TrackingUniverseRawAndUncalibrated = 2
k_unMaxTrackedDeviceCount = 4
TrackedDeviceClass_Controller = 2
TrackedControllerRole_RightHand = 2
k_EButton_Grip = 2
TrackingResult_Uninitialized = 1
TrackingResult_Running_OK = 200


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


class _State:
    def __init__(self, pressed):
        self.ulButtonPressed = pressed


def _inside(intervals, t):
    return any(a <= t < b for a, b in intervals)


def _yaw(deg):
    """Rotation about the raw-frame vertical axis (OpenVR raw frame is Y-up)."""
    a = math.radians(deg)
    c, s = math.cos(a), math.sin(a)
    return [[c, 0.0, s], [0.0, 1.0, 0.0], [-s, 0.0, c]]


def _mm(a, b):
    return [[sum(a[i][k] * b[k][j] for k in range(3)) for j in range(3)] for i in range(3)]


def _mv(a, v):
    return [sum(a[i][k] * v[k] for k in range(3)) for i in range(3)]


class Scenario:
    def __init__(self, path, t0_ns):
        with open(path) as f:
            self.s = json.load(f)
        self.t0_ns = t0_ns
        self.h0 = self.s.get("hand_origin", [1.0, 1.2, -0.3])

    def now(self):
        return (time.time_ns() - self.t0_ns) / 1e9

    def hand(self, t):
        p = list(self.h0)
        for a, b, v in self.s.get("hand_velocity", []):
            dt = max(0.0, min(t, b) - a)
            for i in range(3):
                p[i] += v[i] * dt
        return p

    def frame(self, t):
        """Cumulative driver-frame transform (R, d) in effect at time t."""
        R = [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]
        d = [0.0, 0.0, 0.0]
        epoch, change_time = 0, None
        for ev in sorted(self.s.get("recenters", []), key=lambda e: e["t"]):
            if ev["t"] <= t:
                Ry = _yaw(ev.get("yaw_deg", 0.0))
                R = _mm(Ry, R)
                d = [x + y for x, y in zip(_mv(Ry, d), ev.get("d", [0, 0, 0]))]
                epoch += 1
                change_time = ev["t"]
        return R, d, epoch, change_time

    def raw_pose(self, t):
        R, d, _, _ = self.frame(t)
        p = [x + y for x, y in zip(_mv(R, self.hand(t)), d)]
        return R, p

    def valid(self, t):
        return not _inside(self.s.get("invalid", []), t)

    def grip_reported(self, t):
        return _inside(self.s.get("grip_reported", []), t)

    def grip_truth(self, t):
        return _inside(self.s.get("grip_truth", self.s.get("grip_reported", [])), t)

    def active(self, t):
        return not _inside(self.s.get("inactive", []), t)


_SCEN = None
_LOG = None


def _scenario():
    global _SCEN, _LOG
    if _SCEN is None:
        _SCEN = Scenario(os.environ["P1_SCENARIO"], int(os.environ["P1_T0_NS"]))
        log = os.environ.get("P1_OPENVR_LOG")
        _LOG = open(log, "a", buffering=1) if log else None
    return _SCEN


class _VRSystem:
    def __init__(self):
        self.sc = _scenario()

    def getDeviceToAbsoluteTrackingPose(self, universe, predicted, poses):
        t = self.sc.now()
        valid = self.sc.valid(t)
        R, p = self.sc.raw_pose(t)
        pose = poses[0]
        pose.bPoseIsValid = valid
        pose.bDeviceIsConnected = valid
        pose.eTrackingResult = TrackingResult_Running_OK if valid else TrackingResult_Uninitialized
        m = pose.mDeviceToAbsoluteTracking
        for i in range(3):
            for j in range(3):
                m[i][j] = R[i][j]
            m[i][3] = p[i]
        if _LOG:
            _LOG.write(json.dumps({"wall_ns": time.time_ns(), "t": t, "pid": os.getpid(), "valid": valid,
                                   "grip": self.sc.grip_reported(t), "raw": p}) + "\n")

    def getTrackedDeviceClass(self, index):
        return TrackedDeviceClass_Controller if index == 0 else 0

    def getControllerRoleForTrackedDeviceIndex(self, index):
        return TrackedControllerRole_RightHand if index == 0 else 0

    def getControllerState(self, index):
        pressed = (1 << k_EButton_Grip) if self.sc.grip_reported(self.sc.now()) else 0
        return True, _State(pressed)


def init(app_type):
    return _VRSystem()


def shutdown():
    pass


def xr_evidence():
    """I_FULL side channel (NOT OpenVR): what a middleware could forward."""
    sc = _scenario()
    t = sc.now()
    R, d, epoch, change_time = sc.frame(t)
    return {"t": t, "active": sc.active(t), "epoch": epoch, "change_time": change_time, "R": R, "d": d}
