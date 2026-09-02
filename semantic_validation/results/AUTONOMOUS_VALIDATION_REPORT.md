# Autonomous Semantic Validation Report

작성 시점: 2026-09-01 KST  
현재 결정: **GO — NOT STRONG GO**

이 문서는 기존 actual Quest 3 run의 재분석과 이번 autonomous validation에서 실행한 software/static checks를 구분한다. 이번 자동 작업에서는 새 XR hardware trial, actual robot/driver, privilege escalation, Docker socket 변경, 방화벽 변경을 수행하지 않았다.

## 1. What was already confirmed

기존 canonical actual-hardware run `spes_quest_hw_20260831T001349Z`에서 다음 Spes finding이 이미 확인되어 있었다.

- T0 baseline은 PASS했다.
- Actual Quest 3의 valid T1 5/5에서 right controller pose는 non-null인 채 `emulatedPosition=true` interval에 들어갔다.
- 그 interval 동안 selected source는 `CONTROLLER`, production `move=true`는 유지되었고 control packet index와 actual Spes production server target callback이 계속 진행했다. 이는 fixed Spes checkout/device/run 범위에서 H1을 확인한다.
- 사용자의 move release/re-press 없이 recovery가 5/5 actionable해졌다. Corrected classification은 T1-1 `RECOVERY_CONTINUOUS`, T1-2~5 `RECOVERY_JUMP_REJECT_THEN_REANCHOR`다.

이 결과는 한 Quest 3, 한 browser/session, valid trial 5회의 software endpoint 관측이다. Controller pose가 null이 되는 viewer fallback H2와 실제 disconnect T4는 관측되지 않았으며, actual ROS sink나 robot/actuator consequence는 실행하지 않았다. Canonical 범위는 [SPES_QUEST_HW_RESULT.md](SPES_QUEST_HW_RESULT.md)에 있다.

## 2. What was newly validated

이번 autonomous campaign에서 새로 확인하거나 강화한 것은 다음과 같다.

1. **독립 raw reconstruction:** Fresh browser generation `4`를 이전 client와 격리해 raw experiment/server JSONL에서 T0와 valid T1 5회를 다시 구성했다. Canonical analysis와 비교한 129 fields에서 mismatch는 0이었다: `INDEPENDENT_REANALYSIS_PASS`. 자세한 결과는 [SPES_HW_REANALYSIS.md](SPES_HW_REANALYSIS.md)에 있다.
2. **Classifier correction:** Recovery jump window를 semantic loss detection 이후로 한정했다. 이로써 T1-1의 pre-loss jump reject 오염을 제거했고, raw evidence와 일치하는 1 continuous / 4 jump-reanchor 분류를 회귀 검사했다. [SPES_CLASSIFIER_REGRESSION.md](SPES_CLASSIFIER_REGRESSION.md)
3. **정량 경계:** 5 trials 모두 emulated interval, downstream continuation, no-user-rearm을 보였다. Reacquisition latency와 target delta는 descriptive statistics로만 계산했으며 population rate로 해석하지 않았다. [SPES_HW_QUANTITATIVE_SUMMARY.md](SPES_HW_QUANTITATIVE_SUMMARY.md)
4. **Instrumentation non-interference:** Frontend 7 cases에서 production pose payload의 key/value/exact serialization/send condition이 같았고, server differential 12 cases에서 callback, target, internal control state, exception이 같았다. Experiment field는 production pose payload에 들어가지 않았고 actual `Teleop.__update` delegation은 1회였다: `INSTRUMENTATION_NON_INTERFERENCE_PASS`. [SPES_INSTRUMENTATION_INTEGRITY.md](SPES_INSTRUMENTATION_INTEGRITY.md)
5. **Quest2ROS2 callback boundary:** Pinned production callback에 synthetic/test-double source를 넣은 기존 finding은 stale/future stamp와 frame provenance를 callback-time `now`/configured frame으로 대체하는 `CONFIRMED_RUNTIME_SYNTHETIC_SOURCE`로 유지됐다. 이번 actual ROS 2 retry는 Docker daemon access가 없어 `BLOCKED_ENV`였고 DDS, actual node, actual ROS publisher/subscriber는 실행되지 않았다. 따라서 증거 수준을 actual ROS transport로 승격하지 않았다. [QUEST2ROS2_STALE_RESTAMP.md](QUEST2ROS2_STALE_RESTAMP.md), [QUEST2ROS2_ROS_RUNTIME.md](QUEST2ROS2_ROS_RUNTIME.md)
6. **PickNik serialized dataflow:** Pinned checkout에서 33/33 machine checks가 PASS했다. `isTracked`/`trackingState`는 enabled scene의 tracked-pose component를 통해 controller Transform까지 연결되지만 production `RosPublishers`는 resulting Transform만 읽고 tracking state/source time을 Odometry/TF에 넣거나 gate하지 않으며 wall-clock으로 re-stamp한다. Strongest level은 `SOURCE_DATAFLOW_CONFIRMED`; Unity, Quest, ROS runtime은 실행하지 않았다. [PICKNIK_DEEP_VALIDATION.md](PICKNIK_DEEP_VALIDATION.md)
7. **NVIDIA comparison:** Linked release의 activity/`VALID` dataflow는 machine-checked static evidence로, current main의 invalid hold/zero/rebaseline은 upstream pure-Python synthetic tests 10/10으로 재검증했다. 그러나 inspected tracker는 OpenXR `TRACKED` bits를 보존하지 않아 inferred-but-valid interval의 complete positive control이 아니다. [NVIDIA_VS_SPES_ANALYSIS.md](NVIDIA_VS_SPES_ANALYSIS.md)
8. **Composed invariant model:** Analytical oracle에서 tracking state, identity, time, generation, invalidation/re-arm을 각각 단독으로 검사하는 정책은 다른 hazard class를 놓쳤다. 이는 executable model evidence이지 runtime/hardware evidence가 아니다. [TRIVIAL_FIX_THREAT.md](TRIVIAL_FIX_THREAT.md)

