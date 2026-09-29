#!/usr/bin/env python3
"""Robot-free ROS 2 observer for a PickNik Quest hardware validation run."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import signal
import time
from typing import Any

try:
    import rclpy
    from nav_msgs.msg import Odometry
    from rclpy.node import Node
    from tf2_msgs.msg import TFMessage
    ROS_IMPORT_ERROR: ModuleNotFoundError | None = None
except ModuleNotFoundError as exc:
    rclpy = None  # type: ignore[assignment]
    Odometry = Any  # type: ignore[misc,assignment]
    TFMessage = Any  # type: ignore[misc,assignment]
    Node = object  # type: ignore[misc,assignment]
    ROS_IMPORT_ERROR = exc


def stamp_ns(stamp: Any) -> int:
    return int(stamp.sec) * 1_000_000_000 + int(stamp.nanosec)


class PickNikObserver(Node):
    def __init__(self, output: Path) -> None:
        super().__init__("picknik_semantic_validation_observer")
        self._stream = output.open("x", encoding="utf-8", buffering=1)
        self._counts = {"/left_controller_odom": 0, "/right_controller_odom": 0, "/tf": 0}
        self.create_subscription(
            Odometry,
            "/left_controller_odom",
            lambda msg: self._odom("/left_controller_odom", msg),
            100,
        )
        self.create_subscription(
            Odometry,
            "/right_controller_odom",
            lambda msg: self._odom("/right_controller_odom", msg),
            100,
        )
        self.create_subscription(TFMessage, "/tf", self._tf, 100)
        self._write({"event_type": "observer_started", "topics": sorted(self._counts)})

    def _write(self, record: dict[str, Any]) -> None:
        record.update(
            {
                "wall_time_ns": time.time_ns(),
                "monotonic_time_ns": time.monotonic_ns(),
            }
        )
        self._stream.write(json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n")

    def _odom(self, topic: str, msg: Odometry) -> None:
        self._counts[topic] += 1
        pose = msg.pose.pose
        self._write(
            {
                "event_type": "ros_receive_odometry",
                "topic": topic,
                "index": self._counts[topic],
                "ros_stamp_ns": stamp_ns(msg.header.stamp),
                "frame_id": msg.header.frame_id,
                "child_frame_id": msg.child_frame_id,
                "position": [pose.position.x, pose.position.y, pose.position.z],
                "orientation": [
                    pose.orientation.x,
                    pose.orientation.y,
                    pose.orientation.z,
                    pose.orientation.w,
                ],
            }
        )

    def _tf(self, msg: TFMessage) -> None:
        for transform in msg.transforms:
            if transform.child_frame_id not in ("left_controller_odom", "right_controller_odom"):
                continue
            self._counts["/tf"] += 1
            translation = transform.transform.translation
            rotation = transform.transform.rotation
            self._write(
                {
                    "event_type": "ros_receive_tf",
                    "topic": "/tf",
                    "index": self._counts["/tf"],
                    "ros_stamp_ns": stamp_ns(transform.header.stamp),
                    "frame_id": transform.header.frame_id,
                    "child_frame_id": transform.child_frame_id,
                    "position": [translation.x, translation.y, translation.z],
                    "orientation": [rotation.x, rotation.y, rotation.z, rotation.w],
                }
            )

    def close(self) -> None:
        self._write({"event_type": "observer_stopped", "counts": self._counts})
        self._stream.close()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if args.output.exists():
        raise SystemExit(f"refusing to overwrite {args.output}")
    if rclpy is None:
        raise SystemExit(f"BLOCKED_ENV: ROS 2 Python modules unavailable: {ROS_IMPORT_ERROR}")

    rclpy.init()
    node = PickNikObserver(args.output)
    interrupted = False

    def stop(_signum: int, _frame: Any) -> None:
        nonlocal interrupted
        interrupted = True

    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)
    try:
        while rclpy.ok() and not interrupted:
            rclpy.spin_once(node, timeout_sec=0.25)
    finally:
        node.close()
        node.destroy_node()
        rclpy.shutdown()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
