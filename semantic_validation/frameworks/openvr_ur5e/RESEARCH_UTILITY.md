# FRAMEWORK: OpenVR/SteamVR UR5e (Jazzy)

## Identity

- Repository: `https://github.com/mrutyunjaykalyani/teleoperation-of-a-UR5e-robot-in-Gazebo-using-Meta-Quest-3-via-ROS2-bridge-jazzy-.git`
- Revision: `170dad582d624f536359a3192a7f829669c2b031` (2026-04-09), worktree clean, **single-commit repository**
- Local checkout: `semantic_validation/targets/openvr_ur5e_jazzy`
- License: LICENSE file present
- ROS distro: **Jazzy** (README badges; `ur5_description/launch/gazebo.launch.py:36-37` branches on `ROS_DISTRO`; `log.txt:167` shows `/opt/ros/jazzy`)

## Architecture

```text
Meta Quest 3 -> ALVR/SteamVR -> OpenVR runtime
  -> quest_bridge/quest_teleop.py (pyopenvr)
     getDeviceToAbsoluteTrackingPose(TrackingUniverseRawAndUncalibrated, 0, poses)
  -> /servo_node/pose_target_cmds  [geometry_msgs/PoseStamped, frame_id "base_link"]
  -> MoveIt Servo (pose_tracking mode, ur_servo.yaml)
  -> /ur5_arm_controller/joint_trajectory
  -> gz_ros2_control (GazeboSimSystem) -> Gazebo Sim (UR5e)
```

## System Relevance

- Classification: **`HIGH_XR_ROS_CONTROL`**
- Why: the XR controller pose is the direct Cartesian command consumed by MoveIt Servo's pose-tracking mode, which drives a simulated UR5e. Complete in-source control path.

## Semantic Observability

| Axis | Finding | Evidence |
| --- | --- | --- |
| I1 tracking validity | **`bPoseIsValid` IS a gate** — the entire publish path is inside it. **But `eTrackingResult` is never read**, so `Running_OutOfRange` / `Calibrating_InProgress` (states in which OpenVR may still report `bPoseIsValid=true`) are not distinguished. `bDeviceIsConnected` also never read. | gate at `quest_teleop.py:49`; absence confirmed repo-wide |
| I2 source identity | Device re-resolved **every tick** by `getTrackedDeviceClass == TrackedDeviceClass_Controller` and `getControllerRoleForTrackedDeviceIndex == TrackedControllerRole_RightHand`. No serial-number/identity continuity check. Left hand unused. Output `frame_id` hardcoded `"base_link"`. | `quest_teleop.py:45-49`, `:82` |
| I3 source time | **DROPPED.** `fPredictedSecondsToPhotonsFromNow` is hardcoded `0`; no OpenVR-side time is captured; header stamp is `self.get_clock().now()`. No age check anywhere in the bridge. | `quest_teleop.py:43`, `:81` |
| I4 session/generation | **Absent** in the bridge. `openvr.init()` is called once with no runtime re-check; SteamVR exit during operation would raise inside the timer callback rather than degrade gracefully. Per-tick device re-resolution does, however, make index reassignment across reconnect harmless. | `quest_teleop.py:16-20,40-103` |
| I5 invalidation/recovery | **Grip deadman + explicit re-anchor.** Publishing only while `k_EButton_Grip` is held; on release the node returns immediately (no hold-last, no stop message) and sets `first_packet=True`, so the next engagement re-calibrates the offset. Downstream, Servo's `incoming_command_timeout: 0.5` halts motion when commands stop. | `quest_teleop.py:51-59,73-77`; `ur_servo.yaml:14` |
| Source visibility | **`FULL_SOURCE`** for the bridge and the whole ROS side. The XR runtime itself (ALVR/SteamVR/OpenVR) is external and opaque. | — |

## Native Decisions

- Tracking gate: `bPoseIsValid` only — a **partial** validity gate of exactly the kind this research distinguishes from tracked-vs-inferred state.
- Deadman/clutch: yes, grip-held, with automatic re-anchoring on re-engagement (a legitimate I5 recovery policy, not a violation).
- Freshness: none at the XR boundary; only Servo's generic 0.5 s command timeout downstream.

## Control Depth

