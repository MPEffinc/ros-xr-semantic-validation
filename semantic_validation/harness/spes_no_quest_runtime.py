#!/usr/bin/env python3

"""Actual Spes HTTPS/WSS/server tests driven by synthetic semantic sources."""

import argparse
import json
import logging
import socket
import ssl
import sys
import threading
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path


VALIDATION_ROOT = Path(__file__).resolve().parents[1]
TARGET_PACKAGE = VALIDATION_ROOT / "targets" / "spes_teleop" / "teleop"
EXPECTED_COMMIT = "c5d808155a87b584d6147a5943d4b87c34c92db0"
sys.path.insert(0, str(Path(__file__).resolve().parent))

import uvicorn  # noqa: E402
from spes_hardware_server import JsonlWriter, ServerObserver, Teleop, transform_record  # noqa: E402
from websockets.sync.client import connect  # noqa: E402


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.bind(("127.0.0.1", 0))
        return listener.getsockname()[1]


def pose_packet(x: float, y: float, z: float, move: bool = True) -> dict:
    return {
        "position": {"x": x, "y": y, "z": z},
        "orientation": {"x": 0.0, "y": 0.0, "z": 0.0, "w": 1.0},
        "move": move,
        "gripper": "open",
        "fps": 90,
        "scale": 1.0,
        "reservedButtonA": False,
        "reservedButtonB": False,
        "device": "VR",
        "message": "synthetic no-Quest source",
    }


def state_snapshot(teleop: Teleop) -> dict:
    def present(name: str) -> bool:
        return getattr(teleop, f"_Teleop__{name}") is not None

    return {
        "relative_anchor_exists": present("relative_pose_init"),
        "absolute_anchor_exists": present("absolute_pose_init"),
        "previous_received_pose_exists": present("previous_received_pose"),
        "current_target": transform_record(getattr(teleop, "_Teleop__pose")),
    }


def latest_update(path: Path, update_index: int) -> dict:
    for line in reversed(path.read_text(encoding="utf-8").splitlines()):
        record = json.loads(line)
        if record.get("event") == "server_update" and record.get("server_update_index") == update_index:
            return record
    raise RuntimeError(f"server update {update_index} not found in {path}")


class ContextualWriter:
    """Add the common experiment fields to observer-generated records."""

    def __init__(self, writer: JsonlWriter, experiment: str):
        self.writer = writer
        self.path = writer.path
        self.experiment = experiment

    def append(self, record: dict) -> None:
        enriched = {
            "experiment": self.experiment,
            "trial": "runtime_event",
            "monotonic_timestamp_ns": record.get(
                "server_receive_monotonic_ns", time.monotonic_ns()
            ),
            "input_semantic_ground_truth": "CORRELATED_BY_CLIENT_SEND_RECORD",
            **record,
        }
        self.writer.append(enriched)


