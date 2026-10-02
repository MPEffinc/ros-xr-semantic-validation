"""TEST-ONLY fake of the OpenVR surface used by quest_teleop.py: replays a tick trace (env M39_FAKE_TRACE, JSON lines
{"t": s after P1_T0_NS, "valid": bool, "grip": bool, "p": [x,y,z], "q": [x,y,z,w]}). getDeviceToAbsoluteTrackingPose
blocks to the next 50 ms tick (the xrizer v3 pump rate) and returns the latest trace row at or before now."""
import bisect, ctypes, json, os, time
from scipy.spatial.transform import Rotation as _R
VRApplication_Background = 3; TrackingUniverseRawAndUncalibrated = 2; k_unMaxTrackedDeviceCount = 4
TrackedDeviceClass_Controller = 2; TrackedControllerRole_RightHand = 2; k_EButton_Grip = 2
class OpenVRError(Exception): pass
class HmdMatrix34_t(ctypes.Structure):
    _fields_ = [("m", (ctypes.c_float * 4) * 3)]
    def __getitem__(self, i): return self.m[i]
class TrackedDevicePose_t(ctypes.Structure):
    _fields_ = [("mDeviceToAbsoluteTracking", HmdMatrix34_t), ("vVelocity", ctypes.c_float * 3), ("vAngularVelocity", ctypes.c_float * 3),
                ("eTrackingResult", ctypes.c_int), ("bPoseIsValid", ctypes.c_bool), ("bDeviceIsConnected", ctypes.c_bool)]
class _St:
    def __init__(self, b): self.ulButtonPressed = b
class _VR:
    def __init__(self):
        self.rows = [json.loads(l) for l in open(os.environ["M39_FAKE_TRACE"])]; self.ts = [r["t"] for r in self.rows]
        self.t0 = int(os.environ["P1_T0_NS"]) / 1e9; self.cur = self.rows[0]
    def _row(self):
        i = bisect.bisect_right(self.ts, time.time() - self.t0) - 1
        return self.rows[max(i, 0)]
    def getDeviceToAbsoluteTrackingPose(self, origin, pred, poses):
        now = time.time(); time.sleep(0.05 - (now % 0.05))
        r = self.cur = self._row(); p = poses[1]
        p.bPoseIsValid = r["valid"]; p.eTrackingResult = 200 if r["valid"] else 201; p.bDeviceIsConnected = True
        M = _R.from_quat(r.get("q", [0, 0, 0, 1])).as_matrix(); pos = r.get("p", [0.2, 1.0, -0.3])
        for i in range(3):
            for j in range(3): p.mDeviceToAbsoluteTracking.m[i][j] = M[i][j]
            p.mDeviceToAbsoluteTracking.m[i][3] = pos[i]
    def getTrackedDeviceClass(self, i): return TrackedDeviceClass_Controller if i in (1, 2) else 0
    def getControllerRoleForTrackedDeviceIndex(self, i): return {1: TrackedControllerRole_RightHand, 2: 1}.get(i, 0)
    def getControllerState(self, i):
        g = self.cur["grip"] if (i == 1 and self.cur["valid"]) else False   # probe: grip reads false while invalid
        return True, _St((1 << k_EButton_Grip) if g else 0)
def init(kind): return _VR()
def shutdown(): pass
