# System Inventory

All revisions are HEAD on 2026-09-30 unless stated. Checkouts are git-ignored and re-created with
`scripts/fetch_upstreams.sh`. Nothing was built or run in PHASE 2.

## 1. Primary systems (full line-level audit in SOURCE_AUDIT.md)

| System | Repository @ SHA (commit date) | What it actually provides | What it does **not** provide (needs separate integration) |
|---|---|---|---|
| Isaac ROS Teleop | NVIDIA-ISAAC-ROS/isaac_ros_teleop @ `e80602863a0c4c94360a22b02248164c2dad6fa4` (2026-09-21); submodule IsaacTeleop gitlink `de761a036a0e7188409c0741de861fe691c7b739` (release/1.4.x, 2026-07-28) | ROS 2 launch of `teleop_ros2_node` (publishes `xr_teleop/*` poses/joints/twist, node-clock stamps) and `pose_reset_node` (static TF anchor) | Any robot controller, any robot-state feedback, any recorder or dataset writer (no rosbag2 / dataset pipeline in the repo or the linked IsaacTeleop tree) |
| IsaacTeleop | NVIDIA/IsaacTeleop @ `47f33af3cc50d01bc3d60f51d17ef0a480fa0969` (2026-09-29; package `isaaccapture`, v1.6.x) — not a descendant of `de761a03` (merge-base `7968ce10`) | OpenXR/CloudXR device I/O, retargeting engine, `TeleopSession`, MCAP record/replay of raw tracker data (headset-free replay into the same retargeting graph), WebXR client input recorder, `examples/lerobot/record.py` (head/hands only, no robot) | Robot, robot state, camera and demonstration recording; its docs point to LeRobot and Isaac Lab for that |
| Isaac Lab | isaac-sim/IsaacLab @ `5eef1d70f3c7f3af1e1c99eae85192b61cda52ac` (2026-09-29) | XR teleop via `isaaclab_teleop`/IsaacTeleop in simulation, `record_demos.py` → HDF5 (robomimic schema) with `actions`, `processed_actions`, `states`, `obs`, `initial_state`; `replay_demos.py` (optional state check); Mimic annotation/generation; robomimic training | ROS (none on this path). Runs only inside Isaac Sim/Kit (RTX-class GPU) |
| LeRobot | huggingface/lerobot @ `e0d50211ef236143ae867228662b7dfaba554f02` (2026-09-29) | `examples/isaac_teleop_to_so101/` (XR controller → clutch → IK → SO-101 follower, recording LeRobotDataset v3.0), upstream `lerobot-record`, dataset writer/reader, Hub push, training | ROS (none). The example pins PyPI `isaacteleop~=1.3.131`, which matches neither pinned IsaacTeleop tree (NV equivalence) |
| XRoboToolkit | XR-Robotics/XRoboToolkit-Teleop-Sample-Python @ `79e5cb8a56e3455515ce1b476e993c764ec58739` (2025-12-31); SDK binding XRoboToolkit-PC-Service-Pybind @ `c64ccf6a` (HEAD, unpinned by setup.sh) | PICO XR → Placo IK → ARX R5 (CAN), Galaxea R1 Lite (**ROS 1** topics), UR5e (RTDE), MuJoCo sims; `DataLogger` pickles per episode (ARX, Galaxea only) | Training pipeline (external openpi converter `zhigenzhao/openpi@72a2f9bd`, key-incompatible with current logger — NV) |

## 2. Assembled end-to-end paths that exist in public code

| Path | XR input | ROS? | Robot | Recorder → dataset | Learning | Runnable here? |
|---|---|---|---|---|---|---|
| P1 IsaacTeleop → LeRobot SO-101 | CloudXR headset/browser controller | **no** | real SO-101 only | in-process `_record_loop` → LeRobotDataset | LeRobot / GR00T (docs; GR00T guide "pending") | not end-to-end: no SO-101, no headset; dataset writer and loaders run on CPU |
| P2 IsaacTeleop → Isaac Lab | CloudXR headset/browser | **no** | simulated | in-process RecorderManager → HDF5 | robomimic | **no** (Isaac Sim requires RTX; host GPU GTX 1050 Ti) |
| P3 XRoboToolkit | PICO | ROS 1 only for Galaxea | real ARX/Galaxea | in-process DataLogger → pickle | external converter | no hardware |
| P4 tidybot_ros | WebXR **phone** (Flask-SocketIO) | **ROS 2** | Gazebo / Isaac Sim / real | separate ROS 2 recorder node → rosbag2 + MP4 → HDF5/parquet/RLDS | diffusion policy / OpenVLA (repo) | plausibly in Gazebo (NV) |
| P5 isaac_ros_teleop | CloudXR | ROS 2 | — | none | — | publisher only |

