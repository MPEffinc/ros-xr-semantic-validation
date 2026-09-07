# FRAMEWORK: Docker_Teleop

## Identity

- Repository: `https://github.com/Noah727/Docker_Teleop.git`
- Revision: `64cbdde88bc52c6a80d37f994752e50f95ba537e` (2026-07-28, "Consolidate public README polish"), worktree clean
- Local checkout: `semantic_validation/targets/docker_teleop`
- Paper/project: none found; public repository with `docs/` set
- License: third-party notices retained per `docs/System_Setup.md:324-328`; no single top-level license identified in audit
- Unity: `UnityApp/ProjectSettings/ProjectVersion.txt:1-2` → `6000.2.10f1`

## Architecture

```text
Meta Quest (OpenXR 1.15.1 + Meta XR SDK 72.0.0, Unity 6000.2.10f1)
  -> OVRCameraRig/TrackingSpace/{Left,Right}ControllerAnchor Transform
  -> HandPoseSender.cs  (JSON over raw TCP, newline framed, port 5026->5005)
  -> quest_controller_receiver (rclpy)      [teleop_bridge_msgs/ReceivedPoseStates]
  -> hand_pose_mapper                        [teleop_bridge_msgs/TargetTwistStates]
  -> servo_command_bridge                    [geometry_msgs/TwistStamped]
  -> MoveIt Servo (servo_node)               [/servo_node/delta_twist_cmds]
  -> /joint_group_velocity_controller/commands
  -> gz_ros2_control -> Ignition Gazebo (UR5e + Robotiq Hand-E)
```

Second, independent TCP channel: vendored Unity `ROS-TCP-Endpoint` for ordinary ROS topics.

## System Relevance

- Classification: **`HIGH_XR_ROS_CONTROL`**
- Why: XR controller pose is the sole driver of Cartesian twist commands consumed by MoveIt Servo, which produces joint velocity commands that actuate a simulated UR5e. The control path is complete and in-source from XR acquisition to simulated joint motion.

## Semantic Observability

| Axis | Finding | Evidence |
| --- | --- | --- |
| I1 tracking validity | **Partially preserved, and it gates.** `HandData.isTracked` is serialized in the wire payload and re-checked server-side. **But its raw meaning is controller *connection*, not pose validity/quality.** | `HandPoseSender.cs:81` (field), `:1242-1244` (`IsControllerConnected()` wraps `OVRInput.GetConnectedControllers()`), `:1252-1257,1269-1274` (position left at default when untracked), `servo_command_bridge.py:123-125` (`tracked_ok` gates forwarding) |
| I1 (hand fallback) | Genuine Meta hand-tracking validity used as a gate on the OVRHand path | `HandPoseSender.cs:1280-1298` (`ovrHand.IsTracked`) |
| I1 (absent) | `trackingState`, `InputTrackingState`, `IsPoseValid`, `confidence`: **NOT FOUND IN SOURCE** | repo-wide grep, zero hits |
| I2 source identity | Left/right preserved as separate fields and separate topics; modality (controller vs hand) is collapsed into one `isTracked` boolean | `HandPoseSender.cs:78-84`, `quest_controller_receiver.py:46-47` |
| I3 source time | **Computed then DROPPED.** Unity `Time.time` is placed in the payload but the receiver never reads it. All staleness is measured on ROS-side receipt time. | `HandPoseSender.cs:89,250` (sent); `quest_controller_receiver.py:237-421` (never read); `:425,471-473` (`get_clock().now()` stamping) |
| I4 session/generation | **Absent.** No sequence number, packet counter, or session/generation id in `Packet`, `ControlsData`, `ReceivedPoseStates.msg`, or `TargetTwistStates.msg`. New TCP client silently replaces the old one with no handshake. | `HandPoseSender.cs:86-151`; `quest_controller_receiver.py:94-105` (`_set_client` closes old socket) |
| I5 invalidation/recovery | **Strong, multi-layer, but receipt-time based.** On staleness the receiver substitutes a neutral safe state rather than latching the last value; the servo bridge publishes an all-zero twist; MoveIt Servo halts. | `quest_controller_receiver.py:423-436,587-625`; `hand_pose_mapper.py:911-914`; `servo_command_bridge.py:122-150`; `servo_gz.yaml` `incoming_command_timeout: 0.25` |
| Source visibility | **`FULL_SOURCE`** — Unity C#, all ROS nodes, launch, Docker, world files present | — |

## Native Decisions

- Tracking gate: yes — `tracked_ok` in `servo_command_bridge.py:123-125`, plus `isTracked`-conditional population in Unity.
- Validity gate: only in the connection sense; no pose-validity/quality API is consulted.
- Deadman/clutch: yes, and double-enforced. Client-side `rightGripValue >= analogPressThreshold` (`HandPoseSender.cs:434`, threshold `0.55` at `:155`); server-side `arm_input_active = input_active and self._teleop_enable` (`hand_pose_mapper.py:916`). Grip release clears session state (`:768-772`). Thumbstick recenter/pause at `:758-763`.
- Freshness: four independent 0.25 s receipt-age gates plus Servo's own `incoming_command_timeout`. **None of them validates capture-to-command age**, because the capture time is discarded.
- Session: none.
- Recovery: neutral-state substitution and zero-twist, not last-value latching. This is a **safe** design pattern.

## Control Depth