class ScenarioServer:
    def __init__(self, experiment: str, output: Path):
        self.experiment = experiment
        self.writer = ContextualWriter(JsonlWriter(output), experiment)
        teleop_logger = logging.getLogger("teleop")
        handlers_before = set(teleop_logger.handlers)
        self.teleop = Teleop(host="127.0.0.1", port=0, frontend_dir=str(TARGET_PACKAGE))
        self.upstream_handlers = [
            handler for handler in teleop_logger.handlers if handler not in handlers_before
        ]
        self.observer = ServerObserver(self.teleop, self.writer)
        self.port = free_port()
        self.server = uvicorn.Server(
            uvicorn.Config(
                app=self.teleop._Teleop__app,
                host="127.0.0.1",
                port=self.port,
                ssl_keyfile=str(TARGET_PACKAGE / "key.pem"),
                ssl_certfile=str(TARGET_PACKAGE / "cert.pem"),
                log_level="warning",
                access_log=False,
            )
        )
        self.thread = threading.Thread(target=self.server.run, daemon=True)
        self.connection_generation = 0

    def __enter__(self):
        self.writer.append(
            {
                "experiment": self.experiment,
                "trial": "run",
                "monotonic_timestamp_ns": time.monotonic_ns(),
                "event": "run_start",
                "target_commit": EXPECTED_COMMIT,
                "source_kind": "SYNTHETIC_SEMANTIC_SOURCE",
                "transport": "ACTUAL_HTTPS_WSS",
                "server_logic": "ACTUAL_TELEOP_UPDATE",
                "robot_connected": False,
            }
        )
        self.thread.start()
        deadline = time.monotonic() + 10.0
        while not self.server.started and self.thread.is_alive() and time.monotonic() < deadline:
            time.sleep(0.02)
        if not self.server.started:
            raise RuntimeError("WSS server failed to start")
        return self

    def __exit__(self, exc_type, exc, traceback):
        self.server.should_exit = True
        self.thread.join(timeout=5.0)
        self.observer.close()
        teleop_logger = logging.getLogger("teleop")
        for handler in self.upstream_handlers:
            teleop_logger.removeHandler(handler)

    @contextmanager
    def client(self):
        self.connection_generation += 1
        generation = self.connection_generation
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        websocket = None
        last_error = None
        for attempt in range(3):
            try:
                websocket = connect(
                    f"wss://127.0.0.1:{self.port}/ws",
                    ssl=context,
                    open_timeout=5.0,
                    close_timeout=2.0,
                    legacy=True,
                )
                break
            except Exception as error:
                last_error = error
                if attempt < 2:
                    time.sleep(0.1 * (attempt + 1))
        if websocket is None:
            raise RuntimeError("WSS handshake failed after 3 attempts") from last_error
        try:
            deadline = time.monotonic() + 2.0
            while self.observer.connection_generation < generation and time.monotonic() < deadline:
                time.sleep(0.005)
            yield RuntimeClient(self, websocket, generation)
        finally:
            websocket.close()
        deadline = time.monotonic() + 2.0
        while self.observer.active_connection_generation is not None and time.monotonic() < deadline:
            time.sleep(0.005)

    def decision(self, trial: str, result: str, **details) -> None:
        self.writer.append(
            {
                "experiment": self.experiment,
                "trial": trial,
                "monotonic_timestamp_ns": time.monotonic_ns(),
                "event": "decision",
                "evidence_level": "CONFIRMED_RUNTIME_SYNTHETIC_SOURCE",
                "result": result,
                **details,
            }
        )


class RuntimeClient:
    def __init__(self, server: ScenarioServer, websocket, connection_generation: int):
        self.server = server
        self.websocket = websocket
        self.connection_generation = connection_generation

    def send_pose(
        self,
        trial: str,
        packet: dict,
        semantic_ground_truth: dict,
        generated_monotonic_ns: int | None = None,
    ) -> dict:
        generated_ns = generated_monotonic_ns or time.monotonic_ns()
        send_ns = time.monotonic_ns()
        expected_index = self.server.observer.update_index + 1
        self.server.writer.append(
            {
                "experiment": self.server.experiment,
                "trial": trial,
                "monotonic_timestamp_ns": send_ns,
                "event": "client_send",
                "input_semantic_ground_truth": semantic_ground_truth,
                "source_generated_monotonic_ns": generated_ns,
                "source_age_ms_at_send": (send_ns - generated_ns) / 1_000_000.0,
                "control_packet": packet,
                "source_timestamp_in_control_packet": False,
                "source_identity_in_control_packet": False,
                "sequence_in_control_packet": False,
                "connection_generation": self.connection_generation,
                "expected_server_update_index": expected_index,
            }
        )
        self.websocket.send(json.dumps({"type": "pose", "data": packet}))
        deadline = time.monotonic() + 2.0
        while self.server.observer.update_index < expected_index and time.monotonic() < deadline:
            time.sleep(0.005)
        if self.server.observer.update_index < expected_index:
            raise TimeoutError(f"server did not process update {expected_index}")
        update = latest_update(self.server.writer.path, expected_index)
        self.server.writer.append(
            {
                "experiment": self.server.experiment,
                "trial": trial,
                "monotonic_timestamp_ns": time.monotonic_ns(),
                "event": "correlated_result",
                "connection_generation": self.connection_generation,
                "server_update_index": expected_index,
                "callback_emitted": update["callback_emitted"],
                "pose_jump_warning": update["pose_jump_warning"],
                "relative_anchor_reset": update["relative_anchor_reset"],
                "relative_anchor_created": update["relative_anchor_created"],
                "target": update["target"],
                "target_delta": update["target_delta"],
            }
        )
        return update


