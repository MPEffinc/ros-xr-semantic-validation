#!/usr/bin/env python3
"""Execute every hardware-independent semantic validation without stopping early."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import time
from typing import Any


EXPERIMENT = "no_quest_integrated_validation"


def append_jsonl(path: Path, record: dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n")


def print_phase(name: str, status: str, detail: str = "") -> None:
    suffix = f" — {detail}" if detail else ""
    print(f"[{status:10}] {name}{suffix}", flush=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--run-id",
        default=f"no_quest_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
    )
    parser.add_argument("--result-root", type=Path)
    args = parser.parse_args()

    validation_root = Path(__file__).resolve().parents[1]
    workspace_root = validation_root.parent
    result_root = args.result_root or validation_root / "logs" / "no_quest" / args.run_id
    if result_root.exists():
        raise SystemExit(f"refusing to overwrite existing result directory: {result_root}")
    result_root.mkdir(parents=True)
    summary_path = result_root / "integrated_summary.jsonl"
    semantic_deps = Path(os.environ.get("SEMANTIC_PY_DEPS", "/tmp/ros_xr_semantic_deps"))
    nvidia_deps = Path(os.environ.get("NVIDIA_PY_DEPS", "/tmp/ros_xr_nvidia_deps"))
    records: list[dict[str, Any]] = []

    append_jsonl(
        summary_path,
        {
            "experiment": EXPERIMENT,
            "trial": "setup",
            "monotonic_timestamp_ns": time.monotonic_ns(),
            "event": "run_start",
            "run_id": args.run_id,
            "result_root": str(result_root.resolve()),
            "hardware_used": False,
            "robot_connected": False,
            "semantic_python_deps": str(semantic_deps),
            "nvidia_python_deps": str(nvidia_deps),
        },
    )

    def record_status(
        name: str,
        status: str,
        *,
        event: str,
        detail: str,
        command: list[str] | None = None,
        duration_ms: float | None = None,
        return_code: int | None = None,
        output: str | None = None,
    ) -> None:
        record = {
            "experiment": EXPERIMENT,
            "trial": name,
            "monotonic_timestamp_ns": time.monotonic_ns(),
            "event": event,
            "input_semantic_ground_truth": "SYNTHETIC_OR_STATIC_NO_QUEST",
            "status": status,
            "detail": detail,
            "command": shlex.join(command) if command else None,
            "duration_ms": duration_ms,
            "return_code": return_code,
            "evidence_file": output,
            "connection_generation": None,
        }
        append_jsonl(summary_path, record)
        records.append(record)
        print_phase(name, status, detail)

    def run_component(
        name: str,
        command: list[str],
        output: Path,
        *,
        env: dict[str, str] | None = None,
        available: bool = True,
        unavailable_reason: str = "dependency unavailable",
    ) -> None:
        if not available:
            record_status(
                name,
                "SKIP_ENV",
                event="component_result",
                detail=unavailable_reason,
                command=command,
                output=str(output.resolve()),
            )
            return
        stdout_path = result_root / f"{name}.stdout.txt"
        stderr_path = result_root / f"{name}.stderr.txt"
        started = time.monotonic_ns()
        try:
            completed = subprocess.run(
                command,
                cwd=workspace_root,
                env=env,
                text=True,
                capture_output=True,
                timeout=120.0,
                check=False,
            )
            stdout_path.write_text(completed.stdout, encoding="utf-8")
            stderr_path.write_text(completed.stderr, encoding="utf-8")
            duration_ms = (time.monotonic_ns() - started) / 1_000_000
            artifact_status = None
            if output.is_file():
                try:
                    values = [
                        json.loads(line)
                        for line in output.read_text(encoding="utf-8").splitlines()
                        if line.strip()
                    ]
                    for value in values:
                        candidate = value.get("status") or value.get("result")
                        if candidate in {"PASS", "FAIL", "SKIP_ENV", "BLOCKED_HW"}:
                            artifact_status = candidate
                except (OSError, json.JSONDecodeError):
                    artifact_status = None
            status = (
                "FAIL"
                if completed.returncode != 0
                else artifact_status
                if artifact_status is not None
                else "PASS"
            )
            detail = (
                f"return_code={completed.returncode}; raw={output.relative_to(workspace_root)}"
                if output.is_relative_to(workspace_root)
                else f"return_code={completed.returncode}; raw={output}"
            )
            record_status(
                name,
                status,
                event="component_result",
                detail=detail,
                command=command,
                duration_ms=duration_ms,
                return_code=completed.returncode,
                output=str(output.resolve()),
            )
        except subprocess.TimeoutExpired as error:
            stdout_path.write_text(error.stdout or "", encoding="utf-8")
            stderr_path.write_text(error.stderr or "", encoding="utf-8")
            record_status(
                name,
                "FAIL",
                event="component_result",
                detail="timeout after 120 seconds",
                command=command,
                duration_ms=(time.monotonic_ns() - started) / 1_000_000,
                output=str(output.resolve()),
            )
        except Exception as error:
            record_status(
                name,
                "FAIL",
                event="component_result",
                detail=f"runner exception: {type(error).__name__}: {error}",
                command=command,
                duration_ms=(time.monotonic_ns() - started) / 1_000_000,
                output=str(output.resolve()),
            )

    base_env = os.environ.copy()
    semantic_env = base_env | {
        "PYTHONPATH": f"{semantic_deps}{os.pathsep}{base_env.get('PYTHONPATH', '')}".rstrip(os.pathsep)
    }
    nvidia_env = base_env | {
        "PYTHONPATH": f"{nvidia_deps}{os.pathsep}{base_env.get('PYTHONPATH', '')}".rstrip(os.pathsep)
    }
    node_available = shutil.which("node") is not None
    semantic_available = (semantic_deps / "numpy").is_dir()
    nvidia_available = all((nvidia_deps / package).is_dir() for package in ("numpy", "scipy", "pytest"))

    run_component(
        "s1_frontend",
        ["node", str(validation_root / "harness/spes_frontend_s1.mjs"), "--output", str(result_root / "s1_frontend.jsonl")],
        result_root / "s1_frontend.jsonl",
        available=node_available,
        unavailable_reason="node executable not found",
    )
    run_component(
        "s1_server",
        [sys.executable, str(validation_root / "harness/spes_server_replay.py"), "--output", str(result_root / "s1_server_replay.jsonl")],
        result_root / "s1_server_replay.jsonl",
        env=semantic_env,
        available=semantic_available,
        unavailable_reason=f"numpy dependency directory missing at {semantic_deps}",
    )
    run_component(
        "spes_semantic_collision",
        ["node", str(validation_root / "harness/spes_semantic_collision.mjs"), "--output", str(result_root / "spes_semantic_collision.jsonl")],
        result_root / "spes_semantic_collision.jsonl",
        available=node_available,
        unavailable_reason="node executable not found",
    )
    run_component(
        "spes_runtime_suite",
        [sys.executable, str(validation_root / "harness/spes_no_quest_runtime.py"), "--result-dir", str(result_root / "spes_runtime")],
        result_root / "spes_runtime/spes_suite_summary.jsonl",
        env=semantic_env,
        available=semantic_available and (semantic_deps / "websockets").is_dir(),
        unavailable_reason=f"numpy/websockets dependency directory missing at {semantic_deps}",
    )
    run_component(
        "quest2ros2_callback",
        [sys.executable, str(validation_root / "harness/quest2ros2_stale_restamp.py"), "--output", str(result_root / "quest2ros2_stale_restamp.jsonl")],
        result_root / "quest2ros2_stale_restamp.jsonl",
        env=semantic_env,
        available=semantic_available,
        unavailable_reason=f"numpy dependency directory missing at {semantic_deps}",
    )
    run_component(
        "picknik_machine_check",
        [sys.executable, str(validation_root / "harness/picknik_machine_check.py"), "--output", str(result_root / "picknik_machine_check.jsonl")],
        result_root / "picknik_machine_check.jsonl",
    )
    run_component(
        "nvidia_positive_control",
        [sys.executable, str(validation_root / "harness/nvidia_positive_control.py"), "--output", str(result_root / "nvidia_positive_control.jsonl")],
        result_root / "nvidia_positive_control.jsonl",
        env=nvidia_env,
        available=nvidia_available,
        unavailable_reason=f"numpy/scipy/pytest dependency directories missing at {nvidia_deps}",
    )

    docker = shutil.which("docker")
    docker_detail = "docker CLI not found"
    docker_access = False
    if docker:
        check = subprocess.run(
            [docker, "info"], text=True, capture_output=True, timeout=10.0, check=False
        )
        docker_access = check.returncode == 0
        docker_detail = (
            "docker daemon accessible"
            if docker_access
            else f"docker info denied/failed: {(check.stderr or check.stdout).strip().splitlines()[-1]}"
        )
    record_status(
        "quest2ros2_ros_transport",
        "SKIP_ENV",
        event="environment_result",
        detail=(
            "Docker is accessible, but this runner has no authorized robot-free ROS graph launch"
            if docker_access
            else docker_detail
        ),
        command=[docker or "docker", "info"],
    )

    unity = next((shutil.which(name) for name in ("Unity", "unity-editor", "unityhub") if shutil.which(name)), None)
    record_status(
        "picknik_unity_runtime",
        "SKIP_ENV",
        event="environment_result",
        detail=("Unity executable present but no scene test was authorized/configured" if unity else "Unity executable not found"),
        command=[unity or "Unity", "-batchmode"],
    )
    for name, detail in (
        ("spes_quest_activation", "controller-loss/emulatedPosition activation needs Quest 3"),
        ("picknik_quest_activation", "tracked/emulated Transform behavior needs Quest runtime"),
        ("quest2ros2_xr_producer", "upstream XR producer semantics and real frame lineage need Quest/client source"),
        ("nvidia_openxr_deviceio", "native OpenXR/DeviceIO tracking paths need compatible XR runtime/device"),
    ):
        record_status(name, "BLOCKED_HW", event="hardware_boundary", detail=detail)

    counts = {status: sum(record["status"] == status for record in records) for status in ("PASS", "FAIL", "SKIP_ENV", "BLOCKED_HW")}
    overall = "FAIL" if counts["FAIL"] else "PASS"
    append_jsonl(
        summary_path,
        {
            "experiment": EXPERIMENT,
            "trial": "summary",
            "monotonic_timestamp_ns": time.monotonic_ns(),
            "event": "suite_result",
            "status": overall,
            "counts": counts,
            "hardware_used": False,
            "robot_connected": False,
            "claim_boundary": "PASS covers hardware-independent static and synthetic-source runtime checks only; BLOCKED_HW entries remain unresolved.",
        },
    )
    print_phase("overall", overall, json.dumps(counts, sort_keys=True))
    print(f"RESULT_ROOT={result_root.resolve()}")
    return 1 if overall == "FAIL" else 0


if __name__ == "__main__":
    raise SystemExit(main())
