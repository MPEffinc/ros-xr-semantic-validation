#!/usr/bin/env python3
"""Quest2ROS2 in-repo SimulationInput -> actual production controller -> DDS -> Pi sink.

This differs from ``run_quest2ros2_ros_runtime.py`` in three ways:

1. the pose source is the framework's OWN in-repo simulator
   (``q2r2_bringup/SimulationInput.py``), not a harness-authored publisher;
2. the container uses host networking so the actual DDS traffic crosses the
   dedicated research Ethernet to the physical Raspberry Pi; and
3. the observation endpoint is the Pi ``semantic_robot_sink``, pointed directly
   at the framework's own production output topic so no republishing hop is
   introduced.

Evidence discipline: the source is still synthetic (a circle generator), so the
result is E2 ``SYNTHETIC_RUNTIME``. No Quest, robot, driver, CLIK controller, or
gripper action server is used. The Pi sink only sets ``PI_RECEIVED``.

The pinned upstream target is copied to a temporary workspace; colcon never
writes into the pinned checkout.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path

EXPERIMENT = "quest2ros2_simulationinput_pi"
PRODUCTION_OUTPUT_TOPIC = "/bh_robot/right_arm_clik_controller/target_frame"
PRODUCTION_INPUT_TOPIC = "/q2r_right_hand_pose"
BASE_FRAME = "bh_robot_base"
EE_FRAME = "right_arm_link_ee"


def utc_run_id() -> str:
    return datetime.now(timezone.utc).strftime(f"{EXPERIMENT}_%Y%m%dT%H%M%SZ")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def log_event(path: Path, event: str, **fields) -> None:
    record = {"event": event, "timestamp": now_iso(), **fields}
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, sort_keys=True) + "\n")


def run(cmd, **kwargs) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, **kwargs)


def stage_target(target_root: Path, workspace: Path) -> None:
    """Copy the pinned target into a disposable colcon workspace."""
    source_root = workspace / "src"
    source_root.mkdir(parents=True, exist_ok=True)

    def ignore(directory, names):
        return {n for n in names if n in {".git", "__pycache__", "Files_for_msg_pkg"}}

    shutil.copytree(target_root, source_root / "quest2ros2", ignore=ignore)
    # The controllers import `quest2ros.msg`; upstream README builds that package
    # from Files_for_msg_pkg. Reproduce that exactly.
    shutil.copytree(target_root / "Files_for_msg_pkg", source_root / "quest2ros")


CONTAINER_SCRIPT = f"""
set -e
source /opt/ros/humble/setup.bash
mkdir -p "$HOME"
cd /runtime_ws
colcon build --packages-select quest2ros q2r2_bringup \
  --event-handlers console_direct+ --cmake-args -DBUILD_TESTING=OFF
source /runtime_ws/install/setup.bash

# TF fixture only: the pinned controller looks up base->end-effector before it
# will publish. No robot, controller_manager, or driver is started.
ros2 run tf2_ros static_transform_publisher \
  0.4 -0.1 0.3 0 0 0 {BASE_FRAME} {EE_FRAME} >/tmp/tf.log 2>&1 &
TF_PID=$!
sleep 3

# The framework's OWN in-repo simulator, unmodified.
ros2 run q2r2_bringup SimulationInput --ros-args -p side:=right -p mode:=teleop \
  >/tmp/sim.log 2>&1 &
SIM_PID=$!

# The actual pinned production consumer.
ros2 run q2r2_bringup right_arm_controller >/tmp/ctrl.log 2>&1 &
CTRL_PID=$!

# Phase 1: the framework's own simulator alone. Its SimulationInput holds
# button_lower permanently True; the pinned controller toggles allow_pose_update
# on a RISING EDGE, so that single first edge flips streaming from its default
# ENABLED to DISABLED. Observe that for PHASE1_SECONDS.
sleep "$PHASE1_SECONDS"

# Phase 2: emit one operator-equivalent button RELEASE on the framework's own
# inputs topic. This is the minimum action a human operator performs on a real
# headset; it resets the controller's edge latch so the simulator's continuing
# True forms a second rising edge and re-enables streaming. Nothing in the
# pinned target is modified.
python3 - <<'PY' >/tmp/rearm.log 2>&1
import rclpy
from rclpy.node import Node
from quest2ros.msg import OVR2ROSInputs

