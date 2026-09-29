# XR-to-Robot Semantic Invariant Matrix

## 결론

현재 증거는 **다섯 invariant를 비교할 수 있는 cross-stack pattern**을 보이지만, 증거 강도는 비대칭이다.

- Spes만 actual Quest 3 tracking transition과 actual production server callback을 같은 run에서 연결했다.
- Quest2ROS2는 synthetic source로 pinned production node, actual ROS/DDS, Pi 619/619 및
  disconnect/reconnect 상태 보존까지 실행했다. XR frontend는 여전히 black box다.
- Docker_Teleop과 OpenVR UR5e는 controlled fake/synthetic source에서 production
  MoveIt Servo/Gazebo와 simulated joint consequence까지 실행됐다.
- PickNik은 enabled Unity scene source dataflow와 별도의 ROS-TCP backend 3600/3600을
  확인했지만, replay injection이 PickNik code 뒤이므로 native publisher runtime은 아니다.
- NVIDIA는 production ROS message builders/gate를 real rosidl types로 실행한 partial
  positive control이다. Native OpenXR/Quest runtime은 실행하지 않았다.

따라서 이 matrix는 common invariant의 **연구 필요성**을 지지하지만 cross-stack runtime generality를 확정하지 않는다. 두 번째 independent runtime/hardware actionable confirmation은 현재 없다.

## Invariant와 판정 용어

| ID | Invariant | Required property |
| --- | --- | --- |
| I1 | Tracking-State Preservation | Actively tracked와 inferred/emulated를 downstream에서 구별하거나 action 전 동등하게 재검증해야 한다. |
| I2 | Source Identity Preservation | Controller/HMD/hand 또는 그에 준하는 source identity가 같은 actionable pose로 조용히 collapse되면 안 된다. |
| I3 | Source-Time Lineage | 필요한 경로에서 source sample time/clock contract/freshness가 사라지거나 무조건 `now`로 대체되면 안 된다. |
| I4 | Session/Generation Isolation | 새 transport/session generation이 명시적 검증 없이 이전 control context를 상속하면 안 된다. |
| I5 | Causal Invalidation/Re-arm | Tracking/session/control invalidation 뒤 old-context stream이 명시적 조건 없이 자동으로 actionable해지면 안 된다. |

`VIOLATED`는 검사한 boundary에서 required property가 충족되지 않았다는 뜻이다. `PARTIAL`은 일부 identity/state는 보존하지만 invariant 전체는 충족하지 못한다. `POSITIVE CONTROL`은 특정 invalid state에 대한 안전 동작을 확인했다는 뜻이며, 다른 semantic state까지 안전하다는 뜻이 아니다. `UNKNOWN`은 부재 증거가 아니라 해당 transition/endpoint를 실행하지 않았다는 뜻이다.

### Evidence level

| Level | 이 연구에서의 의미 |
| --- | --- |
| `ACTUAL_XR_HARDWARE -> ACTUAL_SPES_SERVER_CALLBACK` | Actual Quest 3 raw semantic transition, production packet progression, actual Spes target callback을 correlation함. ROS/robot은 포함하지 않음. |
| `CONFIRMED_RUNTIME_SYNTHETIC_SOURCE` | Unchanged production frontend/callback/server method를 synthetic source 또는 최소 test double로 실행함. Actual XR producer 또는 actual ROS transport라는 뜻이 아님. |
| `RUNTIME_SYNTHETIC` | Upstream pure-software tests에서 해당 control behavior를 실행함. Native OpenXR/ROS/hardware는 포함하지 않음. |
| `SOURCE_DATAFLOW_CONFIRMED` | Serialized scene/prefab/action reference와 source publisher boundary를 machine-check함. Runtime claim이 아님. |
| `MACHINE_CHECKED_STATIC` | Pinned source/schema/token/structure assertion 또는 executable source model. Runtime claim이 아님. |
| `PUBLIC_ISSUE_SELF_REPORT` | 외부 contributor의 public hardware/robot report. 이 연구의 독립 재현으로 세지 않음. |
| `BLOCKED_ENV` / `BLOCKED_HW` | 필요한 environment/hardware가 없어 실행하지 않음. Negative result가 아님. |

