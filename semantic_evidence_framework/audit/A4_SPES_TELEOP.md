> **Provenance.** This audit was delegated to a read-only subagent on 2026-10-01 under `AUDIT_METHOD.md` and reviewed by the lead auditor. Claims spot-checked against the pinned source by the lead: head-pose fallback (`index.html` L330–346) and jump guard (`__init__.py` L228–266). Other claims carry the subagent's citations and have not been re-read line by line. Treat them as SOURCE_CONFIRMED at the cited lines, subject to re-check before any claim is published. Scratchpad paths (`rtc/`) refer to read-only copies of upstream files fetched by commit.

# Source audit: SpesRobotics/teleop (XR/WebXR → WSS → Python → ROS 2)

## Pins & scope

| Item | Value | Label |
|---|---|---|
| Target commit | `c5d808155a87b584d6147a5943d4b87c34c92db0` ("Document iPhone WebXR setup", 2026-07-17) | SOURCE_CONFIRMED (`git rev-parse HEAD`) |
| Worktree | clean (`git status --porcelain` empty) | SOURCE_CONFIRMED |
| Remote | `origin` = github.com/SpesRobotics/teleop; `git ls-remote origin HEAD` = `c5d8081…`, so the pin matches upstream HEAD on 2026-10-01 | SOURCE_CONFIRMED |
| History | Shallow clone with 1 commit, so the change history was not audited | SOURCE_CONFIRMED |
| Lineage | `gh api repos/SpesRobotics/teleop`: `fork:false`, no parent. PyPI package `teleop` v0.1.5 (`pyproject.toml:6-7`) | SOURCE_CONFIRMED |
| WebXR spec | https://immersive-web.github.io/webxr/ was fetched on 2026-10-01 (the page states "Candidate Recommendation" status). The WebXR Gamepads Module page was also fetched. | SOURCE_CONFIRMED (spec text) |
| OpenXR ref | OpenXR-Docs `5a82d45b`, `spaces.adoc:218-267` (VALID/TRACKED bits), `:205-255` (`XrEventDataReferenceSpaceChangePending.changeTime`), `input.adoc:234,834-860` (`isActive`) | SOURCE_CONFIRMED (spec text). Spes does not use OpenXR directly. |
| Prior internal results | `ros_xr_evidence/.../results/SPES_*.md`, used only as pointers. They agree with the source reading below (semantic collision, reconnect, freshness, control state). | PRIOR_INTERNAL |
| Out of scope | `teleop/key.pem` and `teleop/cert.pem` exist and are used. Their content was not read. | — |

Code locations in scope: `teleop/index.html` (inline JS, WebXR loop), `teleop/assets/teleop-ui.js` (phone DOM UI), `teleop/__init__.py` (FastAPI/WSS server and mapper), and the consumers `teleop/ros2/__main__.py`, `teleop/ros2_ik/__main__.py` with `teleop/utils/jacobi_robot{,_ros}.py`, `teleop/xarm/__main__.py`, `teleop/basic/__main__.py` and `examples/webots/.../inverse_kinematics.py`. `teleop/utils/transform_limiter.py` is not imported by any consumer: NOT_FOUND_IN_SEARCH (queries: `transform_limiter`, `compute_next_transform`).

## Command path table

