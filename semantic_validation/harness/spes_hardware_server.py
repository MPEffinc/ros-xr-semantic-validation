#!/usr/bin/env python3

"""Observation-only Spes server with a separate Quest experiment side-band."""

import argparse
import asyncio
import json
import logging
import math
import re
import signal
import sys
import tempfile
import threading
import time
from datetime import datetime, timezone
from pathlib import Path


VALIDATION_ROOT = Path(__file__).resolve().parents[1]
TARGET_ROOT = VALIDATION_ROOT / "targets" / "spes_teleop"
TARGET_PACKAGE = TARGET_ROOT / "teleop"
DEFAULT_FRONTEND = VALIDATION_ROOT / "instrumented" / "spes_frontend"
DEFAULT_RESULT_ROOT = VALIDATION_ROOT / "logs" / "quest_hw"
EXPECTED_COMMIT = "c5d808155a87b584d6147a5943d4b87c34c92db0"
sys.path.insert(0, str(TARGET_ROOT))

import numpy as np  # noqa: E402
import transforms3d as t3d  # noqa: E402
import uvicorn  # noqa: E402
from fastapi import WebSocket, WebSocketDisconnect  # noqa: E402
from teleop import Teleop, get_local_ip  # noqa: E402


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def json_safe(value):
    if isinstance(value, dict):
        return {str(key): json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(item) for item in value]
    if isinstance(value, np.generic):
        return value.item()
    return value


class JsonlWriter:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if self.path.exists():
            raise FileExistsError(f"refusing to overwrite existing log: {self.path}")
        self.path.touch()
        self.lock = threading.Lock()

    def append(self, record: dict) -> None:
        rendered = json.dumps(json_safe(record), sort_keys=True, separators=(",", ":"))
        with self.lock:
            with self.path.open("a", encoding="utf-8") as stream:
                stream.write(rendered + "\n")


