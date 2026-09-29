# Quest2ROS2 in-repo simulator → production node → DDS → Raspberry Pi

## Result

**`PASS`** — canonical run `quest2ros2_simulationinput_pi_20260907T053724Z`.

| Axis | Value |
| --- | --- |
| Evidence level | **E2 `SYNTHETIC_RUNTIME`** |
| Replay subclass | N/A — the source is a synthetic generator, not a replayed trace |
| Trace provenance | `SYNTHETIC_CANONICAL_EVENT` (the framework's own "Fake Quest") |
| Semantic disposition, I3 source time | `DROPPED` (output re-stamped with the consumer's clock) |
| Semantic disposition, I2 frame provenance | `DROPPED` / replaced (`bh_robot_base` on every received message) |
| Semantic disposition, I5 arming | see the arming finding below |
| Downstream consequence | **`PI_RECEIVED`** (619/619) |
| XR hardware | none |
| Robot / driver / actuator | none |

## Executed path

```text
q2r2_bringup/SimulationInput.py            (the framework's OWN in-repo simulator, unmodified)
 -> /q2r_right_hand_pose, /q2r_right_hand_inputs
 -> q2r2_bringup RightArmController         (the pinned production consumer, unmodified)
 -> /bh_robot/right_arm_clik_controller/target_frame
 -> actual DDS over the dedicated research Ethernet (desktop 10.10.10.1 -> Pi 10.10.10.2)
 -> physical Raspberry Pi `rosxr`, semantic_robot_sink subscribed DIRECTLY to the
    production output topic (no republishing hop, no topic renaming)
```

Fixtures: a `static_transform_publisher` supplying `bh_robot_base -> right_arm_link_ee`, which the
pinned controller requires before it will publish. No `controller_manager`, no CLIK controller, no
gripper action server, no driver.

## Arming finding — the framework's own simulator disarms its own controller

This was observed at runtime, and it corroborates the source reading recorded in
[`frameworks/quest2ros2/RESEARCH_UTILITY.md`](../frameworks/quest2ros2/RESEARCH_UTILITY.md).

- `robot_arm_controller_base.py:89` initialises `allow_pose_update = True`, so the controller is
  **armed by default at node start**, before any operator input.
- `robot_arm_controller_base.py:356-358` toggles that flag on a **rising edge** of
  `button_lower`; there is no hold-to-drive requirement.
- `SimulationInput.py:75` holds `button_lower` permanently `True`.

Consequence, observed directly in the container log:

```text
[right_kuka_arm_controller]: Lower button pressed: pose streaming is now **DISABLED (hold position)**
```

The first inputs message from the framework's own simulator produces the one and only rising edge,
which flips streaming from armed to **disarmed**. Run in the documented way, the simulator plus the
production controller therefore emit **zero** control targets.

To reach the publish path, the harness emits a **single operator-equivalent button release**
(`button_lower=False`) on the framework's own inputs topic — the minimum action a human performs on
a real headset — which resets the edge latch so the simulator's continuing `True` re-arms
streaming. Nothing in the pinned target is modified; the harness publishes only on the topic the
simulator itself uses. The run records 3 disable and 3 enable transitions and 619 published targets.

**Interpretation boundary.** This is a defect in the *combination* of the repository's own
simulator and its own arming semantics, demonstrated at runtime. It is **not** evidence about what
the real Quest frontend sends, which is external and unaudited, and it is **not** a safety claim.

## Correlation

| Quantity | Value |
| --- | --- |
| Targets published by the production node | 619 |
| Records received by the Pi sink | **619** |
| Distinct `frame_id` values received | exactly one: `bh_robot_base` |
| Input frames offered by the simulator | `world` (`SimulationInput.py:89`) — never appears downstream |

The one-to-one count match across an actual DDS boundary onto a physically separate ARM64 machine
is the strongest correlation the project has produced for this framework. It nevertheless remains
E2: the pose source is a circle generator.

## What this does and does not support

Supports:

- The pinned Quest2ROS2 control node, driven by the repository's own simulator, publishes Cartesian
  targets that traverse actual DDS to a physically separate robot-side computer.
- Input `frame_id` (`world`) is not preserved; every received message carries the configured
  `bh_robot_base`.
- The default-armed, edge-toggled arming semantics are real and observable, and they interact badly
  with the repository's own simulator.

Does not support:

- Anything about the actual Quest app, actual tracking state, or actual XR transitions.
- Any actuation, robot motion, or native robot-controller acceptance. The CLIK controller and the
  gripper action server were absent throughout; `Waiting for gripper action server` and
  `Gripper action server not available` appear in the log.
- Any relabelling of `PI_RECEIVED` as actionability.

## Reproduce

```bash
cd /home/cclab/ros_xr
sg docker -c "python3 semantic_validation/harness/quest2ros2_simulationinput_pi.py \
  --phase1-seconds 12 --phase2-seconds 20"
```

Artifacts: `semantic_validation/logs/quest2ros2_simulationinput_pi/quest2ros2_simulationinput_pi_20260907T053724Z/`
(`summary.json`, `pi_sink.jsonl`, `container.stdout.txt`, `environment.jsonl`).

## Known harness defects fixed while producing this result

- The Pi sink log directory was passed as `~/…` inside a `-p name:=value` argument, which the
  remote shell does not tilde-expand; the sink wrote into a literal `~` directory and the collector
  found nothing. Three earlier runs of this experiment appeared to receive zero messages for this
  reason alone. Fixed by using an absolute path; the stray directory's contents were moved into the
  correct location on the Pi and the literal `~` directory removed.
- The Pi sink raised `ExternalShutdownException` on SIGTERM at the end of a timed run. Fixed in
  `semantic_robot_sink.py` (also now tolerant of double `rclpy.shutdown()`).
- The container needed `--user $(id -u):$(id -g)` and `mkdir -p "$HOME"` to let colcon create its
  log directory in the bind-mounted workspace, matching the already-working
  `run_quest2ros2_ros_runtime.py`.
