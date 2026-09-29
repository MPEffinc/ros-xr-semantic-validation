# OpenVR UR5e downstream runtime — MoveIt Servo and Gazebo consequence

## Scope

- Upstream repository: `mrutyunjaykalyani/teleoperation-of-a-UR5e-robot-in-Gazebo-using-Meta-Quest-3-via-ROS2-bridge-jazzy-`
- Pinned revision: `170dad582d624f536359a3192a7f829669c2b031` (worktree unmodified)
- Production component: `src/quest_bridge/quest_bridge/quest_teleop.py`
- Runtime: ROS 2 Jazzy container `openvr-jazzy-sim:local`, `--network none`, `--cap-drop ALL`,
  `--security-opt no-new-privileges`, `ROS_DOMAIN_ID=98`, `rmw_fastrtps_cpp`
- Injection boundary: a minimal `openvr` API fake supplied through `PYTHONPATH`, upstream of
  every production decision in `quest_teleop.py`
- Executed chain:

```text
fake OpenVR provider (raw controller pose + bPoseIsValid + eTrackingResult + grip)
-> production quest_teleop                     (unmodified, pinned)
-> /servo_node/pose_target_cmds  PoseStamped   (actual ROS 2)
-> MoveIt Servo  (moveit_servo/servo_node, POSE command mode)
-> /ur5_arm_controller/joint_trajectory        (JointTrajectory)
-> joint_trajectory_controller -> gz_ros2_control -> Gazebo Sim
-> /joint_states                               (simulated robot feedback)
```

No Quest, no SteamVR/ALVR, no UR driver, no `robot_ip`, no physical robot and no actuator were
involved. The pinned repository contains **no physical-driver path at all**: a repo-wide search
for `robot_ip`, `ur_robot_driver`, `ur_bringup` and any IP literal returns zero matches, and the
installed image contains no `ur_robot_driver` package.

This extends [OPENVR_UR5E_FAKE_RUNTIME.md](OPENVR_UR5E_FAKE_RUNTIME.md), which stopped at the
ROS publication boundary, to the native downstream consumer and the simulated robot.

## Environment deviations (deliberate, recorded)

1. The simulation dependencies (`ros-jazzy-moveit`, `moveit-servo`, `ros-gz-sim`, `ros-gz-bridge`,
   `gz-ros2-control`, `ros2-controllers`) were installed into a purpose-built image. The pinned
   repository is otherwise self-contained; no application source was changed.
2. Gazebo was run headless under `xvfb-run`, because the pinned `gazebo.launch.py` starts the GUI
   unconditionally.
3. The pinned `ur5_servo.launch.py` starts its own `robot_state_publisher` in addition to the one
   started by `gazebo.launch.py`. Both pinned launch files were used as written, so two instances
   run; both publish the same TF from the same URDF.
4. `moveit_servo` in Jazzy starts in `JOINT_JOG` command mode. Before every trial, including the
   baseline, the standard operator-facing service `/servo_node/switch_command_type` was called with
   `command_type: 2` (POSE) and returned `success=True`. This is a service call, not a source
   change, and it was applied **identically to all four trials**, so it cannot account for any
   difference between them.
5. The fake OpenVR module adds a linear translation to the **raw controller pose** so that a
   motion consequence can exist at all. The earlier ROS-boundary fake emitted a static pose, which
   after the production node's own relative calibration yields a constant target. The translation
   is applied strictly upstream of `bPoseIsValid`, the grip deadman and the calibration logic.

## Trials

All four trials used a fresh Gazebo / controller / Servo bring-up so that each starts from the
same arm configuration, and an identical 14 s capture window. Controllers active in every trial:
`joint_state_broadcaster`, `ur5_arm_controller` (`joint_trajectory_controller`), `hand_controller`.

| Trial | `bPoseIsValid` | `eTrackingResult` | Production ROS poses | Servo `JointTrajectory` out | `/joint_states` samples | Max joint excursion (rad) | Max abs joint velocity (rad/s) |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |
| W0 baseline (no production node) | — | — | 0 | 0 | 893 | `1.173248e-10` | `5.645491e-05` |
| W1 | `true` | `Running_OK` | 543 | 537 | 910 | `1.536350e+00` | `2.073817e+00` |
| W2 | `true` | `Running_OutOfRange` | 511 | 520 | 919 | `1.536454e+00` | `2.056010e+00` |
| W3 | `false` | `Running_OK` | 0 | 0 | 930 | `3.592504e-11` | `5.645491e-05` |

In W1 and W2 the production node's commanded `pose.position.z` swept to the same endpoint
(`0.450000` in both); `frame_id` was `base_link` and the orientation payload was identical in every
published message of both trials.

### W1 versus W2 — the decisive comparison

