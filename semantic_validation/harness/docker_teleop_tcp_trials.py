#!/usr/bin/env python3
"""Synthetic newline-JSON sender for the pinned Docker_Teleop TCP boundary.

This is a research harness only.  It reproduces the schema emitted by
``UnityApp/Assets/Scripts/HandPoseSender.cs`` without modifying the upstream
Unity or ROS application.  It deliberately writes the wire boundary upstream
of ``quest_controller_receiver``.
"""

from __future__ import annotations

import argparse
import json
import socket
import time


def packet(*, tracked: bool, timestamp: float, x: float, grip: bool = True) -> bytes:
    hand = {
        "isTracked": tracked,
        "pos": {"x": x, "y": 0.20, "z": 0.30},
        "rot": {"x": 0.0, "y": 0.0, "z": 0.0, "w": 1.0},
    }
    payload = {
        "timestamp": timestamp,
        "left_hand": hand,
        "right_hand": hand,
        "controls": {
            "teleop_enable": grip,
            "right_teleop_enable": grip,
            "grip_value": 1.0 if grip else 0.0,
            "source": "research_synthetic_tcp",
        },
    }
    return (json.dumps(payload, separators=(",", ":")) + "\n").encode("utf-8")


def send_for(sock: socket.socket, *, tracked: bool, timestamp: float, x: float, seconds: float) -> None:
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        sock.sendall(packet(tracked=tracked, timestamp=timestamp, x=x))
        time.sleep(0.05)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=15005)
    parser.add_argument("--stall-sec", type=float, default=0.60)
    args = parser.parse_args()

    now = time.time()
    first = socket.create_connection((args.host, args.port), timeout=3.0)
    print("D1_BASELINE_START", flush=True)
    send_for(first, tracked=True, timestamp=now, x=0.10, seconds=0.60)
    send_for(first, tracked=True, timestamp=now + 0.60, x=0.35, seconds=2.00)
    print("D1_BASELINE_END", flush=True)

    print("D2_TRACKED_FALSE_START", flush=True)
    send_for(first, tracked=False, timestamp=now + 2.60, x=0.35, seconds=1.20)
    print("D2_TRACKED_FALSE_END", flush=True)

    print("D3_STALL_START", flush=True)
    time.sleep(args.stall_sec)
    print("D3_STALL_END", flush=True)

    print("D4_OLD_TIMESTAMP_START timestamp=1.0 pose_x=0.45", flush=True)
    send_for(first, tracked=True, timestamp=1.0, x=0.45, seconds=0.70)
    print("D4_OLD_TIMESTAMP_END", flush=True)

    print("D5_SECOND_CLIENT_START", flush=True)
    second = socket.create_connection((args.host, args.port), timeout=3.0)
    send_for(second, tracked=True, timestamp=now + 3.0, x=0.55, seconds=0.35)
    print("D5_SECOND_CLIENT_SENT_WHILE_FIRST_OPEN", flush=True)
    first.close()
    send_for(second, tracked=True, timestamp=now + 3.4, x=0.55, seconds=0.70)
    second.close()
    print("D5_SECOND_CLIENT_END", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
