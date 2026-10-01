# A1 — OpenVR UR5e (Quest 3 → ALVR → SteamVR → OpenVR → `quest_teleop.py` → MoveIt Servo → Gazebo)

Audited 2026-10-01. Method: `AUDIT_METHOD.md`. Labels: `../docs/02_REQUIREMENTS_AND_THREAT_MODEL.md` §4.

## Pins

| Component | Pin | Where |
|---|---|---|
| Target app | `mrutyunjaykalyani/teleoperation-of-a-UR5e-robot-in-Gazebo-using-Meta-Quest-3-via-ROS2-bridge-jazzy-` @ `170dad582d624f536359a3192a7f829669c2b031`; this equals remote HEAD (checked 2026-10-01); clean | `/home/cclab/ros_xr/Deprecated/semantic_validation/targets/openvr_ur5e_jazzy` |
| ALVR | `alvr-org/ALVR` @ `9f11839431f95f0df6764790d9a16f8e308a0d79` (HEAD 2026-10-01) | `../references/upstream/ALVR` |
| OpenVR API header | `ValveSoftware/openvr` @ `0924064316de3effbcd1acf1e309182a2deb1c05` (v2.15.6) | `../references/upstream/openvr/headers/openvr.h` |
| MoveIt Servo | `moveit/moveit2` tag `2.12.4` @ `1ade0e9d`; this is the version in `openvr-jazzy-sim:local` (`ros-jazzy-moveit-servo 2.12.4`) | `../references/upstream/moveit2_2.12.4` |
| OpenXR spec | `KhronosGroup/OpenXR-Docs` `release-1.1.63` @ `5a82d45b` | `../references/upstream/OpenXR-Docs` |

**Scope limits.**

- The README names ALVR but does not pin a version. Whether the author's ALVR version behaves like
  HEAD is **NOT_VERIFIED**.
- Meta's Quest OpenXR runtime is closed source. Its behaviour is taken from the spec only; actual
  conformance is **NOT_VERIFIED**.
- SteamVR's mapping from driver input components to the legacy `GetControllerState` is closed
  source and **NOT_VERIFIED**.

## Command path

| Hop | Code | What crosses the hop |
|---|---|---|
| 1. Quest OpenXR runtime | closed | action states, `XrSpaceLocation` flags, session state, `XrEventDataReferenceSpaceChangePending` |
| 2. ALVR client (OpenXR app on the headset) | `client_openxr/src/interaction.rs` (`get_hand_data` ≈L777–870, `update_buttons` L919–950), `lib.rs` L422–470, `stream.rs` L255–290, L549, L665–669 | controller motion (pose plus velocity), only when the grip-pose action `is_active`; **button entries only when `changed_since_last_sync`**; `PlayspaceSync` on reference-space change |
| 3. ALVR server core | `server_core/src/connection.rs` L1267–1290 (PlayspaceSync → `recenter()`), L1317– (Buttons); `tracking/mod.rs` L74–115 | recentred poses; button values |
| 4. ALVR OpenVR driver | `server_openvr/cpp/alvr_server/Controller.cpp` `SetButton` L142–172, `OnPoseUpdate` L175–205 | `DriverPose_t{poseIsValid, deviceIsConnected, result}`; `UpdateBooleanComponent` |
| 5. SteamVR → OpenVR client API | closed | `TrackedDevicePose_t{mDeviceToAbsoluteTracking, eTrackingResult, bPoseIsValid, bDeviceIsConnected}`; `VRControllerState_t.ulButtonPressed` |
| 6. `quest_teleop.py` (ROS node) | `src/quest_bridge/quest_bridge/quest_teleop.py` L40–103 | `geometry_msgs/PoseStamped` on `/servo_node/pose_target_cmds`, frame `base_link`, stamp `now()` |
| 7. MoveIt Servo 2.12.4 (`servo_node`) | `moveit_ros/moveit_servo/src/servo_node.cpp` `poseCallback` L209–213, `processPoseCommand` L289–318, `servoLoop` L360–430; `servo.cpp` `getPlanningToCommandFrameTransform` L551–570 | `trajectory_msgs/JointTrajectory` → `/ur5_arm_controller/joint_trajectory` (config `src/ur5_moveit_config/config/ur_servo.yaml`) |
| 8. ros2_control JTC → Gazebo | config | joint motion |

## Item-by-item findings

### A1 — focus/session, action active

