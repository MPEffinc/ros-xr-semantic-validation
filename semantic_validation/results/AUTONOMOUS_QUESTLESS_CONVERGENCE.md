# Autonomous Quest-less Convergence — 2026-09-07

## Decision

**`GO — NOT STRONG GO` 유지.** 이 phase는 Quest를 연결하지 않았고, actual physical robot,
driver, actuator를 한 번도 실행하지 않았다. 따라서 새 E5/E6은 없으며, E2 synthetic/replay나
E1 source audit를 native XR 결과로 승격하지 않는다.

## Infrastructure

| Item | Verified state | Evidence / limit |
| --- | --- | --- |
| Docker | daemon active, socket `root:docker 0660`; `cclab` is in `docker` group | current process needs `sg docker` (or a fresh login); `docker info`, `docker ps`, compose config pass |
| Desktop ROS | `ros-xr-humble:local`, host network, `ROS_DOMAIN_ID=0`, `rmw_fastrtps_cpp` | in-container `ros2`, `rclpy`, `geometry_msgs`, `nav_msgs`, `tf2_msgs` import pass |
| Pi | `rosxr`, native ROS 2 and `semantic_robot_sink`, `eth0=10.10.10.2` | sink is observation-only and has no driver |
| Dedicated link / DDS | desktop `10.10.10.1` to Pi `10.10.10.2` | Docker publisher→Pi listener and Pi publisher→Docker listener both received test strings |
| PickNik endpoint | official ROS-TCP Endpoint `main-ros2@54c1a64b6d5ef6ffa0a0431570bb74329b15b` | isolated build and local listener start only; no Unity client message |

## New Spes runtime evidence

Final automated canonical run: `logs/questless_all_20260907T043540Z/` and
`logs/spes_questless_all_20260907T043540Z/spes_runtime/`. The earlier direct run at
`logs/spes_ros_pi_20260907T041600Z/` independently produced the same three-event result.

```text
synthetic WSS input after browser-native gate
 -> pinned Spes WSS server / accepted callback
 -> side-band post-callback ROS adapter
 -> /robot_target_pose -> DDS -> physical Pi semantic_robot_sink
```

Three accepted events matched the Pi header stamps and pose values exactly.  Classification is
`E2 / BOUNDARY_LIMITED_REPLAY`; consequence is **only `PI_RECEIVED`**.  The first failed
root-owned attempt (`...041500Z`) is retained locally but excluded from the canonical result.

## Principal frameworks

| Framework | Revision / family | XR source and semantic decision | Transport / ROS boundary / downstream | Quest-less result and readiness |
| --- | --- | --- | --- | --- |
| Spes | pinned `c5d808…`; WebXR/WSS | browser-native decision precedes test injection; accepted callback is observed without modifying payload | WSS → callback → research `PoseStamped` adapter → DDS → Pi | E2 Pi observation PASS; `QUEST_READY` orchestration for future native run |
| PickNik | `bbaef0762fdb0b429b8ea12a4ca65040748b41dd`; Unity/OpenXR + ROS-TCP | `isTracked`/`trackingState` are audited side-band raw inputs, not equated to other APIs | ROS-TCP → `/left_controller_odom`, `/right_controller_odom`, `/tf` → Pi observer; external MoveIt Pro unrun | backend `RUNTIME_READY`, Unity/APK `BLOCKED_ENV`, Quest procedure ready |
| xiaoxiaoxh/vr-teleoperation | `1d29f9f35f77ec5024f6837a0a3d790cc37b7bd1`; Unity Meta/HTTP + ROS2 | no source-visible native tracking gate in audited send path | direct Flexiv server boundary exists | Group A source-only; no safe stub yet, so runtime deliberately not launched |
| HRI-EU/reachy-vr-quest | `242120ee9e356e4a4f2117ee56c8b340c9b7ec64`; Unity Meta Movement/direct WebSocket | `IsPoseValid` + stable-delay, then skeleton readiness gates payload build | daemon `/api/move/ws/set_target`, no ROS | Group A E1 independent direct-robot family; inert WebSocket stub is exact remaining prerequisite |

## Positive controls, auxiliary, and exclusions

| Framework | Group | Family | Source | Control path | Runtime | Pi | O4 | Quest-ready | Evidence |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| NU-MECH vr-hand-tracking | B | Unity Meta/UDP/ROS2 | validity gate visible | visualizer only | source only | no | no | source plan | E1 |
| legged unity_ros_teleoperation | B | Unity/OpenXR ROS-TCP | `XRHand.isTracked` gate | original consumer unconfirmed | source only | no | no | source plan | E1 partial |
| homebrew vr-teleop | B | Unity XR/rosbridge WebSocket | controller/hand fallback gate visible | no included robot consumer | source only | no | no | Unity 2022 required | E1 |
| XRoboToolkit | C | vendor service/custom ROS | opaque native source | ARX receiver external | source/wire only | no | no | no | E0/E1 |
| LTS0429 | C | opaque APK/UDP/ROS2 | opaque | unconfirmed | no | no | no | no | E0/E1 |
| AgileX | C | opaque APK/ADB/ROS2 | opaque | host IK only | no | no | no | no | E0/E1 |
| RuiyuWANG xarm_quest_teleop | D | Quest2ROS/ROS1/xArm | shared Quest2ROS lineage | direct xArm service | not launched | no | no | no | excluded, E1 map |

