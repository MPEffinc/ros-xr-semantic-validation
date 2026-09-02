# Spes freshness result

## Result

**PASS — `CONFIRMED_RUNTIME_SYNTHETIC_SOURCE`**

합성 sample의 생성 monotonic time은 harness가 보존했지만 actual Spes pose packet에는 timestamp/sequence를 넣지 않았다. 실제 WSS와 `Teleop.__update`를 통해 다음을 실행했다.

| Trial | Source age ground truth | 관측 |
| --- | --- | --- |
| F1 | 정상 즉시 3-sample trajectory | 3 callback; freshness guard 없음. |
| F2 | 단일 sample을 1.05 s 이상 보류 | server가 age를 알 수 없는 채 callback 수용. |
| F3 | 3-sample trajectory 전체를 1.05 s 이상 보류 후 순서대로 전송 | 3 callback; application order는 유지됐지만 source time lineage는 소실. |

## Claim

> 검사한 Spes WSS/server 경계는 source timestamp를 받지 않으므로 delayed sample과 delayed trajectory를 source age에 따라 reject할 수 없다.

이것은 TCP reorder 결과가 아니다. delay/queue는 application-level controlled replay이고, 네트워크가 임의로 재정렬했다고 주장하지 않는다. 실제 Quest producer의 timestamp 특성은 `BLOCKED_HW`다.

## Evidence

- F1: [`spes_freshness_normal.jsonl`](../logs/no_quest/no_quest_20260830T142000Z/spes_runtime/spes_freshness_normal.jsonl)
- F2: [`spes_freshness_delayed_single.jsonl`](../logs/no_quest/no_quest_20260830T142000Z/spes_runtime/spes_freshness_delayed_single.jsonl)
- F3: [`spes_freshness_delayed_trajectory.jsonl`](../logs/no_quest/no_quest_20260830T142000Z/spes_runtime/spes_freshness_delayed_trajectory.jsonl)
- Reproduce all: `./run_no_quest_validation.sh --run-id <new-id>`

Finding: `F-SPES-003`.
