#!/usr/bin/env python3
"""Inert local stand-in for the Reachy daemon target WebSocket endpoint.

SAFETY CONTRACT
---------------
This server is a *sink*. It accepts a WebSocket upgrade on the
`/api/move/ws/set_target` path, logs every received frame verbatim to JSONL,
and does nothing else. It has:

  * no robot, daemon, serial, CAN, motor, or actuator code path;
  * no outbound socket of any kind (it never forwards anything anywhere);
  * a hard bind guard: it refuses to bind to any address other than a
    loopback address.

It exists so that a Reachy teleop client can be observed without any real
Reachy daemon or robot being contacted. Receiving a frame here is
`TRANSPORT_SENT` evidence at most; it is never a robot command and must never
be reported as one.

Protocol
--------
Mimics only what the pinned client needs:
  - HTTP GET + `Upgrade: websocket` on `/api/move/ws/set_target`
    (`ReachyDaemonTargetWebSocketClient.cs:18` DefaultTargetPath,
     `Assets/Config/ReachyTeleopConfig.asset:15`
     `daemonTargetWebSocketUrl: ws://localhost:8000/api/move/ws/set_target`)
  - RFC 6455 text/binary/ping/close frame handling, server->client silence
    apart from pong and close echo.
  - Optional `--http-ok-paths` so that plain HTTP probes (the client's
    `/api` wake/sound calls) get a 200 with an empty JSON body instead of a
    connection error. Those handlers also do nothing but log.

Expected wire payload (logged, never interpreted as a command):
  `ReachyDaemonPayloadDtos.cs:15-22`
  {"target_head_pose": {"m": [16 floats]},
   "target_antennas": [right, left],
   "target_body_yaw": radians}

Usage:
  python3 reachy_inert_target_endpoint.py --port 8000 --log-dir <dir>
"""

import argparse
import base64
import hashlib
import ipaddress
import json
import os
import socket
import socketserver
import struct
import sys
import threading
import time

GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
DEFAULT_TARGET_PATH = "/api/move/ws/set_target"

_log_lock = threading.Lock()
_log_fh = None
_counters = {"connections": 0, "frames": 0, "bytes": 0, "http_requests": 0}


def log_event(**kw):
    rec = {"wall_ns": time.time_ns(), "monotonic_ns": time.monotonic_ns()}
    rec.update(kw)
    line = json.dumps(rec)
    with _log_lock:
        _log_fh.write(line + "\n")
        _log_fh.flush()
    print(line, flush=True)


def assert_loopback(host: str):
    try:
        addr = ipaddress.ip_address(host)
    except ValueError:
        raise SystemExit(f"REFUSED: bind host {host!r} is not a literal IP address")
    if not addr.is_loopback:
        raise SystemExit(
            f"REFUSED: bind host {host} is not loopback. This endpoint may only "
            f"ever be reachable from the local machine.")


def recv_exact(sock, n):
    buf = b""
    while len(buf) < n:
        chunk = sock.recv(n - len(buf))
        if not chunk:
            return None
        buf += chunk
    return buf


def read_frame(sock):
    """Return (opcode, payload_bytes) or None on clean EOF."""
    hdr = recv_exact(sock, 2)
    if hdr is None:
        return None
    b0, b1 = hdr[0], hdr[1]
    opcode = b0 & 0x0F
    masked = bool(b1 & 0x80)
    length = b1 & 0x7F
    if length == 126:
        ext = recv_exact(sock, 2)
        if ext is None:
            return None
        length = struct.unpack("!H", ext)[0]
    elif length == 127:
        ext = recv_exact(sock, 8)
        if ext is None:
            return None
        length = struct.unpack("!Q", ext)[0]
    mask = None
    if masked:
        mask = recv_exact(sock, 4)
        if mask is None:
            return None
    payload = recv_exact(sock, length) if length else b""
    if payload is None:
        return None
    if masked:
        payload = bytes(payload[i] ^ mask[i % 4] for i in range(len(payload)))
    return opcode, payload


def send_frame(sock, opcode, payload=b""):
    header = bytes([0x80 | opcode])
    n = len(payload)
    if n < 126:
        header += bytes([n])
    elif n < 1 << 16:
        header += bytes([126]) + struct.pack("!H", n)
    else:
        header += bytes([127]) + struct.pack("!Q", n)
    sock.sendall(header + payload)