Only P4 connects XR, ROS 2 and a learning dataset in one public implementation. Its XR source is a phone
WebXR pose. In the public launch files the recorder is included only by the phone launch
(`launch_phone_policy.launch.py:98-104`); the gamepad policy publishes velocity topics
(`/tidybot/arm/target_vel`, `/tidybot/base/target_vel`, `gamepad_policy.py:102-109`) that the recorder does
not subscribe to. The recorder itself consumes only generic target-pose / gripper topics
(`synchronized_recorder.cpp:275-291`), which are also published by the non-XR `remote_policy_diffusion.py:86,92`,
so nothing in the recorder depends on XR-specific data.

## 3. Additional repositories surveyed (SOURCE_AUDIT.md §5)

| Repository | HEAD SHA | Last commit | XR | ROS | Learning dataset |
|---|---|---|---|---|---|
| roahmlab/tidybot_ros | `e32cb459514abe556a9a9a954d9131d0bb50c210` | 2026-03-27 | WebXR phone | 2 | rosbag2 → HDF5/parquet/RLDS |
| OmMandhane/Phone2Act | `7a75b07382c477c4be755315e1e35977b1d75d1b` | 2026-05-05 | ARCore phone (rosbridge) | 2 | LeRobot v2.0 |
| iblnkn/rosetta | `294136dc435a040d608d9efd773d70ae0b421d00` | 2026-09-22 | none | 2 | rosbag2 → LeRobot |
| ngres/leros2 | `c8ca08b550a34db1a4e87edaad468f4ad829524a` | 2026-08-14 | none | 2 | MCAP → LeRobot |
| YAnG-0419/Convert_data | `17bef2a83d1cbb609dcc1c00551845b03b424ad1` | 2026-09-24 | none (GELLO) | 2 (bags) | LeRobot/ACT/DP3 |
| Interbotix/aloha | `4fa6b2c4428f5334441a7bee5ab2b2e8071cff93` | 2024-12-05 | none | 2 | ACT HDF5 |
| ycheng517/lerobot-ros | `dabe6c6c7637c2f139e1c9964864a64921893ba1` | 2026-08-12 | none | 2 | LeRobot |
| unitreerobotics/xr_teleoperate | `817fb00c63cde15e5f24a0f8fa08e1e33ed89d3b` | 2026-09-07 | AVP/PICO/Quest | none (Unitree DDS) | JSON |
| aadhithya14/Open-Teach | `32a7d44b33953066ff27312a7b2b4c294f4f52c5` | 2026-01-24 | Quest 3 | 1 + ZMQ | HDF5 |
| wuphilipp/gello_software | `204f53a64bef89471a1e483b0f874f755fbd2d3a` | 2026-09-14 | Quest (non-ROS path) | 2 (no recorder) | pickle |
| Taokt/Quest2ROS2 | `07aaf65149c9e29103f1fc61deb466cef8a55cef` | 2026-03-06 | Quest | 2 | none |
| saiyuhang123/QuestArmTeleop | `b75965b2943dc98c2aaadaf5d14c58b96a9a4096` | 2026-09-17 | Quest/WebXR | 2 | none |
| eliasbitsch/MetaMove | `57d7d42068e127c33335817fe292b9ecf61b6fd0` | 2026-09-27 | Quest 3 | 2 | `ros2 bag -a` only |
| Quest2ROS/quest2ros | `7f03e9440af0efc3d105a9c6d991fd558935eee8` | 2023-12-13 | Quest | 1 | none |
| Tony1984creator/quest-piper-vla-button-press | `93c761711d4ab8138846dc84836106868df45a09` | 2026-09-28 | Quest | 2 (code private) | LeRobot (private) |
| astroyat/lerobot-ros | `9e504ba0be4e4e222c0ae3dc51a47b0d3e94103d` | 2025-10-23 | none | 2 | none in repo |
| OpenTeleVision/TeleVision | `e6e25afdb16c1b326b5bf37bd0ae79919bf79f26` | 2024-09-26 | AVP | none | HDF5 |

## 4. Environment constraints relevant to later phases

- Host GPU GTX 1050 Ti (4 GiB, sm_61): Isaac Sim/Kit not runnable → P2 cannot be executed natively.
- No Quest/PICO attached; no SO-101/ARX/Galaxea hardware.
- Docker available (`ros:humble-ros-base`, `ros:jazzy-ros-base` images present locally).
