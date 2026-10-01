# A2 — Quest2ROS2 (Quest app `com.Tiguin.Q2R` → ROS-TCP → `BaseArmController` → Cartesian controller)

Audited 2026-10-01. Method: `AUDIT_METHOD.md`.

## Pins and scope

| Component | Pin | Status |
|---|---|---|
| ROS side | `Taokt/Quest2ROS2` @ `07aaf65149c9e29103f1fc61deb466cef8a55cef`. This is remote HEAD; the last commit is 2026-03-06. Clean checkout. | `/home/cclab/ros_xr/Deprecated/semantic_validation/targets/quest2ros2` |
| Quest frontend | Quest2ROS app `com.Tiguin.Q2R` v1.1, observed on 2026-09-17 (PRIOR_INTERNAL). The project page https://quest2ros.github.io/ and `Quest2ROS/quest2ros` contain ROS-side code only. A search for the frontend source gave **NOT_FOUND_IN_SEARCH** (`gh search repos quest2ros`; site text grep for github/unity/apk). | **closed binary: NOT_VERIFIED** |
| Transport | `guguroro/ros_tcp_communication` @ `5c5f0895…` (README step 4). PRIOR_INTERNAL: it is not compatible with the app without CDR/NUL fixes. | not re-audited |
| Final consumer | "Cartesian end-effector position controller" on `<ctrl_prefix>/target_frame` (README "Prerequisites"; `left_arm_controller.py` L13). The controller is **not in the repo**. | **NOT_VERIFIED** |

**Lineage.** The project is "built based on Quest2ROS" (README L2), the ROS 1 project of the same app.
Forks found by search include `youssefhindawi-nodogoro/Quest2ROS2`, `SreevaatsavB/quest2ros2-fr5` and
`kimsooyoung/quest2ros`. They are not counted as independent implementations.

**Scope.** Only the ROS-side mapper is source-visible. Every statement about what the Quest app reads
or forwards is NOT_VERIFIED.

## Command path

| Hop | Code | What crosses |
|---|---|---|
| 1. Quest runtime / OVR SDK | closed | — |
| 2. Quest2ROS app | closed | publishes `/q2r_{left,right}_hand_{pose,inputs,twist}` through ROS-TCP |
| 3. ROS-TCP endpoint | external package | CDR decode → ROS 2 topics |
| 4. Message types | `Files_for_msg_pkg/msg/OVR2ROSInputs.msg`: `button_upper`, `button_lower`, `thumb_stick_{horizontal,vertical}`, `press_index`, `press_middle`. Pose: `geometry_msgs/PoseStamped`. | **no validity, tracking, focus, session, sequence or device-id field** |
| 5. `BaseArmController` (one node per arm) | `q2r2_bringup/robot_arm_controller_base.py` | subscriptions L112–123; `_pose_callback` L211–308; `_inputs_callback` L334–384 |
| 6. Command | `PoseStamped` on `<ctrl_prefix>/target_frame`, frame = configured `base_frame_id`, stamp = `now()` (L302–306) | — |
| 7. Cartesian controller → robot | not in repo | NOT_VERIFIED |

## Item-by-item findings (all SOURCE_CONFIRMED at `07aaf65` unless labelled)

### A1 — focus/session, action active

- No field in either message carries focus, session or action-active state (hop 4).
- The ROS side cannot observe an XR interruption except as **message silence**, and it has no
  silence handling (A7).

### A2 — valid vs tracked

- There is no tracking or validity information. The pose is consumed as long as messages arrive
  (L211–232).
- Whether the closed app sends last-known, inferred or no poses on tracking loss is NOT_VERIFIED.
- PRIOR_INTERNAL, 2026-09-17: the real-Quest trial showed pose-arrival gaps of 30.3 s and 0.8 s that
  could not be attributed (`NO_TRANSITION_OBSERVED`).

### A3 — permission, toggle, caching

- **The permission is a latched toggle, not a deadman.**
  - `allow_pose_update = True` at start (L89): streaming is enabled before any operator action.
  - Each rising edge of `button_lower` flips it (L356–358).
  - The previous button level is kept in `_button_lower_pressed_state` (L342–345, L384).
- **Disabling has three effects:**
  - pose callbacks return early (L220–221);
  - nothing is published, so the controller keeps the last target (consumer NOT_VERIFIED);
  - the next enable re-anchors the robot to the current EE pose from tf and the Quest to the next
    filtered sample (L363–381).

  Re-anchor on enable is therefore implemented.
- **Gripper.** `button_upper` rising edge toggles an internal `is_gripper_closed` flag and sends a
  `GripperCommand` goal asynchronously (L310–332, L348–353). The flag flips *before* any result, so a
  failed or rejected goal desynchronizes it.

### A4 — device / profile / arm binding

