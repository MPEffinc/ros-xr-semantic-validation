> **Provenance.** This audit was delegated to a read-only subagent on 2026-10-01 under `AUDIT_METHOD.md` and reviewed by the lead auditor. Claims spot-checked against the pinned source by the lead: `isTracked` = `IsControllerConnected` (`HandPoseSender.cs` L1238–1270). Other claims carry the subagent's citations and have not been re-read line by line. Treat them as SOURCE_CONFIRMED at the cited lines, subject to re-check before any claim is published. Scratchpad paths (`rtc/`) refer to read-only copies of upstream files fetched by commit.

# Audit: Noah727/Docker_Teleop, XR to ROS teleop command path (source level, read-only)

**Commit audited: `64cbdde88bc52c6a80d37f994752e50f95ba537e`** ("Consolidate public README polish", 2026-07-28)

## 1. Pins & scope

| Item | Value |
|---|---|
| Local checkout | `/home/cclab/ros_xr/Deprecated/semantic_validation/targets/docker_teleop` |
| `git rev-parse HEAD` | `64cbdde88bc52c6a80d37f994752e50f95ba537e`; `git status --porcelain` is empty (clean) |
| `git ls-remote origin HEAD` | `0a8f756f052735beef88a1ba0702bbfcee29220b`. Remote is **1 commit ahead**: "Feature evaluation throughput at start of README". `gh api compare` shows the only changed file is `README.md`, so the code under audit is the same as remote HEAD. |
| Unity | `UnityApp/ProjectSettings/ProjectVersion.txt` = 6000.2.10f1. `Packages/manifest.json`: `com.meta.xr.sdk.core` 72.0.0, `com.meta.xr.sdk.interaction.ovr` 72.0.0, `com.unity.xr.openxr` 1.15.1. The SDK sources (OVRInput, OVRManager, OVRHand) are **not in the repo**: wrapper boundary, everything beyond it is NOT_VERIFIED. |
| Backend | `ros_backend1.1/` (ROS 2 Humble). Servo is the container's `ros-humble-moveit-servo` 2.5.9 (per caller). Reference source: `moveit2_2.5.9/moveit_ros/moveit_servo`. |
| Vendored / lineage | `ros_backend1.1/src/ROS-TCP-Endpoint` is Unity-Technologies v0.7.0 (`package.xml:5`, `CHANGELOG.md:26`). It is **not on the arm-control path**; Unity uses it only for telemetry, task select and scene sync (`RecordingPerformanceTraceLogger.cs:224-281`, `MREvaluationTracePublisher.cs:104-163`, `MRCentralControlPanel.cs:2051-2084`). Also vendored: `robotiq_hande_description`, `ur_moveit_config` (upstream UR). `teleop_bridge`, `receiver` and `teleop_bridge_msgs` are the author's own. |
| Runtime config used | Dual-arm scene `Assets/Scenes/GazeboReplica_DualArm_MR.unity` (serialized HandPoseSender at lines 3441-3491: port 5026, `preferControllers:1`, `sendRelativeToControlFrame:0`, `includeWorkspacePoseInControls:1`, `mappingMode: unity_world_delta`). Backend is `scripts/backend11_lifecycle.sh`: receiver runs with **no params** (`:401`, default `listen_port` 5005, docker maps host 5026→5005 at `docker-compose.yaml:8`). Per-arm mapper and bridge run with `teleop_tuning_dual_{left,right}.yaml` (`:660-667`). Servo comes from `servo_dual_gz.launch.py` with `servo_gz.yaml`. |
| Evidence level | Source only. README/docs = AUTHOR_CLAIM. Runtime facts from PRIOR_INTERNAL (`DOCKER_TELEOP_*_RUNTIME.md`, `S2_DOCKER_CONTROL_BASELINE.md`) are synthetic-sender runs without a Quest and are cited as background only. |

## 2. Command path table