A checker의 `PASS`는 위 evidence level에서 검사가 통과했다는 뜻이지 stack이 invariant를 만족한다는 뜻이 아니다.

## I1 — Tracking-State Preservation

| Stack | Boundary result | Strongest evidence | Exact boundary and remaining unknown |
| --- | --- | --- | --- |
| **Spes** | **VIOLATED** | `ACTUAL_XR_HARDWARE -> ACTUAL_SPES_SERVER_CALLBACK` | Valid T1 5/5에서 controller pose는 non-null, `emulatedPosition=true`, source는 `CONTROLLER`, `move=true`였지만 production packet에 tracking state가 없었고 packet/server callback이 계속 진행했다. Pinned upstream ROS2 publisher→Pi 30/30은 별도 E2 run이며 prior hardware trace와 같은 continuous run은 아니다. |
| **Quest2ROS2** | **UNKNOWN for tracked-vs-inferred** | I1 transition에는 direct evidence 없음; callback의 최고 level은 `CONFIRMED_RUNTIME_SYNTHETIC_SOURCE` | Callback 입력은 `PoseStamped`이고 actual XR producer/tracking flag를 실행하지 않았다. Pose acceptance만으로 actively tracked와 inferred collapse를 주장하지 않는다. |
| **PickNik** | **VIOLATED at Transform -> Odometry/TF dataflow boundary** | `SOURCE_DATAFLOW_CONFIRMED` | `trackingState`와 `isTracked`는 enabled scene의 controller Transform driver까지 연결되지만 `RosPublishers`는 resulting Transform만 읽고 tracking state를 serialize/gate하지 않는다. Real Quest가 loss 때 어떤 state/Transform을 내는지는 `BLOCKED_HW`; ROS continuation도 미실행. |
| **NVIDIA** | **PARTIAL POSITIVE CONTROL; I1 incomplete** | linked release `MACHINE_CHECKED_STATIC`; current main invalid-path `RUNTIME_SYNTHETIC` | Controller activity와 OpenXR position/orientation `VALID`는 보존/gate하지만 `POSITION_TRACKED`/`ORIENTATION_TRACKED`는 읽거나 serialize하지 않는다. Current main은 `is_valid=false`에서 hold/zero/rebaseline하지만, `VALID=true`인 inferred pose를 구별한다는 증거는 없다. |

### `VALID`와 `TRACKED`의 구분

