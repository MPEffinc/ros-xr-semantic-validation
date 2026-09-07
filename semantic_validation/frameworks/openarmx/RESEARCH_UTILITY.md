# FRAMEWORK: OpenArmX Teleop VR

## Identity

- Repository: `https://github.com/openarmx/openarmx_teleop_vr.git`
- Revision: `a3da7411b3d6ecaa7f94df859e07fb642aec859b` (2026-08-18), branch `6.0_basic`, worktree clean, shallow single-commit clone
- Local checkout: `semantic_validation/targets/openarmx_teleop_vr`
- XR frontend: **separate repository** `openarmx/openarmx_teleop_vr_apk` (`README.md:11-16`) — not fetched, source availability unverified
- IK core: **closed dependency** `openarmx_arm_driver` (`openarmx_teleop_vr_node.py:11-17`), required to run
- Author: Chengdu Changshu Robot Co., Ltd.; Chinese-language source comments throughout

## Architecture

```text
PICO / OpenXR headset app                        [EXTERNAL APK repo]
  -> UDP, ASCII whitespace-delimited tokens, port 5100, 512-byte max
     kinds: LEFT/RIGHT/L/R, LEFT_ABS/RIGHT_ABS, HEAD, JOY, BTN, CFG POSE_MODE, MODE, CALIBRATE_DONE
  -> openarmx_teleop_bridge_vr_node (C++)        [IN REPO]
  -> pico_{left,right}_controller/pose [PoseStamped], .../trigger|grip|rate [Float32],
     .../button_* [Bool], vr/head/pose, vr/control_mode [String], ...
  -> openarmx_teleop_vr_node (Python)            [IN REPO, but imports closed core]
     PinocchioTeleopCore / ik_solver              [CLOSED, openarmx_arm_driver]
  -> {left,right}_forward_position_controller/commands [Float64MultiArray]
  -> ros2_control forward_position_controller -> CAN driver [EXTERNAL openarmx_bringup]
```

## System Relevance

- Classification: **`HIGH_XR_ROS_CONTROL`**
- Why: a complete XR→UDP→ROS 2→IK→joint-command path. Joint commands are the last in-repo artefact, one hop from a real CAN-bus arm.

## Semantic Observability

| Axis | Finding | Evidence |
| --- | --- | --- |
| I1 tracking validity | **Entirely absent.** Repo-wide grep for every tracking-validity token: zero hits. The only "is this usable" test in the system is a freshness test, not a tracking test. | full-tree grep |
| I2 source identity | Left/right and head are separate topics and separate wire tokens; `frame_id_` parameter defaults to `pico_hmd`; optional TF children `pico_{left,right}_controller`. Modality/device identity beyond side is not carried. | `openarmx_teleop_bridge_vr_node.cpp:94-98,592-606` |
| I3 source time | **The most instructive case in the population: preserved at one internal boundary, then dropped at the next.** The bridge parses `timestamp_ns` from the datagram and uses it for `PoseStamped.header.stamp` when positive, else falls back to `now()`. The consuming teleop node then **discards `header.stamp` entirely** and re-stamps with `time.monotonic()` at callback entry. Every non-`PoseStamped` topic (trigger, grip, buttons, rate, mode) has no header at all, so their source time is unconditionally dropped. | bridge `cpp:510-525`, `:434-489`; consumer `openarmx_teleop_vr_node.py:356-376` (`pose.timestamp = time.monotonic()`) |
| I4 session/generation | **Absent.** UDP is connectionless; the bridge tracks no peer liveness. `absolute_packet_seen_`/`head_packet_seen_` only log the first packet ever. `SO_RCVTIMEO` of 1 s is a receiver poll timeout that gates nothing. | `cpp:299-304,257-259,612-617,630-633,734-735` |
| I5 invalidation/recovery | **Freshness-based gate plus grip deadman.** `raw_pose_fresh = (monotonic - pose.timestamp) <= 0.3` combined with `enabled`; on failure the node releases control and clears the reference pose. A separate joint-state completeness gate stops the loop when robot state is unavailable. | `openarmx_teleop_vr_node.py:404-405,420-430,901-903,939-964`; `config/teleop_params.yaml:8` |
| Source visibility | **`PARTIAL_SOURCE`** — bridge and ROS adapter fully readable; the XR app and the IK core are not. | — |

