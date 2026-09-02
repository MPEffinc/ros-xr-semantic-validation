#!/usr/bin/env python3

"""Exercise generated HTTPS, production WSS, and experiment WSS on loopback."""

import asyncio
import hashlib
import json
import os
import socket
import ssl
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path


VALIDATION_ROOT = Path(__file__).resolve().parents[1]
SERVER = VALIDATION_ROOT / "harness" / "spes_hardware_server.py"


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.bind(("127.0.0.1", 0))
        return int(listener.getsockname()[1])


def pose_message() -> dict:
    return {
        "type": "pose",
        "data": {
            "position": {"x": 0.0, "y": 0.0, "z": 0.0},
            "orientation": {"x": 0.0, "y": 0.0, "z": 0.0, "w": 1.0},
            "move": True,
            "gripper": "open",
            "fps": 72,
            "scale": 1.0,
            "reservedButtonA": False,
            "reservedButtonB": False,
            "device": "VR",
            "message": "endpoint selftest",
        },
    }


async def websocket_roundtrip(port: int, context: ssl.SSLContext) -> dict:
    import websockets

    async with websockets.connect(f"wss://127.0.0.1:{port}/experiment", ssl=context) as sideband:
        hello = json.loads(await asyncio.wait_for(sideband.recv(), timeout=3.0))
        assert hello["type"] == "experiment_hello"
        await sideband.send(
            json.dumps(
                {
                    "type": "experiment_event",
                    "data": {
                        "schema": "spes-quest-operator-v1",
                        "event_type": "endpoint_selftest",
                        "sample_kind": "SEMANTIC_EVENT",
                    },
                }
            )
        )
        async with websockets.connect(f"wss://127.0.0.1:{port}/ws", ssl=context) as production:
            await production.send(json.dumps(pose_message()))
            acknowledgement = json.loads(await asyncio.wait_for(sideband.recv(), timeout=3.0))
            assert acknowledgement["type"] == "server_ack"
            assert acknowledgement["server_update_index"] == 1
            assert acknowledgement["callback_emitted"] is True
            return acknowledgement


def main() -> int:
    port = free_port()
    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    with tempfile.TemporaryDirectory(prefix="spes_live_endpoint_") as temp_dir:
        result_root = Path(temp_dir) / "runs"
        command = [
            sys.executable,
            str(SERVER),
            "--no-console",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
            "--run-id",
            "endpoint_selftest",
            "--result-root",
            str(result_root),
        ]
        process = subprocess.Popen(
            command,
            env=os.environ.copy(),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        page = None
        try:
            deadline = time.monotonic() + 12.0
            while time.monotonic() < deadline:
                if process.poll() is not None:
                    stdout, stderr = process.communicate()
                    raise RuntimeError(f"server exited early: stdout={stdout!r} stderr={stderr!r}")
                try:
                    with urllib.request.urlopen(
                        f"https://127.0.0.1:{port}/", context=context, timeout=1.0
                    ) as response:
                        page = response.read().decode("utf-8")
                    break
                except Exception:
                    time.sleep(0.1)
            if page is None:
                raise TimeoutError("HTTPS endpoint did not become ready")
            assert "/assets/quest-operator.js" in page
            acknowledgement = asyncio.run(websocket_roundtrip(port, context))
            time.sleep(0.2)
            with socket.create_connection(("127.0.0.1", port), timeout=2.0) as raw_socket:
                with context.wrap_socket(raw_socket, server_hostname="127.0.0.1") as tls_socket:
                    certificate_sha256 = hashlib.sha256(tls_socket.getpeercert(binary_form=True)).hexdigest()
        finally:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=8.0)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=3.0)
        experiment_log = result_root / "endpoint_selftest" / "experiment.jsonl"
        records = [json.loads(line) for line in experiment_log.read_text(encoding="utf-8").splitlines()]
        assert any(record.get("event_type") == "endpoint_selftest" for record in records)
        print(
            json.dumps(
                {
                    "event": "spes_live_endpoint_selftest",
                    "https_page": "PASS",
                    "tls_certificate_sha256": certificate_sha256,
                    "production_wss_pose": "PASS",
                    "experiment_wss_event": "PASS",
                    "server_ack": "PASS",
                    "server_update_index": acknowledgement["server_update_index"],
                    "result": "PASS",
                },
                sort_keys=True,
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
