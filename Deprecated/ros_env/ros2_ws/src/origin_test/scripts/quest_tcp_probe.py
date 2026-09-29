#!/usr/bin/env python3

import argparse
import json
import socket
import struct
import sys
import time


MAX_FRAME_BYTES = 1024 * 1024


def recv_exact(connection, size):
    chunks = bytearray()
    while len(chunks) < size:
        chunk = connection.recv(size - len(chunks))
        if not chunk:
            raise ConnectionError("connection closed while reading frame")
        chunks.extend(chunk)
    return bytes(chunks)


def read_frame(connection):
    destination_size = struct.unpack("<I", recv_exact(connection, 4))[0]
    if destination_size > MAX_FRAME_BYTES:
        raise ValueError(f"destination too large: {destination_size}")
    destination = recv_exact(connection, destination_size).decode("utf-8").rstrip("\x00")
    body_size = struct.unpack("<I", recv_exact(connection, 4))[0]
    if body_size > MAX_FRAME_BYTES:
        raise ValueError(f"body too large: {body_size}")
    return destination, recv_exact(connection, body_size)


def frame(destination, body):
    destination_bytes = destination.encode("utf-8")
    return (
        struct.pack("<I", len(destination_bytes))
        + destination_bytes
        + struct.pack("<I", len(body))
        + body
    )


def command_frame(destination, parameters):
    return frame(destination, json.dumps(parameters, separators=(",", ":")).encode("utf-8"))


def twist_payload(linear_x, angular_z):
    return struct.pack("<6d", linear_x, 0.0, 0.0, 0.0, 0.0, angular_z)


def connect_with_retry(args):
    deadline = time.monotonic() + args.connect_timeout
    last_error = None
    while time.monotonic() < deadline:
        try:
            return socket.create_connection((args.host, args.port), timeout=2.0)
        except OSError as error:
            last_error = error
            time.sleep(0.1)
    raise ConnectionError(f"connect timeout: {last_error!r}")


def run(args):
    connection = connect_with_retry(args)
    connection.settimeout(args.read_timeout)
    print(
        f"QUEST_TCP_CONNECTED client={args.client_id} endpoint={args.host}:{args.port}",
        flush=True,
    )

    try:
        destination, body = read_frame(connection)
        if destination != "__handshake":
            raise ValueError(f"expected __handshake, received {destination!r}")
        handshake = json.loads(body.decode("utf-8"))
        print(
            f"QUEST_TCP_HANDSHAKE client={args.client_id} "
            f"version={handshake.get('version', '-')} metadata={handshake.get('metadata', '-')}",
            flush=True,
        )

        if not args.skip_register:
            registration = {
                "topic": args.topic,
                "message_name": args.message_type,
                "queue_size": 10,
                "latch": False,
            }
            connection.sendall(command_frame("__publish", registration))
            print(
                f"QUEST_TCP_REGISTERED client={args.client_id} topic={args.topic} "
                f"type={args.message_type}",
                flush=True,
            )
            time.sleep(args.discovery_wait)
        else:
            print(
                f"QUEST_TCP_REGISTER_SKIPPED client={args.client_id} topic={args.topic}",
                flush=True,
            )

        time.sleep(args.pre_send_delay)
        payload = twist_payload(args.linear_x, args.angular_z)
        for sequence in range(1, args.count + 1):
            connection.sendall(frame(args.topic, payload))
            print(
                f"QUEST_TCP_SENT client={args.client_id} sequence={sequence} "
                f"linear_x={args.linear_x:.3f} angular_z={args.angular_z:.3f}",
                flush=True,
            )
            time.sleep(args.interval)

        time.sleep(args.hold_seconds)
        return 0
    except Exception as error:
        print(f"QUEST_TCP_FAILED client={args.client_id} error={error!r}", flush=True)
        return 20
    finally:
        if args.disconnect == "rst":
            try:
                connection.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, struct.pack("ii", 1, 0))
            except OSError:
                pass
        else:
            try:
                connection.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
        connection.close()
        print(
            f"QUEST_TCP_CLOSED client={args.client_id} mode={args.disconnect}",
            flush=True,
        )


def build_parser():
    parser = argparse.ArgumentParser(description="Quest2ROS2 ROS-TCP protocol probe")
    parser.add_argument("--client-id", required=True)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=10000)
    parser.add_argument("--topic", default="q2r_right_hand_twist")
    parser.add_argument("--message-type", default="geometry_msgs/Twist")
    parser.add_argument("--linear-x", type=float, required=True)
    parser.add_argument("--angular-z", type=float, default=0.0)
    parser.add_argument("--count", type=int, default=4)
    parser.add_argument("--interval", type=float, default=0.25)
    parser.add_argument("--discovery-wait", type=float, default=1.0)
    parser.add_argument("--pre-send-delay", type=float, default=0.0)
    parser.add_argument("--hold-seconds", type=float, default=0.0)
    parser.add_argument("--connect-timeout", type=float, default=10.0)
    parser.add_argument("--read-timeout", type=float, default=5.0)
    parser.add_argument("--skip-register", action="store_true")
    parser.add_argument("--disconnect", choices=("normal", "rst"), default="normal")
    return parser


def main():
    return run(build_parser().parse_args())


if __name__ == "__main__":
    sys.exit(main())
