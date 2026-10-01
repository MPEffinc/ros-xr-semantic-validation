> **Provenance.** This audit was delegated to a read-only subagent on 2026-10-01 under `AUDIT_METHOD.md` and reviewed by the lead auditor. Claims spot-checked against the pinned source by the lead: clutch and stream-freshness logic (`openarmx_teleop_vr_node.py` L398–440), rate fan-out to both hands (bridge `.cpp` L530–539), TRANSIENT_LOCAL IK override (`.py` L560–573). Other claims carry the subagent's citations and have not been re-read line by line. Treat them as SOURCE_CONFIRMED at the cited lines, subject to re-check before any claim is published. Scratchpad paths (`rtc/`) refer to read-only copies of upstream files fetched by commit.

# OpenArmX VR teleop: source-level safety audit (A1–A9)

**Target commit:** `openarmx/openarmx_teleop_vr` @ `a3da7411b3d6ecaa7f94df859e07fb642aec859b` (default branch `6.0_basic`)

## 1. Pins & scope

| Item | Value | Label |
|---|---|---|
| Local checkout | `/home/cclab/ros_xr/Deprecated/semantic_validation/targets/openarmx_teleop_vr`. `rev-parse HEAD` = a3da741…; `status --porcelain` is empty (clean); `ls-remote origin HEAD` = a3da741… (matches) | SOURCE_CONFIRMED |
| Lineage | `gh repo view`: `isFork=false`, `parent=null`. The wire format is a custom ASCII UDP protocol. It is not the XRoboToolkit binary protocol. Topic names `pico_*` refer to the device and do not show code lineage. PRIOR_INTERNAL `FRAMEWORK_LINEAGE_MATRIX.md:16` agrees (no fork evidence) | SOURCE_CONFIRMED (no fork) / HYPOTHESIS (no hidden lineage) |
| XR frontend | `openarmx/openarmx_teleop_vr_apk` @ `27808afdb01dd49e04d5c298c5666c6c91d5d2dc`. The repo holds only binaries (`openarmx_vr_pico.apk`, `openarmx-vr-quest.apk`) plus README/LICENSE, with no source. README says it "captures OpenXR headset and controller data", supports Gripper Mode (AIM) and Hand Mode (GRIP), and sends to UDP 5100. Not decompiled | **NOT_VERIFIED** (frontend), AUTHOR_CLAIM (README) |
| IK/mapper core | `openarmx_arm_driver._lib.teleop_core.PinocchioTeleopCore` (imported at `openarmx_teleop_vr_node.py:11-17`). The docstring says "wraps the closed teleop core" (`:2`, `:26`). NOT_FOUND_IN_SEARCH (queries: `gh repo view openarmx/openarmx_arm_driver`, `openarmx_ros2` tree grep `arm_driver`, org repo list). PRIOR_INTERNAL E2 run hit `ModuleNotFoundError` (`runs/openarmx_udp_e2_20260914_01/downstream_attempt.log`) | Audit stops at wrapper boundary |
| Consumer | `openarmx/openarmx_ros2` @ `bc45d1a6c8e0474e0530a7ba924ae14c2b43cc5a`, `openarmx_bringup/config/v10_controllers/openarmx_v10_bimanual_controllers.yaml:21-22,33-34,55-66,127-138`. `{left,right}_forward_position_controller` = `forward_command_controller/ForwardCommandController`, 8 joints (7 arm + `finger_joint1`) per side. O6-hand bringup (`openarmx_hands`) not inspected | SOURCE_CONFIRMED (gripper bringup) / NOT_VERIFIED (O6) |
| OpenXR reference | `OpenXR-Docs` @ `5a82d45b`: `spaces.adoc:826-852` (VALID/TRACKED bits), `spaces.adoc:378-414` (`XrEventDataReferenceSpaceChangePending`, `changeTime`), `input.adoc:234,834-841` (`isActive`), `input.adoc:784-811` (`XrEventDataInteractionProfileChanged`) | reference |
| Runtime | Static source only. PRIOR_INTERNAL E2 (`OPENARMX_UDP_RUNTIME.md`) confirmed stamp pass-through and zero→`now()` at the bridge | background |

Files audited: `openarmx_teleop_bridge_vr/src/openarmx_teleop_bridge_vr_node.cpp` (748 lines), `openarmx_teleop_vr/openarmx_teleop_vr/openarmx_teleop_vr_node.py` (1033), `openarmx_teleop_vr/config/teleop_params.yaml`, `openarmx_teleop_vr/launch/teleop_vr.launch.py`, the READMEs.

## 2. Command path table