| # | Hop | File:function:lines | Input to output | Freshness / gating |
|---|---|---|---|---|
| H0 | Source API (OVR wrapper over OpenXR) | `HandPoseSender.cs:GetRightInputData/GetLeftInputData` 1246-1278; `GetHandDataFromTransform` 1280-1299; button/axis reads 377-436, 1013-1098 | `OVRInput.Get*` and `RightControllerAnchor.position/rotation` (Unity world) | `isTracked = IsControllerConnected()` (`OVRInput.GetConnectedControllers`, 1240-1244). The hand path uses `OVRHand.IsTracked` (1285). |
| H1 | XR app packet | `HandPoseSender.Update` 229-263; `GetControlsData` 373-534 | `Packet{timestamp=Time.time, left_hand, right_hand, controls{…}}`, sent as JSON once per frame | No focus or pause gating (§3 A1/A7) |
| H2 | Transport | `SendJsonPacket` 325-344 (raw TCP, newline JSON); `ConnectTcp` 281-323 | TCP to 127.0.0.1:5026 (adb reverse), then docker to 5005 | A send exception closes the socket and reconnects every 1 s (`reconnectIntervalSec`) |
| H3 | ROS receiver | `quest_controller_receiver.py:_rx_loop` 122-182, `_store_payload` 224-235, `_parse_payload` 237-421, `_publish_loop` 423-469, `_make_msg` 471-511 | Latest-wins state, republished at 60 Hz as `ReceivedPoseStates` on `/received_pose_states` and `/{left,right}_arm/received_pose_states` | `stale_timeout_sec` 0.25 on packet arrival (monotonic) produces `_neutral_state` (433-436, 587-625). The client is dropped after 1.5 s with no bytes (155-161). |
| H4 | Mapper (per arm) | `hand_pose_mapper.py:_on_pose_states` 735-909, `_publish_loop` 911-1098 | P-controller: `twist = kp*(target_pos − ee_pos)`, speed-limited (1011-1013), giving `TargetTwistStates` | Mapper stale 0.25 s on msg arrival (913). Requires `tracked`, `teleop_enable`, and a successful TF lookup (914-916, 1000-1002). |
| H5 | Servo bridge | `servo_command_bridge.py:_publish_loop` 120-150 | `TwistStamped` on `/{arm}/servo_node/delta_twist_cmds` at 60 Hz, **always published** (zero twist when inactive) | `active = have_msg ∧ ¬stale(0.25) ∧ tracked ∧ ¬reset` (122-125) |
| H6 | MoveIt Servo 2.5.9 | `servo_calcs.cpp:calculateSingleIteration` 330-470; `twistStampedCB` 1154-1166; `cartesianServoCalcs` 530-567 | Velocity commands to `/{side}_joint_group_velocity_controller/commands` (`servo_dual_gz.launch.py:84,150,158`; `servo_gz.yaml:13-17`) | `incoming_command_timeout` 0.25 and `num_outgoing_halt_msgs_to_publish` 4 (`servo_gz.yaml:30-31`); staleness = `now − header.stamp` (342-345) |
| H7 | Controller to Gazebo | `simulation/config/ur5e_gz_controllers_*.yaml` (not deep-audited) | JointGroupVelocityController | NOT_VERIFIED (behaviour on missing commands depends on upstream controller) |
| Side | Gripper | `simple_gripper_command_bridge.py:_on_input` 93-101, `_tick` 138-167 (or `coupled_gripper_controller`, chosen at `backend11_lifecycle.sh:642-648`) | `gripper_cmd` ±1/0 is integrated into a position target | Command zeroed when stale or reset (145). `require_tracked: false` in dual configs (`teleop_tuning_dual_left.yaml:83,106`). |
| Side | Reset | `reset_manager.py:_on_target_twist` 505-517, `_run_reset_sequence` 545-606 | Rising edge of `reset_robot_enable` calls stop_servo, homes the arm, then start_servo | |

## 3. Findings A1–A9

### A1 Focus / session / action-active
- SOURCE_CONFIRMED: no focus or session handling on the control path. `HandPoseSender` has no `OnApplicationFocus`/`OnApplicationPause` and no `OVRManager` focus or session events. NOT_FOUND_IN_SEARCH (queries: `OnApplicationPause|OnApplicationFocus|HMDUnmounted|InputFocus|hasInputFocus|focusLost|focusAcquired|OVRManager\.\w+\s*\+=` over `UnityApp/Assets/Scripts`). The only `OnApplicationPause` is in `VRCameraFix.cs:21-29`, which is **not attached** in any tracked scene (its script GUID `b624ed26…` matches no `.unity` or `.prefab`).
- SOURCE_CONFIRMED: the packet has no focus or action-active field (`Packet`/`ControlsData` 86-151). The receiver and mapper have no such input (`ReceivedPoseStates.msg`).
- NOT_VERIFIED: what `OVRInput.Get*` returns when the OpenXR session is not FOCUSED. The OpenXR spec says `isActive` must be false and values unavailable while unfocused (`input.adoc:834-841`), but the OVR wrapper is outside the repo.
- Existing protection: if a non-focused or paused app stops calling `Update`, the receiver neutralizes after 0.25 s (`receiver:433-436`).