rclpy.init()
node = Node("harness_operator_rearm")
pub = node.create_publisher(OVR2ROSInputs, "/q2r_right_hand_inputs", 10)
msg = OVR2ROSInputs()
msg.button_lower = False
msg.button_upper = False
for _ in range(5):
    pub.publish(msg)
    rclpy.spin_once(node, timeout_sec=0.05)
node.get_logger().info("published operator-equivalent button_lower release")
node.destroy_node()
rclpy.shutdown()
PY

sleep "$PHASE2_SECONDS"

ros2 topic list > /tmp/topics.log 2>&1 || true

kill $CTRL_PID $SIM_PID $TF_PID 2>/dev/null || true
sleep 2
echo "===== SIMULATION INPUT ====="; cat /tmp/sim.log || true
echo "===== ARM CONTROLLER ====="; cat /tmp/ctrl.log || true
echo "===== OPERATOR REARM ====="; cat /tmp/rearm.log || true
echo "===== TOPICS ====="; cat /tmp/topics.log || true
"""


def main() -> int:
    repo_root = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", default=utc_run_id())
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=repo_root / "semantic_validation" / "logs" / EXPERIMENT,
    )
    parser.add_argument(
        "--target-root",
        type=Path,
        default=repo_root / "semantic_validation" / "targets" / "quest2ros2",
    )
    parser.add_argument("--image", default="ros-xr-humble:local")
    parser.add_argument("--pi-host", default="rosxr")
    parser.add_argument("--phase1-seconds", type=int, default=12)
    parser.add_argument("--phase2-seconds", type=int, default=18)
    parser.add_argument("--sink-ceiling-seconds", type=int, default=900)
    args = parser.parse_args()
    args.run_seconds = args.phase1_seconds + args.phase2_seconds

    run_dir = args.output_dir / args.run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    env_log = run_dir / "environment.jsonl"

    target_commit = run(
        ["git", "-C", str(args.target_root), "rev-parse", "HEAD"]
    ).stdout.strip()
    target_status_before = run(
        ["git", "-C", str(args.target_root), "status", "--short"]
    ).stdout
    log_event(
        env_log,
        "target_provenance",
        target_root=str(args.target_root),
        target_commit=target_commit,
        target_clean_before=target_status_before.strip() == "",
    )

    identity = run(["id"]).stdout.strip()
    log_event(env_log, "host_identity", id=identity)

    # ---- Pi sink, pointed at the framework's own production output topic ----
    pi_run_marker = f"{args.run_id}"
    # Absolute path: a leading "~" inside a `-p name:=value` argument is NOT
    # tilde-expanded by the remote shell and would create a literal "~" directory.
    pi_log_dir = f"/home/cclab/semantic_robot_endpoint_logs/{pi_run_marker}"
    pi_cmd = (
        "source /opt/ros/humble/setup.bash && "
        "source ~/ros2_ws/install/setup.bash && "
        f"mkdir -p {pi_log_dir} && "
        # Generous ceiling: the container must colcon-build the pinned target
        # first, which takes minutes. The harness terminates the sink explicitly
        # once the container exits, so this bound is only a safety net.
        f"timeout {args.sink_ceiling_seconds} ros2 run semantic_robot_endpoint semantic_robot_sink "
        f"--ros-args -p pose_topic:={PRODUCTION_OUTPUT_TOPIC} "
        f"-p log_dir:={pi_log_dir} "
        "-p tf_topic:=/tf_unused_by_this_run"
    )
    log_event(env_log, "pi_sink_command", host=args.pi_host, command=pi_cmd)
    pi_proc = subprocess.Popen(
        ["ssh", "-o", "BatchMode=yes", args.pi_host, pi_cmd],
        stdout=(run_dir / "pi_sink.stdout.txt").open("w"),
        stderr=subprocess.STDOUT,
    )

    status = "UNKNOWN"
    try:
        with tempfile.TemporaryDirectory(prefix=f"{EXPERIMENT}_") as temporary:
            workspace = Path(temporary) / "runtime_ws"
            stage_target(args.target_root, workspace)
            log_event(env_log, "workspace_staged", workspace=str(workspace))

            docker_cmd = [
                "docker", "run", "--rm",
                "--network", "host",
                "--cap-drop", "ALL",
                "--security-opt", "no-new-privileges",
                "--user", f"{os.getuid()}:{os.getgid()}",
                "-e", "PYTHONDONTWRITEBYTECODE=1",
                "-e", "ROS_DOMAIN_ID=0",
                "-e", "RMW_IMPLEMENTATION=rmw_fastrtps_cpp",
                "-e", "ROS_LOCALHOST_ONLY=0",
                "-e", f"PHASE1_SECONDS={args.phase1_seconds}",
                "-e", f"PHASE2_SECONDS={args.phase2_seconds}",
                "-e", "HOME=/tmp/q2r2-home",
                "-v", f"{workspace}:/runtime_ws",
                "-w", "/runtime_ws",
                args.image,
                "bash", "-lc", CONTAINER_SCRIPT,
            ]
            log_event(env_log, "container_command", command=docker_cmd[:12] + ["..."])
            container = run(docker_cmd, timeout=args.run_seconds + 420)
            (run_dir / "container.stdout.txt").write_text(container.stdout)
            (run_dir / "container.stderr.txt").write_text(container.stderr)
            log_event(env_log, "container_result", returncode=container.returncode)
            status = "PASS" if container.returncode == 0 else "FAIL"
    finally:
        # The sink was started before the container build; stop it now that the
        # observation window has closed.
        run(["ssh", "-o", "BatchMode=yes", args.pi_host, "pkill -INT -f semantic_robot_sink || true"])
        try:
            pi_proc.wait(timeout=60)
        except subprocess.TimeoutExpired:
            pi_proc.kill()

    target_status_after = run(
        ["git", "-C", str(args.target_root), "status", "--short"]
    ).stdout

    # ---- collect the Pi-side observation ----
    collect = run(
        ["ssh", "-o", "BatchMode=yes", args.pi_host, f"cat {pi_log_dir}/*.jsonl"]
    )
    (run_dir / "pi_sink.jsonl").write_text(collect.stdout)
    pi_records = [json.loads(line) for line in collect.stdout.splitlines() if line.strip()]

    container_out = (run_dir / "container.stdout.txt").read_text(errors="replace")
    disabled_events = container_out.count("pose streaming is now **DISABLED")
    enabled_events = container_out.count("pose streaming is now **ENABLED")
    published_events = container_out.count("Published new target pose")

    summary = {
        "experiment": EXPERIMENT,
        "run_id": args.run_id,
        "timestamp": now_iso(),
        "evidence_level": "E2_SYNTHETIC_RUNTIME",
        "replay_subclass": "N/A_SYNTHETIC_SOURCE",
        "source": "in-repo q2r2_bringup/SimulationInput.py (circle generator)",
        "xr_hardware_used": False,
        "robot_or_driver_used": False,
        "clik_controller_present": False,
        "gripper_action_server_present": False,
        "target_commit": target_commit,
        "target_clean_before": target_status_before.strip() == "",
        "target_clean_after": target_status_after.strip() == "",
        "production_input_topic": PRODUCTION_INPUT_TOPIC,
        "production_output_topic": PRODUCTION_OUTPUT_TOPIC,
        "pi_host": args.pi_host,
        "arming_streaming_disabled_events": disabled_events,
        "arming_streaming_enabled_events": enabled_events,
        "controller_published_target_events": published_events,
        "own_simulator_alone_disables_streaming": disabled_events >= 1,
        "pi_received_count": len(pi_records),
        "pi_frames_observed": sorted({r.get("frame_id") for r in pi_records if r.get("frame_id")}),
        "downstream_consequence": "PI_RECEIVED" if pi_records else "NO_OUTPUT",
        "container_status": status,
        "status": "PASS" if (status == "PASS" and pi_records) else "INCOMPLETE",
    }
    (run_dir / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True))
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if summary["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
