# XR→ROS Semantic Propagation Audit

## 1. Scope and notation

이 문서는 고정된 공개 source에서 다음 12개 semantic을 추적한다.

1. source sample timestamp
2. sequence/order information
3. tracking validity
4. actively tracked vs inferred/emulated state
5. controller/device connected state
6. source identity
7. reference space/frame identity
8. XR session/focus state
9. clutch/control enable state
10. reconnect/session generation
11. downstream timestamp 재생성
12. stale data 검사

판단 label:

- `CONFIRMED_STATIC`: 고정 commit의 source에서 직접 확인
- `HYPOTHESIS`: 실제 runtime/device 검증 필요
- `UNKNOWN`: inspected source만으로 확인 불가

Matrix code는 해당 stage에 도달한 semantic의 상태를 뜻한다.

- `P`: Preserved / 명시적으로 표현
- `D`: Dropped / 더 이상 표현되지 않음
- `R`: Regenerated / local 값으로 교체
- `A`: Aliased / 다른 source 또는 불충분한 label로 대체
- `G`: Explicitly guarded / 진행 전에 검사
- `U`: Unknown / source 부재 또는 repository 범위 밖

한 칸에는 하나의 code만 사용한다. `Control`과 `Robot target`은 공개 repository가 실제 control output을 포함할 때만 채우며, 실제 physical actuation을 뜻하지 않는다.

## 2. Fixed revisions

모든 target은 shallow clone이며 upstream source patch는 없다.

| Repository | Default branch | Clone time (Asia/Seoul) | HEAD | Latest commit date |
| --- | --- | --- | --- | --- |
| `https://github.com/SpesRobotics/teleop.git` | `main` | `2026-08-30T21:41:40+09:00` | `c5d808155a87b584d6147a5943d4b87c34c92db0` | `2026-07-17T12:17:58+02:00` |
| `https://github.com/PickNikRobotics/meta_quest_teleoperation.git` | `main` | `2026-08-30T21:41:54+09:00` | `bbaef0762fdb0b429b8ea12a4ca65040748b41dd` | `2026-08-12T16:57:46-06:00` |
| `https://github.com/Taokt/Quest2ROS2.git` | `main` | `2026-08-30T21:41:52+09:00` | `07aaf65149c9e29103f1fc61deb466cef8a55cef` | `2026-03-06T17:11:23+00:00` |
| `https://github.com/NVIDIA-ISAAC-ROS/isaac_ros_teleop.git` | `main` | `2026-08-30T21:41:51+09:00` | `197f5cd9ff2cbd90533a93c67be2a661319048ba` | `2026-08-18T19:37:31-07:00` |
| `https://github.com/NVIDIA/IsaacTeleop.git` | `main` | `2026-08-30T21:41:53+09:00` | `9fba23c4a3bd5b6de732cac77a47f471fca25276` | `2026-08-28T20:34:31-07:00` |

`isaac_ros_teleop@197f5cd9`의 `.gitmodules`는 `release/1.3.x`를 지정하며 gitlink는 `IsaacTeleop@465ce637120ac35404f5f741a9f25f3f1a1a25ea` (`2026-07-01T19:58:10+00:00`)이다. 따라서 NVIDIA primary control은 이 gitlink revision으로 판단하고, 현재 `main@9fba23c4`의 개선은 별도 comparison으로 표기한다.

## 3. Target A — SpesRobotics/teleop

### Architecture

```text
WebXR right tracked-pointer / viewer
  → teleop/index.html onXRFrame
  → JSON {type:"pose", data:{position, orientation, move, ..., device}}
  → FastAPI WebSocket / Teleop.__update
  → relative target calculation + subscriber callback
  → teleop.ros2 PoseStamped(target_frame) + TF
```

### Semantic matrix

| Semantic | XR runtime source | XR app | Wire | ROS ingress | Control | Robot target |
| --- | :---: | :---: | :---: | :---: | :---: | :---: |
| source sample timestamp | P | D | D | D | R | R |
| sequence/order | U | D | D | D | D | D |
| tracking validity | P | A | D | D | D | D |
| tracked vs inferred/emulated | P | D | D | D | D | D |
| controller/device connected | P | A | A | D | D | D |
| source identity | P | A | A | A | A | A |
| reference space/frame | P | P | D | D | R | R |
| XR session/focus | P | D | D | D | D | D |
| clutch/control enable | P | P | P | P | G | G |
| reconnect/session generation | U | D | D | D | A | A |
| downstream timestamp regeneration | P | D | D | D | R | R |
| stale-data check | U | D | D | D | D | D |

