# Framework Population Matrix

Generated 2026-09-07. Supersedes the population tables in
[NEXT_PHASE_STATUS.md](NEXT_PHASE_STATUS.md) and
[AUTONOMOUS_QUESTLESS_CONVERGENCE.md](AUTONOMOUS_QUESTLESS_CONVERGENCE.md) by adding the
frameworks audited in this session and by replacing the single INCLUDED/EXCLUDED bit with the
four independent axes defined in the audit brief.

> **Quest-free closure update (2026-09-14):** identity and role assignments remain useful here,
> but current build/runtime/status results are authoritative in
> [QUESTLESS_COMPLETION_MATRIX.md](QUESTLESS_COMPLETION_MATRIX.md). The rows below have been
> corrected where later execution changed a factual boundary.

Axis vocabularies are those of the brief: **System relevance** (`HIGH_XR_ROS_CONTROL`,
`XR_ROS_BRIDGE_ONLY`, `XR_ROBOT_NON_ROS`, `XR_UI_OR_VISUALIZATION`, `NOT_RELEVANT`);
**Semantic observability** (`FULL_SOURCE`, `PARTIAL_SOURCE`, `BLACK_BOX_XR_FRONTEND`,
`BLACK_BOX_DOWNSTREAM`, `WIRE_ONLY`, `UNKNOWN`); **Control depth** (`TELEMETRY_ONLY`,
`ROS_PUBLISHED`, `CONTROL_TARGET`, `NATIVE_CONSUMER`, `DRIVER_PREWRITE`, `ACTUATOR_BOUNDARY`);
**Testbed adaptability** (`DIRECT_PI`, `ROS_ADAPTER_REQUIRED`, `SIMULATOR_AVAILABLE`,
`INERT_STUB_FEASIBLE`, `NATIVE_OBSERVER_ONLY`, `BLACK_BOX_RUNTIME_ONLY`, `NOT_FEASIBLE`).

`(prior)` marks findings carried forward from earlier sessions and not re-verified here.
Everything else was audited against the pinned source in this session.

## A. Identity and pinned revision

| # | Framework | Repository | Pinned revision | Audited this session |
| --- | --- | --- | --- | --- |
| 1 | Spes | `SpesRobotics/teleop` | `c5d808155a87…` | (prior) |
| 2 | PickNik | `PickNikRobotics/meta_quest_teleoperation` | `bbaef0762fdb…` | (prior) |
| 3 | Quest2ROS2 | `Taokt/Quest2ROS2` | `07aaf65149c9…` | **yes** |
| 4 | Docker_Teleop | `Noah727/Docker_Teleop` | `64cbdde88bc5…` | **yes** |
| 5 | OpenVR UR5e | `mrutyunjaykalyani/teleoperation-…-jazzy-` | `170dad582d62…` | **yes** |
| 6 | OpenArmX | `openarmx/openarmx_teleop_vr` | `a3da7411b3d6…` (`6.0_basic`) | **yes** |
| 7 | VR-hand-bridge | `mahmoud-maan/VR-hand-bridge-ROS2` | `a5da3e09def3…` | **yes** |
| 8 | Nakama | `nakama-lab/VR_Teleop_Interface` | `aebf6394a16d…` | **yes** |
| 9 | xiaoxiaoxh | `xiaoxiaoxh/vr-teleoperation` | `1d29f9f35f77…` | (prior) |
| 10 | Reachy VR Quest | `HRI-EU/reachy-vr-quest` | `242120ee9e35…` | (prior) |
| 11 | NU-MECH | `NU-MECH-ENG-495/vr-hand-tracking` | `8b685f91727b…` | (prior) |
| 12 | Legged | `leggedrobotics/unity_ros_teleoperation` | `0edde9493721…` | (prior) |
| 13 | Homebrew | `homebrewroboticsclub/vr-teleop` | `2952d27…` | (prior) |
| 14 | XRoboToolkit | `XR-Robotics/XRoboToolkit-Teleop-ROS` | `a516bb280610…` | (prior) |
| 15 | LTS0429 | `lts0429/teleoperation` | `65ce76c9b92d…` | (prior) |
| 16 | AgileX | `agilexrobotics/QuestArmTeleop` | `145b80360cf2…` | (prior) |
| 17 | xArm Quest | `RuiyuWANG/xarm_quest_teleop` | `8220579…` | (prior) |
| 18 | NVIDIA IsaacTeleop | `NVIDIA/IsaacTeleop` + `isaac_ros_teleop` | `9fba23c…` / `197f5cd…` | (prior) |