| # | Hop | Artifact (file:lines) | Carried fields | Dropped/unknown |
|---|---|---|---|---|
| H0 | OpenXR runtime → APK | binary APK | (claimed) AIM/GRIP pose, buttons | session state, isActive, location flags, profile: NOT_VERIFIED |
| H1 | APK → UDP:5100 (ASCII) | parsed at bridge `parseDatagram` cpp:327-432 | `L/R/LEFT/RIGHT/LEFT_ABS/RIGHT_ABS px py pz qx qy qz qw trig grip a b x y rate ts_ns`; `HEAD p q ts`; `JOY hand x y [ts]`; `BTN hand JOYSTICK p ts`; `CFG POSE_MODE 0/1 ts`; `MODE str [ts]`; `CALIBRATE_DONE [ts]` | no seq, no valid/tracked/active flag, no device id |
| H2 | Bridge → ROS topics | `publishSample` cpp:608-673 | `PoseStamped{stamp=ts_ns if >0 else now(), frame_id=pico_hmd}` cpp:510-525; Float32 trigger/grip/rate; Bool buttons; String mode | stamps on trigger/grip/buttons/mode/calibrate are dropped (std_msgs, no header) |
| H3 | Teleop wrapper ingest | callbacks py:587-678 | pose → `PoseInput{pos, quat, timestamp=time.monotonic()}` py:356-376 | `header.stamp` and `frame_id` discarded |
| H4 | Wrapper clutch/relative | `_update_relative_pose_state` py:407-443, `_current_relative_input` py:680-695 | delta vs reference, enabled→grip 1.0/0.0 | — |
| H5 | Closed core | `core.step(rel, abs)` py:890; `calibrate_absolute` py:618; `update_absolute_mode` py:612 | `result.{active_mode,target_q,left_active,right_active,waiting_for_joint_states,calibration_required}` | internals NOT_VERIFIED |
| H6 | Step limit + publish | `_limit_joint_step` py:966-995; `_publish_joint_commands` py:1001-1012 | `Float64MultiArray` 7 or 8 values per side | no header/stamp/id |
| H7 | Controller | ForwardCommandController (openarmx_ros2 yaml above) | position per joint | command timeout: NOT_VERIFIED (upstream FCC normally holds last command) |

## 3. Findings A1–A9

### A1 Focus/session and action-active state
- The UDP hand payload has no session, focus or isActive field (cpp:434-489). The bridge and wrapper never gate on such state. NOT_FOUND_IN_SEARCH (queries: `focus|session|active|valid|tracked` in cpp/py). Whether the APK suppresses sending when not FOCUSED is **NOT_VERIFIED**. SOURCE_CONFIRMED for the ROS side.
- Existing gate: an engagement requires grip > `grip_threshold` 0.5 (py:404-405, yaml:8), or the IK override (see A3). SOURCE_CONFIRMED.

### A2 Valid vs tracked
- The packet has no location flags. Pose components are copied verbatim (cpp:435-444, 517-523). Quaternions are not normalized or checked at the bridge or the wrapper (py:356-376). A frozen or inferred (valid-but-untracked) pose cannot be told apart from a tracked one at H1-H6. SOURCE_CONFIRMED (ROS side). APK filtering: NOT_VERIFIED.
- `frame_id` is the fixed parameter `pico_hmd` (cpp:94). The actual XrSpace basis used by the APK is NOT_VERIFIED. The wrapper ignores frame_id (py:356-376).

### A3 Buttons / toggle / clutch / deadman
- **Clutch (relative):** the latest cached grip value is the deadman. On a rising edge (or a null reference), the reference is re-captured from the current raw pose and an identity delta is emitted (py:432-435). On release or stale data, `enabled=False`, `reference=None`, and the pose becomes identity-if-was-enabled (py:425-430). So relative mode **does** re-anchor on engage. SOURCE_CONFIRMED.
- **Grip/trigger caches** (py:599-653) have no freshness of their own. They are gated indirectly through the pose freshness check (py:420-423). SOURCE_CONFIRMED.
- **IK enable override:** topic `openarmx_teleop_vr/ik_enable_override`, QoS RELIABLE + **TRANSIENT_LOCAL** depth 1 (py:564-573). It ORs into the enable for **both** arms (py:404-405) and counts as manual override (py:720-722). A latched `True` from any publisher is delivered to a node that starts later, and it bypasses the grip deadman while poses are fresh. It is never reset in code. NOT_FOUND_IN_SEARCH for a reset (query `ik_enable_override =`). SOURCE_CONFIRMED.
- **Button actions:** rising-edge latch into `pending_*` flags (py:667-672), consumed once per control cycle (py:741-749). B (relative or absolute) → `go_home`, all 14 joints to 0 (py:806, 751-752). Y → `hands_up`, both arms (py:808, 754-759). Absolute X → `absolute_capture` (py:809-821). One controller's button commands **both** arms. SOURCE_CONFIRMED.
- The bridge publishes A/B only for packets labelled RIGHT and X/Y only for LEFT (cpp:541-557, 573-589), even though every hand packet carries all four (cpp:453-469). SOURCE_CONFIRMED.
- Missing trailing fields default to trigger/grip/buttons = 0 (cpp:446-469). This disengages, which is the safe default. SOURCE_CONFIRMED.