| # | Hop | Code location | What crosses |
|---|---|---|---|
| H0 | WebXR source | `index.html:284-287` `requestSession('immersive-ar', required local-floor, optional hand-tracking, unbounded, dom-overlay…)`; `:325` `requestReferenceSpace('local-floor')` | XRFrame, `session.inputSources`, `gamepad.buttons/axes` |
| H1 | Source selection | `index.html:254-262` `detectDeviceType` (run on `inputsourceschange`, `:298-301`); `:264-278` `getPoseFromInputSource` (first `handedness==='right' && targetRayMode==='tracked-pointer'`, `frame.getPose(targetRaySpace, ref)`); `:334-353` falls back to `frame.getViewerPose().views[0].transform` | `position`, `orientation` only (`pose.transform.*`) |
| H2 | Controls | VR: `TeleopJoystick.handleControllerInput` `index.html:115-140` (`buttons[1]` sets move, `buttons[0]` toggles gripper, `buttons[4]/[5]` reserved, `axes[0]` scale). Phone: `teleop-ui.js:264-362` (hold-to-move, toggle gripper, slider) | `move`, `gripper`, `scale`, `reservedButtonA/B` |
| H3 | Packet build/send | `index.html:355-381`, throttle `time - lastSendTime > 10` ms; `sendPose` `:241-250` (drops the packet when the socket is not OPEN) | JSON `{type:'pose', data:{position{x,y,z}, orientation{x,y,z,w}, move, gripper, fps, scale, reservedButtonA, reservedButtonB, device:'VR'/'Phone', message}}` |
| H4 | Transport | Browser WSS `wss://host/ws` (`index.html:188-229`, auto-reconnect 3 s `:216`); server `uvicorn` TLS with bundled `key.pem`/`cert.pem`, host `0.0.0.0`, port 4443 (`__init__.py:317-336`); route `/ws` `:297-315` | text frames; no auth |
| H5 | Mapper | `Teleop.__update` `__init__.py:220-285`: RUB→FLU (`TF_RUB2FLU` `:14`, `:237-243`), `@ natural_phone_pose` (`:244`), jump guard (`:246-258`), clutch anchor (`:260-264`), relative delta onto `absolute_pose_init` (`:266-276`), scale (`:271-282`) | 4x4 `self.__pose` plus the raw `message` dict to the subscribers (`:216-218`, `:285`; also on `move=false` `:231-235`) |
| H6a | ROS 2 Cartesian | `ros2/__main__.py:95-141`: TF `base_link→teleop_target` on every callback; `PoseStamped` on `target_frame` (QoS depth 1) `frame_id "link_base"`; one-shot `/current_pose` init `:124-128` | `PoseStamped` (stamp = node clock now) |
| H6b | ROS 2 IK | `ros2_ik/__main__.py:238-251`: `/gripper_command` `String` on every callback; when `move`, `JacobiRobotROS.servo_to_pose(pose, 0.2)` → `JointTrajectory` on `/joint_trajectory` (`jacobi_robot_ros.py:156-206`) | 1-point `JointTrajectory`, positions and velocities, `time_from_start=0.2 s`, header not set |
| H6c | xArm SDK | `xarm/__main__.py:101-105`: `arm.set_servo_cartesian` on every callback; Lite6 gripper | mm/rad Cartesian servo |
| H7 | Final consumer | README: fzi `cartesian_controllers` / MoveIt Servo (H6a), `joint_trajectory_controller` (H6b). Not in this repo. | AUTHOR_CLAIM (`README.md:53`, `:159`) |

## Findings A1–A9

### A1 Focus, session visibility and action-active state
- SOURCE_CONFIRMED: no handling of `XRSession.visibilityState` or `visibilitychange`. NOT_FOUND_IN_SEARCH (queries: `visibilitychange`, `visibilityState`, `blur`, `pagehide` in `index.html` and `teleop-ui.js`). The only session event handled is `end` (`index.html:293-296`), and it only hides the DOM overlay.
- WebXR spec (§ XRSession visibility state): when `hidden`, "requestAnimationFrame() callbacks will not be processed … Input is not processed"; when `visible-blurred`, "rAF MAY be throttled. Input is not processed". "Determine if poses may be reported" returns false only for `hidden`. SOURCE_CONFIRMED (spec).
- HYPOTHESIS: when `hidden`, the rAF loop (`:328-388`) stops, so no packets are sent. When `visible-blurred`, rAF may still run, and the controller pose may become null. In that case the code falls back to the viewer pose (`:340-346`) while `moveButtonPressed` keeps its last value. The runtime behaviour on Quest was NOT_VERIFIED here.
- SOURCE_CONFIRMED: no session, focus or active field crosses H3. The server and ROS hops have no such input.
- SOURCE_CONFIRMED: the WebXR `select*`/`squeeze*` events and `gamepad.mapping` are not used. Buttons are polled directly by index (`index.html:120-136`). NOT_FOUND_IN_SEARCH (queries: `squeeze`, `selectstart`, `mapping`).