### A2 Valid vs tracked
- SOURCE_CONFIRMED: for controllers, `isTracked` means **"controller connected"**: `data.isTracked = IsControllerConnected(OVRInput.Controller.RTouch)` (`HandPoseSender.cs:1251,1268`; 1240-1244). Pose is the anchor `Transform` (1254-1255, 1271-1272). Position/orientation tracked or valid flags are not read. NOT_FOUND_IN_SEARCH (queries: `GetControllerPositionTracked|GetControllerOrientationTracked|PositionValid|OrientationTracked|IsDataValid|IsDataHighConfidence|TrackingState` over `UnityApp/Assets`).
- SOURCE_CONFIRMED: the hand path uses `OVRHand.IsTracked` (1285), or **true if no OVRHand component** (`ovrHand == null ? true`). It is only taken when no active controller anchor exists (1248, 1265).
- SOURCE_CONFIRMED: one bool `tracked` survives every hop: receiver `hand.isTracked` (251) to `msg.tracked` (475); mapper `_tracked`, `if not self._tracked: return` and sessions reset (866-870); bridge `require_tracked` (123). No VALID/TRACKED split (OpenXR `spaces.adoc:218-220,265-267`) exists anywhere.
- NOT_VERIFIED: what the OVR anchor transform does when optical tracking is lost but the controller stays connected (held pose, IMU-only, or other). HYPOTHESIS: a connected but optically lost controller would pass the gate. Prior S2 D2 only tested a synthetic `isTracked=false`.

### A3 Buttons / toggle / clutch / deadman
- SOURCE_CONFIRMED deadman: per-arm grip analog `>= 0.55`, a **level** sampled each frame, not latched (`HandPoseSender.cs:434,436,476-477`). The mapper requires it every cycle (`arm_input_active = input_active and self._teleop_enable`, 916). An engage edge requests a re-anchor (765-767). A release resets sessions (768-772).
- SOURCE_CONFIRMED clutch: right thumbstick press, level (`recenter_held` 388-391), mapped to `recenter_enable` (468). The mapper zeroes motion while held (949-953) and re-anchors on release (1220-1229). Note: the msg field `recenter_enable` is the clutch, **not** an XR origin recenter. The left arm has no thumbstick clutch: `left_recenter_enable` is only `leftAttachmentPaused` (469-470).
- SOURCE_CONFIRMED latched in Unity: gripper toggle state `left/rightGripperToggleCommand` (441-445), attachment mode `left/rightAttachmentModeActive` (393-401), `gamepadModeActive` (959). None of these is reset by `CloseTcpClient` (346-371) or any pause handler (none exists). `ToggleControllerArmSwap` (963-977) resets edge memories but not the toggle states.
- SOURCE_CONFIRMED pulses: reset requests are time pulses of 0.25 s on Unity `Time.time` (979-1011). The mapper latches robot reset for `reset_hold_sec` 8 s (747-749) and auto-releases it (932-935).
- SOURCE_CONFIRMED: on stale, the receiver's neutral state sets close/open/teleop/attachment to false (600-613). The mapper zeroes `gripper_cmd` if not `packet_active` (920). The gripper bridge zeroes its hold command when stale (145).

### A4 Device / interaction-profile change
- SOURCE_CONFIRMED: Unity handles profile variability by OR/max over several bindings (`IsLeftYHeld` etc. 1013-1055; `MaxAxis` over Primary/Secondary/combined Touch 1057-1098; stick fallback 422-430). The code comment calls this a "Quest/OpenXR profile" workaround (408-410).
- NOT_FOUND_IN_SEARCH (queries: `InteractionProfileChanged|deviceConnected|deviceDisconnected|InputDevices\.|ControllerChanged|GetActiveController` over `UnityApp/Assets/Scripts`; `InputDevices` appears only in `HandTrackingDebugger.cs:67,73`): no profile or device change event is consumed. Controller-to-hand switching is implicit: anchor `activeInHierarchy` (1248) and the connected flag.
- SOURCE_CONFIRMED: `source` string `quest_dual_controller[_swapped]` (495) is published (`msg.source`, receiver 501) but the mapper does not consume it. Hand vs controller is not distinguished downstream (`source` is not read in `_on_pose_states`).