Canonical integrated run [`semantic_validation_20260831T153536Z`](../logs/semantic_validation_20260831T153536Z/summary.jsonl)의 최종 count는 `PASS=11`, `FAIL=0`, `SKIP_ENV=2`, `BLOCKED_HW=1`이다. PASS는 실제 실행된 component에만 적용된다. Current sandbox의 local-socket restriction으로 nested no-Quest Spes WSS scenarios가 `SKIP_ENV`였으며, 이는 이전 canonical 10-scenario PASS를 취소하지도 이번 run에서 재확인하지도 않는다. Integrated runner 실행 자체는 `hardware_used=false`, `robot_used=false`, `privilege_escalation_used=false`였고 Quest re-analysis component는 frozen actual-hardware raw log를 입력으로 사용했다.

## 3. What was disproved

이번 작업에서 예상과 달랐거나 더 좁게 고쳐야 했던 항목은 다음과 같다.

- **T1-1의 이전 recovery label:** Pre-loss jump reject까지 recovery window에 포함해 T1-1을 jump-reanchor로 분류한 것은 잘못이었다. Correct label은 `RECOVERY_CONTINUOUS`다. H1/downstream-continuation finding 자체는 바뀌지 않았다.
- **PickNik에 tracking metadata 경로가 전혀 없다는 broad reading:** 이는 틀렸다. `isTracked`와 `trackingState`는 scene/action에서 controller Transform driver까지 실제로 연결된다. 확인된 결함 경계는 그 뒤의 Transform-to-Odometry/TF publisher에서 tracking state와 source time이 소실된다는 것이다.
- **NVIDIA `VALID` gate를 complete tracked-vs-inferred positive control로 보는 해석:** 지지되지 않는다. Current main은 `is_valid=false`를 안전하게 처리하지만 `POSITION_TRACKED`/`ORIENTATION_TRACKED`를 검사하지 않으므로 `VALID=true, TRACKED=false` interval에 대한 결론은 낼 수 없다.
- **한 field가 전체 cross-stack 문제를 설명한다는 reduction:** Narrow Spes H1은 `emulatedPosition` 전달/gate 한 개로 직접 완화할 수 있지만, executable case matrix에서는 identity, time, generation, causal re-arm 중 하나만 검사하면 다른 hazard class가 남았다. 이는 analytical falsification이며 두 번째 runtime confirmation을 대신하지 않는다.

반대로 H2 viewer fallback, actual disconnect, Quest2ROS2 actual DDS transport, PickNik hardware continuation은 **disproved가 아니다**. 각각 `NOT_OBSERVED`, `BLOCKED_ENV`, 또는 `BLOCKED_HW`다.

## 4. Cross-stack evidence