## Candidate search

Ten additional public identities were independently resolved to immutable SHA during screening:
`RuiyuWANG/xarm_quest_teleop`, `nakama-lab/VR_Teleop_Interface`,
`homebrewroboticsclub/vr-teleop`, `h2r/GHOST`, `openarmx/openarmx_teleop_vr`,
`paulonhantumbojr/sawyer_vr_teleop`, `HRI-EU/reachy-vr-quest`, `elpis-lab/UR10_Teleop`,
`dongridong/Meta_for_teleoperation`, and `Quest2ROS/quest2ros`.  Deep-audited new candidates are
Homebrew, xArm and Reachy; their pinned source maps are under `frameworks/`.  This prevents fork
or shared-Quest2ROS lineage from being counted as independent confirmation.

## Architecture coverage and semantic contract

Source population covers WebXR/WSS, Unity/OpenXR ROS-TCP, Unity Meta HTTP/ROS2, Unity XR
rosbridge/WebSocket, Quest2ROS/ROS1, and Unity Meta direct WebSocket.  Runtime confirmation is
far narrower: only WebXR WSS post-gate replay to ROS/DDS/Pi and ROS-TCP endpoint listen.

| Invariant | Spes | PickNik | xiaoxiaoxh | Reachy | Interpretation |
| --- | --- | --- | --- | --- | --- |
| I1 raw tracking/source state | browser-owned before injection | side-band raw tracked state planned | no consumed gate found | `IsPoseValid` + stable delay | APIs are non-equivalent raw semantics |
| I2 source identity | WebSocket client/source context upstream | Unity device identity side-band | Quest2ROS input identity upstream | skeleton provider readiness | must preserve/transform/revalidate, not necessarily serialize raw fields |
| I3 source-time/freshness | callback monotonic + ROS header side-band | side-band/ROS correlation plan | ROS stamps synchronized | send cadence but no source stamp field map yet | Pi receive time alone is insufficient |
| I4 session/generation | server update index side-band | focus/pause/XR state logger | not validated | WebSocket queue/generation source-visible | require native observation in future runs |
| I5 invalidation/recovery | synthetic post-gate cannot test it | future T1 capture | unrun | provider not-ready prevents payload | gate, revalidate, or explicit degrade are all legitimate |

## Related work and novelty boundary

See [RELATED_WORK_UPDATE_20260907.md](RELATED_WORK_UPDATE_20260907.md).  The update covers
RoboFuzz, ROS runtime verification/field testing, TeleXR, XRoboToolkit, and Quest2ROS2 with exact
identities/links.  The defensible novelty remains a cross-architecture evidence method, not a
claim that any framework is unsafe or generally secure.

## Automation and exact next Quest session

`semantic_validation/run_all_questless.sh` performs independent Docker/Pi preflight, ROS-TCP
endpoint check, Spes observer-only run/collection, and cleanup while recording per-component
status.  It does not attach ADB/Quest or start a driver.  Spes lifecycle commands are in
`frameworks/spes/spes_{preflight,start_all,status,collect,stop_all}.sh`.

When an authorized Quest is deliberately introduced, keep every framework robot-free:

1. Preflight Docker/Pi/DDS and start only dummy observers/inert stubs.
2. T0 baseline for 10 seconds; confirm raw native state and all side-band streams.
3. T1: induce a 3–5 second tracking degradation, recover for 5–10 seconds, and repeat until five
   **raw native** valid transitions occur.
4. If physical occlusion yields no raw transition, record `NO_TRANSITION_OBSERVED`; do not infer a
   tracking-loss outcome.
5. Collect/analyze/stop; call Pi output `PI_RECEIVED` only.  T4/T5 are used only where the
   framework's source semantics make them applicable.

## Evidence gained / still missing / recommendation

Gained: standard Docker access, bidirectional DDS baseline, actual Spes callback→ROS→Pi E2
correlation, isolated PickNik ROS dependency/endpoint readiness, and two new deep source audits
with an independent direct-WebSocket architecture.  Still missing: actual raw Quest transitions,
Unity build/APK for PickNik, native-source-to-ROS runtime for a second principal stack, and an
inert native-consumer run (O4).  Recommendation: proceed to the explicitly robot-free Quest
session after a compatible Unity editor is installed and a Reachy/xiaoxiaoxh inert boundary is
audited.  **Do not promote to STRONG GO before that evidence exists.**
