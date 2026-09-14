#!/usr/bin/env python3
"""Synthetic ROS-TCP client that speaks the ros_tcp_endpoint wire protocol.

SCOPE / HONESTY BOUNDARY
------------------------
This harness exercises the **transport backend** (Unity-Technologies
``ros_tcp_endpoint``, the endpoint PickNik's pinned ``UnityProject`` targets via
``com.unity.robotics.ros-tcp-connector``).  It does **not** execute PickNik's own
C# ``RosPublishers`` class.  The injection point is the ROS-TCP socket, i.e.
downstream of every Unity-side line of code: the XRI input actions, the
tracked-pose driver, the ``Transform``, the FLU change-of-basis and
``PublishOdomAndTf()`` are all bypassed.

Therefore:
  * This is NOT evidence about PickNik's semantic handling.
  * It IS evidence that the message schema PickNik emits, once on the wire,
    carries no tracking-validity field and is byte-identical for a "tracked"
    and an "inferred/frozen" source that share the same pose.
  * Replay subclass: BOUNDARY_LIMITED_REPLAY (methodology/EVIDENCE_LEVELS_V2.md).

What is faithfully reproduced from the pinned source
(``UnityProject/Assets/ROSPublishers.cs`` @ bbaef0762fdb0b429b8ea12a4ca65040748b41dd):
  * topic names and child frame ids            (:34-43)
  * header ``frame_id = "quest"``, shared by Odometry and TF (:105,:124)
  * publish rate ``1/60 s``                    (:33,:322)
  * 2.0 s registration gate before first publish (:74,:184,:290)
  * per-sample header stamp regenerated from host UTC wall clock, NOT a source
    sample time                                (:367-380,:394)
  * zero twist                                 (:110-113)
  * left then right, Odometry then TF, per tick (:326-327,:405,:416)

Poses are supplied already in ROS REP-103 FLU, so the Unity coordinate
conversion is *not* modelled -- it sits upstream of the injection point.

The ``is_tracked`` / ``tracking_state`` values carried in the local JSONL are
harness-side ground truth ONLY.  They are deliberately not serialized, because
the pinned publisher has no field for them; that absence is the thing under
test.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import socket
import struct
import time
from pathlib import Path
from typing import Any

try:
    from nav_msgs.msg import Odometry
    from tf2_msgs.msg import TFMessage
    from geometry_msgs.msg import TransformStamped
    from rclpy.serialization import serialize_message

    ROS_IMPORT_ERROR: ModuleNotFoundError | None = None
except ModuleNotFoundError as exc:  # pragma: no cover
    ROS_IMPORT_ERROR = exc

PINNED_REVISION = "bbaef0762fdb0b429b8ea12a4ca65040748b41dd"

LEFT_ODOM_TOPIC = "/left_controller_odom"
RIGHT_ODOM_TOPIC = "/right_controller_odom"
TF_TOPIC = "/tf"
LEFT_CHILD_FRAME = "left_controller_odom"
RIGHT_CHILD_FRAME = "right_controller_odom"
PARENT_FRAME = "quest"

ODOM_PUBLISH_PERIOD = 1.0 / 60.0
REGISTRATION_DELAY_SECONDS = 2.0


# --------------------------------------------------------------------------
# ROS-TCP wire protocol (ros_tcp_endpoint/client.py:read_message, :88-104)
#   <uint32 LE destination length><destination utf-8>
#   <uint32 LE payload length><payload bytes>
# System commands use a destination beginning with "__" and a JSON payload
# whose final byte is stripped by the server (server.py:120-127), so a
# trailing NUL is appended exactly as the Unity connector does.
# --------------------------------------------------------------------------
def frame(destination: str, payload: bytes) -> bytes:
    dest = destination.encode("utf-8")
    return struct.pack("<I", len(dest)) + dest + struct.pack("<I", len(payload)) + payload


def syscommand(command: str, params: dict[str, Any]) -> bytes:
    payload = json.dumps(params).encode("utf-8") + b"\x00"
    return frame(command, payload)


def ros_time_now() -> tuple[int, int]:
    """Mirror of ROSPublishers.GetRosTime() (:367-380): publication wall clock."""
    ns = time.time_ns()
    return int(ns // 1_000_000_000), int(ns % 1_000_000_000)


def build_odometry(sec: int, nanosec: int, child_frame: str, pose: dict[str, float]) -> Odometry:
    msg = Odometry()
    msg.header.stamp.sec = sec
    msg.header.stamp.nanosec = nanosec
    msg.header.frame_id = PARENT_FRAME
    msg.child_frame_id = child_frame
    msg.pose.pose.position.x = pose["px"]
    msg.pose.pose.position.y = pose["py"]
    msg.pose.pose.position.z = pose["pz"]
    msg.pose.pose.orientation.x = pose["ox"]
    msg.pose.pose.orientation.y = pose["oy"]
    msg.pose.pose.orientation.z = pose["oz"]
    msg.pose.pose.orientation.w = pose["ow"]
    return msg


def build_tf(sec: int, nanosec: int, child_frame: str, pose: dict[str, float]) -> TFMessage:
    ts = TransformStamped()
    ts.header.stamp.sec = sec
    ts.header.stamp.nanosec = nanosec
    ts.header.frame_id = PARENT_FRAME
    ts.child_frame_id = child_frame
    ts.transform.translation.x = pose["px"]
    ts.transform.translation.y = pose["py"]
    ts.transform.translation.z = pose["pz"]
    ts.transform.rotation.x = pose["ox"]
    ts.transform.rotation.y = pose["oy"]
    ts.transform.rotation.z = pose["oz"]
    ts.transform.rotation.w = pose["ow"]
    out = TFMessage()
    out.transforms = [ts]
    return out


# --------------------------------------------------------------------------
# Scenario: a controller moving on a circle, then a tracking-loss interval in
# which the harness freezes the pose (the behaviour a frozen Unity Transform
# would produce), then reacquisition.  is_tracked/tracking_state are ground
# truth held only on the harness side.
# --------------------------------------------------------------------------
SCENARIOS: dict[str, list[tuple[str, float, bool, int, bool]]] = {
    # (name, duration_s, is_tracked, tracking_state, pose_frozen)
    "occlusion": [
        ("BASELINE_TRACKED", 3.0, True, 3, False),
        ("TRACKING_LOST_FROZEN", 4.0, False, 0, True),
        ("REACQUIRED_TRACKED", 3.0, True, 3, False),
    ],
    # Positive control for the schema-collision question: the pose is held at a
    # single fixed value across the whole run while only the harness-side
    # tracking ground truth flips.  Any difference in the emitted bytes would
    # have to come from a tracking field -- the pinned publisher has none.
    "collision": [
        ("FIXED_POSE_TRACKED", 2.0, True, 3, True),
        ("FIXED_POSE_UNTRACKED", 2.0, False, 0, True),
        ("FIXED_POSE_TRACKED_AGAIN", 2.0, True, 3, True),
    ],
}


def phase_at(phases, elapsed: float) -> tuple[str, bool, int, bool, float]:
    t = 0.0
    for name, dur, tracked, tstate, frozen in phases:
        if elapsed < t + dur:
            return name, tracked, tstate, frozen, t
        t += dur
    name, dur, tracked, tstate, frozen = phases[-1]
    return name, tracked, tstate, frozen, t - dur


def pose_at(t: float, side: str) -> dict[str, float]:
    sign = 1.0 if side == "left" else -1.0
    ang = 0.7 * t
    return {
        "px": round(0.40 + 0.10 * math.cos(ang), 6),
        "py": round(sign * (0.20 + 0.10 * math.sin(ang)), 6),
        "pz": round(1.10 + 0.05 * math.sin(0.5 * ang), 6),
        "ox": 0.0,
        "oy": 0.0,
        "oz": round(math.sin(ang / 2.0), 6),
        "ow": round(math.cos(ang / 2.0), 6),
    }


def total_duration(phases) -> float:
    return sum(p[1] for p in phases)


def run(args: argparse.Namespace) -> int:
    if ROS_IMPORT_ERROR is not None:
        raise SystemExit(f"BLOCKED_ENV: ROS 2 Python modules unavailable: {ROS_IMPORT_ERROR}")

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    if out.exists():
        raise SystemExit(f"refusing to overwrite {out}")
    stream = out.open("x", encoding="utf-8", buffering=1)

    def log(rec: dict[str, Any]) -> None:
        rec.update({"wall_time_ns": time.time_ns(), "monotonic_time_ns": time.monotonic_ns()})
        stream.write(json.dumps(rec, sort_keys=True, separators=(",", ":")) + "\n")

    log(
        {
            "event_type": "client_started",
            "pinned_revision": PINNED_REVISION,
            "endpoint": f"{args.host}:{args.port}",
            "evidence_note": "TRANSPORT_BACKEND_ONLY; PickNik C# publisher NOT executed",
            "injection_point": "ROS-TCP socket (downstream of all Unity code)",
            "replay_subclass": "BOUNDARY_LIMITED_REPLAY",
            "scenario": args.scenario,
        }
    )

    sock = socket.create_connection((args.host, args.port), timeout=10.0)
    sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)

    registrations = [
        (LEFT_ODOM_TOPIC, "nav_msgs/Odometry"),
        (RIGHT_ODOM_TOPIC, "nav_msgs/Odometry"),
        (TF_TOPIC, "tf2_msgs/TFMessage"),
    ]
    for topic, message_name in registrations:
        sock.sendall(syscommand("__publish", {"topic": topic, "message_name": message_name}))
        log({"event_type": "register_publisher_sent", "topic": topic, "message_name": message_name})

    # ROSPublishers.MarkRegisteredAfterDelay() (:182-186)
    time.sleep(REGISTRATION_DELAY_SECONDS)
    log({"event_type": "registration_gate_opened", "delay_s": REGISTRATION_DELAY_SECONDS})

    phases = SCENARIOS[args.scenario]
    start = time.monotonic()
    duration = total_duration(phases)
    seq = 0
    next_tick = start
    frozen_pose_cache: dict[str, dict[str, float]] = {}

    while True:
        now = time.monotonic()
        elapsed = now - start
        if elapsed >= duration:
            break
        if now < next_tick:
            time.sleep(min(next_tick - now, 0.005))
            continue
        next_tick += ODOM_PUBLISH_PERIOD
        seq += 1

        phase, is_tracked, tracking_state, frozen, phase_start = phase_at(phases, elapsed)

        for side, odom_topic, child_frame in (
            ("left", LEFT_ODOM_TOPIC, LEFT_CHILD_FRAME),
            ("right", RIGHT_ODOM_TOPIC, RIGHT_CHILD_FRAME),
        ):
            if frozen:
                if side not in frozen_pose_cache:
                    frozen_pose_cache[side] = pose_at(phase_start, side)
                pose = frozen_pose_cache[side]
            else:
                frozen_pose_cache.pop(side, None)
                pose = pose_at(elapsed, side)

            sec, nanosec = ros_time_now()
            odom = build_odometry(sec, nanosec, child_frame, pose)
            odom_bytes = serialize_message(odom)
            sock.sendall(frame(odom_topic, odom_bytes))

            tf = build_tf(sec, nanosec, child_frame, pose)
            tf_bytes = serialize_message(tf)
            sock.sendall(frame(TF_TOPIC, tf_bytes))

            # Digest of the payload with the wall-clock stamp zeroed out, so
            # that two samples differing ONLY in tracking validity can be
            # compared for byte equality.
            stamp_free_odom = serialize_message(build_odometry(0, 0, child_frame, pose))
            stamp_free_tf = serialize_message(build_tf(0, 0, child_frame, pose))

            log(
                {
                    "event_type": "rostcp_publish_sent",
                    "seq": seq,
                    "side": side,
                    "phase": phase,
                    "odom_topic": odom_topic,
                    "child_frame_id": child_frame,
                    "frame_id": PARENT_FRAME,
                    "ros_stamp_ns": sec * 1_000_000_000 + nanosec,
                    "pose": pose,
                    "harness_ground_truth": {
                        "is_tracked": is_tracked,
                        "tracking_state": tracking_state,
                        "pose_frozen": frozen,
                        "serialized_into_ros_output": False,
                    },
                    "odom_payload_len": len(odom_bytes),
                    "tf_payload_len": len(tf_bytes),
                    "odom_digest_stamp_zeroed": hashlib.sha256(stamp_free_odom).hexdigest(),
                    "tf_digest_stamp_zeroed": hashlib.sha256(stamp_free_tf).hexdigest(),
                }
            )

    log({"event_type": "client_stopped", "ticks": seq, "scenario": args.scenario})
    sock.close()
    stream.close()
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=10000)
    p.add_argument("--output", required=True)
    p.add_argument("--scenario", default="occlusion", choices=sorted(SCENARIOS))
    return run(p.parse_args())


if __name__ == "__main__":
    raise SystemExit(main())