### H1 — Tracking semantic loss / source identity confusion

**CONFIRMED_STATIC**

- `getPoseFromInputSource()` selects only `handedness === 'right'` and `targetRayMode === 'tracked-pointer'`, calls `frame.getPose(inputSource.targetRaySpace, referenceSpace)`, and returns only position/orientation. Evidence: `SpesRobotics/teleop@c5d80815:teleop/index.html:252-278`, grep string `frame.getPose(inputSource.targetRaySpace, referenceSpace)`.
- 따라서 controller `XRPose`가 non-null인 채 `emulatedPosition=true`가 되더라도 이 semantic은 helper에서 사라지고 controller position/orientation은 정상 packet과 같은 경로로 전송된다. 실제 Quest 3가 tracking loss 때 이 상태를 만드는지는 아직 hardware 검증 전이다.
- In `onXRFrame`, `isVRDevice` true plus controller pose null enters `frame.getViewerPose(xrReferenceSpace)` and copies `views[0].transform`. Evidence: `teleop/index.html:328-353`, grep strings `if (controllerPose)` and `const viewerPose = frame.getViewerPose`.
- Pose source selection and `move` selection are independent. The pose may come from viewer while `teleopFrontEnd` remains `teleopJoystick`, so right gamepad `moveButtonPressed` is serialized. Evidence: `teleop/index.html:334-380`, especially `teleopFrontEnd = (isVRDevice) ? teleopJoystick : teleopUI` and `move: teleopFrontEnd.isMotionEnabled()`.
- Payload has only position, orientation, move, gripper, fps, scale, reserved buttons, `device`, message. It has no controller/viewer source identity, tracking validity, `emulatedPosition`, XR frame time, sequence, or session generation. `device` remains `VR` after viewer fallback. Evidence: `teleop/index.html:355-380`.
- Server `Teleop.__update()` reads `move`, `position`, `orientation`, optional `scale`; it never checks source identity or tracking state. Evidence: `SpesRobotics/teleop@c5d80815:teleop/__init__.py:220-285`.
- ROS output has no source field and generates its own stamp. Evidence: `SpesRobotics/teleop@c5d80815:teleop/ros2/__main__.py:95-141`.

**Runtime support:** source-faithful S1-A reproduced controller selection, viewer fallback, and viewer fallback with `move=true`. Hardware instrumentation preflight additionally verified that an observation-only logger can expose controller `emulatedPosition=true` while leaving the upstream `type:"pose"` packet byte-for-structure equivalent. Both are software runtime evidence, not Quest tracking-loss evidence. See `results/S1_RESULT.md` and `results/SPES_QUEST_HW_RESULT.md`.

### H2 — Recovery after pose jump

**CONFIRMED_STATIC**

- With a prior pose, a sample beyond 5 cm or 35° clears `__relative_pose_init`, stores the rejected sample in `__previous_received_pose`, and returns before subscriber notification. Evidence: `teleop/__init__.py:246-257`, grep `Pose jump detected, resetting the pose`.
- A following sample close to the rejected sample passes comparison. Because the relative anchor is null, that following sample becomes the new anchor and `__previous_received_pose` is cleared. Evidence: `teleop/__init__.py:258-265`.
- Subsequent samples are computed relative to the new anchor and notify subscribers. Evidence: `teleop/__init__.py:266-285`.

**Runtime confirmed in S1-B:** `P1 → P2 → Q1 → Q2 → Q3` produced callbacks `P1, P2, Q2, Q3`. Q1 was rejected; Q2 re-anchored without target motion; Q3 changed the target.

### H3 — Reconnect state

**CONFIRMED_STATIC**

- `__relative_pose_init`, `__absolute_pose_init`, `__previous_received_pose`, and current `__pose` are instance state created once in `Teleop.__init__`. Evidence: `teleop/__init__.py:153-172`.
- WebSocket disconnect only removes the socket from `ConnectionManager`; it does not reset Teleop state. Evidence: `teleop/__init__.py:297-315`.
- Frontend WebSocket close schedules `connectWebSocket` after three seconds without recreating the WebXR session or `TeleopJoystick`. Evidence: `teleop/index.html:183-232`.
- Server does not retain a separate move flag; every message supplies `move`. The frontend joystick state can persist across socket reconnect because the object remains in the page.

**HYPOTHESIS:** actual disconnect timing may determine whether an intervening `move=false` message is delivered. No real WebSocket reconnect run was performed.

### Other semantic findings

