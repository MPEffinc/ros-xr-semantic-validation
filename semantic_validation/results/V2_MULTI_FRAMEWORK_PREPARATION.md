# Multi-Framework Preparation Status — Methodology V2

## Decision recommendation

**`GO — NOT STRONG GO`를 유지한다.** 이번 Quest-less preparation은 new E5/E6 evidence를
만들지 않았다. Spes의 기존 actual Quest → production server callback evidence는 그대로
남지만 actual ROS/consumer boundary를 포함하지 않는다. PickNik은 E1 source/dataflow를
현재 pinned checkout에서 재검증했으나 Unity/Quest/ROS runtime은 실행하지 않았다.

## Framework selection and lineage matrix

| Framework | Verified identity / revision | Family | Inclusion decision | Lineage note |
| --- | --- | --- | --- | --- |
| Spes | `SpesRobotics/teleop@c5d808155a87` | WebXR/WSS | included | standalone WebXR frontend and FastAPI/WSS server |
| PickNik | `PickNikRobotics/meta_quest_teleoperation@bbaef0762fdb` | Unity/ROS-TCP | included | standalone Unity application, external MoveIt Pro consumer |
| LTS0429 | `lts0429/teleoperation@65ce76c9b92d` | Custom UDP/ROS2 | inclusion deferred | public APK source is absent; host UDP path only |
| AgileX | `agilexrobotics/QuestArmTeleop@145b80360cf2` | Quest reader/ADB + ROS2 | inclusion deferred | public host/IK path, opaque bundled APK |
| Legged | `leggedrobotics/unity_ros_teleoperation@0edde9493721` | Unity/OpenXR ROS-TCP | inclusion deferred | hand telemetry is mapped; original control consumer is not |
| NU-MECH | candidate repository unspecified | unknown | `CANDIDATE_IDENTITY_UNCONFIRMED` | no repository was guessed or cloned |

Deferred does not mean safe or unsafe. It means the V2 inclusion criteria are not yet met.

## Semantic and boundary matrix

| Framework | I1 tracking | I2 identity | I3 source time | I4/I5 generation/recovery | Replay boundary | Downstream boundary |
| --- | --- | --- | --- | --- | --- |
| Spes | raw generic T1 mapping ambiguous; packet lacks tracking field | controller/viewer distinction omitted from packet | omitted | not generation-bound in server E2 test | WSS packet: `BOUNDARY_LIMITED_REPLAY` | original server callback; optional ROS unrun |
| PickNik | source tracking actions reach Transform; dropped at Odometry/TF publisher | left/right partial preservation | wall-clock restamp | no audited publisher contract | packet/topic replay is boundary-limited | MoveIt Pro external/unavailable |
| LTS0429 | unmapped behind opaque APK | topic labels only | receiver restamp | unmapped | no adapter | MoveIt Servo candidate unrun |
| AgileX | unmapped behind opaque APK | host left/right keys only | host restamp | absent from host representation | no adapter | IK emits JointState; driver external |
| Legged | hand telemetry gates at `hand.isTracked` | inspected right-hand telemetry | no source stamp in inspected payload | consumer contract unconfirmed | post-gate replay boundary-limited | no connected original consumer |

The detailed maps are in `semantic_validation/frameworks/<id>/`. A source-side result is never
promoted to runtime, Pi, native-consumer, or actuator evidence.

## MULTI-FRAMEWORK PREPARATION STATUS

| Framework | Family | Source mapped | Env | Replay | Pi | Native consumer | Quest ready | Evidence |
| --------- | ------ | ------------- | --- | ------ | -- | --------------- | ----------- | -------- |
| Spes | WebXR/WSS | R1 ready | R2 synthetic ready | R4 boundary-limited | not connected | callback only; ROS consumer unavailable | R5 run orchestration present | E2 synthetic WSS/server; prior hardware callback below E5 |
| PickNik | Unity/ROS-TCP | R1 ready | R2 blocked: Unity/ROS absent | only boundary-limited candidate | observer prepared, unrun | external MoveIt Pro unavailable | blocked by Unity environment | E1 33/33 source/dataflow |
| LTS0429 | Custom UDP/ROS2 | `SOURCE_PATH_UNCONFIRMED` | blocked: ROS/Quest absent | not prepared | unrun | unrun | blocked | E0/E1 host-wire only |
| AgileX | ADB + ROS2 | `SOURCE_PATH_UNCONFIRMED` | blocked: ROS/Quest absent | not prepared | unrun | IK source only; driver unrun | blocked by hardware/env | E0/E1 host-path only; syntax check |
| Legged | Unity/OpenXR ROS-TCP | telemetry partial; control path unconfirmed | blocked: Unity/ROS absent | boundary-limited only | unrun | unconfirmed | blocked by environment | E1 partial telemetry map |
| NU-MECH | unknown | identity unconfirmed | N/A | N/A | N/A | N/A | N/A | E0 only |