- Arm ↔ hand binding is static. It is set by topic name and `mirror` (L98–101).
- README step 6 requires that `mirror` be identical in both arm files. Nothing checks this. If one
  file has `mirror=True` and the other `False`, both arms bind to the same hand. This is a
  configuration error (SOURCE_CONFIRMED that no check exists).
- No controller-swap or profile information is delivered (hop 4).

### A5 — origin change and effective time

- The input `frame_id` and `stamp` are ignored. The output is restamped with `now()` and the configured
  frame (L302–304).
  - PRIOR_INTERNAL `QUEST2ROS2_STALE_RESTAMP.md` and `QUEST2ROS2_ROS_RUNTIME.md` confirmed this at
    runtime with synthetic sources.
- There is no origin-change notification. **Consequence (HYPOTHESIS H-B2):** the robot target jumps by
  the recenter displacement. The mechanism is the following:
  1. A Quest recenter (or a guardian or relocalization change) moves the app's tracking origin while
     streaming is enabled.
  2. After the change, `offset = avg_quest_pos − first_received_quest_position` mixes a pre-change
     anchor with post-change samples (L246–267).
  3. The 20-sample moving average (`left_arm_controller.py` L11; L166–208) also averages across the
     discontinuity for one window length, which smooths the jump.

  Whether the app emits poses in a space that changes on recenter is NOT_VERIFIED (closed app).

### A6 — calibration, anchor, and the transform used

- The anchor pair (robot EE pose from tf, Quest filtered pose) is captured on the first full-window
  sample (L235–244).
- The robot EE pose comes from `tf_buffer.lookup_transform(base, ee, rclpy.time.Time())` (L153–155),
  that is, the **latest** transform. For a "current EE" anchor that is the intended semantics.
- The Quest pose is used in whatever frame the app sends; `frame_id` is ignored. No XR-to-robot
  extrinsic is applied. Hand deltas are added in the robot base frame as is, so axis alignment is
  assumed (AUTHOR_CLAIM: none stated).

### A7 — disconnect/reconnect, pause/resume

- There is no timeout, watchdog or connection generation. The anchor and filter survive a source
  disconnect.
  - PRIOR_INTERNAL `QUEST2ROS2_RECONNECT_RUNTIME.md`, synthetic: the source baseline was x = 0.50,
    moved to 0.60, was silent for 2.5 s, and reconnected at x = 0.70. The output target was
    x = 0.60, computed from the old anchor and a filter mixing pre- and post-gap samples.
- On resume the robot moves to wherever the *hand displacement since the original anchor* points.
  This is the resume/re-reference class, analogous to S5 #10. It is **APPLICATION**, and the
  conventional fix (re-anchor after silence) applies.

### A8 — pending commands, previous goal

- No command queue exists. The consumer holds the last target (NOT_VERIFIED).
- In-flight gripper goals are not tracked (A3).

### A9 — linkage

- There is no sequence number. The stamp is replaced (L304) and the input frame dropped.
  Source→command linkage is by timing only.

## Information-delivery table

| Evidence | Quest runtime | App (closed) | Message | Controller | Consumer |
|---|---|---|---|---|---|
| action active / focus | yes | NOT_VERIFIED | **not carried** | — | — |
| deadman | — | — | `button_lower` level (used as a toggle edge) | latched toggle | — |
| valid / tracked | yes | NOT_VERIFIED | **not carried** | — | — |
| origin change | yes | NOT_VERIFIED | **not carried** | — | — |
| sample time | yes | NOT_VERIFIED | `header.stamp` (meaning NOT_VERIFIED) | **ignored, restamped** | stamp = controller `now()` |
| frame | yes | NOT_VERIFIED | `header.frame_id` | **ignored** | configured base |
| target arm | — | topic name | topic | static `mirror` mapping, unchecked | per-arm controller |

## Summary for the matrix

| Item | Class candidate | Label |
|---|---|---|
| No focus/tracking/origin evidence on the wire | METADATA. Delivering it needs the closed app; the ROS-side substitute is a silence watchdog. | SOURCE_CONFIRMED (message), NOT_VERIFIED (app) |
| Latched toggle permission; enabled at start | APPLICATION policy. The conventional alternative is a deadman, or a toggle with silence revoke. | SOURCE_CONFIRMED |
| No silence timeout; anchor and filter survive a gap | INTEGRATION + APPLICATION (re-anchor after silence) | SOURCE_CONFIRMED + PRIOR_INTERNAL runtime |
| Recenter during enabled streaming → jump (H-B2) | interval mixing; conventional fix is re-anchor on discontinuity or epoch | HYPOTHESIS (app side NOT_VERIFIED) |
| `mirror` consistency unchecked | configuration check (one line) | SOURCE_CONFIRMED |
| Gripper flag flips before the result | IMPLEMENTATION (result handling) | SOURCE_CONFIRMED |
