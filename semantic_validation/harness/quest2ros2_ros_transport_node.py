#!/usr/bin/env python3
"""Robot-free actual ROS transport test for the pinned Quest2ROS2 node.

This file runs inside the ROS 2 Humble container.  It wraps the production
callback with a side-band arrival recorder but delegates every callback to the
unchanged upstream implementation.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import datetime, timezone
import json
from pathlib import Path
import threading
import time
from typing import Any

import rclpy
from rclpy.executors import MultiThreadedExecutor
from rclpy.node import Node
from geometry_msgs.msg import PoseStamped, TransformStamped
from tf2_ros import StaticTransformBroadcaster

from q2r2_bringup.right_arm_controller import RightArmController


EXPERIMENT = "quest2ros2_actual_ros_runtime"
INPUT_TOPIC = "/q2r_right_hand_pose"
OUTPUT_TOPIC = "/bh_robot/right_arm_clik_controller/target_frame"
BASE_FRAME = "bh_robot_base"
EEF_FRAME = "right_arm_link_ee"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def stamp_to_ns(stamp: Any) -> int:
    return int(stamp.sec) * 1_000_000_000 + int(stamp.nanosec)


def pose_value(message: PoseStamped) -> dict[str, float]:
    return {
        "position_x": float(message.pose.position.x),
        "position_y": float(message.pose.position.y),
        "position_z": float(message.pose.position.z),
        "orientation_x": float(message.pose.orientation.x),
        "orientation_y": float(message.pose.orientation.y),
        "orientation_z": float(message.pose.orientation.z),
        "orientation_w": float(message.pose.orientation.w),
    }


class Recorder:
    def __init__(self, output_path: Path) -> None:
        self.output_path = output_path
        self.lock = threading.RLock()
        self.condition = threading.Condition(self.lock)
        self.callbacks: dict[tuple[int, str], list[dict[str, Any]]] = defaultdict(list)

    def record(self, value: dict[str, Any]) -> None:
        value = dict(value)
        value.setdefault("wall_timestamp", utc_now())
        value.setdefault("monotonic_timestamp_ns", time.monotonic_ns())
        with self.lock:
            with self.output_path.open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n")

    def callback_arrival(self, message: PoseStamped, node_time_ns: int) -> None:
        key = (stamp_to_ns(message.header.stamp), message.header.frame_id)
        observation = {
            "event": "actual_callback_consumption",
            "input_stamp_ns": key[0],
            "input_frame": key[1],
            "callback_node_time_ns": node_time_ns,
        }
        self.record(observation)
        with self.condition:
            self.callbacks[key].append(observation)
            self.condition.notify_all()

    def wait_callback(self, key: tuple[int, str], timeout: float = 5.0) -> dict[str, Any] | None:
        deadline = time.monotonic() + timeout
        with self.condition:
            while not self.callbacks.get(key):
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    return None
                self.condition.wait(remaining)
            return self.callbacks[key].pop(0)


class ObservedRightArmController(RightArmController):
    """Production node with a non-mutating side-band callback entry hook."""

    def __init__(self, recorder: Recorder) -> None:
        self._runtime_recorder = recorder
        super().__init__()

    def _pose_callback(self, pose_stamped: PoseStamped) -> Any:
        self._runtime_recorder.callback_arrival(
            pose_stamped, self.get_clock().now().nanoseconds
        )
        return super()._pose_callback(pose_stamped)


class TransportDriver(Node):
    def __init__(self, recorder: Recorder) -> None:
        super().__init__("quest2ros2_semantic_transport_driver")
        self.recorder = recorder
        self.pose_publisher = self.create_publisher(PoseStamped, INPUT_TOPIC, 10)
        self.input_subscription = self.create_subscription(
            PoseStamped, INPUT_TOPIC, self._input_arrival, 10
        )
        self.output_subscription = self.create_subscription(
            PoseStamped, OUTPUT_TOPIC, self._output_arrival, 10
        )
        self.condition = threading.Condition()
        self.input_arrivals: dict[tuple[int, str], list[dict[str, Any]]] = defaultdict(list)
        self.outputs: list[dict[str, Any]] = []

    def _input_arrival(self, message: PoseStamped) -> None:
        key = (stamp_to_ns(message.header.stamp), message.header.frame_id)
        observation = {
            "event": "actual_ros_input_monitor_arrival",
            "input_stamp_ns": key[0],
            "input_frame": key[1],
            "monitor_node_time_ns": self.get_clock().now().nanoseconds,
        }
        self.recorder.record(observation)
        with self.condition:
            self.input_arrivals[key].append(observation)
            self.condition.notify_all()

    def _output_arrival(self, message: PoseStamped) -> None:
        observation = {
            "event": "actual_ros_output_subscriber_arrival",
            "output_stamp_ns": stamp_to_ns(message.header.stamp),
            "output_frame": message.header.frame_id,
            "subscriber_node_time_ns": self.get_clock().now().nanoseconds,
            "output_pose": pose_value(message),
        }
        self.recorder.record(observation)
        with self.condition:
            self.outputs.append(observation)
            self.condition.notify_all()

    def wait_input(self, key: tuple[int, str], timeout: float = 5.0) -> dict[str, Any] | None:
        deadline = time.monotonic() + timeout
        with self.condition:
            while not self.input_arrivals.get(key):
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    return None
                self.condition.wait(remaining)
            return self.input_arrivals[key].pop(0)

    def wait_output_after(self, count: int, timeout: float = 5.0) -> dict[str, Any] | None:
        deadline = time.monotonic() + timeout
        with self.condition:
            while len(self.outputs) <= count:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    return None
                self.condition.wait(remaining)
            return self.outputs[count]


def make_pose(stamp_ns: int, frame_id: str, x: float) -> PoseStamped:
    message = PoseStamped()
    message.header.stamp.sec = stamp_ns // 1_000_000_000
    message.header.stamp.nanosec = stamp_ns % 1_000_000_000
    message.header.frame_id = frame_id
    message.pose.position.x = x
    message.pose.position.y = -0.2
    message.pose.position.z = 0.5
    message.pose.orientation.w = 1.0
    return message


def wait_until(predicate: Any, timeout: float, interval: float = 0.02) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(interval)
    return False


def write_summary(path: Path, value: dict[str, Any]) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def execute(args: argparse.Namespace) -> dict[str, Any]:
    recorder = Recorder(args.output_jsonl)
    recorder.record(
        {
            "event": "provenance",
            "experiment": EXPERIMENT,
            "target_commit": args.target_commit,
            "node_class": "q2r2_bringup.right_arm_controller.RightArmController",
            "callback": "BaseArmController._pose_callback",
            "callback_wrapper": "side-band entry timestamp then unchanged super callback",
            "input_topic": INPUT_TOPIC,
            "output_topic": OUTPUT_TOPIC,
            "tf_fixture": f"{BASE_FRAME}<-{EEF_FRAME}",
            "robot_or_driver_used": False,
            "container_network": "none",
        }
    )

    rclpy.init()
    controller: ObservedRightArmController | None = None
    driver: TransportDriver | None = None
    fixture: Node | None = None
    executor: MultiThreadedExecutor | None = None
    spin_thread: threading.Thread | None = None
    try:
        controller = ObservedRightArmController(recorder)
        driver = TransportDriver(recorder)
        fixture = Node("quest2ros2_static_tf_fixture")
        broadcaster = StaticTransformBroadcaster(fixture)
        executor = MultiThreadedExecutor(num_threads=4)
        for node in (controller, driver, fixture):
            executor.add_node(node)
        spin_thread = threading.Thread(target=executor.spin, daemon=True)
        spin_thread.start()

        transform = TransformStamped()
        transform.header.stamp = fixture.get_clock().now().to_msg()
        transform.header.frame_id = BASE_FRAME
        transform.child_frame_id = EEF_FRAME
        transform.transform.translation.x = 0.4
        transform.transform.translation.y = -0.1
        transform.transform.translation.z = 0.3
        transform.transform.rotation.w = 1.0
        broadcaster.sendTransform(transform)

        graph_ready = wait_until(
            lambda: driver.pose_publisher.get_subscription_count() >= 2
            and controller.target_pose_publisher.get_subscription_count() >= 1,
            10.0,
        )
        tf_ready = wait_until(
            lambda: controller.tf_buffer.can_transform(
                BASE_FRAME, EEF_FRAME, rclpy.time.Time()
            ),
            10.0,
        )
        recorder.record(
            {
                "event": "preflight",
                "graph_ready": graph_ready,
                "tf_ready": tf_ready,
                "input_subscription_count": driver.pose_publisher.get_subscription_count(),
                "output_subscription_count": controller.target_pose_publisher.get_subscription_count(),
            }
        )
        if not graph_ready or not tf_ready:
            raise RuntimeError(f"ROS graph/TF preflight failed: graph={graph_ready}, tf={tf_ready}")

        # The production node uses a 20-sample filter.  These 20 actual ROS
        # messages fill the filter and establish its first anchor without
        # generating a target output.
        for index in range(20):
            stamp_ns = driver.get_clock().now().nanoseconds + index
            message = make_pose(stamp_ns, "xr_warmup_anchor", 0.5)
            key = (stamp_ns, message.header.frame_id)
            driver.pose_publisher.publish(message)
            callback = recorder.wait_callback(key)
            monitor = driver.wait_input(key)
            if callback is None or monitor is None:
                raise RuntimeError(f"warm-up message {index + 1} did not cross ROS transport")
        if driver.outputs:
            raise RuntimeError("production node unexpectedly published during 20-message anchor warm-up")

        trials = [
            ("age_10ms", 10_000_000, "xr_controller_A"),
            ("age_100ms", 100_000_000, "xr_controller_B"),
            ("age_500ms", 500_000_000, "old_reference_space"),
            ("age_1s", 1_000_000_000, "new_reference_space"),
            ("age_3s", 3_000_000_000, "xr_controller_A"),
            ("age_10s", 10_000_000_000, "old_reference_space"),
            ("future_1s", -1_000_000_000, "new_reference_space"),
        ]
        trial_results: list[dict[str, Any]] = []
        for index, (trial, requested_age_ns, frame_id) in enumerate(trials, start=1):
            emit_ros_ns = driver.get_clock().now().nanoseconds
            input_stamp_ns = emit_ros_ns - requested_age_ns
            message = make_pose(input_stamp_ns, frame_id, 0.5 + 0.01 * index)
            key = (input_stamp_ns, frame_id)
            output_count_before = len(driver.outputs)
            emit_monotonic_ns = time.monotonic_ns()
            driver.pose_publisher.publish(message)
            monitor = driver.wait_input(key)
            callback = recorder.wait_callback(key)
            output = driver.wait_output_after(output_count_before)
            published = output is not None
            output_stamp_ns = output["output_stamp_ns"] if output else None
            output_frame = output["output_frame"] if output else None
            trial_result = {
                "event": "age_and_frame_trial_result",
                "trial": trial,
                "requested_age_ns": requested_age_ns,
                "publisher_emit_ros_ns": emit_ros_ns,
                "publisher_emit_monotonic_ns": emit_monotonic_ns,
                "original_input_stamp_ns": input_stamp_ns,
                "original_input_frame": frame_id,
                "input_pose": pose_value(message),
                "actual_ros_monitor_arrival": monitor,
                "actual_callback_consumption": callback,
                "published": published,
                "output_target_stamp_ns": output_stamp_ns,
                "output_target_frame": output_frame,
                "output_target_pose": output["output_pose"] if output else None,
                "source_stamp_preserved": output_stamp_ns == input_stamp_ns if output else None,
                "source_frame_preserved": output_frame == frame_id if output else None,
                "output_retimestamped": output_stamp_ns != input_stamp_ns if output else None,
                "configured_frame_substituted": output_frame == BASE_FRAME if output else None,
            }
            recorder.record(trial_result)
            trial_results.append(trial_result)

        chain_complete = all(
            result["actual_ros_monitor_arrival"] is not None
            and result["actual_callback_consumption"] is not None
            and result["published"]
            for result in trial_results
        )
        all_stamps_replaced = all(result["output_retimestamped"] for result in trial_results)
        all_frames_replaced = all(
            result["configured_frame_substituted"] for result in trial_results
        )
        all_age_cases_published = all(result["published"] for result in trial_results)
        observed_frames = sorted({result["original_input_frame"] for result in trial_results})
        required_frames = sorted(
            {"xr_controller_A", "xr_controller_B", "old_reference_space", "new_reference_space"}
        )
        if not chain_complete:
            status = "FAIL"
        elif all_age_cases_published and all_stamps_replaced and all_frames_replaced:
            status = "PASS"
        else:
            status = "DISPROVED"
        summary = {
            "experiment": EXPERIMENT,
            "timestamp": utc_now(),
            "status": status,
            "evidence_level": "ACTUAL_ROS2_TRANSPORT_ACTUAL_NODE",
            "target_commit": args.target_commit,
            "actual_quest2ros2_node_executed": True,
            "production_callback_delegated_unchanged": True,
            "sideband_callback_entry_observer": True,
            "synthetic_pose_publisher": True,
            "actual_ros_subscription": True,
            "actual_ros_target_publisher": True,
            "dummy_target_subscriber": True,
            "dummy_static_tf": True,
            "robot_or_driver_used": False,
            "container_network": "none",
            "trial_count": len(trial_results),
            "transport_chain_complete": chain_complete,
            "all_age_cases_published": all_age_cases_published,
            "all_source_stamps_replaced": all_stamps_replaced,
            "all_source_frames_replaced_with_configured_base": all_frames_replaced,
            "required_frame_provenance_inputs": required_frames,
            "observed_frame_provenance_inputs": observed_frames,
            "frame_provenance_sweep_complete": observed_frames == required_frames,
            "trials": trial_results,
        }
        recorder.record({"event": "summary", **summary})
        return summary
    finally:
        if executor is not None:
            executor.shutdown(timeout_sec=2.0)
        if spin_thread is not None:
            spin_thread.join(timeout=2.0)
        for node in (driver, controller, fixture):
            if node is not None:
                node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-jsonl", type=Path, required=True)
    parser.add_argument("--summary-json", type=Path, required=True)
    parser.add_argument("--target-commit", required=True)
    args = parser.parse_args()
    args.output_jsonl.parent.mkdir(parents=True, exist_ok=True)
    if args.output_jsonl.exists() or args.summary_json.exists():
        raise SystemExit("refusing to overwrite existing evidence")
    try:
        summary = execute(args)
    except Exception as error:
        summary = {
            "experiment": EXPERIMENT,
            "timestamp": utc_now(),
            "status": "FAIL",
            "evidence_level": "ROS_RUNTIME_ATTEMPT_FAILED",
            "target_commit": args.target_commit,
            "actual_quest2ros2_node_executed": False,
            "robot_or_driver_used": False,
            "error_type": type(error).__name__,
            "error": str(error),
        }
        if args.output_jsonl.exists():
            Recorder(args.output_jsonl).record({"event": "fatal_error", **summary})
    write_summary(args.summary_json, summary)
    print(json.dumps(summary, sort_keys=True))
    return 0 if summary["status"] in {"PASS", "DISPROVED"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