## B. Four independent axes

| # | Framework | System relevance | Semantic observability | Control depth (best auditable) | Testbed adaptability |
| --- | --- | --- | --- | --- | --- |
| 1 | Spes | `HIGH_XR_ROS_CONTROL` | `FULL_SOURCE` | `CONTROL_TARGET` at server callback; `ROS_PUBLISHED` through pinned upstream `teleop/ros2` | `DIRECT_PI` |
| 2 | PickNik | `HIGH_XR_ROS_CONTROL` | `FULL_SOURCE` | `ROS_PUBLISHED`; original consumer MoveIt Pro is external | `DIRECT_PI`, `NATIVE_OBSERVER_ONLY` (Unity build blocked) |
| 3 | Quest2ROS2 | `HIGH_XR_ROS_CONTROL` | `BLACK_BOX_XR_FRONTEND` + full host source | **`NATIVE_CONSUMER`** (executed) | `DIRECT_PI`, `INERT_STUB_FEASIBLE`, in-repo simulator |
| 4 | Docker_Teleop | `HIGH_XR_ROS_CONTROL` | `FULL_SOURCE` | **`NATIVE_CONSUMER`** + simulated joint motion | `SIMULATOR_AVAILABLE`, `DIRECT_PI`, `INERT_STUB_FEASIBLE` |
| 5 | OpenVR UR5e | `HIGH_XR_ROS_CONTROL` | `FULL_SOURCE` (bridge); XR runtime opaque | **`NATIVE_CONSUMER`** + simulated joint motion | `SIMULATOR_AVAILABLE` (Jazzy container required) |
| 6 | OpenArmX | `HIGH_XR_ROS_CONTROL` | `PARTIAL_SOURCE` (closed IK core, external APK) | `ROS_PUBLISHED` reachable; `DRIVER_PREWRITE` blocked by closed core | `INERT_STUB_FEASIBLE` for bridge only |
| 7 | VR-hand-bridge | `XR_ROS_BRIDGE_ONLY` | `FULL_SOURCE` | `TELEMETRY_ONLY` / `ROS_PUBLISHED` | `DIRECT_PI` (low yield) |
| 8 | Nakama | `NOT_RELEVANT` at this identity (`SOURCE_PATH_UNCONFIRMED`) | `UNKNOWN` — no code in repo | none | `NOT_FEASIBLE` |
| 9 | xiaoxiaoxh | `HIGH_XR_ROS_CONTROL` | `FULL_SOURCE` | `NATIVE_CONSUMER` exists in source (direct Flexiv server); wire schema only executed | `HARDWARE_ONLY_UNSAFE` for the control path |
| 10 | Reachy VR Quest | `XR_ROBOT_NON_ROS` | `FULL_SOURCE` | `NATIVE_CONSUMER` via daemon WebSocket, no ROS | `INERT_STUB_FEASIBLE` (prior) |
| 11 | NU-MECH | `XR_ROS_BRIDGE_ONLY` | `FULL_SOURCE` | `TELEMETRY_ONLY` (Qt visualiser) | `DIRECT_PI` (prior) |
| 12 | Legged | `XR_ROS_BRIDGE_ONLY` (control path unconfirmed) | `PARTIAL_SOURCE` | `ROS_PUBLISHED` telemetry | `NATIVE_OBSERVER_ONLY` (prior) |
| 13 | Homebrew | `XR_ROS_BRIDGE_ONLY` | `FULL_SOURCE` | no included robot consumer | Unity 2022 required (prior) |
| 14 | XRoboToolkit | `HIGH_XR_ROS_CONTROL` (vendor stack) | `WIRE_ONLY` / `BLACK_BOX_XR_FRONTEND` | `ROS_PUBLISHED`; ARX consumer external | `BLACK_BOX_RUNTIME_ONLY` (prior) |
| 15 | LTS0429 | `HIGH_XR_ROS_CONTROL` (claimed) | `BLACK_BOX_XR_FRONTEND` (APK only) | unconfirmed | `BLACK_BOX_RUNTIME_ONLY` (prior) |
| 16 | AgileX | `HIGH_XR_ROS_CONTROL` (claimed) | `BLACK_BOX_XR_FRONTEND` (APK only) | host IK only | `BLACK_BOX_RUNTIME_ONLY` (prior) |
| 17 | xArm Quest | `HIGH_XR_ROS_CONTROL` | `BLACK_BOX_XR_FRONTEND` (Quest2ROS lineage) | direct xArm service | not launched (prior) |
| 18 | NVIDIA IsaacTeleop | `HIGH_XR_ROS_CONTROL` | `FULL_SOURCE` | `ROS_PUBLISHED` production message builders/gate executed; native XR source not run | synthetic dependency-boundary adaptation complete; native OpenXR still requires hardware stack |

