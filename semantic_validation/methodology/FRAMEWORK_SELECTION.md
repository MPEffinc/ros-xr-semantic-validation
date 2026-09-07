# Framework Selection and Lineage Policy V2

## Inclusion rule

후보는 안전해 보인다는 이유로 제외하지 않는다. 다만 다음 일곱 조건을 source audit로
확인하기 전에는 included framework로 기록하지 않는다.

1. 공개 source가 존재한다.
2. actual XR hardware input을 사용한다.
3. control-producing path가 존재한다.
4. ROS/ROS 2 또는 명시적 robot-control boundary가 존재한다.
5. source semantic 또는 source abstraction을 audit할 수 있다.
6. physical actuator 없이 downstream을 관측할 수 있다.
7. repository identity와 revision을 pin할 수 있다.

repo 이름, organization, branch, availability를 추측해서 clone하지 않는다. identity가
확인되지 않으면 `CANDIDATE_IDENTITY_UNCONFIRMED`로, source chain을 연결하지 못하면
`SOURCE_PATH_UNCONFIRMED`로 기록한다. candidate가 조건을 충족하지 않는 것은 failure나
negative semantic finding이 아니다.

## Batch 1 candidate ledger

| ID | User-named candidate | 현재 identity 상태 | 처리 원칙 |
| --- | --- | --- | --- |
| Spes | `SpesRobotics/teleop` | local pinned checkout `c5d808155a87` verified | WebXR/WSS source map과 existing hardware boundary를 V2로 migrate |
| PickNik | `PickNikRobotics/meta_quest_teleoperation` | local pinned checkout `bbaef0762fdb` verified | Unity/ROS-TCP source map, disposable staging, existing sideband harness 활용 |
| LTS | `lts0429/teleoperation` | identity re-verification pending | URL/branch/control path 확인 전 clone/build 금지 |
| AgileX | `agilexrobotics/QuestArmTeleop` | identity re-verification pending | URL/branch/control path 확인 전 clone/build 금지 |
| Legged | `leggedrobotics/unity_ros_teleoperation` | identity re-verification pending | URL/branch/control path 확인 전 clone/build 금지 |
| NU-MECH | Quest/hand-tracking ROS 2 candidate | candidate name/repository pending | source identity 확인 전 `CANDIDATE_IDENTITY_UNCONFIRMED` |

Existing Quest2ROS2와 NVIDIA/Isaac local checkouts are comparative/positive-control
evidence from the previous decision; they are not silently substituted for a named Batch 1
candidate. Any addition to Batch 1 must document the selection decision.

## Independence and lineage

Implementation count와 architecture-family count를 분리한다. fork, shared example,
shared SDK wrapper, shared core implementation을 independent stack으로 중복 계산하지
않는다. `independent stack`은 다음 record가 완성된 뒤에만 사용한다.

| Required lineage field | Meaning |
| --- | --- |
| upstream repository / URL | verified canonical source origin |
| pinned SHA / tag / branch | reproducible source identity |
| framework lineage | fork/derivative/shared-example relationship |
| XR SDK / API | WebXR, Unity XR/Meta, OpenXR 등 |
| ROS integration | ROS-TCP, rosbridge, DDS, native node 등 |
| transport | WSS, TCP, UDP, DDS, ADB 등 |
| downstream controller | original consumer, dry-run availability, actuator boundary |
| shared-code origin | re-used package, common transport, common frontend evidence |

Possible family labels include `WebXR/WSS`, `Unity/ROS-TCP`, `Custom UDP/ROS2`,
`Quest reader/ADB`, `native OpenXR`, `ROSBridge/WebSocket`, `custom DDS`. Labels alone는
independence 증거가 아니며 source lineage record가 우선한다.

## Readiness model

| Level | Requirement | Hardware claim? |
| --- | --- | --- |
| R0 `DISCOVERED` | repository identity and pin verified | 아니오 |
| R1 `SOURCE_MAPPED` | native production dataflow와 relevant semantic decision point identified | 아니오 |
| R2 `ENVIRONMENT_READY` | isolated environment/build success | 아니오 |
| R3 `SYNTHETIC_RUNTIME_READY` | synthetic input으로 production-path runtime success | 아니오 |
| R4 `REPLAY_READY` | adapter, injection boundary, classification validated | 아니오 |
| R5 `QUEST_READY` | actual Quest run scripts/runbook/preflight ready | 아니오 |

Readiness와 evidence level은 orthogonal이다. R5는 native hardware result가 아니며,
actual hardware evidence는 E5/E6에만 기록한다.

## Selection outcome template

각 candidate에는 `manifest.yaml`과 `PINNED_REVISION`을 만들고 identity decision,
inclusion criteria status, architecture family, lineage, readiness, blockers를 기록한다.
source availability를 입증하지 못한 candidate에는 empty skeleton이나 guessed command를
만들지 않는다. verified source가 있는 candidate만 framework directory와 source audit을
진행한다.

## Positive-control policy

semantic을 preserve/gate하는 implementation은 positive control로 유지한다. positive
control은 failure가 아니라 ambiguity를 줄이는 design pattern의 근거다. NVIDIA existing
comparison은 `VALID` gate가 `TRACKED` semantics까지 보존한다는 증거가 아니므로 partial
positive control로만 표기한다.