def run_reconnect_near(output: Path) -> None:
    with ScenarioServer("spes_reconnect_near", output) as server:
        with server.client() as client_a:
            client_a.send_pose("A_P1", pose_packet(0.0, 0.0, 0.0), {"source": "CONTROLLER", "move": True})
            client_a.send_pose("A_P2", pose_packet(0.0, 0.02, 0.0), {"source": "CONTROLLER", "move": True})
            before_disconnect = state_snapshot(server.teleop)
        after_disconnect = state_snapshot(server.teleop)
        assert after_disconnect == before_disconnect
        with server.client() as client_b:
            p3 = client_b.send_pose("B_P3", pose_packet(0.0, 0.03, 0.0), {"source": "CONTROLLER", "move": True, "user_rearm": False})
            p4 = client_b.send_pose("B_P4", pose_packet(0.0, 0.04, 0.0), {"source": "CONTROLLER", "move": True, "user_rearm": False})
        assert p3["callback_emitted"] and p4["callback_emitted"]
        assert p3["server_connection_generation"] == 2
        server.decision(
            "R1_summary",
            "PASS",
            disconnect_reset_state=False,
            new_connection_immediate_callback=True,
            user_rearm_observed=False,
            transport_generation_bound_to_control_state=False,
        )


def run_reconnect_far(output: Path) -> None:
    with ScenarioServer("spes_reconnect_far", output) as server:
        with server.client() as client_a:
            client_a.send_pose("A_P1", pose_packet(0.0, 0.0, 0.0), {"source": "CONTROLLER", "move": True})
            client_a.send_pose("A_P2", pose_packet(0.0, 0.02, 0.0), {"source": "CONTROLLER", "move": True})
        with server.client() as client_b:
            q1 = client_b.send_pose("B_Q1", pose_packet(1.0, 0.0, 0.0), {"source": "CONTROLLER", "move": True, "user_rearm": False})
            q2 = client_b.send_pose("B_Q2", pose_packet(1.02, 0.0, 0.0), {"source": "CONTROLLER", "move": True, "user_rearm": False})
            q3 = client_b.send_pose("B_Q3", pose_packet(1.04, 0.0, 0.0), {"source": "CONTROLLER", "move": True, "user_rearm": False})
        assert q1["pose_jump_warning"] and not q1["callback_emitted"]
        assert q1["relative_anchor_reset"]
        assert q2["relative_anchor_created"] and q2["callback_emitted"]
        assert q3["callback_emitted"] and q3["target_delta"]["linear_m"] > 0.0
        server.decision(
            "R2_R3_summary",
            "PASS",
            q1_rejected=True,
            q2_reanchored=True,
            q3_actionable=True,
            explicit_rearm_required=False,
            control_session_identity_field_present=False,
        )


def run_freshness_normal(output: Path) -> None:
    with ScenarioServer("spes_freshness_normal", output) as server:
        with server.client() as client:
            updates = [
                client.send_pose(f"F1_P{index}", pose_packet(0.0, 0.01 * index, 0.0), {"source": "CONTROLLER", "stream": "fresh"})
                for index in (1, 2, 3)
            ]
        assert all(update["callback_emitted"] for update in updates)
        server.decision("F1_summary", "PASS", callbacks=3, freshness_guard_observed=False)


