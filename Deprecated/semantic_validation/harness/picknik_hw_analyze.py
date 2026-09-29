#!/usr/bin/env python3
"""Classify future PickNik Quest side-band and robot-free ROS observations.

This script does not create evidence by itself. Its result level depends on the
provenance of the two supplied logs; no hardware run is performed here.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


POSE_TRACKING_BITS = 1 | 2  # UnityEngine.XR.InputTrackingState Position | Rotation


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, 1):
            if not line.strip():
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_number}: invalid JSON: {exc}") from exc
    return records


def pose_valid(sample: dict[str, Any]) -> bool:
    return (
        bool(sample.get("input_present"))
        and bool(sample.get("game_object_present"))
        and bool(sample.get("is_tracked"))
        and (int(sample.get("tracking_state", 0)) & POSE_TRACKING_BITS) == POSE_TRACKING_BITS
    )


def source_stamp_ns(sample: dict[str, Any]) -> int:
    return int(sample["wall_unix_ms"]) * 1_000_000


def side_matches_ros(side: str, record: dict[str, Any]) -> bool:
    expected = f"{side}_controller_odom"
    return record.get("child_frame_id") == expected or record.get("topic") == f"/{expected}"


def find_loss_intervals(samples: list[dict[str, Any]]) -> list[dict[str, Any]]:
    intervals: list[dict[str, Any]] = []
    saw_valid = False
    active: dict[str, Any] | None = None
    for sample in samples:
        valid = pose_valid(sample)
        if valid:
            if active is not None:
                active["reacquired"] = sample
                intervals.append(active)
                active = None
            saw_valid = True
            continue
        if saw_valid and active is None:
            active = {"loss_start": sample, "loss_samples": []}
        if active is not None:
            active["loss_samples"].append(sample)
    if active is not None:
        active["reacquired"] = None
        intervals.append(active)
    return intervals


def analyze(sideband: list[dict[str, Any]], ros: list[dict[str, Any]]) -> dict[str, Any]:
    trials: list[dict[str, Any]] = []
    for side in ("left", "right"):
        samples = sorted(
            (
                record
                for record in sideband
                if record.get("event_type") == "raw_sample" and record.get("side") == side
            ),
            key=lambda record: (int(record.get("wall_unix_ms", 0)), int(record.get("unity_frame", 0))),
        )
        for interval in find_loss_intervals(samples):
            loss_samples = interval["loss_samples"]
            start_ns = source_stamp_ns(interval["loss_start"])
            last_loss_ns = source_stamp_ns(loss_samples[-1])
            reacquired = interval["reacquired"]
            recovery_ns = source_stamp_ns(reacquired) if reacquired is not None else None
            invalid_focus = any(
                not bool(sample.get("application_focused", True))
                or bool(sample.get("application_paused", False))
                or not bool(sample.get("xr_display_running", True))
                for sample in loss_samples
            )
            relevant_ros = [
                record
                for record in ros
                if side_matches_ros(side, record)
                and start_ns <= int(record.get("ros_stamp_ns", -1)) <= last_loss_ns
            ]
            odom = [record for record in relevant_ros if record.get("event_type") == "ros_receive_odometry"]
            tf = [record for record in relevant_ros if record.get("event_type") == "ros_receive_tf"]
            stamps = sorted({int(record["ros_stamp_ns"]) for record in relevant_ros})
            transforms = {
                tuple(record.get("position", [])) + tuple(record.get("orientation", []))
                for record in relevant_ros
            }
            if invalid_focus:
                classification = "INVALID_FOCUS_OR_XR_SESSION"
            elif len(odom) >= 2 and len(tf) >= 2 and len(stamps) >= 2:
                classification = "HW_PICKNIK_UNTRACKED_ROS_CONTINUES"
            elif len(odom) == 0 and len(tf) == 0:
                classification = "HW_PICKNIK_NO_DOWNSTREAM_DURING_LOSS"
            else:
                classification = "HW_PICKNIK_PARTIAL_DOWNSTREAM_OBSERVATION"
            trials.append(
                {
                    "side": side,
                    "loss_start_source_wall_ns": start_ns,
                    "last_loss_source_wall_ns": last_loss_ns,
                    "recovery_source_wall_ns": recovery_ns,
                    "loss_duration_ms": (last_loss_ns - start_ns) / 1_000_000.0,
                    "loss_sample_count": len(loss_samples),
                    "is_tracked_false_observed": any(not bool(sample.get("is_tracked")) for sample in loss_samples),
                    "pose_tracking_bits_missing_observed": any(
                        (int(sample.get("tracking_state", 0)) & POSE_TRACKING_BITS) != POSE_TRACKING_BITS
                        for sample in loss_samples
                    ),
                    "application_or_xr_invalid": invalid_focus,
                    "odom_during_loss": len(odom),
                    "tf_during_loss": len(tf),
                    "ros_stamp_progression_ns": stamps[-1] - stamps[0] if len(stamps) >= 2 else 0,
                    "distinct_ros_transforms": len(transforms),
                    "reacquired": reacquired is not None,
                    "classification": classification,
                }
            )
    return {
        "status": "PASS",
        "trial_count": len(trials),
        "trials": trials,
        "counts": {
            classification: sum(trial["classification"] == classification for trial in trials)
            for classification in sorted({trial["classification"] for trial in trials})
        },
        "overall": "HW_NO_LOSS_OBSERVED" if not trials else "OBSERVATIONS_CLASSIFIED",
        "evidence_level": "INPUT_PROVENANCE_REQUIRED",
        "claim_boundary": "Classifications are only hardware/runtime evidence if both input logs are demonstrated to come from the same actual Quest run and robot-free ROS endpoint. This analyzer was prepared but not run on hardware data in this phase.",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sideband", type=Path, required=True)
    parser.add_argument("--ros", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit(f"refusing to overwrite {args.output}")
    result = analyze(read_jsonl(args.sideband), read_jsonl(args.ros))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "overall": result["overall"], "trials": result["trial_count"], "output": str(args.output)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