### A4 Device / profile change; left/right binding
- **Binding is purely the ASCII label.** The first token `L/LEFT/LEFT_ABS` vs `R/RIGHT/RIGHT_ABS` selects `HandIndex` (cpp:335-358), which indexes the publishers (cpp:620, 530, 534, 563, 567). There is no device id, serial, profile or handedness cross-check. The APK's mapping from OpenXR `/user/hand/left|right` to the label is NOT_VERIFIED. SOURCE_CONFIRMED (ROS side).
- Wrapper: relative input topics are **hard-coded** `pico_left_controller/*`, `pico_right_controller/*` (py:534-557). Absolute topics and command topics are parameters (py:229-247). The left arm gets `q[:7]` → `left_cmd_topic` and the right arm gets `q[7:14]` → `right_cmd_topic` (py:927-931, 942-957). Nothing checks that `left_cmd_topic` reaches a controller owning `openarmx_left_*` joints, so a parameter or remap swap is not detected. SOURCE_CONFIRMED.
- **Cross-hand coupling of rate:** every hand packet's `rate` is published to **both** `pico_left/right_controller/rate` (cpp:536-539). The wrapper folds both into one `relative_is_full_speed` (py:552-557, 655-656) that sets the step limit for all 14 joints (py:904-907). The last packet wins. SOURCE_CONFIRMED.
- **Pose-source (AIM/GRIP) change:** `CFG POSE_MODE` → `vr/controller_pose_mode` (cpp:399-410, 652-656). The wrapper never subscribes to it (NOT_FOUND_IN_SEARCH, query `controller_pose_mode` in py: only param uses at 123-131, 251). The mapping matrices are fixed at startup from the launch param (py:123-139). If the APK switches AIM↔GRIP at runtime, the wrong matrices are used silently. SOURCE_CONFIRMED (ROS side); APK emission timing NOT_VERIFIED.
- Interaction-profile change (OpenXR `XrEventDataInteractionProfileChanged`): no wire field exists. NOT_FOUND_IN_SEARCH.

### A5 Origin / recenter
- Relative mode: re-anchoring happens only on the engage edge (py:432-435). A recenter while engaged (`XrEventDataReferenceSpaceChangePending`, spaces.adoc:378-414) is not represented on the wire. It shows up as a pose discontinuity that passes through `_compute_raw_relative_pose` (py:392-402). It is clipped only by the step limiter (see A8). SOURCE_CONFIRMED (no recenter signal); APK handling NOT_VERIFIED.
- Absolute mode: `CALIBRATE_DONE` → Bool → `calibrate_absolute(latest cached abs input)` (cpp:423-429, 665-670; py:614-621). The packet's `ts_ns` is dropped at H2. SOURCE_CONFIRMED.

### A6 Calibration / anchor × which sample
- Relative reference = a copy of the **latest** raw pose at engage time (py:433). Later deltas use `reference_rotation.T @ (cur - ref)` with the latest raw pose at each 100 Hz tick (py:392-402, 682-683). Both are "latest-received" values, not values interpolated to a given sample time. SOURCE_CONFIRMED.
- Absolute calibration uses the head/left/right poses cached at callback time (py:697-711). These may come from different UDP packets and different moments, because each hand and the head are separate datagrams (cpp:349-364). The core's use of `body_anchor_offset` and `position_scale_xyz` (py:152-166) is closed (NOT_VERIFIED). SOURCE_CONFIRMED (wrapper).
- Fixed axis/orientation matrices: the same defaults are used for left and right (yaml:76-84; py:252-296). Relative orientation is conjugated as `M R Mᵀ` (py:453). SOURCE_CONFIRMED.