| Stack | Strongest self-generated evidence | Confirmed boundary | Missing boundary |
| --- | --- | --- | --- |
| **Spes** `c5d8081` | `ACTUAL_XR_HARDWARE -> ACTUAL_SPES_SERVER_CALLBACK` | Actual Quest 3 emulated interval에서 tracking state가 production packet에 없고 move/packet/target callback이 5/5 계속됨; no-user-rearm recovery 5/5 | Actual controller-null fallback/disconnect, ROS, robot, independent device/session |
| **Quest2ROS2** `07aaf65` | `CONFIRMED_RUNTIME_SYNTHETIC_SOURCE` | Unchanged callback이 synthetic stale/future `PoseStamped`와 frame labels를 소비해 publish test double까지 진행 | Actual XR producer와 actual ROS graph/DDS/node/publisher/subscriber; current retry는 `BLOCKED_ENV` |
| **PickNik** `bbaef07` | `SOURCE_DATAFLOW_CONFIRMED` | Tracking state가 Transform driver까지 연결되고 production Odometry/TF publisher boundary에서는 소실; source time은 wall-clock으로 재생성 | Unity compile/runtime, actual Quest transition, actual ROS endpoint progression; `BLOCKED_ENV/BLOCKED_HW` |
| **NVIDIA** linked release `465ce63`; local executed main `9fba23c` (remote `334978b` semantic files source-equivalent) | `MACHINE_CHECKED_STATIC` + current-main `RUNTIME_SYNTHETIC` | Activity/`VALID` partial gate와 invalid hold/zero/rebaseline positive control | Native OpenXR exact `VALID`/`TRACKED`, Quest, ROS, recovery/generation trace |

NVIDIA IsaacTeleop issue #731은 contributor가 Quest 3/CloudXR occlusion, inferred/extrapolated behavior, recovery snap, SO-101 lurch를 보고한 **`PUBLIC_ISSUE_SELF_REPORT`**다. 이 연구가 raw telemetry나 exact flag trace를 재실행·재분석한 independent reproduction이 아니며, 73 cm/frame 결과를 이 연구의 observation으로 사용하지 않는다.

## 5. Common invariants

상위 비교 단위는 wire field의 동일성보다 action boundary에서 다음 의미를 보존하거나 동등하게 재검증하는가이다.

| ID | Required invariant | Current cross-stack evidence |
| --- | --- | --- |
| **I1 Tracking-State Preservation** | Actively tracked와 inferred/emulated를 구별하거나 action 전 gate | Spes actual boundary에서 violated. PickNik publisher dataflow에서 violated지만 runtime consequence unknown. NVIDIA는 `VALID` partial positive control이고 `TRACKED`는 incomplete. Quest2ROS2는 unknown. |
| **I2 Source Identity Preservation** | Controller/HMD/hand/reference-space provenance의 silent collapse 방지 | Spes source-faithful software runtime과 Quest2ROS2 frame lineage에서 partial/violation evidence. PickNik/NVIDIA는 handedness는 보존하지만 modality는 incomplete. |
| **I3 Source-Time Lineage** | Source sample time, clock contract, freshness의 보존 또는 age gate | Spes와 Quest2ROS2 callback runtime에서 violated; PickNik publisher dataflow와 NVIDIA inspected actionable path에서 incomplete/violated. Quest2ROS2 actual DDS는 미실행. |
| **I4 Session/Generation Isolation** | 새 session/transport generation이 old control context를 무검증 상속하지 않음 | Spes actual WSS-route synthetic runtime에서 violated. 다른 세 stack은 inspected path에 complete contract가 없거나 runtime unknown. |
| **I5 Causal Invalidation/Re-arm** | Tracking/session invalidation 뒤 explicit causal condition 없이 actionable 재개 금지 | Spes actual Quest-to-server에서 violated. PickNik contract는 incomplete지만 runtime consequence unknown. NVIDIA current main은 invalid-path partial positive control. Quest2ROS2는 unknown. |

Stack별 exact evidence/unknown cell은 [INVARIANT_MATRIX.md](INVARIANT_MATRIX.md)에 있다. 현재 matrix는 common research question을 지지하지만 **두 stack runtime generality를 확정하지 않는다.**

## 6. Novelty threats

