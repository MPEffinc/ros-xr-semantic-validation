# NVIDIA positive-control validation

## Version boundary

- `isaac_ros_teleop@197f5cd9ff2cbd90533a93c67be2a661319048ba`의 실제 gitlink: `IsaacTeleop@465ce637120ac35404f5f741a9f25f3f1a1a25ea` (`release/1.3.x`).
- runtime subset을 보유한 comparison checkout: current main `9fba23c4a3bd5b6de732cac77a47f471fca25276`.

두 revision의 evidence를 섞지 않는다. linked release는 machine-checked static이고, 10개 runtime test는 current main이다.

## Linked-release machine checks

**8/8 PASS — `CONFIRMED_STATIC`**

- inactive controller와 action sync/locate failure는 tracked snapshot을 clear한다.
- grip/aim 위치는 OpenXR POSITION_VALID와 ORIENTATION_VALID bits를 모두 요구한다.
- controller left/right는 별도 path/object다.
- internal `DeviceDataTimestamp`는 available/sample local monotonic 및 raw device clock을 정의한다.
- ROS EE builder는 aim validity를 gate한다.
- invalid release-side pose는 explicit validity가 없는 `PoseArray`에서 identity pose로 substitution된다.
- ROS header는 node `now`, payload timestamp는 `time.time_ns()`로 재생성된다.
- inspected controller→ROS path에 source-age threshold는 찾지 못했다.
- POSITION_TRACKED/ORIENTATION_TRACKED bits는 사용하지 않으므로 valid와 actively tracked/inferred를 구분하지 않는다.

## Current-main upstream tests

**10/10 PASS — `CONFIRMED_RUNTIME_SYNTHETIC_SOURCE`**

Repository에 존재하는 test files를 pytest로 그대로 실행했다. optional native `_schema` root import만 pure-Python package root로 제한했고 test/source body는 수정하지 않았다.

| Test subset | Passed | Positive-control behavior |
| --- | ---: | --- |
| `test_se3_retargeter_pose_validity.py` | 5 | invalid grip에서 absolute는 last pose hold; relative는 zero delta, smoothing clear; recovery는 jump 없이 rebaseline. |
| `test_hand_tracking_gate_retargeter.py` | 5 | tracked hand pass-through; invalid/absent validity는 absent output; valid recovery 재개. |

Relevant source는 current main `se3_retargeter.py:251-258,393-416`와 `hand_tracking_gate_retargeter.py:19-66`이다.

## Normalized interpretation

| Property | Result |
| --- | --- |
| Controller active gating | linked release `CONFIRMED_STATIC` positive control |
| Grip pose validity | linked release static; current main runtime positive control |
| Invalid pose handling | release identity substitution; current main hold/zero/rebaseline |
| `is_valid` preservation | internal/gate에서 사용; release `PoseArray` downstream에는 explicit field 없음 |
| `is_tracked` preservation | controller path에서 없음 (`CONFIRMED_STATIC`) |
| Source timestamp | internal schema에는 있음; inspected ROS output까지 보존되지 않음 |
| ROS timestamp regeneration | 있음 (`CONFIRMED_STATIC`) |
| Age guard | inspected path에서 찾지 못함 |

NVIDIA는 모든 semantics의 완전한 positive control이 아니다. validity를 일부 보존하고 안전한 invalid handling을 제공하는 **partial positive control**이다.

## Limitation

Native DeviceIO/OpenXR, real controller active/invalid state, CloudXR, ROS graph, Quest를 실행하지 않았다. current-main test pass를 linked release runtime pass로 승격하지 않는다.

## Evidence

- Runner: [`harness/nvidia_positive_control.py`](../harness/nvidia_positive_control.py)
- Raw: [`nvidia_positive_control.jsonl`](../logs/no_quest/no_quest_20260830T142000Z/nvidia_positive_control.jsonl)
- Pytest stdout: [`nvidia_positive_control.stdout.txt`](../logs/no_quest/no_quest_20260830T142000Z/nvidia_positive_control.stdout.txt)
- Reproduce: `PYTHONPATH=/tmp/ros_xr_nvidia_deps python3 semantic_validation/harness/nvidia_positive_control.py --output <new-jsonl>`

Findings: `F-NVIDIA-001`, `F-NVIDIA-002`, `F-NVIDIA-003`.
