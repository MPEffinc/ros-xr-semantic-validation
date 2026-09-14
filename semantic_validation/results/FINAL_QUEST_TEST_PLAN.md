# Final Quest Hardware Campaign Plan

Written at the end of the Quest-free phase (2026-09-14). Every experiment below is specified to
the point where the hardware day requires **no dependency discovery, no environment build, no
topic discovery, no logger development, no harness development and no trial design** — with the
exceptions stated explicitly in §6, which are named rather than hidden.

Decision entering the hardware campaign: **`GO — NOT STRONG GO`**. The campaign exists to produce
the E5/E6 evidence that would justify moving it.

## 0. Preconditions common to every target

| Item | State |
| --- | --- |
| Desktop | Ubuntu 24.04, Docker via `sg docker`, images `ros-xr-humble:local`, `docker-teleop-humble:local`, `openvr-jazzy-sim:local`, `openvr-jazzy-runtime:local` all built |
| Robot-side | Raspberry Pi 4 `rosxr`, Ubuntu 22.04 arm64, native ROS 2 Humble, `semantic_robot_sink` built and proven (`PI_RECEIVED` only) |
| Dedicated link | desktop `enp3s0f1` 10.10.10.1/24 ↔ Pi `eth0` 10.10.10.2/24 |
| Quest 3 | **not yet authorised/connected** — the campaign's one universal prerequisite |
| Safety | no physical robot, no actuator, no CAN, no `robot_ip`, at any point in this campaign |

Every target below is Gazebo-only or observation-only. The launch files in the safety register of
[FRAMEWORK_TESTBED_ADAPTATION_PLAN.md](FRAMEWORK_TESTBED_ADAPTATION_PLAN.md) must never be run.

## 1. PickNik — highest value, white-box

- **Pinned revision:** `PickNikRobotics/meta_quest_teleoperation@bbaef0762fdb0b429b8ea12a4ca65040748b41dd`
- **Application/build:** Unity `6000.1.6f1` (installed) + `AndroidPlayer`; pinned `SampleScene`;
  APK build, install, launch on the Quest.
- **Backend:** vendored `Unity-Technologies/ROS-TCP-Endpoint@54c1a64`, rebuilt non-symlinked and
  proven to run. Command in
  [PICKNIK_QUESTLESS_CONVERGENCE.md](PICKNIK_QUESTLESS_CONVERGENCE.md) §6.
- **Device setup:** Quest on the same Wi-Fi as the desktop; `ROS_IP` set to the desktop's address
  on that network; `ROS_TCP_PORT=10000`; `ROS_DOMAIN_ID=71`.
- **Exact state transition:** occlude the tracked controller (cover the optical markers / place it
  out of headset view) until XRI `isTracked` goes false and the `trackingState` Position+Rotation
  bits clear, then reacquire. Five cycles.
- **Native XR state to record:** `isTracked`, `trackingState` bits, and the controller GameObject
  `Transform` on the Quest side-band log, plus focus / pause / XR-display-active so interrupted
  intervals can be excluded.
- **Downstream topics:** `/left_controller_odom`, `/right_controller_odom` (`nav_msgs/Odometry`),
  and `/tf` filtered to those two child frames.
- **Trial IDs:** `hw_baseline`, then `hw_t01` … `hw_t05`.
- **Logger:** `semantic_validation/harness/picknik_ros_observer.py` (proven, line-flushed,
  refuses to overwrite). Analyser: `picknik_hw_analyze.py` (self-test 4/4).
- **Stop condition:** five valid `valid → invalid → reacquired` intervals with no overlapping
  focus/pause interruption, or 20 minutes.
- **Success criterion:** each interval classifies as exactly one of
  `HW_PICKNIK_UNTRACKED_ROS_CONTINUES` / `HW_PICKNIK_NO_DOWNSTREAM_DURING_LOSS` /
  `HW_PICKNIK_PARTIAL_DOWNSTREAM_OBSERVATION`, with `distinct_ros_transforms` reported; ≥5
  intervals free of `INVALID_FOCUS_OR_XR_SESSION`.
- **Strongest possible evidence:** `E5 NATIVE_XR_TO_ROS`. Not E6 — the ROS consumer here is the
  project's observer, not MoveIt Pro.
- **Quest-only question:** when tracking is lost, does the controller `Transform` freeze,
  extrapolate, or reset — and does the 60 Hz Odometry/TF stream continue regardless while the
  header stamp keeps advancing?

## 2. Docker_Teleop — the gate-semantics question

