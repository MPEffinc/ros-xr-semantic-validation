# Research Decision

## Decision

**GO — NOT STRONG GO**

연구 방향은 계속 진행할 가치가 있다. 다만 현재 self-generated evidence에서 actual XR hardware transition과 downstream actionable consequence를 함께 확인한 implementation은 Spes 하나뿐이다. 따라서 cross-stack generality나 mature-stack-wide vulnerability를 claim할 단계가 아니며, **두 번째 independent runtime/hardware actionable confirmation이 명시적으로 부재한다.**

여기서 GO는 paper claim 확정이나 deployment safety 판정이 아니라 다음 decisive cross-stack experiment로 진행한다는 결정이다.

## Rubric 적용

| Rubric | Required conditions | Current decision |
| --- | --- | --- |
| **STRONG GO** | Independent stack >=2; same higher-level invariant; different implementation mechanisms; runtime or hardware evidence; downstream actionable consequence observed | **NOT MET.** Spes만 actual Quest 3 -> production server callback consequence를 self-generated raw evidence로 보였다. 다른 stack은 synthetic runtime, source/dataflow, static, blocker, 또는 external self-report다. |
| **GO** | Actual hardware motivating finding; cross-stack static/runtime evidence; second independent hardware/runtime confirmation needed | **MET.** Spes actual hardware finding이 있고 Quest2ROS2 callback runtime, PickNik source/dataflow, NVIDIA release/main comparison과 synthetic positive control이 있다. 두 번째 confirmation은 아직 필요하다. |
| **CONDITIONAL GO** | Strong result only one implementation; rest weak/static | **NOT SELECTED.** Strong hardware result는 하나지만, 나머지가 단순 grep만은 아니다. Quest2ROS2 unchanged callback synthetic runtime, PickNik serialized source dataflow 33/33, NVIDIA current-main behavior tests가 있어 rubric의 GO 조건인 cross-stack static/runtime evidence를 충족한다. 단, 이들이 second actionable confirmation을 대신하지는 않는다. |
| **NO-GO** | Single trivial bug; metadata one-field explains everything; same generic ROS/network bug even without XR; mature stacks all safely handle semantics | **NOT MET.** Narrow Spes H1 patch는 one-field fix가 가능하지만 source identity, source time, generation, invalidation/re-arm은 독립 축이다. NVIDIA도 partial guard만 제공하며 `TRACKED`, freshness, generation은 complete positive control이 아니다. |

## 왜 STRONG GO가 아닌가

STRONG GO에는 두 implementation에서 같은 higher-level invariant가 서로 다른 mechanism으로 무너지고, runtime/hardware 및 downstream actionable consequence까지 관측되어야 한다.

| Candidate second stack | Current strongest evidence | Missing decisive link |
| --- | --- | --- |
| Quest2ROS2 | `CONFIRMED_RUNTIME_SYNTHETIC_SOURCE`: unchanged callback이 stale/future stamp와 frame lineage를 대체하며 publish test double까지 진행 | Actual XR producer, actual ROS graph/DDS/node/subscriber, tracking/session transition이 없음. Current Docker probe는 `BLOCKED_ENV`. |
| PickNik | `SOURCE_DATAFLOW_CONFIRMED`: tracking state가 controller Transform driver에는 연결되고 Odometry/TF publisher에서 소실; source time은 wall-clock으로 재생성 | Unity/Quest runtime, actual tracking loss, actual Odometry/TF progression, dummy endpoint reception이 없음. |
| NVIDIA | Linked release `MACHINE_CHECKED_STATIC`; current main invalid-path `RUNTIME_SYNTHETIC`; issue #731 `PUBLIC_ISSUE_SELF_REPORT` | Native OpenXR `VALID`/`TRACKED` trace, ROS output, 이 연구의 independent hardware/robot reproduction이 없음. |

NVIDIA issue #731은 다른 mechanism과 actual hardware/robot을 보고한 중요한 motivation이지만, raw artifact를 이 연구가 재실행·재분석하지 않았으므로 독립 confirmation으로 계산하지 않는다.

## 현재 지지되는 claim

다음 범위는 현재 evidence로 지지된다.

1. **Spes actual hardware finding:** actual Quest 3 valid T1 5/5에서 non-null controller pose가 `emulatedPosition=true`였고 `move=true`가 유지된 동안 production packet과 actual Spes server target callback이 계속됐다.
2. **Spes causal recovery finding:** user move release/re-press 없이 1/5는 continuous, 4/5는 jump reject 뒤 automatic re-anchor/callback resume였다.
3. **Cross-stack boundary pattern:** inspected stacks는 tracking state, source identity, source time, generation, invalidation/re-arm을 서로 다른 조합으로 보존·삭제·재생성·gate한다. 단일 pose object나 `VALID` boolean만으로 actionability를 설명할 수 없다.
4. **Partial positive control:** NVIDIA current main은 `is_valid=false`에서 hold/zero/rebaseline을 synthetic tests로 확인했지만 `TRACKED` bits를 보존하지 않아 inferred-valid interval까지 커버하지 않는다.
5. **Instrumentation attribution:** Spes operator/observer는 tested frontend pose bytes/send decisions와 server callback/control state를 바꾸지 않았다. 이는 tested instrumentation이 hardware finding을 만든 원인이라는 대안을 약화한다.

## 현재 허용되지 않는 claim