- `local-floor` is explicit only inside WebXR. It is absent from the packet. ROS output independently labels TF parent `base_link` and PoseStamped frame `link_base`. This is frame regeneration, not preservation. `CONFIRMED_STATIC` — `teleop/index.html:284-326`, `teleop/ros2/__main__.py:102-132`.
- WebXR frame `time` controls a 10 ms send interval but is not serialized. `CONFIRMED_STATIC` — `teleop/index.html:328-380`.
- ROS TF and target PoseStamped both use `node.get_clock().now()`. `CONFIRMED_STATIC` — `teleop/ros2/__main__.py:102-104,130-132`.
- The 5 cm/35° logic is a spatial discontinuity guard, not an age/freshness guard. No timestamp/age check was found. `CONFIRMED_STATIC`.

## 4. Target B — PickNik meta_quest_teleoperation

### Architecture

```text
Quest/XR components update leftController/rightController GameObject Transform
  → RosPublishers.Update at configured 60 Hz
  → ROS-TCP-Connector Odometry + TF + button topics
  → ros_tcp_endpoint
  → host-side MoveIt Pro objective (outside this repository)
```

### Semantic matrix

| Semantic | XR runtime source | XR app | Wire | ROS ingress | Control | Robot target |
| --- | :---: | :---: | :---: | :---: | :---: | :---: |
| source sample timestamp | U | R | R | R | U | U |
| sequence/order | U | D | D | D | U | U |
| tracking validity | U | D | D | D | U | U |
| tracked vs inferred/emulated | U | D | D | D | U | U |
| controller/device connected | P | D | D | D | U | U |
| source identity | P | P | P | P | U | U |
| reference space/frame | P | P | P | P | U | U |
| XR session/focus | P | D | D | D | U | U |
| clutch/control enable | P | P | P | P | U | U |
| reconnect/session generation | U | D | D | D | U | U |
| downstream timestamp regeneration | U | R | R | R | U | U |
| stale-data check | U | D | D | D | U | U |

### H4 — Tracking-state loss / freshness laundering

**CONFIRMED_STATIC**

- `Update()` advances a local timer and calls `PublishOdomAndTf(leftController.transform, ...)` and the right equivalent at `1/60 s`. Evidence: `meta_quest_teleoperation@bbaef076:UnityProject/Assets/ROSPublishers.cs:32-54,318-340`.
- `PublishOdomAndTf()` directly calls `sourceTransform.GetPositionAndRotation()` and publishes the result. No `isTracked`, `trackingState`, XR device connection, pose validity, or sample-age check occurs in this method or before its call. Evidence: `ROSPublishers.cs:381-416`; repository search for `isTracked`, `trackingState`, `InputTracking`, and `OnApplicationFocus` found no publisher check.
- Header stamp is produced by `DateTime.UtcNow`, not an XR sample timestamp. Evidence: `ROSPublishers.cs:367-379,394`.
- Source side and frame are preserved through separate left/right odometry topics, `child_frame_id`, and header frame `quest`. Evidence: `ROSPublishers.cs:35-48,103-126,381-416`.
- Grip/button state is published on separate topics, but this repository does not bind it atomically to a pose sample or implement host clutch logic. Evidence: `ROSPublishers.cs:307-340,343-356`; README states clutch is host-side.

**HYPOTHESIS:** on real Quest tracking loss, Unity may freeze, infer, or otherwise continue updating the controller GameObject Transform. If it does, this publisher will emit that Transform with a fresh wall-clock ROS header. The Transform behavior itself is not established by this static audit.

**UNKNOWN:** host MoveIt Pro objective freshness/validity handling because that code is not in this target checkout.

## 5. Target C — Quest2ROS2

### Architecture

```text
Quest/Unity app — source absent from repository
  → ROS-TCP wire — implementation external
  → /q2r_<side>_hand_pose PoseStamped + Inputs
  → BaseArmController moving average / relative anchor
  → <arm controller>/target_frame PoseStamped
```

### Semantic matrix

| Semantic | XR runtime source | XR app | Wire | ROS ingress | Control | Robot target |
| --- | :---: | :---: | :---: | :---: | :---: | :---: |
| source sample timestamp | U | U | U | P | D | R |
| sequence/order | U | U | U | D | D | D |
| tracking validity | U | U | U | D | D | D |
| tracked vs inferred/emulated | U | U | U | D | D | D |
| controller/device connected | U | U | U | D | D | D |
| source identity | U | U | U | A | A | A |
| reference space/frame | U | U | U | P | R | R |
| XR session/focus | U | U | U | D | D | D |
| clutch/control enable | U | U | U | P | G | G |
| reconnect/session generation | U | U | U | D | D | D |
| downstream timestamp regeneration | U | U | U | P | D | R |
| stale-data check | U | U | U | P | D | D |

