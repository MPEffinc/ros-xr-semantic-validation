#!/usr/bin/env python3
"""Diagnostic (not the app): replicate quest_teleop.py's per-poll checks and print which one fails."""
import time, openvr
vr = openvr.init(openvr.VRApplication_Background)
t0 = time.time()
while time.time() - t0 < 12:
    poses = (openvr.TrackedDevicePose_t * openvr.k_unMaxTrackedDeviceCount)()
    vr.getDeviceToAbsoluteTrackingPose(openvr.TrackingUniverseRawAndUncalibrated, 0, poses)
    row = []
    for i in range(6):
        cls = vr.getTrackedDeviceClass(i)
        if cls == 0: continue
        role = vr.getControllerRoleForTrackedDeviceIndex(i)
        ok, st = vr.getControllerState(i)
        row.append(f"i{i} cls{cls} role{role} valid{int(poses[i].bPoseIsValid)} res{poses[i].eTrackingResult} ok{int(ok)} btn{st.ulButtonPressed:#x} grip{int(bool(st.ulButtonPressed & (1 << openvr.k_EButton_Grip)))} x{poses[i].mDeviceToAbsoluteTracking[0][3]:.3f}")
    print(f"{time.time()-t0:5.2f} " + " | ".join(row), flush=True)
    time.sleep(1.0)
openvr.shutdown()