Notable: `ik_enable_override` is a subscribed topic with `TRANSIENT_LOCAL`/`RELIABLE` QoS that
force-enables control independently of the grip deadman (`openarmx_teleop_vr_node.py:244,405,564-573`).
A latched override topic that bypasses the operator deadman is a design decision worth recording;
it is not by itself evidence of a defect.

## Native Decisions

- Tracking gate: none.
- Validity gate: none.
- Deadman/clutch: `grip_value > grip_threshold` (default `0.5`), documented as a deliberate safety measure (`README.md:239-241`) — but bypassable via `ik_enable_override`.
- Freshness: 0.3 s, measured on **ROS-callback receipt monotonic time**, not the transmitted `timestamp_ns` which the consumer ignores.
- Recovery: release control and clear the relative reference pose on staleness; re-arm requires grip re-engagement.

## Control Depth

- Last auditable in-source boundary: `left_cmd_pub.publish(...)` / `right_cmd_pub.publish(...)` at `openarmx_teleop_vr_node.py:1006,1012` — `Float64MultiArray` on `{left,right}_forward_position_controller/commands`.
- Original consumer: `ros2_control` `forward_position_controller` in external `openarmx_bringup` / `openarmx_hand_bringup`.
- Physical driver dependency: **yes, and it is CAN-bus based** (`can0`/`can1`, up to `can3` for O6 hands) — launched only by the external bringup package with `use_fake_hardware:=false` (`README.md:72-83,123-129`). **That launch must never be invoked.** No robot IP/hostname exists in-repo; nothing in this repository talks to hardware directly.
- Classification: **`DRIVER_PREWRITE`** is reachable in principle (joint commands are exactly the pre-driver artefact), but only with the closed IK core present.

## Testbed Adaptation

| Question | Answer |
| --- | --- |
| Desktop Humble usable? | Probably (package format 3, ament); distro not pinned in-source. |
| Can publish to Pi? | Yes for the bridge's `PoseStamped` topics — the bridge alone is fully runnable and self-contained. |
| Simulator available? | **No.** `use_fake_hardware` belongs to the external bringup package. |
| Inert stub feasible? | Yes and low-risk: simply do not launch `openarmx_bringup`; nothing subscribes to the joint-command topics. A synthetic `/joint_states` publisher would be needed to pass the `current_q is None` gate. |
| Production path preserved? | For the **bridge**, fully. For the teleop node, not without the closed `openarmx_arm_driver`. |
| Replay injection boundary | **UDP datagrams to port 5100** — upstream of everything in-repo. A synthetic UDP sender emitting the ASCII protocol is straightforward and would be `UPSTREAM_FAITHFUL_REPLAY` for the entire in-repo path. |

## Quest-less Potential

- **Immediately achievable, valuable, and safe:** synthetic UDP → `openarmx_teleop_bridge_vr_node` → ROS topics → Pi observer. This directly demonstrates the I3 finding: a `timestamp_ns` supplied on the wire *does* reach `PoseStamped.header.stamp`, which the downstream consumer then ignores. Because the bridge has no external dependency, this needs only a ROS 2 container and a ~30-line UDP sender.
- **Blocked:** the teleop node / joint-command stage, because `openarmx_arm_driver` is closed and not installable. Do not fabricate a stand-in for it and then attribute the result to the framework.

## Future Quest Test

Not a priority. The frontend is a separate APK repository targeting PICO hardware, which we do not have. If the APK repository turns out to ship source, the audit should be extended; otherwise this stays black-box on the XR side.

## Research Value

- RQ: high, and unusually sharp for I3. It is the population's clearest example of **source time surviving one internal boundary and then being discarded at the next inside a single framework** — which is a stronger argument than "framework X drops timestamps" because both behaviours are visible in one codebase.
- Invariants: I3 (preserve-then-drop), I5 (freshness gate on the wrong clock), I1 (absent), I4 (absent).
- White-box/black-box: mixed; bridge white-box, XR app and IK core black-box.
- Independent architecture: **yes** — custom ASCII-over-UDP, PICO/OpenXR, distinct from every other family in the population.

## Weaknesses

- Closed IK core blocks the control-producing half at runtime.
- XR frontend in a different repository, unaudited.
- Single-commit shallow clone of one branch; no history.
- No simulator; hardware is CAN-based and must be strictly avoided.

## Final Role

- **`PRINCIPAL_BLACKBOX`** (XR side)
- **`AUXILIARY_WIRE`** (the UDP/bridge boundary is the auditable, runnable part)

## Priority

**B** — excellent I3 evidence obtainable cheaply at the bridge, but the control-producing half is not runnable and the frontend is out of reach.
