#!/usr/bin/env python3

"""Repeatable, non-hardware preflight for the Spes Quest instrumentation."""

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


VALIDATION_ROOT = Path(__file__).resolve().parents[1]
HARNESS_ROOT = VALIDATION_ROOT / "harness"
TARGET_ROOT = VALIDATION_ROOT / "targets" / "spes_teleop"
DEFAULT_OUTPUT = VALIDATION_ROOT / "logs" / "spes_hardware_preflight.jsonl"
EXPECTED_COMMIT = "c5d808155a87b584d6147a5943d4b87c34c92db0"


def run(command: list[str], env=None) -> dict:
    completed = subprocess.run(command, capture_output=True, text=True, env=env)
    return {
        "command": command,
        "returncode": completed.returncode,
        "stdout": completed.stdout.strip(),
        "stderr": completed.stderr.strip(),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists() and not args.overwrite:
        raise FileExistsError(f"use --overwrite to replace generated preflight log: {output}")

    python_env = os.environ.copy()
    deps = python_env.get("SEMANTIC_PY_DEPS", "/tmp/ros_xr_semantic_deps")
    python_env["PYTHONPATH"] = (
        deps
        if not python_env.get("PYTHONPATH")
        else f"{deps}{os.pathsep}{python_env['PYTHONPATH']}"
    )
    records = [
        {
            "event": "preflight_start",
            "time_utc": datetime.now(timezone.utc).isoformat(),
            "hardware_used": False,
            "robot_connected": False,
        }
    ]

    checks = [
        (
            "prepare_instrumented_frontend",
            [sys.executable, str(HARNESS_ROOT / "prepare_spes_hardware_frontend.py")],
            None,
        ),
        (
            "frontend_control_payload_equivalence",
            ["node", str(HARNESS_ROOT / "spes_hardware_frontend_selftest.mjs")],
            None,
        ),
        (
            "quest_operator_hud_audio_left_control",
            ["node", str(HARNESS_ROOT / "spes_quest_operator_selftest.mjs")],
            None,
        ),
        (
            "server_observer_actual_update",
            [sys.executable, str(HARNESS_ROOT / "spes_hardware_server.py"), "--self-test"],
            python_env,
        ),
        (
            "https_production_wss_experiment_wss_ack",
            [sys.executable, str(HARNESS_ROOT / "spes_live_endpoint_selftest.py")],
            python_env,
        ),
        (
            "uvicorn_websocket_backend",
            [sys.executable, "-c", "import websockets; print(websockets.__version__)"],
            python_env,
        ),
        (
            "python_syntax",
            [
                sys.executable,
                "-m",
                "py_compile",
                str(HARNESS_ROOT / "prepare_spes_hardware_frontend.py"),
                str(HARNESS_ROOT / "spes_hardware_server.py"),
                str(HARNESS_ROOT / "spes_live_endpoint_selftest.py"),
                str(HARNESS_ROOT / "ros_dummy_sink.py"),
            ],
            None,
        ),
    ]
    all_required_passed = True
    environment_blocked_checks = 0
    live_endpoint_ready = False
    for name, command, env in checks:
        result = run(command, env=env)
        passed = result["returncode"] == 0
        environment_blocked = (
            name == "https_production_wss_experiment_wss_ack"
            and not passed
            and "PermissionError: [Errno 1] Operation not permitted" in result["stderr"]
        )
        if environment_blocked:
            environment_blocked_checks += 1
        else:
            all_required_passed = all_required_passed and passed
        if name == "https_production_wss_experiment_wss_ack":
            live_endpoint_ready = passed
        records.append({
            "event": "preflight_check",
            "check": name,
            "passed": passed,
            "status": "PASS" if passed else "SKIP_ENV" if environment_blocked else "FAIL",
            "environment_blocked": environment_blocked,
            **result,
        })

    head = run(["git", "-C", str(TARGET_ROOT), "rev-parse", "HEAD"])
    status = run(["git", "-C", str(TARGET_ROOT), "status", "--porcelain"])
    target_clean = (
        head["returncode"] == 0
        and head["stdout"] == EXPECTED_COMMIT
        and status["returncode"] == 0
        and status["stdout"] == ""
    )
    all_required_passed = all_required_passed and target_clean
    records.append(
        {
            "event": "preflight_check",
            "check": "upstream_target_clean_fixed_revision",
            "passed": target_clean,
            "head": head["stdout"],
            "status": status["stdout"],
        }
    )

    docker = run(["docker", "info"])
    docker_available = docker["returncode"] == 0
    records.append(
        {
            "event": "environment_check",
            "check": "docker_daemon_access",
            "available": docker_available,
            "returncode": docker["returncode"],
            "stderr": docker["stderr"],
            "interpretation": "ROS_DUMMY_SINK_AVAILABLE" if docker_available else "ROS_DUMMY_SINK_BLOCKED",
        }
    )
    result = (
        "FAIL"
        if not all_required_passed
        else "SKIP_ENV"
        if environment_blocked_checks
        else "PASS"
    )
    records.append(
        {
            "event": "preflight_summary",
            "instrumentation_ready": all_required_passed,
            "payload_equivalence_ready": all_required_passed,
            "https_ready": live_endpoint_ready,
            "production_wss_ready": live_endpoint_ready,
            "experiment_ack_wss_ready": live_endpoint_ready,
            "hud_operator_static_ready": all_required_passed,
            "in_xr_webgl_hud_fallback_ready": all_required_passed,
            "audio_fallback_static_ready": all_required_passed,
            "left_controller_operator_ready": all_required_passed,
            "docker_ros_ready": docker_available,
            "environment_blocked_checks": environment_blocked_checks,
            "quest_hardware_executed": False,
            "result": result,
        }
    )
    output.write_text(
        "".join(json.dumps(record, sort_keys=True) + "\n" for record in records),
        encoding="utf-8",
    )
    print(json.dumps(records[-1], sort_keys=True))
    print(f"preflight_log={output}")
    return 0 if result != "FAIL" else 1


if __name__ == "__main__":
    raise SystemExit(main())
