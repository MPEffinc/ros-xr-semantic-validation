#!/usr/bin/env python3

"""Read-only ROS 2 sink for Spes target_frame/TF observations."""

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import rclpy
from geometry_msgs.msg import PoseStamped
from rclpy.node import Node
from tf2_msgs.msg import TFMessage


class DummySink(Node):
    def __init__(
        self,
        output: Path,
        target_topic: str,
        tf_topic: str,
        max_samples: int,
        run_id: str,
    ):
        super().__init__("semantic_validation_dummy_sink")
        self._output = output
        self._max_samples = max_samples
        self._run_id = run_id
        self._local_index = 0
        self._target_index = 0
        self._tf_index = 0
        self._output.parent.mkdir(parents=True, exist_ok=True)
        self._output.write_text("", encoding="utf-8")
        self.create_subscription(PoseStamped, target_topic, self._on_pose, 10)
        self.create_subscription(TFMessage, tf_topic, self._on_tf, 10)

    @property
    def done(self) -> bool:
        return self._max_samples > 0 and self._local_index >= self._max_samples

    def _base_record(self, kind: str) -> dict:
        self._local_index += 1
        return {
            "event": kind,
            "run_id": self._run_id,
            "local_index": self._local_index,
            "arrival_wall_utc": datetime.now(timezone.utc).isoformat(),
            "arrival_monotonic_ns": time.monotonic_ns(),
        }

    def _append(self, record: dict) -> None:
        rendered = json.dumps(record, sort_keys=True)
        print(rendered, flush=True)
        with self._output.open("a", encoding="utf-8") as stream:
            stream.write(rendered + "\n")

    def _on_pose(self, msg: PoseStamped) -> None:
        self._target_index += 1
        record = self._base_record("target_frame")
        record.update(
            {
                "topic_index": self._target_index,
                "ros_header_stamp": {
                    "sec": msg.header.stamp.sec,
                    "nanosec": msg.header.stamp.nanosec,
                },
                "frame_id": msg.header.frame_id,
                "position": {
                    "x": msg.pose.position.x,
                    "y": msg.pose.position.y,
                    "z": msg.pose.position.z,
                },
                "orientation": {
                    "x": msg.pose.orientation.x,
                    "y": msg.pose.orientation.y,
                    "z": msg.pose.orientation.z,
                    "w": msg.pose.orientation.w,
                },
            }
        )
        self._append(record)

    def _on_tf(self, msg: TFMessage) -> None:
        for transform in msg.transforms:
            self._tf_index += 1
            record = self._base_record("tf")
            record.update(
                {
                    "topic_index": self._tf_index,
                    "ros_header_stamp": {
                        "sec": transform.header.stamp.sec,
                        "nanosec": transform.header.stamp.nanosec,
                    },
                    "frame_id": transform.header.frame_id,
                    "child_frame_id": transform.child_frame_id,
                    "position": {
                        "x": transform.transform.translation.x,
                        "y": transform.transform.translation.y,
                        "z": transform.transform.translation.z,
                    },
                    "orientation": {
                        "x": transform.transform.rotation.x,
                        "y": transform.transform.rotation.y,
                        "z": transform.transform.rotation.z,
                        "w": transform.transform.rotation.w,
                    },
                }
            )
            self._append(record)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--target-topic", default="target_frame")
    parser.add_argument("--tf-topic", default="/tf")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--max-samples", type=int, default=0)
    parser.add_argument("--duration-sec", type=float, default=30.0)
    args = parser.parse_args()

    rclpy.init()
    node = DummySink(
        args.output,
        args.target_topic,
        args.tf_topic,
        args.max_samples,
        args.run_id,
    )
    deadline = time.monotonic() + args.duration_sec
    try:
        while rclpy.ok() and time.monotonic() < deadline and not node.done:
            rclpy.spin_once(node, timeout_sec=0.1)
    finally:
        node.destroy_node()
        rclpy.shutdown()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