### A2 Valid vs tracked
- SOURCE_CONFIRMED: `XRPose.emulatedPosition` is never read. NOT_FOUND_IN_SEARCH (query: `emulatedPosition`). Only `pose.transform.position/orientation` is copied (`index.html:268-273`, `:343-344`, `:350-351`).
- WebXR spec (§ Populate the pose): for an untracked or 3DoF position, the UA uses an emulated or last-known position and sets `emulatedPosition=true`. OpenXR equivalent: VALID without TRACKED (`spaces.adoc:218-221`). SOURCE_CONFIRMED (spec).
- SOURCE_CONFIRMED: a null controller pose silently selects the head (viewer) pose in VR mode (`index.html:337-346`). The packet `device` stays `'VR'` (`:377`), so the server cannot tell controller from viewer. PRIOR_INTERNAL: SPES_SEMANTIC_COLLISION found the packets byte-identical, and SPES_QUEST_HW_RESULT observed `emulatedPosition=true` on Quest 3 in 5 of 5 trials with motion continuing.
- SOURCE_CONFIRMED (existing guard): the server jump guard rejects a single sample when the delta from the previous received pose exceeds 5 cm or 35° (`__init__.py:246-257`). On reject it clears `relative_pose_init` and returns without notifying. The next nearby sample re-anchors (`:261-264`), and the sample after that is compared against `previous_received_pose=None` (`:264`, `:247`), so it is unguarded. The guard is a discontinuity filter, not a validity gate.

### A3 Buttons, toggle, clutch, deadman
- SOURCE_CONFIRMED (VR, move/clutch): the move button is level-polled each frame (`index.html:120-124`), but only while a right gamepad input source is present (`:118`). Otherwise `moveButtonPressed` keeps its last value.
- SOURCE_CONFIRMED (VR, gripper): the gripper is a toggle latched in `TeleopJoystick.gripper` (`:108`, `:126-129`). Edge detection uses an expando `wasPressed` on the `GamepadButton` object. HYPOTHESIS: if the UA returns fresh button objects each frame, the gripper would toggle every frame. The latch is never reset on session end, input-source change or socket close: NOT_FOUND_IN_SEARCH (queries: `gripper =`, `reset`).
- SOURCE_CONFIRMED (phone): motion is hold-to-move. It starts on `mousedown`/`touchstart` on the button and ends on document `mouseup`/`touchend` (`teleop-ui.js:291-312`, `:349-352`). `touchcancel` is not handled: NOT_FOUND_IN_SEARCH (query: `touchcancel`). HYPOTHESIS: a cancelled touch (system gesture, overlay) leaves `motionEnabled=true`. `TeleopUI` state (`motionEnabled`, `gripperEngaged`) survives session end and restart (`index.html:293-296` does not reset it).
- SOURCE_CONFIRMED (server, existing policy): `move=false` clears `relative_pose_init` and `absolute_pose_init` (`__init__.py:231-235`), so the next engage re-anchors. This is a working clutch. `previous_received_pose` is not cleared there (PRIOR_INTERNAL SPES_CONTROL_STATE_RESULT agrees).
- SOURCE_CONFIRMED: the re-anchor base is `self.__pose` (`:263`), which is the last commanded target, not the measured robot pose. `set_pose` is called once at startup in every consumer:
  - `ros2/__main__.py:124-128` (`pose_initiated` is never reset)
  - `ros2_ik/__main__.py:234-236`
  - `xarm/__main__.py:108`
  - webots `:66-67`

  This contradicts README `:64` (`current_pose` "Used to update the reference pose"), which is an AUTHOR_CLAIM, because the code applies it only once. This is a known application-level re-anchor issue.
- SOURCE_CONFIRMED (consumer gating differs):
  - ros2 publishes `target_frame` on every callback, including `move=false` (held pose), after init (`ros2/__main__.py:121-141`).
  - ros2_ik publishes trajectories only when `move` (`:248-251`), but publishes the gripper always (`:243`).
  - xarm servos on every callback (`xarm:101-102`).
  - webots servos while the last `move` was true (`webots:46-52,73-75`).
- SOURCE_CONFIRMED (xArm gripper mapping): `'close'` becomes 1.0, and `set_gripper_state` calls `open()` when the value is ≥1.0 (`xarm/__main__.py:104`, `:40-46`). The default client state is `'open'`, so the first callback calls `close()`, because `prev is None` triggers a command (`:36-42`). HYPOTHESIS: the inversion may be intended for Lite6 semantics.

