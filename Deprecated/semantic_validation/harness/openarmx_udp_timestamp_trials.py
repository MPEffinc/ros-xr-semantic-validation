#!/usr/bin/env python3
"""Inject timestamp trials at the OpenArmX production UDP wire boundary."""

import argparse
import json
import socket
import time
from pathlib import Path

import rclpy
from geometry_msgs.msg import PoseStamped
from rclpy.node import Node


class PoseCollector(Node):
    def __init__(self, topic: str) -> None:
        super().__init__("openarmx_udp_timestamp_trials")
        self.messages = []
        self.create_subscription(PoseStamped, topic, self.messages.append, 10)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=55100)
    parser.add_argument("--topic", default="/pico_right_controller/pose")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    cases = [
        ("A_CURRENT_POSITIVE", None),
        ("B_DELIBERATELY_OLD", 946684800123456789),
        ("C_ZERO_FALLBACK", 0),
    ]

    rclpy.init()
    node = PoseCollector(args.topic)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    results = []

    try:
        # Allow discovery between the production bridge and this subscriber.
        deadline = time.monotonic() + 5.0
        while time.monotonic() < deadline:
            rclpy.spin_once(node, timeout_sec=0.1)

        for trial_id, timestamp_ns in cases:
            if timestamp_ns is None:
                timestamp_ns = time.time_ns()
            before_count = len(node.messages)
            packet = (
                "RIGHT 0.125 -0.250 0.375 0.0 0.0 0.0 1.0 "
                f"0.25 0.75 0 0 0 0 0.1 {timestamp_ns}"
            )
            send_wall_ns = time.time_ns()
            send_monotonic_ns = time.monotonic_ns()
            sock.sendto(packet.encode("ascii"), (args.host, args.port))

            deadline = time.monotonic() + 5.0
            while len(node.messages) == before_count and time.monotonic() < deadline:
                rclpy.spin_once(node, timeout_sec=0.1)
            if len(node.messages) == before_count:
                raise RuntimeError(f"no ROS PoseStamped received for {trial_id}")

            msg = node.messages[-1]
            output_ns = msg.header.stamp.sec * 1_000_000_000 + msg.header.stamp.nanosec
            results.append(
                {
                    "trial_id": trial_id,
                    "udp_packet": packet,
                    "input_timestamp_ns": timestamp_ns,
                    "send_wall_ns": send_wall_ns,
                    "send_monotonic_ns": send_monotonic_ns,
                    "ros_header": {
                        "sec": msg.header.stamp.sec,
                        "nanosec": msg.header.stamp.nanosec,
                        "timestamp_ns": output_ns,
                        "frame_id": msg.header.frame_id,
                    },
                    "pose": {
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
                    },
                    "header_equals_input": output_ns == timestamp_ns,
                    "header_minus_send_wall_ns": output_ns - send_wall_ns,
                }
            )
            time.sleep(0.2)
    finally:
        sock.close()
        node.destroy_node()
        rclpy.shutdown()

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps({"cases": results}, indent=2) + "\n")
    print(json.dumps({"cases": results}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