- Last auditable downstream boundary: **`/ur5_arm_controller/joint_trajectory` → `gz_ros2_control` → Gazebo Sim joint motion**.
- Original consumer: MoveIt Servo pose-tracking, present in-repo.
- Physical driver dependency: **none anywhere in the repository.** Repo-wide grep for `robot_ip`, `ur_robot_driver`, `ur_client_library`, `use_fake_hardware`, `use_mock_hardware` returned **zero matches**; the only `<hardware>` plugin is `gz_ros2_control/GazeboSimSystem` (`ur5_robot.ros2_control.xacro:7`). This target is **structurally incapable of contacting a physical UR5e** at this revision.
- Classification: **`NATIVE_CONSUMER`** + simulated control effect.

## Testbed Adaptation

| Question | Answer |
| --- | --- |
| Desktop Humble usable? | **No** — Jazzy target. Must not be mixed into the Humble environment. |
| Separate Jazzy required? | **Yes.** A `ros:jazzy-ros-base` image is already present locally, which lowers this cost substantially. |
| Can publish to Pi? | Yes, but the Pi runs Humble; cross-distro DDS between Jazzy and Humble is not a supported configuration and any such observation must be labelled accordingly. Prefer observing inside the Jazzy container. |
| Simulator available? | **Yes** — Gazebo Sim, plus an external `ur_simulation_gazebo` package referenced by the README that is **not vendored**. |
| Inert stub feasible? | Unnecessary — simulator-only by construction. |
| Production path preserved? | Yes if injection is at `/servo_node/pose_target_cmds`. |
| Replay injection boundary | Injecting at `/servo_node/pose_target_cmds` is **downstream of `bPoseIsValid` and the grip deadman**, so it is `BOUNDARY_LIMITED_REPLAY` for I1/I5. Injecting inside the bridge by substituting the `openvr` module (a fake `pyopenvr` shim returning controlled `TrackedDevicePose_t` values) would be `UPSTREAM_FAITHFUL_REPLAY` and is the technically correct approach for I1. |

## Quest-less Potential

- Highest-fidelity option: a **fake `openvr` Python module** injected on `PYTHONPATH` that returns controlled `bPoseIsValid`, `eTrackingResult`, and pose matrices. This exercises the actual gate at `quest_teleop.py:49` and the actual deadman at `:51-59`. This modifies nothing in the pinned target — the substitution is at the dependency boundary.
- That yields a directly decisive I1 result: does the node keep publishing when `bPoseIsValid=true` but `eTrackingResult != Running_OK`? Source says **yes**, because `eTrackingResult` is never read. A runtime demonstration of that is a genuine E2 `UPSTREAM_FAITHFUL_REPLAY` result.
- Downstream consequence reachable: `NATIVE_CONSUMER_ACCEPTED` and simulated joint motion in a Jazzy container.

Blockers: Jazzy container build with MoveIt + Servo + Gazebo (large but purely additive); external `ur_simulation_gazebo` package.

## Future Quest Test

- Requires ALVR/SteamVR on a machine with a supported GPU stack — a substantially heavier hardware/software prerequisite than the Unity/Android targets. Deprioritise the native-Quest run here relative to the fake-`openvr` runtime work, which already answers the interesting question.

## Research Value

- RQ: direct hit on the **`VALID` vs `TRACKED`** distinction, this time in the OpenVR API family rather than OpenXR or WebXR. This is the same structural gap already documented for NVIDIA IsaacTeleop, but reached through a completely different API and an independent implementation.
- Invariants: I1 (partial gate, quality state unread), I2 (role-based identity, no continuity check), I3 (dropped), I5 (deadman + explicit re-anchor).
- White-box: yes for the bridge; the XR runtime is opaque.
- Independent architecture: **yes** — OpenVR/SteamVR is a distinct XR runtime family from WebXR, Unity XR/Meta, and Godot OpenXR.
- Positive control: partial (a real gate exists), and simultaneously a partial-gap case.

## Weaknesses

- Single-commit hobby-scale repository assembled from MoveIt Setup Assistant output, a third-party description package, and tutorial code (mismatched maintainer identities; leftover `yourusername` clone URL in README). Low maturity; do not present it as a representative production stack.
- README/code disagree on rate (README 30 Hz, code 50 Hz).
- Depends on an external non-vendored simulation package.

## Final Role

- **`PRINCIPAL_WHITEBOX`** (for the OpenVR family)
- **`POSITIVE_CONTROL`** (partial: a validity gate exists)

## Priority

**A** — high research value for the `VALID`-vs-`TRACKED` question and zero hardware risk, but requires a separate Jazzy environment and the repository is low-maturity.
