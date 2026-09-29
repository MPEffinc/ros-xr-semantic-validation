#!/usr/bin/env python3
"""Analyze a PickNik ROS-TCP transport-backend run.

Joins the harness client JSONL (what was pushed onto the ROS-TCP socket, with
harness-side tracking ground truth) against the picknik_ros_observer JSONL
(what actually arrived on ROS 2 topics), per topic, in order.

Scope reminder: this measures the TRANSPORT BACKEND (ros_tcp_endpoint), not
PickNik's C# publisher. See picknik_rostcp_synthetic_client.py.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any


def load(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--client", type=Path, required=True)
    ap.add_argument("--ros", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()

    client = [r for r in load(args.client) if r["event_type"] == "rostcp_publish_sent"]
    ros = load(args.ros)
    odom_rx = defaultdict(list)
    tf_rx = defaultdict(list)
    for r in ros:
        if r["event_type"] == "ros_receive_odometry":
            odom_rx[r["topic"]].append(r)
        elif r["event_type"] == "ros_receive_tf":
            tf_rx[r["child_frame_id"]].append(r)

    sent_by_topic = defaultdict(list)
    for r in client:
        sent_by_topic[r["odom_topic"]].append(r)

    result: dict[str, Any] = {
        "pinned_revision": "bbaef0762fdb0b429b8ea12a4ca65040748b41dd",
        "evidence_level": "E2 SYNTHETIC_RUNTIME",
        "replay_subclass": "BOUNDARY_LIMITED_REPLAY",
        "scope": "TRANSPORT_BACKEND_ONLY: ros_tcp_endpoint executed; PickNik C# RosPublishers NOT executed",
        "delivery": {},
        "per_phase": {},
        "semantic_checks": {},
    }

    for topic, sent in sent_by_topic.items():
        rx = odom_rx.get(topic, [])
        result["delivery"][topic] = {
            "sent": len(sent),
            "received": len(rx),
            "loss": len(sent) - len(rx),
        }
    total_tf_sent = len(client)  # one TF message per side per tick
    total_tf_rx = sum(len(v) for v in tf_rx.values())
    result["delivery"]["/tf"] = {
        "sent": total_tf_sent,
        "received": total_tf_rx,
        "loss": total_tf_sent - total_tf_rx,
    }

    # --- per-phase behaviour, joined in order per topic ---
    for topic, sent in sent_by_topic.items():
        rx = odom_rx.get(topic, [])
        n = min(len(sent), len(rx))
        phases: dict[str, Any] = {}
        for i in range(n):
            s, r = sent[i], rx[i]
            ph = s["phase"]
            p = phases.setdefault(
                ph,
                {
                    "sent": 0,
                    "received": 0,
                    "harness_is_tracked": s["harness_ground_truth"]["is_tracked"],
                    "harness_tracking_state": s["harness_ground_truth"]["tracking_state"],
                    "distinct_received_positions": set(),
                    "ros_stamps": [],
                    "received_frame_ids": set(),
                    "received_child_frame_ids": set(),
                    "digests": set(),
                },
            )
            p["sent"] += 1
            p["received"] += 1
            p["distinct_received_positions"].add(tuple(round(v, 6) for v in r["position"]))
            p["ros_stamps"].append(r["ros_stamp_ns"])
            p["received_frame_ids"].add(r["frame_id"])
            p["received_child_frame_ids"].add(r["child_frame_id"])
            p["digests"].add(s["odom_digest_stamp_zeroed"])
        out = {}
        for ph, p in phases.items():
            stamps = p["ros_stamps"]
            out[ph] = {
                "sent": p["sent"],
                "received": p["received"],
                "harness_is_tracked": p["harness_is_tracked"],
                "harness_tracking_state": p["harness_tracking_state"],
                "distinct_received_positions": len(p["distinct_received_positions"]),
                "distinct_payload_digests_stamp_zeroed": len(p["digests"]),
                "ros_stamp_monotonic_progressing": all(
                    stamps[i] <= stamps[i + 1] for i in range(len(stamps) - 1)
                ),
                "ros_stamp_span_ns": (max(stamps) - min(stamps)) if stamps else None,
                "received_frame_ids": sorted(p["received_frame_ids"]),
                "received_child_frame_ids": sorted(p["received_child_frame_ids"]),
            }
        result["per_phase"][topic] = out

    # --- semantic checks on what actually arrived ---
    odom_fields = set()
    for r in ros:
        if r["event_type"] in ("ros_receive_odometry", "ros_receive_tf"):
            odom_fields |= set(r.keys())
    result["semantic_checks"]["tracking_field_present_in_received_records"] = any(
        k in odom_fields for k in ("is_tracked", "tracking_state", "isTracked", "trackingState")
    )

    # Payload collision: a tracked sample and an untracked sample that carry the
    # same pose serialize to the same bytes once the stamp is removed.
    by_digest = defaultdict(set)
    for s in client:
        by_digest[s["odom_digest_stamp_zeroed"]].add(
            (s["harness_ground_truth"]["is_tracked"], s["side"])
        )
    collisions = {
        d: sorted(str(v) for v in vals) for d, vals in by_digest.items() if len({v[0] for v in vals}) > 1
    }
    result["semantic_checks"]["payload_digests_shared_between_tracked_and_untracked"] = len(
        collisions
    )

    # Continuation during the loss interval, per topic.
    cont = {}
    for topic, per in result["per_phase"].items():
        lost = per.get("TRACKING_LOST_FROZEN")
        if lost:
            cont[topic] = {
                "received_during_loss": lost["received"],
                "ros_stamp_kept_progressing": lost["ros_stamp_monotonic_progressing"],
                "ros_stamp_span_ns": lost["ros_stamp_span_ns"],
                "distinct_positions_during_loss": lost["distinct_received_positions"],
            }
    result["semantic_checks"]["continuation_during_harness_tracking_loss"] = cont

    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
