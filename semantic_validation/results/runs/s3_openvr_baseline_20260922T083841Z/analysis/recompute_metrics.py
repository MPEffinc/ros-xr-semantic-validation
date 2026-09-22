#!/usr/bin/env python3
"""Independent JSON-only checks for S3 OpenVR downstream captures.

This intentionally does not import the historical analyzer.  It reports only
values contained in each capture and keeps capture-monotonic time distinct
from ROS header stamps.
"""
import json
import math
import sys
from pathlib import Path


def pose_span(poses):
    if not poses:
        return None
    xyz = list(zip(*(p["position"] for p in poses)))
    return {
        "first_position": poses[0]["position"],
        "last_position": poses[-1]["position"],
        "min_position": [min(axis) for axis in xyz],
        "max_position": [max(axis) for axis in xyz],
        "frame_ids": sorted({p["frame_id"] for p in poses}),
        "distinct_positions": len({tuple(p["position"]) for p in poses}),
    }


def joint_metrics(samples):
    if not samples:
        return {"count": 0, "max_excursion_rad": None, "max_abs_velocity_rad_s": None}
    base = dict(zip(samples[0]["name"], samples[0]["position"]))
    max_excursion = 0.0
    max_velocity = 0.0
    for sample in samples:
        for name, position in zip(sample["name"], sample["position"]):
            if name in base:
                max_excursion = max(max_excursion, abs(position - base[name]))
        max_velocity = max(max_velocity, *(abs(v) for v in sample.get("velocity", [])))
    return {
        "count": len(samples),
        "first_position": samples[0]["position"],
        "last_position": samples[-1]["position"],
        "max_excursion_rad": max_excursion,
        "max_abs_velocity_rad_s": max_velocity,
    }


def main():
    root = Path(sys.argv[1])
    result = {}
    for path in sorted(root.glob("W*/W*_downstream.json")):
        data = json.loads(path.read_text())
        poses = data["pose_target_cmds"]
        trajectories = data["arm_controller_joint_trajectory"]
        joints = data["joint_states"]
        result[path.parent.name] = {
            "pose_target_count": len(poses),
            "joint_trajectory_count": len(trajectories),
            "servo_status_count": len(data["servo_status"]),
            "joint_state": joint_metrics(joints),
            "pose_target": pose_span(poses),
            "trajectory_first_monotonic": trajectories[0]["monotonic"] if trajectories else None,
            "trajectory_last_monotonic": trajectories[-1]["monotonic"] if trajectories else None,
        }
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
