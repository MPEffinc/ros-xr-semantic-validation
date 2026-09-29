#!/usr/bin/env python3
"""Spes accepted-callback -> research ROS adapter -> actual ROS 2/DDS -> physical Pi sink.

What this driver actually executes
----------------------------------
1. Starts ``semantic_robot_sink`` on the physical Raspberry Pi (``rosxr``,
   10.10.10.2) over the dedicated research Ethernet, subscribed to
   ``/robot_target_pose``.
2. Runs ``spes_ros_pi_smoke.py`` inside the ``ros-xr-humble:local`` container
   with host networking, so the pinned Spes FastAPI/uvicorn WSS server, the
   pinned ``Teleop.__update`` control calculation, the research ROS adapter and
   the rclpy publisher all run for real and DDS traffic leaves the desktop.
3. Stops the sink, copies the Pi-side JSONL back, and correlates.

Evidence discipline
-------------------
* The pose source is SYNTHETIC (a harness-authored WSS packet sequence entering
  the pinned WSS route). No Quest, no headset, no robot, no driver, no actuator.
* Spes is **not** a native XR->ROS framework. The ROS hop exists only because of
  the research-created ``spes_ros_callback_adapter``. This run must never be
  counted as a native XR->ROS implementation.
* ``PI_RECEIVED`` is reception by an observation endpoint with
  ``accept_decision`` hardcoded to ``ACCEPTED_NO_SEMANTIC_GATING``. It is not
  native-consumer acceptance and not actionability.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

EXPERIMENT = "spes_ros_pi"
POSE_TOPIC = "/robot_target_pose"
REPO_ROOT = Path(__file__).resolve().parents[2]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def utc_run_id() -> str:
    return datetime.now(timezone.utc).strftime(f"{EXPERIMENT}_%Y%m%dT%H%M%SZ")


def log_event(path: Path, event: str, **fields) -> None:
    record = {"event": event, "timestamp": now_iso(), **fields}
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, sort_keys=True) + "\n")


def run(cmd, **kwargs) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, **kwargs)


CONTAINER_SCRIPT = """
set -e
export HOME=/tmp/spes-home
mkdir -p "$HOME"
source /opt/ros/humble/setup.bash
cd /repo/semantic_validation/harness
python3 spes_ros_pi_smoke.py \
  --run-id "$RUN_ID" \
  --result-dir "/repo/$RESULT_REL/desktop" \
  --topic "$POSE_TOPIC" \
  --pose-count "$POSE_COUNT" \
  --pose-step "$POSE_STEP" \
  --send-interval "$SEND_INTERVAL" \
  --require-subscribers "$REQUIRE_SUBSCRIBERS"
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", default=utc_run_id())
    parser.add_argument("--image", default="ros-xr-humble:local")
    parser.add_argument("--pi-host", default="rosxr")
    parser.add_argument("--domain-id", default="74")
    parser.add_argument("--pose-count", type=int, default=30)
    parser.add_argument("--pose-step", type=float, default=0.02)
    parser.add_argument("--send-interval", type=float, default=0.1)
    parser.add_argument("--require-subscribers", type=int, default=1)
    parser.add_argument("--sink-ceiling-seconds", type=int, default=300)
    parser.add_argument("--docker-wrapper", default="sg docker -c")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=REPO_ROOT / "semantic_validation" / "results" / "runs",
    )
    args = parser.parse_args()

    run_dir = args.output_dir / args.run_id
    if run_dir.exists():
        raise SystemExit(f"refusing to overwrite {run_dir}")
    run_dir.mkdir(parents=True)
    result_rel = run_dir.relative_to(REPO_ROOT)
    env_log = run_dir / "environment.jsonl"

    target_root = REPO_ROOT / "semantic_validation" / "targets" / "spes_teleop"
    target_commit = run(["git", "-C", str(target_root), "rev-parse", "HEAD"]).stdout.strip()
    status_before = run(["git", "-C", str(target_root), "status", "--short"]).stdout
    log_event(
        env_log, "target_provenance",
        target_root=str(target_root),
        target_commit=target_commit,
        target_clean_before=status_before.strip() == "",
        pinned_revision_file=str(REPO_ROOT / "semantic_validation/frameworks/spes/PINNED_REVISION"),
    )
    log_event(env_log, "host_identity", id=run(["id"]).stdout.strip())
    log_event(
        env_log, "safety_register",
        xr_hardware_used=False, robot_or_driver_used=False, actuator_used=False,
        native_xr_to_ros_framework=False,
        ros_hop_origin="RESEARCH_CREATED_ADAPTER: semantic_validation/harness/spes_ros_callback_adapter.py",
    )

    # ---- Pi sink ----
    # ABSOLUTE path on purpose: a leading "~" inside a ROS `-p name:=value`
    # argument is NOT tilde-expanded and creates a literal "~" directory.
    pi_log_dir = f"/home/cclab/spes_logs/{args.run_id}"
    pi_cmd = (
        "source /opt/ros/humble/setup.bash && "
        "source ~/ros2_ws/install/setup.bash && "
        f"export ROS_DOMAIN_ID={args.domain_id} && "
        "export RMW_IMPLEMENTATION=rmw_fastrtps_cpp && "
        "export ROS_LOCALHOST_ONLY=0 && "
        f"mkdir -p {pi_log_dir} && "
        f"timeout {args.sink_ceiling_seconds} ros2 run semantic_robot_endpoint semantic_robot_sink "
        f"--ros-args -p pose_topic:={POSE_TOPIC} "
        f"-p log_dir:={pi_log_dir} "
        "-p tf_topic:=/tf_unused_by_this_run"
    )
    log_event(env_log, "pi_sink_command", host=args.pi_host, command=pi_cmd, log_dir=pi_log_dir)
    pi_proc = subprocess.Popen(
        ["ssh", "-o", "BatchMode=yes", args.pi_host, pi_cmd],
        stdout=(run_dir / "pi_sink.stdout.txt").open("w"),
        stderr=subprocess.STDOUT,
    )

    docker_cmd = [
        "docker", "run", "--rm",
        "--network", "host",
        "--cap-drop", "ALL",
        "--security-opt", "no-new-privileges",
        "--user", f"{os.getuid()}:{os.getgid()}",
        "-e", "PYTHONDONTWRITEBYTECODE=1",
        "-e", f"ROS_DOMAIN_ID={args.domain_id}",
        "-e", "RMW_IMPLEMENTATION=rmw_fastrtps_cpp",
        "-e", "ROS_LOCALHOST_ONLY=0",
        "-e", "HOME=/tmp/spes-home",
        "-e", f"RUN_ID={args.run_id}",
        "-e", f"RESULT_REL={result_rel}",
        "-e", f"POSE_TOPIC={POSE_TOPIC}",
        "-e", f"POSE_COUNT={args.pose_count}",
        "-e", f"POSE_STEP={args.pose_step}",
        "-e", f"SEND_INTERVAL={args.send_interval}",
        "-e", f"REQUIRE_SUBSCRIBERS={args.require_subscribers}",
        "-v", f"{REPO_ROOT}:/repo",
        "-w", "/repo",
        args.image,
        "bash", "-lc", CONTAINER_SCRIPT,
    ]
    log_event(env_log, "container_command", command=docker_cmd)

    status = "UNKNOWN"
    try:
        wrapper = args.docker_wrapper.split()
        if wrapper:
            shell_cmd = " ".join(_quote(part) for part in docker_cmd)
            full = wrapper + [shell_cmd]
        else:
            full = docker_cmd
        container = run(full, timeout=args.sink_ceiling_seconds + 120)
        (run_dir / "container.stdout.txt").write_text(container.stdout)
        (run_dir / "container.stderr.txt").write_text(container.stderr)
        log_event(env_log, "container_result", returncode=container.returncode)
        status = "PASS" if container.returncode == 0 else "FAIL"
    finally:
        run(["ssh", "-o", "BatchMode=yes", args.pi_host,
             "pkill -INT -f semantic_robot_sink || true"])
        try:
            pi_proc.wait(timeout=60)
        except subprocess.TimeoutExpired:
            pi_proc.kill()

    status_after = run(["git", "-C", str(target_root), "status", "--short"]).stdout
    log_event(env_log, "target_clean_after", clean=status_after.strip() == "")

    collect = run(["ssh", "-o", "BatchMode=yes", args.pi_host, f"cat {pi_log_dir}/*.jsonl"])
    (run_dir / "pi_sink.jsonl").write_text(collect.stdout)
    pi_records = [json.loads(line) for line in collect.stdout.splitlines() if line.strip()]

    adapter_path = run_dir / "desktop" / "adapter.jsonl"
    adapter_records = (
        [json.loads(line) for line in adapter_path.read_text().splitlines() if line.strip()]
        if adapter_path.exists() else []
    )

    correlation = None
    if adapter_records and pi_records:
        analyze = run([
            sys.executable,
            str(REPO_ROOT / "semantic_validation/harness/analyze_spes_ros_pi.py"),
            "--adapter", str(adapter_path),
            "--pi", str(run_dir / "pi_sink.jsonl"),
            "--output", str(run_dir / "correlation.json"),
        ])
        (run_dir / "analyze.stdout.txt").write_text(analyze.stdout + analyze.stderr)
        if (run_dir / "correlation.json").exists():
            correlation = json.loads((run_dir / "correlation.json").read_text())

    summary = {
        "experiment": EXPERIMENT,
        "run_id": args.run_id,
        "timestamp": now_iso(),
        "target_commit": target_commit,
        "target_clean_before": status_before.strip() == "",
        "target_clean_after": status_after.strip() == "",
        "evidence_level": "E2_BOUNDARY_LIMITED_REPLAY",
        "source": "SYNTHETIC_WSS_POST_BROWSER_GATE",
        "xr_hardware_used": False,
        "robot_or_driver_used": False,
        "native_xr_to_ros_framework": False,
        "ros_hop_provenance": "RESEARCH_CREATED_ADAPTER",
        "ros_domain_id": args.domain_id,
        "pose_topic": POSE_TOPIC,
        "pi_host": args.pi_host,
        "pi_log_dir": pi_log_dir,
        "wss_packets_sent": args.pose_count,
        "adapter_published_count": len(adapter_records),
        "pi_received_count": len(pi_records),
        "server_update_index_final": (
            max((r.get("server_update_index") or 0) for r in adapter_records)
            if adapter_records else 0
        ),
        "correlation": correlation,
        "downstream_consequence": "PI_RECEIVED" if pi_records else "NO_OUTPUT",
        "container_status": status,
        "status": (
            "PASS" if status == "PASS" and correlation and correlation.get("result") == "PASS"
            else "INCOMPLETE"
        ),
        "claim_limit": (
            "Observation endpoint reception only. No native Spes ROS consumer, no "
            "actuator, no XR hardware. PI_RECEIVED != NATIVE CONSUMER ACCEPTED."
        ),
    }
    (run_dir / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True))
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if summary["status"] == "PASS" else 1


def _quote(part: str) -> str:
    if part and all(c.isalnum() or c in "-_=:./," for c in part):
        return part
    return "'" + part.replace("'", "'\\''") + "'"


if __name__ == "__main__":
    raise SystemExit(main())