class ExperimentHub:
    """Separate WSS for operator events and observation-only server ACKs."""

    def __init__(self, writer: JsonlWriter, run_id: str):
        self.writer = writer
        self.run_id = run_id
        self.clients: set[WebSocket] = set()
        self.loop = None

    async def endpoint(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.loop = asyncio.get_running_loop()
        self.clients.add(websocket)
        self.writer.append(
            {
                "event": "experiment_connection",
                "state": "connected",
                "run_id": self.run_id,
                "server_receive_monotonic_ns": time.monotonic_ns(),
                "wall_utc": utc_now(),
            }
        )
        await websocket.send_text(
            json.dumps(
                {
                    "type": "experiment_hello",
                    "schema": "spes-quest-experiment-sideband-v1",
                    "run_id": self.run_id,
                }
            )
        )
        try:
            while True:
                payload = await websocket.receive_text()
                receive_ns = time.monotonic_ns()
                try:
                    message = json.loads(payload)
                    parse_error = None
                except json.JSONDecodeError as error:
                    message = {"raw": payload}
                    parse_error = str(error)
                if message.get("type") == "experiment_event":
                    record = message.get("data")
                    if not isinstance(record, dict):
                        record = {"raw": record}
                    self.writer.append(
                        {
                            "event": "quest_operator_event",
                            "run_id": self.run_id,
                            "server_receive_monotonic_ns": receive_ns,
                            "server_wall_utc": utc_now(),
                            "parse_error": parse_error,
                            **record,
                        }
                    )
                elif message.get("type") == "ping":
                    await websocket.send_text(json.dumps({"type": "pong", "run_id": self.run_id}))
                else:
                    self.writer.append(
                        {
                            "event": "experiment_unknown_message",
                            "run_id": self.run_id,
                            "server_receive_monotonic_ns": receive_ns,
                            "wall_utc": utc_now(),
                            "parse_error": parse_error,
                        }
                    )
        except WebSocketDisconnect:
            pass
        finally:
            self.clients.discard(websocket)
            self.writer.append(
                {
                    "event": "experiment_connection",
                    "state": "disconnected",
                    "run_id": self.run_id,
                    "server_receive_monotonic_ns": time.monotonic_ns(),
                    "wall_utc": utc_now(),
                }
            )

    async def _broadcast(self, message: dict) -> None:
        serialized = json.dumps(json_safe(message), separators=(",", ":"))
        broken = []
        for client in list(self.clients):
            try:
                await client.send_text(serialized)
            except Exception:
                broken.append(client)
        for client in broken:
            self.clients.discard(client)

    def publish(self, message: dict) -> None:
        if self.loop is None or not self.clients:
            return

        def schedule() -> None:
            asyncio.create_task(self._broadcast(message))

        self.loop.call_soon_threadsafe(schedule)


def transform_record(pose: np.ndarray) -> dict:
    quaternion = t3d.quaternions.mat2quat(pose[:3, :3])
    return {
        "position": {
            "x": float(pose[0, 3]),
            "y": float(pose[1, 3]),
            "z": float(pose[2, 3]),
        },
        "orientation": {
            "x": float(quaternion[1]),
            "y": float(quaternion[2]),
            "z": float(quaternion[3]),
            "w": float(quaternion[0]),
        },
    }


def target_delta(previous: np.ndarray | None, current: np.ndarray) -> dict | None:
    if previous is None:
        return None
    relative_rotation = previous[:3, :3].T @ current[:3, :3]
    cosine = np.clip((np.trace(relative_rotation) - 1.0) / 2.0, -1.0, 1.0)
    return {
        "linear_m": float(np.linalg.norm(current[:3, 3] - previous[:3, 3])),
        "angular_rad": float(math.acos(float(cosine))),
    }


class TeleopLogHandler(logging.Handler):
    def __init__(self, observer):
        super().__init__(level=logging.INFO)
        self.observer = observer

    def emit(self, record: logging.LogRecord) -> None:
        try:
            message = record.getMessage()
            if message == "Pose jump detected, resetting the pose":
                self.observer.note_jump_warning()
            elif message.startswith("Received log message: "):
                self.observer.note_frontend_log(message.removeprefix("Received log message: "))
            elif message in {"Client connected", "Client disconnected"}:
                self.observer.note_connection(message)
        except Exception:
            self.handleError(record)


class ServerObserver:
    """Wrap Teleop.__update and subscribe without changing its control calculation."""

    def __init__(self, teleop: Teleop, writer: JsonlWriter, ack_publisher=None):
        self.teleop = teleop
        self.writer = writer
        self.original_update = teleop._Teleop__update
        self.update_index = 0
        self.last_update_index = None
        self.last_target = None
        self.current_update = None
        self.callback_count = 0
        self.last_callback_time = None
        self.connection_generation = 0
        self.active_connection_generation = None
        self.ack_publisher = ack_publisher or (lambda _record: None)
        self.log_handler = TeleopLogHandler(self)
        logging.getLogger("teleop").addHandler(self.log_handler)
        teleop.subscribe(self._subscriber_callback)
        teleop._Teleop__update = self._observed_update

    def close(self) -> None:
        logging.getLogger("teleop").removeHandler(self.log_handler)

    def _private(self, suffix: str):
        return getattr(self.teleop, f"_Teleop__{suffix}")

    def _subscriber_callback(self, pose: np.ndarray, message: dict) -> None:
        if self.current_update is not None:
            self.current_update["callback_emitted"] = True
            self.current_update["callback_target"] = np.array(pose, copy=True)
            self.callback_count += 1
            self.last_callback_time = utc_now()

    def note_jump_warning(self) -> None:
        if self.current_update is not None:
            self.current_update["pose_jump_warning"] = True

    def note_connection(self, message: str) -> None:
        if message == "Client connected":
            self.connection_generation += 1
            self.active_connection_generation = self.connection_generation
        self.writer.append(
            {
                "event": "server_connection",
                "state": "connected" if message == "Client connected" else "disconnected",
                "server_connection_generation": self.active_connection_generation,
                "server_receive_monotonic_ns": time.monotonic_ns(),
                "wall_utc": utc_now(),
            }
        )
        if message == "Client disconnected":
            self.active_connection_generation = None

    def note_frontend_log(self, payload: str) -> None:
        receive_ns = time.monotonic_ns()
        try:
            frontend = json.loads(payload)
            parse_error = None
        except json.JSONDecodeError as error:
            frontend = {"raw": payload}
            parse_error = str(error)
        control_packet_index = frontend.get("control_packet_index")
        if control_packet_index is None:
            correlation = "NO_CONTROL_INDEX"
            correlated_update = self.last_update_index
        elif self.last_update_index == control_packet_index:
            correlation = "MATCH_LATEST_UPDATE"
            correlated_update = self.last_update_index
        else:
            correlation = "ORDER_MISMATCH"
            correlated_update = self.last_update_index
        self.writer.append(
            {
                "event": "frontend_semantic",
                "server_receive_monotonic_ns": receive_ns,
                "wall_utc": utc_now(),
                "frontend_semantic_event_sequence": frontend.get("semantic_event_sequence"),
                "frontend_control_packet_index": control_packet_index,
                "correlated_server_update_index": correlated_update,
                "correlation_status": correlation,
                "server_connection_generation": self.active_connection_generation,
                "parse_error": parse_error,
                "frontend": frontend,
            }
        )

    def _observed_update(self, message: dict):
        self.update_index += 1
        index = self.update_index
        receive_ns = time.monotonic_ns()
        relative_before = self._private("relative_pose_init")
        absolute_before = self._private("absolute_pose_init")
        previous_before = self._private("previous_received_pose")
        self.current_update = {
            "callback_emitted": False,
            "callback_target": None,
            "pose_jump_warning": False,
        }
        error = None
        try:
            result = self.original_update(message)
        except Exception as caught:
            error = f"{type(caught).__name__}: {caught}"
            raise
        finally:
            current = self.current_update
            relative_after = self._private("relative_pose_init")
            absolute_after = self._private("absolute_pose_init")
            previous_after = self._private("previous_received_pose")
            target = np.array(self._private("pose"), copy=True)
            delta = target_delta(self.last_target, target)
            complete_ns = time.monotonic_ns()
            complete_wall = utc_now()
            record = {
                    "event": "server_update",
                    "server_update_index": index,
                    "server_connection_generation": self.active_connection_generation,
                    "server_receive_monotonic_ns": receive_ns,
                    "server_complete_monotonic_ns": complete_ns,
                    "wall_utc": complete_wall,
                    "move": bool(message.get("move")),
                    "source_pose": {
                        "position": message.get("position"),
                        "orientation": message.get("orientation"),
                    },
                    "target": transform_record(target),
                    "target_delta": delta,
                    "pose_jump_warning": current["pose_jump_warning"],
                    "relative_anchor_before_exists": relative_before is not None,
                    "relative_anchor_after_exists": relative_after is not None,
                    "relative_anchor_reset": relative_before is not None and relative_after is None,
                    "relative_anchor_created": relative_before is None and relative_after is not None,
                    "absolute_anchor_before_exists": absolute_before is not None,
                    "absolute_anchor_after_exists": absolute_after is not None,
                    "previous_received_pose_before_exists": previous_before is not None,
                    "previous_received_pose_after_exists": previous_after is not None,
                    "callback_emitted": current["callback_emitted"],
                    "callback_target": transform_record(current["callback_target"])
                    if current["callback_target"] is not None
                    else None,
                    "error": error,
                }
            self.writer.append(record)
            self.ack_publisher(
                {
                    "type": "server_ack",
                    "schema": "spes-quest-server-ack-v1",
                    "server_update_index": index,
                    "server_connection_generation": self.active_connection_generation,
                    "server_complete_monotonic_ns": complete_ns,
                    "last_callback_time": self.last_callback_time,
                    "callback_emitted": current["callback_emitted"],
                    "callback_count": self.callback_count,
                    "jump_reject": current["pose_jump_warning"],
                    "target_delta": delta,
                    "target": transform_record(target),
                    "error": error,
                }
            )
            self.last_target = target
            self.last_update_index = index
            self.current_update = None
        return result


def pose_message(x: float, y: float, z: float, move: bool = True) -> dict:
    return {
        "position": {"x": x, "y": y, "z": z},
        "orientation": {"x": 0.0, "y": 0.0, "z": 0.0, "w": 1.0},
        "move": move,
        "gripper": "open",
        "scale": 1.0,
        "device": "VR",
    }


def self_test() -> int:
    with tempfile.TemporaryDirectory(prefix="spes_hw_server_selftest_") as temp_dir:
        path = Path(temp_dir) / "server.jsonl"
        writer = JsonlWriter(path)
        teleop = Teleop(frontend_dir=str(TARGET_PACKAGE))
        acknowledgements = []
        observer = ServerObserver(teleop, writer, acknowledgements.append)
        try:
            for message in [
                pose_message(0.0, 0.0, 0.0),
                pose_message(0.0, 0.02, 0.0),
                pose_message(1.0, 0.0, 0.0),
                pose_message(1.02, 0.0, 0.0),
                pose_message(1.04, 0.0, 0.0),
            ]:
                teleop._Teleop__update(message)
        finally:
            observer.close()
        records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
        updates = [record for record in records if record["event"] == "server_update"]
        assert len(updates) == 5
        assert [record["callback_emitted"] for record in updates] == [True, True, False, True, True]
        assert updates[2]["pose_jump_warning"] is True
        assert updates[2]["relative_anchor_reset"] is True
        assert updates[3]["relative_anchor_created"] is True
        assert updates[4]["target_delta"]["linear_m"] > 0.0
        assert len(acknowledgements) == 5
        assert [ack["callback_emitted"] for ack in acknowledgements] == [True, True, False, True, True]
        assert acknowledgements[2]["jump_reject"] is True
    print(
        json.dumps(
            {
                "event": "hardware_server_selftest",
                "actual_upstream_update_wrapped": True,
                "callback_sequence": [True, True, False, True, True],
                "jump_warning_observed": True,
                "anchor_reset_observed": True,
                "sideband_ack_observed": True,
                "result": "PASS",
            }
        )
    )
    return 0


def run_server(args) -> int:
    manifest_path = args.frontend_dir / "INSTRUMENTATION_MANIFEST.json"
    if not manifest_path.is_file():
        raise FileNotFoundError(
            f"instrumented frontend missing at {args.frontend_dir}; run prepare_spes_hardware_frontend.py"
        )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("source_commit") != EXPECTED_COMMIT:
        raise RuntimeError("instrumented frontend source commit mismatch")
    if not re.fullmatch(r"[A-Za-z0-9_.-]+", args.run_id):
        raise ValueError("run id may contain only letters, digits, dot, underscore, and hyphen")

    run_dir = args.result_root / args.run_id
    server_writer = JsonlWriter(run_dir / "server.jsonl")
    experiment_writer = JsonlWriter(run_dir / "experiment.jsonl")
    server_writer.append(
        {
            "event": "run_start",
            "run_id": args.run_id,
            "wall_utc": utc_now(),
            "monotonic_ns": time.monotonic_ns(),
            "target_commit": EXPECTED_COMMIT,
            "frontend_manifest": manifest,
            "robot_connected": False,
            "ros_sink_enabled": False,
            "operator_mode": "SELF_CONTAINED_QUEST",
        }
    )
    experiment_writer.append(
        {
            "event": "experiment_log_start",
            "schema": "spes-quest-operator-v1",
            "run_id": args.run_id,
            "wall_utc": utc_now(),
            "monotonic_ns": time.monotonic_ns(),
            "hardware_observation_status": "NOT_YET_OBSERVED",
        }
    )

    teleop = Teleop(host=args.host, port=args.port, frontend_dir=str(args.frontend_dir))
    experiment_hub = ExperimentHub(experiment_writer, args.run_id)
    teleop._Teleop__app.websocket("/experiment")(experiment_hub.endpoint)
    observer = ServerObserver(teleop, server_writer, experiment_hub.publish)
    config = uvicorn.Config(
        app=teleop._Teleop__app,
        host=args.host,
        port=args.port,
        ssl_keyfile=str(TARGET_PACKAGE / "key.pem"),
        ssl_certfile=str(TARGET_PACKAGE / "cert.pem"),
        log_level="warning",
        access_log=False,
    )
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, name="spes-uvicorn", daemon=True)
    thread.start()
    deadline = time.monotonic() + 10.0
    while not server.started and thread.is_alive() and time.monotonic() < deadline:
        time.sleep(0.05)
    if not server.started:
        observer.close()
        raise RuntimeError("Spes server did not become ready within 10 seconds")

    local_ip = get_local_ip()
    print(f"Quest URL: https://{local_ip}:{args.port}", flush=True)
    print(f"Server log: {server_writer.path}", flush=True)
    print(f"Experiment log: {experiment_writer.path}", flush=True)
    print("READY FOR QUEST EXPERIMENT", flush=True)
    server_writer.append(
        {
            "event": "ready",
            "run_id": args.run_id,
            "url": f"https://{local_ip}:{args.port}",
            "server_log": str(server_writer.path),
            "experiment_log": str(experiment_writer.path),
            "wall_utc": utc_now(),
            "monotonic_ns": time.monotonic_ns(),
        }
    )
    outcome = "ERROR"
    try:
        stop_event = threading.Event()

        def stop_handler(_signum, _frame):
            stop_event.set()

        previous_term = signal.signal(signal.SIGTERM, stop_handler)
        previous_int = signal.signal(signal.SIGINT, stop_handler)
        while thread.is_alive() and not stop_event.wait(0.5):
            pass
        signal.signal(signal.SIGTERM, previous_term)
        signal.signal(signal.SIGINT, previous_int)
        outcome = "SERVER_STOP_REQUESTED" if stop_event.is_set() else "SERVER_THREAD_EXITED"
    except KeyboardInterrupt:
        outcome = "INTERRUPTED"
    finally:
        server_writer.append(
            {
                "event": "run_finished",
                "run_id": args.run_id,
                "outcome": outcome,
                "wall_utc": utc_now(),
                "monotonic_ns": time.monotonic_ns(),
            }
        )
        server.should_exit = True
        thread.join(timeout=5.0)
        observer.close()
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--no-console", action="store_true", help="compatibility flag; server is always detached/non-interactive")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=4443)
    parser.add_argument("--frontend-dir", type=Path, default=DEFAULT_FRONTEND)
    parser.add_argument("--result-root", type=Path, default=DEFAULT_RESULT_ROOT)
    parser.add_argument(
        "--run-id",
        default=datetime.now().strftime("spes_quest_%Y%m%dT%H%M%S"),
    )
    args = parser.parse_args()
    if args.self_test:
        return self_test()
    return run_server(args)


if __name__ == "__main__":
    raise SystemExit(main())
