# Trivial-Fix Threat: Is One Flag Enough?

## 결론

**개별 관측을 막는 작은 patch는 가능하지만, 현재 확인한 failure envelope 전체는 한 field로 닫히지 않는다.**

Spes H1만 좁게 보면 `emulatedPosition`을 pose packet에 추가하고 `true`를 reject하는 것이 유효한 최소 완화다. 따라서 “Spes가 flag 하나를 빠뜨렸다”만 contribution으로 삼으면 novelty threat가 크다. 반면 tracking state, source identity, source time, connection generation, invalidation/re-arm은 서로 독립적인 축이며, 하나의 값만 검사하면 다른 축의 actionable ambiguity가 남는다.

이 판단은 production defense를 구현했다는 뜻이 아니다. 아래 executable oracle은 threat model의 논리적 독립성만 검사한다.

## Finding별 최소 완화와 잔여 문제

| Finding/path | 가장 작은 국소 완화 | 그 완화가 직접 닫는 범위 | 여전히 남는 범위 | 판정 |
| --- | --- | --- | --- | --- |
| Spes F-SPES-HW-001 | production packet에 `emulatedPosition` 추가 후 `true` gate | 이번 Quest run의 non-null emulated interval | controller-null viewer fallback, controller/HMD source binding, stale sample, reconnect generation | H1의 국소 fix는 trivial할 수 있음 |
| Spes F-SPES-HW-002 | tracking invalidation latch + explicit re-arm | loss 뒤 이전 clutch context로 자동 복귀하는 경로 | source/time/generation의 원인 구분과 safe recovery policy | flag보다 transition policy가 필요 |
| Spes freshness/reconnect | timestamp 또는 generation ID 추가 | 각각 stale age 또는 old connection 구분 | clock domain/future stamp, anchor reset, source transition, reauthorization coupling | field만 전달해서는 불충분 |
| Quest2ROS2 F-Q2R-001/002 | source stamp 보존 + age threshold | old/future PoseStamped의 단순 acceptance | input frame/source provenance, clock contract, reference-space generation, re-arm | 현재는 synthetic callback evidence; ROS transport 미검증 |
| PickNik F-PICKNIK-001 | Unity tracking-state를 side-band/payload gate에 연결 | reliable tracking-state가 false인 interval | cached Transform 의미, focus/session, publish time 대 source time, TF/source identity | hardware behavior 전에는 국소 fix 효과도 미확정 |
| NVIDIA | existing `VALID` gate 또는 main hold/zero/rebaseline | invalid pose와 recovery discontinuity 일부 | `VALID`인 inferred pose, TRACKED bits, freshness, reconnect generation | 한 flag가 큰 개선은 하지만 complete positive control 아님 |

## 왜 `emulatedPosition` 하나로 끝나지 않는가

WebXR `emulatedPosition`은 이번 Spes hardware path에서 중요한 신호였지만 전체 semantic contract는 아니다.

1. pose가 HMD/viewer로 fallback하면 controller의 `emulatedPosition`을 검사하는 것만으로 source substitution을 표현하지 못한다.
2. actively tracked pose라도 오래된 sample 또는 이전 connection generation이면 현재 action으로 승인할 수 없다.
3. tracking recovery 뒤 현재 pose가 정상이어도, invalidation 이전 clutch/anchor가 자동 상속되었는지는 별도 causal state다.
4. OpenXR `VALID`와 `TRACKED`가 분리되는 stack에서는 WebXR field 이름을 그대로 이식할 수 없다.

따라서 방어 가능한 공통 단위는 단일 boolean이 아니라 최소한 다음 binding이다.

```text
pose validity + tracked/inferred state + source identity
+ source time/clock contract + session generation
+ invalidation/re-arm epoch
```

각 stack이 모든 field를 wire format에 그대로 넣어야 한다는 뜻은 아니다. Boundary에서 동등한 검증을 수행하고 그 결과가 recovery/control state에 인과적으로 결합되어도 된다.

## Executable one-field oracle

Command:

```bash
python3 semantic_validation/harness/semantic_binding_oracle.py \
  --output semantic_validation/logs/semantic_binding_oracle_20260831T151700Z/summary.jsonl
```

Result: `PASS` as an **ANALYTICAL_EXECUTABLE_MODEL**.

| Guard | 놓친 hazard |
| --- | --- |
| pose-valid only | inferred, viewer fallback, stale/future time, old generation, no re-arm |
| tracked/emulated only | viewer fallback, stale/future time, old generation, no re-arm |
| source only | inferred, stale/future time, old generation, no re-arm |
| age only | inferred, viewer fallback, old generation, no re-arm |
| generation only | inferred, viewer fallback, stale/future time, no re-arm |
| re-arm epoch only | inferred, viewer fallback, stale/future time, old generation |
| composed binding | oracle의 정상 case 허용, 여섯 hazard 모두 차단 |

Raw: [`summary.jsonl`](../logs/semantic_binding_oracle_20260831T151700Z/summary.jsonl).

이 oracle은 선택한 threat cases에 대해 field 독립성을 보이는 모델일 뿐이며, 실제 middleware latency, operator intent, robot safety를 검증하지 않는다.

## Novelty threat 판정

- **위협이 큰 framing:** “Quest tracking loss 때 emulated flag를 보내지 않은 최초 bug” 또는 “한 boolean을 추가하는 protocol patch”.
- **현재 방어 가능한 framing:** 이질적인 XR→control→ROS boundary에서 actionability에 필요한 semantic binding과 causal invalidation을 evidence-driven하게 검사하는 방법.
- **아직 필요한 것:** 두 번째 독립 stack에서 같은 상위 invariant가 runtime/hardware 및 downstream actionable consequence까지 이어지는 증거, 그리고 별도 literature search.

따라서 현재 결과는 common abstraction의 필요성을 지지하지만 paper-level novelty를 확정하지 않는다. 독립 runtime confirmation이 없으면 서로 다른 one-field hardening item의 묶음이라는 반론이 여전히 가능하다.
