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
