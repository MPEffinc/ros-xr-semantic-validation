# Spes Hardware Independent Re-analysis

## Result

**INDEPENDENT_REANALYSIS_PASS**

기존 derived analysis를 입력으로 사용하지 않고 raw `experiment.jsonl`과 `server.jsonl`에서 session과 trial을 다시 구성했다.

## Session isolation

- Production generation: `4`
- Fresh browser-session events: `876`
- Concurrent prior production client: `False`
- Correlation samples: `777`; server-control offset min/max `11942/11942`

## Valid T1 trials

| Valid | Loss | Pose/source/move integrity | Packet Δ | Server Δ | Callback/reject | Loss→reacquired | Recovery | Classification |
| --- | --- | --- | ---: | ---: | --- | ---: | --- | --- |
| 1 | EMULATED_TRACKING_LOSS | pose=True, source=CONTROLLER, move_false=False | 403 | 403 | 404/404; reject 0 | 1989.3 ms | RECOVERY_CONTINUOUS | HW_EMULATED_CONTINUES |
| 2 | EMULATED_TRACKING_LOSS | pose=True, source=CONTROLLER, move_false=False | 359 | 359 | 356/360; reject 4 | 1510.6 ms | RECOVERY_JUMP_REJECT_THEN_REANCHOR | HW_EMULATED_CONTINUES |
| 3 | EMULATED_TRACKING_LOSS | pose=True, source=CONTROLLER, move_false=False | 360 | 361 | 358/362; reject 4 | 1510.6 ms | RECOVERY_JUMP_REJECT_THEN_REANCHOR | HW_EMULATED_CONTINUES |
| 4 | EMULATED_TRACKING_LOSS | pose=True, source=CONTROLLER, move_false=False | 358 | 357 | 353/358; reject 5 | 1500.0 ms | RECOVERY_JUMP_REJECT_THEN_REANCHOR | HW_EMULATED_CONTINUES |
| 5 | EMULATED_TRACKING_LOSS | pose=True, source=CONTROLLER, move_false=False | 359 | 360 | 356/361; reject 5 | 1510.9 ms | RECOVERY_JUMP_REJECT_THEN_REANCHOR | HW_EMULATED_CONTINUES |

## Existing-analysis comparison

Compared fields: `129`; mismatches: `0`.

Non-decisive diagnostic differences:

| Field | Existing | Re-analyzed | Reason |
| --- | --- | --- | --- |
| `session_partition.semantic_correlation_events` | `788` | `777` | Existing count included the broader connection/final-display window; re-analysis stops at the server-received experiment-complete boundary. |

## Validity exclusions

- T0 manual abort: `3`
- T1 move release: `1`
- Focus invalid: `0`
- Invalid attempts do not contribute to the five valid trials.

## Raw output

- `/home/cclab/ros_xr/semantic_validation/logs/reanalysis/reanalyze_spes_hw_20260831T152922Z/reanalyzed.json`
- `/home/cclab/ros_xr/semantic_validation/logs/reanalysis/reanalyze_spes_hw_20260831T152922Z/comparison.json`
- `/home/cclab/ros_xr/semantic_validation/logs/reanalysis/reanalyze_spes_hw_20260831T152922Z/trial_evidence.jsonl`

## Boundary

이 결과는 actual Quest 3 semantic event와 actual Spes server target callback까지다. ROS sink, robot, actuator evidence는 아니다.