- **Spec, SOURCE_CONFIRMED.** When the session is not focused, `xrSyncActions` returns
  `XR_SESSION_NOT_FOCUSED` and all action states are inactive (`input.adoc` L1344–1346, L839–841). For
  an inactive action, state = 0/false, **`changedSinceLastSync = XR_FALSE`**, and `lastChangeTime = 0`
  (L864–866). If the action was inactive at the previous sync, `changedSinceLastSync` is again `XR_FALSE`
  (L857–858).
- **ALVR client, SOURCE_CONFIRMED.**
  - Buttons are forwarded only on `state.changed_since_last_sync` (`interaction.rs` L931, L943). The
    `is_active` state of button actions is not forwarded.
  - The pose is sent only while the grip-pose action is active (`interaction.rs` L787–791).
  - Session states `READY`, `STOPPING`, `EXITING` and `LOSS_PENDING` are handled (`lib.rs` L422–446).
    In a search for `FOCUSED|VISIBLE|is_active` on button actions, `VISIBLE` and `FOCUSED` were
    **NOT_FOUND_IN_SEARCH**.
- **ALVR driver, SOURCE_CONFIRMED.**
  - No controller motion → `poseIsValid = deviceIsConnected = false`, `result = Uninitialized`
    (`Controller.cpp` L199–205).
  - `SetButton` returns early while the pose is invalid (L145–147). Nothing resets the button components.
- **Consequence (HYPOTHESIS H-A1, code-derived, not observed).**
  1. While grip is held, focus is lost, e.g. the system menu opens. The pose goes invalid. No release
     edge can be generated: the spec forbids `changedSinceLastSync = true` across the inactive interval.
  2. SteamVR's grip component stays at the last value forwarded, *pressed*.
  3. On refocus, the first sync again reports `changedSinceLastSync = false`. Grip therefore stays
     *pressed* until the user next physically changes it.
  4. `quest_teleop.py` sees a valid pose plus grip pressed. Its `first_packet` was not reset during the
     invalid interval (L49 skips, L55–59 not reached), so the robot follows the hand with the
     **pre-interruption offset** and without a current deadman press.
- **Limits of H-A1.** Steps 2–3 depend on the closed SteamVR and Quest runtimes (NOT_VERIFIED). A
  hardware run is needed to confirm. **On the ROS side, the consumption of such a stale grip is directly
  testable with the fake OpenVR module.** The existing harness is
  `Deprecated/semantic_validation/harness/openvr_ur5e_downstream/openvr.py` (`OPENVR_FAKE_GRIP_SEQUENCE`).
- **Relation to S5.**
  - S5 W4/W5 covered validity loss followed by R_AUTO resume, and the absolute re-reference (#10,
    APPLICATION).
  - H-A1 differs in its *evidence source*. The resume is driven by a deadman value that the middleware
    holds over from a different interval, not by a fresh press.
  - The S5 re-arm logic (rising edge plus dwell) at the ROS side would also block it, **if** the ROS
    side could observe a rising edge. Here it cannot: the cached value never falls. Possible defenses,
    in the order of what they need:
    1. ALVR emits a release for every held button when actions go inactive or the session leaves
       FOCUSED. This is a one-place fix at hop 2 (IMPLEMENTATION class).
    2. Or the ROS side requires a fresh rising edge after any `bPoseIsValid` false→true transition.
       This is S5-style re-arm with the edge defined on the validity transition, not on the button.

### A2 — valid vs tracked

- ALVR forwards a pose when `ORIENTATION_VALID` / `POSITION_VALID` are set. It never reads the
  `*_TRACKED_BIT`s, and it **holds the last value** for invalid components (`interaction.rs` L793–806).
  Per the spec, a valid-but-untracked position may be inferred or last-known (`spaces.adoc` L833–856).
  - The driver sets `result = TrackingResult_Running_OK` for every forwarded pose (`Controller.cpp`
    L205), so the tracked/untracked distinction is **lost at hop 2/4**. SOURCE_CONFIRMED.
- `quest_teleop.py` checks only `bPoseIsValid` (L49). It ignores `eTrackingResult` and
  `bDeviceIsConnected`. SOURCE_CONFIRMED; PRIOR_INTERNAL S5 #3 (METADATA, "the original ignores a
  native field").
- **Conclusion.** Even an app that read `eTrackingResult` would receive `Running_OK` for inferred
  poses on this path. The tracked bit is not delivered: this is METADATA loss in the middleware. An
  `eTrackingResult` check at hop 6 is therefore not sufficient on ALVR. It would be sufficient on a
  driver that reports `Running_OutOfRange`, which is the case S5 W2 emulated.

### A3 — buttons, deadman, caching

