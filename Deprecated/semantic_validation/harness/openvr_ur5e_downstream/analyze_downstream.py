#!/usr/bin/env python3
"""Summarise the OpenVR UR5e downstream trials.

Reports, per trial, only what the recordings contain:
  * production ROS pose publications
  * MoveIt Servo status codes observed
  * Servo -> controller JointTrajectory commands
  * simulated joint excursion relative to the trial's own first sample

No claim about physical actuation is derived here; the joint values come from
the Gazebo simulation's /joint_states feedback.
"""
import json
import pathlib
import sys


def joint_excursion(samples):
    """Max |position - first_position| per joint name, over the trial."""
    if not samples:
        return {}, 0.0
    baseline = dict(zip(samples[0]["name"], samples[0]["position"]))
    worst = {name: 0.0 for name in baseline}
    for sample in samples:
        for name, value in zip(sample["name"], sample["position"]):
            if name in baseline:
                worst[name] = max(worst[name], abs(value - baseline[name]))
    return worst, max(worst.values()) if worst else 0.0


def max_abs_velocity(samples):
    peak = 0.0
    for sample in samples:
        for value in sample.get("velocity", []):
            peak = max(peak, abs(value))
    return peak


def main():
    root = pathlib.Path(sys.argv[1])
    summary = {}
    for path in sorted(root.glob("*_downstream.json")):
        trial = path.name.split("_downstream.json")[0]
        data = json.loads(path.read_text())
        joints = data["joint_states"]
        worst, worst_value = joint_excursion(joints)
        summary[trial] = {
            "pose_target_cmds_count": len(data["pose_target_cmds"]),
            "servo_status_codes": sorted({s["code"] for s in data["servo_status"]}),
            "servo_status_count": len(data["servo_status"]),
            "joint_trajectory_count": len(data["arm_controller_joint_trajectory"]),
            "joint_state_count": len(joints),
            "max_joint_excursion_rad": worst_value,
            "per_joint_excursion_rad": worst,
            "max_abs_joint_velocity_rad_s": max_abs_velocity(joints),
            "first_pose_target": data["pose_target_cmds"][0] if data["pose_target_cmds"] else None,
            "last_pose_target": data["pose_target_cmds"][-1] if data["pose_target_cmds"] else None,
        }
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
