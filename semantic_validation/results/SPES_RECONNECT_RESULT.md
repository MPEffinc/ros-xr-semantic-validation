# Spes WSS reconnect result

## Result

**PASS — `CONFIRMED_RUNTIME_SYNTHETIC_SOURCE`**

실제 FastAPI/Uvicorn HTTPS/WSS `/ws` route와 실제 `Teleop.__update`를 사용했다. 매 scenario는 새 server instance에서 시작했고 WSS connection generation을 raw log에 기록했다.

| Trial | 입력 | 관측 결과 |
| --- | --- | --- |
| R1 near reconnect | generation 1의 P1/P2 뒤 disconnect, generation 2의 P3/P4; user re-arm 없음 | disconnect 전후 anchors/state가 동일. P3가 즉시 callback되고 target이 0.01 m 이동. |
| R2 far reconnect | P1/P2 뒤 새 connection에서 1 m 떨어진 Q1/Q2/Q3 | Q1은 jump guard가 reject/reset, Q2는 자동 re-anchor+callback, Q3는 0.02 m target 변화. |
| R3 identity | connection generation과 source/control session field 비교 | transport generation은 observer에만 있고 control packet/server state key에는 없음. explicit re-arm 없이 R1/R2 진행. |

Upstream WebSocket disconnect handler는 connection을 제거하고 log만 남긴다(`teleop/__init__.py:297-315`). `Teleop`의 anchors는 instance fields이고 disconnect와 결합되지 않는다.

## Claim

> 검사한 Spes server는 transport reconnect를 control-session generation으로 격리하지 않는다. near continuation은 새 connection에서 즉시 actionable server callback이 되며, far continuation은 한 sample reject 후 다음 sample을 새 anchor로 받아들인다.

“actionable”은 이 실험에서 server subscriber callback/target 변화까지를 뜻한다. ROS publish와 robot motion은 실행하지 않았다.

## Evidence

- Harness: [`harness/spes_no_quest_runtime.py`](../harness/spes_no_quest_runtime.py)
- R1 raw: [`spes_reconnect_near.jsonl`](../logs/no_quest/no_quest_20260830T142000Z/spes_runtime/spes_reconnect_near.jsonl)
- R2/R3 raw: [`spes_reconnect_far.jsonl`](../logs/no_quest/no_quest_20260830T142000Z/spes_runtime/spes_reconnect_far.jsonl)
- Suite: [`spes_suite_summary.jsonl`](../logs/no_quest/no_quest_20260830T142000Z/spes_runtime/spes_suite_summary.jsonl)

Finding: `F-SPES-002`.
