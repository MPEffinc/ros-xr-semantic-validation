#!/usr/bin/env python3
"""Machine-check the pinned PickNik Unity publisher's semantic boundaries."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import time
from typing import Any


EXPERIMENT = "picknik_unity_no_hw_validation"


def extract_method(text: str, signature_pattern: str) -> str:
    match = re.search(signature_pattern, text)
    if not match:
        raise AssertionError(f"method signature not found: {signature_pattern}")
    brace = text.find("{", match.end())
    if brace < 0:
        raise AssertionError("method body opener not found")
    depth = 0
    for index in range(brace, len(text)):
        if text[index] == "{":
            depth += 1
        elif text[index] == "}":
            depth -= 1
            if depth == 0:
                return text[match.start() : index + 1]
    raise AssertionError("unterminated method body")


def append_jsonl(path: Path, record: dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--target-root",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "targets" / "meta_quest_teleoperation",
    )
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if args.output.exists():
        raise SystemExit(f"refusing to overwrite {args.output}")

    source = args.target_root / "UnityProject" / "Assets" / "ROSPublishers.cs"
    version_file = args.target_root / "UnityProject" / "ProjectSettings" / "ProjectVersion.txt"
    source_text = source.read_text(encoding="utf-8")
    version_text = version_file.read_text(encoding="utf-8").strip()
    commit = subprocess.check_output(
        ["git", "-C", str(args.target_root), "rev-parse", "HEAD"], text=True
    ).strip()
    source_hash = hashlib.sha256(source.read_bytes()).hexdigest()

    update_method = extract_method(source_text, r"public\s+void\s+Update\s*\(\s*\)")
    publish_method = extract_method(
        source_text,
        r"private\s+void\s+PublishOdomAndTf\s*\(\s*Transform\s+sourceTransform\s*,\s*string\s+childFrame\s*,\s*string\s+odomTopicName\s*\)",
    )
    time_method = extract_method(source_text, r"private\s+static\s+TimeMsg\s+GetRosTime\s*\(\s*\)")

    tracking_tokens = [
        "isTracked",
        "trackingState",
        "TryGetFeatureValue",
        "InputTrackingState",
        "CommonUsages.isTracked",
    ]
    checks = {
        "left_and_right_use_same_publish_method": (
            "PublishOdomAndTf(leftController.transform, leftChildFrame, leftOdomTopicName);" in update_method
            and "PublishOdomAndTf(rightController.transform, rightChildFrame, rightOdomTopicName);" in update_method
        ),
        "pose_read_unconditionally_inside_method": "sourceTransform.GetPositionAndRotation" in publish_method,
        "publication_time_assigned": "_odomHeader.stamp = GetRosTime();" in publish_method,
        "wall_clock_used": "DateTime.UtcNow" in time_method,
        "odom_published": "ros.Publish(odomTopicName, _odomMsg);" in publish_method,
        "tf_published": "ros.Publish(tfTopicName, _tfMessage);" in publish_method,
        "tracking_state_not_an_argument": not any(token in publish_method for token in tracking_tokens),
        "tracking_state_not_queried_in_source": not any(token in source_text for token in tracking_tokens),
        "focus_loss_does_not_invalidate": "OnApplicationFocus" not in source_text,
        "reference_space_identity_not_encoded": (
            'frame_id = "quest"' in source_text and "sourceTransform" in publish_method
        ),
    }
    failures = [name for name, passed in checks.items() if not passed]
    for name, passed in checks.items():
        append_jsonl(
            args.output,
            {
                "experiment": EXPERIMENT,
                "trial": name,
                "monotonic_timestamp_ns": time.monotonic_ns(),
                "event": "machine_check",
                "source_generation": commit,
                "source_file": str(source.resolve()),
                "source_sha256": source_hash,
                "status": "PASS" if passed else "FAIL",
                "evidence_level": "CONFIRMED_STATIC_MACHINE_CHECKED",
            },
        )

    unity_binaries = {
        candidate: shutil.which(candidate)
        for candidate in ("Unity", "unity-editor", "unityhub")
    }
    test_sources = sorted(
        str(path.relative_to(args.target_root))
        for path in (args.target_root / "UnityProject" / "Assets").rglob("*.cs")
        if "test" in path.name.lower() or "test" in {part.lower() for part in path.parts}
    )
    append_jsonl(
        args.output,
        {
            "experiment": EXPERIMENT,
            "trial": "unity_runtime_availability",
            "monotonic_timestamp_ns": time.monotonic_ns(),
            "event": "environment_check",
            "source_generation": commit,
            "unity_version": version_text,
            "unity_binaries": unity_binaries,
            "repository_test_sources": test_sources,
            "status": "SKIP_ENV" if not any(unity_binaries.values()) else "UNKNOWN",
            "evidence_level": "ENVIRONMENT_OBSERVATION",
            "claim_boundary": "No Unity executable means no EditMode/PlayMode scene or Transform execution was performed.",
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
            "source_generation": commit,
            "status": status,
            "failed_checks": failures,
            "static_result": "CONFIRMED_STATIC_MACHINE_CHECKED" if status == "PASS" else "DISPROVED",
            "unity_runtime_result": "BLOCKED_ENV" if not any(unity_binaries.values()) else "UNKNOWN",
            "quest_runtime_result": "BLOCKED_HW",
            "claim_boundary": "Machine-checked source only; tracked, emulated, focus-loss, and reference-space counterfactuals were not executed in Unity or on Quest.",
        },
    )
    print(json.dumps({"status": status, "output": str(args.output), "failed": failures}))
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