1. **Public prior report:** NVIDIA issue #731이 Quest occlusion/extrapolation/recovery snap과 robot lurch라는 broad phenomenon을 이미 공개했다. 따라서 “Quest occlusion robot lurch 최초 발견”은 방어할 수 없다. 또한 그 issue는 self-report라서 현재 연구의 second confirmation으로도 셀 수 없다.
2. **Trivial narrow fix:** Spes만 놓고 보면 `emulatedPosition`을 payload에 추가해 server에서 gate하는 작은 patch가 H1을 직접 완화할 수 있다. “누락된 boolean 하나” framing은 novelty가 약하다.
3. **Generic timing/transport explanation:** Stale re-stamp, reconnect state inheritance, missing generation은 XR 없이도 generic ROS/network/control bug로 나타날 수 있다. XR-specific contribution은 actual tracked-to-inferred/source transition과 actionability의 causal binding을 입증해야 한다.
4. **Heterogeneous evidence strength:** Spes만 actual hardware-to-production-server다. Quest2ROS2는 synthetic callback, PickNik은 source dataflow, NVIDIA는 static/synthetic positive control이므로 second independent actionable runtime failure가 없다.
5. **External validity:** Spes는 한 device/session의 5 trials이고 browser/runtime version도 canonical raw result에 완전 기록되지 않았다. Population frequency, 모든 Quest/browser, 모든 XR-to-robot stack으로 일반화할 수 없다.
6. **Literature novelty unresolved:** 이번 corpus/repository validation만으로 exhaustive prior-art search나 paper-level novelty를 확정하지 않았다.

현재 방어 가능한 연구 방향은 단일 flag omission보다 다음 composed boundary contract와 그 검증 방법이다.

```text
pose validity + tracked/inferred state + source identity
+ source time/clock contract + session generation
+ invalidation/re-arm epoch
```

이 방향도 두 번째 independent runtime confirmation 전에는 여러 hardening item을 묶은 abstraction이라는 반론이 남는다.

## 7. Current decision

**GO — NOT STRONG GO.** 상세 rubric은 [RESEARCH_DECISION.md](RESEARCH_DECISION.md)에 있다.

- GO인 이유: Spes actual Quest finding이 raw reconstruction과 non-interference로 지지되고, 다른 stack에도 단순 grep보다 강한 callback runtime/source-dataflow/synthetic positive-control evidence가 있다.
- STRONG GO가 아닌 이유: 같은 higher-level invariant에 대한 두 번째 independent stack의 actual runtime/hardware + downstream actionable consequence가 없다.
- 따라서 현재 결정은 paper claim 확정이나 deployment safety 판정이 아니라, 다음 decisive cross-stack experiment로 진행한다는 뜻이다.

현재 허용되는 strongest claim은 “fixed Spes stack에서 actual Quest 3 emulated controller interval이 production server actionability로 계속 이어졌고, inspected stacks가 tracking/source/time/generation/re-arm 의미를 서로 다른 boundary에서 부분 보존·소실·재생성한다”이다.

허용되지 않는 claim은 PickNik/Quest2ROS2 actual Quest unsafe continuation, NVIDIA의 inferred-valid fail-close 보장, issue #731 robot result의 독립 재현, actual ROS/robot hazard, 또는 두 stack generality다.

## 8. Only remaining manual experiments

환경만 복구하면 자동 실행할 수 있는 Quest2ROS2 ROS transport retry는 여기 포함하지 않고 [MANUAL_REQUIRED.md](MANUAL_REQUIRED.md)에 분리했다. 실제 Quest 착용 또는 사용자 물리 조작이 필요한 남은 실험만 다음과 같다. 모두 robot/robot driver 없이 dummy endpoint까지만 수행한다.

1. **Primary decisive experiment — PickNik Quest-to-dummy-ROS:** Actual Quest에서 baseline `isTracked`/tracking bits/Transform과 Odometry/TF reception을 correlation하고, controller를 3–5초 occlude한 뒤 invalid interval의 production Odometry/TF progression과 no-user-rearm recovery를 다섯 valid transitions까지 기록한다. 이것이 repeated `HW_PICKNIK_UNTRACKED_ROS_CONTINUES`로 확인되어야 STRONG GO 후보가 된다. 준비 상태는 [PICKNIK_HW_READY.md](PICKNIK_HW_READY.md)에 있다.
2. **Independent Spes replication:** 별도 session, 가능하면 별도 Quest/browser/runtime에서 T0/T1을 반복해 H1/H3의 재현성과 metadata를 강화한다. Controller-null viewer fallback H2와 actual disconnect T4는 T1과 분리해 관측 가능한 경우에만 수행하며, `NO_LOSS_OBSERVED`를 negative proof로 쓰지 않는다.
3. **NVIDIA native semantic trace:** Linked release와 current main을 분리해 actual Quest/native OpenXR에서 exact `POSITION/ORIENTATION_VALID`, `POSITION/ORIENTATION_TRACKED`, controller activity, retargeter output, dummy ROS reception을 같은 run에 기록한다. Issue #731의 self-report를 raw result로 가져오지 않는다.

이 세 실험 전후 모두 production payload non-interference와 raw time/index correlation을 보존해야 한다. Physical robot 또는 actuator validation은 현재 decision에 필요하지도 허가되지도 않았다.