### A5 Origin / recenter
- SOURCE_CONFIRMED: no handling of tracking-origin or recenter events. NOT_FOUND_IN_SEARCH (queries: `DisplayRecentered|RecenteredPose|TrackingOriginChanged|trackingOriginType|ReferenceSpaceChangePending` over `UnityApp/Assets`, scenes included). `VRCameraFix.Recenter()` calls `OVRManager.display.RecenterPose()` (48-59) but is unattached (A1).
- SOURCE_CONFIRMED: poses are sent in Unity world space (`sendRelativeToControlFrame:0`, `sendRelativeToHeadset:0` in the dual scene). The mapper's `unity_world_delta` uses `latest_hand_world_pos − ref_hand_world_pos` (1242). There is no packet field or ROS field for origin or recenter epoch.
- HYPOTHESIS (not runtime-verified, no Quest): a system recenter during an engaged session moves the controller's world pose without user motion. The mapper then sees it as a hand delta. It would be bounded by `max_linear_speed` (dual 0.85 m/s, `teleop_tuning_dual_left.yaml:25`) and the clip `[-1,1]` m (48-49). OpenXR defines `XrEventDataReferenceSpaceChangePending.changeTime` for this case (`spaces.adoc:205-208,251-255`). It is not visible past the OVR wrapper, so NOT_VERIFIED.

### A6 Calibration / anchor; which transform multiplies which sample
- SOURCE_CONFIRMED: the workspace pose (`GazeboWorkspace` transform) is sampled in the **same Update and packet** as the hand pose (`HandPoseSender.cs:252-257` with 499-509). The mapper stores the latest workspace pose per msg (804-825).
- SOURCE_CONFIRMED: delta mapping rotates the world-frame delta since the anchor by the **current** workspace rotation (`_unity_world_vector_to_workspace` 1478-1481, used at 1243). It is not the rotation at anchor time. The author comment says this is deliberate (1238-1241). Workspace drag is blocked only while the **dragging controller's own** grip is held (`WorkspaceDragController.cs:142-152`). HYPOTHESIS: dragging or rotating the workspace with one controller while the other arm is engaged re-rotates that arm's accumulated delta.
- SOURCE_CONFIRMED: attachment mode with `attachment_use_absolute_position/rotation: true` (dual configs 14-16) maps the absolute hand world pose plus offset through the latest workspace pose and static `attachment_base_xyz/xyzw` (1273-1288, 1305-1315). It does not anchor relative to engage, so on engage the arm drives to the absolute hand pose, speed-limited. This is by design (APPLICATION).
- SOURCE_CONFIRMED: the attachment offset is captured in Unity from the replica `tool0` transform against the current packet pose (`TryCaptureAttachmentOffsetFromCurrentPose` 597-632) and persisted in PlayerPrefs (879-889). HYPOTHESIS: the replica tool pose reflects ROS joint states with transport lag, so the offset can encode that lag.
- SOURCE_CONFIRMED: the EE pose is a TF lookup with `rclpy.time.Time()` (latest available), `lookup_transform(target_frame, ee_frame, Time())` (1531). It is paired with the latest received hand sample. There is no sample-time alignment.
- SOURCE_CONFIRMED (Servo 2.5.9): the bridge frame_id is the mapper `target_frame` = `left_base_link` (`teleop_tuning_dual_left.yaml:6`), which equals Servo `planning_frame` (`servo_dual_gz.launch.py:81`), so Servo applies no frame transform (`servo_calcs.cpp:531`). Any other frame would be resolved via `current_state_->getGlobalLinkTransform` from the latest robot state (354-360, 552-554), not TF at the command stamp.
- Re-anchor on engage **exists** (765-767, 1207-1229), and on clutch release, tracking regain (866-869 then 1220), mode change (774-777, 789, 801) and reset (750). Not a gap.

