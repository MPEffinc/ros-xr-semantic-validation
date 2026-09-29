# Quest-less Completion Matrix

The single high-level status table for the Quest-free phase. Every framework identity in the
population carries exactly one final questless status; none is left unexamined.

Decision on entry and on exit: **`GO — NOT STRONG GO`**. No Quest hardware, physical robot,
driver, motor, actuator or CAN bus was used in this phase. Every new runtime result is at most
`E2 SYNTHETIC_RUNTIME`.

Status vocabulary: `QUESTLESS_RUNTIME_COMPLETE`, `QUESTLESS_PARTIAL_COMPLETE`,
`SOURCE_ONLY_COMPLETE`, `BLOCKED_EXTERNAL_DEPENDENCY`, `OPAQUE_FRONTEND`,
`HARDWARE_ONLY_UNSAFE`, `NON_INDEPENDENT`, `SOURCE_PATH_UNCONFIRMED`.

The matrix is split into two tables over the same 18 keys because the required column set is too
wide to read as one.

## Table A — identity, execution reach, evidence

| # | Framework | Pinned revision | Architecture family | Role / priority | Source audit | Build | Synthetic / fake runtime | Native ROS / control boundary | Simulator / inert consequence | Pi reached | Strongest evidence |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | **Docker_Teleop** | `64cbdde` | Unity Meta → newline-JSON TCP → ROS 2 → MoveIt Servo | `PRINCIPAL_WHITEBOX` / S | full | yes (x86_64 rebase) | yes, D1–D5 | yes — MoveIt Servo + `joint_group_velocity_controller` | **yes** — D1 `0.134070 m` Hand-E, D2/D3 halt `~1e-10 rad/s` | no (deliberate) | `E2` / `UPSTREAM_FAITHFUL_REPLAY` |
| 2 | **OpenVR UR5e** | `170dad5` | ALVR/SteamVR/OpenVR → rclpy → MoveIt Servo → Gazebo | `PRINCIPAL_WHITEBOX` / A | full | yes (Jazzy) | yes, V1–V4 + W0–W3 | yes — MoveIt Servo (POSE mode) | **yes** — W1 `1.536350 rad`, W2 `1.536454 rad`, W3 at baseline | no (distro mismatch) | `E2` / `UPSTREAM_FAITHFUL_REPLAY` |
| 3 | **Quest2ROS2** | `07aaf65` | black-box Quest APK → TCP bridge → ROS 2 | `PRINCIPAL_BLACKBOX` / S | host side full; frontend external | yes | yes — age sweep, `SimulationInput`, reconnect | yes — pinned `RightArmController` | no (CLIK controller absent from repo) | **yes** — 619/619 | `E2`, actual DDS |
| 4 | **Spes** | `c5d8081` | WebXR → WSS → server callback → **upstream** `teleop/ros2` | motivating case + native optional ROS / A | full | yes | yes | yes — pinned upstream ROS 2 module | no robot consumer | **yes** — 30/30 native publisher + 30/30 adapter; final workflow 10/10 | actual Quest 3 hardware → server callback; `E2` for the ROS leg |
| 5 | **NVIDIA IsaacTeleop** | `9fba23c` (+ `197f5cd`) | OpenXR/DeviceIO → retargeting → rclpy | `POSITIVE_CONTROL` / B | full | yes | yes, 15/15 | yes — production validity gate executed | inert | no | `E2 SYNTHETIC_RUNTIME` |
| 6 | **OpenArmX** | `a3da741` | PICO APK → UDP ASCII → C++ bridge → ROS 2 | `PRINCIPAL_BLACKBOX` / B | bridge full; IK closed | bridge only | yes — 3 timestamp cases | bridge only | no | no | `E2 SYNTHETIC_RUNTIME` |
| 7 | **VR-hand-bridge** | `a5da3e0` | Godot OpenXR → WebSocket JSON → rclpy | `AUXILIARY_WIRE` / C | full | yes | yes — 207 `PoseStamped` | no control consumer exists | n/a | no | `E2 SYNTHETIC_RUNTIME` |
| 8 | **LTS0429** | `65ce76c` | opaque APK → UDP text → rclcpp | `AUXILIARY_WIRE` / DROP | host half only | yes | yes, 8/8 | host parser only | inert | no | `E2 SYNTHETIC_RUNTIME` |
| 9 | **XRoboToolkit** | `a516bb2` | PicoXR Robotics Service → `xr_msgs/Custom` → rclcpp | `AUXILIARY_WIRE` / C | open half only | yes (inert SDK stub) | yes, 7/7 | publisher only; ARX consumer external | inert | no | `E2 SYNTHETIC_RUNTIME` + captured blocker |
| 10 | **AgileX QuestArmTeleop** | `145b803` | opaque APK → ADB logcat text → rclpy → external CAN driver | `AUXILIARY_WIRE` / DROP | host half only | yes | yes, 6/6 (representation layer) | representation layer only | inert | no | `E2 SYNTHETIC_RUNTIME` |
| 11 | **NU-MECH** | `8b685f9` | Unity Oculus Interaction → UDP text → rclcpp | `POSITIVE_CONTROL` / C | full | yes | yes, 5/5 | visualizer only | inert | no | `E2 SYNTHETIC_RUNTIME` |
| 12 | **PickNik** | `bbaef07` | Unity/OpenXR → ROS-TCP → Odometry/TF | `PRINCIPAL_WHITEBOX` / A | full | backend yes; Unity blocked | **transport backend only**, 3600/3600 | not reached — injection is downstream of all PickNik code | n/a | no (deliberate) | `E1 SOURCE_DATAFLOW_CONFIRMED` |
| 13 | **Reachy VR Quest** | `242120e` | Unity Meta Movement SDK → WebSocket → Reachy daemon | `POSITIVE_CONTROL` + `ADJACENT_NON_ROS` / B | full | inert endpoint yes; Unity blocked | endpoint self-test only | not reached | inert endpoint ready | no | `E1 SOURCE_DATAFLOW_CONFIRMED` |
| 14 | **Legged** | `0edde94` | Unity 6000.2 OpenXR + XR Hands → ROS-TCP | `POSITIVE_CONTROL` / C | full | no | no | no | no | no | `E1 SOURCE_DATAFLOW_CONFIRMED` |
| 15 | **Homebrew vr-teleop** | `2952d27` | Unity 2022.3 OpenXR → rosbridge JSON/WebSocket | `POSITIVE_CONTROL` / C | full | no | no | no | no | no | `E1 SOURCE_DATAFLOW_CONFIRMED` |
| 16 | **xiaoxiaoxh** | `1d29f9f` | Unity Meta → JSON HTTP `/unity` → direct Flexiv | `ADJACENT_NON_ROS` / B | full | schema only | wire schema 5/5 | control path not attempted | none | no | `E2` schema; `E1` control path |
| 17 | **xArm Quest Teleop** | `8220579` | *none of its own* — consumes the Quest2ROS frontend | `EXCLUDED` / DROP | lineage only | n/a | n/a | n/a | n/a | n/a | `E1` lineage determination |
| 18 | **Nakama** | `aebf639` | claimed Unity + Humble + Franka; **no code at the pinned ref** | `EXCLUDED` / DROP | none possible | n/a | n/a | n/a | n/a | n/a | `E0 DISCOVERED` |

