# OpenArmX UDP Source-Time Runtime

## Scope

- Upstream repository: `openarmx/openarmx_teleop_vr`
- Pinned revision: `a3da7411b3d6ecaa7f94df859e07fb642aec859b`
- Runtime: isolated `ros-xr-humble:local` container
- `ROS_DOMAIN_ID=47`, `ROS_LOCALHOST_ONLY=1`, `--network none`
- Physical robot, CAN bringup, and actuator paths were not started.
- Evidence level: `E2 SYNTHETIC_RUNTIME`

The exercised production path was:

```text
synthetic UDP datagram
-> production openarmx_teleop_bridge_vr_node
-> actual ROS 2 geometry_msgs/msg/PoseStamped
-> research subscriber
```

The injection point is the production UDP wire boundary, before the bridge's
timestamp selection and ROS publication logic. The production C++ source was
not modified.

## Build

Both pinned packages built successfully in an isolated ROS 2 Humble workspace:

```bash
source /opt/ros/humble/setup.bash
colcon build \
  --packages-select openarmx_teleop_bridge_vr openarmx_teleop_vr \
  --event-handlers console_direct+
```

The bridge was run on test-only UDP port `55100`:

```bash
ros2 run openarmx_teleop_bridge_vr openarmx_teleop_bridge_vr_node \
  --ros-args -p listen_port:=55100
```

## Trials

All cases used the same right-controller pose, orientation, trigger, grip,
button, and rate fields. Only `timestamp_ns` changed.

| Trial | UDP `timestamp_ns` | ROS header ns | Equal | Frame |
| --- | ---: | ---: | --- | --- |
| A_CURRENT_POSITIVE | `1789366749510582464` | `1789366749510582464` | yes | `pico_hmd` |
| B_DELIBERATELY_OLD | `946684800123456789` | `946684800123456789` | yes | `pico_hmd` |
| C_ZERO_FALLBACK | `0` | `1789366749912283262` | no | `pico_hmd` |

The C fallback header was generated 72,415 ns after the harness recorded its
send wall time. The exact gap is scheduling-dependent; the relevant observed
behavior is that a non-positive value did not remain zero and was replaced by
the bridge's ROS clock time.

For every case, the actual output pose was unchanged:

```text
position = (0.125, -0.250, 0.375)
orientation = (0.0, 0.0, 0.0, 1.0)
```

## Runtime Finding

At the production UDP-to-ROS bridge boundary:

- a positive source `timestamp_ns` is preserved exactly in
  `PoseStamped.header.stamp`;
- a deliberately old but positive timestamp is also preserved exactly;
- `timestamp_ns <= 0` is a supported fallback case and is transformed to the
  bridge's current ROS time;
- the bridge accepted the deliberately old source time and published the pose;
  this run observed no bridge-level source-age rejection.

This supports a bounded source-time claim only. It does not establish whether
the closed downstream teleoperation core performs an equivalent freshness
decision.

## Native Downstream Attempt

The pinned `openarmx_teleop_vr` package built successfully, but its actual
entrypoint failed before node construction:

```text
ModuleNotFoundError: No module named 'openarmx_arm_driver'
[ros2run]: Process exited with failure 1
```

The missing module supplies `TeleopConfig`, `PinocchioTeleopCore`, and its input
frame types. It is neither provided by the pinned repository nor declared as an
installable dependency in `setup.py`. No research-created replacement was used,
so no claim is made about native IK acceptance, command generation, or an
actuator boundary.

## Evidence Files

- `semantic_validation/harness/openarmx_udp_timestamp_trials.py`
- `semantic_validation/results/runs/openarmx_udp_e2_20260914_01/build.log`
- `semantic_validation/results/runs/openarmx_udp_e2_20260914_01/bridge.log`
- `semantic_validation/results/runs/openarmx_udp_e2_20260914_01/harness.log`
- `semantic_validation/results/runs/openarmx_udp_e2_20260914_01/trials.json`
- `semantic_validation/results/runs/openarmx_udp_e2_20260914_01/downstream_attempt.log`

## Boundary

Confirmed: `UDP_RECEIVED -> ROS_PUBLISHED` with timestamp transformation
classified above.

Not confirmed: native XR frontend behavior, native downstream consumer
acceptance, robot command, CAN write, or actuator execution.
