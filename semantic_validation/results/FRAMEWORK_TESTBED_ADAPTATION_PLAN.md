# Framework Testbed Adaptation Plan

Current testbed (verified 2026-09-07):

| Component | State |
| --- | --- |
| Desktop | Ubuntu 24.04, Docker OK via `sg docker`, image `ros-xr-humble:local` (Humble, host network, `ROS_DOMAIN_ID=0`, `rmw_fastrtps_cpp`); `ros:jazzy-ros-base` also present |
| Robot-side | Raspberry Pi 4 `rosxr`, Ubuntu 22.04 arm64, native ROS 2 Humble, `semantic_robot_sink` |
| Dedicated link | desktop `enp3s0f1` 10.10.10.1/24 ↔ Pi `eth0` 10.10.10.2/24, no gateway |
| DDS | bidirectional talker/listener verified; container-with-`--cap-drop ALL --user` → Pi verified this session |

Absolute constraints: no Quest, no physical robot, no driver, no actuator. `semantic_robot_sink`
sets only `PI_RECEIVED`.

## Tier 1 — completed this session

### Quest2ROS2 (S)

- **Done:** actual ROS 2 transport with the pinned production node (`--network none`), age/frame
  sweep. → [QUEST2ROS2_ROS_RUNTIME.md](QUEST2ROS2_ROS_RUNTIME.md)
- **Done:** in-repo `SimulationInput` → production node → DDS → physical Pi, 619/619.
  → [QUEST2ROS2_SIMULATIONINPUT_PI.md](QUEST2ROS2_SIMULATIONINPUT_PI.md)
- Harness: `semantic_validation/harness/quest2ros2_simulationinput_pi.py`
- **Remaining for this target:** an inert stand-in for the CLIK controller so the next consumer
  boundary can be observed; and a disconnect/reconnect protocol to demonstrate the stale-anchor
  behaviour at runtime rather than only in source.

## Tier 2 — next, highest value per unit of effort

### Docker_Teleop (S)

Goal: exercise the **true wire boundary**, which is upstream of every ROS-side semantic gate, and
observe the effect at MoveIt Servo and in Gazebo.

1. Build an x86_64 backend image from `ros_backend1.1/Dockerfile` with the base changed from
   `arm64v8/ros:humble-ros-base` to `ros:humble-ros-base`. **Record this as a deliberate
   environment deviation** in the run report; it does not touch application source.
2. Bring up the simulator path only: `simulation/launch/run_tabletop_sim.sh`, then
   `servo_test_config/launch/servo_gz.launch.py`, then `quest_controller_receiver`,
   `hand_pose_mapper`, `servo_command_bridge`. **Never** `servo_test.launch.py` (it includes
   `ur_robot_driver` with `robot_ip`).
3. Write a synthetic TCP client that speaks the newline-JSON schema from
   `HandPoseSender.cs:249-261`. This is the injection point that yields
   `UPSTREAM_FAITHFUL_REPLAY` for the ROS-side gates.
4. Experiments, all robot-free:
   - **D1 baseline:** `isTracked=true`, grip held → expect non-zero twist and simulated motion.
   - **D2 tracked=false:** flip only `isTracked` → expect `tracked_ok` false, zero twist,
     no motion. Confirms the gate is real end to end.
   - **D3 stall:** stop sending for >0.25 s → expect neutral-state substitution, zero twist,
     Servo halt. Confirms recovery policy.
   - **D4 stale source time:** send an old Unity `timestamp` with fresh arrival → expect **no
     effect**, because the receiver never reads it. Confirms the I3 drop.
   - **D5 client replacement:** open a second TCP connection → expect silent takeover with no
     handshake and no state reset. Confirms the I4 gap.
5. Observe in parallel on the Pi via `semantic_robot_sink` on `/target_twist_states` or the joint
   command topic; label reception `PI_RECEIVED` only.