def run_freshness_delayed_single(output: Path) -> None:
    generated_ns = time.monotonic_ns()
    packet = pose_packet(0.2, 0.2, 0.2)
    time.sleep(1.05)
    with ScenarioServer("spes_freshness_delayed_single", output) as server:
        with server.client() as client:
            update = client.send_pose(
                "F2_old_Q",
                packet,
                {"source": "CONTROLLER", "stream": "delayed", "ground_truth_age_class": ">1s"},
                generated_ns,
            )
        assert update["callback_emitted"]
        server.decision(
            "F2_summary",
            "PASS",
            delayed_sample_accepted=True,
            source_timestamp_available_to_server=False,
            freshness_guard_observed=False,
        )


def run_freshness_delayed_trajectory(output: Path) -> None:
    queued = []
    for index in range(3):
        queued.append((f"F3_old_P{index + 1}", pose_packet(0.0, index * 0.02, 0.0), time.monotonic_ns()))
        time.sleep(0.01)
    time.sleep(1.05)
    with ScenarioServer("spes_freshness_delayed_trajectory", output) as server:
        with server.client() as client:
            updates = [
                client.send_pose(
                    trial,
                    packet,
                    {"source": "CONTROLLER", "stream": "queued_old_trajectory", "source_order": index},
                    generated_ns,
                )
                for index, (trial, packet, generated_ns) in enumerate(queued, start=1)
            ]
        assert all(update["callback_emitted"] for update in updates)
        server.decision(
            "F3_summary",
            "PASS",
            delayed_trajectory_callbacks=len(updates),
            source_time_lineage_preserved=False,
            application_order_preserved=True,
        )


def run_control_near_rearm(output: Path) -> None:
    with ScenarioServer("spes_control_near_rearm", output) as server:
        with server.client() as client:
            client.send_pose("C1_P1", pose_packet(0.0, 0.0, 0.0), {"source": "CONTROLLER", "move": True})
            client.send_pose("C1_P2", pose_packet(0.0, 0.02, 0.0), {"source": "CONTROLLER", "move": True})
            disabled = client.send_pose("C1_DISABLE", pose_packet(0.0, 0.02, 0.0, move=False), {"source": "CONTROLLER", "move": False})
            client.send_pose("C1_DISABLED_P3", pose_packet(0.0, 0.03, 0.0, move=False), {"source": "CONTROLLER", "move": False})
            reenabled = client.send_pose("C1_REENABLE_P3", pose_packet(0.0, 0.03, 0.0), {"source": "CONTROLLER", "move": True, "explicit_rearm": True})
            p4 = client.send_pose("C1_P4", pose_packet(0.0, 0.04, 0.0), {"source": "CONTROLLER", "move": True})
        assert disabled["relative_anchor_reset"] and disabled["callback_emitted"]
        assert reenabled["relative_anchor_created"] and reenabled["callback_emitted"]
        assert p4["callback_emitted"] and p4["target_delta"]["linear_m"] > 0.0
        server.decision("C1_summary", "PASS", explicit_clutch_reanchors=True, near_rearm_actionable=True)


def run_control_far_rearm(output: Path) -> None:
    with ScenarioServer("spes_control_far_rearm", output) as server:
        with server.client() as client:
            client.send_pose("C2_P1", pose_packet(0.0, 0.0, 0.0), {"source": "CONTROLLER", "move": True})
            client.send_pose("C2_P2", pose_packet(0.0, 0.02, 0.0), {"source": "CONTROLLER", "move": True})
            client.send_pose("C2_DISABLE", pose_packet(0.0, 0.02, 0.0, move=False), {"source": "CONTROLLER", "move": False})
            client.send_pose("C2_DISABLED_Q1", pose_packet(1.0, 0.0, 0.0, move=False), {"source": "CONTROLLER", "move": False})
            q1 = client.send_pose("C2_REENABLE_Q1", pose_packet(1.0, 0.0, 0.0), {"source": "CONTROLLER", "move": True, "explicit_rearm": True})
            q2 = client.send_pose("C2_Q2", pose_packet(1.02, 0.0, 0.0), {"source": "CONTROLLER", "move": True})
            q3 = client.send_pose("C2_Q3", pose_packet(1.04, 0.0, 0.0), {"source": "CONTROLLER", "move": True})
        assert q1["pose_jump_warning"] and not q1["callback_emitted"]
        assert q2["relative_anchor_created"] and q2["callback_emitted"]
        assert q3["callback_emitted"] and q3["target_delta"]["linear_m"] > 0.0
        server.decision(
            "C2_summary",
            "PASS",
            disabled_pose_did_not_replace_previous_received_pose=True,
            first_far_rearm_rejected=True,
            nearby_followup_reanchored=True,
        )