- **Pinned revision:** `Noah727/Docker_Teleop@64cbdde88bc52c6a80d37f994752e50f95ba537e`
- **Application/build:** the in-tree Unity app (`HandPoseSender.cs`) built and installed on the
  Quest. Backend already built and proven: `docker-teleop-humble:local`, workspace colcon-built.
- **Simulator bring-up (never `servo_test.launch.py`):** `simulation/launch/run_tabletop_sim.sh`,
  then `servo_test_config/launch/servo_gz.launch.py`, then `quest_controller_receiver`,
  `hand_pose_mapper`, `servo_command_bridge` — the exact sequence already executed in
  [DOCKER_TELEOP_DOWNSTREAM_RUNTIME.md](DOCKER_TELEOP_DOWNSTREAM_RUNTIME.md).
- **Exact state transition:** hold grip/teleop active and drive the arm (the D1 condition), then
  **optically occlude the controller** without disconnecting it. Five cycles.
- **Native XR state to record:** `OVRInput.GetConnectedControllers()` and the serialised
  `isTracked` field in the outgoing wire payload, on the Quest side-band log.
- **Downstream topics:** `/received_pose_states`, `/target_twist_states`,
  `/servo_node/delta_twist_cmds`, `/joint_states` — all four already recorded to a bag in the
  synthetic run, with `extract_joint_state.py` proven against it.