## Table B — semantics, remaining work, status

| # | Framework | Semantic axes and disposition | Quest-less conclusion | Remaining non-Quest work | Quest-only question | Final questless status | Checkpoint |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | **Docker_Teleop** | I1 `PRESERVED` + `REVALIDATED` server-side, but keyed on controller *connection*; I3 `DROPPED`; I4 partial | Production path and Gazebo consequence complete | none | Does optical occlusion change `OVRInput.GetConnectedControllers()`? | `QUESTLESS_RUNTIME_COMPLETE` | `f1cfa56` |
| 2 | **OpenVR UR5e** | I1 `bPoseIsValid` `GATED`, `eTrackingResult` `DROPPED`; I3 re-stamped; I5 grip re-anchor | Production path and Gazebo consequence complete | none | Does actual ALVR/OpenVR expose valid `Running_OutOfRange`? | `QUESTLESS_RUNTIME_COMPLETE` | `c43769a` |
| 3 | **Quest2ROS2** | I1 absent host-side; I2 frame replaced; I3 stale/future accepted; I4 state survives reconnect | Host production/DDS/Pi/session runtime complete | no safely attributable consumer beyond missing CLIK package | Actual app tracking and reconnect semantics | `QUESTLESS_RUNTIME_COMPLETE` | `de658b8` |
| 4 | **Spes** | I1 omitted at packet; I2 ROS frame fixed; I3 re-stamped | Quest hardware→callback and separate native ROS→Pi legs complete | none | Join both legs in one continuous run | `QUESTLESS_RUNTIME_COMPLETE` | `a77f03c` |
| 5 | **NVIDIA IsaacTeleop** | I1 validity serialised/gated but tracked detail dropped; I3 re-stamped | Production ROS builder/gate runtime complete | none | Native valid-but-inferred behavior | `QUESTLESS_RUNTIME_COMPLETE` | `a06525e` |
| 6 | **OpenArmX** | I3 preserved at bridge then ignored by closed consumer | Open UDP bridge complete; native consumer unavailable | none safely reachable | PICO frontend semantics | `QUESTLESS_PARTIAL_COMPLETE` | `d341343` |
| 7 | **VR-hand-bridge** | I1/I3 gate absent on exercised bridge; validity never leaves sender | Complete through actual ROS publication; no control consumer exists | none | none of control relevance | `QUESTLESS_RUNTIME_COMPLETE` | `1696a7d` |
| 8 | **LTS0429** | I1 absent on wire; I3 dropped/re-stamped | Open host half runtime complete | none | opaque frontend | `QUESTLESS_PARTIAL_COMPLETE` | `a06525e` |
| 9 | **XRoboToolkit** | controller status overwritten; I3 transported without enforcement | Open publisher half complete with inert SDK substitute | none reachable | opaque PicoXR service semantics | `QUESTLESS_PARTIAL_COMPLETE` | `a06525e` |
| 10 | **AgileX** | I1/I3/I4 absent from logcat representation | Host representation runtime complete | none | opaque frontend | `QUESTLESS_PARTIAL_COMPLETE` | `a06525e` |
| 11 | **NU-MECH** | upstream gate; validity unrepresentable on downstream wire | UDP→ROS half runtime complete | none | real Unity gate behavior | `QUESTLESS_PARTIAL_COMPLETE` | `a06525e` |
| 12 | **PickNik** | I1 dropped at Odometry/TF; I3 re-stamped | Source audit and backend-only replay complete | Unity licence entitlement then prepared APK build | Native tracking loss→PickNik publisher behavior | `BLOCKED_EXTERNAL_DEPENDENCY` | `1696a7d` |
| 13 | **Reachy VR Quest** | defined validity/stability gate has no production call site | Inert endpoint ready; Unity side externally blocked | Unity `6000.3.9f1`, entitlement, package restore/artifact | Actual provider-loss behavior | `BLOCKED_EXTERNAL_DEPENDENCY` | `1696a7d` |
| 14 | **Legged** | I1 computed then discarded; headers stamp zero | Source-only closure is sufficient | none worth doing | real hand-loss output | `SOURCE_ONLY_COMPLETE` | `a06525e` |
| 15 | **Homebrew** | tracking mode computed then omitted; URL-only session | Source-only closure is sufficient | none worth doing | real fallback/loss output | `SOURCE_ONLY_COMPLETE` | `a06525e` |
| 16 | **xiaoxiaoxh** | unconditional `valid=true`; app-local time unconsumed | Wire schema closed; direct Flexiv path intentionally prohibited | none safely reachable | no hardware trial scheduled | `HARDWARE_ONLY_UNSAFE` | `a06525e` |
| 17 | **xArm Quest Teleop** | shares Quest2ROS frontend/wire | Lineage determination complete | none | none independently countable | `NON_INDEPENDENT` | `a06525e` |
| 18 | **Nakama** | no code at pinned identity | Identity cannot support audit | authoritative implementation identity | none until identity resolves | `SOURCE_PATH_UNCONFIRMED` | `a06525e` |

