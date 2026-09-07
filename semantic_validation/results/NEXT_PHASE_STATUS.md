# Next-Phase Status — Quest-less Multi-Framework Preparation V3

## Decision

**`GO — NOT STRONG GO` 유지.** This session created no E5/E6 evidence. The only executed
new check was a dependency-light E1 adapter self-test; all source audits are E1. No Quest,
physical robot, actuator, driver, network configuration, or upstream source modification was
used.

## Spes

- ROS adapter: `harness/spes_ros_callback_adapter.py` publishes only after the accepted pinned
  `Teleop` callback and uses a side-band JSONL mapping; it does not modify production payloads.
- Synthetic callback → ROS: **not executed**. Desktop ROS publisher needs the existing Docker
  environment, whose daemon socket is inaccessible to the current execution identity.
- Pi receive: **not executed for Spes**. The existing Pi `semantic_robot_sink` is an observation
  endpoint only; its earlier generic DDS smoke is not a Spes result.
- Correlation: adapter records `run_id`, local event ID, server update index, callback/publish
  monotonic time and ROS header stamp. The standard `PoseStamped` has no injected ID.
- Evidence: adapter self-test `PASS` at
  `logs/next_phase_20260907T000000Z/spes_ros_adapter_selftest.jsonl`; this proves adapter schema
  discipline only and creates no research E-level upgrade: it did not invoke the actual callback,
  WSS, ROS, DDS, Pi reception, XR, or actionability.
- Regression: unchanged robot-free localhost Spes WSS/server suite passed 10/10 at
  `logs/next_phase_20260907T000000Z/spes_existing_synthetic_regression/`. This is existing
  `BOUNDARY_LIMITED_REPLAY` coverage, not a ROS/Pi or XR result.
- Quest readiness: existing Quest orchestration plus new T0/T1/observable documentation are
  present; actual ROS/Pi preflight remains blocked.

## PickNik

- Docker ROS2 / `rclpy` / message modules: image runtime **not re-verified** because `docker info`
  returns socket permission denial. The compose configuration itself validates.
- `ros_tcp_endpoint`: **not verified present**; no container can be inspected. Do not infer it
  from `rosbridge-suite` or source files.
- Pi observer: generic Pi `semantic_robot_sink` and PickNik-specific observer preparation exist;
  no PickNik Unity/ROS message has reached the Pi in this session.
- Remaining blocker: Docker daemon access for the desktop container; then image dependencies and
  `ros_tcp_endpoint` must be checked in-container. Unity 6000.1.6f1-compatible editor, Android
  module, and an authorized Quest are still unavailable.
- Quest readiness: source/dataflow plus instrumentation remain ready; backend is not yet ready.

## NU-MECH

- Repo/revision: `NU-MECH-ENG-495/vr-hand-tracking@8b685f91727bba98cd28322f296fef30c3173309`
  (`main`, independently resolved and shallow-cloned).
- XR source: Unity Oculus Interaction `IHand.WhenHandUpdated`; direct scene/prefab linkage needs
  Unity-editor verification.
- Tracking semantics: `IsTrackedDataValid` gates before UDP send; it is not serialized.
- Transport / ROS boundary: UDP formatted angle text → C++ regex parser →
  `hand_joint_angles` `Float32MultiArray`.
- Native consumer: included Qt visualizer only; no robot control consumer found.
- Inclusion/readiness: **Group B / POSITIVE_CONTROL_ONLY**, E1 source map, not Quest-ready.

## xiaoxiaoxh

- Repo/revision: `xiaoxiaoxh/vr-teleoperation@1d29f9f35f77ec5024f6837a0a3d790cc37b7bd1`
  (`main`, independently resolved and shallow-cloned).
- XR source: Unity Oculus controller `Transform` and `OVRInput`; `OVRSkeleton` is not used in
  the audited send path.
- Tracking semantics: no native validity/confidence/tracking gate is consumed; application
  `message.valid=true` is not native tracking evidence.
- Transport / ROS boundary: Unity JSON HTTP `/unity` enters `TeleopServer`; its rclpy publisher
  is parallel infrastructure rather than a proven serial Unity-to-ROS path.
- Native consumer: source contains direct Flexiv robot-server command path. It was not launched.
- Inclusion/readiness: **Group A source-only high-risk downstream**, E1 only; no synthetic run is
  authorized until an inert endpoint replacement is source-audited.

## XRoboToolkit

- Repo/revision: `XR-Robotics/XRoboToolkit-Teleop-ROS@a516bb28061030a0fb5a73367241bcaa883eaf02`
  (`main`, independently resolved and shallow-cloned).