- **Trial IDs:** `hw_dt_baseline`, `hw_dt_t01` … `hw_dt_t05`.
- **Logger:** `ros2 bag record` of the four topics (the synthetic run's bag schema), analysed with
  the existing `runs/docker_teleop_e2e_20260914/extract_joint_state.py`.
- **Stop condition:** five occlusion intervals in which the Quest log shows the controller
  remained *connected*, or 20 minutes.
- **Success criterion:** for each interval, whether the wire `isTracked` changed, and whether the
  simulated arm continued to move. The comparison baseline is D1 (`0.134070 m` Hand-E
  displacement) versus D2 (`8.19e-11 m`).
- **Strongest possible evidence:** `E6 NATIVE_XR_TO_NATIVE_CONSUMER` — this is the only target
  where actual Quest input can reach an original downstream software consumer (MoveIt Servo) and a
  simulated control effect, with no physical robot.
- **Quest-only question:** **does optical occlusion actually change
  `OVRInput.GetConnectedControllers()`?** If a connected-but-occluded controller keeps `isTracked`
  true, the gate-semantics mismatch becomes a hardware-confirmed finding rather than a
  source-level inference. This is the single highest-value question in the whole campaign.

## 3. Quest2ROS2 — black-box frontend, native ROS side

- **Pinned revision:** `Taokt/Quest2ROS2@07aaf65149c9e29103f1fc61deb466cef8a55cef`
- **Application/build:** the third-party Quest2ROS APK (frontend is outside the repository — this
  is the population's `PRINCIPAL_BLACKBOX`).
- **Backend:** already proven end-to-end — `SimulationInput` → production `RightArmController` →
  actual DDS → physical Pi, 619/619
  ([QUEST2ROS2_SIMULATIONINPUT_PI.md](QUEST2ROS2_SIMULATIONINPUT_PI.md)); reconnect behaviour
  characterised ([QUEST2ROS2_RECONNECT_RUNTIME.md](QUEST2ROS2_RECONNECT_RUNTIME.md)).
- **Device setup:** Quest2ROS app pointed at the desktop; `ROS_DOMAIN_ID=0`,
  `rmw_fastrtps_cpp`, dedicated link to the Pi.
- **Exact state transitions, two separate trials:**
  1. **Tracking degradation** — occlude the controller while streaming.
  2. **App disconnect/reconnect** — background or kill the Quest app for >2.5 s, then resume.
- **Native XR state to record:** whatever the app exposes on the wire (`/q2r_right_hand_pose` and
  the inputs topic) — the frontend is a black box, so the recording is of the *transport* state,
  and must be labelled as such.
- **Downstream topics:** `/q2r_right_hand_pose`, `/bh_robot/right_arm_clik_controller/target_frame`,
  and the Pi `semantic_robot_sink` JSONL (absolute `log_dir`, never `~`).
- **Trial IDs:** `hw_q2r_track_t01` … `t05`, `hw_q2r_reconnect_t01` … `t05`.
- **Logger:** `semantic_validation/harness/quest2ros2_simulationinput_pi.py` observation path,
  with the production node substituted for the simulator.
- **Stop condition:** five clean intervals per trial type, or 20 minutes each.
- **Success criterion:** for reconnect, whether the anchor/filter/`button_lower` latch state
  survives as it does synthetically; for degradation, whether the target frame keeps advancing.
- **Strongest possible evidence:** `E5 NATIVE_XR_TO_ROS` with `PI_RECEIVED`. **Not E6** — the
  original CLIK controller and gripper action server are absent from the repository and must not
  be fabricated.
- **Quest-only question:** how do actual app disconnect/reconnect and actual tracking degradation
  appear at the host, given that the frontend is unauditable?

## 4. Spes — the existing hardware case, now with a native ROS boundary

- **Pinned revision:** `SpesRobotics/teleop@c5d808155a87b584d6147a5943d4b87c34c92db0`
- **Already held:** actual Quest 3 controller-occlusion evidence, 5/5 valid trials —
  `emulatedPosition=true`, `source=CONTROLLER`, the production packet omitting that tracking
  semantic, the server target callback continuing, recovery 5/5 without user re-press. **Do not
  re-run this.**
- **New in this phase:** pinned upstream `teleop/ros2/__main__.py` executed unmodified to the
  physical Pi, 30/30 ([SPES_ROS_PI_INTEGRATION.md](SPES_ROS_PI_INTEGRATION.md)). Spes therefore
  now has a framework-native ROS boundary.
- **Exact remaining hardware experiment:** repeat the *existing* occlusion protocol with the
  upstream ROS 2 module attached, so that one continuous run spans actual Quest → Spes server
  callback → upstream ROS publisher → DDS → Pi.
- **Trial IDs:** `hw_spes_ros_t01` … `t05`.
- **Logger:** `launch_spes_quest_experiment.sh` orchestration (preflight 9/9 PASS) plus
  `spes_upstream_ros2_pi.py`.
- **Success criterion:** each emulated-tracking interval correlates to Pi reception by ordering,
  stamp and payload equality (`<1e-9`), as validated in the synthetic run.
- **Strongest possible evidence:** `E5 NATIVE_XR_TO_ROS` with `PI_RECEIVED`.
- **Quest-only question:** none new — the XR-side question is already answered. This run exists to
  upgrade the *boundary* of an existing hardware finding.

## 5. Optional fifth target

**OpenVR UR5e** would add a genuinely independent XR runtime (ALVR → SteamVR → OpenVR rather than
Meta's Unity/OpenXR path) and could reach `E6` in Gazebo, because its downstream consumer is now
proven to work ([OPENVR_UR5E_DOWNSTREAM_RUNTIME.md](OPENVR_UR5E_DOWNSTREAM_RUNTIME.md)). It is
optional because it requires an ALVR + SteamVR install that does not yet exist, and because the
repository is a low-maturity single-author project.

Its Quest-only question is nonetheless sharp: **does a real Quest 3 through ALVR/SteamVR ever
report `bPoseIsValid=true` together with `eTrackingResult=Running_OutOfRange`?** If it never does,
the `VALID`-vs-`TRACKED` finding is a latent-only gap for this stack, which is itself worth
stating.

## 6. What the hardware day still requires — stated honestly

These are the residual gaps. They are small, but the campaign is **not** literally
zero-development:

1. **Unity licence entitlement** on the operator's account. This blocks PickNik and Reachy, and it
   is an account action, not an engineering one.
2. **PickNik APK build** after activation. The project has no test assemblies, so there is no
   play-mode shortcut.
3. **Docker_Teleop Unity app build** for the Quest, which has not been attempted.
4. **Spes Quest orchestration does not yet attach a ROS publisher.** The wiring is specified in §4
   above but has not been executed; this is perhaps an hour of work and should be done *before*
   the hardware day, not during it.
5. **An authorised Quest 3**, ADB-connected.

## 7. Recommended order

1. **Docker_Teleop** — highest scientific value (`E6` reachable, answers the gate-semantics
   question), and its backend is the most thoroughly proven.
2. **PickNik** — the primary white-box case, once the licence exists.
3. **Spes** — cheap, upgrades an existing finding's boundary.
4. **Quest2ROS2** — black-box frontend, but the most widely referenced public stack.
5. **OpenVR UR5e** — only if an ALVR/SteamVR path is available.

## 8. What must not be claimed, whatever the campaign returns

- That any framework is `vulnerable`, `unsafe`, `secure` or `fail-safe`.
- That a physical robot moved or an actuator executed. No physical robot exists in this testbed.
- That `PI_RECEIVED` is actionability.
- That source-architecture breadth is runtime generality.
- That `emulatedPosition`, `isTracked`, `trackingState`, `IsTracked`, `GetConnectedControllers`,
  `bPoseIsValid`, `eTrackingResult`, `POSITION_VALID` and `POSITION_TRACKED` denote the same thing.