### A7 Disconnect / reconnect, pause / resume
- SOURCE_CONFIRMED sender: a TCP write failure closes and retries after 1 s (338-343, 265-279). The connect is a blocking `WaitOne` up to 300 ms on the main thread (297-298). No pause handler.
- SOURCE_CONFIRMED receiver: a single client. Accept happens only when no client is held (126-150). The client is dropped on peer close, socket error, or 1.5 s without bytes (155-176). The buffer is cleared on drop (148, 161, 165, 175). Stale after 0.25 s produces the neutral state (433-436).
- SOURCE_CONFIRMED: the neutral state forces `teleop_enable=False` and `attachment_mode=False` downstream. On reconnect the mapper sees new edges and re-anchors (765-767, 774-777). PRIOR_INTERNAL D3/D5 observed this (reference recapture after reconnect).
- SOURCE_CONFIRMED: Unity latched states (A3) persist across disconnect or pause. After reconnect, the previous gripper toggle and attachment mode re-assert without user action. HYPOTHESIS: the effect is the gripper resuming its last close/open direction.
- SOURCE_CONFIRMED Servo: the bridge publishes fresh-stamped messages at 60 Hz even when inactive (zero twist, 135-150). Servo's `incoming_command_timeout` therefore never trips while the bridge is alive. Zero commands follow the "not stale, all zero" branch: last positions with zero velocities, published each cycle because `done_stopping_` is reset (`servo_calcs.cpp:410-418, 425-428, 447-450`). Servo's stale or halt path (`filteredHalt` 870-905; stop publishing after more than 4 halt messages, 432-438) only applies if the bridge or upstream dies. Staleness is measured against the **bridge stamp** in sim time (bridge and servo `use_sim_time: true`; `servo_dual_gz.launch.py:134`, `teleop_tuning_dual_left.yaml:53`).

### A8 Pending commands, previous goal, auto-resume
- SOURCE_CONFIRMED: the twist pipeline is stateless latest-value (no queue). Mapper targets come from the current anchor. The bridge holds only `_latest_msg` (65-69). Servo holds only `latest_twist_stamped_` (1157).
- SOURCE_CONFIRMED auto-resume after reset: the mapper reset latch auto-releases after 8 s (932-935). `arm_input_active` depends only on the grip **level** (916), so if the grip is held through the reset, motion resumes without a new engage edge, from a fresh anchor (`_request_position_recenter` at 750, then 1220-1229). The bridge re-calls `start_servo` on reset release (127-133), and Servo `start()` unpauses (`servo.cpp:69`). Relative re-anchoring avoids a jump. The re-engage gesture is not required.
- SOURCE_CONFIRMED (upstream): `ServoCalcs::start()` does not clear `latest_twist_stamped_`. NOT_FOUND_IN_SEARCH (query: `latest_twist_stamped_.reset|latest_twist_stamped_ = nullptr` in `servo_calcs.cpp`). It is harmless here because the bridge overwrites it at 60 Hz.

### A9 Source-sample linkage
- SOURCE_CONFIRMED: Unity sends `timestamp = Time.time` (250), seconds since app start, float32. The receiver **never reads it**: `timestamp` does not occur in `quest_controller_receiver.py` (grep). There is no sequence or packet id field in `Packet` or the messages.
- SOURCE_CONFIRMED restamping at each hop: receiver `header.stamp = get_clock().now()` at publish time (425, 473). The receiver runs without params, so wall clock (`backend11_lifecycle.sh:401`). The mapper restamps `now()` in sim time (1059; `use_sim_time: true` at `teleop_tuning_dual_left.yaml:3`). The bridge restamps again (136). Each hop's freshness check uses local monotonic **arrival** time (receiver 228-234, 428-433; mapper 736, 913; bridge 68, 122), not source time.
- Consequence (SOURCE_CONFIRMED structurally): from Servo backwards, no field links a consumed `TwistStamped` to the source XR sample or its sample time. PRIOR_INTERNAL S2 D4 reached the same conclusion at runtime ("does not retain or age-check the supplied source `timestamp`").

## 4. Information-delivery table (evidence × hop)

Legend: **R** = read/produced, **F** = forwarded, **C** = consumed for gating or logic, **L** = lost or dropped, **–** = never present, **NV** = beyond wrapper, not verified.

