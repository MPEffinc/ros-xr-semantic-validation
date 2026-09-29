#!/usr/bin/env python3
"""Spes UPSTREAM optional ROS 2 module -> actual ROS 2/DDS -> physical Raspberry Pi.

Why this exists alongside ``spes_ros_pi_runtime.py``
----------------------------------------------------
``spes_ros_pi_runtime.py`` drives a RESEARCH-CREATED adapter
(``spes_ros_callback_adapter.py``). This driver instead runs the **pinned
upstream** module ``teleop/ros2/__main__.py``, which is genuine Spes production
source and contains its own ``rclpy`` publisher. Nothing in the pinned target is
modified: the module is executed as ``python3 -m teleop.ros2`` with only its own
documented CLI flags and a standard ROS topic remap.

Upstream gate that had to be satisfied
--------------------------------------
``teleop/ros2/__main__.py`` refuses to publish while
``current_robot_pose_message is None``; that value normally arrives from a robot
on ``/current_pose``. Rather than stand up a fake robot publisher, this driver
uses the module's OWN ``--omit-current-pose`` flag, which upstream provides
precisely to run without a robot. No robot, driver, controller, or actuator is
started, and no ``/current_pose`` message is fabricated.

Evidence discipline
-------------------
The pose source is still SYNTHETIC WSS packets injected after the WebXR browser
frontend, so this stays E2 ``BOUNDARY_LIMITED_REPLAY``. The Pi sink establishes
``PI_RECEIVED`` only -- never native-consumer acceptance or actionability.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path

EXPERIMENT = "spes_upstream_ros2_pi"
POSE_TOPIC = "/robot_target_pose"
UPSTREAM_TOPIC = "target_frame"
REPO_ROOT = Path(__file__).resolve().parents[2]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def utc_run_id() -> str:
    return datetime.now(timezone.utc).strftime(f"{EXPERIMENT}_%Y%m%dT%H%M%SZ")


def log_event(path: Path, event: str, **fields) -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps({"event": event, "timestamp": now_iso(), **fields},
                                sort_keys=True) + "\n")


def run(cmd, **kwargs) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, **kwargs)


# The WSS client and the desktop-side observer both run inside the container.
# The observer is an ordinary ROS subscriber; it does not touch the upstream
# process and cannot influence what it publishes.
CLIENT_SOURCE = r'''
import json, os, ssl, sys, time
from datetime import datetime, timezone
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import PoseStamped
from websocket import create_connection

port = int(os.environ["SPES_PORT"])
count = int(os.environ["POSE_COUNT"])
step = float(os.environ["POSE_STEP"])
interval = float(os.environ["SEND_INTERVAL"])
settle = float(os.environ["DISCOVERY_SETTLE"])
out = os.environ["CLIENT_OUT"]

rclpy.init()
node = Node("spes_upstream_desktop_observer")
seen = []
node.create_subscription(
    PoseStamped, os.environ["POSE_TOPIC"],
    lambda m: seen.append({
        "desktop_observer_index": len(seen) + 1,
        "header_stamp": {"sec": int(m.header.stamp.sec),
                         "nanosec": int(m.header.stamp.nanosec)},
        "frame_id": m.header.frame_id,
        "position": {"x": m.pose.position.x, "y": m.pose.position.y,
                     "z": m.pose.position.z},
        "observe_monotonic_ns": time.monotonic_ns(),
        "observe_wall_utc": datetime.now(timezone.utc).isoformat(),
    }), 10)

# Give cross-host DDS discovery an unhurried window before any WSS packet is
# sent, so that a discovery race cannot be mistaken for message loss.
end = time.monotonic() + settle
while time.monotonic() < end:
    rclpy.spin_once(node, timeout_sec=0.05)

ws = create_connection("wss://127.0.0.1:%d/ws" % port, timeout=10,
                       sslopt={"cert_reqs": ssl.CERT_NONE, "check_hostname": False})
sent = []
for i in range(count):
    packet = {
        "position": {"x": 0.0, "y": round(i * step, 9), "z": 0.0},
        "orientation": {"x": 0.0, "y": 0.0, "z": 0.0, "w": 1.0},
        "move": True, "gripper": "open", "scale": 1.0, "device": "VR",
        "message": "questless synthetic source",
    }
    ws.send(json.dumps({"type": "pose", "data": packet}))
    sent.append({"wss_packet_index": i + 1,
                 "send_monotonic_ns": time.monotonic_ns(),
                 "send_wall_utc": datetime.now(timezone.utc).isoformat(),
                 "position": packet["position"]})
    end = time.monotonic() + interval
    while time.monotonic() < end:
        rclpy.spin_once(node, timeout_sec=0.01)
ws.close()

end = time.monotonic() + 3.0
while time.monotonic() < end:
    rclpy.spin_once(node, timeout_sec=0.05)

with open(out, "w") as handle:
    for record in sent:
        handle.write(json.dumps({"event": "wss_packet_sent", **record}, sort_keys=True) + "\n")
    for record in seen:
        handle.write(json.dumps({"event": "desktop_observed_publish", **record}, sort_keys=True) + "\n")
print(json.dumps({"wss_packets_sent": len(sent), "desktop_observed_publishes": len(seen)}))
node.destroy_node()
rclpy.shutdown()
'''

CONTAINER_SCRIPT = r"""
set -e
export HOME=/tmp/spes-home
mkdir -p "$HOME"
source /opt/ros/humble/setup.bash
export PYTHONPATH="/repo/semantic_validation/targets/spes_teleop:${PYTHONPATH:-}"
cd /tmp