`PoseStamped`이 timestamp/frame field를 갖는다는 의미에서 ROS ingress를 `P`로 표시했지만, 값의 실제 XR origin은 upstream app source 부재로 `UNKNOWN`이다. Source identity는 Topic 이름으로 left/right만 암시되므로 `A`다.

### H5 — Stale input re-stamping

**CONFIRMED_STATIC**

- Controller subscribes to `/q2r_<side>_hand_pose` as `PoseStamped`. Evidence: `Quest2ROS2@07aaf651:q2r2_bringup/robot_arm_controller_base.py:92-127`.
- `_pose_callback()` stores the message and reads only `pose.position`/`pose.orientation`; it never reads `pose_stamped.header.stamp` or input `frame_id`. Moving average also stores only pose arrays. Evidence: `robot_arm_controller_base.py:166-208,211-262`.
- No message age, maximum delay, monotonic sequence, or freshness threshold occurs on this control path. Repository search found no freshness logic in `robot_arm_controller_base.py`.
- Output target creates a new `PoseStamped`, sets configured `base_frame_id`, and stamps it with `self.get_clock().now()`. Evidence: `robot_arm_controller_base.py:301-306`.
- Therefore an old input message that reaches the callback is not rejected for age and its source stamp is not propagated to `target_frame`. This is static freshness laundering at the callback/output boundary; it does not prove the upstream app actually replays stale samples.
- `allow_pose_update` is an explicit local gate toggled by the lower-button Inputs callback, but it is not a freshness check. Evidence: `robot_arm_controller_base.py:81-90,334-384`.

**UNKNOWN:** XR runtime→Unity→wire semantics. The target repository contains no Unity `Assets/`, `.cs`, or client socket implementation. Existing workspace evidence also recorded this limitation.

## 6. NVIDIA control

### Architecture and version boundary

```text
OpenXR actions / xrLocateSpace
  → IsaacTeleop live controller tracker
  → ControllerSnapshot + validity / optional active state + timestamp record
  → retargeting tensor groups
  → teleop_ros2 output builder
  → ROS EE/controller topics
```

Primary evidence below is `IsaacTeleop@465ce637`, the exact gitlink of `isaac_ros_teleop@197f5cd9`. Current `IsaacTeleop main@9fba23c4` is listed only where behavior is newer.

### Semantic matrix — linked release

| Semantic | XR runtime source | XR app | Internal schema | ROS ingress | Control | Robot target |
| --- | :---: | :---: | :---: | :---: | :---: | :---: |
| source sample timestamp | P | P | P | D | D | R |
| sequence/order | U | D | D | D | D | D |
| tracking validity | P | P | P | G | G | A |
| tracked vs inferred/emulated | P | D | D | D | D | D |
| controller/device connected | P | G | P | A | G | A |
| source identity | P | P | P | A | P | A |
| reference space/frame | P | P | D | R | R | R |
| XR session/focus | P | U | D | D | U | U |
| clutch/control enable | P | P | P | P | U | U |
| reconnect/session generation | U | U | D | D | U | U |
| downstream timestamp regeneration | P | P | P | R | R | R |
| stale-data check | U | D | D | D | D | D |

### H6 — Positive control findings

**CONFIRMED_STATIC at linked release `465ce637`**

- Controller pose action state is queried and inactive controllers clear the tracked data object instead of reusing the previous frame. Evidence: `IsaacTeleop@465ce637:src/core/live_trackers/cpp/live_controller_tracker_impl.cpp:350-373`, grep `tracked.data.reset()`.
- Grip and aim `xrLocateSpace` results require both `XR_SPACE_LOCATION_POSITION_VALID_BIT` and `XR_SPACE_LOCATION_ORIENTATION_VALID_BIT`. The schema has separate `ControllerPose.is_valid`. Evidence: `live_controller_tracker_impl.cpp:375-415`; `src/core/schema/fbs/controller.fbs:24-43`.
- Locate failure clears the tracked object before throwing, and action sync failure clears both sides. This prevents stale prior controller objects from surviving those failure paths. Evidence: `live_controller_tracker_impl.cpp:350-404`.
- Left/right identity is distinct in action subpaths and separate tracked objects. Evidence: `live_controller_tracker_impl.cpp:190-278,442-449`.
- `DeviceDataTimestamp` defines available local monotonic, sample local monotonic, and raw device time. Evidence: `src/core/schema/fbs/timestamp.fbs:6-26`; controller recording constructs it at `live_controller_tracker_impl.cpp:445-449`.
- ROS EE construction calls `controller_aim_is_valid()` before using each side. Invalid/absent side is replaced by an identity pose in the release `PoseArray`. Evidence: `examples/teleop_ros2/python/tensor_group_helpers.py:16-26`; `examples/teleop_ros2/python/messages.py:114-158`.

