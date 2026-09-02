# Spes Classifier Regression

## Result

**PASS**

Recovery jump evidence is now counted from semantic loss detection through recovery completion. A reject observed while preparing/baselining a trial cannot set its recovery label.

## Actual Quest raw-log regression

| Valid T1 | Pre-loss jump/reject | Loss-window jump/reject | Derived recovery | Result |
| ---: | ---: | ---: | --- | --- |
| 1 | 1 | 0 | RECOVERY_CONTINUOUS | PASS |
| 2 | 1 | 4 | RECOVERY_JUMP_REJECT_THEN_REANCHOR | PASS |
| 3 | 1 | 4 | RECOVERY_JUMP_REJECT_THEN_REANCHOR | PASS |
| 4 | 1 | 5 | RECOVERY_JUMP_REJECT_THEN_REANCHOR | PASS |
| 5 | 0 | 5 | RECOVERY_JUMP_REJECT_THEN_REANCHOR | PASS |

The actual first valid trial contains one pre-loss jump/reject but no loss-window jump; it is therefore `RECOVERY_CONTINUOUS`. Trials 2–5 retain their raw-evidence `RECOVERY_JUMP_REJECT_THEN_REANCHOR` labels.

## Valid/invalid and session isolation

- Valid T1 count: `5`.
- Excluded `INVALID_MOVE_RELEASED`: `1`.
- Raw `INVALID_SESSION_FOCUS`: `0`; the synthetic focus-invalid path exclusion test is `True`.
- Production connection generation: `4`; prior-generation overlap: `False`.
- Server/control correlation offset min/max: `11942/11942`.

## Synthetic boundary regression

- Pre-loss reject excluded: `True`.
- Post-loss reject retained: `True`.
- Move-release invalid attempt excluded: `True`.
- Focus-invalid attempt excluded: `True`.
- Operator selftest: `PASS`.

## Artifacts

- Operator SHA-256: `5aacab70ad87d1577e54d99b31c5b9d9d303b12543e17f9fcd630c6898533ba9`
- Machine-readable result: `/home/cclab/ros_xr/semantic_validation/logs/classifier_regression/spes_classifier_regression_20260831T151624Z/result.json`
- Event summary: `/home/cclab/ros_xr/semantic_validation/logs/classifier_regression/spes_classifier_regression_20260831T151624Z/summary.jsonl`

## Evidence boundary

The recovery labels are reconstructed from one actual Quest 3 run plus deterministic classifier tests. They do not establish population rates or robot actuation.