- 두 개 이상의 independent stack에서 같은 invariant의 runtime/hardware actionable consequence를 확인했다.
- PickNik 또는 Quest2ROS2가 actual Quest tracking loss에서 unsafe output을 계속 보낸다.
- NVIDIA가 모든 inferred/extrapolated pose를 fail-close한다.
- NVIDIA issue #731의 73 cm/frame robot result를 이 연구가 재현했다.
- Spes 결과가 actual ROS sink, robot motion, actuator hazard까지 이어졌다.
- 한 Quest/session의 5 trials를 population rate나 모든 browser/runtime 동작으로 일반화한다.
- 이 결과만으로 paper-level novelty 또는 deployment-safe defense가 확정됐다.

## Trivial-fix와 novelty threat

Narrow framing인 “Spes packet에 `emulatedPosition` 한 field가 빠졌다”는 작은 patch로 직접 완화할 수 있으므로 novelty threat가 크다. 또한 NVIDIA issue #731은 Quest occlusion/extrapolation/recovery snap과 robot lurch, validity gate 필요성이라는 broad problem framing을 먼저 공개했다.

계속 연구할 수 있는 단위는 다음 composed binding과 그 transition policy다.

```text
pose validity + tracked/inferred state + source identity
+ source time/clock contract + session generation
+ invalidation/re-arm epoch
```

각 stack이 모든 field를 동일 wire schema로 보내야 한다는 주장은 아니다. Boundary에서 동등한 검증을 수행하고 결과를 actionable state와 causal recovery에 결합할 수도 있다. 그러나 두 번째 independent runtime confirmation 전에는 이 abstraction이 실제 공통 failure를 설명한다기보다 여러 one-field hardening 항목을 묶은 것이라는 반론이 남는다.

## Decisive next experiment

### Primary: PickNik hardware-to-dummy-ROS observation

PickNik이 가장 직접적인 STRONG GO 판별 대상이다. Tracking state가 enabled scene의 controller Transform driver까지 연결되고 publisher boundary에서 빠진다는 dataflow가 이미 고정되었기 때문이다.

필요한 성공 조건:

1. Actual Quest에서 baseline `isTracked=true`와 Position+Rotation tracking bits, controller Transform, Odometry/TF reception을 함께 기록한다.
2. Focus/session interruption 없이 controller loss transition을 실제로 만든다.
3. Invalid interval 동안 같은 Transform source에서 production Odometry와 TF index/header/pose가 dummy ROS observer까지 진행하는지 본다.
4. Reacquisition 뒤 explicit re-arm 없이 output이 계속되거나 재개되는지 기록한다.
5. Side-band와 ROS endpoint log를 correlation하고 production `ROSPublishers.cs`가 byte-identical임을 유지한다.

`HW_PICKNIK_UNTRACKED_ROS_CONTINUES`가 valid trial에서 반복되고 downstream dummy observer progression이 확인되면 I1 또는 I5에 대한 second independent hardware/runtime actionable confirmation 후보가 된다. `HW_NO_LOSS_OBSERVED`는 hypothesis failure가 아니라 device path 미관측이다. Robot은 필요하지 않다.

Current blocker는 compatible Unity executable/Android build environment와 ADB-connected authorized Quest, ROS 2 Python environment다. 준비된 instrumentation은 `MACHINE_CHECKED_STATIC READY`일 뿐 hardware result가 아니다.

### Secondary alternatives

- NVIDIA native path에서 exact OpenXR `VALID`/`TRACKED`, controller activity, retargeter output, ROS message를 같은 run에 기록한다. Linked release와 current main을 별도로 실행해야 한다.
- Quest2ROS2 actual ROS harness는 I3 callback result를 DDS/node/subscriber까지 upgrade하는 데 유용하다. 그러나 synthetic pose producer만 사용하면 그 자체로 independent XR tracking-state hardware confirmation은 아니다.

## Upgrade, hold, and pivot criteria

| Outcome | Decision effect |
| --- | --- |
| Second independent stack에서 같은 I1 또는 I5가 different mechanism으로 actual runtime/hardware와 downstream dummy endpoint까지 확인됨 | **STRONG GO 후보**. Raw correlation, non-interference, valid-trial exclusions를 재검증한 뒤 upgrade. |
| Second stack에서 I3만 actual transport로 확인되지만 XR source transition은 synthetic | **GO 유지**. Important cross-stack runtime evidence지만 hardware actionable confirmation 조건은 아직 미충족. |
| PickNik/NVIDIA actual loss에서 semantic이 end-to-end 보존되고 explicit fail-close/re-arm이 일관되게 작동 | **GO 또는 CONDITIONAL GO 재평가**. Safe counterexample로 invariant 설계를 정교화하고 Spes-specific 범위를 축소. |
| 여러 independent mature stack이 모두 safely preserve/gate하고 Spes만 one-field omission으로 남음 | **CONDITIONAL GO 또는 NO-GO/pivot**. General vulnerability가 아니라 implementation case study/validation method로 축소. |
| Actual second-stack transition을 반복해도 loss state 자체가 관측되지 않음 | `NO_LOSS_OBSERVED`; negative safety proof로 쓰지 말고 runtime/device path를 바꾸거나 `UNKNOWN` 유지. |
| Robot/actuator evidence 없이 server/dummy endpoint 결과만 있음 | Actionable software endpoint claim만 유지; physical safety consequence claim 금지. |

## Final disposition

> **GO:** Actual Spes hardware finding과 cross-stack static/synthetic-runtime evidence는 semantic binding과 causal invalidation을 다음 연구 단계로 진행할 충분한 근거다. 그러나 현재 self-generated evidence에는 두 번째 independent runtime/hardware actionable confirmation이 없다. 따라서 결과는 `STRONG GO`가 아니며, 다음 decisive objective는 PickNik 또는 동등한 independent stack에서 actual tracking transition과 downstream dummy endpoint progression을 함께 확인하는 것이다.

근거 matrix: [INVARIANT_MATRIX.md](INVARIANT_MATRIX.md).
