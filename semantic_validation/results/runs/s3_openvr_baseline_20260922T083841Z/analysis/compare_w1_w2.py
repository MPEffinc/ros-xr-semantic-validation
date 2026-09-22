#!/usr/bin/env python3
"""Compare observed W1/W2 endpoints without assuming equal capture phase."""
import json
from pathlib import Path
import sys


def load(root, trial):
    return json.loads((Path(root) / trial / f"{trial}_downstream.json").read_text())


def max_keyed_difference(a, b):
    return max(abs(a[k] - b[k]) for k in a.keys() & b.keys())


def main():
    root = sys.argv[1]
    w1, w2 = load(root, "W1"), load(root, "W2")
    w1_first, w2_first = w1["joint_states"][0], w2["joint_states"][0]
    w1_last, w2_last = w1["joint_states"][-1], w2["joint_states"][-1]
    initial_1 = dict(zip(w1_first["name"], w1_first["position"]))
    initial_2 = dict(zip(w2_first["name"], w2_first["position"]))
    final_1 = dict(zip(w1_last["name"], w1_last["position"]))
    final_2 = dict(zip(w2_last["name"], w2_last["position"]))
    p1, p2 = w1["pose_target_cmds"], w2["pose_target_cmds"]
    result = {
        "capture_phase_note": "First captured production pose is not a common reference: capture began at different points in the 300-step fake motion.",
        "first_pose_z": {"W1": p1[0]["position"][2], "W2": p2[0]["position"][2]},
        "last_pose": {"W1": p1[-1], "W2": p2[-1]},
        "last_pose_position_max_abs_difference_m": max(abs(a-b) for a, b in zip(p1[-1]["position"], p2[-1]["position"])),
        "last_pose_orientation_max_abs_difference": max(abs(a-b) for a, b in zip(p1[-1]["orientation"], p2[-1]["orientation"])),
        "first_joint_state_max_abs_difference_rad": max_keyed_difference(initial_1, initial_2),
        "last_joint_state_max_abs_difference_rad": max_keyed_difference(final_1, final_2),
        "counts": {
            "W1": {"pose": len(p1), "trajectory": len(w1["arm_controller_joint_trajectory"]), "joint": len(w1["joint_states"])},
            "W2": {"pose": len(p2), "trajectory": len(w2["arm_controller_joint_trajectory"]), "joint": len(w2["joint_states"])},
        },
    }
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
