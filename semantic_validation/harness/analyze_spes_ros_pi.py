#!/usr/bin/env python3
"""Correlate post-callback Spes adapter records with Pi observation records."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def records(path: Path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def key(stamp: dict) -> tuple[int, int]:
    return int(stamp["sec"]), int(stamp["nanosec"])


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--adapter", type=Path, required=True)
    parser.add_argument("--pi", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    adapter = records(args.adapter)
    pi = records(args.pi)
    pi_by_stamp = {key(item["header_stamp"]): item for item in pi if item.get("header_stamp")}
    matches, missing, mismatches = [], [], []
    for event in adapter:
        observed = pi_by_stamp.get(key(event["ros_header_stamp"]))
        if observed is None:
            missing.append(event["adapter_local_event_id"])
            continue
        expected = event["accepted_target"]
        actual = observed["position"]
        same = all(abs(float(expected[axis]) - float(actual[axis])) < 1e-9 for axis in ("x", "y", "z"))
        (matches if same else mismatches).append({
            "adapter_local_event_id": event["adapter_local_event_id"],
            "server_update_index": event["server_update_index"],
            "pi_receive_count": observed["receive_count_for_topic"],
            "ros_header_stamp": event["ros_header_stamp"],
        })
    result = {
        "classification": "E2_BOUNDARY_LIMITED_REPLAY",
        "consequence": "PI_RECEIVED",
        "adapter_events": len(adapter), "pi_records_total": len(pi),
        "matched": matches, "missing_adapter_event_ids": missing,
        "pose_mismatches": mismatches,
        "result": "PASS" if len(matches) == len(adapter) and not missing and not mismatches else "FAIL",
        "claim_limit": "Pi observation only; no native consumer or actuator evidence.",
    }
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, sort_keys=True))
    return 0 if result["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