Per-joint displacement from each trial's own first sample to its last:

| Joint | W1 delta (rad) | W2 delta (rad) | Difference |
| --- | ---: | ---: | ---: |
| `shoulder_pan_joint` | `-0.276379` | `-0.276379` | `0.000000` |
| `shoulder_lift_joint` | `-0.235478` | `-0.235477` | `1.0e-06` |
| `elbow_joint` | `+0.481535` | `+0.481516` | `1.9e-05` |
| `wrist_1_joint` | `-0.194376` | `-0.194278` | `9.8e-05` |
| `wrist_2_joint` | `+1.287733` | `+1.287766` | `3.3e-05` |
| `wrist_3_joint` | `-1.536350` | `-1.536454` | `1.04e-04` |

The two trials agree on every joint to within `1.04e-04 rad`, against excursions of up to
`1.54 rad`. The residual is consistent with bring-up and capture-start jitter — the trials
published 543 and 511 messages respectively over the same window — and not with any difference in
handling.

### W3 versus W0 — the gate that does work

W3's maximum joint excursion (`3.59e-11 rad`) is below the W0 no-command baseline
(`1.17e-10 rad`), and its maximum joint velocity is identical to the baseline to all printed
digits. With `bPoseIsValid=false` the production node published nothing, Servo emitted no
controller command, and the simulated arm was indistinguishable from an idle simulator.

## Result

At the tested dependency boundary, and now carried through to the native downstream consumer and
the simulated robot:

- `bPoseIsValid=false` is **`GATED`**: no ROS publication, no Servo command, no simulated motion
  (`NO_OUTPUT`).
- With `bPoseIsValid=true`, `Running_OK` and `Running_OutOfRange` are **`DROPPED`**: the
  production node never reads `eTrackingResult` (`quest_teleop.py:49` tests only `bPoseIsValid`),
  so the two produce equivalent ROS pose streams, equivalent Servo controller commands, and
  simulated arm motion agreeing to `1.04e-04 rad` across a `1.54 rad` excursion.

This is the `VALID`-versus-`TRACKED` gap carried from source, through actual ROS 2 transport,
through an unmodified native consumer (MoveIt Servo), to a measured simulated-robot consequence.
It was previously documented for NVIDIA IsaacTeleop's OpenXR path and for this framework only at
the ROS publication boundary.

Semantic disposition: `GATED` for `bPoseIsValid`, `DROPPED` for `eTrackingResult`.
Downstream consequence: `NATIVE_CONSUMER_ACCEPTED` plus a simulated control effect.

## Evidence level and limits

`E2 SYNTHETIC_RUNTIME` with `UPSTREAM_FAITHFUL_REPLAY` for the ROS-side logic: the injection point
is the OpenVR dependency, which is upstream of the validity gate, the grip deadman and the
calibration state under study, and all of that production logic remained active.

What this does **not** establish:

- Any native Quest, SteamVR or ALVR behaviour. Whether a real Quest 3 through ALVR/SteamVR ever
  reports `bPoseIsValid=true` together with `Running_OutOfRange` is not answered here; that is the
  Quest-only question for this framework.
- Physical actuator execution. The joint values are Gazebo's `/joint_states` feedback through
  `gz_ros2_control`; no physical robot exists in this testbed.
- Production-grade representativeness. The pinned repository is a low-maturity single-author
  project.
- Anything about `/servo_node/status`. Servo published **zero** status messages in all four
  trials, including the baseline, so the status channel was not available as an observable and no
  inference is drawn from its absence. `servo_node` also logged `Waiting to receive robot state
  update.` as its last line in every trial while nevertheless producing 537 and 520 controller
  commands in W1 and W2 — the message is not a functional blocker here, and no claim rests on it.

## Reproduction and raw evidence

- Harness: `semantic_validation/harness/openvr_ur5e_downstream/`
  (`Dockerfile`, `openvr.py` fake, `build_ws.sh`, `run_trial.sh`, `capture_downstream.py`,
  `analyze_downstream.py`, `diag.sh`)
- Raw output: `semantic_validation/results/runs/openvr_ur5e_downstream_20260914T065659Z/`
  - `W*_downstream.json` — every captured `PoseStamped`, `JointTrajectory` and `JointState`
  - `W*_node.log` — the production node's own lifecycle log and the injected fake configuration
  - `W*_servo.log`, `W*_gazebo.log`, `W*_controller.log`, `W*_controllers.txt` — bring-up evidence
  - `W*_switch.log` — the command-type switch call and its response
  - `summary.json` — the aggregate produced by `analyze_downstream.py`
  - `diag/` — the standalone bring-up diagnostic (`/clock` rate, `/joint_states`, TF, parameters)