## Hardware-free validation artifacts

| Check | Result | Exact boundary |
| --- | --- | --- |
| Spes synthetic runtime suite | 10/10 `PASS`, 0 hardware/robot | production loopback HTTPS/WSS and `Teleop.__update`; `BOUNDARY_LIMITED_REPLAY` |
| PickNik source/dataflow validator | 33/33 `PASS` | pinned Unity source plus serialized scene/action links; no Unity runtime |
| PickNik analyzer self-test | 4/4 `OK` | deterministic source-model/analyzer helper tests |
| AgileX host script syntax | `py_compile` pass | four public Python host scripts; no imports/device/ROS execution |

Artifacts: `semantic_validation/logs/v2_multi_framework_20260907T000002Z/` (PickNik) and
`semantic_validation/logs/v2_multi_framework_20260907T000003Z/` (Spes). Earlier setup/sandbox
attempts were preserved outside the repository as non-canonical diagnostics and are not used as
evidence.

## Ready for canonical replay

None. The only executable Spes replay begins at the WSS packet after browser-native source
selection, so it is not canonical pre-gate replay. PickNik, LTS0429, AgileX, and Legged have no
validated pre-gate injection adapter.

## Boundary-limited only

- Spes: production WSS packet to server replay; server logic stays active, browser WebXR logic is bypassed.
- PickNik: prospective Transform/ROS-TCP/topic injection would bypass Unity Input/OpenXR tracking logic.
- Legged: prospective payload injection would bypass `XRHand.isTracked`.

## Ready for native Quest

Spes retains existing Quest orchestration but a new run must correlate raw V2 observables and
actual ROS before it can reach E5. PickNik has a complete robot-free procedure and sideband/Pi
analysis package, but is **not** R5 until Unity `6000.1.6f1` and a compatible ROS shell are
available. No other candidate is Quest-ready.

## Blocked

- No compatible Unity executable or host ROS 2 Python environment is present.
- No authorized ADB-connected Quest is present; ADB binary existence alone is not device evidence.
- LTS0429 and AgileX omit source for their APK-native semantic contract.
- Legged's telemetry-to-original-control-consumer dataflow is incomplete.
- Original MoveIt Pro and actual arm-driver consumers are not in scope for launch without a
  robot-free dry-run/stub proof.

## Positive controls

Legged `HandPub` has an inspected `hand.isTracked` source gate, but its control path is
unconfirmed, so it is not a counterexample to an end-to-end finding. Existing NVIDIA evidence
remains the project's partial positive control: `VALID` is gated while `TRACKED` is not proven
preserved. Positive controls are retained as design evidence, not failure labels.

## Architecture-family coverage

Identity is verified for five repositories spanning WebXR/WSS, Unity/ROS-TCP, custom UDP/ROS2,
ADB/logcat-to-ROS2, and Unity/OpenXR ROS-TCP. This is implementation discovery/source coverage,
not five independent native runtime confirmations. Only Spes and PickNik currently meet the V2
source-audit inclusion bar for the principal comparison population.

## Methodological threats still open

1. Pre-gate replay is unavailable for every current candidate; replay evidence cannot answer RQ3.
2. Pi reception remains O3 transport evidence, never native consumer acceptance.
3. Raw API semantics are not equivalent by name; Unity/Meta/OpenXR/WebXR mappings need per-run
   raw capture and confidence records.
4. Opaque APKs prevent assessment of native tracking, source-time, and session semantics.
5. A second independent E5/E6 architecture-family result is still absent.

## Recommended next hardware session

After supplying Unity `6000.1.6f1` (Android support), a ROS 2 Python environment, and an
authorized Quest, run the already prepared **PickNik actual Quest → dummy ROS observer** T0/T1
procedure. Do not attach a physical robot or driver. Require five valid raw
tracked→degraded→reacquired transitions, sideband-to-ROS correlation, and report at most E5 if
actual ROS reception is established; Pi reception alone remains `PI_RECEIVED`.