## C. Invariant disposition matrix

Values: `P` preserved, `T` transformed, `RV` revalidated at the boundary, `G` gated,
`D` dropped, `U` unknown/not auditable, `—` not applicable.
A cell records the **audited production path**, not intent.

| # | Framework | I1 tracking | I2 source id | I3 source time | I4 session/gen | I5 invalidation/re-arm |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | Spes | `D` at the packet boundary (prior) | `P` side/context upstream | `D` | `D` (no generation in payload) | automatic re-anchor, no explicit re-arm (prior) |
| 2 | PickNik | `D` at the Odometry/TF publisher (prior) | `P` left/right | `D`/`T` wall-clock re-stamp | `U` | `U` runtime |
| 3 | Quest2ROS2 | `U` (frontend opaque); **absent host-side** | `P` side; **`D`** input `frame_id` | **`D`**, demonstrated on actual ROS transport | **`D`** — anchors and filter survive reconnect | **toggle, default-armed**; manual re-arm only |
| 4 | Docker_Teleop | **`P`+`G`** end-to-end — but the raw meaning is *controller connection*, not pose validity | `P` left/right; modality collapsed | **`D`** source time; **`RV`** locally on receipt age (4 layers) | **`D`** — no sequence/session id; client silently replaced | **`G`** strong: neutral-state substitution + zero twist + Servo halt |
| 5 | OpenVR UR5e | **`G`** on `bPoseIsValid`; `eTrackingResult` never read | `T` role-based re-resolution each tick; frame hardcoded | **`D`** (prediction 0, node-clock stamp) | `D` in bridge | **`G`** grip deadman + explicit re-anchor on re-engage |
| 6 | OpenArmX | **absent** | `P` side/head | **`P` at bridge → `D` at consumer** (the same field, two boundaries) | `D` | **`G`** on receipt-age freshness + grip deadman (bypassable by latched override) |
| 7 | VR-hand-bridge | **absent** (`left_valid` is a null check) | `P` left/right | **`D`** — never carried at all | `D` | absent |
| 8 | Nakama | `U` | `U` | `U` | `U` | `U` |
| 9 | xiaoxiaoxh | application `valid=true` is unconditional and unconsumed | positional left/right only | Unity `Time.time` carried but unconsumed | absent | control path not executed |
| 10 | Reachy | **`G`** `IsPoseValid` + stable-delay + provider readiness (prior) | `P` skeleton provider | `U` | source-visible WS queue/generation (prior) | provider-not-ready blocks payload (prior) |
| 11 | NU-MECH | **`G`** `IsTrackedDataValid` before UDP send; unrepresentable on the wire | laterality implicit in endpoint | `D`; message type has no header | absent | upstream gate only; downstream loss is silence |
| 12 | Legged | `XRHand.isTracked` computed then discarded | right-hand topic/frame only | every header has `stamp = 0` | absent | no downstream watchdog/re-arm |
| 13 | Homebrew | tracking mode computed then discarded; fallback substitutes poses | side/body part in topic/message layout | send time, not sample time | URL session only | reconnect without a payload generation |
| 14 | XRoboToolkit | head status `P`; controller status overwritten with constant `3` | laterality `T`; `deviceID` dropped | wire time `P`, not revalidated | absent | consumer not run |
| 15 | LTS0429 | absent on wire | token name `T` to topic/frame | `D`, receiver re-stamp | absent | absent; malformed token can terminate bridge |
| 16 | AgileX | absent in logcat representation | laterality only | absent | absent | host clutch only; frontend opaque |
| 17 | xArm Quest | `U` (Quest2ROS lineage) | `U` | `U` | `U` | `U` |
| 18 | NVIDIA | `VALID` `P`+`G`; `TRACKED` **`D`**, ROS builder gate runtime-confirmed | `P` handedness; modality incomplete | `D`/`T` in actionable path | `D` | invalid-pose hold/zero/rebaseline |

