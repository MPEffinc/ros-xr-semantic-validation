# Spes Continuous Quest-to-Upstream-ROS Feasibility — 2026-09-17

## Scope

- Run ID: `hw_spes_native_20260917T081300Z`
- Pinned source: `SpesRobotics/teleop@c5d808155a87b584d6147a5943d4b87c34c92db0`
- Existing orchestration used without a new ad-hoc harness:
  `semantic_validation/harness/spes_native_hardware_day.py`
- Executed path:

```text
actual Quest WebXR
→ production Spes server callback
→ pinned upstream teleop/ros2 publisher
→ /robot_target_pose over DDS
→ physical Pi semantic_robot_sink observation endpoint
```

No physical robot, driver, CAN path, or actuator was launched.

## Actual Quest semantic observation

The same run's `experiment_sideband.jsonl` contains 628 side-band events,
including 591 `selected_source=CONTROLLER` records, 113 records with
`controller_emulated_position=true`, and 101 records classified
`HW_EMULATED_CONTINUES`.

These observations are from the production WebXR page plus the existing
side-band observer. They show an actual controller-emulated tracking semantic
while the production WSS/server path remained connected. They are not a claim
that an actuator executed or that every tracking API has identical semantics.

## Upstream ROS and Pi observation

- `native_ros_observer.jsonl` recorded **5,197** publications from the pinned
  upstream ROS2 path.
- The run's ROS header-stamp set has 5,197 unique elements.
- Pi collection contains all **5,197 / 5,197** of those header stamps, in the
  observed first-to-last ROS stamp range.
- The Pi is only `PI_RECEIVED`; its endpoint is intentionally
  `ACCEPTED_NO_SEMANTIC_GATING` and is not a native consumer/actuator result.

## Collect limitation

The existing `collect` action produced `result=FAIL` because the Pi sink log
contained 9,297 records: all 5,197 expected ROS header stamps plus 4,100
additional stamps. It therefore did not satisfy the orchestration's strict
`len(native_ros) == len(pi)` condition.

This does not erase the observed 5,197 header-stamp inclusions, but it prevents
a clean one-to-one Pi count claim for this run. The extra Pi records must be
diagnosed before using the run for a strict lossless-delivery statistic. No
physical robot conclusion follows from either outcome.

## Feasibility disposition

**PASS, with bounded Pi correlation.** One continuous actual Quest run reached
the production Spes server, pinned upstream ROS2 publisher, DDS, and Pi
observation endpoint while the side-band recorded actual emulated-controller
semantic observations. The feasible continuous path is established.

The run should be cited as native Quest-to-ROS/Pi-observation feasibility with
the stated extra-record limitation, not as a clean 1:1 Pi delivery proof,
native consumer acceptance, robot movement, or actuator execution.

## Raw evidence

Local run root (preserved, not committed as bulk raw evidence):

```text
semantic_validation/results/runs/hw_spes_native_20260917T081300Z/
```

Key artifacts: `experiment_sideband.jsonl`, `native_ros_observer.jsonl`,
`pi_sink.jsonl`, and `hardware_day_summary.json`.