### A4 Input source, hand vs controller
- SOURCE_CONFIRMED: `inputsourceschange` is handled, but only to recompute `isVRDevice` (`index.html:298-301`). `event.added`/`event.removed` are not inspected, and server-side anchors are not invalidated. When the right controller disappears, `isVRDevice` becomes false, so `teleopFrontEnd` switches to `teleopUI` (`:357`). `move` then comes from the DOM button, which is normally false. This acts as an accidental disengage, and it relies on the event firing.
- SOURCE_CONFIRMED: hands and controllers are not distinguished (no `inputSource.hand` check). Any right `tracked-pointer` is accepted (`:257`, `:267`), and button semantics assume xr-standard indices. The Gamepads Module lists `buttons[0]` as trigger and `buttons[1]` as squeeze; `[4]/[5]` are not in the xr-standard table (SOURCE_CONFIRMED, spec). `axes[0]` is touchpad X, which on touchpad-less controllers is a placeholder reporting 0, so VR scale stays at 1.0 (HYPOTHESIS).
- SOURCE_CONFIRMED: there is no source-generation field in the packet. PRIOR_INTERNAL SPES_NETWORK_COMPOSITION/CONTROL_STATE C3: a controller→viewer switch is rejected once by the jump guard and then accepted.

### A5 Origin, recenter and `reset`
- SOURCE_CONFIRMED: no `XRReferenceSpace` `reset` handler. NOT_FOUND_IN_SEARCH (queries: `onreset`, `'reset'`, `addEventListener('reset'`). `XRReferenceSpaceEvent.transform` is unused.
- WebXR spec (§ XRReferenceSpace / reset): reset "MUST be dispatched prior to the execution of any XR animation frames that make use of the new origin". OpenXR equivalent: `changeTime` (`spaces.adoc:205-208`). SOURCE_CONFIRMED (spec).
- HYPOTHESIS: a recenter during `move=true` appears to the server only as a pose discontinuity. It is caught by the jump guard if it exceeds 5 cm or 35°, and then re-anchored. A smaller recenter passes into the target. The effective-time information is discarded at H1.

### A6 Calibration, anchor and transform application
- SOURCE_CONFIRMED: the transforms applied are the constants `TF_RUB2FLU` and `natural_phone_pose` (CLI `--natural-position/--natural-orientation`, fixed at construction, `__init__.py:174-182`). Both apply to each received sample in arrival order (`:240-244`). There is no runtime calibration update and no time-indexed transform. The anchor `relative_pose_init` is the first engaged sample after clear or jump (`:261-264`). Every later sample is differenced against it, at arrival time.
- SOURCE_CONFIRMED: `scale` comes from the client and is not bounded server-side. When >1, it multiplies the translation only (`:271-272`). When <1, it uses SLERP with `assert 0<=alpha<=1` (`__init__.py:95`, `:279-282`), so a negative scale raises an AssertionError inside the WS loop.
- SOURCE_CONFIRMED: frame naming is inconsistent in ros2. TF uses `frame_id "base_link"` (`ros2/__main__.py:104`), while `target_frame` uses `"link_base"` (`:132`). The incoming `/current_pose` header frame is ignored (`ros2numpy` uses `.pose` only, `:16-40`, `:125`).
- SOURCE_CONFIRMED (ros2_ik): `JacobiRobotROS` accepts `/joint_states` once (`jacobi_robot_ros.py:136-139` returns early once received). After that, `servo_to_pose` integrates its own model open-loop (`jacobi_robot.py` `update_state:327-336`, `q += dq*dt`). `prev_linear_vel`/`prev_angular_vel` (`jacobi_robot.py:104,278-279`) persist across disengage periods, because ros2_ik skips servo when `move=false`.

### A7 Disconnect, reconnect, pause and resume
- SOURCE_CONFIRMED (client): `onclose` reconnects with `setTimeout(connectWebSocket, 3000)` (`index.html:207-217`). While disconnected, packets are dropped, not queued (`:241-249`). The XR session and controls state are untouched. After reconnect, sending resumes with the current `move`, with no re-arm.
- SOURCE_CONFIRMED (server): `WebSocketDisconnect` only removes the connection and logs (`__init__.py:313-315`). `Teleop` anchors are instance state shared by all connections (`:168-172`) and are not reset on disconnect. Several simultaneous clients would all feed the same `__update`. Other exceptions (JSON, KeyError, AssertionError) exit the handler without `manager.disconnect` (`:302-315`). PRIOR_INTERNAL SPES_RECONNECT_RESULT R1: near reconnect continued with no re-arm. R2: far reconnect was rejected once and then re-anchored.
- SOURCE_CONFIRMED (consumers): there is no watchdog or timeout in any Spes consumer. NOT_FOUND_IN_SEARCH (queries: `timeout`, `watchdog`, `create_timer` in `teleop/`). ros2 publishes only from the callback, so a stalled source means the last `target_frame` stands. Whether a stale target is held or timed out is up to the external controller (NOT_VERIFIED, not in repo).
- Pause/resume: see A1. There is no XR visibility handling. A session `end` followed by Start creates a new session and adds another `exit` listener per Start (`index.html:289-291`).

