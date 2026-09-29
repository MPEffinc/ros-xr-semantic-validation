# Spes preparation and runbook

## Verified hardware-free check

```bash
PYTHONPATH=/tmp/ros_xr_semantic_deps python3 \
  semantic_validation/harness/spes_no_quest_runtime.py \
  --result-dir semantic_validation/logs/v2_multi_framework_20260907T000003Z/spes_synthetic_runtime
```

The 2026-09-07 run recorded 10/10 scenario `PASS`, with `hardware_used=false` and
`robot_connected=false`. It is E2 and `BOUNDARY_LIMITED_REPLAY` only.

## Quest readiness

Existing orchestration is retained in `semantic_validation/start_quest_experiment.sh`,
`status_quest_experiment.sh`, and `stop_quest_experiment.sh`. A future run must use V2
T0/T1/T4/T5 observables and cannot call the existing server callback E5/E6 without actual ROS
and native-consumer correlation.

## ROS/Pi preparation added in this phase

`../../harness/spes_ros_callback_adapter.py` is a research-only post-callback adapter. It is
registered after the actual pinned `Teleop` target callback observer, publishes the accepted
target to `/robot_target_pose`, and writes `adapter.jsonl` with `run_id`, local event ID, server
update index, ROS publish time and header stamp. It neither changes upstream source nor adds
correlation/tracking fields to `PoseStamped`.

Its dependency-light self-test passed at
`semantic_validation/logs/next_phase_20260907T000000Z/spes_ros_adapter_selftest.jsonl`.
This verifies adapter-side schema/correlation logic only.

## Verified Quest-less ROS/Pi runtime

The standard Docker group mechanism is now usable through `sg docker` (a new login session will
also acquire the group).  The final automated canonical run
`semantic_validation/logs/spes_questless_all_20260907T043540Z/spes_runtime/` passed with three
exact adapter-header/Pi-header and pose matches. The earlier direct run at
`semantic_validation/logs/spes_ros_pi_20260907T041600Z/` independently has the same result:

```text
synthetic WSS after browser gate -> pinned Spes server -> accepted callback
-> research post-callback adapter -> /robot_target_pose -> DDS -> Pi sink
```

Use `./spes_preflight.sh`, `./spes_start_all.sh <run-id>`, `./spes_status.sh <run-id>`,
`./spes_collect.sh <run-id>`, and `./spes_stop_all.sh <run-id>` for a fresh observation-only
run.  `spes_start_all.sh` starts only `semantic_robot_sink`, never a robot driver.  The result
classification is necessarily `E2_BOUNDARY_LIMITED_REPLAY`: the synthetic input begins after the
browser-native gate.  The Pi proves only `PI_RECEIVED`, never native-consumer acceptance,
actionability, or actuator activity.
