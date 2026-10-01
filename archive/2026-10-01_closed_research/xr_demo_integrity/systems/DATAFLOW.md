# Dataflow

Condensed from `SOURCE_AUDIT.md` (all entries SOURCE_CONFIRMED there unless marked NV). The goal of this
file is to fix the **intended meaning** of each recorded field before any integrity question is asked.

## 0. Is there one connected XR → ROS → recorder → dataset → learning path?

**Not in the NVIDIA stack.** Isaac ROS Teleop publishes XR poses into ROS 2 but has no robot controller
feedback, recorder or dataset writer. The two NVIDIA-documented demonstration paths (LeRobot SO-101,
Isaac Lab) use IsaacTeleop **without ROS**. The only public implementation found that connects XR, ROS 2 and
a learning dataset is `roahmlab/tidybot_ros` (phone WebXR). See SYSTEM_INVENTORY §2.

## 1. P1 — IsaacTeleop → LeRobot `isaac_teleop_to_so101` (single Python process)

| Hop | Code | Output / frame | Clock | Recorded? |
|---|---|---|---|---|
| OpenXR controller locate | IT `live_controller_tracker_impl.cpp:341-449` | grip/aim pose + `is_valid`, squeeze, trigger; OpenXR base space | host monotonic → XrTime at `update()` (not a device capture time) | no (MCAP off in this path) |
| Anchor transform | IT `controller_transform.py:91-131`; LR `config_isaac_teleop.py:59-95` | pose in "robot base" frame via constant `base_T_anchor` (no calibration step) | — | no |
| Device read | LR `teleop_xr_controller.py:161-204` | `grip_pos`, `grip_quat`, `squeeze`, `trigger`; zeros on `is_none`; **`GRIP_IS_VALID` not read** | — | no |
| Clutch + map + bounds + IK | LR `common.py:371-408`, `clutch.py:95-102`, `robot_kinematic_processor.py:234-354`, `kinematics.py:98-154` | joint targets (deg); box/step clamp logged only; IK without convergence check | — | no |
| Hold latch | LR `common.py:104-129` | latched measured joints on idle frames | — | (becomes `action`) |
| Robot command | LR `record.py:160`; `so_follower.py:229-254` | `sync_write Goal_Position` (no ack); optional `max_relative_target` clip; **return value discarded** | — | no |
| Robot state | LR `so_follower.py:204-226` | `Present_Position` read **before** the action of the same row | none returned | `observation.state` |
| Camera | LR `camera_opencv.py:457-617` | newest frame ≤ 500 ms old; capture time not returned | `perf_counter` internally | `observation.images.*` (lossy video) |
| Recorder | LR `record.py:122-168` | one row per loop: obs, action, task | loop `perf_counter`, not stored | — |
| Writer | LR `dataset_writer.py:202-394` | parquet + video + meta; `timestamp = frame_index/fps` | synthetic | yes |
| Loader | LR `dataset_reader.py:163-472`, `video_utils.py:190-205` | index-offset windows; video PTS vs parquet timestamp within 1e-4 s | synthetic | — |

**Intended semantics (defined by code):** `action[t]` = the joint target the loop decided to send at step
*t* before bus-level clipping; `observation.state[t]` = measured joints read just before deciding `action[t]`;
the executed result of `action[t]` appears only in `observation.state[t+1]`. Upstream `lerobot-record` uses
the teleop-processed action before `robot_action_processor` (TODO acknowledged in code,
`lerobot_record.py:359-361`). Hold frames are recorded without a flag; there is no success label.

## 2. P2 — IsaacTeleop → Isaac Lab `record_demos.py` (single Kit process, simulation)

| Hop | Code | Recorded as |
|---|---|---|
| XR → retargeter (clutch, pipelined execution by default) | `isaac_teleop_device.py`, `clutch_retargeter.py:577-619`, `session_lifecycle.py:985-998` | — (tracking loss → last pose held, no flag) |
| env action (8-D abs EE pose + gripper for SO-101 IK-Abs) | `so101/stack_ik_abs_env_cfg.py:144-169` | `actions` (pre-step, `recorders.py:34-38`) |
| action term processing / IK | `task_space_actions.py:202-219`, `differential_ik.py:170-175` | `processed_actions` (post-step); IK joint targets **not** recorded |
| physics step (decimation, step_dt 0.05 s) | `manager_based_rl_env.py:205-279` | `states` (post-step `scene.get_state`), `obs` (pre-step) |
| pause / `action is None` | `record_demos.py:719-722` | **not stepped, not recorded, no gap marker** |
| success | `record_demos.py:505-537` (N consecutive success steps) | `success=True`; export SUCCEEDED_ONLY (`:365`) |
| replay check | `replay_demos.py:97-124` | optional, abs tol 0.01, prints mismatches |

