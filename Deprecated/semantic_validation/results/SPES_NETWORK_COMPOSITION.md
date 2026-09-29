# Spes network composition

## Result

**PASS — exploratory `CONFIRMED_RUNTIME_SYNTHETIC_SOURCE`**

이 실험은 TCP fault injection이 아니다. WSS 위에서 application이 의도적으로 packet을 보류한 뒤 전송한 `APPLICATION_LEVEL_CONTROLLED_REPLAY`다.

| Trial | Composition | 관측 |
| --- | --- | --- |
| N1 | controller P1/P2 뒤 viewer Q1/Q2/Q3를 250 ms 보류 후 같은 connection에서 전송 | Q1 jump reject, Q2 re-anchor, Q3 target 변화. |
| N2 | source generation 0의 controller queue를 만들고 generation 1 viewer trajectory 처리 후 old queue 재생 | generation field가 packet에 없으므로 old Q first reject 뒤 다음 두 old samples가 다시 re-anchor/actionable. |
| N3 | reconnect/session generation 결합 여부 | N2는 reconnect를 포함하지 않았고 generic network vulnerability는 주장하지 않음. reconnect 결과는 별도 R1–R3. |

## Claim boundary

> Source generation/age metadata가 control packet에 없으면 application replay가 old-source sample임을 server가 판별할 수 없고, geometric jump recovery 뒤 이를 새 trajectory로 수용할 수 있다.

이 결과만으로 TCP reordering, WebSocket protocol flaw, adversarial network exploit, XR-specific 발생 가능성을 주장하지 않는다. 따라서 독립 취약점이 아니라 semantic erosion과 application replay의 **exploratory composition**으로 남긴다.

## Evidence

- N1: [`spes_network_stall_switch.jsonl`](../logs/no_quest/no_quest_20260830T142000Z/spes_runtime/spes_network_stall_switch.jsonl)
- N2/N3: [`spes_network_old_generation_replay.jsonl`](../logs/no_quest/no_quest_20260830T142000Z/spes_runtime/spes_network_old_generation_replay.jsonl)

Finding: `F-SPES-005` (exploratory; not promoted to generic network finding).
