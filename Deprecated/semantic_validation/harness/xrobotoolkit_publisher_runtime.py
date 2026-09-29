#!/usr/bin/env python3
"""XRoboToolkit-Teleop-ROS — synthetic-wire runtime against the unmodified
production ROS 2 publisher (`picoxr/talker`, ros2/picoxr/src/publisher.cpp).

Executed path
-------------
  synthetic PICO device-state JSON records (this harness, a local file)
      -> INERT LOCAL SUBSTITUTE for libPXREARobotSDK.so, which only replays those
         records into the upstream callback  (see harness/xrobotoolkit_stub/)
      -> picoxr/talker  (UNMODIFIED upstream C++ publisher.cpp)
      -> DDS (ROS_DOMAIN_ID=73, loopback only, container --network none)
      -> rclpy observer subscribing /xr_pose  (xr_msgs/Custom)

Substitutions (dependency-boundary only, both documented in the output record)
------------------------------------------------------------------------------
1. `PXREARobotSDK.h` + `libPXREARobotSDK.so` are proprietary PICO Robotics
   Service artefacts that are not present and cannot be obtained here. An inert
   local substitute declaring only the symbols publisher.cpp uses is installed at
   the exact path upstream's CMakeLists.txt probes. It performs no device
   discovery, opens no socket, and contains no PICO code. Without it the
   upstream build fails hard — that failure is captured separately as the
   BLOCKED_EXTERNAL_DEPENDENCY evidence.
2. Upstream `ros2/xr_msgs/CMakeLists.txt` calls `rosidl_generate_interfaces()`
   but only `find_package(rosidl_generator_cpp)`, which does not define that
   macro on ROS 2 Jazzy. The missing `find_package(rosidl_default_generators)`
   is injected through CMake's `CMAKE_PROJECT_<name>_INCLUDE` hook rather than
   by editing upstream source.

publisher.cpp itself is byte-for-byte upstream; its SHA-256 is recorded.

The PicoXR frontend and the PICO Robotics Service are opaque and are NOT
executed. Nothing is claimed about what a PicoXR `status` value natively means.
Injection is at the service-JSON boundary: ``BOUNDARY_LIMITED_REPLAY``.
Highest admissible evidence level: ``E2 SYNTHETIC_RUNTIME``.
No Quest, no PICO headset, no ARX arm, no robot, no actuator, no driver.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import time
from pathlib import Path
from typing import Any

import rclpy
from rclpy.node import Node
from xr_msgs.msg import Custom

EXPERIMENT = "xrobotoolkit_publisher_runtime"
TOPIC = "xr_pose"

# Synthetic device-state records, in the envelope publisher.cpp expects:
#   outer  {"value": "<stringified inner json>"}
#   inner  {"timeStampNs":..., "Input":..., "Head":{...}, "Controller":{...}}
STALE_TS = 1_000_000_000_000  # ~1970-01-01T00:16:40Z, deliberately ancient


def _record(inner: dict[str, Any]) -> str:
    return json.dumps({"value": json.dumps(inner)})


def controller(status: int, trigger: float = 0.0) -> dict[str, Any]:
    return {
        "axisX": 0.0,
        "axisY": 0.0,
        "axisClick": False,
        "grip": 0.0,
        "trigger": trigger,
        "primaryButton": False,
        "secondaryButton": False,
        "menuButton": False,
        "pose": "0.1,0.2,0.3,0,0,0,1",
        "status": status,
    }


SYNTHETIC_RECORDS = [
    # r0 — head status 1, both controllers report status 1 on the wire
    _record(
        {
            "timeStampNs": 111_222_333_444_555,
            "Input": 0,
            "Head": {"pose": "0,1.6,0,0,0,0,1", "status": 1},
            "Controller": {"left": controller(1), "right": controller(1, 0.75)},
        }
    ),
    # r1 — head status 0 and both controllers status 0 (a would-be "not valid"
    #      report from the service)
    _record(
        {
            "timeStampNs": 111_222_333_555_555,
            "Input": 0,
            "Head": {"pose": "0,1.6,0,0,0,0,1", "status": 0},
            "Controller": {"left": controller(0), "right": controller(0)},
        }
    ),
    # r2 — no Controller key at all (controllers absent)
    _record(
        {
            "timeStampNs": 111_222_333_666_555,
            "Input": 0,
            "Head": {"pose": "0,1.6,0,0,0,0,1", "status": 2},
        }
    ),
    # r3 — no Head key at all
    _record(
        {
            "timeStampNs": 111_222_333_777_555,
            "Input": 0,
            "Controller": {"left": controller(1), "right": controller(1)},
        }
    ),
    # r4 — an ancient source timestamp, otherwise identical to r0
    _record(
        {
            "timeStampNs": STALE_TS,
            "Input": 0,
            "Head": {"pose": "0,1.6,0,0,0,0,1", "status": 1},
            "Controller": {"left": controller(1), "right": controller(1, 0.75)},
        }
    ),
]


def append_jsonl(path: Path, record: dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n")


class Observer(Node):
    def __init__(self) -> None:
        super().__init__("xrobotoolkit_observer")
        self.messages: list[dict[str, Any]] = []
        self.create_subscription(Custom, TOPIC, self._cb, 50)

    def _cb(self, msg: Custom) -> None:
        self.messages.append(
            {
                "recv_wall_ns": time.time_ns(),
                "timestamp_ns": int(msg.timestamp_ns),
                "input": int(msg.input),
                "head_status": int(msg.head.status),
                "head_pose": [round(float(v), 4) for v in msg.head.pose],
                "left_status": int(msg.left_controller.status),
                "right_status": int(msg.right_controller.status),
                "right_trigger": round(float(msg.right_controller.trigger), 4),
            }
        )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--node-exe", type=Path, required=True)
    parser.add_argument("--source-file", type=Path, required=True)
    parser.add_argument("--stub-dir", type=Path, required=True)
    parser.add_argument("--json-file", type=Path, required=True)
    parser.add_argument("--revision", required=True)
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if args.output.exists():
        raise SystemExit(f"refusing to overwrite {args.output}")

    args.json_file.write_text("\n".join(SYNTHETIC_RECORDS) + "\n")

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
            "production_node": "picoxr/talker (ros2/picoxr/src/publisher.cpp)",
            "node_source_modified": False,
            "substitutions": [
                "INERT_LOCAL_SDK_STUB: PXREARobotSDK.h + libPXREARobotSDK.so replaced "
                "by a local no-device, no-socket replayer of synthetic JSON records",
                "BUILD_HOOK: find_package(rosidl_default_generators) injected into "
                "xr_msgs via CMAKE_PROJECT_xr_msgs_INCLUDE (upstream CMakeLists omits it)",
            ],
            "stub_sha256": {
                p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                for p in sorted(args.stub_dir.glob("*"))
                if p.is_file()
            },
            "injection_point": "PICO_SERVICE_DEVICE_STATE_JSON",
            "replay_class": "BOUNDARY_LIMITED_REPLAY",
            "bypassed_native_logic": "PicoXR frontend and PICO Robotics Service (opaque, not executed)",
            "active_native_logic": "publisher.cpp OnPXREAClientCallback JSON parse, "
            "field mapping, xr_msgs/Custom construction and publish",
            "xr_hardware_used": False,
            "robot_used": False,
            "arx_consumer_launched": False,
            "ros_transport_used": True,
            "synthetic_records": len(SYNTHETIC_RECORDS),
            "evidence_level": "E2_SYNTHETIC_RUNTIME",
        },
    )

    env_line = f"XRT_SYNTHETIC_JSON={args.json_file}"
    proc = subprocess.Popen(
        ["env", env_line, str(args.node_exe)],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    rclpy.init()
    observer = Observer()
    results: list[dict[str, Any]] = []

    def record(trial, observed, expected, note="") -> None:
        status = "PASS" if observed == expected else "FAIL"
        rec = {
            "experiment": EXPERIMENT,
            "trial": trial,
            "event": "wire_to_ros_result",
            "monotonic_timestamp_ns": time.monotonic_ns(),
            "source_generation": args.revision,
            "source_kind": "SYNTHETIC_SERVICE_JSON",
            "observed": observed,
            "expected": expected,
            "note": note,
            "status": status,
            "evidence_level": "E2_SYNTHETIC_RUNTIME",
        }
        results.append(rec)
        append_jsonl(args.output, rec)

    try:
        deadline = time.monotonic() + 20.0
        while time.monotonic() < deadline and len(observer.messages) < len(
            SYNTHETIC_RECORDS
        ):
            rclpy.spin_once(observer, timeout_sec=0.1)
        msgs = list(observer.messages)

        record(
            "t0_all_synthetic_records_reach_ros",
            {"received": len(msgs)},
            {"received": len(SYNTHETIC_RECORDS)},
            "Each service-JSON record produces exactly one xr_msgs/Custom on /xr_pose.",
        )
        if len(msgs) < len(SYNTHETIC_RECORDS):
            raise SystemExit("insufficient messages received; see trial t0")

        # --- I3: the source timestamp IS carried through, verbatim ---
        record(
            "t1_source_timestamp_preserved_verbatim",
            {
                "r0": msgs[0]["timestamp_ns"],
                "r1": msgs[1]["timestamp_ns"],
                "wire_value_r0": 111_222_333_444_555,
            },
            {
                "r0": 111_222_333_444_555,
                "r1": 111_222_333_555_555,
                "wire_value_r0": 111_222_333_444_555,
            },
            "publisher.cpp:130 copies value_obj[\"timeStampNs\"] into "
            "custom_msg.timestamp_ns. Unlike every re-stamping bridge in this study, "
            "XRoboToolkit does carry a source time onto the ROS message.",
        )

        # --- I3: but nothing checks it; an ancient stamp publishes unchanged ---
        record(
            "t2_stale_source_timestamp_published_unchanged",
            {
                "stale_timestamp_on_topic": msgs[4]["timestamp_ns"],
                "message_published": True,
                "head_status": msgs[4]["head_status"],
            },
            {
                "stale_timestamp_on_topic": STALE_TS,
                "message_published": True,
                "head_status": 1,
            },
            "A source timestamp decades in the past is published with no age guard, "
            "no warning and no status change. Freshness is carried but never enforced "
            "on this path; whether any consumer enforces it is a separate question.",
        )

        # --- I1: the head status IS preserved from the service ---
        record(
            "t3_head_status_preserved_from_service",
            {"r0": msgs[0]["head_status"], "r1": msgs[1]["head_status"],
             "r2": msgs[2]["head_status"]},
            {"r0": 1, "r1": 0, "r2": 2},
            "publisher.cpp:142 copies head_j[\"status\"] verbatim.",
        )

        # --- I1 key finding: the CONTROLLER status is overwritten with a constant ---
        record(
            "t4_controller_status_overwritten_with_constant_3",
            {
                "r0_wire_status": 1,
                "r0_left_on_topic": msgs[0]["left_status"],
                "r0_right_on_topic": msgs[0]["right_status"],
                "r1_wire_status": 0,
                "r1_left_on_topic": msgs[1]["left_status"],
                "r1_right_on_topic": msgs[1]["right_status"],
                "topic_values_differ_between_r0_and_r1": (
                    msgs[0]["left_status"] != msgs[1]["left_status"]
                ),
            },
            {
                "r0_wire_status": 1,
                "r0_left_on_topic": 3,
                "r0_right_on_topic": 3,
                "r1_wire_status": 0,
                "r1_left_on_topic": 3,
                "r1_right_on_topic": 3,
                "topic_values_differ_between_r0_and_r1": False,
            },
            "publisher.cpp:167 assigns controller_msg.status = 3 unconditionally, "
            "discarding ctrl_j[\"status\"] which is present in the same object and is "
            "read for no other field. Two service records carrying different "
            "controller status values produce identical status on /xr_pose.",
        )

        # --- I1: absence IS distinguishable (status -1 sentinel) ---
        record(
            "t5_absent_controller_and_head_use_minus_one_sentinel",
            {
                "r2_left_status": msgs[2]["left_status"],
                "r2_right_status": msgs[2]["right_status"],
                "r3_head_status": msgs[3]["head_status"],
                "r3_head_pose_all_zero": all(v == 0.0 for v in msgs[3]["head_pose"]),
            },
            {
                "r2_left_status": -1,
                "r2_right_status": -1,
                "r3_head_status": -1,
                "r3_head_pose_all_zero": True,
            },
            "publisher.cpp:144,178-179 set status -1 when the Head/Controller key is "
            "absent. Presence/absence therefore survives to ROS even though "
            "controller tracking status does not; and the absent head's pose array is "
            "left at all-zeros, which is a legal-looking pose paired with status -1.",
        )

        # --- I2/I4: what identity and generation information reaches the topic ---
        record(
            "t6_no_device_or_session_identity_on_the_topic",
            {
                "custom_msg_fields": sorted(
                    f for f in Custom.get_fields_and_field_types()
                ),
                "left_right_are_separate_fields": True,
            },
            {
                "custom_msg_fields": [
                    "head",
                    "input",
                    "left_controller",
                    "right_controller",
                    "timestamp_ns",
                ],
                "left_right_are_separate_fields": True,
            },
            "xr_msgs/Custom has no device id, no session id, and no sequence number. "
            "The stub's deviceID is available to the callback (publisher.cpp:121) and "
            "is not copied into the message. Laterality survives only as separate "
            "left_controller/right_controller fields.",
        )
    finally:
        observer.destroy_node()
        rclpy.shutdown()
        proc.terminate()
        try:
            node_log = proc.communicate(timeout=10)[0]
        except subprocess.TimeoutExpired:
            proc.kill()
            node_log = proc.communicate()[0]
        (args.output.parent / "xrobotoolkit_node_stdout.txt").write_text(node_log or "")

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
            "I1_tracking": "head status PRESERVED; controller status DROPPED "
            "(overwritten with constant 3); absence PRESERVED as -1 sentinel",
            "I2_source_id": "TRANSFORMED (laterality only; deviceID dropped)",
            "I3_source_time": "PRESERVED on the message, NOT revalidated anywhere "
            "on this path",
            "I4_session_generation": "ABSENT",
            "I5_invalidation": "NOT_OBSERVABLE at this boundary (no consumer run)",
        },
        "downstream_consequence": "ROS_PUBLISHED",
        "evidence_level": "E2_SYNTHETIC_RUNTIME",
        "claim_boundary": (
            "Unmodified upstream publisher.cpp executed over real DDS with synthetic "
            "service JSON delivered through an inert local SDK substitute. The PicoXR "
            "frontend and PICO Robotics Service are opaque and were not executed, so "
            "the native meaning of any status value is not established. The ARX "
            "consumer was not built or launched; no control consequence is claimed."
        ),
    }
    append_jsonl(args.output, summary)
    print(json.dumps({k: summary[k] for k in ("status", "trials", "passed", "failures")}))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