## Counts at the end of the Quest-free phase

| Measure | Count | Note |
| --- | ---: | --- |
| Screened identities with verified repository + pinned revision | **18** | 19 checkouts; NVIDIA contributes two repositories |
| Distinguishable architecture families with inspected source | **12** | source breadth, **not** runtime generality |
| Frameworks with **actual runtime evidence** | **11** | up from 2 at the start of the phase |
| Frameworks reaching a **native ROS/control boundary** at runtime | **6** | Docker_Teleop, OpenVR UR5e, Quest2ROS2, Spes, NVIDIA, OpenArmX (bridge) |
| Frameworks with a **simulator or inert consequence** measured | **2** | Docker_Teleop and OpenVR UR5e — both Gazebo, both robot-free |
| Frameworks that reached the **physical Pi** | **2** | Quest2ROS2 (619/619), Spes (30/30 twice) — `PI_RECEIVED` only |
| Positive controls retained | **6** | NVIDIA (now runtime-confirmed), Reachy, NU-MECH, Legged, Homebrew, plus Docker_Teleop's neutral-state recovery |
| Identities left unexamined | **0** | — |

`E5`/`E6` evidence produced in this phase: **none**, by design. No Quest was connected.

## Repeated semantic patterns across the population

1. **Every framework that gates, gates on a proxy.** Docker_Teleop keys on controller
   *connection*; OpenVR UR5e reads the weaker of two available OpenVR flags; NVIDIA declares
   `head_is_tracked` and never reads it. *Valid-but-inferred* is indistinguishable from
   *valid-and-actively-tracked* everywhere in this population.
