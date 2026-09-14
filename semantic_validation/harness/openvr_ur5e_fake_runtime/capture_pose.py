#!/usr/bin/env python3
import argparse
import json
import time

import rclpy
from geometry_msgs.msg import PoseStamped


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--duration", type=float, default=1.2)
    args = parser.parse_args()
    rclpy.init()
    node = rclpy.create_node("openvr_pose_capture")
    start = time.monotonic()
    messages = []

    def callback(msg):
        messages.append({
            "monotonic": time.monotonic(),
            "stamp_sec": msg.header.stamp.sec,
            "stamp_nanosec": msg.header.stamp.nanosec,
            "frame_id": msg.header.frame_id,
            "position": [msg.pose.position.x, msg.pose.position.y, msg.pose.position.z],
            "orientation": [msg.pose.orientation.x, msg.pose.orientation.y,
                            msg.pose.orientation.z, msg.pose.orientation.w],
        })

    node.create_subscription(PoseStamped, "/servo_node/pose_target_cmds", callback, 100)
    while time.monotonic() - start < args.duration:
        rclpy.spin_once(node, timeout_sec=0.05)
    print(json.dumps({"count": len(messages), "messages": messages}, sort_keys=True))
    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()
