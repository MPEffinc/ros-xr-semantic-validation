#!/usr/bin/env python3
"""Replay timestamp/pathology cases through Quest2ROS2's real pose callback.

ROS message classes and node services are intentionally minimal test doubles because
ROS 2 isn't available on this host.  The callback implementation itself is loaded
unchanged from the pinned upstream checkout.
"""

from __future__ import annotations

import argparse
from collections import deque
from dataclasses import dataclass, field
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import time
import types
from typing import Any

import numpy as np


EXPERIMENT = "quest2ros2_stale_restamp"


@dataclass
class TimeMsg:
    sec: int = 0
    nanosec: int = 0


@dataclass
class Header:
    stamp: TimeMsg = field(default_factory=TimeMsg)
    frame_id: str = ""


@dataclass
class Point:
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0


@dataclass
class Quaternion:
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    w: float = 0.0


@dataclass
class Pose:
    position: Point = field(default_factory=Point)
    orientation: Quaternion = field(default_factory=Quaternion)


@dataclass
class PoseStamped:
    header: Header = field(default_factory=Header)
    pose: Pose = field(default_factory=Pose)


@dataclass
class Transform:
    translation: Point = field(default_factory=Point)
    rotation: Quaternion = field(default_factory=Quaternion)


@dataclass
class TransformStamped:
    header: Header = field(default_factory=Header)
    child_frame_id: str = ""
    transform: Transform = field(default_factory=Transform)


@dataclass
class ColorRGBA:
    r: float = 0.0
    g: float = 0.0
    b: float = 0.0
    a: float = 0.0


class Marker:
    LINE_LIST = 5
    ADD = 0

    def __init__(self) -> None:
        self.header = Header()
        self.ns = ""
        self.id = 0
        self.type = 0
        self.action = 0
        self.pose = Pose()
        self.scale = types.SimpleNamespace(x=0.0, y=0.0, z=0.0)
        self.points: list[Point] = []
        self.colors: list[ColorRGBA] = []


class OVR2ROSInputs:
    def __init__(self) -> None:
        self.button_upper = False
        self.button_lower = False


class Logger:
    def info(self, _message: str) -> None:
        pass

    def warning(self, _message: str) -> None:
        pass

    warn = warning
    error = warning


class ClockNow:
    def __init__(self, stamp_ns: int) -> None:
        self.stamp_ns = stamp_ns

    def to_msg(self) -> TimeMsg:
        return ns_to_stamp(self.stamp_ns)


class Clock:
    def now(self) -> ClockNow:
        return ClockNow(time.time_ns())


class Node:
    def get_logger(self) -> Logger:
        return Logger()

    def get_clock(self) -> Clock:
        return Clock()


class Publisher:
    def __init__(self) -> None:
        self.messages: list[Any] = []

    def publish(self, message: Any) -> None:
        self.messages.append(message)


class GripperCommand:
    class Goal:
        def __init__(self) -> None:
            self.command = types.SimpleNamespace(position=0.0, max_effort=0.0)


