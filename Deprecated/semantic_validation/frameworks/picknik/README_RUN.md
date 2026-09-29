# PickNik preparation and runbook

## Verified source validation

```bash
python3 semantic_validation/harness/picknik_deep_validation.py \
  --output semantic_validation/logs/v2_multi_framework_20260907T000002Z/picknik_source_dataflow.jsonl \
  --summary semantic_validation/logs/v2_multi_framework_20260907T000002Z/picknik_source_dataflow_summary.json
python3 semantic_validation/harness/picknik_deep_validation_selftest.py
```

2026-09-07 result: validator 33/33 `PASS`; analyzer self-test 4/4 `OK`. Both are E1/source or
harness checks, never Unity/Quest/ROS runtime.

## Verified Quest-less backend

The official `Unity-Technologies/ROS-TCP-Endpoint` ROS 2 branch
`main-ros2@54c1a64b6d5ef6ffa0a0431570bb74329b79b15b` (Apache-2.0, optional ignored checkout at
`ros_env/ros2_ws/src/ros_tcp_endpoint`) was built in the isolated Humble workspace.  The
container has `rclpy`, `nav_msgs`, `tf2_msgs`, and `geometry_msgs`; `ros2 run ros_tcp_endpoint
default_server_endpoint --ros-args -p ROS_IP:=127.0.0.1 -p ROS_TCP_PORT:=10000` reached
`Starting server`.  This is endpoint readiness only: no Unity client, ROS-TCP message, Pi
observation, MoveIt Pro consumer, robot, or Quest evidence was generated.

## Remaining blocker

The project requests Unity `6000.1.6f1`.  The official Unity CLI `1.0.0-beta.8` is installed and
its Android dry-run resolved the requested editor/modules, but the actual editor installation did
not complete; `unity editors` still reports it uninstalled.  ADB exists and no device is attached.
The disposable staging and future T1/Pi procedure are in
`semantic_validation/results/PICKNIK_HW_READY.md`; use requires an authorized Quest and remains
robot-free.
