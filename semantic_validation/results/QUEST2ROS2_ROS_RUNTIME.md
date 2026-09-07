# Quest2ROS2 actual ROS 2 transport validation

## Result

**`PASS` — actual ROS 2 transport with the actual pinned production node was executed.**

Canonical run: `quest2ros2_ros_runtime_20260907T050835Z`
(2026-09-07 05:08:35 UTC / 14:08:35 KST).

Classification under [EVIDENCE_LEVELS_V2](../methodology/EVIDENCE_LEVELS_V2.md):

| Axis | Value | Reason |
| --- | --- | --- |
| Evidence level | **E2 `SYNTHETIC_RUNTIME`** | the pose source is a synthetic publisher, not an actual Quest or the Quest2ROS2 Unity frontend |
| Qualifier | **actual ROS 2 transport + actual production node** | the previous `BLOCKED_ENV` limitation on `F-Q2R-001/002` is resolved |
| Semantic disposition (I3 source time) | **`DROPPED` / re-generated** | 7/7 cases: `source_stamp_preserved=false` |
| Semantic disposition (I2 frame provenance) | **`DROPPED` / replaced** | 7/7 cases: `source_frame_preserved=false`, substituted with configured `bh_robot_base` |
| Downstream consequence | **`NATIVE_CONSUMER_ACCEPTED`** | the framework's own production consumer node accepted the input and published its control target |

This is the project's first `NATIVE_CONSUMER_ACCEPTED` observation. It is **not** E5/E6:
the input never came from actual XR hardware, so no native XR claim is created. It also
never reached an actuator: the original CLIK controller and gripper action server were
absent (see Downstream boundary below).

## Environment and isolation

| Check | Observation |
| --- | --- |
| Docker daemon | accessible (`docker_daemon_accessible: true`) |
| Container network | `none` |
| Robot / driver / gripper hardware | `robot_or_driver_used: false` |
| Target repository | `Taokt/Quest2ROS2@07aaf65149c9e29103f1fc61deb466cef8a55cef` |
| Target worktree | clean **before and after** (`target_clean_before/after: true`) |
| Production callback | `production_callback_delegated_unchanged: true`; side-band records only an entry timestamp before calling the unchanged `super()._pose_callback` |

Immediately before this run, the same harness recorded `BLOCKED_ENV` at
`quest2ros2_ros_runtime_20260907T050818Z` because that process had no effective
`docker` group membership. Both directories are retained: the blocked one documents the
exact blocking condition, the later one is canonical. The 2026-08-31 blocked probe
(`quest2ros2_ros_runtime_20260831T150939Z`) is likewise retained as history.

## Executed path

```text
synthetic PoseStamped publisher (age/frame sweep)
 -> actual ROS 2 subscription of the pinned production node
    q2r2_bringup.right_arm_controller.RightArmController  ("right_kuka_arm_controller")
    input topic: /q2r_right_hand_pose
 -> unchanged production _pose_callback
 -> actual production target publisher
    output topic: /bh_robot/right_arm_clik_controller/target_frame
 -> dummy target subscriber (observation only)
```

A dummy static TF `bh_robot_base <- right_arm_link_ee` was supplied as a fixture.

## Age and frame-provenance sweep — actual transport

| Trial | Requested input age | Published? | Source stamp preserved? | Source frame preserved? | Input frame → output frame |
| --- | ---: | --- | --- | --- | --- |
| `age_10ms` | 10 ms old | yes | no | no | `xr_controller_A` → `bh_robot_base` |
| `age_100ms` | 100 ms old | yes | no | no | `xr_controller_B` → `bh_robot_base` |
| `age_500ms` | 500 ms old | yes | no | no | `old_reference_space` → `bh_robot_base` |
| `age_1s` | 1 s old | yes | no | no | `new_reference_space` → `bh_robot_base` |
| `age_3s` | 3 s old | yes | no | no | `xr_controller_A` → `bh_robot_base` |
| `age_10s` | 10 s old | yes | no | no | `old_reference_space` → `bh_robot_base` |
| `future_1s` | 1 s in the future | yes | no | no | `new_reference_space` → `bh_robot_base` |

Aggregates recorded by the harness: `all_age_cases_published: true`,
`all_source_stamps_replaced: true`,
`all_source_frames_replaced_with_configured_base: true`,
`frame_provenance_sweep_complete: true`, `trial_count: 7`.

The callback-only E2 result in [QUEST2ROS2_STALE_RESTAMP.md](QUEST2ROS2_STALE_RESTAMP.md)
is therefore reproduced across an actual DDS boundary and the actual node, rather than
against test doubles.

## Downstream boundary — exactly where this stops

- The node logged `Waiting for gripper action server:
  /bh_robot/right_arm_gripper_action_controller/gripper_cmd`; that server was **not**
  present. The original gripper path was not exercised.
- The original CLIK controller that consumes
  `/bh_robot/right_arm_clik_controller/target_frame` was **not** running; a dummy
  subscriber observed the topic instead.
- Therefore `NATIVE_CONSUMER_ACCEPTED` applies to the arm-controller node itself
  (it accepted input and emitted a control target). It does **not** mean the robot's
  own controller accepted a command, and it is **not** `ACTUATOR_STUB_COMMAND` or any
  actuator claim.

## What this does and does not support

Supports:

- Under actual ROS 2 transport, the pinned production consumer publishes a control
  target for inputs aged 10 ms to 10 s and for a 1 s future stamp, with no observed
  age gate at this boundary.
- Source stamp and input `frame_id` are not carried into the emitted control target.

Does not support:

- Any claim about the actual Quest2ROS2 Unity/Quest frontend, which is not exercised
  here and whose XR-side semantics remain a black box in this repository.
- Any claim that a physical or simulated robot moved, or that a real robot controller
  accepted the target.
- Any upgrade of `F-Q2R-001/002` to E5/E6.

## Reproduce

```bash
cd /home/cclab/ros_xr
sg docker -c "python3 semantic_validation/harness/run_quest2ros2_ros_runtime.py"
```

The harness re-probes the environment, copies the pinned target into a temporary
workspace, runs the container with `--network none`, `--cap-drop ALL`, and
`no-new-privileges`, and writes a new immutable evidence directory under
`semantic_validation/logs/quest2ros2_ros_runtime/`.

Artifacts for the canonical run:
[`summary.json`](../logs/quest2ros2_ros_runtime/quest2ros2_ros_runtime_20260907T050835Z/summary.json),
[`transport_summary.json`](../logs/quest2ros2_ros_runtime/quest2ros2_ros_runtime_20260907T050835Z/transport_summary.json),
[`transport.jsonl`](../logs/quest2ros2_ros_runtime/quest2ros2_ros_runtime_20260907T050835Z/transport.jsonl),
[`environment.jsonl`](../logs/quest2ros2_ros_runtime/quest2ros2_ros_runtime_20260907T050835Z/environment.jsonl),
[`container.stdout.txt`](../logs/quest2ros2_ros_runtime/quest2ros2_ros_runtime_20260907T050835Z/container.stdout.txt),
[`container.stderr.txt`](../logs/quest2ros2_ros_runtime/quest2ros2_ros_runtime_20260907T050835Z/container.stderr.txt).

## Scope boundary

- No actual Quest input was used; no XR runtime was executed.
- No robot, robot controller, gripper server, or hardware driver was connected.
- The container had no network access to the host or the dedicated research link.
- No upstream file changed; the pinned target was clean before and after.
- Pi `semantic_robot_sink` was not involved in this run.