def run_control_hidden_switch(output: Path) -> None:
    with ScenarioServer("spes_control_hidden_source_switch", output) as server:
        with server.client() as client:
            client.send_pose("C3_controller_P1", pose_packet(0.0, 0.0, 0.0), {"source": "RIGHT_CONTROLLER", "move": True})
            client.send_pose("C3_controller_P2", pose_packet(0.0, 0.02, 0.0), {"source": "RIGHT_CONTROLLER", "move": True})
            q1 = client.send_pose("C3_viewer_Q1", pose_packet(1.0, 0.0, 0.0), {"source": "VIEWER", "move": True, "source_transition_in_packet": False})
            q2 = client.send_pose("C3_viewer_Q2", pose_packet(1.02, 0.0, 0.0), {"source": "VIEWER", "move": True, "source_transition_in_packet": False})
            q3 = client.send_pose("C3_viewer_Q3", pose_packet(1.04, 0.0, 0.0), {"source": "VIEWER", "move": True, "source_transition_in_packet": False})
        assert q1["pose_jump_warning"] and not q1["callback_emitted"]
        assert q2["callback_emitted"] and q3["callback_emitted"]
        server.decision(
            "C3_summary",
            "PASS",
            source_transition_visible_to_server=False,
            first_jump_rejected=True,
            viewer_trajectory_actionable_after_reanchor=True,
        )


def run_network_stall_switch(output: Path) -> None:
    with ScenarioServer("spes_network_stall_source_switch", output) as server:
        with server.client() as client:
            client.send_pose("N1_controller_P1", pose_packet(0.0, 0.0, 0.0), {"source": "RIGHT_CONTROLLER", "move": True})
            client.send_pose("N1_controller_P2", pose_packet(0.0, 0.02, 0.0), {"source": "RIGHT_CONTROLLER", "move": True})
            queued = [
                (f"N1_viewer_Q{index}", pose_packet(1.0 + (index - 1) * 0.02, 0.0, 0.0), time.monotonic_ns())
                for index in (1, 2, 3)
            ]
            time.sleep(0.25)
            updates = [
                client.send_pose(
                    trial,
                    packet,
                    {"source": "VIEWER", "move": True, "composition": "application_queue_after_stall"},
                    generated,
                )
                for trial, packet, generated in queued
            ]
        assert not updates[0]["callback_emitted"] and updates[0]["pose_jump_warning"]
        assert updates[1]["callback_emitted"] and updates[2]["callback_emitted"]
        server.decision(
            "N1_summary",
            "PASS",
            composition="APPLICATION_LEVEL_CONTROLLED_REPLAY",
            tcp_reorder_claimed=False,
            queued_viewer_trajectory_actionable_after_reanchor=True,
        )


