# FRAMEWORK: Quest2ROS2 (Taokt)

## Identity

- Repository: `https://github.com/Taokt/Quest2ROS2.git`
- Revision: `07aaf65149c9e29103f1fc61deb466cef8a55cef` (2026-03-06), worktree clean, single branch `main`
- Local checkout: `semantic_validation/targets/quest2ros2`
- XR frontend: **external** — the `quest2ros` headset app (`README.md:20`, `https://quest2ros.github.io/`)
- Transport bridge: **external** — `ros_tcp_communication` cloned separately (`README.md:26-30`)

## Architecture

```text
Meta Quest 2/3
  -> quest2ros headset app                       [EXTERNAL, not in repo]
  -> ROS-TCP (ros_tcp_communication)             [EXTERNAL, not in repo]
  -> /q2r_{left,right}_hand_pose   [geometry_msgs/PoseStamped]
     /q2r_{left,right}_hand_inputs [quest2ros/OVR2ROSInputs]
  -> q2r2_bringup BaseArmController / {Left,Right}ArmController   [IN REPO]
  -> /bh_robot/{left,right}_arm_clik_controller/target_frame  [PoseStamped]
     /bh_robot/{left,right}_arm_gripper_action_controller/gripper_cmd [GripperCommand]
  -> CLIK Cartesian controller + gripper action server        [EXTERNAL, not in repo]
```

## System Relevance

- Classification: **`HIGH_XR_ROS_CONTROL`**
- Why: the in-repo node is the actual control-producing consumer that turns XR hand pose into a Cartesian target for a bimanual robot. That the frontend and the final controller live outside the repository does not reduce system relevance; it changes observability.

## Semantic Observability

| Axis | Finding | Evidence |
| --- | --- | --- |
| I1 tracking validity | **Absent on the ROS side.** Repo-wide grep for `isTracked / trackingState / IsPoseValid / confidence`: zero hits. Whatever validity handling exists is inside the external headset app. | full-tree grep |
| I2 source identity | Left/right preserved by topic and by node instance (`mirror` flag can deliberately cross them). Input `frame_id` is never read; output `frame_id` is hardcoded to `base_frame_id`. | `right_arm_controller.py:8-14`; `robot_arm_controller_base.py:303` |
| I3 source time | **DROPPED.** `pose_stamped.header` is never accessed in `_pose_callback`; only `pose.position/orientation` are read. Output is stamped `self.get_clock().now()`. No age or future-stamp validation. | `robot_arm_controller_base.py:178,181-182,211-308,304` |
| I4 session/generation | **Absent, with a specific consequence.** No subscription-status callback, no watchdog timer. Filter deques and the pose anchors persist across a disconnect and are cleared **only** on a `button_lower` rising edge. A reconnecting client that resumes streaming without a button press continues computing offsets from the pre-disconnect anchor. | `robot_arm_controller_base.py:334-384`, `:368-381`; absence confirmed by full read |
| I5 invalidation/re-arm | **Toggle, not deadman, and enabled by default.** `allow_pose_update` initialises to `True`, so publishing is armed at node start before any operator action; `button_lower` rising edge *toggles* it. There is no hold-to-drive requirement. | `robot_arm_controller_base.py:89` (default `True`), `:220-221` (gate), `:356-358` (toggle) |
| Source visibility | **`BLACK_BOX_XR_FRONTEND` + `FULL_SOURCE` host side.** | — |

Notable: the repository *contains* a working freshness watchdog — `QuestMonitor` in
`CheckTCPconnection.py:34-138` flags `time_since_last_msg > 2.0` as "Signal Lost" — but it is a
standalone diagnostic tool and is **not wired into the control path**. The author was evidently
aware of the need; the control node does not use it.

## Native Decisions

- Tracking gate: none in-repo.
- Validity gate: none in-repo.
- Deadman/clutch: a latching toggle, default-on (see I5). This is materially weaker than a
  hold-to-drive deadman and is a source-visible design decision, not an inference.
- Freshness: none in the control path.
- Recovery: manual only — the operator must press `button_lower` to clear the filter and re-anchor.
- Filter warm-up: 20 samples; `_apply_moving_average_filter` returns `(None, None)` while filling, so nothing is published during warm-up.

## Control Depth

- Last auditable in-source boundary: **`/bh_robot/right_arm_clik_controller/target_frame` publish** at `robot_arm_controller_base.py:306`.
- Original consumer: an external CLIK Cartesian controller for a `bh_robot` KUKA-class bimanual robot, plus a `control_msgs/GripperCommand` action server. Neither is in the repository.
- Physical driver dependency: yes for real operation (`README.md:14-15,135-137`), entirely external.
- Classification achieved so far: **`NATIVE_CONSUMER`** — the arm controller itself is the framework's own consumer, and it has been executed.