- XR source: external PicoXR Robot SDK/service; native semantic source is not auditable here.
- Tracking semantics: wire exposes timestamp/status, but publisher overwrites present controller
  status with `3`; audited ARX example consumes pose/triggers, not status/freshness.
- Transport / ROS boundary: SDK device-state JSON → `xr_msgs/Custom` → `/xr_pose`.
- Native consumer: ARX example emits `PosCmd`, receiving controller unavailable.
- Inclusion/readiness: **Group C / auxiliary opaque native source**, E1 wire/downstream only;
  excluded from independent native confirmation count.

## Legged

Recheck found no connected original robot-control consumer beyond the already mapped hand/head
telemetry and ROS-TCP registration. Keep **Group B / POSITIVE_CONTROL_ONLY /
CONTROL_PATH_UNCONFIRMED**. `XRHand.isTracked` is source-side gate evidence only.

## Population

| Framework | Group | Family | Source auditable | Control path | Synthetic | Pi | Quest-ready | Evidence |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Spes | A | WebXR/WSS | yes | callback; optional ROS adapter | adapter self-test only | not Spes-tested | partial; ROS preflight blocked | E1 source map + non-evidence selftest; prior bounded hardware callback |
| PickNik | A | Unity/ROS-TCP | yes | external MoveIt Pro | source/analyzer only | infrastructure ready, target unrun | blocked | E1 |
| xiaoxiaoxh | A source-only | Unity Meta/HTTP + ROS2 | yes | direct robot server source-visible | not authorized | unrun | blocked | E1 |
| NU-MECH | B | Unity Meta/UDP/ROS2 | yes | visualizer only | not run | unrun | blocked | E1 |
| Legged | B | Unity/OpenXR ROS-TCP | partial telemetry | unconfirmed | not run | unrun | blocked | E1 partial |
| XRoboToolkit | C | proprietary PicoXR/ROS | wire only | ARX consumer external | not run | unrun | blocked | E1 wire only |
| LTS0429 | C | opaque APK/UDP/ROS2 | no native source | unrun | not run | unrun | blocked | E0/E1 host wire |
| AgileX | C | opaque APK/ADB + ROS2 | no native source | host IK only | not run | unrun | blocked | E0/E1 host path |

### Principal comparison population

Spes and PickNik remain principal ready-for-comparison targets. xiaoxiaoxh is source-auditable
and has a control-producing path, but remains source-only until its direct robot endpoints are
replaced by a verified inert stub; it contributes no runtime confirmation.

### Positive-control population

NU-MECH (source gate, no original control outcome) and Legged (hand telemetry gate, control path
unconfirmed).

### Auxiliary/opaque population

XRoboToolkit, LTS0429, and AgileX. They are not independent native XR confirmations.

### Architecture-family coverage

The source inventory now includes WebXR/WSS, Unity/ROS-TCP, Unity Meta/UDP/ROS2, Unity
Meta/HTTP robot-server, and PicoXR proprietary-service/custom ROS. This is coverage of source
architectures, not runtime/hardware confirmation count. Shared Unity/vendor SDK usage is not
counted as independent lineage.

### Remaining environment blockers

1. Current execution identity lacks effective Docker group access; `/var/run/docker.sock` returns
   permission denied. No socket chmod/group/system change was attempted.
2. Therefore the Desktop Humble image, `rclpy` availability, `ros_tcp_endpoint`, and desktop DDS
   publisher cannot be rechecked this session.
3. A compatible Unity editor/Android module is unavailable for PickNik/Unity targets.

### Remaining hardware blockers

No authorized ADB-connected Quest is present. No actual tracking transition, source raw trace,
Spes ROS publish, DDS transfer, or Pi receive was generated by this session.

### Recommended actual Quest session order

1. Restore desktop Docker access and verify only the isolated ROS image/observer dependencies.
2. Run Spes synthetic callback → desktop ROS → Pi sink, classify exactly as E2/
   `BOUNDARY_LIMITED_REPLAY` and `PI_RECEIVED`.
3. Run PickNik T0 then five valid T1 controller-loss/recovery trials to the dummy Pi observer;
   no robot or driver.
4. Only after a source-audited inert stub exists, consider xiaoxiaoxh runtime preparation.

### Current GO / STRONG GO recommendation

**`GO — NOT STRONG GO` remains.** No second independent actual XR transition plus downstream
software consequence was observed, and Pi reception must never be rewritten as actionability.
