#!/usr/bin/env python3
"""ROS 2 evidence gate between the unmodified quest_teleop app and MoveIt Servo.

app --/p1/app_cmd--> gate --/servo_node/pose_target_cmds--> Servo
The gate reads evidence through its OWN OpenVR client (the same fake, time-scripted
source the app reads), polls at 100 Hz, and applies gate_core.Gate(DEFENSE).
Disarm = stop forwarding + /servo_node/pause_servo(True) (common stop);
arm = pause_servo(False) before forwarding resumes.
Under I_ALVR the gate may read only OpenVR API fields; I_FULL adds openvr.xr_evidence().
"""
import json
import os
import sys
import time

import rclpy
from geometry_msgs.msg import PoseStamped
from std_srvs.srv import SetBool

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import openvr  # noqa: E402  (fake, from PYTHONPATH/harness)
from gate_core import Gate, I_FULL  # noqa: E402


def main():
    defense = os.environ["P1_DEFENSE"]
    log = open(os.environ["P1_GATE_LOG"], "a", buffering=1)
    rclpy.init()
    node = rclpy.create_node("p1_evidence_gate")
    pub = node.create_publisher(PoseStamped, "/servo_node/pose_target_cmds", 10)
    pause = node.create_client(SetBool, "/servo_node/pause_servo")
    vr = openvr.init(openvr.VRApplication_Background)
    gate = Gate(defense)
    poses = (openvr.TrackedDevicePose_t * openvr.k_unMaxTrackedDeviceCount)()
    counts = {"forwarded": 0, "dropped": 0}

    def call_pause(flag):
        req = SetBool.Request()
        req.data = flag
        pause.call_async(req)
        log.write(json.dumps({"wall_ns": time.time_ns(), "event": "pause_servo", "data": flag}) + "\n")

    def poll():
        vr.getDeviceToAbsoluteTrackingPose(openvr.TrackingUniverseRawAndUncalibrated, 0, poses)
        p = poses[0]
        m = p.mDeviceToAbsoluteTracking
        _, st = vr.getControllerState(0)
        obs = {"t": openvr._scenario().now(), "valid": bool(p.bPoseIsValid),
               "grip": bool(st.ulButtonPressed & (1 << openvr.k_EButton_Grip)),
               "raw": [m[i][3] for i in range(3)], "R": [[m[i][j] for j in range(3)] for i in range(3)],
               "active": None, "epoch": None}
        if defense in I_FULL:
            ev = openvr.xr_evidence()
            obs["active"], obs["epoch"] = ev["active"], ev["epoch"]
        armed, reason = gate.step(obs)
        if reason:
            log.write(json.dumps({"wall_ns": time.time_ns(), "t": obs["t"], "event": "state",
                                  "armed": armed, "reason": reason}) + "\n")
            call_pause(not armed)

    def on_cmd(msg):
        if gate.armed:
            pub.publish(msg)
            counts["forwarded"] += 1
        else:
            counts["dropped"] += 1

    node.create_subscription(PoseStamped, "/p1/app_cmd", on_cmd, 10)
    node.create_timer(0.01, poll)
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, rclpy.executors.ExternalShutdownException):
        pass
    finally:
        log.write(json.dumps({"wall_ns": time.time_ns(), "event": "final", **counts}) + "\n")


if __name__ == "__main__":
    main()