## D. Runtime and readiness

| # | Framework | Best evidence level reached | Downstream consequence reached | Simulator | Quest-ready | Priority |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | Spes | E2 ROS leg + prior hardware-to-callback | `PI_RECEIVED`, 30/30 through upstream publisher and 30/30 through adapter | no | yes; native publisher orchestration is the last Quest-free closure item | A |
| 2 | PickNik | E1; transport-only replay reached ROS-TCP 3600/3600 | boundary-limited backend relay only | no | blocked by Unity licence entitlement | A |
| 3 | Quest2ROS2 | **E2 with actual ROS 2 transport** | pinned `RightArmController`; `PI_RECEIVED` 619/619 | in-repo source simulator | external app required for Quest semantics | **S** |
| 4 | Docker_Teleop | **E2 upstream-faithful replay** | MoveIt Servo + simulated joint effect | **Ignition Gazebo** | app build readiness tracked separately | **S** |
| 5 | OpenVR UR5e | **E2 upstream-faithful replay** | MoveIt Servo + simulated joint effect | **Gazebo Sim** | optional, heavy ALVR/SteamVR path | A |
| 6 | OpenArmX | **E2 synthetic UDP runtime** | actual ROS `PoseStamped`; closed driver blocks consumer | no | frontend opaque/PICO | B |
| 7 | VR-hand-bridge | **E2 boundary-limited replay** | `ROS_PUBLISHED`, no control consumer | no | low control value | C |
| 8 | Nakama | E0 | none | no | no | DROP |
| 9 | xiaoxiaoxh | E2 wire-schema only; E1 control path | no control consequence | no | `HARDWARE_ONLY_UNSAFE` | B |
| 10 | Reachy | E1 | none | no | blocked | B |
| 11 | NU-MECH | E2 boundary-limited UDP runtime | `ROS_PUBLISHED`; no robot consumer | no | Quest-only gate question | C (positive control) |
| 12 | Legged | E1 partial | none | no | no | C (positive control) |
| 13 | Homebrew | E1 | none | no | no | C (positive control) |
| 14 | XRoboToolkit | E2 with inert vendor-SDK substitute | `ROS_PUBLISHED`; external consumer not run | inert | frontend opaque | C |
| 15 | LTS0429 | E2 synthetic UDP runtime | `ROS_PUBLISHED`; frontend opaque | inert | APK required | DROP |
| 16 | AgileX | E2 representation runtime | no ROS/DDS/control consequence | inert | APK/ADB required | DROP |
| 17 | xArm Quest | E1 | none | no | no | DROP (lineage) |
| 18 | NVIDIA | E2 production ROS builder/gate | real rosidl message construction; no DDS/native XR | inert | native OpenXR required | B (positive control) |