2. **Two distinct I1 failure shapes at serialization.** *Unrepresentable* — the wire format has no
   field for validity (NU-MECH, AgileX; NU-MECH additionally corrupts a validity token into a
   joint angle). *Computed then discarded* — the bit is derived and dropped (Legged, Homebrew,
   xiaoxiaoxh).
3. **I3 splits three ways:** dropped and re-stamped with the receiver clock (LTS0429, NU-MECH,
   NVIDIA's EE header, PickNik, Quest2ROS2, OpenVR UR5e, Spes); never present (Legged — every
   header ships `stamp = 0`); or carried verbatim and never enforced (XRoboToolkit, OpenArmX's
   bridge half).
4. **I4 is absent almost everywhere.** Only Homebrew has a session concept, and it lives in a URL
   rather than the payload. Quest2ROS2 demonstrates the consequence at runtime: anchors, filter
   state and the arming latch all survive a transport reconnect.
5. **Opacity is not unexaminability.** Three of the four repositories previously written off as
   opaque (LTS0429, AgileX, XRoboToolkit) yielded real runtime evidence once the examination was
   aimed at the open half, with the frontend boundary left explicitly unclaimed.

## Discipline reminders binding on every row above

- `PI_RECEIVED` is never actionability. The Pi sink is an observation endpoint with
  `ACCEPTED_NO_SEMANTIC_GATING`.
- Source-architecture breadth (12 families) is not runtime generality.
- Synthetic and replay evidence is never native Quest behaviour.
- A black-box XR frontend is not a source-visible tracking semantic.
- Shared lineage is not independent implementation (xArm).
- No framework is described as `vulnerable`, `unsafe`, `secure` or `fail-safe`.