def run_network_old_generation_replay(output: Path) -> None:
    with ScenarioServer("spes_network_old_generation_replay", output) as server:
        with server.client() as client:
            client.send_pose("N2_controller_P1", pose_packet(0.0, 0.0, 0.0), {"source": "RIGHT_CONTROLLER", "source_generation": 0, "move": True})
            client.send_pose("N2_controller_P2", pose_packet(0.0, 0.02, 0.0), {"source": "RIGHT_CONTROLLER", "source_generation": 0, "move": True})
            old_queue = [
                (f"N2_old_controller_P{index}", pose_packet(0.0, index * 0.01, 0.0), time.monotonic_ns())
                for index in (3, 4, 5)
            ]
            viewer_updates = [
                client.send_pose(
                    f"N2_viewer_Q{index}",
                    pose_packet(1.0 + (index - 1) * 0.02, 0.0, 0.0),
                    {"source": "VIEWER", "source_generation": 1, "move": True},
                )
                for index in (1, 2, 3)
            ]
            replay_updates = [
                client.send_pose(
                    trial,
                    packet,
                    {"source": "RIGHT_CONTROLLER", "source_generation": 0, "move": True, "replayed_after_generation_1": True},
                    generated,
                )
                for trial, packet, generated in old_queue
            ]
        assert viewer_updates[0]["pose_jump_warning"] and viewer_updates[1]["callback_emitted"]
        assert replay_updates[0]["pose_jump_warning"] and not replay_updates[0]["callback_emitted"]
        assert replay_updates[1]["callback_emitted"] and replay_updates[2]["callback_emitted"]
        server.decision(
            "N2_N3_summary",
            "PASS",
            composition="APPLICATION_LEVEL_CONTROLLED_REPLAY",
            stale_source_generation_field_available=False,
            old_generation_actionable_after_reanchor=True,
            reconnect_composed=False,
            generic_network_vulnerability_claimed=False,
        )


SCENARIOS = [
    ("reconnect_near", run_reconnect_near),
    ("reconnect_far", run_reconnect_far),
    ("freshness_normal", run_freshness_normal),
    ("freshness_delayed_single", run_freshness_delayed_single),
    ("freshness_delayed_trajectory", run_freshness_delayed_trajectory),
    ("control_near_rearm", run_control_near_rearm),
    ("control_far_rearm", run_control_far_rearm),
    ("control_hidden_switch", run_control_hidden_switch),
    ("network_stall_switch", run_network_stall_switch),
    ("network_old_generation_replay", run_network_old_generation_replay),
]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--result-dir", type=Path, required=True)
    args = parser.parse_args()
    result_dir = args.result_dir.resolve()
    if result_dir.exists():
        raise FileExistsError(f"refusing to overwrite result directory: {result_dir}")
    result_dir.mkdir(parents=True)
    summary = JsonlWriter(result_dir / "spes_suite_summary.jsonl")
    failures = 0
    skipped_environment = 0
    passed = 0
    for name, function in SCENARIOS:
        started = time.monotonic_ns()
        try:
            function(result_dir / f"spes_{name}.jsonl")
            status = "PASS"
            error = None
        except Exception as caught:
            if isinstance(caught, PermissionError) and caught.errno in {1, 13}:
                skipped_environment += 1
                status = "SKIP_ENV"
            else:
                failures += 1
                status = "FAIL"
            error = f"{type(caught).__name__}: {caught}"
        else:
            passed += 1
        record = {
            "experiment": "spes_no_quest_runtime_suite",
            "trial": name,
            "monotonic_timestamp_ns": time.monotonic_ns(),
            "event": "scenario_result",
            "status": status,
            "error": error,
            "duration_ms": (time.monotonic_ns() - started) / 1_000_000.0,
            "raw_log": str(result_dir / f"spes_{name}.jsonl"),
        }
        summary.append(record)
        print(json.dumps(record), flush=True)
    suite_status = "FAIL" if failures else "PASS" if passed else "SKIP_ENV"
    summary.append(
        {
            "experiment": "spes_no_quest_runtime_suite",
            "trial": "summary",
            "monotonic_timestamp_ns": time.monotonic_ns(),
            "event": "suite_result",
            "passed": passed,
            "failed": failures,
            "skipped_environment": skipped_environment,
            "status": suite_status,
            "hardware_used": False,
            "robot_connected": False,
        }
    )
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
