# XR-to-Robot Semantic Validation Experiment Protocol V2

## 목적과 범위

이 프로토콜은 각 framework의 **native production path**에서 다음 질문을 같은
표현으로 검증하기 위한 것이다.

> 안전 관련 XR semantic context가 XR application → transport/bridge → ROS →
> downstream control 경계를 통과하면서 보존, 동등 변환, 재검증, gate, 또는
> 조용히 소실되는가?

모든 raw field를 같은 wire format으로 끝까지 보존해야 한다는 요구는 아니다.
동등한 의미를 재검증하거나 gate/degrade하는 구현도 유효하다. semantic distinction이
필요한 구간에서 distinction이 사라지고 downstream에 동등 검증도 없을 때만
finding 후보가 된다.

이 프로토콜은 physical robot 또는 actuator 연결을 요구하거나 허용하지 않는다.
Pi `semantic_robot_sink` 수신은 `PI_RECEIVED` transport/reception 증거이며
`NATIVE_CONSUMER_ACCEPTED`, `ACTUATOR_STUB_COMMAND`, robot motion의 증거가 아니다.

## Research questions

| ID | 질문 |
| --- | --- |
| RQ1 | XR-to-robot teleoperation stack은 native control path에서 안전 관련 XR semantic을 어떻게 preserve, transform, revalidate, gate, discard하는가? |
| RQ2 | 비교 가능한 XR state transition에서 semantic contract 차이가 downstream ROS 및 native control behavior에 어떤 차이를 만드는가? |
| RQ3 | controlled replay로 확인한 behavior가 독립 architecture family의 native XR hardware execution에서도 재현되는가? |

RQ3의 답은 E5/E6 native evidence가 있을 때만 강화한다. replay-only 결과와
Pi-only reception은 second native confirmation으로 계산하지 않는다.

## 공통 transition suite

각 framework는 지원 가능한 transition만 수행하며, 지원하지 않는 경우 `N/A`와
근거를 기록한다. 같은 물리 행동이 같은 native transition을 만든다고 가정하지
않으며, 매 trial에서 raw native transition을 관측해야 한다.

| ID | 전이 | 의도 | 최소 native 관측 |
| --- | --- | --- | --- |
| T0 | `VALID_BASELINE` | 정상 tracking/control baseline | framework가 정의하는 valid state, source, pose progression |
| T1 | `SPATIAL_TRACKING_DEGRADE` | controller/hand spatial tracking degrade | raw tracking validity/status와 valid→degraded→reacquired 경계 |
| T2 | `SOURCE_TRANSITION` | controller/hand/HMD/fallback 전환 | native source identity 또는 source abstraction 변화; 미지원이면 `N/A` |
| T3 | `FRESHNESS_STALL` | old/stalled/replayed/future sample | source-time/sequence/age contract가 실제로 있는 boundary만 사용 |
| T4 | `TRANSPORT_RECONNECT` | transport disconnect/reconnect | connection generation 또는 registration/reconnect event |
| T5 | `SESSION_INVALIDATION` | XR focus/session/background/resume | framework에 존재하는 focus, pause, session lifecycle event |
| T6 | `RECOVERY` | T1/T4/T5 이후 recovery | recovery 전후 gate, re-arm, stale-state disposal 또는 explicit policy |

Automatic recovery는 그 자체로 violation이 아니다. recovery가 이전 context를 어떤
조건으로 폐기/재사용하는지를 I4/I5 관점에서 기록한다.

## 관측 지점과 correlation

각 run은 stable `run_id`를 갖고 다음 O1–O5를 가능한 범위에서 같은 run에
상관시킨다. 다른 clock을 무조건 직접 비교하지 않고, monotonic timestamp,
sequence number, shared marker, 또는 명시적 offset/alignment를 기록한다.

| 관측점 | 이름 | 최소 기록 | 무엇을 증명하는가 |
| --- | --- | --- | --- |
| O1 | XR raw semantic | API/raw fields, pose, source time, source identity, focus/session, monotonic capture time | intended native transition의 존재 |
| O2 | application/serialization | production representation, send decision, sequence/time | application output 또는 transport send |
| O3 | ROS/Pi observer | ROS publish/receive time, header, frame, payload digest/count | ROS publication 또는 Pi reception |
| O4 | original consumer dry-run | original callback/decision, no-op/stub boundary | native consumer acceptance 또는 actuator-stub command |
| O5 | lifecycle/control | reconnect/session generation, authorization/control state, recovery action | invalidation/re-arm contract |