- Last auditable downstream boundary: **`/joint_group_velocity_controller/commands` → `gz_ros2_control` → simulated joint motion in Ignition Gazebo**.
- Original consumer: MoveIt Servo, present and configured in-repo (`servo_gz.launch.py:82-95`, `servo_gz.yaml`).
- Physical driver dependency: `ur_robot_driver` exists in the image and in an **alternate** launch path only (`servo_test.launch.py:29,33-34,92-93`, `robot_ip` default `192.168.56.101`; also a placeholder in `ur_moveit_config/launch/ur_moveit.launch.py:89`). It is **not** on the default `backend11_lifecycle.sh` path. **Never invoke `servo_test.launch.py`.**
- Classification: **`NATIVE_CONSUMER`** reachable, and **simulated control effect** reachable, without any physical robot.

## Testbed Adaptation

| Question | Answer |
| --- | --- |
| Desktop Humble usable? | Distro matches (Humble), but `ros_backend1.1/Dockerfile:1` is `arm64v8/ros:humble-ros-base` — an **ARM64** base. On our x86_64 desktop this needs either an x86_64 equivalent base image (a deliberate, documented deviation) or qemu emulation (too slow for Gazebo). |
| Separate distro required? | No. Humble. |
| Can publish to Pi? | Yes — any of `/received_pose_states`, `/target_twist_states`, `/servo_node/delta_twist_cmds`, or the joint command topic can be observed by the Pi sink over the dedicated link. |
| Simulator available? | **Yes** — Ignition Gazebo world `ur_hande_tabletop.sdf` via `simulation/launch/run_tabletop_sim.sh`. |
| Inert stub feasible? | Yes, and mostly unnecessary: the default path is already simulator-only. |
| Production path preserved? | Yes, if injection happens at the **TCP wire boundary**. |
| Replay injection boundary | **Preferred: a synthetic TCP client speaking the newline-JSON protocol** (`HandPoseSender.cs:249-261` schema) → exercises `quest_controller_receiver` framing, staleness, and client-replacement logic. In-repo alternatives (`debug_hand_generator.py`, `fake_hand_publisher.py`) inject **after** the receiver and therefore yield `BOUNDARY_LIMITED_REPLAY` — `scripts/test_tools/eval_scripts/04_synthetic_hand_receiver_test.py:31-32` explicitly stops the receiver first. |

## Quest-less Potential

Achievable now, with a hand-written synthetic TCP client (not present in-repo):

- E2 with **`UPSTREAM_FAITHFUL_REPLAY`** relative to the ROS-side semantic gates, because injection at the TCP boundary is upstream of `tracked_ok`, all four staleness gates, and the server-side deadman re-check.
- Directly testable, robot-free: does `isTracked=false` in the payload actually suppress motion end-to-end? Does a stalled stream produce neutral state and a zero twist? Does an old Unity `timestamp` change anything (predicted: no, because it is never read)?
- Downstream consequence reachable: `NATIVE_CONSUMER_ACCEPTED` (MoveIt Servo) and simulated joint motion.

Blockers: ARM64 base image versus x86_64 host; Gazebo + MoveIt image build time; no in-repo wire-protocol client.

## Future Quest Test

- T0: grip held, controller tracked, 10 s baseline. Observe `isTracked=true` in payload, non-zero twist at `/servo_node/delta_twist_cmds`, simulated motion.
- T1: occlude the controller 3–5 s **without** releasing grip and without headset focus loss. Observe whether `OVRInput.GetConnectedControllers()` actually changes (it likely does **not** under mere optical occlusion — the controller stays connected while its pose degrades). This is the decisive question for this framework.
- Observable raw transition: Unity-side side-band of `isTracked`, `OVRInput` connection set, and the raw anchor Transform, correlated against the TCP payload and the Servo input.
- Expected correlation: if connection-derived `isTracked` stays true under occlusion, then the framework's otherwise-strong gate does not fire for optical tracking loss, and the extrapolated/frozen Transform reaches Servo.
- Manual steps: install APK, hold grip, occlude, recover; five valid transitions.

## Research Value

- RQ: directly on target — a complete XR→ROS→control-consumer path with an explicit, source-visible validity gate.
- Invariants: I1 (gate present but semantically mismatched), I3 (source time computed then dropped; freshness revalidated locally), I5 (strong neutral-state recovery), I4 (absent).
- White-box: **yes**, fully.
- Independent architecture: **yes** — raw TCP JSON with a bespoke receiver, distinct from Unity ROS-TCP Connector message flow, WebXR/WSS, and UDP/ASCII families. Note the repo also vendors ROS-TCP-Endpoint for a separate channel, so lineage is mixed.
- Positive control: **partially** — it is the clearest example of a framework that *does* propagate and gate on a validity-ish flag and *does* fail to a neutral state, while still dropping source time. This makes it valuable as a contrast case rather than a pure failure case.

## Weaknesses

- The `isTracked` field's raw meaning (connection) may not change under optical occlusion, so the gate may be weaker in practice than it appears in source. This must be tested, not assumed.
- ARM64 image base complicates faithful reproduction on the x86_64 desktop.
- Real-hardware launch path exists in-tree and must be actively avoided.
- No in-repo synthetic client for the true wire boundary.

## Final Role

- **`PRINCIPAL_WHITEBOX`**
- **`POSITIVE_CONTROL`** (for I5 neutral-state recovery and for I1 gate presence)

## Priority

**S** — highest-value Quest-less target: full source, native consumer, simulator, no hardware requirement, and a semantically interesting gate whose raw meaning is testable.