def ns_to_stamp(stamp_ns: int) -> TimeMsg:
    return TimeMsg(sec=stamp_ns // 1_000_000_000, nanosec=stamp_ns % 1_000_000_000)


def stamp_to_ns(stamp: TimeMsg) -> int:
    return stamp.sec * 1_000_000_000 + stamp.nanosec


def quaternion_inverse(q: Any) -> np.ndarray:
    q_array = np.asarray(q, dtype=float)
    norm_squared = float(np.dot(q_array, q_array))
    return np.array([-q_array[0], -q_array[1], -q_array[2], q_array[3]]) / norm_squared


def quaternion_multiply(q1: Any, q2: Any) -> np.ndarray:
    x1, y1, z1, w1 = np.asarray(q1, dtype=float)
    x2, y2, z2, w2 = np.asarray(q2, dtype=float)
    return np.array(
        [
            w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2,
            w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2,
            w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2,
            w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2,
        ]
    )


def install_ros_stubs() -> None:
    rclpy = types.ModuleType("rclpy")
    rclpy.time = types.SimpleNamespace(Time=object)
    node_module = types.ModuleType("rclpy.node")
    node_module.Node = Node
    action_module = types.ModuleType("rclpy.action")
    action_module.ActionClient = object
    geometry_module = types.ModuleType("geometry_msgs.msg")
    for name, value in {
        "PoseStamped": PoseStamped,
        "Quaternion": Quaternion,
        "Pose": Pose,
        "TransformStamped": TransformStamped,
        "Point": Point,
    }.items():
        setattr(geometry_module, name, value)
    quest_module = types.ModuleType("quest2ros.msg")
    quest_module.OVR2ROSInputs = OVR2ROSInputs
    visualization_module = types.ModuleType("visualization_msgs.msg")
    visualization_module.Marker = Marker
    std_module = types.ModuleType("std_msgs.msg")
    std_module.ColorRGBA = ColorRGBA
    tf2_module = types.ModuleType("tf2_ros")
    tf2_module.TransformListener = object
    tf2_module.Buffer = object
    control_module = types.ModuleType("control_msgs.action")
    control_module.GripperCommand = GripperCommand
    transforms_module = types.ModuleType("tf_transformations")
    transforms_module.quaternion_inverse = quaternion_inverse
    transforms_module.quaternion_multiply = quaternion_multiply
    modules = {
        "rclpy": rclpy,
        "rclpy.node": node_module,
        "rclpy.action": action_module,
        "geometry_msgs": types.ModuleType("geometry_msgs"),
        "geometry_msgs.msg": geometry_module,
        "quest2ros": types.ModuleType("quest2ros"),
        "quest2ros.msg": quest_module,
        "visualization_msgs": types.ModuleType("visualization_msgs"),
        "visualization_msgs.msg": visualization_module,
        "std_msgs": types.ModuleType("std_msgs"),
        "std_msgs.msg": std_module,
        "tf2_ros": tf2_module,
        "control_msgs": types.ModuleType("control_msgs"),
        "control_msgs.action": control_module,
        "tf_transformations": transforms_module,
    }
    sys.modules.update(modules)


def load_controller(source: Path):
    install_ros_stubs()
    # This upstream repository tracks generated __pycache__ files.  Never let
    # the validation import mutate the pinned target checkout.
    sys.dont_write_bytecode = True
    spec = importlib.util.spec_from_file_location("q2r_actual_robot_arm_controller_base", source)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {source}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.BaseArmController


def make_controller(controller_class):
    controller = controller_class.__new__(controller_class)
    controller.arm_name = "right"
    controller.robot_name = "stubbed_robot_sink"
    controller.base_frame_id = "robot_base"
    controller.filter_window_size = 1
    controller.position_history = deque(maxlen=1)
    controller.orientation_history = deque(maxlen=1)
    controller.last_pose_stamped_always = None
    controller.initial_orientation = None
    controller.initial_position = None
    controller.first_received_quest_position = None
    controller.first_received_quest_orientation = None
    controller.current_robot_pose = None
    controller.allow_pose_update = True
    controller.marker_pub = Publisher()
    controller.target_pose_publisher = Publisher()
    controller._get_robot_current_pose = types.MethodType(
        lambda _self: ((0.4, -0.1, 0.3), Quaternion(w=1.0)), controller
    )
    return controller


def make_pose(stamp_ns: int, frame_id: str, x: float) -> PoseStamped:
    message = PoseStamped()
    message.header.stamp = ns_to_stamp(stamp_ns)
    message.header.frame_id = frame_id
    message.pose.position = Point(x=x, y=-0.2, z=0.5)
    message.pose.orientation = Quaternion(w=1.0)
    return message


def append_jsonl(path: Path, record: dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--target-root",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "targets" / "quest2ros2",
    )
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if args.output.exists():
        raise SystemExit(f"refusing to overwrite {args.output}")

    source = args.target_root / "q2r2_bringup" / "robot_arm_controller_base.py"
    commit = subprocess.check_output(
        ["git", "-C", str(args.target_root), "rev-parse", "HEAD"], text=True
    ).strip()
    controller_class = load_controller(source)
    controller = make_controller(controller_class)

    append_jsonl(
        args.output,
        {
            "experiment": EXPERIMENT,
            "trial": "setup",
            "monotonic_timestamp_ns": time.monotonic_ns(),
            "event": "provenance",
            "target_commit": commit,
            "callback_source": str(source.resolve()),
            "callback": "BaseArmController._pose_callback",
            "source_kind": "SYNTHETIC_POSESTAMPED",
            "ros_message_and_node_services": "TEST_DOUBLES",
            "ros_transport": "NOT_EXECUTED",
            "hardware_used": False,
        },
    )

    anchor_ns = time.time_ns()
    controller._pose_callback(make_pose(anchor_ns, "xr_anchor", 0.0))
    if controller.target_pose_publisher.messages:
        raise AssertionError("anchor unexpectedly published a target")

    trials = [
        ("age_10ms", 10_000_000, "xr_controller_A"),
        ("age_100ms", 100_000_000, "xr_controller_A"),
        ("age_500ms", 500_000_000, "xr_controller_A"),
        ("age_1s", 1_000_000_000, "xr_controller_A"),
        ("age_3s", 3_000_000_000, "xr_controller_B"),
        ("age_10s", 10_000_000_000, "old_reference_space"),
        ("future_1s", -1_000_000_000, "future_reference_space"),
    ]
    failures: list[str] = []
    for index, (trial, requested_age_ns, frame_id) in enumerate(trials, start=1):
        callback_start_ns = time.time_ns()
        source_stamp_ns = callback_start_ns - requested_age_ns
        before = len(controller.target_pose_publisher.messages)
        controller._pose_callback(make_pose(source_stamp_ns, frame_id, index * 0.01))
        callback_end_ns = time.time_ns()
        published = len(controller.target_pose_publisher.messages) == before + 1
        output = controller.target_pose_publisher.messages[-1] if published else None
        output_stamp_ns = stamp_to_ns(output.header.stamp) if output else None
        result = (
            published
            and output.header.frame_id == "robot_base"
            and output_stamp_ns != source_stamp_ns
            and abs(output_stamp_ns - callback_end_ns) < 100_000_000
        )
        if not result:
            failures.append(trial)
        append_jsonl(
            args.output,
            {
                "experiment": EXPERIMENT,
                "trial": trial,
                "monotonic_timestamp_ns": time.monotonic_ns(),
                "event": "callback_result",
                "source_generation": "synthetic_age_sweep_v1",
                "source_frame_id": frame_id,
                "source_stamp_ns": source_stamp_ns,
                "requested_age_ms": requested_age_ns / 1_000_000,
                "observed_age_at_callback_ms": (callback_start_ns - source_stamp_ns) / 1_000_000,
                "published": published,
                "output_frame_id": output.header.frame_id if output else None,
                "output_stamp_ns": output_stamp_ns,
                "output_minus_source_ms": (
                    (output_stamp_ns - source_stamp_ns) / 1_000_000 if output_stamp_ns else None
                ),
                "source_stamp_preserved": output_stamp_ns == source_stamp_ns if output else None,
                "source_frame_preserved": output.header.frame_id == frame_id if output else None,
                "freshness_guard_observed": False,
                "status": "PASS" if result else "FAIL",
                "evidence_level": "CONFIRMED_RUNTIME_SYNTHETIC_SOURCE",
            },
        )

    trajectory_start = len(controller.target_pose_publisher.messages)
    trajectory_source_ns = time.time_ns() - 3_000_000_000
    trajectory_outputs: list[dict[str, Any]] = []
    for sequence in range(5):
        source_stamp_ns = trajectory_source_ns + sequence * 20_000_000
        controller._pose_callback(make_pose(source_stamp_ns, "stale_trajectory_frame", 0.2 + sequence * 0.02))
        output = controller.target_pose_publisher.messages[-1]
        trajectory_outputs.append(
            {
                "sequence": sequence,
                "source_stamp_ns": source_stamp_ns,
                "output_stamp_ns": stamp_to_ns(output.header.stamp),
                "output_x": output.pose.position.x,
            }
        )
    trajectory_published = len(controller.target_pose_publisher.messages) - trajectory_start
    trajectory_result = trajectory_published == 5 and all(
        item["output_stamp_ns"] != item["source_stamp_ns"] for item in trajectory_outputs
    )
    if not trajectory_result:
        failures.append("stale_trajectory")
    append_jsonl(
        args.output,
        {
            "experiment": EXPERIMENT,
            "trial": "stale_trajectory_3s",
            "monotonic_timestamp_ns": time.monotonic_ns(),
            "event": "trajectory_result",
            "source_generation": "synthetic_stale_trajectory_v1",
            "source_frame_id": "stale_trajectory_frame",
            "published_count": trajectory_published,
            "outputs": trajectory_outputs,
            "freshness_guard_observed": False,
            "status": "PASS" if trajectory_result else "FAIL",
            "evidence_level": "CONFIRMED_RUNTIME_SYNTHETIC_SOURCE",
        },
    )

    status = "PASS" if not failures else "FAIL"
    append_jsonl(
        args.output,
        {
            "experiment": EXPERIMENT,
            "trial": "summary",
            "monotonic_timestamp_ns": time.monotonic_ns(),
            "event": "suite_result",
            "status": status,
            "failed_trials": failures,
            "callback_invoked": True,
            "actual_ros_transport": "BLOCKED_ENV",
            "hardware_requirement": "BLOCKED_HW",
            "claim_boundary": "Actual upstream callback with synthetic messages and ROS test doubles; no ROS graph, robot, Unity, or Quest execution.",
        },
    )
    print(json.dumps({"status": status, "output": str(args.output), "failed": failures}))
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