### A7 Disconnect / reconnect, pause / resume
- **Existing timeouts:** bridge `SO_RCVTIMEO` 1 s just loops (cpp:299-304, 257-258), so the bridge itself has no stale signal. The wrapper's relative raw-pose freshness is 0.3 s using **receive-time** `time.monotonic()` (py:119, 371, 420-423). The core gets `stream_timeout_sec=0.3` (py:165); its behavior is closed, NOT_VERIFIED. SOURCE_CONFIRMED.
- **Auto-resume:** if grip is still cached > threshold (or override is True) when the stream returns after more than 0.3 s, `was_enabled` is False, so the reference is re-captured and motion resumes **without a fresh operator engage edge** (py:425-435). There is no jump, but the arm re-engages by itself. SOURCE_CONFIRMED.
- **Button motions ignore the VR stream:** `_run_button_motion` checks only joint_states completeness, manual override and target reached (py:823-877). A `go_home`/`hands_up` started before a disconnect runs to completion at 0.5°/cycle (yaml:47). SOURCE_CONFIRMED.
- joint_states are cached with no freshness, and `joint_states_received` is never reset (py:674-678, 939-964). SOURCE_CONFIRMED.
- Absolute pose caches have no wrapper freshness check (py:591-597); this is delegated to the closed core. NOT_VERIFIED.

### A8 Pending commands, previous goal, auto-resume
- `pending_*` flags are one-shot and cleared each tick (py:741-749), so they are short-lived. SOURCE_CONFIRMED. The edge state (`*_pressed`) is not reset on disconnect. That is conservative: a stale True cannot create a new edge.
- Control-loop exceptions are swallowed silently (py:933-935). When `target_q is None`, idle or calibration-required, the node publishes nothing (py:898-899). The consumer then holds the last command. Holding behavior: HYPOTHESIS/NOT_VERIFIED against the exact ros2_controllers version. The publish gap: SOURCE_CONFIRMED.
- **Step limiter is non-monotonic:** a per-joint delta is clipped to `max_step` only when `|delta| > threshold` (py:987-994). Default slow `max_step` is 4°, but `threshold` = 20/16/12/12/14/8/12° (py:182-188, 218-224; yaml:9-15, 40-46). So in slow mode, any delta up to the threshold (for example 19° on J1) passes unclipped in one 10 ms cycle. Only larger deltas are cut to 4°. In fast mode, threshold equals max_step (yaml:24-30 vs 40-46). The limit is relative to the measured `current_q`, not the last command. SOURCE_CONFIRMED (code); intent AUTHOR_CLAIM ("fast parameters, don't modify", py:199, 217).
- Gripper vs hand mode output length: 8 vs 7 values (py:1004-1011). The gripper bringup expects 8 joints (openarmx_ros2 yaml:55-66). A mode/bringup mismatch → FCC size rejection: HYPOTHESIS.

### A9 Linkage of consumed command to source sample
- The source `ts_ns` survives only into `PoseStamped.header.stamp` (cpp:510-515; E2 runtime confirmed in PRIOR_INTERNAL). The wrapper discards it and restamps with `time.monotonic()` (py:371). The output `Float64MultiArray` has no header, sequence or id (py:1001-1012). No sequence number exists anywhere (cpp:434-489). A consumed command cannot be linked to a UDP sample. SOURCE_CONFIRMED.
- Bridge timestamp parsing quirks: `rate` is accepted only if exactly 0.1 or 1.0, otherwise the token is reinterpreted as `timestamp_ns` (cpp:471-486). A non-positive stamp falls back to `now()` (cpp:511-512). SOURCE_CONFIRMED.
- Transport auth: `recvfrom` sender address is unused (cpp:247-251). The default bind is `0.0.0.0` (cpp:92, 309-310) with `SO_REUSEADDR` (cpp:294-297). Any host on the LAN can inject L/R packets, buttons (go_home), or CALIBRATE_DONE. SOURCE_CONFIRMED. Port co-binding via REUSEADDR: HYPOTHESIS.

## 4. Information-delivery table (evidence × hop)

✓ = carried, ✗ = not carried/dropped, ? = NOT_VERIFIED, n/a = not applicable