### A8 Pending commands, previous goal and auto-resume
- SOURCE_CONFIRMED: there is no queue in the client or server. The ros2 publishers use QoS depth 1 (`ros2/__main__.py:88`, `jacobi_robot_ros.py:85-87`). ros2_ik sends a single-point `JointTrajectory` with `time_from_start = 0.2 s` (`ros2_ik:251` → `jacobi_robot_ros.py:178-180`) and an unset header stamp (`:166-181`). HYPOTHESIS: a zero stamp means "start now" for JTC (NOT_VERIFIED). The last goal therefore completes within about 0.2 s and is held. When `servo_to_pose` hits the "Excessive joint velocities" path it returns False without integrating (`jacobi_robot.py:310-313`), yet the wrapper still publishes, because only `None` is treated as failure (`jacobi_robot_ros.py:197-206`). The result is the unchanged `q` with the previous `dq` velocities.
- SOURCE_CONFIRMED (auto-resume): after reconnect, visibility resume or source switch with `move=true`, motion resumes from the retained anchor, or from a re-anchor after one rejected sample (A2/A7). The only path that requires an explicit re-engage is `move=false` (A3).
- SOURCE_CONFIRMED: the webots example keeps `target_pose` and servos to it every sim step while the last message had `move=true` (`webots:46-52,73-75`). It converges to the last target, with no timeout.

### A9 Source-to-command lineage
- SOURCE_CONFIRMED: the packet carries no sequence id, no XR frame `time` or `predictedDisplayTime` equivalent, and no session or connection id (`index.html:359-379`). The rAF `time` is used only for throttling (`:356-358`). `fps` and `message` are diagnostic only.
- SOURCE_CONFIRMED: ROS stamps are generated at publish time (`ros2/__main__.py:103,131`). The JointTrajectory header is unset. `/gripper_command` is a bare `String`. A consumed command cannot be linked to its source sample from the message contents. Timing correlation is the only option. PRIOR_INTERNAL SPES_FRESHNESS_RESULT: delayed samples were accepted with no age check.

### Security notes (SOURCE_CONFIRMED)
- The TLS private key ships in the repo and package (`teleop/key.pem`), and `run()` uses it (`__init__.py:326-334`). Every installation shares the same key, so TLS gives no confidentiality or authenticity against anyone with the public repo. Content not inspected.
- The server binds `0.0.0.0:4443` with no authentication or origin check on `/ws` (`__init__.py:297-309`). Any LAN client can send `type:'pose'` and drive the shared state. Inputs (`scale`, missing keys, non-finite numbers) are not validated (`:221-229`).
- In the ros2 path, `rclpy.spin_once(node, 0.01)` runs inside the async WS handler (`ros2/__main__.py:116-119`). This blocks the event loop for up to 10 ms per message (latency HYPOTHESIS).

## Information-delivery table (evidence × hop)

Y = present or used, — = not present, P = partial or indirect.

| Evidence | H0 WebXR (spec) | H1/H2 JS read | H3 packet | H5 mapper | H6 ROS msg | H7 consumer |
|---|---|---|---|---|---|---|
| visibilityState / visibilitychange | Y | — | — | — | — | — |
| session end | Y | P (hides UI) | — | — | — | — |
| emulatedPosition / VALID vs TRACKED | Y | — | — | P (jump guard only) | — | — |
| null pose → viewer fallback | Y | Y (silent) | — (`device` unchanged) | P (jump guard) | — | — |
| input source identity / add-remove | Y | P (`isVRDevice`) | P (`device` VR/Phone) | — | — | — |
| move / clutch | Y (buttons) | Y | Y `move` | Y (anchor clear) | P (ros2 publishes regardless; ros2_ik gates) | — |
| gripper | Y | Y (latched toggle) | Y `gripper` | passthrough | Y (ros2_ik String, xarm SDK); — (ros2) | ? |
| reset / recenter + effective time | Y | — | — | P (jump guard) | — | — |
| calibration transform | n/a | — | — | Y (constant, at arrival) | — | — |
| robot measured pose for anchor | n/a | n/a | n/a | P (once at startup) | P (`/current_pose` once) | — |
| source timestamp / seq | Y (frame time) | P (throttle only) | — | — | — (now() stamps) | — |
| connection / session generation | n/a | P (`isConnected`) | — | — | — | — |

