# Spes control-state invalidation result

## Result

**PASS — `CONFIRMED_RUNTIME_SYNTHETIC_SOURCE`**

실제 `Teleop.__update`에서 `move=false`는 relative/absolute anchors를 clear하고 현재 target을 subscriber에 다시 notify한다(`teleop/__init__.py:231-235`). 그러나 `previous_received_pose`는 clear하지 않는다. 다음 상태 전이를 실제 WSS로 재생했다.

| Trial | 전이 | 관측 |
| --- | --- | --- |
| C1 | near P1/P2 → disable → disabled P3 → explicit re-enable P3/P4 | disable에서 anchors clear; re-enable P3가 re-anchor; P4가 0.01 m target 변화. |
| C2 | P1/P2 → disable → disabled far Q1 → re-enable Q1/Q2/Q3 | disabled Q1은 `previous_received_pose`를 바꾸지 않음. re-enable Q1은 jump reject, Q2 re-anchor, Q3 target 변화. |
| C3 | controller P1/P2 → hidden viewer Q1/Q2/Q3, 계속 `move=true` | server에는 source transition field가 없음. Q1만 jump reject하고 Q2/Q3는 callback/target 변화. |

## Interpretation

- 명시적 clutch off/on은 anchor invalidation을 제공한다.
- tracking invalidity, source switch, reconnect와 이 invalidation은 자동 결합되지 않는다.
- jump guard는 첫 큰 차이를 reject하지만 다음 nearby sample을 새 baseline으로 자동 수용한다. 따라서 persistent invalidation/authorization gate는 아니다.
- `move=false`도 server subscriber callback을 발생시킨다. 실제 ROS wrapper가 이를 어떻게 publish하는지는 source상 별도 로직이 있으나 이번 WSS experiment에서는 ROS graph를 실행하지 않았다.

## Evidence

- C1: [`spes_control_near_rearm.jsonl`](../logs/no_quest/no_quest_20260830T142000Z/spes_runtime/spes_control_near_rearm.jsonl)
- C2: [`spes_control_far_rearm.jsonl`](../logs/no_quest/no_quest_20260830T142000Z/spes_runtime/spes_control_far_rearm.jsonl)
- C3: [`spes_control_hidden_switch.jsonl`](../logs/no_quest/no_quest_20260830T142000Z/spes_runtime/spes_control_hidden_switch.jsonl)

Finding: `F-SPES-004`.
