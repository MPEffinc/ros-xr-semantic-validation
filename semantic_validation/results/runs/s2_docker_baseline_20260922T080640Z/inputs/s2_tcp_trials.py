#!/usr/bin/env python3
"""S2 synthetic TCP input only; vendor receiver/mapper/bridge are unmodified."""
from __future__ import annotations

import argparse
import json
import socket
import time
from pathlib import Path


def payload(trial: str, *, tracked: bool, source_timestamp: float, x: float) -> dict:
    hand = {"isTracked": tracked, "pos": {"x": x, "y": 0.20, "z": 0.30},
            "rot": {"x": 0.0, "y": 0.0, "z": 0.0, "w": 1.0}}
    return {"timestamp": source_timestamp, "left_hand": hand, "right_hand": hand,
            "controls": {"teleop_enable": True, "right_teleop_enable": True,
                         "grip_value": 1.0, "source": "s2_synthetic_tcp", "trial_id": trial}}


def marker(out: Path, trial: str, event: str, **fields: object) -> None:
    rec = {"record_type": "marker", "trial_id": trial, "event": event,
           "wall_time_ns": time.time_ns(), "monotonic_ns": time.monotonic_ns(), **fields}
    with out.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(rec, sort_keys=True) + "\n")
    print(json.dumps(rec, sort_keys=True), flush=True)


def send_for(sock: socket.socket, out: Path, trial: str, *, tracked: bool, source_timestamp: float,
             x: float, seconds: float) -> None:
    marker(out, trial, "START", tracked=tracked, source_timestamp=source_timestamp, x=x, seconds=seconds)
    deadline = time.monotonic() + seconds
    sequence = 0
    while time.monotonic() < deadline:
        message = payload(trial, tracked=tracked, source_timestamp=source_timestamp, x=x)
        wire = (json.dumps(message, separators=(",", ":")) + "\n").encode("utf-8")
        sent_wall_ns = time.time_ns()
        sent_monotonic_ns = time.monotonic_ns()
        sock.sendall(wire)
        rec = {"record_type": "send", "trial_id": trial, "sequence": sequence,
               "sent_wall_ns": sent_wall_ns, "sent_monotonic_ns": sent_monotonic_ns,
               "tracked": tracked, "teleop": True, "source_timestamp": source_timestamp,
               "x": x, "wire_utf8": wire.decode("utf-8").rstrip("\n")}
        with out.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(rec, sort_keys=True) + "\n")
        sequence += 1
        time.sleep(0.05)
    marker(out, trial, "END", sends=sequence)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=15006)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)

    marker(args.output, "D0", "START", condition="no_control_idle", seconds=2.0)
    time.sleep(2.0)
    marker(args.output, "D0", "END")

    current = time.time()
    first = socket.create_connection((args.host, args.port), timeout=5.0)
    marker(args.output, "CONNECTION_1", "CONNECTED")
    send_for(first, args.output, "D1_REFERENCE", tracked=True, source_timestamp=current, x=0.10, seconds=0.8)
    send_for(first, args.output, "D1_ACTIVE", tracked=True, source_timestamp=current + 0.8, x=0.35, seconds=1.2)
    send_for(first, args.output, "D2_TRACKING_FALSE", tracked=False, source_timestamp=current + 2.0, x=0.35, seconds=1.2)
    marker(args.output, "D3_SENDER_STALL", "START", condition="no_bytes_after_tracked_false", seconds=0.75)
    time.sleep(0.75)
    marker(args.output, "D3_SENDER_STALL", "END")

    fresh = time.time()
    send_for(first, args.output, "D4_FRESH_REFERENCE", tracked=True, source_timestamp=fresh, x=0.12, seconds=0.8)
    send_for(first, args.output, "D4_FRESH_ACTIVE", tracked=True, source_timestamp=fresh + 0.8, x=0.37, seconds=1.0)
    marker(args.output, "D4_RESET_BEFORE_OLD", "START", seconds=0.5)
    time.sleep(0.5)
    marker(args.output, "D4_RESET_BEFORE_OLD", "END")
    send_for(first, args.output, "D4_OLD_REFERENCE", tracked=True, source_timestamp=1.0, x=0.16, seconds=0.8)
    send_for(first, args.output, "D4_OLD_ACTIVE", tracked=True, source_timestamp=1.0, x=0.41, seconds=1.0)

    marker(args.output, "D5_DISCONNECT", "START")
    first.close()
    marker(args.output, "CONNECTION_1", "CLOSED")
    time.sleep(0.6)
    second = socket.create_connection((args.host, args.port), timeout=5.0)
    marker(args.output, "CONNECTION_2", "CONNECTED")
    reconnect = time.time()
    send_for(second, args.output, "D5_RECONNECT_REFERENCE", tracked=True, source_timestamp=reconnect, x=0.24, seconds=0.8)
    send_for(second, args.output, "D5_RECONNECT_ACTIVE", tracked=True, source_timestamp=reconnect + 0.8, x=0.50, seconds=1.0)
    second.close()
    marker(args.output, "CONNECTION_2", "CLOSED")
    marker(args.output, "POST_TRIAL", "START", seconds=0.8)
    time.sleep(0.8)
    marker(args.output, "POST_TRIAL", "END")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