## Candidate matrix rows

| Item | Class candidate | Label |
|---|---|---|
| `emulatedPosition` not read; valid/emulated/viewer-fallback collapse to the same packet (`index.html:264-381`) | METADATA | SOURCE_CONFIRMED |
| Silent controller→viewer (head) pose fallback while `move` is held (`index.html:337-346`) | IMPLEMENTATION | SOURCE_CONFIRMED (Quest activation PRIOR_INTERNAL) |
| No `visibilitychange` / `visibilityState` handling (`index.html`) | INTEGRATION | SOURCE_CONFIRMED (absence by search); runtime effect HYPOTHESIS |
| No `reset` handler; recenter effective time lost (`index.html:325-326`) | INTEGRATION | SOURCE_CONFIRMED (search) |
| `inputsourceschange` only toggles `isVRDevice`; no anchor invalidation and no hand/controller distinction (`index.html:298-301`) | INTEGRATION | SOURCE_CONFIRMED |
| No seq or source stamp in the packet; ROS stamps from now() (`index.html:359-379`, `ros2/__main__.py:103,131`) | METADATA | SOURCE_CONFIRMED |
| Server anchors not reset on WS disconnect; shared across clients; auto-resume (`__init__.py:168-172,313-315`) | PLACEMENT | SOURCE_CONFIRMED |
| Jump guard is a single-sample reject, then auto re-anchor; the post-anchor sample is unguarded (`__init__.py:246-264`) | IMPLEMENTATION | SOURCE_CONFIRMED |
| Re-anchor base is the last command, not the measured robot pose; `/current_pose` used once despite README (`__init__.py:263`, `ros2/__main__.py:124-128`) | APPLICATION (known issue) | SOURCE_CONFIRMED vs AUTHOR_CLAIM |
| Gripper toggle latched, never reset; per-frame expando edge detection (`index.html:126-129`) | IMPLEMENTATION | SOURCE_CONFIRMED (latch); HYPOTHESIS (expando) |
| Phone `touchcancel` not handled (`teleop-ui.js:349-352`) | IMPLEMENTATION | SOURCE_CONFIRMED (search); effect HYPOTHESIS |
| ros2 publishes the held target even when `move=false`; ros2_ik gates on `move` (consumer inconsistency) | APPLICATION | SOURCE_CONFIRMED |
| ros2 frame-id mismatch `base_link` vs `link_base` (`ros2/__main__.py:104,132`) | INTEGRATION | SOURCE_CONFIRMED |
| ros2_ik open-loop model after the first `/joint_states`; stale accel state across disengage (`jacobi_robot_ros.py:136-139`, `jacobi_robot.py:104,278`) | IMPLEMENTATION | SOURCE_CONFIRMED |
| ros2_ik publishes after the "excessive velocity" early return (`jacobi_robot_ros.py:197-206`) | IMPLEMENTATION | SOURCE_CONFIRMED |
| No consumer-side timeout or watchdog in Spes; stale-target handling deferred to the external controller | PLACEMENT | SOURCE_CONFIRMED (search) / NOT_VERIFIED (external) |
| Bundled shared TLS private key; no auth on `/ws`; unvalidated `scale` (`__init__.py:221-229,297-334`) | IMPLEMENTATION (security) | SOURCE_CONFIRMED |
| xArm gripper close→`open()` mapping; first-message actuation (`xarm/__main__.py:36-46,104`) | APPLICATION | SOURCE_CONFIRMED (code); intent HYPOTHESIS |
| End-to-end runtime of these paths on Quest + ROS controller | OBSERVATION | PRIOR_INTERNAL partial; otherwise NOT_VERIFIED |
