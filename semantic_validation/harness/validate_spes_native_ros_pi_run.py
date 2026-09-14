#!/usr/bin/env python3
"""Validate a completed pinned-Spes ROS-to-Pi run without replaying it.

Creates explicit trial IDs from the ordered WSS inputs and binds each one to
the upstream PoseStamped observed on the desktop and the byte-equivalent
PoseStamped observed on the Pi.  It refuses an output path that already exists.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def stamp(record: dict) -> tuple[int, int]:
    value = record["header_stamp"]
    return int(value["sec"]), int(value["nanosec"])


def same_pose(left: dict, right: dict) -> bool:
    return all(abs(float(left[k]) - float(right[k])) < 1e-12 for k in ("x", "y", "z"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--overwrite-refusal-rc", type=int, required=True)
    parser.add_argument("--desktop-container-count-after", type=int, required=True)
    parser.add_argument("--pi-sink-count-after", type=int, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit(f"refusing to overwrite {args.output}")

    summary = json.loads((args.run_dir / "summary.json").read_text())
    run_id = summary["run_id"]
    desktop = load_jsonl(args.run_dir / "desktop.jsonl")
    sent = [r for r in desktop if r["event"] == "wss_packet_sent"]
    observed = [r for r in desktop if r["event"] == "desktop_observed_publish"]
    pi = load_jsonl(args.run_dir / "pi_sink.jsonl")
    pi_by_stamp = {stamp(r): r for r in pi}

    trials = []
    for index, (source, publish) in enumerate(zip(sent, observed), 1):
        pi_record = pi_by_stamp.get(stamp(publish))
        trials.append({
            "run_id": run_id,
            "trial_id": f"{run_id}:packet-{index:03d}",
            "source_packet_index": source["wss_packet_index"],
            "synthetic_wss_position": source["position"],
            "upstream_ros_header_stamp": publish["header_stamp"],
            "upstream_ros_frame_id": publish["frame_id"],
            "upstream_ros_position": publish["position"],
            "pi_receive_count": pi_record.get("receive_count_for_topic") if pi_record else None,
            "pi_position": pi_record.get("position") if pi_record else None,
            "pi_accept_decision": pi_record.get("accept_decision") if pi_record else None,
            "desktop_pi_pose_equal": bool(pi_record and same_pose(publish["position"], pi_record["position"])),
        })

    checks = {
        "run_dir_matches_run_id": args.run_dir.name == run_id,
        "summary_pass": summary.get("status") == "PASS",
        "pinned_target_clean_before_after": bool(summary.get("target_clean_before") and summary.get("target_clean_after")),
        "production_publisher": summary.get("ros_publisher_provenance") == "PINNED_UPSTREAM teleop/ros2/__main__.py",
        "count_30_30_30": len(sent) == len(observed) == len(pi) == 30,
        "indices_ordered": [r["wss_packet_index"] for r in sent] == list(range(1, 31)),
        "desktop_stamps_unique": len({stamp(r) for r in observed}) == len(observed),
        "all_stamps_on_pi": all(stamp(r) in pi_by_stamp for r in observed),
        "all_desktop_pi_poses_equal": all(t["desktop_pi_pose_equal"] for t in trials),
        "all_frames_link_base": all(t["upstream_ros_frame_id"] == "link_base" for t in trials),
        "trial_ids_unique": len({t["trial_id"] for t in trials}) == len(trials),
        "overwrite_refused": args.overwrite_refusal_rc != 0,
        "desktop_container_clean_shutdown": args.desktop_container_count_after == 0,
        "pi_sink_clean_shutdown": args.pi_sink_count_after == 0,
        "no_xr_hardware": summary.get("xr_hardware_used") is False,
        "no_robot_or_driver": summary.get("robot_or_driver_used") is False,
    }
    result = {
        "run_id": run_id,
        "validation": "SPES_PINNED_UPSTREAM_ROS_DDS_PI",
        "checks": checks,
        "counts": {"wss_sent": len(sent), "desktop_ros_observed": len(observed), "pi_received": len(pi)},
        "trials": trials,
        "result": "PASS" if all(checks.values()) else "FAIL",
        "evidence_level": "E2_BOUNDARY_LIMITED_REPLAY",
        "consequence": "PI_RECEIVED",
        "claim_limit": "Synthetic post-browser input; Pi observation only; no Quest and no robot/driver/actuator.",
    }
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"run_id": run_id, "result": result["result"], "checks": checks}, sort_keys=True))
    return 0 if result["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