O3의 Pi observer는 observation endpoint이며 semantic gate도 original controller도
아니다. O4가 불가능하면 `NATIVE_CONSUMER_UNAVAILABLE`로 남기고 O3까지만 주장한다.

## Trial validity와 exclusion

T1 valid trial에는 다음 네 조건이 모두 필요하다.

1. 의도한 native XR transition이 raw O1에서 실제 관측된다.
2. 필요한 logging stream이 손상 없이 존재한다.
3. pinned production path가 active이며 test path가 아닌 것이 확인된다.
4. O1과 downstream stream을 run id/sequence/time contract로 상관할 수 있다.

다음은 negative/safe outcome이 아니라 exclusion 또는 별도 상태다.

| 조건 | 기록값 | 이유 |
| --- | --- | --- |
| controller를 가렸지만 native state 변화가 없음 | `NO_TRANSITION_OBSERVED` | 물리 행동은 semantic event의 증거가 아님 |
| focus/pause/session interruption이 T1과 겹침 | `INVALID_FOCUS_OR_XR_SESSION` | tracking degradation만의 효과로 분리 불가 |
| logging stream 또는 production path가 없음 | `INVALID_LOGGING_OR_PATH` | correlation 불가 |
| known gate 뒤에서 replay injection | `BOUNDARY_LIMITED_REPLAY` | native gate의 behavior를 시험하지 않음 |
| environment/hardware가 없음 | `BLOCKED_ENV` / `BLOCKED_HW` | negative result가 아님 |

## 실행 순서

1. T0에서 raw semantic, production-path activation, observer correlation을 확인한다.
2. framework가 지원하는 T1–T5를 하나씩 실행하고 O1–O5 evidence를 보존한다.
3. 각 invalidation 뒤 T6를 기록한다. 사용자 re-arm 없이 recovery했는지와 explicit
   policy가 있었는지를 분리한다.
4. synthetic/replay는 native decision point 이전 injection인지 먼저 판정하고,
   injection boundary와 bypass된 logic을 결과에 함께 쓴다.
5. semantic disposition과 downstream consequence를 독립 축으로 판정한다.
6. valid/excluded trial 수, exact boundary, evidence level, unresolved alternative를
   framework result report에 기록한다.

## 결과 판정 규칙

`PRESERVED`, `TRANSFORMED`, `REVALIDATED`, `GATED`, `DROPPED`, `UNKNOWN`,
`N/A`는 semantic disposition이다. `NO_OUTPUT`, `APP_OUTPUT`,
`TRANSPORT_SENT`, `ROS_PUBLISHED`, `PI_RECEIVED`,
`NATIVE_CONSUMER_ACCEPTED`, `ACTUATOR_STUB_COMMAND`, `UNKNOWN`, `N/A`는
downstream consequence이다. 두 값을 하나의 vulnerability/safety label로 합치지
않는다.

예를 들어 `DROPPED + PI_RECEIVED`는 `DROPPED + NATIVE_CONSUMER_ACCEPTED`와
동일하지 않다. 어떤 outcome도 evidence level과 exact boundary 없이는
`vulnerable`, `unsafe`, `robot moved`, `end-to-end confirmed`, `general`로
표현하지 않는다.

## Recovery 관찰 규칙

T6에서는 (a) valid stream이 계속되었는지, (b) output이 gate/hold/zero 되었는지,
(c) 새 source/session/generation 또는 explicit user action이 필요한지, (d) old
state가 재사용되었는지를 각각 관찰한다. `automatic`이라는 사실만으로 I5 violation을
판정하지 않으며, raw native state와 downstream policy 사이의 causal contract가
없는 경우에만 그 한계를 기록한다.

## 현재 decision gate

현재 decision은 **`GO — NOT STRONG GO`**다. `STRONG GO`에는 최소 두 독립
architecture family에서 native actual XR transition, native production path,
actual ROS/control progression, correlated downstream software consequence가 필요하다.
E3/E4 replay-only와 Pi-only O3 evidence는 이 조건을 충족하지 않는다.

관련 공통 정의는 [CANONICAL_EVENT_MODEL.md](CANONICAL_EVENT_MODEL.md), evidence
claim 경계는 [EVIDENCE_LEVELS_V2.md](EVIDENCE_LEVELS_V2.md)를 따른다.
