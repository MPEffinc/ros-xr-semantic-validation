# OpenVR UR5e fake-runtime validation

## Scope

- Upstream repository: `mrutyunjaykalyani/teleoperation-of-a-UR5e-robot-in-Gazebo-using-Meta-Quest-3-via-ROS2-bridge-jazzy-`
- Pinned revision: `170dad582d624f536359a3192a7f829669c2b031`
- Production component: `src/quest_bridge/quest_bridge/quest_teleop.py`
- Runtime: isolated ROS 2 Jazzy container, `--network none`, `ROS_DOMAIN_ID=98`
- Injection boundary: minimal `openvr` API fake supplied through `PYTHONPATH`, upstream of the unmodified production decision logic
- Output boundary: actual ROS 2 `geometry_msgs/msg/PoseStamped` on `/servo_node/pose_target_cmds`
- Physical Quest, UR driver, physical robot, MoveIt Servo and Gazebo were not run in this experiment.

The container built the pinned `quest_bridge` package with `colcon build
--packages-select quest_bridge`, then ran the installed production console
entry point. The fake supplied only the OpenVR methods and constants used by
that production component.

## Trials

All trials used the same identity pose matrix, right-controller role and grip
state except where stated. The capture subscriber was started before the
production node. Each message retained `frame_id=base_link`, position
`[0.4, 0.0, 0.3]`, and orientation approximately
`[0.0, 0.70682518, 0.0, 0.70738827]` after production calibration.

| Trial | Fake OpenVR input | Actual ROS messages | Observed disposition |
| --- | --- | ---: | --- |
| V1 | `bPoseIsValid=true`, `eTrackingResult=Running_OK`, grip held | 70 | Published at approximately 50 Hz |
| V2 | `bPoseIsValid=true`, `eTrackingResult=Running_OutOfRange`, grip held | 65 | Published at approximately 50 Hz with the same pose payload as V1 |
| V3 | `bPoseIsValid=false`, `eTrackingResult=Running_OK`, grip held | 0 | Publication gated |
| V4 | valid/OK; grip held 20 callbacks, released 20, then held | 44 | Publication paused during release and resumed after re-engagement |

V1's median inter-message gap was `0.020001 s`; V2's was `0.020021 s`.
Their maximum gaps were `0.020382 s` and `0.020212 s`, respectively. V4's
maximum gap was `0.420732 s`; the production log recorded `Teleop
Disengaged.` followed by a second `Teleop Engaged: Relative tracking active.`

Counts differ slightly because DDS discovery time is part of the bounded
capture interval. The inference relies on publication presence, payload and
rate, not exact equality of counts.

## Result

At the tested dependency boundary, the production application distinguished
`bPoseIsValid=false` from valid poses and gated ROS publication. It did not
distinguish `Running_OK` from `Running_OutOfRange` while
`bPoseIsValid=true`: both produced equivalent ROS pose streams for identical
pose/grip input. Grip release gated publication and re-engagement caused the
production component to capture a new relative reference before publishing
again.

This is `E2 SYNTHETIC_RUNTIME`. It confirms behavior of the pinned production
application with a controlled fake OpenVR provider; it is not native Quest or
SteamVR/ALVR evidence. It also does not establish MoveIt Servo acceptance,
Gazebo motion, or physical actuator behavior.

## Reproduction and raw evidence

- Harness: `semantic_validation/harness/openvr_ur5e_fake_runtime/`
- Raw output: `semantic_validation/results/runs/openvr_ur5e_fake_runtime_20260914/`
- `V*_node.log` records the injected validity/tracking-result configuration and production lifecycle decisions.
- `V*_pose.json` records every actual ROS message received during the capture interval.

The harness runs all trials in one fresh container execution, isolates each
production node in its own process group, and terminates it after its fixed
capture window so no publisher survives into the next trial.
