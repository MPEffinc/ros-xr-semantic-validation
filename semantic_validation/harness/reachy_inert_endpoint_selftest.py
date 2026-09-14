#!/usr/bin/env python3
"""Self-test for `reachy_inert_target_endpoint.py`.

SCOPE WARNING
-------------
This is a *harness self-test only*. The frames it sends are written by this
research harness, NOT produced by the pinned Unity/C# client
(`ReachyHeadCommandPublisher` -> `ReachyDaemonTargetAdapter` ->
`ReachyDaemonTargetWebSocketClient`). It therefore proves only that the inert
endpoint accepts a WebSocket upgrade on the pinned target path and records
frames verbatim. It is NOT evidence about the Reachy client's validity gate,
and it must never be reported as Reachy runtime evidence.

The payload shape is copied from the pinned DTOs so that the endpoint's
recording format is exercised realistically:
  `Assets/Scripts/Runtime/Reachy/ReachyDaemonPayloadDtos.cs:15-22`
"""

import argparse
import base64
import json
import os
import socket
import struct
import time

GUID_ACCEPT_LEN = 28


def ws_connect(host, port, path):
    sock = socket.create_connection((host, port), timeout=5)
    key = base64.b64encode(os.urandom(16)).decode()
    req = (f"GET {path} HTTP/1.1\r\nHost: {host}:{port}\r\n"
           f"Upgrade: websocket\r\nConnection: Upgrade\r\n"
           f"Sec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n")
    sock.sendall(req.encode())
    buf = b""
    while b"\r\n\r\n" not in buf:
        chunk = sock.recv(4096)
        if not chunk:
            raise RuntimeError("server closed during handshake")
        buf += chunk
    status = buf.split(b"\r\n", 1)[0].decode()
    if b"101" not in buf.split(b"\r\n", 1)[0]:
        raise RuntimeError(f"handshake failed: {status}")
    return sock, status


def ws_send_text(sock, text):
    payload = text.encode()
    mask = os.urandom(4)
    masked = bytes(payload[i] ^ mask[i % 4] for i in range(len(payload)))
    n = len(payload)
    header = bytes([0x81])
    if n < 126:
        header += bytes([0x80 | n])
    elif n < 1 << 16:
        header += bytes([0x80 | 126]) + struct.pack("!H", n)
    else:
        header += bytes([0x80 | 127]) + struct.pack("!Q", n)
    sock.sendall(header + mask + masked)


def ws_close(sock):
    mask = os.urandom(4)
    payload = struct.pack("!H", 1000)
    masked = bytes(payload[i] ^ mask[i % 4] for i in range(len(payload)))
    sock.sendall(bytes([0x88, 0x80 | len(payload)]) + mask + masked)
    sock.close()


def target_frame(yaw_rad: float, seq: int):
    m = [1.0, 0.0, 0.0, 0.0,
         0.0, 1.0, 0.0, 0.0,
         0.0, 0.0, 1.0, float(seq) / 1000.0,
         0.0, 0.0, 0.0, 1.0]
    return {"target_head_pose": {"m": m},
            "target_antennas": [0.0, 0.0],
            "target_body_yaw": yaw_rad}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--path", default="/api/move/ws/set_target")
    ap.add_argument("--frames", type=int, default=20)
    ap.add_argument("--rate-hz", type=float, default=20.0)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    result = {"role": "HARNESS_SELFTEST_ONLY",
              "payload_provenance": "SYNTHETIC_HARNESS_AUTHORED_NOT_PINNED_UNITY_CLIENT",
              "steps": []}

    sock, status = ws_connect(args.host, args.port, args.path)
    result["steps"].append({"step": "connect", "handshake_status": status})

    period = 1.0 / args.rate_hz
    sent = 0
    t0 = time.monotonic_ns()
    for i in range(args.frames):
        ws_send_text(sock, json.dumps(target_frame(0.1 * i, i)))
        sent += 1
        time.sleep(period)
    t1 = time.monotonic_ns()
    result["steps"].append({"step": "send_target_frames", "sent": sent,
                            "window_ns": t1 - t0})

    ws_close(sock)
    result["steps"].append({"step": "close"})
    time.sleep(0.3)

    # reconnect check
    sock2, status2 = ws_connect(args.host, args.port, args.path)
    ws_send_text(sock2, json.dumps(target_frame(0.0, 9999)))
    sent += 1
    time.sleep(0.3)
    ws_close(sock2)
    result["steps"].append({"step": "reconnect_and_send", "handshake_status": status2})
    result["total_frames_sent"] = sent

    with open(args.out, "w") as fh:
        json.dump(result, fh, indent=2)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
