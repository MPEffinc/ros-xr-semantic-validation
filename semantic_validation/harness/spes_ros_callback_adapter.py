#!/usr/bin/env python3
"""Research-only Spes callback-to-ROS adapter.

The adapter is deliberately registered *after* ``ServerObserver`` on the
actual pinned ``Teleop`` object.  It does not alter the WebXR frontend, WSS
packet, or ``Teleop.__update``.  It publishes only the already-accepted
callback target as ``PoseStamped`` and records a side-band correlation log;
the standard ROS message receives no experiment identifier.
"""

from __future__ import annotations

import argparse
import json
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import numpy as np


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class Jsonl:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            raise FileExistsError(f"refusing to overwrite log: {path}")
        self.path = path
        self._stream = path.open("x", encoding="utf-8")

    def write(self, event: dict[str, Any]) -> None:
        self._stream.write(json.dumps(event, sort_keys=True) + "\n")
        self._stream.flush()

    def close(self) -> None:
        self._stream.close()


class SpesRosCallbackAdapter:
    """Translate the accepted target callback at an observational boundary."""

    def __init__(
        self,
        *,
        run_id: str,
        publisher: Any,
        pose_factory: Callable[[], Any],
        now_message: Callable[[], Any],
        log: Jsonl,
        server_update_index: Callable[[], int],
    ):
        self.run_id = run_id
        self.publisher = publisher
        self.pose_factory = pose_factory
        self.now_message = now_message
        self.log = log
        self.server_update_index = server_update_index
        self.local_event_id = 0

    @staticmethod
    def _pose_dict(pose: np.ndarray) -> dict[str, float]:
        # This adapter intentionally does not generate a tracking status or a
        # source timestamp; neither exists in the accepted Spes callback.
        import transforms3d as t3d

        quat = t3d.quaternions.mat2quat(pose[:3, :3])
        return {
            "x": float(pose[0, 3]), "y": float(pose[1, 3]), "z": float(pose[2, 3]),
            "qx": float(quat[1]), "qy": float(quat[2]),
            "qz": float(quat[3]), "qw": float(quat[0]),
        }

    def callback(self, pose: np.ndarray, params: dict[str, Any]) -> None:
        self.local_event_id += 1
        event_id = self.local_event_id
        callback_ns = time.monotonic_ns()
        message = self.pose_factory()
        message.header.stamp = self.now_message()
        message.header.frame_id = "spes_accepted_target"
        values = self._pose_dict(pose)
        message.pose.position.x = values["x"]
        message.pose.position.y = values["y"]
        message.pose.position.z = values["z"]
        message.pose.orientation.x = values["qx"]
        message.pose.orientation.y = values["qy"]
        message.pose.orientation.z = values["qz"]
        message.pose.orientation.w = values["qw"]
        server_index = self.server_update_index()
        self.publisher.publish(message)
        self.log.write({
            "event": "spes_callback_ros_publish",
            "run_id": self.run_id,
            "adapter_local_event_id": event_id,
            "server_update_index": server_index,
            "callback_monotonic_ns": callback_ns,
            "adapter_publish_monotonic_ns": time.monotonic_ns(),
            "adapter_wall_utc": utc_now(),
            "ros_header_stamp": {
                "sec": int(message.header.stamp.sec),
                "nanosec": int(message.header.stamp.nanosec),
            },
            "topic": "/robot_target_pose",
            "frame_id": message.header.frame_id,
            "accepted_target": values,
            "source_timestamp_preserved": False,
            "tracking_semantic_added": False,
            "production_schema_modified": False,
            "production_callback_params": {"move": bool(params.get("move"))},
        })


def self_test() -> int:
    """Dependency-light test for post-callback logging and schema discipline."""
    class Stamp:
        sec, nanosec = 7, 42

    class Header:
        stamp = None
        frame_id = ""

    class Position:
        x = y = z = 0.0

    class Orientation:
        x = y = z = 0.0
        w = 1.0

    class Pose:
        position, orientation = Position(), Orientation()

    class FakePoseStamped:
        header, pose = Header(), Pose()

        def __init__(self):
            self.header, self.pose = Header(), Pose()
            self.pose.position, self.pose.orientation = Position(), Orientation()

    class Publisher:
        messages: list[FakePoseStamped]

        def __init__(self): self.messages = []
        def publish(self, message): self.messages.append(message)

    with tempfile.TemporaryDirectory(prefix="spes_ros_adapter_") as directory:
        log = Jsonl(Path(directory) / "adapter.jsonl")
        publisher = Publisher()
        adapter = SpesRosCallbackAdapter(
            run_id="selftest", publisher=publisher, pose_factory=FakePoseStamped,
            now_message=Stamp, log=log, server_update_index=lambda: 19,
        )
        adapter.callback(np.eye(4), {"move": True})
        log.close()
        records = [json.loads(line) for line in (Path(directory) / "adapter.jsonl").read_text().splitlines()]
    assert len(publisher.messages) == len(records) == 1
    record = records[0]
    assert record["adapter_local_event_id"] == 1 and record["server_update_index"] == 19
    assert record["production_schema_modified"] is False
    assert record["tracking_semantic_added"] is False
    assert publisher.messages[0].header.frame_id == "spes_accepted_target"
    print(json.dumps({"event": "spes_ros_callback_adapter_selftest", "result": "PASS"}))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        return self_test()
    parser.error("The runtime launcher is intentionally separate; use the documented Docker runbook.")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
