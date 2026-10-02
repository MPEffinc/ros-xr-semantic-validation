#!/usr/bin/env python3
"""Pre-flight observation (not an arm): replicate quest_teleop.py's per-tick reads at the app's own rate and log, for the
right-hand controller, bPoseIsValid, eTrackingResult and the grip bit on EVERY tick (also when the pose is invalid, which
the app itself never reads). Purpose: check whether pose-invalid/release detects each executed runtime deactivation, and
what grip reads on the first valid tick after reactivation (fresh-press race). Args: <out.jsonl> <dur_s>"""
import json, sys, time, openvr
vr = openvr.init(openvr.VRApplication_Background); out = open(sys.argv[1], 'w', buffering=1); t0 = time.time()
while time.time() - t0 < float(sys.argv[2]):
    poses = (openvr.TrackedDevicePose_t * openvr.k_unMaxTrackedDeviceCount)()
    vr.getDeviceToAbsoluteTrackingPose(openvr.TrackingUniverseRawAndUncalibrated, 0, poses)
    rec = {"wall": time.time(), "mono": time.monotonic(), "right": None}
    for i in range(openvr.k_unMaxTrackedDeviceCount):
        if vr.getTrackedDeviceClass(i) == openvr.TrackedDeviceClass_Controller and \
           vr.getControllerRoleForTrackedDeviceIndex(i) == openvr.TrackedControllerRole_RightHand:
            ok, st = vr.getControllerState(i); m = poses[i].mDeviceToAbsoluteTracking
            rec["right"] = {"i": i, "valid": bool(poses[i].bPoseIsValid), "res": int(poses[i].eTrackingResult), "ok": bool(ok),
                            "grip": bool(st.ulButtonPressed & (1 << openvr.k_EButton_Grip)), "x": m[0][3]}
    out.write(json.dumps(rec) + "\n")
openvr.shutdown()