class Handler(socketserver.StreamRequestHandler):
    timeout = 300
    target_path = DEFAULT_TARGET_PATH
    http_ok_paths = True

    def handle(self):
        peer = f"{self.client_address[0]}:{self.client_address[1]}"
        try:
            request_line = self.rfile.readline(65536).decode("latin-1").strip()
        except Exception:
            return
        if not request_line:
            return
        headers = {}
        while True:
            line = self.rfile.readline(65536).decode("latin-1")
            if line in ("\r\n", "\n", ""):
                break
            if ":" in line:
                k, v = line.split(":", 1)
                headers[k.strip().lower()] = v.strip()

        parts = request_line.split()
        method = parts[0] if parts else ""
        path = parts[1] if len(parts) > 1 else ""

        is_upgrade = headers.get("upgrade", "").lower() == "websocket"
        if not is_upgrade:
            _counters["http_requests"] += 1
            body = b""
            clen = int(headers.get("content-length", "0") or 0)
            if clen:
                body = self.rfile.read(clen)
            log_event(event="HTTP_REQUEST", peer=peer, method=method, path=path,
                      headers=headers, body=body.decode("utf-8", "replace"),
                      action="LOGGED_ONLY_NOTHING_COMMANDED")
            status = b"200 OK" if self.http_ok_paths else b"404 Not Found"
            payload = b"{}"
            self.wfile.write(b"HTTP/1.1 " + status +
                             b"\r\nContent-Type: application/json\r\nContent-Length: " +
                             str(len(payload)).encode() + b"\r\nConnection: close\r\n\r\n" +
                             payload)
            return

        key = headers.get("sec-websocket-key", "")
        accept = base64.b64encode(
            hashlib.sha1((key + GUID).encode()).digest()).decode()
        path_match = path.split("?")[0] == self.target_path
        _counters["connections"] += 1
        conn_id = _counters["connections"]
        log_event(event="WS_UPGRADE", peer=peer, conn_id=conn_id, path=path,
                  path_matches_pinned_target_path=path_match,
                  request_line=request_line, headers=headers)
        self.wfile.write(
            b"HTTP/1.1 101 Switching Protocols\r\n"
            b"Upgrade: websocket\r\nConnection: Upgrade\r\n"
            b"Sec-WebSocket-Accept: " + accept.encode() + b"\r\n\r\n")

        sock = self.connection
        seq = 0
        try:
            while True:
                frame = read_frame(sock)
                if frame is None:
                    log_event(event="WS_EOF", conn_id=conn_id, peer=peer,
                              frames_on_connection=seq)
                    break
                opcode, payload = frame
                if opcode == 0x8:  # close
                    log_event(event="WS_CLOSE", conn_id=conn_id, peer=peer,
                              frames_on_connection=seq)
                    try:
                        send_frame(sock, 0x8, payload[:2])
                    except Exception:
                        pass
                    break
                if opcode == 0x9:  # ping
                    log_event(event="WS_PING", conn_id=conn_id, peer=peer)
                    send_frame(sock, 0xA, payload)
                    continue
                if opcode == 0xA:
                    continue
                seq += 1
                _counters["frames"] += 1
                _counters["bytes"] += len(payload)
                text = payload.decode("utf-8", "replace")
                parsed = None
                try:
                    parsed = json.loads(text)
                except Exception:
                    parsed = None
                log_event(event="WS_FRAME", conn_id=conn_id, peer=peer,
                          conn_frame_seq=seq, global_frame_seq=_counters["frames"],
                          opcode=opcode, byte_len=len(payload), raw_text=text,
                          parsed_json=parsed,
                          action="LOGGED_ONLY_NOTHING_COMMANDED")
        except (ConnectionResetError, socket.timeout, OSError) as exc:
            log_event(event="WS_ERROR", conn_id=conn_id, peer=peer,
                      error=type(exc).__name__, detail=str(exc))


class Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--path", default=DEFAULT_TARGET_PATH)
    ap.add_argument("--log-dir", required=True)
    ap.add_argument("--duration", type=float, default=0.0,
                    help="seconds to run; 0 = until interrupted")
    args = ap.parse_args()

    assert_loopback(args.host)
    os.makedirs(args.log_dir, exist_ok=True)

    global _log_fh
    _log_fh = open(os.path.join(args.log_dir, "inert_endpoint.jsonl"), "a")

    Handler.target_path = args.path
    srv = Server((args.host, args.port), Handler)
    log_event(event="ENDPOINT_START", host=args.host, port=args.port,
              path=args.path, pid=os.getpid(),
              contract="INERT_SINK: logs frames, commands nothing, no outbound socket")

    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    try:
        if args.duration > 0:
            time.sleep(args.duration)
        else:
            while True:
                time.sleep(3600)
    except KeyboardInterrupt:
        pass
    finally:
        srv.shutdown()
        log_event(event="ENDPOINT_STOP", counters=dict(_counters))
        _log_fh.close()


if __name__ == "__main__":
    sys.exit(main())