Expected outcome: E2 with `UPSTREAM_FAITHFUL_REPLAY`, downstream consequence up to
`NATIVE_CONSUMER_ACCEPTED` and simulated control effect. This would be the project's first
simulator-backed native-consumer result.

### OpenVR UR5e (A)

Goal: demonstrate the `VALID`-vs-`TRACKED` gap at runtime in the OpenVR family.

1. Build a Jazzy container from `ros:jazzy-ros-base` with MoveIt, `moveit_servo`, `ros_gz_sim`,
   `gz_ros2_control`, plus the external `ur_simulation_gazebo` package the README requires.
2. Substitute a **fake `openvr` Python module** on `PYTHONPATH` returning controlled
   `TrackedDevicePose_t` values. This is a dependency-boundary substitution; `quest_teleop.py` is
   not modified, so its `bPoseIsValid` gate at `:49` and its grip deadman at `:51-59` stay active.
3. Experiments:
   - **V1:** `bPoseIsValid=true`, `eTrackingResult=Running_OK`, grip held → publishes.
   - **V2:** `bPoseIsValid=true`, `eTrackingResult=Running_OutOfRange` → **predicted: still
     publishes**, because `eTrackingResult` is never read. This is the decisive trial.
   - **V3:** `bPoseIsValid=false` → predicted: no publish.
   - **V4:** grip released mid-motion → predicted: publishing stops; on re-engage the offset
     re-anchors (`first_packet=True`).
4. Keep this entirely inside the Jazzy container. Do **not** attempt cross-distro Jazzy↔Humble DDS
   to the Pi for canonical evidence; if reception on the Pi is wanted, label the distro mismatch
   explicitly.

### OpenArmX bridge only (B)

Goal: demonstrate the preserve-then-drop I3 behaviour cheaply.

1. Run only `openarmx_teleop_bridge_vr_node` (C++, no external dependencies) in a Humble container.
2. Send synthetic UDP datagrams on port 5100 using the ASCII protocol
   (`openarmx_teleop_bridge_vr_node.cpp:335-431`), with and without a positive `timestamp_ns`.
3. Observe `pico_right_controller/pose` on the Pi: with `timestamp_ns>0` the header carries the
   wire time; with `timestamp_ns<=0` it carries the bridge's `now()`.
4. **Do not** run `openarmx_teleop_vr_node` — it requires the closed `openarmx_arm_driver`. Do not
   fabricate a substitute and attribute results to the framework. **Never** launch
   `openarmx_bringup` (CAN hardware).

## Tier 3 — blocked or deliberately withheld

| Target | Status | Exact prerequisite |
| --- | --- | --- |
| PickNik | `BLOCKED_ENV` | Unity 6000.1.6f1-compatible editor + Android module; then an authorised Quest |
| Spes end-to-end | ready | actual Quest session; ROS adapter and Pi path already proven |
| xiaoxiaoxh | withheld | a source-audited inert replacement for the direct Flexiv robot-server endpoint must exist **before** any runtime attempt |
| Reachy | withheld | an inert WebSocket stub for `/api/move/ws/set_target` |
| NVIDIA native | `NOT_FEASIBLE` here | native OpenXR/CloudXR stack |
| Nakama | not schedulable | resolve source identity (`JuanR5` fork) first |

## Safety register for this plan

- `servo_test.launch.py` (Docker_Teleop) — contains `ur_robot_driver` + `robot_ip`. **Never run.**
- `ur_moveit_config/launch/ur_moveit.launch.py:89` (Docker_Teleop) — `robot_ip` placeholder.
- `openarmx_bringup` / `openarmx_hand_bringup` with `use_fake_hardware:=false` — CAN bus. **Never run.**
- xiaoxiaoxh direct Flexiv server path — do not launch without an audited inert endpoint.
- Reachy daemon endpoint — do not point at a real Reachy.
- OpenVR UR5e — verified to contain **no** hardware driver path at its pinned revision.
