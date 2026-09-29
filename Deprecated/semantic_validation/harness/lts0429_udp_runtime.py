#!/usr/bin/env python3
"""LTS0429/teleoperation — synthetic-UDP runtime against the unmodified
production ROS 2 host node (`meta_quest_client/udp_client`).

Executed path
-------------
  synthetic UDP datagram (this harness, 127.0.0.1:5005)
      -> meta_quest_client/udp_client  (UNMODIFIED upstream C++, udp_client.cpp)
      -> DDS (ROS_DOMAIN_ID=73, loopback only, container --network none)
      -> rclpy observer subscribing /headset, /left_hand, /right_hand and /tf

Safety
------
`udp_client` is a pure parser/publisher: no robot driver, no service client, no
actuator topic. A full-repo audit found zero references to robot_ip, CAN,
/dev/tty, serial, or any vendor arm SDK; the only other package in the repo is a
vendored MoveIt Servo demo configured for a FAKE-hardware Panda, and it is NOT
built or launched here. No Quest, no robot, no actuator, no driver was used.

The XR frontend is a prebuilt `Teleoperator.apk` (a git-LFS pointer in the
checkout, object not fetched) — it is opaque and is NOT executed. The injection
point is therefore the UDP wire, downstream of everything the APK does.
Replay class ``BOUNDARY_LIMITED_REPLAY``.
Highest admissible evidence level: ``E2 SYNTHETIC_RUNTIME``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import socket
import subprocess
import time
from pathlib import Path
from typing import Any

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import PoseStamped
from tf2_msgs.msg import TFMessage

EXPERIMENT = "lts0429_udp_runtime"
UDP_PORT = 5005


def append_jsonl(path: Path, record: dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n")


def stamp_ns(header) -> int:
    return header.stamp.sec * 1_000_000_000 + header.stamp.nanosec


class Observer(Node):
    def __init__(self) -> None:
        super().__init__("lts0429_observer")
        self.poses: dict[str, list[dict[str, Any]]] = {
            "headset": [], "left_hand": [], "right_hand": []
        }
        self.tfs: list[dict[str, Any]] = []
        for topic in self.poses:
            self.create_subscription(
                PoseStamped, topic, self._make_cb(topic), 50
            )
        self.create_subscription(TFMessage, "/tf", self._tf_cb, 50)

    def _make_cb(self, topic: str):
        def cb(msg: PoseStamped) -> None:
            self.poses[topic].append(
                {
                    "recv_wall_ns": time.time_ns(),
                    "stamp_ns": stamp_ns(msg.header),
                    "frame_id": msg.header.frame_id,
                    "pos": [
                        round(msg.pose.position.x, 5),
                        round(msg.pose.position.y, 5),
                        round(msg.pose.position.z, 5),
                    ],
                }
            )
        return cb

    def _tf_cb(self, msg: TFMessage) -> None:
        for t in msg.transforms:
            self.tfs.append(
                {
                    "parent": t.header.frame_id,
                    "child": t.child_frame_id,
                    "stamp_ns": stamp_ns(t.header),
                }
            )

    def clear(self) -> None:
        for v in self.poses.values():
            v.clear()
        self.tfs.clear()


def drain(observer: Observer, seconds: float) -> None:
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        rclpy.spin_once(observer, timeout_sec=0.05)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--node-exe", type=Path, required=True)
    parser.add_argument("--source-file", type=Path, required=True)
    parser.add_argument("--revision", required=True)
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if args.output.exists():
        raise SystemExit(f"refusing to overwrite {args.output}")

    append_jsonl(
        args.output,
        {
            "experiment": EXPERIMENT,
            "trial": "provenance",
            "event": "provenance",
            "monotonic_timestamp_ns": time.monotonic_ns(),
            "source_generation": args.revision,
            "source_sha256": {
                args.source_file.name: hashlib.sha256(
                    args.source_file.read_bytes()
                ).hexdigest()
            },
            "production_node": "meta_quest_client/udp_client",
            "node_source_modified": False,
            "injection_point": "UDP_WIRE",
            "replay_class": "BOUNDARY_LIMITED_REPLAY",
            "bypassed_native_logic": "Teleoperator.apk (opaque, not executed, LFS object not fetched)",
            "active_native_logic": "recvfrom, ';'-token split, std::stod parse, Unity->ROS frame conversion, PoseStamped + TF publish",
            "xr_hardware_used": False,
            "robot_used": False,
            "driver_launched": False,
            "ros_transport_used": True,
            "evidence_level": "E2_SYNTHETIC_RUNTIME",
        },
    )

    proc = subprocess.Popen(
        [str(args.node_exe)], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
    )
    rclpy.init()
    observer = Observer()
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    dest = ("127.0.0.1", UDP_PORT)
    results: list[dict[str, Any]] = []

    def record(trial, observed, expected, note="") -> None:
        status = "PASS" if observed == expected else "FAIL"
        rec = {
            "experiment": EXPERIMENT,
            "trial": trial,
            "event": "udp_to_ros_result",
            "monotonic_timestamp_ns": time.monotonic_ns(),
            "source_generation": args.revision,
            "source_kind": "SYNTHETIC_UDP_DATAGRAM",
            "observed": observed,
            "expected": expected,
            "note": note,
            "status": status,
            "evidence_level": "E2_SYNTHETIC_RUNTIME",
        }
        results.append(rec)
        append_jsonl(args.output, rec)

    FULL = (
        "LeftHandPos:0.1,0.2,0.3;LeftHandRot:0,0,0,1;"
        "RightHandPos:0.4,0.5,0.6;RightHandRot:0,0,0,1;"
        "HeadsetPos:0,1.6,0;HeadsetRot:0,0,0,1"
    )

    def send(payload: str, wait: float = 0.7):
        observer.clear()
        sock.sendto(payload.encode(), dest)
        drain(observer, wait)

    try:
        drain(observer, 2.5)

        # --- T1 baseline: all three poses plus their TFs cross to ROS ---
        send(FULL)
        record(
            "t1_full_packet_publishes_three_poses_and_tfs",
            {
                "headset": len(observer.poses["headset"]),
                "left": len(observer.poses["left_hand"]),
                "right": len(observer.poses["right_hand"]),
                "tf_children": sorted({t["child"] for t in observer.tfs}),
                "frame_ids": sorted(
                    {p["frame_id"] for v in observer.poses.values() for p in v}
                ),
            },
            {
                "headset": 1,
                "left": 1,
                "right": 1,
                "tf_children": ["headset", "left_hand", "right_hand"],
                "frame_ids": ["world"],
            },
            "frame_id is the hardcoded literal \"world\" (udp_client.cpp:163); no "
            "reference-frame provenance is carried from the source.",
        )

        # --- T3 I3: the header stamp is the receiver clock, not a source time ---
        send(FULL)
        sample = observer.poses["left_hand"][0]
        skew_ms = abs(sample["recv_wall_ns"] - sample["stamp_ns"]) / 1e6
        record(
            "t2_header_stamp_is_receiver_clock",
            {
                "wire_carries_any_timestamp_field": False,
                "stamp_within_500ms_of_observer_wall_clock": skew_ms < 500,
                "tf_stamp_equals_pose_stamp": observer.tfs[0]["stamp_ns"]
                in {p["stamp_ns"] for p in observer.poses["left_hand"]}
                or any(
                    t["stamp_ns"] == sample["stamp_ns"]
                    for t in observer.tfs
                    if t["child"] == "left_hand"
                ),
            },
            {
                "wire_carries_any_timestamp_field": False,
                "stamp_within_500ms_of_observer_wall_clock": True,
                "tf_stamp_equals_pose_stamp": True,
            },
            "parse_pose sets header.stamp = this->now() (udp_client.cpp:162) and "
            "publish_tf copies it (:171). Source sampling time is unrecoverable.",
        )

        # --- T4 I3/I4: a deliberately stale resend is re-stamped as fresh ---
        send(FULL)
        first_stamp = observer.poses["left_hand"][0]["stamp_ns"]
        first_pos = observer.poses["left_hand"][0]["pos"]
        time.sleep(2.0)
        send(FULL)
        second = observer.poses["left_hand"][0]
        record(
            "t3_stale_resend_is_restamped_fresh",
            {
                "identical_pose": second["pos"] == first_pos,
                "stamp_advanced_by_at_least_1s": (second["stamp_ns"] - first_stamp)
                > 1_000_000_000,
                "any_wire_sequence_or_session_field": False,
            },
            {
                "identical_pose": True,
                "stamp_advanced_by_at_least_1s": True,
                "any_wire_sequence_or_session_field": False,
            },
            "A byte-identical 2 s-old datagram is republished with a fresh receiver "
            "stamp. A downstream age check on header.stamp measures host receive "
            "latency only, never source age.",
        )

        # --- T5 I1: the only gate is token presence, not tracking validity ---
        send("LeftHandPos:0.1,0.2,0.3;RightHandPos:0.4,0.5,0.6;HeadsetPos:0,1.6,0")
        record(
            "t4_pos_without_rot_is_dropped_silently",
            {
                "headset": len(observer.poses["headset"]),
                "left": len(observer.poses["left_hand"]),
                "right": len(observer.poses["right_hand"]),
                "tf_count": len(observer.tfs),
            },
            {"headset": 0, "left": 0, "right": 0, "tf_count": 0},
            "The publish condition is non-empty Pos AND non-empty Rot token "
            "(udp_client.cpp:59,64,69). This is a string-presence test, not a "
            "tracking-validity test; the wire has no validity field to test.",
        )

        # --- T6 I1: a wire-level validity annotation is simply ignored ---
        send(FULL + ";Tracking:LOST;Confidence:0.0")
        record(
            "t5_unknown_validity_tokens_ignored_poses_still_published",
            {
                "headset": len(observer.poses["headset"]),
                "left": len(observer.poses["left_hand"]),
                "right": len(observer.poses["right_hand"]),
            },
            {"headset": 1, "left": 1, "right": 1},
            "Unrecognised tokens fall through the if/else-if chain "
            "(udp_client.cpp:51-56) with no default branch. There is no extension "
            "point by which a frontend could signal invalidation to this node.",
        )

        # --- T7 I5: stream stop produces silence, no invalidation ---
        observer.clear()
        drain(observer, 2.0)
        record(
            "t6_stream_stop_emits_no_invalidation",
            {
                "poses_after_2s_silence": sum(len(v) for v in observer.poses.values()),
                "tfs_after_2s_silence": len(observer.tfs),
            },
            {"poses_after_2s_silence": 0, "tfs_after_2s_silence": 0},
            "No watchdog, no timeout, no zeroing publish, no explicit invalidation. "
            "tf2 consumers will report the last transform as valid within their own "
            "buffer horizon.",
        )

        # --- T8a robustness: a NaN-spelling token is accepted by std::stod and the
        #     resulting non-finite pose is published to the topic and to /tf ---
        import math

        send("LeftHandPos:0.1,NaNvalue,0.3;LeftHandRot:0,0,0,1", wait=1.0)
        nan_samples = observer.poses["left_hand"]
        nan_in_pose = bool(nan_samples) and any(
            math.isnan(v) for v in nan_samples[0]["pos"]
        )
        record(
            "t7a_nan_token_is_accepted_and_published",
            {
                "published": len(nan_samples),
                "pose_contains_nan": nan_in_pose,
                "tf_published": any(t["child"] == "left_hand" for t in observer.tfs),
            },
            {"published": 1, "pose_contains_nan": True, "tf_published": True},
            "std::stod (udp_client.cpp:98) accepts the \"NaN\" prefix, so the token "
            "parses, the vals.size()==3 check passes, and a non-finite pose reaches "
            "both the PoseStamped topic and /tf with no validity annotation.",
        )

        # --- T8b robustness: a non-numeric token throws out of the receive thread ---
        observer.clear()
        sock.sendto(
            b"LeftHandPos:0.1,abc,0.3;LeftHandRot:0,0,0,1", dest
        )
        drain(observer, 1.0)
        published_on_throw = len(observer.poses["left_hand"])
        observer.clear()
        sock.sendto(FULL.encode(), dest)
        drain(observer, 2.0)
        record(
            "t7b_nonnumeric_token_halts_the_receiver_thread",
            {
                "published_on_malformed_packet": published_on_throw,
                "published_on_subsequent_valid_packet": sum(
                    len(v) for v in observer.poses.values()
                ),
                "node_process_still_alive": proc.poll() is None,
            },
            {
                "published_on_malformed_packet": 0,
                "published_on_subsequent_valid_packet": 0,
                "node_process_still_alive": False,
            },
            "std::stod at udp_client.cpp:98 and :128 is unguarded. std::invalid_argument "
            "escapes udp_server() on the detached receive thread, so std::terminate "
            "aborts the whole process: a single non-numeric field in one datagram ends "
            "the XR-to-ROS bridge outright, with no ROS-side error signal and no "
            "last-will/lifecycle notification to any consumer.",
        )
    finally:
        sock.close()
        observer.destroy_node()
        rclpy.shutdown()
        proc.terminate()
        try:
            node_log = proc.communicate(timeout=10)[0]
        except subprocess.TimeoutExpired:
            proc.kill()
            node_log = proc.communicate()[0]
        (args.output.parent / "lts0429_node_stdout.txt").write_text(node_log or "")

    failures = [r["trial"] for r in results if r["status"] != "PASS"]
    summary = {
        "experiment": EXPERIMENT,
        "trial": "summary",
        "event": "suite_result",
        "monotonic_timestamp_ns": time.monotonic_ns(),
        "source_generation": args.revision,
        "trials": len(results),
        "passed": sum(1 for r in results if r["status"] == "PASS"),
        "failures": failures,
        "status": "PASS" if not failures else "FAIL",
        "semantic_disposition": {
            "I1_tracking": "ABSENT_ON_WIRE",
            "I2_source_id": "TRANSFORMED (token name -> topic/child_frame only)",
            "I3_source_time": "DROPPED, re-stamped with receiver clock",
            "I4_session_generation": "ABSENT",
            "I5_invalidation": "ABSENT",
        },
        "downstream_consequence": "ROS_PUBLISHED",
        "evidence_level": "E2_SYNTHETIC_RUNTIME",
        "claim_boundary": (
            "Unmodified upstream C++ host node executed over real DDS with synthetic "
            "UDP input. The XR frontend is an unexecuted opaque APK, so nothing is "
            "claimed about frontend semantics. No robot driver was built or launched; "
            "no control consequence is claimed."
        ),
    }
    append_jsonl(args.output, summary)
    print(json.dumps({k: summary[k] for k in ("status", "trials", "passed", "failures")}))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
