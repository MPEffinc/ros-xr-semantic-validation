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

## Exact blockers

The project requests Unity `6000.1.6f1`; neither `Unity` nor `unity-editor` is installed, and
`ros2`/`rclpy` are absent. The disposable staging and future T1/Pi procedure are in
`semantic_validation/results/PICKNIK_HW_READY.md`; use requires authorized Quest hardware and
must remain robot-free.
