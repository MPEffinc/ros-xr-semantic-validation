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
This verifies adapter-side schema/correlation logic only. Desktop Docker daemon access was
`BLOCKED_ENV` in the current execution identity, so an actual callback → desktop ROS/DDS → Pi
smoke test was not run. The readiness scripts beside this file explicitly refuse to claim an
unverified runtime launch.
