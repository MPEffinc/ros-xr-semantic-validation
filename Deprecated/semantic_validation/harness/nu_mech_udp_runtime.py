#!/usr/bin/env python3
"""NU-MECH vr-hand-tracking — synthetic-UDP runtime against the unmodified
production ROS 2 node.

Executed path
-------------
  synthetic UDP datagram (this harness)
      -> hand_tracking_quest/hand_tracker_quest_node   (UNMODIFIED upstream C++,
         HandTrackerQuest.cpp: recvfrom -> parseJointAngles regex -> publish)
      -> DDS (rmw, ROS_DOMAIN_ID=73, loopback only, container --network none)
      -> rclpy observer in this harness, subscribing /hand_joint_angles

The Unity/Meta Oculus Interaction frontend is NOT executed. The upstream
`IsTrackedDataValid` gate lives in that frontend and is therefore upstream of
this injection point: this is a ``BOUNDARY_LIMITED_REPLAY``-class injection and
may only support claims about behaviour AT AND AFTER the UDP wire.

Highest admissible evidence level: ``E2 SYNTHETIC_RUNTIME``.
No Quest, no robot, no actuator, no driver. The upstream repo contains no robot
consumer at all; its only in-repo consumer is a Qt visualiser.
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
from std_msgs.msg import Float32MultiArray

EXPERIMENT = "nu_mech_udp_runtime"
UDP_PORT = 9000
TOPIC = "hand_joint_angles"


def append_jsonl(path: Path, record: dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n")


class Observer(Node):
    def __init__(self) -> None:
        super().__init__("nu_mech_observer")
        self.received: list[dict[str, Any]] = []
        self.create_subscription(Float32MultiArray, TOPIC, self._cb, 50)

    def _cb(self, msg: Float32MultiArray) -> None:
        self.received.append(
            {
                "recv_monotonic_ns": time.monotonic_ns(),
                "data": [round(float(v), 4) for v in msg.data],
                "len": len(msg.data),
                # std_msgs/Float32MultiArray has no Header at all.
                "has_header": hasattr(msg, "header"),
                "layout_dim": len(msg.layout.dim),
            }
        )


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
            "production_node": "hand_tracking_quest/hand_tracker_quest_node",
            "node_source_modified": False,
            "injection_point": "UDP_WIRE",
            "replay_class": "BOUNDARY_LIMITED_REPLAY",
            "bypassed_native_logic": "Unity IHand.WhenHandUpdated + IsTrackedDataValid gate",
            "active_native_logic": "UDP recvfrom, parseJointAngles regex, Float32MultiArray publish",
            "xr_hardware_used": False,
            "robot_used": False,
            "ros_transport_used": True,
            "evidence_level": "E2_SYNTHETIC_RUNTIME",
        },
    )

    proc = subprocess.Popen(
        [str(args.node_exe)],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    rclpy.init()
    observer = Observer()
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    dest = ("127.0.0.1", UDP_PORT)
    results: list[dict[str, Any]] = []

    def record(trial: str, observed: dict[str, Any], expected: dict[str, Any],
               note: str = "") -> None:
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

    def send_and_collect(payload: str, wait: float = 0.6) -> list[dict[str, Any]]:
        observer.received.clear()
        sock.sendto(payload.encode(), dest)
        drain(observer, wait)
        return list(observer.received)

    try:
        # let the node bind its socket and the DDS match complete
        drain(observer, 2.5)

        # --- T1 baseline: a well-formed 5-angle packet crosses to ROS ---
        got = send_and_collect("10.5,-20.25,30.0,0.0,-45.75")
        record(
            "t1_wellformed_packet_reaches_ros",
            {
                "messages": len(got),
                "data": got[0]["data"] if got else None,
                "has_header": got[0]["has_header"] if got else None,
            },
            {
                "messages": 1,
                "data": [10.5, -20.25, 30.0, 0.0, -45.75],
                "has_header": False,
            },
            "std_msgs/Float32MultiArray has no Header field, so I3 source time "
            "cannot be carried even in principle on this topic.",
        )

        # --- T2 I1: the wire has no validity field, and the regex parser has no
        #     field discipline. A validity token added to the payload is not
        #     interpreted as validity — its numeric part is consumed as an angle.
        got = send_and_collect("IsTrackedDataValid:0;10.5,-20.25,30.0,0.0,-45.75")
        record(
            "t2_validity_token_is_swallowed_as_an_angle",
            {
                "messages": len(got),
                "len": got[0]["len"] if got else None,
                "first_value": got[0]["data"][0] if got else None,
                "tail_matches_t1": got[0]["data"][1:] if got else None,
            },
            {
                "messages": 1,
                "len": 6,
                "first_value": 0.0,
                "tail_matches_t1": [10.5, -20.25, 30.0, 0.0, -45.75],
            },
            "parseJointAngles (HandTrackerQuest.cpp:169-187) applies the regex "
            "[-+]?[0-9]*\\.?[0-9]+ to the whole datagram with no key parsing, so any "
            "number anywhere becomes a joint angle. There is no slot in which a "
            "tracking-validity bit could be transported without corrupting the payload.",
        )

        # --- T3 I4: identical repeated datagrams are indistinguishable downstream ---
        first = send_and_collect("1.0,2.0,3.0")
        time.sleep(1.0)
        second = send_and_collect("1.0,2.0,3.0")
        record(
            "t3_repeated_identical_packet_indistinguishable",
            {
                "first_len": len(first),
                "second_len": len(second),
                "payloads_identical": bool(first)
                and bool(second)
                and first[0]["data"] == second[0]["data"],
                "any_sequence_or_session_field": False,
            },
            {
                "first_len": 1,
                "second_len": 1,
                "payloads_identical": True,
                "any_sequence_or_session_field": False,
            },
            "No sequence number, session id, or generation counter exists on the "
            "wire or in the message; a 1 s-old resend is byte-identical to a fresh one.",
        )

        # --- T4 I5: when the stream stops, the topic simply goes silent ---
        observer.received.clear()
        drain(observer, 2.0)
        record(
            "t4_stream_stop_emits_no_invalidation",
            {"messages_after_2s_silence": len(observer.received)},
            {"messages_after_2s_silence": 0},
            "Source silence produces no invalidation message and no zeroing publish; "
            "the topic just stops. A latched/last-value consumer retains the last "
            "angles with no in-band signal that they are no longer being produced.",
        )

        # --- T5: a datagram containing no number at all is dropped, not zeroed ---
        got = send_and_collect("HandLost")
        record(
            "t5_numberless_packet_is_dropped_not_zeroed",
            {"messages": len(got)},
            {"messages": 0},
            "processingThread logs 'No valid joint angles found' and publishes "
            "nothing (HandTrackerQuest.cpp:153-155): an explicit loss report on the "
            "wire would also produce silence, indistinguishable from a dropped packet.",
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
        (args.output.parent / "nu_mech_node_stdout.txt").write_text(node_log or "")

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
            "I1_tracking": "DROPPED_AT_WIRE",
            "I2_source_id": "DROPPED_AT_WIRE",
            "I3_source_time": "DROPPED_AT_WIRE",
            "I4_session_generation": "ABSENT",
            "I5_invalidation": "ABSENT_DOWNSTREAM",
        },
        "downstream_consequence": "ROS_PUBLISHED",
        "evidence_level": "E2_SYNTHETIC_RUNTIME",
        "claim_boundary": (
            "Unmodified upstream C++ node executed over real DDS with synthetic UDP "
            "input. Injection is downstream of the Unity IsTrackedDataValid gate, so "
            "no claim is made about that gate's native behaviour. The upstream repo "
            "has no robot consumer; no control consequence is claimed."
        ),
    }
    append_jsonl(args.output, summary)
    print(json.dumps({k: summary[k] for k in ("status", "trials", "passed", "failures")}))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