# PINNED UPSTREAM PRODUCTION MODULE, unmodified, run with its own CLI flags only.
python3 -m teleop.ros2 --omit-current-pose --host 127.0.0.1 --port "$SPES_PORT" \
  --ros-args -r target_frame:=$POSE_TOPIC >/tmp/upstream.log 2>&1 &
UPSTREAM_PID=$!

for _ in $(seq 1 200); do
  if curl -sk --max-time 1 "https://127.0.0.1:$SPES_PORT/" >/dev/null 2>&1; then break; fi
  sleep 0.2
done

python3 /tmp/client.py
CLIENT_RC=$?

kill $UPSTREAM_PID 2>/dev/null || true
sleep 1
echo "===== UPSTREAM MODULE LOG ====="
cat /tmp/upstream.log || true
exit $CLIENT_RC
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", default=utc_run_id())
    parser.add_argument("--image", default="ros-xr-humble:local")
    parser.add_argument("--pi-host", default="rosxr")
    parser.add_argument("--domain-id", default="74")
    parser.add_argument("--spes-port", type=int, default=4453)
    parser.add_argument("--pose-count", type=int, default=30)
    parser.add_argument("--pose-step", type=float, default=0.02)
    parser.add_argument("--send-interval", type=float, default=0.1)
    parser.add_argument("--discovery-settle", type=float, default=20.0)
    parser.add_argument("--sink-ceiling-seconds", type=int, default=300)
    parser.add_argument("--docker-wrapper", default="sg docker -c")
    parser.add_argument(
        "--output-dir", type=Path,
        default=REPO_ROOT / "semantic_validation" / "results" / "runs")
    args = parser.parse_args()

    run_dir = args.output_dir / args.run_id
    if run_dir.exists():
        raise SystemExit(f"refusing to overwrite {run_dir}")
    run_dir.mkdir(parents=True)
    env_log = run_dir / "environment.jsonl"

    target_root = REPO_ROOT / "semantic_validation" / "targets" / "spes_teleop"
    target_commit = run(["git", "-C", str(target_root), "rev-parse", "HEAD"]).stdout.strip()
    status_before = run(["git", "-C", str(target_root), "status", "--short"]).stdout
    log_event(env_log, "target_provenance", target_root=str(target_root),
              target_commit=target_commit,
              target_clean_before=status_before.strip() == "",
              upstream_module="teleop/ros2/__main__.py",
              upstream_module_modified=False)
    log_event(env_log, "safety_register", xr_hardware_used=False,
              robot_or_driver_used=False, actuator_used=False,
              current_pose_publisher_fabricated=False,
              current_pose_bypass="upstream --omit-current-pose flag")

    client_path = run_dir / "client.py"
    client_path.write_text(CLIENT_SOURCE)

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
    log_event(env_log, "pi_sink_command", host=args.pi_host, command=pi_cmd)
    pi_proc = subprocess.Popen(
        ["ssh", "-o", "BatchMode=yes", args.pi_host, pi_cmd],
        stdout=(run_dir / "pi_sink.stdout.txt").open("w"),
        stderr=subprocess.STDOUT)

    docker_cmd = [
        "docker", "run", "--rm", "--network", "host",
        "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
        "--user", f"{os.getuid()}:{os.getgid()}",
        "-e", "PYTHONDONTWRITEBYTECODE=1",
        "-e", f"ROS_DOMAIN_ID={args.domain_id}",
        "-e", "RMW_IMPLEMENTATION=rmw_fastrtps_cpp",
        "-e", "ROS_LOCALHOST_ONLY=0",
        "-e", "HOME=/tmp/spes-home",
        "-e", f"SPES_PORT={args.spes_port}",
        "-e", f"POSE_TOPIC={POSE_TOPIC}",
        "-e", f"POSE_COUNT={args.pose_count}",
        "-e", f"POSE_STEP={args.pose_step}",
        "-e", f"SEND_INTERVAL={args.send_interval}",
        "-e", f"DISCOVERY_SETTLE={args.discovery_settle}",
        "-e", "CLIENT_OUT=/tmp/out/desktop.jsonl",
        "-v", f"{REPO_ROOT}:/repo",
        "-v", f"{client_path}:/tmp/client.py:ro",
        "-v", f"{run_dir}:/tmp/out",
        args.image, "bash", "-lc", CONTAINER_SCRIPT,
    ]
    log_event(env_log, "container_command", command=docker_cmd)

    status = "UNKNOWN"
    try:
        wrapper = args.docker_wrapper.split()
        shell_cmd = " ".join(_quote(part) for part in docker_cmd)
        container = run(wrapper + [shell_cmd] if wrapper else docker_cmd,
                        timeout=args.sink_ceiling_seconds + 120)
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
    pi_records = [json.loads(l) for l in collect.stdout.splitlines() if l.strip()]

    desktop_path = run_dir / "desktop.jsonl"
    desktop = ([json.loads(l) for l in desktop_path.read_text().splitlines() if l.strip()]
               if desktop_path.exists() else [])
    sent = [r for r in desktop if r["event"] == "wss_packet_sent"]
    observed = [r for r in desktop if r["event"] == "desktop_observed_publish"]

    def stamp(record, field="header_stamp"):
        return (record[field]["sec"], record[field]["nanosec"])

    observed_stamps = [stamp(r) for r in observed]
    pi_stamps = [stamp(r) for r in pi_records if r.get("header_stamp")]
    matched = sum(1 for s in observed_stamps if s in set(pi_stamps))

    summary = {
        "experiment": EXPERIMENT,
        "run_id": args.run_id,
        "timestamp": now_iso(),
        "target_commit": target_commit,
        "target_clean_before": status_before.strip() == "",
        "target_clean_after": status_after.strip() == "",
        "evidence_level": "E2_BOUNDARY_LIMITED_REPLAY",
        "source": "SYNTHETIC_WSS_POST_BROWSER_GATE",
        "ros_publisher_provenance": "PINNED_UPSTREAM teleop/ros2/__main__.py",
        "upstream_module_modified": False,
        "xr_hardware_used": False,
        "robot_or_driver_used": False,
        "ros_domain_id": args.domain_id,
        "pose_topic_after_remap": POSE_TOPIC,
        "upstream_topic_before_remap": UPSTREAM_TOPIC,
        "wss_packets_sent": len(sent),
        "desktop_observed_publish_count": len(observed),
        "pi_received_count": len(pi_records),
        "observed_stamps_found_on_pi": matched,
        "stamp_uniqueness_desktop": len(set(observed_stamps)) == len(observed_stamps),
        "stamp_uniqueness_pi": len(set(pi_stamps)) == len(pi_stamps),
        "pi_frames_observed": sorted({r.get("frame_id") for r in pi_records if r.get("frame_id")}),
        "downstream_consequence": "PI_RECEIVED" if pi_records else "NO_OUTPUT",
        "container_status": status,
        "status": ("PASS" if status == "PASS" and observed
                   and matched == len(observed) == len(pi_records) else "INCOMPLETE"),
        "claim_limit": ("Observation endpoint reception only. PI_RECEIVED != NATIVE "
                        "CONSUMER ACCEPTED. Synthetic source; no XR hardware."),
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