| Evidence | H0 OVR/OpenXR | H1 Unity packet | H2 TCP | H3 receiver | H4 mapper | H5 bridge | H6 Servo |
|---|---|---|---|---|---|---|---|
| Session focus / action isActive | NV | – | – | – | – | – | – |
| Controller connected | R (`GetConnectedControllers`) | F as `isTracked` | F | F `tracked` | C (866) | C via `tracked` (123) | – |
| Pose VALID/TRACKED bits | NV (not read) | – | – | – | – | – | – |
| Hand `OVRHand.IsTracked` | R (1285) | F as `isTracked` | F | F | C | C | – |
| Deadman (grip level) | R | F `*_teleop_enable` | F | F `teleop_enable` | C (916) | – (only via zero twist) | – |
| Clutch (R thumbstick) | R | F `recenter_enable` | F | F | C (949) | – | – |
| Gripper toggle (Unity-latched) | R edge | F latched level | F | F close/open | C `gripper_cmd` | – (gripper node) | – |
| Interaction profile / device change | NV | L (OR-merged) | – | – | – | – | – |
| Origin / recenter event | NV | – | – | – | – | – | – |
| Workspace pose (same-frame) | – | R/F | F | F | C (latest) | – | – |
| Attachment offset | – | R/F (PlayerPrefs) | F | F | C | – | – |
| Source timestamp | – | R `Time.time` | F | **L** (unread) | – | – | – |
| Arrival freshness | – | – | – | C 0.25 s | C 0.25 s | C 0.25 s | C 0.25 s on bridge stamp |
| EE pose for error | – | – | – | – | R TF `Time()` latest | – | R `current_state_` latest |
| Reset request | R panel pulse | F | F | F | C latch 8 s | C | paused/started via service |

## 5. Candidate matrix rows

| Item | Class | Label |
|---|---|---|
| `isTracked` = controller connected, not pose-tracked/valid (`HandPoseSender.cs:1251,1268`) | METADATA | SOURCE_CONFIRMED (effect when optically lost: HYPOTHESIS) |
| Hand path defaults `tracked=true` without an OVRHand component (`:1285`) | IMPLEMENTATION | SOURCE_CONFIRMED |
| No focus/session/action-active signal anywhere on the path | METADATA | SOURCE_CONFIRMED (OVR behaviour when unfocused: NOT_VERIFIED) |
| No recenter/origin-change event or epoch (`VRCameraFix` unattached) | METADATA | SOURCE_CONFIRMED (motion effect: HYPOTHESIS) |
| No interaction-profile/device-change event; multi-binding OR fallback | INTEGRATION | SOURCE_CONFIRMED |
| Source `timestamp` sent but dropped by receiver; no seq id; restamped at each hop | METADATA | SOURCE_CONFIRMED |
| Freshness = local arrival time at each hop (0.25 s ×4), Servo checks only bridge stamp | PLACEMENT | SOURCE_CONFIRMED |
| Bridge always publishes fresh zero twists, so Servo `incoming_command_timeout`/halt path is effectively bypassed while the bridge is alive (stop via zero-command path) | INTEGRATION | SOURCE_CONFIRMED |
| Receiver neutral-on-stale forces teleop/attachment edges, so re-anchor on reconnect | IMPLEMENTATION (existing defense) | SOURCE_CONFIRMED; PRIOR_INTERNAL runtime D3/D5 |
| Re-anchor on engage/clutch/tracking regain/mode change exists | APPLICATION (existing) | SOURCE_CONFIRMED |
| Unity-latched gripper toggle / attachment mode survive disconnect & pause and re-assert on reconnect | APPLICATION | SOURCE_CONFIRMED (physical effect: HYPOTHESIS) |
| Reset latch auto-releases after 8 s and resumes on held grip without a new engage edge | APPLICATION | SOURCE_CONFIRMED |
| Delta rotated by current (not anchor-time) workspace rotation; drag blocked only by the dragging controller's grip | APPLICATION | SOURCE_CONFIRMED (cross-arm effect: HYPOTHESIS) |
| Attachment absolute mode is not engage-relative (drives to the absolute hand pose) | APPLICATION | SOURCE_CONFIRMED (by design) |
| Attachment offset captured from the Unity replica `tool0` (ROS-lagged) | PLACEMENT | HYPOTHESIS |
| EE pose TF `Time()` latest, paired with latest hand sample (no time alignment) | PLACEMENT | SOURCE_CONFIRMED |
| Mixed clocks: receiver wall, mapper/bridge/Servo sim (`use_sim_time`), Unity `Time.time` | OBSERVATION | SOURCE_CONFIRMED (config); runtime RTF effect NOT_VERIFIED |
| Left arm has no thumbstick clutch (`left_recenter_*` = attachment pause only) | APPLICATION | SOURCE_CONFIRMED |
| README "right thumbstick press: clutch…release to recenter" (`docs/Getting_Started.md:197`) matches code | OBSERVATION | AUTHOR_CLAIM, consistent with source |
| Controller/Gazebo behaviour when Servo stops publishing | INTEGRATION | NOT_VERIFIED |
| OVR anchor pose semantics on tracking loss / unfocused | METADATA | NOT_VERIFIED (wrapper boundary) |
