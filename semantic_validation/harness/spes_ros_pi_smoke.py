#!/usr/bin/env python3
"""Quest-less Spes WSS callback -> ROS -> Pi observation smoke.

The synthetic source enters the actual pinned WSS route.  The research adapter
is registered after ``ServerObserver`` and publishes only accepted callback
targets.  It never changes the production WSS payload or target calculation.
"""

from __future__ import annotations

import argparse
import json
import socket
import ssl
import sys
import threading
import time
from pathlib import Path

VALIDATION_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))

import rclpy  # noqa: E402
import uvicorn  # noqa: E402
from geometry_msgs.msg import PoseStamped  # noqa: E402
from rclpy.node import Node  # noqa: E402
from websocket import create_connection  # noqa: E402
from spes_hardware_server import (  # noqa: E402
    EXPECTED_COMMIT, JsonlWriter, ServerObserver, TARGET_PACKAGE, Teleop,
)
from spes_ros_callback_adapter import Jsonl as AdapterJsonl, SpesRosCallbackAdapter  # noqa: E402


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.bind(("127.0.0.1", 0))
        return listener.getsockname()[1]


def packet(x: float, y: float, z: float) -> dict:
    return {
        "position": {"x": x, "y": y, "z": z},
        "orientation": {"x": 0.0, "y": 0.0, "z": 0.0, "w": 1.0},
        "move": True, "gripper": "open", "scale": 1.0, "device": "VR",
        "message": "questless synthetic source",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--result-dir", type=Path, required=True)
    parser.add_argument("--topic", default="/robot_target_pose")
    # Default 3 preserves the original smoke behaviour exactly. A larger count
    # is used by spes_ros_pi_runtime.py to obtain a non-trivial published vs
    # received comparison. The step stays below the pinned pose-jump tolerance
    # (0.05 m in teleop/__init__.py) so every packet is accepted by production.
    parser.add_argument("--pose-count", type=int, default=3)
    parser.add_argument("--pose-step", type=float, default=0.02)
    parser.add_argument("--send-interval", type=float, default=0.0)
    # Cross-host DDS discovery is not instantaneous. Without this wait the first
    # publishes leave before the remote subscription is matched and are simply
    # never delivered -- a transport artefact, not a semantic finding.
    parser.add_argument("--require-subscribers", type=int, default=0)
    parser.add_argument("--discovery-timeout", type=float, default=60.0)
    args = parser.parse_args()
    if args.pose_step >= 0.05:
        raise SystemExit("pose-step must stay under the pinned 0.05 m jump tolerance")
    if args.result_dir.exists():
        raise SystemExit(f"refusing to overwrite {args.result_dir}")
    args.result_dir.mkdir(parents=True)

    rclpy.init()
    node = Node("spes_ros_pi_smoke_adapter")
    publisher = node.create_publisher(PoseStamped, args.topic, 10)
    adapter_log = AdapterJsonl(args.result_dir / "adapter.jsonl")
    server_log = JsonlWriter(args.result_dir / "server.jsonl")
    teleop = Teleop(host="127.0.0.1", port=0, frontend_dir=str(TARGET_PACKAGE))
    observer = ServerObserver(teleop, server_log)
    adapter = SpesRosCallbackAdapter(
        run_id=args.run_id,
        publisher=publisher,
        pose_factory=PoseStamped,
        now_message=lambda: node.get_clock().now().to_msg(),
        log=adapter_log,
        server_update_index=lambda: observer.update_index,
    )
    teleop.subscribe(adapter.callback)
    port = free_port()
    server = uvicorn.Server(uvicorn.Config(
        app=teleop._Teleop__app, host="127.0.0.1", port=port,
        ssl_keyfile=str(TARGET_PACKAGE / "key.pem"),
        ssl_certfile=str(TARGET_PACKAGE / "cert.pem"),
        log_level="warning", access_log=False,
    ))
    thread = threading.Thread(target=server.run, daemon=True)
    summary = {"run_id": args.run_id, "target_commit": EXPECTED_COMMIT,
               "source": "SYNTHETIC_WSS_POST_BROWSER_GATE",
               "classification": "E2_BOUNDARY_LIMITED_REPLAY",
               "topic": args.topic, "robot_connected": False}
    try:
        thread.start()
        deadline = time.monotonic() + 10
        while not server.started and time.monotonic() < deadline:
            time.sleep(0.02)
        if not server.started:
            raise RuntimeError("pinned Spes WSS server did not start")
        # Give DDS discovery a deterministic opportunity before production callbacks publish.
        time.sleep(2.0)
        if args.require_subscribers > 0:
            deadline = time.monotonic() + args.discovery_timeout
            while (publisher.get_subscription_count() < args.require_subscribers
                   and time.monotonic() < deadline):
                rclpy.spin_once(node, timeout_sec=0.05)
            matched = publisher.get_subscription_count()
            summary["matched_subscriptions_before_send"] = matched
            if matched < args.require_subscribers:
                raise RuntimeError(
                    f"DDS discovery incomplete: {matched} subscriber(s) matched on "
                    f"{args.topic}, required {args.require_subscribers}"
                )
            # Matched != ready to deliver; allow the remote reader a short settle.
            settle = time.monotonic() + 1.0
            while time.monotonic() < settle:
                rclpy.spin_once(node, timeout_sec=0.05)
        ws = create_connection(
            f"wss://127.0.0.1:{port}/ws", timeout=5,
            sslopt={"cert_reqs": ssl.CERT_NONE, "check_hostname": False},
        )
        try:
            poses = [(0.0, round(step * args.pose_step, 9), 0.0)
                     for step in range(args.pose_count)]
            for index, values in enumerate(poses, 1):
                ws.send(json.dumps({"type": "pose", "data": packet(*values)}))
                deadline = time.monotonic() + 2
                while adapter.local_event_id < index and time.monotonic() < deadline:
                    rclpy.spin_once(node, timeout_sec=0.02)
                if adapter.local_event_id != index:
                    raise RuntimeError(f"accepted callback {index} did not publish")
                if args.send_interval:
                    end = time.monotonic() + args.send_interval
                    while time.monotonic() < end:
                        rclpy.spin_once(node, timeout_sec=0.01)
        finally:
            ws.close()
        time.sleep(2.0)
        summary.update({"result": "PASS", "accepted_callbacks": adapter.local_event_id,
                        "ros_publishes": adapter.local_event_id,
                        "server_update_index_final": observer.update_index,
                        "pose_count_requested": args.pose_count})
    except Exception as error:
        summary.update({"result": "FAIL", "error": f"{type(error).__name__}: {error}"})
        raise
    finally:
        (args.result_dir / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
        server.should_exit = True
        thread.join(timeout=5)
        observer.close()
        adapter_log_path = adapter_log.path
        adapter_log.close()
        node.destroy_node()
        rclpy.shutdown()
        print(json.dumps({**summary, "adapter_log": str(adapter_log_path)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