| Evidence | H0 APK | H1 UDP | H2 bridge topics | H3 wrapper ingest | H4/H5 mapper/core | H6 command | H7 controller |
|---|---|---|---|---|---|---|---|
| session/focus, isActive | ? | ✗ | ✗ | ✗ | ✗/? | ✗ | ✗ |
| VALID vs TRACKED bits | ? | ✗ | ✗ | ✗ | ✗/? | ✗ | ✗ |
| hand identity | ? | label token | topic index | hard-coded topic | arm index | topic param | joint list |
| device/profile/serial | ? | ✗ | ✗ | ✗ | ✗ | ✗ | n/a |
| pose source AIM/GRIP | ? (claimed) | `CFG POSE_MODE` | ✓ `vr/controller_pose_mode` | **✗ not subscribed** | fixed param | ✗ | ✗ |
| grip/clutch | ? | ✓ | ✓ Float32 (no stamp) | ✓ cached | ✓ edge re-anchor | ✗ | ✗ |
| recenter event / changeTime | ? | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| calibration event | ? | `CALIBRATE_DONE [ts]` | Bool (ts dropped) | latest-cache calibrate | ? | ✗ | ✗ |
| source timestamp | ? | `ts_ns` | ✓ header.stamp (pose only) | **✗ replaced by monotonic** | ✗ | ✗ | ✗ |
| sequence/id | ? | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| freshness/timeout | ? | ✗ | ✗ (1 s rcv loop) | 0.3 s rx-time (relative) | 0.3 s (closed) | ✗ | ? |
| rate (speed) | ? | per-hand | **broadcast to both** | single flag | both arms | ✗ | ✗ |
| sender authentication | ? | ✗ | ✗ | n/a | n/a | n/a | n/a |

## 5. Candidate matrix rows

| Item | Class | Label |
|---|---|---|
| UDP payload has no valid/tracked/isActive/focus field (cpp:434-489) | METADATA | SOURCE_CONFIRMED (ROS side); APK NOT_VERIFIED |
| Source `ts_ns` discarded at wrapper; restamped `time.monotonic()` (py:371) | METADATA | SOURCE_CONFIRMED |
| No seq/id; output Float64MultiArray unstamped (py:1001-1012) | OBSERVATION | SOURCE_CONFIRMED |
| L/R binding solely via ASCII label; no device/handedness cross-check (cpp:335-358) | METADATA | SOURCE_CONFIRMED |
| Command topics parameterized with no joint-ownership check vs left/right slices (py:246-247, 927-931) | INTEGRATION | SOURCE_CONFIRMED |
| Relative input topics hard-coded while bridge topics are parameterized (py:534-557 vs cpp:99-152) | INTEGRATION | SOURCE_CONFIRMED |
| Per-hand `rate` broadcast to both rate topics → global speed flag (cpp:536-539; py:655-656, 904-907) | IMPLEMENTATION | SOURCE_CONFIRMED |
| `CFG POSE_MODE` published but not consumed; matrices fixed at launch (cpp:652-656; py:123-139) | INTEGRATION | SOURCE_CONFIRMED |
| Single-controller B/Y button drives both arms (py:751-759, 806-808) | APPLICATION | SOURCE_CONFIRMED |
| Button motions continue after VR stream loss (py:823-877) | APPLICATION | SOURCE_CONFIRMED |
| Auto-resume after >0.3 s gap if grip still cached high (py:425-435) | APPLICATION | SOURCE_CONFIRMED |
| TRANSIENT_LOCAL `ik_enable_override` bypasses grip deadman for both arms, never reset (py:404-405, 564-573) | IMPLEMENTATION | SOURCE_CONFIRMED |
| Step limiter passes deltas ≤ threshold unclipped; slow 4° vs threshold up to 20° (py:987-994; yaml:9-15, 40-46) | IMPLEMENTATION | SOURCE_CONFIRMED |
| No recenter signal on wire; mid-engage recenter appears as pose jump (py:392-402) | METADATA | SOURCE_CONFIRMED (ROS); APK NOT_VERIFIED |
| Absolute calibration from latest-cached, per-packet-unsynchronized head/L/R poses; CALIBRATE ts dropped (py:614-621, 697-711; cpp:665-670) | PLACEMENT | SOURCE_CONFIRMED |
| Relative re-anchor on engage edge exists (py:432-435) (known application pattern, acknowledged) | APPLICATION | SOURCE_CONFIRMED |
| joint_states cache without freshness (py:674-678, 939-964) | IMPLEMENTATION | SOURCE_CONFIRMED |
| Control-loop exceptions silently swallowed → publish gap (py:933-935) | IMPLEMENTATION | SOURCE_CONFIRMED |
| Unauthenticated UDP on 0.0.0.0, sender address unused (cpp:247-251, 309-310) | INTEGRATION | SOURCE_CONFIRMED |
| `rate` token reinterpreted as timestamp if not exactly 0.1/1.0 (cpp:471-486) | IMPLEMENTATION | SOURCE_CONFIRMED |
| Core freshness (0.3 s), absolute-mode logic, IK internals (closed `openarmx_arm_driver`) | IMPLEMENTATION | NOT_VERIFIED (wrapper boundary) |
| FCC holds last command when teleop stops publishing | INTEGRATION | HYPOTHESIS |
| APK maps OpenXR left/right paths, gates on FOCUSED/isActive/tracked | METADATA | NOT_VERIFIED |