## Testbed Adaptation — status: **EXECUTED**

| Question | Answer |
| --- | --- |
| Desktop Humble usable? | **Yes, demonstrated.** |
| Can publish to Pi? | **Yes, demonstrated** (see runs below). |
| Simulator available? | **Yes, in-repo**: `q2r2_bringup/SimulationInput.py` is the framework's own "Fake Quest" (`ros2 run q2r2_bringup SimulationInput`). |
| Inert stub feasible? | Yes — a static TF fixture satisfies `_get_robot_current_pose()`; the CLIK controller is simply left absent. |
| Production path preserved? | Yes — the pinned `_pose_callback` runs unchanged; only a side-band entry timestamp is recorded. |
| Replay injection boundary | At `/q2r_{side}_hand_pose`, i.e. **downstream of the external headset app**. All in-repo semantic logic (toggle gate, filter, anchoring, re-stamping, frame substitution) remains active, so it is `UPSTREAM_FAITHFUL_REPLAY` **with respect to in-repo logic only**; it is `BOUNDARY_LIMITED_REPLAY` with respect to any XR-side gate, which is unobservable here. |

## Quest-less Potential — achieved

Two runs exist:

1. `logs/quest2ros2_ros_runtime/quest2ros2_ros_runtime_20260907T050835Z` — harness-authored synthetic
   publisher → actual node → actual publisher → dummy subscriber, in a `--network none` container.
   7/7 age cases (10 ms to 10 s old, 1 s future) published; 7/7 source stamps replaced; 7/7 input
   frames replaced with `bh_robot_base`. See [QUEST2ROS2_ROS_RUNTIME.md](../../results/QUEST2ROS2_ROS_RUNTIME.md).
2. `logs/quest2ros2_simulationinput_pi/` — the framework's **own** `SimulationInput` → actual node →
   actual DDS over the dedicated Ethernet → physical Pi `semantic_robot_sink` subscribed directly to
   the production output topic (no republishing hop).

Both are E2. Neither is an XR-hardware result.

## Future Quest Test

- T0: headset app connected, `button_lower` pressed once to establish the anchor, 10 s baseline.
- T1: occlude the controller 3–5 s. The decisive question is what the **external app** does — does it stop publishing, publish a frozen pose, or publish an extrapolated pose? The in-repo node has no gate, so whatever arrives is filtered, offset, and published.
- T4 (distinctive to this framework): **disconnect/reconnect without pressing `button_lower`.** Source analysis predicts the stale pre-disconnect anchor is reused. This is a framework-specific I4 experiment that no other target in the population offers as cleanly.
- Observable raw transition: app-side is a black box, so the observable set is limited to the ROS wire — arrival gaps, pose discontinuity, and the resulting target jump.
- Manual steps: connect app, anchor, occlude/recover ×5; then a separate disconnect/reconnect protocol.

## Research Value

- RQ: strong. It is the clearest **black-box-frontend** principal case: a real, widely referenced Quest→ROS 2 stack whose control node demonstrably drops source time and frame provenance and whose arming is a default-on toggle.
- Invariants: I3 (dropped, now demonstrated on actual ROS transport), I2 frame provenance (replaced), I4 (stale anchor across reconnect — source-visible absence), I5 (toggle semantics).
- White-box/black-box: **`PRINCIPAL_BLACKBOX`** for XR semantics; white-box for the ROS control node.
- Independent architecture: yes — external app + ROS-TCP + in-repo controller, distinct from Docker_Teleop's bespoke TCP and from WebXR/WSS.
- Generality contribution: it is the external-validity anchor. It shows the ROS-side pattern is not unique to a research adapter.

## Weaknesses

- The XR frontend and the transport bridge are both outside the pinned repository, so no XR-side claim can ever be made from this target alone.
- Message-package naming is internally inconsistent (`quest2ros` in the controllers, `quest2ros2_msg` in `ros2quest.py` and `package.xml:20`, `quest2ros` in the README build step) — a reproducibility hazard that the harness works around by building `Files_for_msg_pkg` as `quest2ros`.
- The final CLIK controller is absent, so `NATIVE_CONSUMER_ACCEPTED` stops at the arm controller.

## Final Role

- **`PRINCIPAL_BLACKBOX`**
- **`AUXILIARY_WIRE`** for the external `ros_tcp_communication` boundary (not audited)

## Priority

**S** — the only principal target with an executed actual-ROS-transport runtime, an in-repo simulator, and a genuinely distinct black-box-frontend character.