OpenXR에서는 inferred 또는 last-known pose가 제공되는 동안 `POSITION_VALID`가 유지되고 `POSITION_TRACKED`가 해제될 수 있다. 따라서 `VALID=true`는 active tracking과 동의어가 아니다. 이 구분 때문에 NVIDIA의 validity gate는 유용한 positive control이지만 I1의 complete positive control은 아니다. 공식 정의: [Khronos OpenXR `XrSpaceLocationFlags`](https://registry.khronos.org/OpenXR/specs/1.1/html/xrspec.html#XrSpaceLocationFlags).

## I2 — Source Identity Preservation

| Stack | Boundary result | Strongest evidence | Exact boundary and remaining unknown |
| --- | --- | --- | --- |
| **Spes** | **VIOLATED in source-faithful software runtime** | `CONFIRMED_RUNTIME_SYNTHETIC_SOURCE` | Actual frontend에서 controller-valid, controller-emulated, controller-null/viewer-fallback의 같은 numeric pose가 byte-equivalent production packet이 됐다. Viewer sequence는 jump 한 번 뒤 server target에 수용됐다. Actual Quest T1에서는 source가 계속 `CONTROLLER`였으므로 viewer fallback hardware activation은 `NOT_OBSERVED`, hypothesis failure가 아니다. |
| **Quest2ROS2** | **PARTIAL VIOLATION for input frame provenance; XR modality UNKNOWN** | `CONFIRMED_RUNTIME_SYNTHETIC_SOURCE` | Unchanged callback은 `xr_controller_A`, `xr_controller_B`, old/new reference-space labels를 output `robot_base`로 대체했다. 이는 software-boundary frame lineage 결과이며 actual controller/HMD/hand transition 또는 OpenXR reference-space switch 재현은 아니다. |
| **PickNik** | **PARTIAL** | `SOURCE_DATAFLOW_CONFIRMED` | Left/right는 separate topics와 child frames로 보존되는 positive control이다. 그러나 input actions는 `XRController`와 `XRHandDevice` bindings를 같은 side Transform으로 공급할 수 있고 ROS schema에는 modality가 없다. Runtime source switching은 미검증. |
| **NVIDIA** | **PARTIAL POSITIVE CONTROL** | `MACHINE_CHECKED_STATIC` | Left/right subaction path와 internal tensor group은 분리된다. Linked release EE `PoseArray`는 positional convention, current main `NamedPoseArray`는 side name을 보존한다. Controller-vs-hand modality는 generic EE output에 first-class identity로 남지 않으며 native runtime switching은 미검증. |

## I3 — Source-Time Lineage

| Stack | Boundary result | Strongest evidence | Exact boundary and remaining unknown |
| --- | --- | --- | --- |
| **Spes** | **VIOLATED** | delayed acceptance `CONFIRMED_RUNTIME_SYNTHETIC_SOURCE`; hardware run은 payload omission을 보조 확인 | Production packet에는 source timestamp/sequence가 없다. Actual WSS/server replay에서 1.05 s 이상 delayed single pose와 trajectory가 source age를 알 수 없는 채 callback으로 수용됐다. Actual Quest age fault나 robot consequence는 미실행. |
| **Quest2ROS2** | **VIOLATED** | `E2 SYNTHETIC_RUNTIME`, actual production node and ROS transport | 10 ms~10 s old 및 1 s future `PoseStamped` 7/7이 actual ROS output까지 진행했다. Input stamp/frame은 읽히지 않고 callback-time `now`/configured `robot_base`로 대체됐다; 별도 SimulationInput run은 Pi 619/619에 도달했다. |
| **PickNik** | **VIOLATED at publisher dataflow boundary** | `SOURCE_DATAFLOW_CONFIRMED` | Publisher에는 source sample-time input이나 age gate가 없고 ROS stamp는 `DateTime.UtcNow`로 생성된다. Unity execution과 actual ROS delivery는 미실행. |
| **NVIDIA** | **INCOMPLETE / actionable path drops lineage** | `MACHINE_CHECKED_STATIC` | Controller snapshot record 내부에는 query/update time이 있으나 retargeter/ROS EE path까지 이어지지 않는다. ROS header/raw payload time은 새로 생성되고 inspected path에 source-age gate가 없다. Physical sensor capture-time contract나 native runtime age behavior는 미검증. |

## I4 — Session/Generation Isolation

| Stack | Boundary result | Strongest evidence | Exact boundary and remaining unknown |
| --- | --- | --- | --- |
| **Spes** | **VIOLATED** | `CONFIRMED_RUNTIME_SYNTHETIC_SOURCE` over actual HTTPS/WSS route and `Teleop.__update` | 새 WSS generation은 production control state에 결합되지 않았다. Near reconnect는 즉시 callback/target update, far reconnect는 한 jump reject 뒤 자동 re-anchor와 target update가 됐다. Hardware disconnect/ROS/robot은 미실행. |
| **Quest2ROS2** | **DROPPED / state retained across reconnect** | `E2 SYNTHETIC_RUNTIME` | 동일 production node가 살아 있는 동안 input publisher를 disconnect/reconnect했다. Anchor, filter lineage와 arming edge latch가 transport replacement 뒤 유지됐고, false→true edge만 명시적으로 re-enable/re-anchor했다. Actual Quest app generation은 여전히 미검증이다. |
| **PickNik** | **NOT REPRESENTED in inspected publisher; runtime UNKNOWN** | `MACHINE_CHECKED_STATIC` | ROS publisher schema/path에 XR session/reference-space generation 또는 focus/pause invalidation hook을 찾지 못했다. 실제 focus, reconnect, app resume, Quest runtime은 `BLOCKED_ENV/HW`. |
| **NVIDIA** | **NOT FOUND in inspected actionable path; runtime UNKNOWN** | `MACHINE_CHECKED_STATIC` | Controller/session reconnect generation을 ROS/control output과 결합하는 field/check를 찾지 못했다. Internal tensor schema generation을 transport generation 증거로 세지 않았다. Native reconnect/session execution은 미실행. |

## I5 — Causal Invalidation/Re-arm

| Stack | Boundary result | Strongest evidence | Exact boundary and remaining unknown |
| --- | --- | --- | --- |
| **Spes** | **VIOLATED** | `ACTUAL_XR_HARDWARE -> ACTUAL_SPES_SERVER_CALLBACK` | Valid T1 5/5에서 loss부터 recovery까지 `move=false`가 없고 user release/re-press도 없었다. 1/5는 `RECOVERY_CONTINUOUS`, 4/5는 loss-window jump reject 뒤 automatic re-anchor/callback resume였다. Explicit `move=false`는 synthetic positive control에서 anchors를 clear하지만 tracking invalidation과 자동 결합되지 않는다. |
| **Quest2ROS2** | **PARTIAL; transport loss does not re-arm** | `E2 SYNTHETIC_RUNTIME` | Input disconnect/reconnect만으로 arming latch/anchor/filter는 reset되지 않았다. A new false→true `button_lower` edge re-enabled and re-anchored. Actual tracking loss and opaque app reconnect semantics remain unknown. |
| **PickNik** | **INCOMPLETE at publisher contract; actionable consequence UNKNOWN** | publisher-boundary absence `SOURCE_DATAFLOW_CONFIRMED` | Publisher는 tracking/focus/session invalidation이나 re-arm을 consume하지 않는다. 하지만 actual loss에서 Transform/ROS가 계속되는지 실행하지 않았으므로 runtime violation이나 downstream consequence를 주장하지 않는다. |
| **NVIDIA** | **PARTIAL POSITIVE CONTROL** | current main `RUNTIME_SYNTHETIC`; linked release `MACHINE_CHECKED_STATIC` | Current main generic retargeters는 `is_valid=false`에서 absolute hold, relative zero/smoothing clear, 다음 valid frame rebaseline을 수행한다. Linked release generic SE3 path에 같은 behavior를 소급하지 않는다. `VALID=true` inferred interval, explicit user authorization epoch, native Quest recovery는 미검증. |

## NVIDIA release와 current-main 경계

| Revision | What is established | What must not be transferred across the boundary |
| --- | --- | --- |
| `isaac_ros_teleop main@197f5cd9` + linked `IsaacTeleop release/1.3.x@465ce637` | Activity/VALID dataflow와 linked-release ROS schema를 machine-check함. SO-101-specific clutch에는 invalid hold가 있으나 generic release SE3 validity/recovery는 implementation-specific. | Current-main generic hold/zero/rebaseline을 이 production-linked release의 behavior로 쓰면 안 됨. |
| `IsaacTeleop current main@334978b0` | Local executed checkout `9fba23c4`와 semantic source files가 official remote main `334978b0`에 source-equivalent함. Upstream pure-Python validity/recovery tests 10/10 PASS. | Synthetic tests를 native DeviceIO/OpenXR, ROS transport, Quest hardware result로 올리면 안 됨. |
| Both | Inspected controller tracker uses `VALID`, not `TRACKED`; source-time/freshness와 reconnect generation은 actionable path에서 완전 보존되지 않음. | `VALID` gate가 inferred/extrapolated pose까지 항상 fail-close한다는 결론은 허용되지 않음. |

## Positive controls — independent findings와 분리

| Positive control | Evidence | What it establishes | What it does not establish |
| --- | --- | --- | --- |
| Spes explicit `move=false` | `CONFIRMED_RUNTIME_SYNTHETIC_SOURCE` | Explicit clutch-off가 anchors를 clear할 수 있음. | Tracking/source/session invalidation과 자동 결합됨을 보이지 않음. |
| PickNik left/right topics and child frames | `SOURCE_DATAFLOW_CONFIRMED` | Handedness는 publisher boundary에서 구분됨. | Controller-vs-hand modality나 reference-space generation 보존을 보이지 않음. |
| NVIDIA activity/VALID gate | `MACHINE_CHECKED_STATIC` | Inactive/invalid controller 상태가 first-class signal로 전달되는 경로가 있음. | `VALID=true` inferred pose의 active tracking 여부를 보이지 않음. |
| NVIDIA current-main invalid recovery | `RUNTIME_SYNTHETIC` | Invalid grip에서 hold/zero 및 relative rebaseline behavior가 regression tested됨. | Linked release, native OpenXR, actual Quest, ROS/robot behavior를 보이지 않음. |

## Explicit unknowns and blockers

| Stack | Still unknown / blocked |
| --- | --- |
| Spes | Actual controller-null viewer fallback, actual disconnect generation/source-age fault on Quest, and one continuous Quest→native ROS→Pi run. Separate native-publisher/Pi E2 leg is complete. |
| Quest2ROS2 | Actual opaque-app XR semantics, I1 transition, actual app generation/reconnect, and original missing CLIK consumer. ROS/DDS/Pi and host reconnect runtime are complete. |
| PickNik | Unity licence entitlement, Quest tracking-state transition and Transform behavior, execution of PickNik Odometry/TF publisher, downstream MoveIt use. Backend-only replay is not that execution. |
| NVIDIA | Native DeviceIO/OpenXR flag trace, `VALID` versus `TRACKED` during Quest occlusion, reconnect generation, hardware reproduction. Production ROS builder/gate E2 is complete without DDS/native XR. |

## External issue and independence boundary

[NVIDIA IsaacTeleop issue #731](https://github.com/NVIDIA/IsaacTeleop/issues/731)은 Quest 3/CloudXR occlusion, extrapolated pose, recovery snap, SO-101 lurch를 보고한 `PUBLIC_ISSUE_SELF_REPORT`다. 이는 중요 external motivation이며 broad “Quest occlusion/robot lurch 최초 발견” claim을 선취한다. 그러나 raw telemetry를 이 연구에서 재분석하거나 실행하지 않았고 exact OpenXR `VALID`/`TRACKED` trace도 없으므로 두 번째 independent reproduction으로 세지 않는다.

## Evidence integrity

- Spes raw re-analysis는 fresh browser generation `4`를 격리했고 valid T1 5회를 raw `experiment.jsonl`/`server.jsonl`에서 다시 구성했다. 기존 analysis와 비교한 129 fields의 mismatch는 0이었다.
- Classifier regression은 recovery window를 semantic loss detection부터 recovery completion까지로 한정했다. T1-1은 `RECOVERY_CONTINUOUS`, T1-2~5는 `RECOVERY_JUMP_REJECT_THEN_REANCHOR`로 raw evidence와 일치한다.
- Spes instrumentation differential은 frontend 7 cases에서 exact production pose bytes/send decisions, server wrapper 12 cases에서 callback/exception/control state equivalence를 확인했다: `INSTRUMENTATION_NON_INTERFERENCE_PASS`.
- 이 integrity result는 관측 계층이 검사한 production behavior의 원인이 아님을 뒷받침하지만, 별도 stack 또는 별도 hardware confirmation으로 세지 않는다.
- PickNik canonical deep run은 33/33 PASS이고 target은 전후 clean이다. PASS의 strongest level은 `SOURCE_DATAFLOW_CONFIRMED`; Unity/Quest/ROS runtime은 아니다.
- NVIDIA linked-release checks 8/8와 current-main pure-Python tests 10/10이 PASS했다. Native runtime/hardware는 아니다.

## Canonical evidence

- [Spes hardware re-analysis](SPES_HW_REANALYSIS.md)
- [Spes classifier regression](SPES_CLASSIFIER_REGRESSION.md)
- [Spes instrumentation integrity](SPES_INSTRUMENTATION_INTEGRITY.md)
- [Spes hardware result](SPES_QUEST_HW_RESULT.md)
- [Spes semantic collision](SPES_SEMANTIC_COLLISION.md)
- [Spes freshness](SPES_FRESHNESS_RESULT.md)
- [Spes reconnect](SPES_RECONNECT_RESULT.md)
- [Quest2ROS2 callback result](QUEST2ROS2_STALE_RESTAMP.md)
- [Quest2ROS2 ROS runtime blocker](QUEST2ROS2_ROS_RUNTIME.md)
- [PickNik deep validation](PICKNIK_DEEP_VALIDATION.md)
- [PickNik hardware readiness](PICKNIK_HW_READY.md)
- [NVIDIA comparison](NVIDIA_VS_SPES_ANALYSIS.md)
- [Trivial-fix threat](TRIVIAL_FIX_THREAT.md)
