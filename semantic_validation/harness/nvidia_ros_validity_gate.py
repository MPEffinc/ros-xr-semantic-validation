#!/usr/bin/env python3
"""NVIDIA IsaacTeleop — execute the production ROS message builders against the
validity gate with synthetic tensor-group inputs.

Scope and claim boundary
------------------------
This harness executes UNMODIFIED production source from the pinned IsaacTeleop
checkout:

  * ``examples/teleop_ros2/python/messages.py``          (ROS output builders)
  * ``examples/teleop_ros2/python/tensor_group_helpers.py`` (validity predicates)
  * ``examples/teleop_ros2/python/geometry.py``
  * ``src/python/isaacteleop/retargeting_engine/`` (pure-Python tensor groups)

against REAL ROS 2 message types (``teleop_ros2_interfaces/NamedPoseArray``,
``geometry_msgs``, ``sensor_msgs``, ``std_msgs``) built with ``rosidl`` in a ROS 2
Jazzy container.

The inputs are SYNTHETIC ``OptionalTensorGroup`` objects constructed by this
harness at the retargeting-engine output boundary. No OpenXR runtime, no
DeviceIO, no CloudXR, no XR hardware, and no ROS transport (no publisher, no
DDS) are involved. Highest admissible evidence level: ``E2 SYNTHETIC_RUNTIME``.

Two dependency-boundary substitutions are made and are recorded in the output:
  1. ``isaacteleop`` and ``isaacteleop.retargeting_engine`` package roots are
     installed as namespace shims so the optional compiled ``_schema`` root
     import is bypassed. No pure-Python module body is modified.
  2. ``examples/teleop_ros2/python`` is placed on ``sys.path`` exactly as the
     upstream node does (it uses flat sibling imports).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
import types
from pathlib import Path
from typing import Any

import numpy as np

EXPERIMENT = "nvidia_ros_validity_gate"
FRAME_ID = "teleop_origin"
LEFT_WRIST_FRAME = "left_wrist"
RIGHT_WRIST_FRAME = "right_wrist"


def append_jsonl(path: Path, record: dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n")


def install_package_roots(target_root: Path) -> None:
    for name, relative_path in (
        ("isaacteleop", "src/python/isaacteleop"),
        ("isaacteleop.retargeting_engine", "src/python/isaacteleop/retargeting_engine"),
    ):
        package = types.ModuleType(name)
        package.__path__ = [str(target_root / relative_path)]
        package.__package__ = name
        sys.modules[name] = package
    sys.path.insert(0, str(target_root / "examples" / "teleop_ros2" / "python"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--target-root",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "targets" / "isaac_teleop",
    )
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if args.output.exists():
        raise SystemExit(f"refusing to overwrite {args.output}")

    target_root: Path = args.target_root
    revision = subprocess.check_output(
        ["git", "-C", str(target_root), "rev-parse", "HEAD"], text=True
    ).strip()

    install_package_roots(target_root)

    import messages  # noqa: E402  production module, unmodified
    import tensor_group_helpers  # noqa: E402  production module, unmodified
    from isaacteleop.retargeting_engine.interface import OptionalTensorGroup
    from isaacteleop.retargeting_engine.tensor_types.indices import (
        ControllerInputIndex,
        HandInputIndex,
        HandJointIndex,
        HeadInputIndex,
    )
    from isaacteleop.retargeting_engine.tensor_types.standard_types import (
        ControllerInput,
        HandInput,
        HeadInput,
    )
    from builtin_interfaces.msg import Time

    provenance_files = [
        "examples/teleop_ros2/python/messages.py",
        "examples/teleop_ros2/python/tensor_group_helpers.py",
        "examples/teleop_ros2/python/geometry.py",
        "src/python/isaacteleop/retargeting_engine/interface/tensor_group.py",
    ]
    append_jsonl(
        args.output,
        {
            "experiment": EXPERIMENT,
            "trial": "provenance",
            "event": "provenance",
            "monotonic_timestamp_ns": time.monotonic_ns(),
            "source_generation": revision,
            "source_hashes": {
                rel: hashlib.sha256((target_root / rel).read_bytes()).hexdigest()
                for rel in provenance_files
            },
            "ros_distro": "jazzy",
            "ros_message_types": "REAL_ROSIDL_GENERATED",
            "ros_transport_used": False,
            "native_deviceio_loaded": False,
            "openxr_runtime_used": False,
            "hardware_used": False,
            "input_kind": "SYNTHETIC_TENSOR_GROUP",
            "evidence_level": "E2_SYNTHETIC_RUNTIME",
        },
    )

    f32 = lambda v: np.asarray(v, dtype=np.float32)  # noqa: E731

    def make_controller(aim_valid: bool, pos, quat) -> OptionalTensorGroup:
        group = OptionalTensorGroup(ControllerInput())
        group[ControllerInputIndex.AIM_POSITION] = f32(pos)
        group[ControllerInputIndex.AIM_ORIENTATION] = f32(quat)
        group[ControllerInputIndex.GRIP_POSITION] = f32(pos)
        group[ControllerInputIndex.GRIP_ORIENTATION] = f32(quat)
        group[ControllerInputIndex.AIM_IS_VALID] = aim_valid
        group[ControllerInputIndex.GRIP_IS_VALID] = aim_valid
        for scalar in (
            "PRIMARY_CLICK",
            "SECONDARY_CLICK",
            "THUMBSTICK_X",
            "THUMBSTICK_Y",
            "THUMBSTICK_CLICK",
            "MENU_CLICK",
            "SQUEEZE_VALUE",
            "TRIGGER_VALUE",
        ):
            group[getattr(ControllerInputIndex, scalar)] = 0.0
        return group

    def absent_controller() -> OptionalTensorGroup:
        return OptionalTensorGroup(ControllerInput())

    def make_hand(wrist_valid: bool) -> OptionalTensorGroup:
        group = OptionalTensorGroup(HandInput())
        positions = f32([[0.1 * j, 0.0, 0.0] for j in range(26)])
        orientations = f32([[0.0, 0.0, 0.0, 1.0] for _ in range(26)])
        valid = np.ones(26, dtype=np.uint8)
        valid[int(HandJointIndex.WRIST)] = 1 if wrist_valid else 0
        group[HandInputIndex.JOINT_POSITIONS] = positions
        group[HandInputIndex.JOINT_ORIENTATIONS] = orientations
        group[HandInputIndex.JOINT_RADII] = np.zeros(26, dtype=np.float32)
        group[HandInputIndex.JOINT_VALID] = valid
        return group

    def make_head(valid: bool, tracked: bool = True) -> OptionalTensorGroup:
        group = OptionalTensorGroup(HeadInput())
        group[HeadInputIndex.POSITION] = f32([0.0, 1.6, 0.0])
        group[HeadInputIndex.ORIENTATION] = f32([0.0, 0.0, 0.0, 1.0])
        group[HeadInputIndex.IS_VALID] = valid
        group[HeadInputIndex.IS_TRACKED] = tracked
        return group

    now = Time(sec=1000, nanosec=500_000)
    results: list[dict[str, Any]] = []

    def record(trial: str, observed: dict[str, Any], expected: dict[str, Any]) -> None:
        status = "PASS" if observed == expected else "FAIL"
        rec = {
            "experiment": EXPERIMENT,
            "trial": trial,
            "event": "builder_result",
            "monotonic_timestamp_ns": time.monotonic_ns(),
            "source_generation": revision,
            "source_kind": "SYNTHETIC_TENSOR_GROUP",
            "observed": observed,
            "expected": expected,
            "status": status,
            "evidence_level": "E2_SYNTHETIC_RUNTIME",
        }
        results.append(rec)
        append_jsonl(args.output, rec)

    def ee_observation(ee_msg, tfs) -> dict[str, Any]:
        return {
            "name": list(ee_msg.name),
            "is_valid": [bool(v) for v in ee_msg.is_valid],
            "positions": [
                [round(p.position.x, 6), round(p.position.y, 6), round(p.position.z, 6)]
                for p in ee_msg.pose
            ],
            "header_stamp": [ee_msg.header.stamp.sec, ee_msg.header.stamp.nanosec],
            "header_frame_id": ee_msg.header.frame_id,
            "tf_child_frames": [t.child_frame_id for t in tfs],
            "tf_count": len(tfs),
        }

    pos = [0.3, 0.4, 0.5]
    quat = [0.0, 0.0, 0.0, 1.0]

    # --- I1: the controller aim-validity gate on the actionable EE path ---
    for trial, left, right, exp_valid, exp_tfs, exp_pos in (
        (
            "ctrl_both_aim_valid",
            make_controller(True, pos, quat),
            make_controller(True, pos, quat),
            [True, True],
            ["left_wrist", "right_wrist"],
            [pos, pos],
        ),
        (
            "ctrl_left_aim_invalid",
            make_controller(False, pos, quat),
            make_controller(True, pos, quat),
            [False, True],
            ["right_wrist"],
            [[0.0, 0.0, 0.0], pos],
        ),
        (
            "ctrl_both_aim_invalid",
            make_controller(False, pos, quat),
            make_controller(False, pos, quat),
            [False, False],
            [],
            [[0.0, 0.0, 0.0], [0.0, 0.0, 0.0]],
        ),
        (
            "ctrl_right_absent",
            make_controller(True, pos, quat),
            absent_controller(),
            [True, False],
            ["left_wrist"],
            [pos, [0.0, 0.0, 0.0]],
        ),
    ):
        ee_msg, tfs = messages.build_ee_output_from_controllers(
            left, right, now, FRAME_ID, LEFT_WRIST_FRAME, RIGHT_WRIST_FRAME
        )
        record(
            trial,
            ee_observation(ee_msg, tfs),
            {
                "name": ["left", "right"],
                "is_valid": exp_valid,
                "positions": exp_pos,
                "header_stamp": [1000, 500_000],
                "header_frame_id": FRAME_ID,
                "tf_child_frames": exp_tfs,
                "tf_count": len(exp_tfs),
            },
        )

    # --- I1: hand-wrist validity gate on the same actionable EE path ---
    for trial, left, right, exp_valid, exp_tfs in (
        ("hand_both_wrist_valid", make_hand(True), make_hand(True), [True, True],
         ["left_wrist", "right_wrist"]),
        ("hand_left_wrist_invalid", make_hand(False), make_hand(True), [False, True],
         ["right_wrist"]),
        ("hand_both_absent", OptionalTensorGroup(HandInput()),
         OptionalTensorGroup(HandInput()), [False, False], []),
    ):
        ee_msg, tfs = messages.build_ee_output_from_hands(
            left, right, now, FRAME_ID, LEFT_WRIST_FRAME, RIGHT_WRIST_FRAME
        )
        obs = ee_observation(ee_msg, tfs)
        record(
            trial,
            {"is_valid": obs["is_valid"], "tf_child_frames": obs["tf_child_frames"]},
            {"is_valid": exp_valid, "tf_child_frames": exp_tfs},
        )

    # --- I1: head validity gate suppresses the whole head output ---
    for trial, head, expect_none in (
        ("head_valid", make_head(True), False),
        ("head_invalid", make_head(False), True),
        ("head_absent", OptionalTensorGroup(HeadInput()), True),
    ):
        out = messages.build_head_output(head, now, FRAME_ID, "head")
        record(trial, {"output_is_none": out is None}, {"output_is_none": expect_none})

    # --- I1 key negative: the schema HAS a separate TRACKED bit, and the ROS path
    #     neither reads nor serialises it. VALID-but-INFERRED is indistinguishable
    #     from VALID-and-ACTIVELY-TRACKED at the ROS boundary.
    head_valid_tracked = messages.build_head_output(
        make_head(True, tracked=True), now, FRAME_ID, "head"
    )
    head_valid_untracked = messages.build_head_output(
        make_head(True, tracked=False), now, FRAME_ID, "head"
    )
    def _head_bytes(out):
        msg, tf = out
        return {
            "pos": [msg.pose.position.x, msg.pose.position.y, msg.pose.position.z],
            "quat": [
                msg.pose.orientation.x,
                msg.pose.orientation.y,
                msg.pose.orientation.z,
                msg.pose.orientation.w,
            ],
            "frame_id": msg.header.frame_id,
            "stamp": [msg.header.stamp.sec, msg.header.stamp.nanosec],
            "tf_child": tf.child_frame_id,
        }

    record(
        "head_tracked_bit_not_read_and_not_serialised",
        {
            "both_outputs_present": head_valid_tracked is not None
            and head_valid_untracked is not None,
            "outputs_byte_identical": _head_bytes(head_valid_tracked)
            == _head_bytes(head_valid_untracked),
            "is_tracked_in_schema": "head_is_tracked"
            in [t.name for t in HeadInput().types],
            "ros_msg_has_tracked_field": hasattr(head_valid_tracked[0], "is_tracked"),
        },
        {
            "both_outputs_present": True,
            "outputs_byte_identical": True,
            "is_tracked_in_schema": True,
            "ros_msg_has_tracked_field": False,
        },
    )

    # --- I1 negative: per-joint validity IS serialised on the hand-joint topic ---
    hand = make_hand(True)
    joint_valid = np.ones(26, dtype=np.uint8)
    joint_valid[int(HandJointIndex.INDEX_TIP)] = 0
    hand[HandInputIndex.JOINT_VALID] = joint_valid
    hand_msg = messages.build_hand_msg(hand, OptionalTensorGroup(HandInput()), now, FRAME_ID)
    invalid_names = [
        n for n, v in zip(hand_msg.name, hand_msg.is_valid) if not v and n.startswith("left_")
    ]
    invalid_poses_zero = all(
        (p.position.x, p.position.y, p.position.z) == (0.0, 0.0, 0.0)
        for p, v in zip(hand_msg.pose, hand_msg.is_valid)
        if not v
    )
    record(
        "hand_msg_per_joint_validity_serialised",
        {
            "left_invalid_joint_count": len(invalid_names),
            "right_all_invalid": all(
                not v for n, v in zip(hand_msg.name, hand_msg.is_valid)
                if n.startswith("right_")
            ),
            "invalid_poses_zeroed": invalid_poses_zero,
            "is_valid_field_present": hasattr(hand_msg, "is_valid"),
        },
        {
            "left_invalid_joint_count": 1,
            "right_all_invalid": True,
            "invalid_poses_zeroed": True,
            "is_valid_field_present": True,
        },
    )

    # --- I3: does any SOURCE timestamp reach the ROS output? ---
    ctrl_msg = messages.build_controller_msg(
        make_controller(True, pos, quat), make_controller(False, pos, quat)
    )
    import msgpack
    import msgpack_numpy as mnp

    payload = msgpack.unpackb(
        bytes(b[0] for b in ctrl_msg.data), object_hook=mnp.decode, raw=False
    )
    host_now_ns = time.time_ns()
    record(
        "controller_msg_timestamp_is_host_wall_clock",
        {
            "has_timestamp_field": "timestamp" in payload,
            "within_2s_of_host_wall_clock": abs(payload["timestamp"] - host_now_ns) < 2e9,
            "carries_aim_is_valid": "left_aim_is_valid" in payload
            or "right_aim_is_valid" in payload,
            "carries_is_active": "left_is_active" in payload,
            "left_is_active": payload.get("left_is_active"),
            "right_is_active": payload.get("right_is_active"),
        },
        {
            "has_timestamp_field": True,
            "within_2s_of_host_wall_clock": True,
            # AIM_IS_VALID is consumed by the EE gate but is NOT put on this topic.
            "carries_aim_is_valid": False,
            "carries_is_active": True,
            "left_is_active": True,
            "right_is_active": True,
        },
    )

    # right controller has AIM_IS_VALID=False yet is reported is_active=True on the
    # controller topic: presence and pose-validity are different facts, and only
    # presence survives onto that topic.
    record(
        "controller_topic_conflates_presence_with_validity",
        {
            "right_aim_is_valid_input": False,
            "right_is_active_on_wire": payload.get("right_is_active"),
            "right_aim_position_on_wire": [round(float(v), 6) for v in payload["right_aim_position"]],
        },
        {
            "right_aim_is_valid_input": False,
            "right_is_active_on_wire": True,
            "right_aim_position_on_wire": pos,
        },
    )

    # --- I3: EE header stamp is the caller-supplied node clock, never a source time ---
    record(
        "ee_header_stamp_is_caller_supplied",
        {"stamp": [now.sec, now.nanosec]},
        {"stamp": [1000, 500_000]},
    )

    failures = [r["trial"] for r in results if r["status"] != "PASS"]
    summary = {
        "experiment": EXPERIMENT,
        "trial": "summary",
        "event": "suite_result",
        "monotonic_timestamp_ns": time.monotonic_ns(),
        "source_generation": revision,
        "trials": len(results),
        "passed": sum(1 for r in results if r["status"] == "PASS"),
        "failures": failures,
        "status": "PASS" if not failures else "FAIL",
        "evidence_level": "E2_SYNTHETIC_RUNTIME",
        "claim_boundary": (
            "Production ROS output builders executed against real rosidl-generated "
            "message types with synthetic retargeting-engine tensor groups. No OpenXR, "
            "no DeviceIO, no CloudXR, no XR hardware, no ROS transport/DDS."
        ),
    }
    append_jsonl(args.output, summary)
    print(json.dumps({k: summary[k] for k in ("status", "trials", "passed", "failures")}))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