**Intended semantics:** index-aligned steps of a deterministic-ish simulator; `actions` is the controller
*command*, `states` the *actual* simulator state after it. No timestamps; the docs state replay is not
deterministic (`teleop_imitation.rst:757`).

## 3. P4 — tidybot_ros (ROS 2, separate recorder node)

| Hop | Code | Notes |
|---|---|---|
| Phone WebXR → Flask-SocketIO | `phone_teleop_server.py:29-82` | `0.0.0.0:5000`, `cors_allowed_origins="*"`, no authentication; events `save_episode` / `discard_episode` (:64-72) |
| → `/teleop_commands` → `phone_policy` | `phone_policy.py:33-55` | publishes `/tidybot/arm/target_pose` (Pose), `/tidybot/gripper/commands`, `/tidybot/base/target_pose` |
| → IK / controllers | `moveit_ee_pose_ik.cpp:48`; `base_server.py:41`; Isaac/Gazebo bridges | **same topics the recorder records as actions** |
| Observations | `synchronized_recorder.cpp:209-270, 562-590` | `/joint_states` (finger joint), 3 camera image topics (latest value, no age check), TF lookups at `Time(0)` with stamps overwritten by recorder `now()` |
| Recording | `:157-196, 517-550, 600-720, 800` | wall timer at `fps` (10 Hz); ≤1 sample per tick while `pending_writes_>0`; latest cached value of every stream; bag write time = recorder `now()` |
| Episode control | `:184-192`; `state_controller.py:49-57` | open services `/start_recording`, `/stop_recording`, `/finalize_recording` (SetBool: save/discard) |
| Conversion | `rosbag_to_hdf5.cpp:172-177, 201-226, 431-460` | pairs obs/actions **by index**, checks equal counts only; no timestamps in HDF5 |

**Intended semantics:** a 10 Hz snapshot of (latest commanded targets, latest observed poses, latest images).
`action` = commanded end-effector / base / gripper target (pre-IK), the same message the controller consumes.

## 4. P3 — XRoboToolkit (in-process; ROS 1 only for Galaxea)

`base_hardware_teleop_controller.py:110-185`, `data_logger.py:41-46`: pickled list of dicts at ~50 Hz with
`timestamp = time.time() - start`, `qpos`, `qvel`, `qpos_des` (ARX: shared Placo state read without lock;
may never have been transmitted), images (RealSense `timestamp_us` only). Galaxea state/images arrive via
ROS 1 topics `/hdas/feedback_arm_*`, `/hdas/camera_*` (`galaxea.py:17-64`, `ros_camera.py:90-107`); header
stamps dropped. No validity, deadman, IK-failure or disconnect flag is logged.

## 5. Answers to the ten audit questions (per path)

| # | P1 LeRobot | P2 Isaac Lab | P4 tidybot_ros | P3 XRoboToolkit |
|---|---|---|---|---|
| ① commanded and actual both recorded | joint target + measured joints (actual lags by one row); raw XR/EE target not stored | yes: `actions`, `processed_actions`, `states` | commanded EE target + measured TF poses/gripper | `qpos_des` + `qpos` (ARX `qpos_des` unreliable) |
| ② action label defined as | pre-clip joint target (example) / teleop-processed action (`lerobot-record`) | raw env action (EE pose) before scale/clip | commanded target topic | external converter: `qpos_des` |
| ③ same instant? | no: motor read → camera newest ≤500 ms → XR locate; skew unrecorded; synthetic timestamps | index-aligned; no timestamps | latest-value snapshot, no age check; stamps overwritten | latest value at 50 Hz; only RealSense stamp kept |
| ④ tracking loss / pause / reset / reconnect | recorded as hold frames, no flag; invalid pose unchecked (NV crash); no reconnect | paused steps dropped, no marker; loss = held pose; reset discards episode | no XR-validity field reaches recorder (NV beyond code read); pause = stale latest values | not logged |
| ⑤ rejection / delay | not recorded (no ack, clip logged only) | not recorded | not recorded | not recorded |
| ⑥ episode start/end/success | keyboard / time limit; no success label | operator + N success steps; SUCCEEDED_ONLY | phone save/discard events via open services | operator buttons; no success |
| ⑦ target vs actual comparable | joint space approx. (row offset) | EE `actions` vs `obs/eef_*` approx. | EE target vs TF pose | joint space |
| ⑧ enough to re-verify | no (no raw XR, calibration, versions, hashes) | partly (`initial_state`, `states`); no seed/cfg/hash | raw bags keep receive times; HDF5 does not | no |
| ⑨ existing checks | schema/dtype/shape, episode buffer, delta-timestamp grid, video PTS tolerance | replay state compare (0.01), annotate success | equal-count check in converter | structural printout |
| ⑩ separate writer components | none in-process; CloudXR endpoint, disk, Hub | none in-process; dataset tools | **separate ROS 2 publishers per topic; open services; SocketIO endpoint** | ROS 1 topics (Galaxea) |
