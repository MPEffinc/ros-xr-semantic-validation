# Spes semantic collision

## Result

**PASS — `CONFIRMED_RUNTIME_SYNTHETIC_SOURCE`**

고정 upstream `c5d808155a87b584d6147a5943d4b87c34c92db0`의 수정하지 않은 `teleop/index.html` inline script를 Node VM의 mock WebXR 객체로 실행했다. 같은 pose `P=(0.25, 0.5, 0.75)`, 같은 orientation, `move=true`에 대해 다음 세 상태를 만들었다.

| Trial | 합성 ground truth | 실제 frontend control packet |
| --- | --- | --- |
| A | right controller, valid, `emulatedPosition=false` | pose/move/device만 포함 |
| B | right controller, inferred/emulated, `emulatedPosition=true` | A와 byte-equivalent JSON object |
| C | controller pose null → viewer pose, 같은 P | A와 byte-equivalent JSON object |

`A == B`와 `A == C`가 모두 true였다. packet에는 `source`, tracking validity, `emulatedPosition`, source timestamp가 없다. 실제 branch는 upstream `index.html:328-380`이며 controller null일 때 viewer를 선택한 뒤 동일한 `state` schema로 보낸다.

## Claim

> 이 frontend 경계는 합성된 controller-valid, controller-emulated, viewer-fallback 상태를 동일한 downstream control representation으로 collapse한다.

이것은 실제 Quest가 obstruction에서 B 또는 C를 발생시킨다는 증거가 아니다. 그 activation은 `BLOCKED_HW`다.

## Evidence

- Harness: [`harness/spes_semantic_collision.mjs`](../harness/spes_semantic_collision.mjs)
- Raw JSONL: [`logs/no_quest/no_quest_20260830T142000Z/spes_semantic_collision.jsonl`](../logs/no_quest/no_quest_20260830T142000Z/spes_semantic_collision.jsonl)
- Reproduce: `node semantic_validation/harness/spes_semantic_collision.mjs --output <new-jsonl>`

Finding: `F-SPES-001`.
