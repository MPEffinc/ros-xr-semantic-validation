# Quest2ROS2 stale-pose and re-stamp validation

## Result

**PASS — `CONFIRMED_RUNTIME_SYNTHETIC_SOURCE` for the actual callback; `BLOCKED_ENV` for ROS transport**

고정 target `07aaf65149c9e29103f1fc61deb466cef8a55cef`의 `BaseArmController._pose_callback`을 source에서 동적 load해 수정 없이 호출했다. ROS message classes, clock, TF result, publisher만 minimal test double이었다. 따라서 callback 계산과 output construction은 실제 upstream code이고 ROS graph/DDS는 실행하지 않았다.

## Age sweep

filter warm-up/anchor 1회를 먼저 수행한 뒤 각 input `PoseStamped`를 actual callback에 전달했다.

| Trial | Input stamp ground truth | Published | Output stamp | Output frame |
| --- | ---: | :---: | --- | --- |
| 10 ms old | `now-10 ms` | yes | callback-time now | `robot_base` |
| 100 ms old | `now-100 ms` | yes | callback-time now | `robot_base` |
| 500 ms old | `now-500 ms` | yes | callback-time now | `robot_base` |
| 1 s old | `now-1 s` | yes | callback-time now | `robot_base` |
| 3 s old | `now-3 s` | yes | callback-time now | `robot_base` |
| 10 s old | `now-10 s` | yes | callback-time now | `robot_base` |
| 1 s future | `now+1 s` | yes | callback-time now | `robot_base` |

모든 case에서 `source_stamp_preserved=false`, `freshness_guard_observed=false`였다. 3 s old 5-sample trajectory도 5개 모두 publish되었고 output X가 `0.60, 0.62, 0.64, 0.66, 0.68`로 진행했다.

실제 source에서도 callback은 pose 값만 moving-average queue에 넣고(`robot_arm_controller_base.py:166-208`), input header를 읽지 않은 채 output에 configured base frame과 `get_clock().now()`를 설정한다(`:211-306`).

## Frame/provenance propagation

`xr_controller_A`, `xr_controller_B`, `old_reference_space`, `future_reference_space`, `stale_trajectory_frame`를 input frame으로 주었지만 output은 모두 `robot_base`였다. 이것은 arbitrary upstream frame/provenance가 이 callback을 통과해 보존되지 않는다는 software-boundary result다. 실제 OpenXR reference-space 전환을 재현한 것은 아니다.

## Claim

> 검사한 Quest2ROS2 callback은 source age 또는 future-stamp를 reject하지 않고, input stamp/frame lineage를 새 output stamp/configured frame으로 대체한다.

이 finding은 XR producer와 결합될 때 semantic erosion chain의 한 부분이다. 그 자체를 XR-specific vulnerability 또는 robot consequence로 주장하지 않는다.

## Environment boundary

- Host `ros2`, `colcon`: 없음.
- Session groups: `cclab nogroup`.
- `/var/run/docker.sock`: mode `660`, owner `nobody:nogroup`; escalated `docker info`도 permission denied.
- Actual ROS graph, subscription/QoS/DDS, real publisher, robot: `BLOCKED_ENV` 또는 범위 밖.
- Quest/client source의 original stamp/validity semantics: `UNKNOWN`/`BLOCKED_HW`.

## Evidence

- Harness: [`harness/quest2ros2_stale_restamp.py`](../harness/quest2ros2_stale_restamp.py)
- Raw: [`quest2ros2_stale_restamp.jsonl`](../logs/no_quest/no_quest_20260830T142000Z/quest2ros2_stale_restamp.jsonl)
- Reproduce: `PYTHONPATH=/tmp/ros_xr_semantic_deps python3 semantic_validation/harness/quest2ros2_stale_restamp.py --output <new-jsonl>`

Findings: `F-Q2R-001`, `F-Q2R-002`.
