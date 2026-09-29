#!/usr/bin/env python3
"""Run NVIDIA's hardware-independent validity tests and release machine checks."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import types
from typing import Any


EXPERIMENT = "nvidia_positive_control"
LINKED_RELEASE = "465ce637120ac35404f5f741a9f25f3f1a1a25ea"


def append_jsonl(path: Path, record: dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n")


def git_output(root: Path, *arguments: str) -> str:
    return subprocess.check_output(["git", "-C", str(root), *arguments], text=True)


def git_show(root: Path, revision: str, relative_path: str) -> str:
    return git_output(root, "show", f"{revision}:{relative_path}")


class JsonRecorder:
    def __init__(self, output: Path, generation: str) -> None:
        self.output = output
        self.generation = generation
        self.outcomes: list[str] = []

    def pytest_runtest_logreport(self, report) -> None:
        if report.when != "call":
            return
        status = "PASS" if report.passed else "SKIP_ENV" if report.skipped else "FAIL"
        self.outcomes.append(status)
        append_jsonl(
            self.output,
            {
                "experiment": EXPERIMENT,
                "trial": report.nodeid,
                "monotonic_timestamp_ns": time.monotonic_ns(),
                "event": "upstream_test_result",
                "source_generation": self.generation,
                "source_kind": "SYNTHETIC_TEST_FIXTURE",
                "status": status,
                "duration_ms": report.duration * 1000.0,
                "failure": str(report.longrepr) if report.failed else None,
                "evidence_level": "CONFIRMED_RUNTIME_SYNTHETIC_SOURCE",
            },
        )


def install_package_roots(target_root: Path) -> None:
    """Bypass optional compiled root imports while loading pure-Python modules."""
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
    parser.add_argument(
        "--isaac-ros-root",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "targets" / "isaac_ros_teleop",
    )
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if args.output.exists():
        raise SystemExit(f"refusing to overwrite {args.output}")

    current_commit = git_output(args.target_root, "rev-parse", "HEAD").strip()
    ros_commit = git_output(args.isaac_ros_root, "rev-parse", "HEAD").strip()
    gitlink = git_output(args.isaac_ros_root, "ls-tree", "HEAD:isaac_teleop_core", "IsaacTeleop")
    gitlink_commit = gitlink.split()[2]
    if gitlink_commit != LINKED_RELEASE:
        raise AssertionError(f"unexpected IsaacTeleop gitlink {gitlink_commit}")

    tracker_path = "src/core/live_trackers/cpp/live_controller_tracker_impl.cpp"
    messages_path = "examples/teleop_ros2/python/messages.py"
    helpers_path = "examples/teleop_ros2/python/tensor_group_helpers.py"
    node_path = "examples/teleop_ros2/python/teleop_ros2_node.py"
    timestamp_path = "src/core/schema/fbs/timestamp.fbs"
    tracker = git_show(args.target_root, LINKED_RELEASE, tracker_path)
    messages = git_show(args.target_root, LINKED_RELEASE, messages_path)
    helpers = git_show(args.target_root, LINKED_RELEASE, helpers_path)
    node = git_show(args.target_root, LINKED_RELEASE, node_path)
    timestamp_schema = git_show(args.target_root, LINKED_RELEASE, timestamp_path)
    combined_control_path = "\n".join((tracker, messages, helpers, node))
    release_checks = {
        "inactive_controller_clears_snapshot": (
            "if (!get_pose_action_active" in tracker and "tracked.data.reset();" in tracker
        ),
        "locate_uses_position_and_orientation_valid_bits": (
            "XR_SPACE_LOCATION_POSITION_VALID_BIT" in tracker
            and "XR_SPACE_LOCATION_ORIENTATION_VALID_BIT" in tracker
        ),
        "tracked_vs_inferred_bits_not_preserved": (
            "XR_SPACE_LOCATION_POSITION_TRACKED_BIT" not in tracker
            and "XR_SPACE_LOCATION_ORIENTATION_TRACKED_BIT" not in tracker
        ),
        "internal_sample_timestamp_schema_exists": all(
            token in timestamp_schema
            for token in (
                "available_time_local_common_clock",
                "sample_time_local_common_clock",
                "sample_time_raw_device_clock",
            )
        ),
        "ros_aim_validity_gate_exists": "controller_aim_is_valid" in messages,
        "invalid_release_pose_uses_identity_substitution": (
            "msg.poses.append(to_pose([0.0, 0.0, 0.0]))" in messages
        ),
        "ros_timestamp_regenerated": (
            "now = self.get_clock().now().to_msg()" in node
            and "msg.header.stamp = now" in messages
        ),
        "source_age_guard_not_found": not any(
            token in combined_control_path.lower()
            for token in ("max_sample_age", "maximum_age", "freshness_threshold", "stale_sample")
        ),
    }
    for trial, passed in release_checks.items():
        append_jsonl(
            args.output,
            {
                "experiment": EXPERIMENT,
                "trial": f"linked_release::{trial}",
                "monotonic_timestamp_ns": time.monotonic_ns(),
                "event": "machine_check",
                "source_generation": LINKED_RELEASE,
                "isaac_ros_generation": ros_commit,
                "gitlink_verified": True,
                "status": "PASS" if passed else "FAIL",
                "evidence_level": "CONFIRMED_STATIC",
            },
        )

    source_files = [
        args.target_root / tracker_path,
        args.target_root / "tests/python/core/retargeting_engine/test_se3_retargeter_pose_validity.py",
        args.target_root / "tests/python/examples/teleop_ros2/test_hand_tracking_gate_retargeter.py",
    ]
    append_jsonl(
        args.output,
        {
            "experiment": EXPERIMENT,
            "trial": "runtime_setup",
            "monotonic_timestamp_ns": time.monotonic_ns(),
            "event": "provenance",
            "source_generation": current_commit,
            "linked_release_generation": LINKED_RELEASE,
            "source_hashes": {
                str(path.relative_to(args.target_root)): hashlib.sha256(path.read_bytes()).hexdigest()
                for path in source_files
            },
            "runtime_scope": "CURRENT_MAIN_PURE_PYTHON_SUBSET",
            "native_deviceio_loaded": False,
            "hardware_used": False,
        },
    )

    install_package_roots(args.target_root)
    os.environ["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
    import pytest

    test_paths = [
        args.target_root / "tests/python/core/retargeting_engine/test_se3_retargeter_pose_validity.py",
        args.target_root / "tests/python/examples/teleop_ros2/test_hand_tracking_gate_retargeter.py",
    ]
    recorder = JsonRecorder(args.output, current_commit)
    pytest_code = pytest.main(
        [str(path) for path in test_paths]
        + ["-q", "--tb=short", "-p", "no:cacheprovider"],
        plugins=[recorder],
    )
    expected_count = 10
    release_failures = [trial for trial, passed in release_checks.items() if not passed]
    runtime_failures = [status for status in recorder.outcomes if status != "PASS"]
    status = (
        "PASS"
        if pytest_code == 0
        and len(recorder.outcomes) == expected_count
        and not runtime_failures
        and not release_failures
        else "FAIL"
    )
    append_jsonl(
        args.output,
        {
            "experiment": EXPERIMENT,
            "trial": "summary",
            "monotonic_timestamp_ns": time.monotonic_ns(),
            "event": "suite_result",
            "source_generation": current_commit,
            "linked_release_generation": LINKED_RELEASE,
            "status": status,
            "pytest_exit_code": int(pytest_code),
            "tests_observed": len(recorder.outcomes),
            "tests_passed": recorder.outcomes.count("PASS"),
            "release_machine_check_failures": release_failures,
            "runtime_failures": runtime_failures,
            "hardware_result": "BLOCKED_HW",
            "claim_boundary": "Linked release gates are machine-checked static evidence. Runtime tests execute current-main pure-Python retargeters with synthetic fixtures; native OpenXR/DeviceIO and ROS transport are not run.",
        },
    )
    print(json.dumps({"status": status, "tests_passed": recorder.outcomes.count("PASS")}))
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
