#!/usr/bin/env python3
import json
import time
from pathlib import Path

import rclpy
from rclpy.node import Node
from std_msgs.msg import String
from teleop_bridge_msgs.msg import ReceivedPoseStates


OUTPUT = Path("/results/rosmonitoring/humble/edge_probe_03.json")


class Probe(Node):
    def __init__(self) -> None:
        super().__init__("s4b_rosmonitoring_edge_probe")
        self.received = {"custom": [], "absent": [], "disconnect": [], "hang": []}
        self.custom_pub = self.create_publisher(ReceivedPoseStates, "/s4b_custom_mon", 10)
        self.absent_pub = self.create_publisher(String, "/s4b_absent_mon", 10)
        self.disconnect_pub = self.create_publisher(String, "/s4b_disconnect_mon", 10)
        self.hang_pub = self.create_publisher(String, "/s4b_hang_mon", 10)
        self.create_subscription(ReceivedPoseStates, "/s4b_custom", lambda msg: self._rx("custom", str(msg.tracked)), 10)
        self.create_subscription(String, "/s4b_absent", lambda msg: self._rx("absent", msg.data), 10)
        self.create_subscription(String, "/s4b_disconnect", lambda msg: self._rx("disconnect", msg.data), 10)
        self.create_subscription(String, "/s4b_hang", lambda msg: self._rx("hang", msg.data), 10)

    def _rx(self, key: str, value: str) -> None:
        self.received[key].append({"value": value, "monotonic_ns": time.monotonic_ns()})

    def spin_for(self, seconds: float) -> None:
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            rclpy.spin_once(self, timeout_sec=0.02)

    def publish_string(self, publisher, value: str) -> int:
        msg = String()
        msg.data = value
        sent = time.monotonic_ns()
        publisher.publish(msg)
        return sent


rclpy.init()
node = Probe()
try:
    node.spin_for(2.0)
    custom_allow = ReceivedPoseStates()
    custom_allow.tracked = True
    custom_allow.teleop_enable = True
    custom_allow.source = "S4B_CUSTOM_ALLOW"
    custom_allow.header.stamp = node.get_clock().now().to_msg()
    custom_allow_sent = time.monotonic_ns()
    node.custom_pub.publish(custom_allow)
    node.spin_for(0.6)

    custom_block = ReceivedPoseStates()
    custom_block.tracked = False
    custom_block.teleop_enable = True
    custom_block.source = "S4B_CUSTOM_BLOCK"
    custom_block.header.stamp = node.get_clock().now().to_msg()
    custom_block_sent = time.monotonic_ns()
    node.custom_pub.publish(custom_block)
    node.spin_for(0.6)

    absent_sent = node.publish_string(node.absent_pub, "fail_open_absent")
    node.spin_for(0.6)
    disconnect_first_sent = node.publish_string(node.disconnect_pub, "disconnect_first")
    node.spin_for(0.6)
    disconnect_second_sent = node.publish_string(node.disconnect_pub, "disconnect_second")
    node.spin_for(0.6)
    hang_sent = node.publish_string(node.hang_pub, "hang_timeout")
    node.spin_for(0.8)

    result = {
        "clock": "CLOCK_MONOTONIC via time.monotonic_ns",
        "sent_monotonic_ns": {
            "custom_allow": custom_allow_sent,
            "custom_block": custom_block_sent,
            "absent": absent_sent,
            "disconnect_first": disconnect_first_sent,
            "disconnect_second": disconnect_second_sent,
            "hang": hang_sent,
        },
        "received": node.received,
        "assertions": {
            "custom_allow_forwarded": len(node.received["custom"]) == 1 and node.received["custom"][0]["value"] == "True",
            "custom_false_blocked": len(node.received["custom"]) == 1,
            "oracle_absent_fail_open": [item["value"] for item in node.received["absent"]] == ["fail_open_absent"],
            "oracle_disconnect_fail_open": [item["value"] for item in node.received["disconnect"]] == ["disconnect_first", "disconnect_second"],
            "oracle_timeout_fail_open": [item["value"] for item in node.received["hang"]] == ["hang_timeout"],
        },
    }
    OUTPUT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if not all(result["assertions"].values()):
        raise SystemExit(1)
finally:
    node.destroy_node()
    if rclpy.ok():
        rclpy.shutdown()
