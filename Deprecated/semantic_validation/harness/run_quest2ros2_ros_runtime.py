#!/usr/bin/env python3
"""Probe Docker and, when available, run the robot-free Quest2ROS2 ROS test.

The container is deliberately isolated with ``--network none``, has no device
mounts, and receives no privileges.  The pinned Quest2ROS2 checkout is copied
to a temporary build workspace so colcon cannot modify the upstream target.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import grp
import json
import os
from pathlib import Path
import pwd
import shutil
import stat
import subprocess
import tempfile
from typing import Any


EXPERIMENT = "quest2ros2_actual_ros_runtime"
DEFAULT_IMAGE = "ros-xr-humble:local"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def run_id_now() -> str:
    return datetime.now(timezone.utc).strftime("quest2ros2_ros_runtime_%Y%m%dT%H%M%SZ")


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def append_jsonl(path: Path, value: dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n")


def command_record(
    log_path: Path,
    label: str,
    command: list[str],
    *,
    cwd: Path | None = None,
    timeout: int = 30,
) -> subprocess.CompletedProcess[str]:
    try:
        completed = subprocess.run(
            command,
            cwd=cwd,
            text=True,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
        record = {
            "timestamp": utc_now(),
            "event": "environment_command",
            "label": label,
            "command": command,
            "cwd": str(cwd) if cwd else None,
            "returncode": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
        }
    except (FileNotFoundError, subprocess.TimeoutExpired) as error:
        if isinstance(error, subprocess.TimeoutExpired):
            stdout = error.stdout.decode() if isinstance(error.stdout, bytes) else (error.stdout or "")
            stderr = error.stderr.decode() if isinstance(error.stderr, bytes) else (error.stderr or "")
            returncode = 124
        else:
            stdout = ""
            stderr = str(error)
            returncode = 127
        completed = subprocess.CompletedProcess(command, returncode, stdout, stderr)
        record = {
            "timestamp": utc_now(),
            "event": "environment_command",
            "label": label,
            "command": command,
            "cwd": str(cwd) if cwd else None,
            "returncode": returncode,
            "stdout": stdout,
            "stderr": stderr,
        }
    append_jsonl(log_path, record)
    return completed


def copy_target_workspace(target_root: Path, workspace: Path) -> None:
    source_root = workspace / "src"
    source_root.mkdir(parents=True)

    def ignore_target(_directory: str, names: list[str]) -> set[str]:
        ignored = {name for name in names if name in {".git", "__pycache__", "Files_for_msg_pkg"}}
        ignored.update(name for name in names if name.endswith(".pyc"))
        return ignored

    shutil.copytree(
        target_root,
        source_root / "q2r2_bringup",
        ignore=ignore_target,
    )
    shutil.copytree(target_root / "Files_for_msg_pkg", source_root / "quest2ros")


def socket_record() -> dict[str, Any]:
    socket_path = Path("/var/run/docker.sock")
    record: dict[str, Any] = {
        "timestamp": utc_now(),
        "event": "docker_socket",
        "path": str(socket_path),
        "exists": socket_path.exists(),
    }
    if not socket_path.exists():
        return record
    details = socket_path.stat()
    record.update(
        {
            "mode": stat.filemode(details.st_mode),
            "mode_octal": oct(stat.S_IMODE(details.st_mode)),
            "uid": details.st_uid,
            "gid": details.st_gid,
            "owner": pwd.getpwuid(details.st_uid).pw_name,
            "group": grp.getgrgid(details.st_gid).gr_name,
        }
    )
    return record


def summarize_blocked(
    run_id: str,
    run_dir: Path,
    target_commit: str,
    target_clean: bool,
    docker_probe: subprocess.CompletedProcess[str],
) -> dict[str, Any]:
    diagnostic = (docker_probe.stderr or docker_probe.stdout).strip()
    return {
        "experiment": EXPERIMENT,
        "run_id": run_id,
        "timestamp": utc_now(),
        "status": "BLOCKED_ENV",
        "blocking_stage": "docker_daemon_access",
        "blocking_condition": diagnostic,
        "docker_daemon_accessible": False,
        "ros_transport_executed": False,
        "actual_quest2ros2_node_executed": False,
        "robot_or_driver_used": False,
        "target_commit": target_commit,
        "target_clean_before": target_clean,
        "evidence_level": "NOT_EXECUTED",
        "claim_upgrade": "NOT_PERMITTED",
        "run_dir": str(run_dir.resolve()),
    }


def main() -> int:
    repo_root = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output-root",
        type=Path,
        default=repo_root / "semantic_validation" / "logs" / "quest2ros2_ros_runtime",
    )
    parser.add_argument("--run-id", default=run_id_now())
    parser.add_argument(
        "--target-root",
        type=Path,
        default=repo_root / "semantic_validation" / "targets" / "quest2ros2",
    )
    parser.add_argument("--image", default=DEFAULT_IMAGE)
    args = parser.parse_args()

    run_dir = args.output_root.resolve() / args.run_id
    if run_dir.exists():
        raise SystemExit(f"refusing to overwrite existing run directory: {run_dir}")
    run_dir.mkdir(parents=True)
    environment_log = run_dir / "environment.jsonl"

    target_commit_result = subprocess.run(
        ["git", "-C", str(args.target_root), "rev-parse", "HEAD"],
        text=True,
        capture_output=True,
        check=False,
    )
    target_commit = target_commit_result.stdout.strip() if target_commit_result.returncode == 0 else "UNKNOWN"
    target_status_result = subprocess.run(
        ["git", "-C", str(args.target_root), "status", "--porcelain"],
        text=True,
        capture_output=True,
        check=False,
    )
    target_clean = target_status_result.returncode == 0 and not target_status_result.stdout.strip()

    group_ids = os.getgroups()
    append_jsonl(
        environment_log,
        {
            "timestamp": utc_now(),
            "event": "host_identity",
            "uid": os.getuid(),
            "gid": os.getgid(),
            "user": pwd.getpwuid(os.getuid()).pw_name,
            "supplementary_gids": group_ids,
            "supplementary_groups": [grp.getgrgid(group_id).gr_name for group_id in group_ids],
            "host_ros2": shutil.which("ros2"),
            "host_colcon": shutil.which("colcon"),
        },
    )
    append_jsonl(environment_log, socket_record())
    append_jsonl(
        environment_log,
        {
            "timestamp": utc_now(),
            "event": "target_provenance",
            "target_root": str(args.target_root.resolve()),
            "target_commit": target_commit,
            "target_clean": target_clean,
            "target_status": target_status_result.stdout,
        },
    )

    command_record(environment_log, "id", ["id"])
    command_record(environment_log, "groups", ["groups"])
    command_record(environment_log, "docker_client_and_server_version", ["docker", "version"])
    docker_probe = command_record(
        environment_log,
        "docker_info",
        ["docker", "info", "--format", "{{json .ServerVersion}}"],
    )
    command_record(
        environment_log,
        "docker_images",
        ["docker", "images", "--no-trunc", "--format", "{{json .}}"],
    )
    command_record(
        environment_log,
        "docker_containers",
        ["docker", "ps", "-a", "--no-trunc", "--format", "{{json .}}"],
    )
    command_record(environment_log, "docker_compose_version", ["docker", "compose", "version"])
    compose_file = repo_root / "ros_env" / "compose.yaml"
    command_record(
        environment_log,
        "docker_compose_config",
        ["docker", "compose", "-f", str(compose_file), "config"],
        cwd=repo_root,
    )
    command_record(
        environment_log,
        "docker_compose_ps",
        ["docker", "compose", "-f", str(compose_file), "ps", "-a"],
        cwd=repo_root,
    )

    if docker_probe.returncode != 0:
        summary = summarize_blocked(
            args.run_id, run_dir, target_commit, target_clean, docker_probe
        )
        target_status_after = subprocess.run(
            ["git", "-C", str(args.target_root), "status", "--porcelain"],
            text=True,
            capture_output=True,
            check=False,
        )
        summary["target_clean_after"] = (
            target_status_after.returncode == 0 and not target_status_after.stdout.strip()
        )
        write_json(run_dir / "summary.json", summary)
        print(json.dumps(summary, sort_keys=True))
        return 0

    image_probe = command_record(
        environment_log,
        "runtime_image_inspect",
        ["docker", "image", "inspect", args.image],
    )
    if image_probe.returncode != 0:
        build_result = command_record(
            environment_log,
            "runtime_image_build",
            ["docker", "compose", "-f", str(compose_file), "build", "ros"],
            cwd=repo_root,
            timeout=900,
        )
        if build_result.returncode != 0:
            summary = {
                "experiment": EXPERIMENT,
                "run_id": args.run_id,
                "timestamp": utc_now(),
                "status": "BLOCKED_ENV",
                "blocking_stage": "runtime_image_build",
                "blocking_condition": (build_result.stderr or build_result.stdout).strip(),
                "docker_daemon_accessible": True,
                "ros_transport_executed": False,
                "actual_quest2ros2_node_executed": False,
                "robot_or_driver_used": False,
                "target_commit": target_commit,
                "target_clean_before": target_clean,
                "evidence_level": "NOT_EXECUTED",
                "claim_upgrade": "NOT_PERMITTED",
                "run_dir": str(run_dir),
            }
            write_json(run_dir / "summary.json", summary)
            print(json.dumps(summary, sort_keys=True))
            return 0

    inner_harness = repo_root / "semantic_validation" / "harness" / "quest2ros2_ros_transport_node.py"
    with tempfile.TemporaryDirectory(prefix="quest2ros2_ros_runtime_") as temporary:
        workspace = Path(temporary) / "runtime_ws"
        copy_target_workspace(args.target_root, workspace)
        container_name = args.run_id.replace("_", "-")[:63]
        container_command = (
            "set -e\n"
            "source /opt/ros/humble/setup.bash\n"
            "mkdir -p \"$HOME\"\n"
            "cd /runtime_ws\n"
            "colcon build --packages-select quest2ros q2r2_bringup "
            "--event-handlers console_direct+ --cmake-args -DBUILD_TESTING=OFF\n"
            "source /runtime_ws/install/setup.bash\n"
            "python3 /harness/quest2ros2_ros_transport_node.py "
            "--output-jsonl /evidence/transport.jsonl "
            "--summary-json /evidence/transport_summary.json "
            f"--target-commit {target_commit}\n"
        )
        docker_command = [
            "docker",
            "run",
            "--rm",
            "--name",
            container_name,
            "--network",
            "none",
            "--cap-drop",
            "ALL",
            "--security-opt",
            "no-new-privileges",
            "--user",
            f"{os.getuid()}:{os.getgid()}",
            "--env",
            "ROS_LOCALHOST_ONLY=1",
            "--env",
            "RMW_IMPLEMENTATION=rmw_fastrtps_cpp",
            "--env",
            "PYTHONDONTWRITEBYTECODE=1",
            "--env",
            "HOME=/tmp/quest2ros2-home",
            "--volume",
            f"{workspace}:/runtime_ws",
            "--volume",
            f"{inner_harness}:/harness/quest2ros2_ros_transport_node.py:ro",
            "--volume",
            f"{run_dir}:/evidence",
            args.image,
            "bash",
            "-lc",
            container_command,
        ]
        runtime_result = command_record(
            environment_log,
            "robot_free_ros_runtime",
            docker_command,
            timeout=300,
        )
        (run_dir / "container.stdout.txt").write_text(runtime_result.stdout, encoding="utf-8")
        (run_dir / "container.stderr.txt").write_text(runtime_result.stderr, encoding="utf-8")

    inner_summary_path = run_dir / "transport_summary.json"
    if inner_summary_path.exists():
        inner_summary = json.loads(inner_summary_path.read_text(encoding="utf-8"))
        status = inner_summary.get("status", "FAIL")
        evidence_level = inner_summary.get("evidence_level", "UNKNOWN")
        blocking_stage = None
        blocking_condition = None
    else:
        inner_summary = None
        status = "BLOCKED_ENV" if runtime_result.returncode != 0 else "FAIL"
        evidence_level = "NOT_EXECUTED"
        blocking_stage = "container_build_or_runtime"
        blocking_condition = (runtime_result.stderr or runtime_result.stdout).strip()

    target_status_after = subprocess.run(
        ["git", "-C", str(args.target_root), "status", "--porcelain"],
        text=True,
        capture_output=True,
        check=False,
    )
    summary = {
        "experiment": EXPERIMENT,
        "run_id": args.run_id,
        "timestamp": utc_now(),
        "status": status,
        "blocking_stage": blocking_stage,
        "blocking_condition": blocking_condition,
        "docker_daemon_accessible": True,
        "ros_transport_executed": inner_summary is not None,
        "actual_quest2ros2_node_executed": bool(
            inner_summary and inner_summary.get("actual_quest2ros2_node_executed")
        ),
        "robot_or_driver_used": False,
        "network_mode": "none",
        "target_commit": target_commit,
        "target_clean_before": target_clean,
        "target_clean_after": target_status_after.returncode == 0
        and not target_status_after.stdout.strip(),
        "evidence_level": evidence_level,
        "claim_upgrade": "PERMITTED" if status == "PASS" else "NOT_PERMITTED",
        "inner_summary": inner_summary,
        "run_dir": str(run_dir),
    }
    write_json(run_dir / "summary.json", summary)
    print(json.dumps(summary, sort_keys=True))
    return 0 if status in {"PASS", "DISPROVED", "BLOCKED_ENV"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