- **Deadman.** Right grip, level-sensitive, read every 50 ms from `ulButtonPressed` (L52–53). Release
  sets `first_packet = True` and returns **without publishing anything** (L55–59). There is no explicit
  stop or hold.
- **Consumer, SOURCE_CONFIRMED.** Servo keeps processing `latest_pose_` while
  `now − header.stamp < incoming_command_timeout`. Here the timeout is 0.5 s (`ur_servo.yaml` L14).
  `new_pose_msg_` is not cleared on success (`servo_node.cpp` L297–306). Only after the timeout does it
  `smoothHalt` (L308–316).
  - **Consequence.** After grip release the arm keeps tracking the *last* target for up to 0.5 s. The
    README's claim "RELEASE GRIP: Robot stops" (AUTHOR_CLAIM) is bounded by that timeout, not by the
    release.
  - Whether the arm moves noticeably in that window depends on how far the last target is from the
    current pose. That is **testable** (pilot P-A, ROS side).
- The `getControllerState` return value is discarded (L52). If it is false, `state` is the zeroed or
  stale struct passed by the binding, so the deadman is read as released. For this field that is
  fail-safe (NOT_VERIFIED for pyopenvr's struct handling).

### A4 — device / interaction-profile change

- ALVR ignores `InteractionProfileChanged` (`lib.rs` ≈L468–470, matched with `PassthroughStateChangedFB`
  → no-op).
- `quest_teleop.py` selects the controller by `TrackedControllerRole_RightHand` on every poll
  (L45–49), so a role swap re-targets silently. VREvent_TrackedDeviceRoleChanged is not polled.
- No offset reset happens on a device change. **Only if** the role moves to a different physical device
  while grip is held does the old offset get applied to the new device's raw pose. HYPOTHESIS, low
  practical relevance: with two Quest controllers, a role swap needs a runtime reassignment
  (NOT_VERIFIED).

### A5 — origin change and effective time

- **The app uses `TrackingUniverseRawAndUncalibrated`** (L43). The header says: "Poses are provided in the
  coordinate system defined by the driver … You usually don't want this one" (`openvr.h` L368). SteamVR
  seated/standing recentering therefore does **not** change the poses this app reads. The app polls no
  events (`PollNextEvent` / `VREvent_*`: no matches in `quest_teleop.py`).
- **The driver coordinate system itself changes on an ALVR recenter.**
  1. The Quest `ReferenceSpaceChangePending` makes the ALVR client recreate its spaces and send
     `PlayspaceSync` (`lib.rs` L448–458; `stream.rs` L255–272).
  2. On receipt, the server recomputes `inverse_recentering_origin` from the **last head pose**. The
     default mode is `LocalFloor` (`settings.rs` L2185–2188; `tracking/mod.rs` L74–107).
  3. That transform is applied to every subsequent pose (`recenter_pose`, L109–111).
  - The event's `changeTime` / `poseValid` / `poseInPreviousSpace` (`spaces.adoc` L395–403) are **not
    used**: a search for `change_time` gave no matches.
  - SteamVR receives only `SetChaperoneArea` (`server_openvr/src/lib.rs` L282–284), not a pose
    discontinuity marker.
- **Consequence (HYPOTHESIS H-B1).** During an engaged teleop, a headset recenter shifts and yaw-rotates
  the raw controller pose. `quest_teleop.py` subtracts the offset captured before the change from a pose
  expressed after it (L86–92). The robot target jumps by `0.5 ×` the recenter displacement. Two intervals
  mix here: a pre-change offset is combined with a post-change pose.
  - There is a second, smaller mix inside ALVR. Motion packets sampled before the client recreated
    its space but processed after `recenter()` get the new transform (HYPOTHESIS; it needs the timing of
    `input_thread` restart vs. packet flight).
- **What is already solved by conventional means.** The fixes are standard and local to the app:
  1. Treat any discontinuity as a disengage and re-capture the offset (the S5 #10 class fix,
     re-anchor on engage).
  2. Or have the middleware forward a recenter epoch.

  Neither the app nor ALVR exposes the effective time. The ROS side cannot distinguish a recenter jump
  from fast motion **unless** an epoch or event is forwarded. A velocity/jump limit is a heuristic
  substitute, with false blocks.

### A6 — calibration/anchor and the transform actually used

- App calibration = `offset_{x,y,z}`, `offset_rot_inv`, captured on the first gripped valid sample
  (L73–77). These are used for every subsequent sample until release (L86–95). The base pose (0.4, 0, 0.3)
  and `robot_home_rot` are fixed constants (L32, L86–88). This is the S5 #10 absolute re-reference
  (PRIOR_INTERNAL; APPLICATION; not re-proposed).
- Command frame `base_link`. Servo transforms to the planning frame through `robot_state` if the frame is
  known. Otherwise it uses `tf lookupTransform(planning, command, rclcpp::Time(0))` (`servo.cpp` L555–565),
  the **latest** transform and not the command stamp. On this path `base_link` is a robot link, so no XR
  transform passes through tf. That Servo behaviour matters for implementations that publish XR frames
  into tf (see A2 Quest2ROS2 and others).

### A7 — disconnect/reconnect, pause/resume

- On disconnect the ALVR driver reports invalid/disconnected (`Controller.cpp` L203–205). The app stops
  publishing without resetting `first_packet` (L49). Servo halts after 0.5 s (A3).
- On reconnect with grip held (or cached, see A1), the app resumes with the **old offset**. PRIOR_INTERNAL
  S5 W5: all arms fail R8, APPLICATION.

### A8 — pending commands, previous goal, resume

- Servo has no queue for pose commands, only `latest_pose_`. The JTC receives a rolling window of
  trajectory points (`updateSlidingWindow`, `max_expected_latency` 0.1 s). Points already sent can
  execute for up to that window after Servo stops publishing. NOT_VERIFIED quantitatively here;
  PRIOR_INTERNAL S5 measured settle ≤ 1 s with a stop adapter.

### A9 — source → command → consumer linkage

- `PoseStamped` carries no source sequence or source time: the stamp is the publish `now()`, L81.
  Linkage from the OpenVR sample to the Servo command is only by timing.
- PRIOR_INTERNAL S5 achieved exact linkage up to Servo `poseCallback` only by harness instrumentation
  (450/450). Servo output → joint remained UNKNOWN_INTERVAL_ONLY.

## Information-delivery table (what each hop knows)

| Evidence | Spec/runtime (1) | ALVR client (2) | ALVR server/driver (3–4) | OpenVR API (5) | App (6) | Servo (7) |
|---|---|---|---|---|---|---|
| action active / focus | yes | read for pose action only | not received | — (`IsInputAvailable` exists, header L2594–2596) | not read | — |
| deadman level | yes | edges only | last value held | `ulButtonPressed` (possibly stale; NOT_VERIFIED) | read | — |
| valid | yes | read | → `poseIsValid` | `bPoseIsValid` | read | — |
| tracked | yes | **dropped** | `Running_OK` constant | `eTrackingResult` (uninformative here) | not read | — |
| origin-change event + `changeTime` | yes | event read, `changeTime` dropped | recenter at receipt | `VREvent_*` not emitted for raw universe (NOT_VERIFIED) | not read | — |
| applied calibration | — | — | `inverse_recentering_origin` | — | offset (local) | — |
| sample time | `XrTime` | yes | yes (`targetTimestampNs`) | `predictedSecondsFromNow = 0` | replaced by `now()` | stamp used for staleness only |
| target arm | right-hand role | — | device id | role | right role only | `ur5_arm` group |

## Summary for the matrix

| Item | Classification candidate | Label |
|---|---|---|
| Release → motion continues ≤ 0.5 s (Servo timeout) | INTEGRATION; conventional fixes are an explicit hold/stop on release or a shorter timeout | SOURCE_CONFIRMED; magnitude to be measured |
| Cached deadman across focus loss (H-A1) | METADATA/IMPLEMENTATION in the middleware (edge-only forwarding plus the spec's inactive semantics) | HYPOTHESIS (hops 2 and 4 SOURCE_CONFIRMED; hops 1 and 5 NOT_VERIFIED) |
| Tracked bit lost | METADATA (middleware) | SOURCE_CONFIRMED |
| Recenter during engage → jump (H-B1) | interval mixing; the conventional fix is re-anchor-on-discontinuity / epoch forwarding | HYPOTHESIS (hops 2–3 and 6 SOURCE_CONFIRMED) |
| Absolute re-reference on resume | APPLICATION (S5 #10) | PRIOR_INTERNAL; not re-proposed |

## Prior reports searched (2026-10-01)

`gh search issues --repo alvr-org/ALVR` was run with these queries: "stuck button", "button stuck menu",
"grip stuck", "buttons stuck after", "focus lost button", "stuck", "held down", "keeps pressed",
"oculus menu input", "trigger stays pressed" and "recenter controller jump". None returned a
matching report. Result: NOT_FOUND_IN_SEARCH. This is not evidence that the issue was never reported
or never observed.