This is a useful positive control because controller active state and pose validity are explicit and used as gates. It is not a perfect semantic-preservation control:

- The tracker checks OpenXR `VALID` bits but not `POSITION_TRACKED` / `ORIENTATION_TRACKED` bits, so actively tracked versus inferred is not preserved for controller pose. `CONFIRMED_STATIC`.
- Linked release ROS output uses positional `PoseArray`; invalid sides become identity poses without an explicit validity field in that message. This is guarded substitution (`A`), not full downstream preservation. `CONFIRMED_STATIC`.
- Internal sample timestamp is not used as the ROS header. The ROS node generates `now = self.get_clock().now().to_msg()`, and controller payload builder uses `time.time_ns()`. `CONFIRMED_STATIC` — `examples/teleop_ros2/python/teleop_ros2_node.py:353` and `messages.py:58,244` at the linked revision.
- No source-age threshold was found on the inspected controller→ROS path. `CONFIRMED_STATIC`.

**Current main comparison `9fba23c4`**

- Current main adds explicit invalid-grip handling in `Se3AbsRetargeter` (hold last pose) and `Se3RelRetargeter` (zero delta, clear smoothing, rebaseline on recovery). Evidence: `IsaacTeleop@9fba23c4:src/python/isaacteleop/retargeters/se3_retargeter.py:248-258,393-416`; regression tests at `tests/python/core/retargeting_engine/test_se3_retargeter_pose_validity.py:85-179`.
- Current main ROS EE output uses `NamedPoseArray` with per-side `is_valid` and omits invalid wrist TFs. Evidence: `examples/teleop_ros2/python/messages.py:43-85,114-141,238-269`.
- Current main still generates ROS header time at publication and still does not preserve controller tracked-vs-inferred bits. Therefore it is a stronger validity control, not a positive control for all 12 semantics.

## 7. Consolidated findings

### CONFIRMED_STATIC

- Spes: controller null→viewer fallback exists; source identity/validity/timestamp are absent; `move` can remain controller-derived; server jump recovery can accept the new viewer trajectory after one reject; disconnect does not reset server anchors.
- PickNik: controller Transform is read periodically without tracking-state checks and is stamped with `DateTime.UtcNow`.
- Quest2ROS2: input PoseStamped header is not checked or propagated; target header uses current node time; no age threshold exists.
- NVIDIA linked release: controller active/pose-validity gates exist and stale tracked objects are cleared on inactive/failure paths, but controller tracked-vs-inferred and source timestamp are not preserved to ROS.

### HYPOTHESIS

- Real Quest 3 controller obstruction produces a non-null controller pose with `emulatedPosition=true`; Spes continues generating actionable target callbacks because this semantic is dropped. This is the primary hardware hypothesis.
- Real Quest 3 controller obstruction may instead produce `frame.getPose()==null` while viewer pose remains available. This controller→viewer substitution is the secondary hardware hypothesis.
- Real PickNik controller Transform freezes or becomes inferred while the publisher continues at 60 Hz.
- Actual reconnect timing allows Spes frontend move state and server anchors to bridge a socket loss exactly as static state layout suggests.

### UNKNOWN / NOT FOUND

- Quest2ROS2 XR application source and its original pose timestamp/validity/session metadata: `UNKNOWN`.
- A source-age guard on Spes, PickNik publisher, Quest2ROS2 arm controller, or inspected NVIDIA controller→ROS path: `NOT FOUND`.
- End-to-end ROS dummy sink result for Spes S1: `UNKNOWN` because not run.
- Physical robot impact: outside scope and not tested.

## 8. Audit conclusion

Spes H1/H2 is the strongest immediate candidate because semantic dropping, the aliasing branch, and server recovery behavior are visible in actual upstream source, while fallback/recovery were reproduced in source-faithful software replay. The appropriate current rating is **PROMISING, NEEDS QUEST VALIDATION**. Hardware priority is now non-null controller pose with `emulatedPosition=true`; controller-null→viewer fallback is secondary. No Quest result has yet raised, weakened, or disproved the candidate.

PickNik and Quest2ROS2 provide independent freshness/re-stamping patterns, but PickNik still needs real tracking-loss behavior and Quest2ROS2 lacks the XR client source. NVIDIA is a partial positive control: it explicitly gates controller active/valid states, while also showing that source timestamp and actively-tracked semantics can still be lost at later ROS boundaries.
