# Quest2ROS2 Quest 3 Feasibility Result — 2026-09-17

## Scope and safety

- Framework: `Taokt/Quest2ROS2@07aaf65149c9e29103f1fc61deb466cef8a55cef`.
- Actual external Quest application: `com.Tiguin.Q2R` version `1.1`, with its
  UI configured as `ROS2`.
- No physical robot, robot driver, CLIK controller, gripper action server, CAN
  endpoint, or actuator was launched. A static TF fixture only supplied the
  in-repo controller's current-pose lookup; the final target topic had no
  physical consumer.

## Actual Quest to production-controller feasibility

The Quest app connected from `192.168.0.178` to `192.168.0.3:10000` and
registered `/q2r_right_hand_pose` and `/q2r_right_hand_inputs`. The pinned
repository specifies an external bridge,
`guguroro/ros_tcp_communication@5c5f08956d4bc7a045c321214b0bc03c63eb20a7`.
Its unmodified current implementation was not compatible with this app:

1. it parsed NUL-terminated system-command JSON without removing the NUL;
2. it treated the four-byte ROS 2 CDR encapsulation as user data; and
3. its pose decoder read doubles from offset 16, although this observed
   `PoseStamped` wire payload begins at offset 20 after the CDR/header fields.

An isolated `/tmp` copy of that **external** bridge was adapted solely to
strip the NUL command terminator and decode the observed ROS 2 CDR layout
(pose offset 20; input/twist payload after the four-byte encapsulation). The
pinned `Quest2ROS2` checkout and `RightArmController` were unchanged.

With that transport-only compatibility adaptation, the actual Quest app
published 5,098 right poses and 5,098 right input messages. The unchanged
production `RightArmController` accepted them and published 2,153
`/bh_robot/right_arm_clik_controller/target_frame` messages. During a normal
right-controller movement, production target values changed, for example,
from `(0.8827, 0.1435, 0.3181)` to `(0.8429, 0.0823, 0.2475)`.

## Visibility/degradation action

One additional actual Quest trial was recorded after the user performed the
requested normal movement, camera-visibility degradation, and recovery
sequence. The black-box host-side output contained 6,526 right poses and the
same number of right inputs. Its pose stream had segments of 613, 4,765, and
1,148 messages, separated by 30.295 s and 0.796 s arrival gaps. The final
segment continued for 15.171 s after the 0.796 s gap before source arrival
stopped.

There is no app-side raw tracking-validity/state capture or trial-phase marker
for this external frontend. Therefore the observed gaps and final stop cannot
be attributed specifically to optical tracking degradation rather than app
focus, transport lifecycle, or another external-app condition. The correct
classification is **`NO_TRANSITION_OBSERVED`** for XR tracking semantics, not
a tracking-loss finding.

## Feasibility decision

| Question | Result |
| --- | --- |
| Actual Quest app can reach the unchanged in-repo production controller | **PASS**, through the documented external bridge after isolated CDR compatibility adaptation |
| Actual controller pose affects the original production target topic | **PASS** — 2,153 targets, no final consumer |
| Unmodified documented external bridge is app-compatible | **FAIL** — NUL/CDR parsing incompatibility observed |
| Actual optical tracking semantic transition is observed | **NO_TRANSITION_OBSERVED** |
| Physical robot/actuator evidence | **None** |

This is actual Quest runtime evidence for an **adapted external transport →
unchanged production controller** boundary. It is not unmodified native
frontend-to-control evidence, does not establish E5 for a tracking semantic
transition, and provides no E6 or physical-action claim.

## Raw evidence (not committed)

| Run root | Purpose | Key SHA-256 |
| --- | --- | --- |
| `hw_quest2ros2_cdr_20260917T093000Z` | CDR-compatible actual Quest baseline and production target | `bag_0.db3` `bf23dea2f3c4abad4348d0e5613dfc948fd0af4f8525914014a4d9990a8613f2` |
| `hw_quest2ros2_visibility_20260917T094000Z` | Single actual visibility/recovery action | `bag_0.db3` `409a46dc5c642c74e8d5a1d339d3d8269750ffe40afff9558f738566a9fbae1e` |

Earlier diagnostic runs remain preserved under
`hw_quest2ros2_native_20260917T085500Z`,
`hw_quest2ros2_compat_20260917T091000Z`, and
`hw_quest2ros2_offset20_20260917T092500Z`.

## Exact remaining requirement

For a genuine tracking-semantics feasibility result, add a noninterfering
app-side raw-state capture or a reproducible host-side transition marker, then
observe one valid transition through the same adapted-transport/in-repo
controller path. Do not infer internal `isTracked` or equivalent state from
this black-box app.
