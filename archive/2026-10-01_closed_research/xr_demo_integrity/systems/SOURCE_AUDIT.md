# Source Audit

Line-level audit of every hop from XR input to training-time loading, at pinned SHAs
(`SYSTEM_INVENTORY.md`). `SC` = SOURCE_CONFIRMED (read, lines given), `NV` = NOT_VERIFIED.
Nothing here was executed; all runtime behaviour is NV unless an experiment says otherwise.

## Provenance of this text and hand re-verification

Sections 1–5 were drafted by research-assistant agents reading the pinned checkouts; they are kept verbatim
except for path cleanup. Before commit the following load-bearing claims were **re-read by hand** in the
pinned trees (all confirmed):

| Claim | Where re-read |
|---|---|
| LeRobot example discards `send_action` return; stores pre-clip `action` | `lerobot@e0d50211` `examples/isaac_teleop_to_so101/record.py:150-164` |
| upstream `lerobot-record` stores `action_values` (teleop-processed) although the comment says "action actually sent is saved"; TODO acknowledges it | `src/lerobot/scripts/lerobot_record.py:318-330, 355-368` |
| dataset `timestamp = frame_index / fps` | `src/lerobot/datasets/dataset_writer.py:220-227` |
| no `check_timestamps_sync`, no content hashing in `datasets/` | `git grep` at `e0d50211` |
| Isaac Lab `record_demos` exports SUCCEEDED_ONLY; `action is None` steps are not stepped/recorded | `IsaacLab@5eef1d70` `scripts/tools/record_demos.py:360-365, 719-745` |
| Isaac Lab recorder stores `actions` (pre-step), `processed_actions`, `states` (post-step) | `source/isaaclab/isaaclab/envs/mdp/recorders/recorders.py:25-62` |
| `replay_demos` state check is a single absolute tolerance 0.01 | `scripts/tools/replay_demos.py:97-124` |
| tidybot recorder: separate ROS 2 node, subscribes `/joint_states`, 3 cameras, 3 action topics; open start/stop/finalize services; writes with recorder `now()` | `tidybot_ros@e32cb459` `src/tidybot_episode/src/synchronized_recorder.cpp:184-192, 209-291, 800` |
| tidybot recorded arm action topic == IK solver input topic | recorder `:281-282`; `src/tidybot_solver/src/moveit_ee_pose_ik.cpp:48`; publisher `phone_policy.py:49` |
| tidybot sampling: wall timer at `fps` (default 10 Hz) writes **at most one** sample per tick, only while `pending_writes_ > 0` (incremented per action message) | `synchronized_recorder.cpp:157-161, 194-196, 517-550` — **this corrects the survey's wording "a write fires on each action msg"** in §5: arrivals gate sampling but do not set its rate |

---

# 1. XR controller → IsaacTeleop → LeRobot `isaac_teleop_to_so101` → LeRobotDataset → training loader


Pinned trees (read-only):
- LR = `references/upstream/lerobot` @ `e0d50211ef236143ae867228662b7dfaba554f02`
- IT = `references/upstream/IsaacTeleop` @ `47f33af3cc50d01bc3d60f51d17ef0a480fa0969` (VERSION `1.6.x`, Python package `isaaccapture`)
- IT-1.4 = gitlink `de761a036a0e7188409c0741de861fe691c7b739` (VERSION `1.4.x`, Python sources under `src/core/*/python/`)

Paths below are relative to those roots. `SC` = SOURCE_CONFIRMED (read, with lines). `NV` = NOT_VERIFIED.

## 0. Version caveat (read this first)

- The LeRobot example imports `isaacteleop.*` (LR `examples/isaac_teleop_to_so101/isaac_teleop/base.py:253-261`, `teleop_xr_controller.py:40-44`) and its README pins `isaacteleop[cloudxr,retargeters-lite]~=1.3.131` from PyPI (LR `examples/isaac_teleop_to_so101/README.md:45`). SC
- At the IT pin, the package is `isaaccapture` (IT `pyproject.toml:12`), and `isaacteleop` is only a deprecation alias that forwards imports (IT `src/compat/isaacteleop.py:3-31`). SC
- Neither pinned IT tree is 1.3.131. So the IT code quoted here is the nearest source we have, **not** proof of what runs with the LeRobot-pinned wheel. NV. Where it matters, I checked IT-1.4 as well: the controller-tracker validity logic and the `RetargetingStepInfo` fields are the same in substance (IT-1.4 `src/core/live_trackers/cpp/live_controller_tracker_impl.cpp:360-403`; `src/core/teleop_session_manager/python/teleop_session.py:90-102`). SC

## 1. Arrow-by-arrow data path (XR controller device, `--teleop.type=xr_controller`)

### A1. XR pose (OpenXR runtime -> IsaacTeleop controller tracker)
- **Function:** `LiveControllerTrackerImpl::update(int64_t monotonic_time_ns)`, IT `src/core/live_trackers/cpp/live_controller_tracker_impl.cpp:341-449`. SC
- **Clock:** `DeviceIOSession::update()` reads `os_monotonic_now_ns()` (IT `src/core/deviceio_session/cpp/deviceio_session.cpp:137-143`). This time is converted to `XrTime` (`:349`), and `xrLocateSpace(grip_space, base_space_, xr_time)` (`:385`) locates the pose at the *current* monotonic time, not a predicted display time. SC
- **Output:** `ControllerSnapshot{grip_pose{pose,is_valid}, aim_pose{…}, inputs{squeeze_value, trigger_value, …}}` (IT `src/core/schema/fbs/controller.fbs:25-44`). Timestamp is `DeviceDataTimestamp(available=monotonic, sample=monotonic, raw_device=xr_time)` (`:446`; fields documented in `schema/fbs/timestamp.fbs`). SC
- **Failure handling:**
  - When the controller is not active, the snapshot is `reset()` (`:374-378`), which Python sees as `None`.
  - When the grip pose is not valid (position or orientation flag missing), `grip_pose` stays a default-constructed `ControllerPose{}` with `is_valid=false` (`:381, :392-401`). The snapshot is still emitted, together with the live squeeze and trigger values (`:431-440`).
  - When `xrSyncActions2NV` or `xrLocateSpace` fails, the code throws `runtime_error` (`:362-366, :386-389`). SC
- **Recording here:** only when the session has an `McapRecordingConfig`: `publish_and_record(mcap_channels_...)` (`:447-448`). The LeRobot path does **not** configure one (see A2). SC

### A2. IsaacTeleop session / source node -> coordinate transform
- **LeRobot session config:** `TeleopSessionConfig(app_name=..., pipeline=...)` (LR `isaac_teleop/base.py:348`). No `mcap_config` is passed, so MCAP recording is off. Execution mode is the default `RetargetingExecutionMode.SYNC` (IT `src/python/isaaccapture/teleop_session_manager/config.py:267`). SC
- **Step:** `TeleopSession.step` -> `_step_sync` -> `_execute_step_request` (IT `teleop_session_manager/teleop_session.py:444-517, 565-649, 678-713`). `graph_time` defaults to `time.monotonic_ns()` (`:588-591`). `last_step_info` records `returned_age_frames=0` and `returned_age_s`/`compute_duration_s` (`:703-710`). SC
- **Source node:** `ControllersSource.poll_tracker` / `_compute_fn` (IT `retargeting_engine/deviceio_source_nodes/controllers_source.py:75-97, 113-200`). A `None` snapshot becomes `set_none()` (`:139-141`). Otherwise the node copies grip pos/quat, `GRIP_IS_VALID`, squeeze and trigger (`:184-200`). SC
- **Transform:** `ControllerTransform._compute_fn` applies a static 4x4 `base_T_anchor` to the grip and aim poses (IT `retargeting_engine/utilities/controller_transform.py:91-131`). The matrix is a constant external input built once (LR `teleop_xr_controller.py:99-103`). Its default maps OpenXR anchor (X right, Y up, Z back) to robot base (X fwd, Y left, Z up) (LR `isaac_teleop/config_isaac_teleop.py:59-67, 87-95`). SC
- **Frames:** after the transform, grip poses are in the "robot base frame". This assumes the OpenXR base space is aligned with the robot. No extrinsic calibration step exists (docs say "there is no manual calibration step", LR `docs/source/isaac_teleop.mdx:225`). SC

### A3. LeRobot XR device read (`XRController.get_action`)
- LR `examples/isaac_teleop_to_so101/isaac_teleop/teleop_xr_controller.py:161-204`. It calls `_step(execution_events=RUNNING, external_inputs=base_T_anchor)` (`:172`). SC
- **Output:** `{"grip_pos": (3,) float32 m, "grip_quat": (4,) xyzw, "squeeze": float, "trigger": float}`. SC
- **Tracking loss:** if `controller.is_none`, it returns zeros, the identity quaternion, and `squeeze=trigger=0.0`, and sets `is_tracking=False` (`:177-181`). A partial-read exception is handled the same way (`:188-197`). SC
- **`GRIP_IS_VALID` is not consulted** (grep: no `is_valid` / `GRIP_IS_VALID` anywhere in `examples/isaac_teleop_to_so101/`). So a frame where the controller is active but the pose is invalid passes on the default pose (`ControllerPose{}`) with the *live* squeeze value. SC. By contrast, IsaacTeleop's own `se3_retargeter.py:256, 400` does check `GRIP_IS_VALID`. SC
  - Expected runtime result (NV): the default flatbuffers `Quaternion` is (0,0,0,0). If the clutch is engaged, `Rotation.from_quat` raises `ValueError("Quaternion must be a non-zero finite vector")` (LR `src/lerobot/utils/rotation.py:36-37`) inside `Clutch.engage/rebase` (`clutch.py:93, 98`). The loop then aborts (see Q4).
- **Health guard:** `_step` raises `RuntimeError` on `worker_exception`. It only logs a warning on `frame_deadline_miss` (LR `isaac_teleop/base.py:475-485`). In SYNC mode `frame_deadline_miss` is always False (IT `teleop_session.py:703-710`). SC
- **Session/CloudXR lifecycle:** `connect()` auto-launches CloudXR via `CloudXRLauncher(install_dir=~/.cloudxr, env_config=default.env)` (LR `base.py:380-411`). There is no reconnect logic. The device only waits at startup, with no timeout, until `is_tracking` is true (LR `common.py:284-299`). SC

### A4. Retargeting: clutch -> rename -> bounds / rate limit -> IK (in-loop, LeRobot side)
- `setup_xr().compute(robot_obs)`, LR `examples/isaac_teleop_to_so101/common.py:371-408`. SC
- **Clutch gate:** `enabled = squeeze > clutch_threshold` (default 0.5, `config_isaac_teleop.py:83`) (`common.py:380`). If not enabled, the function returns `None` (`:399-400`). SC
- **Engage edge:** runs FK on the *measured* joints, then `clutch.engage(grip_pos, grip_quat, measured_base_T_ee)` and `processor.reset()` (`:386-394`). SC
- **Clutch math:** `pos = home_pos + (grip_pos - origin_pos)`, `rot = (R_ctrl · R_origin⁻¹) · R_home` (LR `isaac_teleop/clutch.py:95-102`). The home orientation is the last *commanded* orientation, not the measured one (`:55-59, 91`). SC
- **Map:** `MapXRControllerActionToRobotAction.action` turns `ee_pose` into `ee.x/y/z`, `ee.wx/wy/wz` (rotvec) and `ee.gripper_pos = (1-trigger)*100` (LR `isaac_teleop/xr_controller_processor.py:52-67` in file numbering; in the concatenated listing above it appeared at 155-170). SC
- **Safety:** `EEBoundsAndSafety(end_effector_bounds=[-1,-1,0]..[1,1,1], max_ee_step_m=0.1, raise_on_jump=False)` (LR `common.py:321-325`).
  - Implementation: box clip (`robots/so_follower/robot_kinematic_processor.py:234`), then a per-frame step clamp with `logger.warning` (`:237-253`).
  - Orientation (`wx/wy/wz`) is **not** bounded (`:260-262`). SC
- **IK:** `InverseKinematicsEEToJoints` (warm-started from the previous solution, `initial_guess_current_joints=False`) (LR `common.py:328-333`; `robot_kinematic_processor.py:303-354`).
  - The solver runs placo for a fixed `max_iters=8` with **no residual or convergence check** and returns the joints as-is (LR `src/lerobot/model/kinematics.py:98-154`).
  - The gripper passes through from `ee.gripper_pos` (`robot_kinematic_processor.py:351-352`). SC
- **Output type:** `RobotAction` = `{shoulder_pan.pos, …, gripper.pos}`, in degrees (gripper 0-100). SC

### A5. Hold latch (idle frames)
- `HoldLatch.resolve(action, obs)`: when the action is `None`, it latches `hold_action(obs)` (the measured joints) once, on the active->idle edge, and re-sends that latched pose on each idle frame (LR `common.py:104-129`). SC

### A6. Robot command -> robot controller
- The call site in the example record loop is `robot.send_action(action)`. **Its return value is discarded** (LR `examples/isaac_teleop_to_so101/record.py:160`). SC
- `SOFollower.send_action` (LR `src/lerobot/robots/so_follower/so_follower.py:229-254`):
  - Optional `max_relative_target` clip against a fresh `Present_Position` read (`:247-250`, `robots/utils.py:93-123`). It defaults to `None`, i.e. disabled (`config_so_follower.py:36`).
  - Then `bus.sync_write("Goal_Position", goal_pos)` (`:253`).
  - It returns the dict actually sent (`:254`). SC
- **Hidden transformations below `send_action`:** `_unnormalize` clamps the gripper to [0,100] (and RANGE_M100_100 to ±100). DEGREES mode is not software-clamped. `int()` truncates to ticks (LR `src/lerobot/motors/motors_bus.py:883-911`). SC
- **Write failure:** `sync_write` is a no-status-packet broadcast (`motors_bus.py:1231-1233`). It raises `ConnectionError` only if `txPacket` itself fails after `num_retry` (default 0 here) (`:1262-1282`). SC. The motor does not acknowledge the write, so "command reached the motor" is not confirmed. SC
- **Motor controller:** Feetech STS3215 in position mode with P=16, I=0, D=32 (LR `so_follower.py:183-195`, `config_so_follower.py:45-47`). The steady-state lag under gravity is acknowledged in `common.py:112-116`. SC

### A7. Actual robot state
- `SOFollower.get_observation`: `bus.sync_read("Present_Position", num_retry=2)`, then per-camera `cam.read_latest()` (LR `so_follower.py:204-226`). The `perf_counter` durations are only `logger.debug`-ed (`:209-210, 217-218`). No timestamp is returned. SC
- Only `Present_Position` is read. Velocity, current/load, temperature and goal-register readback are not read or recorded. SC

### A8. Camera observation
- The OpenCV background thread stamps each frame with `time.perf_counter()` into `latest_timestamp` (LR `src/lerobot/cameras/opencv/camera_opencv.py:457-492`). SC
- `read_latest(max_age_ms=500)` returns the newest frame and raises `TimeoutError` if it is older than 500 ms. **The capture timestamp is not returned** (`:585-617`). SC
- The thread raises `RuntimeError` after >10 consecutive read failures (`:487-492`). SC

### A9. Recorder (example loop)
- `_record_loop`, LR `examples/isaac_teleop_to_so101/record.py:122-168`. Per iteration (SC):
  1. `obs = robot.get_observation()` (`:151`)
  2. `observation_frame = build_dataset_frame(..., obs, prefix="observation")` (`:154`)
  3. `action = hold.resolve(device.compute(obs), obs)` (`:158`)
  4. `robot.send_action(action)` (return ignored) (`:160`)
  5. `action_frame = build_dataset_frame(..., action, prefix="action")`, then `dataset.add_frame({...obs, ...action, "task"})` (`:163-164`)
  6. `precise_sleep(max(1/fps - dt, 0))`; loop until `perf_counter() - start >= control_time_s` (`:166-168`)
- **Features** (`record.py:182-194`, with identity default processors `processor/factory.py:50-78`; `utils/feature_utils.py:78-100`):
  - `action` float32 (6,), names `*.pos`
  - `observation.state` float32 (6,)
  - `observation.images.<cam>` video/image (H,W,3)
  - plus the defaults `timestamp` (float32), `frame_index`, `episode_index`, `index`, `task_index` (`utils/constants.py:98-104`)
- No XR fields, EE target, clutch state, squeeze/trigger, IK residual, clipping flag or wall-clock time are in the features. SC
- The config is logged only to the console: `logging.info(pformat(asdict(cfg)))` (`record.py:174`), and `init_logging()` gets no `log_file` (`utils/utils.py:43-48`). SC

### A10. Dataset writer
- `DatasetWriter.add_frame` (LR `src/lerobot/datasets/dataset_writer.py:202-269`) (SC):
  - `validate_frame` (`:218`)
  - **`timestamp = frame_index / fps`** (`:224-227`)
  - image/video frames are written as PNGs to a temp dir, or fed to the streaming encoder (`:254-265`)
- `save_episode` (`:271-394`) (SC):
  - `validate_episode_buffer` (`:279`)
  - stacks arrays and computes episode stats (`:296-324`)
  - writes parquet with snappy (`:441-504`)
  - encodes video from the frame images at `fps` (`:341-375`, `_encode_video_worker`)
  - concatenates into chunk files, storing per-episode `from_timestamp`/`to_timestamp` (`:506-589`)
  - `meta.save_episode` updates `meta/episodes/*.parquet`, `info.json` and `stats.json` (`dataset_metadata.py:644-684`)
- `info.json` contents: `codebase_version="v3.0"`, `fps`, `features`, `robot_type`, chunk sizes, paths (`feature_utils.py:85-120`; `dataset_metadata.py:63`). On episode 0 it also gets video encoder info (`dataset_writer.py:572-580`). SC
- `clear_episode_buffer` discards the buffer and temp images (`:591-605`). `finalize` flushes (`:687-705`). SC
- **Hub push:** `push_to_hub` → `HfApi.create_repo(exist_ok=True)`, `upload_folder(folder_path=root, ignore images/)`, dataset card, then **delete-and-recreate tag `v3.0`** on the pushed branch (LR `src/lerobot/datasets/lerobot_dataset.py:646-726`). `DatasetRecordConfig.push_to_hub` defaults to `True`, `private=None` (org default) (LR `src/lerobot/configs/dataset.py:43-45`). SC

### A11. Learning-time loading
- `DatasetReader.__init__`: when `delta_timestamps` is given, it runs `check_delta_timestamps(delta_timestamps, fps, tolerance_s)`, then `get_delta_indices` (`round(d*fps)`) (LR `src/lerobot/datasets/dataset_reader.py:163-167`; `feature_utils.py:174-232`). SC
- `get_item` (`dataset_reader.py:428-472`) (SC):
  - reads the parquet row
  - neighbor indices are **index offsets clamped to the episode**, with `*_is_pad` flags (`:305-324`)
  - video frames are decoded at the parquet `timestamp` values plus the episode's `from_timestamp` (`:326-343, 386-415`)
- Video decode tolerance: `min |query_ts - decoded_pts| <= tolerance_s`, otherwise `FrameTimestampError` (LR `video_utils.py:190-205` pyav; `:411-414` torchcodec path). Default `tolerance_s=1e-4` (`lerobot_dataset.py:60`; `configs/train.py:150`). SC

## 2. Answers

### Q1. Are both the operator-commanded action and the executed robot state recorded?
Partly. Each row stores two joint vectors (SC):
- `action`: the joint targets the loop decided to send (`record.py:158, 163`)
- `observation.state`: the measured `Present_Position`, read **before** the action was computed and sent in that same iteration (`record.py:151, 154`; `so_follower.py:207`)

The executed result of action *t* only shows up in `observation.state` of row *t+1*, and nothing links the two explicitly. What the operator actually commanded is **not** stored (SC): raw grip pose, squeeze, trigger, the clutch-rebased EE target, and the post-bounds EE target are all missing. The value actually written to the motors (the `send_action` return) is not stored either.

### Q2. What is the dataset's `action` label?
- **Example `record.py` (this path):** `action` = the output of `HoldLatch.resolve(device.compute(obs), obs)` (`record.py:158, 163`). When engaged, that is the IK joint solution after the EE bounds/step clamp (`common.py:315-337, 408`). When idle, it is the latched measured pose (`common.py:122-129`). SC
- **Before or after `max_relative_target`:** **before**. The clipped dict returned by `send_action` (`so_follower.py:254`) is thrown away (`record.py:160`). Also not reflected: the gripper [0,100] clamp and the int-tick truncation inside `_unnormalize` (`motors_bus.py:900-907`). With the default `max_relative_target=None` the two agree except for those bus-level clamps and truncation. SC
- **Upstream `lerobot-record` (for comparison, not used by this example):** the stored `action` is `action_values = teleop_action_processor((act, obs))` (`scripts/lerobot_record.py:325-326, 367`). That is **before** `robot_action_processor` and before clipping; `_sent_action` is unused (`:362`). The inline comment at `:359-361` says "action actually sent is saved in the dataset", but the code saves `action_values`. SC

### Q3. Do camera frames and action/state share an instant? How are timestamps made? Is there any sync check?
- **Timestamps are synthetic:** `timestamp = frame_index / fps` (`dataset_writer.py:224-225`), stored as float32 (`constants.py:99`). No measured time is stored (SC):
  - not the `perf_counter` loop time
  - not the camera `latest_timestamp`
  - not the OpenXR `xr_time` or monotonic time
  - not the motor read time
- **Order inside one row:** motor read (t0) → camera `read_latest` (newest frame, captured up to 500 ms earlier, `camera_opencv.py:585-617`) → XR step and pose locate at `monotonic_now` (t1 > t0, `deviceio_session.cpp:139`) → IK → `sync_write` (t2). So one row mixes samples from different instants, and the skew is not recorded. SC
- **Loop overrun:** `precise_sleep(max(...,0))` (`record.py:167`) gives no warning and no log in the example. Upstream `lerobot-record` has a `CycleTimer` (`lerobot_record.py:291-304`) that the example does not use. When loops overrun, the stored timestamps compress real time. The episode's frame count also shrinks, because the episode ends on elapsed `perf_counter` time (`record.py:144, 168`). SC
- **Write-time sync check:** none. `validate_frame` checks only feature keys, dtype and shape (`feature_utils.py:235-341`). SC
- **Load-time checks:**
  - `check_delta_timestamps` only verifies that requested deltas are multiples of 1/fps within `tolerance_s` (`feature_utils.py:174-215`).
  - Video decode checks that the decoded PTS is within `tolerance_s=1e-4` of the queried parquet timestamp (`video_utils.py:198-205`). Both sides come from `frame_index/fps` (encoding at `fps`, `dataset_writer.py:351`), so this check can only catch encoding or concatenation offsets, not capture skew. SC
- **`check_timestamps_sync` does not exist at this SHA:** a grep over the LR tree finds zero hits. The `tolerance_s` docstring still says the init checks that "each timestamps is separated to the next by 1/fps +/- tolerance_s" (`lerobot_dataset.py:180-184`), but no such check runs. That docstring is stale. SC

### Q4. How are tracking loss, clutch pause, reset and reconnect handled in the recorded data?
- **Clutch released (squeeze ≤ 0.5), or controller absent (`is_none`, which forces squeeze = 0):** `compute` returns `None`, and the frame is **still recorded**. Its `action` is the pose latched from the measured joints at the active→idle edge (`common.py:399-400`, `HoldLatch` `:122-129`). The docstring says so: "All frames are recorded (including hold frames)" (`record.py:48-49`). SC
- **No pause/tracking flag is stored.** Hold frames look like ordinary frames whose action is roughly constant. SC
- **Controller active but grip pose invalid (`is_valid=false`):** this is not detected on the LeRobot side (see A3).
  - If disengaged: the frame is held and recorded like any other hold frame. SC
  - If engaged: the default pose is used. NV at runtime: the zero quaternion raises `ValueError` (`rotation.py:37`). SC for the path that follows: the exception leaves `_record_loop`, and `safe_stop_image_writer` stops the image writer (`image_writer.py:36-46`). `VideoEncodingManager.__exit__` finalizes the dataset and deletes the interrupted episode's images (`video_utils.py:1279-1307`). The **in-progress episode is discarded** (never `save_episode`d). Then `finally` runs, so **`push_to_hub` still executes for the episodes already saved** (`record.py:278-309`).
- **Reset window:** `_record_loop(dataset=None, control_time_s=reset_time_s)` keeps teleoperating but records nothing (`record.py:256-266`). SC
- **Startup reset/align slew:** runs before recording and is not recorded (`common.py:353-360`, `slew` `:132-151`). SC
- **Reconnect:** there is none. The device-side `RuntimeError` from IsaacTeleop (`base.py:477-480`; `TeleopSession.step` documents runtime failures as fatal, `teleop_session.py:492-494`) aborts the run through the same path as above. SC

### Q5. How are robot rejection, delayed execution and clipping recorded?
- **Clipping:**
  - `EEBoundsAndSafety` clamps are only `logger.warning`-ed (`robot_kinematic_processor.py:247-253`).
  - `max_relative_target` clips are only `logger.warning`-ed (`robots/utils.py:116-123`), and the clipped value is dropped (`record.py:160`).
  - Bus-level clamping and truncation leave no trace (`motors_bus.py:896-907`).
  - Nothing about clipping reaches the dataset. SC
- **Rejection/failure:** `sync_write` gets no acknowledgement. A tx failure raises `ConnectionError`, which aborts the run (the current episode is discarded, earlier ones are kept and pushed as in Q4). A `sync_read` failure after 2 retries does the same. SC
- **Delay:** no command or execution latency is measured or stored. The position controller's lag appears only implicitly, as `observation.state[t+1..]` versus `action[t]`. SC
- **IK non-convergence:** not detected (`kinematics.py:133-154`). The IK joints are stored as the `action` even when the EE target is unreachable. SC

### Q6. Who decides episode start/end and success, and how do rerecord/discard work?
- **Start:** after `build_device` startup, which includes the headset connect-wait and the reset slew. Every later episode starts right after the previous reset window (`record.py:246-276`). SC
- **End:** whichever comes first (SC):
  - the time limit `episode_time_s` (default 60, `configs/dataset.py:35`), measured with `perf_counter` (`record.py:144, 168`)
  - Right/`n` → `exit_early` (`common.py:637-642`, `keyboard_input.py:163-173`)
- **Esc/q:** sets `stop_recording` and `exit_early`, and the **current partial episode is still saved** (`record.py:268-276`, the rerecord flag is false). SC
- **Left/r:** sets `rerecord_episode`. The reset window still runs, then `clear_episode_buffer()` discards the episode and it is re-recorded (`record.py:258-273`; `dataset_writer.py:591-605`). SC
- **Success:** no success/failure label exists anywhere in the recorder or the features. SC
- **Task string:** a single CLI-supplied `--dataset.single_task` is used for every frame (`record.py:243, 164`). SC
- The keyboard listener reads the terminal TTY, or pynput / headless no-op when there is no TTY (`common.py:616-650`). SC

### Q7. Can the retargeted target be compared with the actual joint state from stored data?
- **Joint space:** yes, approximately. Compare `action[t]` (the joint targets before `send_action` clipping) with `observation.state[t+1]` (measured). Timing is only known via `frame_index/fps`, and the true intervals are not stored. SC
- **EE/Cartesian target:** no. The clutch-rebased and bounded EE target is not stored. SC
- It *could* be recomputed as FK(`action`) using the URDF, but the URDF is not stored or hashed in the dataset. It is fetched at runtime from the `lerobot/robot-urdfs` bucket, and a `.sync_complete` marker is its only check (`common.py:168-183`). SC
- **Hold frames versus IK frames:** they cannot be told apart reliably, since no clutch flag is stored. SC
- **The value actually written to the motors:** not stored (Q2).

### Q8. Does the stored file carry enough raw information to re-verify?
No. The dataset holds only:
- joint `action` and `observation.state`, float32
- camera video (lossy encode)
- synthetic timestamps
- `task`
- `info.json` with `codebase_version="v3.0"`, `fps`, `robot_type`, features and video codec info
- per-episode stats

Missing (all SC):
- raw XR poses, squeeze/trigger, `GRIP_IS_VALID`
- the OpenXR/monotonic times
- `base_T_anchor`, `clutch_threshold`, `max_ee_step_m`, bounds, IK weight, the URDF or its hash
- robot calibration (kept separately under `HF_LEROBOT_CALIBRATION`, not copied into the dataset)
- the reset-pose file
- LeRobot git SHA, `isaacteleop` version, CloudXR version or device profile
- per-file content hashes

The only way to keep raw XR data is IsaacTeleop MCAP recording, and the LeRobot example does not enable it (see §3).

### Q9. Which checks exist in LeRobot, and what do they catch? (all SC)

| Check | Where | Detects | Does not detect |
|---|---|---|---|
| `validate_frame` → `validate_features_presence`, `validate_feature_dtype_and_shape` (numpy / image / string / language) | `feature_utils.py:235-410`, called at `dataset_writer.py:218` | missing/extra keys; missing `task`; wrong dtype/shape; image shape not HWC/CHW | NaN/Inf, value ranges, semantic or temporal consistency. Pixel range is checked later by the image writer, per the comment at `:359` |
| `validate_episode_buffer` | `feature_utils.py:413-450`, called at `dataset_writer.py:279` | missing `size`/`task`; episode_index ≠ total_episodes; empty episode; buffer keys ≠ features | content |
| `check_delta_timestamps` | `feature_utils.py:174-215`, called at `dataset_reader.py:166` | requested deltas that are not multiples of 1/fps (± `tolerance_s`) | anything about the stored data |
| Video decode tolerance | `video_utils.py:198-205, 411-414` | decoded PTS more than `tolerance_s` (1e-4 s) from the parquet timestamp; missing frames in range | capture-time skew, because both sides are `frame_index/fps` |
| Episode clamping and `*_is_pad` | `dataset_reader.py:305-324` | windows crossing episode boundaries | — |
| `sanity_check_dataset_robot_compatibility` (only with `--resume`) | `common/control_utils.py:126-151`, `record.py:215` | `robot_type` / `fps` / `features` mismatch when resuming | — |
| `check_version_compatibility` / `get_safe_version` | `datasets/utils.py:353+`, `lerobot_dataset.py:336-340` | codebase-version (`v3.0`) tag mismatch against the Hub | — |
| Episode stats (min / max / mean / std / count / quantiles) | `compute_stats.py:504+`, aggregated at `:650` | nothing by itself (normalization input) | — |
| Hub checksums / content hashes | none in `datasets/` (grep for sha256/checksum/hashlib finds only language_render sampling seeds) | — | integrity rests entirely on the Hub git revision; the `v3.0` tag is deleted and recreated on each push (`lerobot_dataset.py:723-726`) |
| `check_timestamps_sync` | absent at this SHA | — | — |

### Q10. Components with limited write access, and where the boundaries are (only those in code or docs, all SC)

- **In-process, no isolation:** the Clutch, the processor pipeline steps (`MapXRControllerActionToRobotAction`, `EEBoundsAndSafety`, IK) and the recorder all run in one Python process and share mutable dicts. `ProcessorStepRegistry.register` is a global registry (`xr_controller_processor.py:38`). No write-access boundary exists between a processor step and the dataset frame.
- **IsaacTeleop external inputs:** `step()` validates keys (a collision with a DeviceIO source name raises; unknown keys are silently ignored) (`teleop_session.py:466-474, 537-538, 907-990`). That is a schema check, not an access check.
- **Leader-arm variant only:** joint data arrives through the CloudXR tensor channel from the separate `so101_leader` plugin process, keyed by `collection_id` (default `"so101_leader"`) (`config_isaac_teleop.py:125-127`, `teleop_so101_leader_arm.py:131-136`). The plugin is spawned by the example with `subprocess.Popen` (`common.py:471-493`). No authentication of the pushing process is visible in the LeRobot code (NV on the IT side).
- **CloudXR runtime / network:**
  - The WSS proxy binds all interfaces (`host=""`) on port 48322 (IT `src/python/isaaccapture/cloudxr/wss.py:660-666`; `oob_teleop_env.py:24`), with a self-signed cert the operator accepts in the browser (LR `common.py:215-217, 280`).
  - Backend port 49100 is documented (`oob_teleop_env.py:101`).
  - The run dir is `~/.cloudxr/run`. `env_config` creates it with mode 0700 and writes its env file with mode 0600 (IT `cloudxr/env_config.py:96-98, 170-173`), but `runtime._setup_openxr_dir` uses mode 0755 (`runtime.py:354`).
  - Logs go to `~/.cloudxr/logs` (LR `default.env`, `NV_CXR_FILE_LOGGING=true`).
  - The MCAP viser viewers bind every interface by default (IT `docs/source/references/mcap_record_replay.rst:184-186`).
- **Dataset files on disk before push:** plain files under `cfg.dataset.root` (or `HF_LEROBOT_HOME/<repo_id>`). The writer does no permission hardening and records no hash. Temp PNGs live under `root/images/` until encoded (`dataset_writer.py:258-265`). `push_to_hub` uploads whatever is in `root`, minus `images/` (`lerobot_dataset.py:685-716`).
- **Hub:** write access is gated by the HF token (the `HfApi()` default). The repo is created with `private=None`, i.e. the org default (`configs/dataset.py:45`). The push also runs from `finally` after a crash (`record.py:305-309`).
- **Motor bus:** `/dev/ttyACM*` serial, protected only by OS device permissions (not in the code).

## 3. IsaacTeleop's own recorders and replay

### `examples/lerobot/record.py` (IT; head and hands only)
- Uses `DeviceIOSession` directly, with `HandTracker` and `HeadTracker` (IT `examples/lerobot/record.py:84-102`). SC
- Features: `observation.head`, `observation.left_hand`, `observation.right_hand`, each position-only float32 (3,) (`:36-67`). There is **no `action`, no robot and no camera**. SC
- An invalid or untracked pose becomes **zeros**, which cannot be told apart from a real origin (`:133-156`). SC
- `fps=60` is declared (`:75`), but the loop does `update()`, then `add_frame`, then `time.sleep(0.016)` (`:120-192`), so the true rate is below 60. Stored timestamps are still `frame_index/60`. SC
- The loop is hard-coded to 10 s (`:118`), despite the "60 seconds" banner (`:110`). A single episode is saved even after `KeyboardInterrupt` (`:193-198`). SC
- Stored locally under `examples/lerobot/local_datasets/teleop_tracking_<ts>` with `repo_id="teleop/tracking_demo"`. No push. SC

### MCAP record/replay (IT)
- **Enabling it:** set `TeleopSessionConfig(mcap_config=McapRecordingConfig(file))`. Channels are auto-discovered from the pipeline sources (IT `docs/source/references/mcap_record_replay.rst:14-60`; `teleop_session.py:1106-1126`). SC
- **Writer:** `mcap::McapWriterOptions("teleop")` with `compression=None` (IT `src/core/deviceio_session/cpp/deviceio_session.cpp:84-94`). SC
- **Messages:**
  - Each message is a FlatBuffer `*Record{data, DeviceDataTimestamp}`.
  - `logTime = publishTime = available_time_local_common_clock` (monotonic ns); `sequence` is a per-channel counter.
  - A write failure is only logged as an error (IT `src/core/mcap/cpp/inc/mcap/tracker_channels.hpp:75-104`). SC
- **What it records:** raw tracker snapshots (for controllers: grip/aim pose, `is_valid` and inputs, `live_controller_tracker_impl.cpp:446-448`). It does **not** record retargeter outputs, external inputs (such as `base_T_anchor`), robot commands or state, or camera frames. SC
- **Replay:** `SessionMode.REPLAY` + `McapReplayConfig` (docs `:62-105`). SC
  - Before the first frame it compares the recorded schema with the running schema and raises on incompatibility (docs `:107-127`; `tracker_channels.hpp:380-399`).
  - Each message is checked with a FlatBuffers `Verifier`, which is structural only (`tracker_channels.hpp:404-414`).
  - `ReplayControllerTrackerImpl::update` **ignores the time argument** and advances one record per `step()`. A missing record becomes `None`, with a one-time warning (IT `src/core/replay_trackers/cpp/replay_controller_tracker_impl.cpp:44-77`).
  - So replay is step-indexed, not paced by the recorded timestamps.
- **Chunk/data CRCs:** whether they are enabled depends on the upstream mcap library defaults (not set explicitly here). NV
- **No link to LeRobot:** nothing in the LeRobot example connects an MCAP file to a LeRobotDataset episode (no shared IDs or clock). SC

## 4. ROS involvement

None on this path. The LR example, the LR robot/dataset code and the IT pieces used here (`TeleopSession`, `ControllersSource`, `ControllerTransform`, the live controller tracker, CloudXR launcher, MCAP) use no ROS or rclpy. SC (grep for ROS/rclpy/ros2 in `examples/isaac_teleop_to_so101/`: no hits). ROS appears only in IT's separate `examples/teleop_ros2/` and in `isaac_ros_teleop`, which consumes IT-1.4. Neither is on this path.

---

# 2. XR → Isaac Lab (isaaclab_teleop) → recorder → HDF5 → replay / Mimic / robomimic

Paths relative to references/upstream/IsaacLab unless noted. SC=SOURCE_CONFIRMED, NV=NOT_VERIFIED.

## 1. RecorderManager (source/isaaclab/isaaclab/managers/recorder_manager.py) [SC]
- Imports: torch L14, warp L15, prettytable L16; EpisodeData/HDF5DatasetFileHandler L19.
- DatasetExportMode L27-33: NONE / ALL / SUCCEEDED_FAILED_IN_SEPARATE_FILES / SUCCEEDED_ONLY.
- Cfg defaults L40-57: export dir /tmp/isaaclab/logs, export_in_record_pre_reset=True, export_in_close=False, compression=True.
- Hooks docstring L67-71: pre_reset, post_reset, pre_step (after action processed, before applied), post_step (end of step), + post_physics_decimation_step L133.
- Failed file = f"{filename}_failed" L194-199.
- add_to_episodes L311-350: clones tensor, per env append; warp->torch.
- record_pre_reset L404-434: success = termination_manager "success" term[env_ids] (L426-431) -> set_success; then export if export_in_record_pre_reset.
- get_ep_meta L453-468: sim_args {dt, decimation, render_interval, num_envs} OR env.cfg.get_ep_meta(). No seed, no version, no hash.
- export_episodes L470-551: routing by mode+success L519-529; counts L537-543; buffer reset L545; flush L547.
- close L553-567: export_in_close then close handlers; term.close(file_path).

## 2. Recorder terms (envs/mdp/recorders/recorders.py, recorders_cfg.py) [SC]
- InitialStateRecorder L14-24: "initial_state" = scene.get_state(is_relative=True)[env_ids] at post_reset.
- PostStepStatesRecorder L27-31: "states" = scene.get_state(is_relative=True) at post_step (ACTUAL sim state).
- PreStepActionsRecorder L34-38: "actions" = action_manager.action at pre_step (raw action tensor fed to env.step = COMMANDED, pre-processing).
- PreStepFlatPolicyObservationsRecorder L41-45: "obs" = env.obs_buf["policy"] at pre_step (i.e. obs computed at END of previous step / reset -> obs that the action was chosen on).
- PostStepProcessedActionsRecorder L48-62: "processed_actions" = concat of each term's processed_actions (after scale/offset/clip; for IK = target pose after processing) at post_step.
- ActionStateRecorderManagerCfg recorders_cfg.py L66-74 bundles all five.

## 3. HDF5DatasetFileHandler / EpisodeData (utils/datasets/) [SC]
- hdf5_dataset_file_handler.py imports: json,os L8-9; numpy L12; torch L13; `from ..math import convert_quat` L15 (utils/math.py imports only logging/math/numpy/torch L11-17); h5py imported lazily inside open L55/create L65/load_episode L166/convert L288. NO omni/isaacsim/warp.
- DATASET_FORMAT_VERSION=1 (XYZW quats) L19-22; file attr "format_version" L77.
- Layout: /data group attr total L81, attr env_args JSON L87,L97-103 ({"env_name","type":2} robomimic-compat + ep_meta sim_args from RecorderManager). /data/demo_N groups L221-224; attrs num_samples=len(actions) L226, seed (if set) L228-229, success L231-232; datasets recursively from nested dict, gzip level 2 L234-243. No timestamps, no per-step time key, no hash, no version of isaaclab/sim, no env cfg dump.
- Duplicate demo name -> ValueError L222-223. Loading: legacy root_pose wxyz->xyzw L192-193.
- episode_data.py imports only torch (L8 of file). add() accumulates list L422-448 (file L88-114); pre_export torch.stack L495-505 -> requires all per-step tensors same shape. get_state/get_next_state, get_joint_target ("joint_targets" key).
- Seed: EpisodeData.seed exists but no recorder in this path sets it (grep below).
- Package chain: isaaclab/__init__.py only stdlib + find_spec; isaacsim import only inside bootstrap_kernel() L148-157 which is "not called currently" (comment L145-147). utils/__init__.py uses lazy_loader L10. datasets/__init__.py -> utils/module.lazy_export (lazy_loader). => Standalone use needs numpy, torch, h5py, lazy_loader (+ importlib metadata). SC by reading; NV by execution.

## 4. env.step / action manager / decimation (source/isaaclab/isaaclab/envs/manager_based_rl_env.py) [SC]
- step L174: process_action(action) L205 -> recorder.record_pre_step L207 (actions + obs recorded here) -> decimation loop L214-224: apply_action, write_data_to_sim, sim.step(render=False), record_post_physics_decimation_step L220, render every render_interval L222 -> counters L228-229 -> termination_manager.compute L231 -> if recorders active: obs_buf=observation_manager.compute() L238 + record_post_step L239 (states, processed_actions) -> resets: record_pre_reset L247 (success + export), _reset_idx L249, record_post_reset L255 (initial_state). Visualizer UI reset L259-269 mirrors lifecycle. Final obs recompute after reset L279.
- => Per step t: actions[t] (raw input), obs[t] = policy obs computed at end of step t-1 (or post-reset), states[t] = scene state after action t (pre-reset, so last element is terminal state), processed_actions[t] = after-step read of term buffers.
- ActionManager.process_action (managers/action_manager.py L381-402): dim check raises ValueError L391-392; _action stored L395; split per term. action property L268-270 = raw input.
- Clock: only sim-step counters (_sim_step_counter, episode_length_buf, common_step_counter). No wall-clock anywhere in the recorder path. Time recoverable only from index * step_dt (env_args sim_args dt, decimation).
- Stack env (contrib/stack/stack_env_cfg.py L385-391): decimation=5, episode_length_s=30, sim.dt=0.01 (100 Hz physics), render_interval=2 -> step_dt=0.05 s (20 Hz control/record).
- Stack policy obs L205-222: last_action, joint_pos_rel, joint_vel_rel, object, cube pos/quat (world), eef_pos, eef_quat, gripper_pos; concatenate_terms=False -> recorded as obs/<term>. rgb_camera group L225-230 empty in base; subtask_terms L233-263 (grasp_1, stack_1, grasp_2). Terminations L272-289: time_out, cube_*_dropping, success=cubes_stacked.

## 5. Action terms / IK (commanded vs actual) [SC]
- DifferentialInverseKinematicsAction (envs/mdp/actions/task_space_actions.py): process_actions L189-200: raw_actions=actions; processed=raw*scale; optional clamp (cfg.clip) L193-196; set_command(processed, ee_curr). apply_actions L202-219: IK compute per physics substep -> joint_pos_des -> set_joint_position_target_index. If ee_quat norm==0, holds current joints L213-217 (silent). joint_pos_des NOT exposed to recorder (not a recorded key).
- DifferentialIKController.set_command (controllers/differential_ik.py L119-175): abs pose: quat normalized; non-finite -> silently replaced by current ee_quat L170-175 (not recorded). rel: apply_delta_pose.
- JointAction.process_actions (envs/mdp/actions/joint_actions.py L169-177): processed = raw*scale+offset, optional clamp_.
- SO101 IK-Abs (contrib/stack/config/so101/stack_ik_abs_env_cfg.py): pipeline L67-169 (SO101ClutchRetargeter + SO101GripperRetargeter + TensorReorderer, 8D [pos xyz, quat xyzw, gripper closedness 0..1]); controller rebased to robot base frame via target_frame_prim_path L304; actions L249-290 (SO101PoseIKActionCfg scale=1.0 adaptive_dls, gripper JointPositionAction scale=CLOSE-OPEN, offset=OPEN); clip unsupported -> NotImplementedError (pose_ik_action_term.py L109-113). No robomimic entry point for SO101 (so101/__init__.py L28-35).
- Franka IK-Abs "IsaacContrib-Stack-Cube-Franka-IK-Abs" (franka/__init__.py L116-120, robomimic bc_rnn_low_dim.json): pipeline Se3AbsRetargeter+GripperRetargeter (stack_ik_abs_env_cfg.py L24-106), world frame via world_T_anchor; DiffIK abs pose dls, scale default L120-125. Docstring L33 says quat_w-first but elements xyzw L87 (doc inconsistency).
- Franka IK-Rel (stack_ik_rel_env_cfg.py L30-67): DiffIK use_relative_mode=True scale=0.5; teleop_devices keyboard/spacemouse only; NO isaac_teleop cfg in this file (grep) -> XR not configured for IK-Rel here.
- Commanded vs actual: actions (raw command) + processed_actions (scaled/offset/clipped command; for IK-Rel = scaled delta, not absolute target) vs states (articulation joint pos/vel, root poses) + obs/eef_pos/eef_quat (actual EE). IK joint targets & actual applied joint targets not recorded by default.

## 6. scripts/tools/record_demos.py [SC]
- Imports: `import warp as wp` L36 (before launcher); isaaclab.app launch_simulation L47; after launch: torch L176, isaaclab_physx.renderers L177, isaaclab.devices.openxr L179, isaaclab_mimic.envs L185; omni.ui in setup_ui L488. args_cli.require_kit=True L154 -> needs Isaac Sim/Kit.
- CLI: --teleop_device L61-70 (explicit forces legacy path), --dataset_file L71-73, --step_hz 30 L74, --num_demos L75-77, --num_success_steps 10 L78-83, --reset_sim_buffer_each_episode L84-92, --cloudxr_env L93-102, --mcap_record_path L109-120 ("Debug-only ... NOT a data-generation format ... lack per-episode segmentation, world-frame anchor state, env reset state"), --disable_external_cameras L129-138.
- Stack selection L328-331: IsaacTeleop if env_cfg.isaac_teleop set and no --teleop_device.
- Env cfg mutation (create_environment_config L295-367): num_envs=1 L320, env_name=task L321; success term REPLACED with inert _never_terminate L336-338 (so env termination_manager "success" is always False and never auto-resets on success); time_out=None L355; policy concatenate_terms=False L356; recorders=ActionStateRecorderManagerCfg unless task gives demo_recorder_cfg_entry_point L358-362; export mode EXPORT_SUCCEEDED_ONLY L365 (hard-coded; no CLI to change).
- RateLimiter L239-269: wall clock time.time() only for pacing (not recorded); disabled with --xr (OpenXR paces) L850-857.
- Success: process_success_condition L505-537: calls success_term.func(env)[0] each loop iter; counter +1 else reset to 0; at >= num_success_steps: record_pre_reset([0], force_export_or_skip=False) (runs pre-reset terms, sets success=False from inert term, no export) then set_success_to_episodes True, export_episodes([0]) L527-531 -> demo attr success=True.
- NOTE (SC by reading): process_success_condition is called L743 every loop iteration regardless of running_recording_instance (paused iterations don't step env but still increment success counter if state satisfies success). It is skipped only when action is None (continue L719-722).
- Callbacks L610-639: R/RESET -> reset_recording_instance (ignored if success_step_count>0 L612-617); START/STOP -> running flag. IsaacTeleop: poll_control_events L712-717 sets is_active / should_reset. Keyboard B/P/R L662-675.
- Loop L707-786: action=teleop_interface.advance() L710; None -> render, skip (no step, no record) L719-722; if running: env.step(actions) L727-729 (recorded) else render only L737-740 (paused steps NOT recorded; no marker of pause gap in data).
- Reset handle_reset L540-572: env.sim.reset() optional, recorder_manager.reset() L566 (DISCARDS in-progress episode buffer, no export), env.reset() (record_pre_reset -> empty -> nothing; post_reset -> new initial_state), teleop_interface.reset().
- Failures (env termination e.g. cube dropping): env.step auto-resets -> record_pre_reset success False -> with EXPORT_SUCCEEDED_ONLY not written; counted in exported_failed_episode_count only (recorder_manager.py L542-543). No failed-file output from record_demos.
- Exit at num_demos L757-770; env.close() L868 -> recorder close (export_in_close False by default).
- Device create failure -> exit(1) L464-470.

## 7. XR -> retargeting -> action (isaaclab_teleop + IsaacTeleop) [SC unless noted]
- IsaacTeleopDevice.advance (source/isaaclab_teleop/isaaclab_teleop/isaac_teleop_device.py L290-354): target_T_world from target_frame_prim_path via _get_target_frame_T_world L451-510 (omni.usd/usdrt/pxr; on failure logs warning and returns None L508-510 -> falls back to world_T_anchor only, i.e. world frame instead of base frame, silently for the data). Calls session_lifecycle.step; returns action tensor or None.
- TeleopSessionLifecycle.step (session_lifecycle.py L1141-1245): None if session not started / restart holdoff (time.monotonic) L1184-1189; pending host reset -> ExecutionEvents(reset=True, RUNNING) L1197-1202; session.step exception -> teardown, return None L1209-1228 (XR "Stop AR" / pipeline error = no action = no env step = not recorded); else action = torch.from_dlpack(result["action"][0]) float32 L1238-1243. Only "action" extracted; IsaacTeleop GraphTime (sim_time_ns, real_time_ns; IsaacTeleop teleop_session_manager/async_retarget_runner.py L86-95) NOT propagated to Isaac Lab / recorder.
- Execution default (session_lifecycle.py L985-998): RetargetingExecutionConfig(mode="pipelined", DeadlinePacingConfig(safety_margin_s=0.025)); IsaacTeleop config.py L260-266: pipelined "returns the latest completed retarget frame while submitting the current step request to a background worker" -> action may be one or more frames stale and may repeat; no frame_id/timestamp stored in HDF5.
- Control events (session_lifecycle.py L166-176): RUNNING->is_active True, PAUSED/STOPPED->False, reset flag.
- Tracking loss (IsaacTeleop src/python/isaaccapture/retargeters/SO101/clutch_retargeter.py _compute_fn L561-642): dropped frame (inp.is_none) L577-584, invalid pose bit L586-594, non-finite/degenerate L600-613, disengaged L615-619 -> output HOLDS _last_pose (non-None) -> Isaac Lab still steps and records it as a normal action. No validity flag reaches the dataset. Reset re-seeds from configured home L565-573. Se3AbsRetargeter (retargeters/se3_retargeter.py ~L209-258) similarly holds _last_pose on invalid grip pose.
- IsaacTeleop Python package is `isaaccapture`; `isaacteleop` is a compat shim (IsaacTeleop pyproject.toml L12, L100, L143).
- --mcap_record_path: live session debug MCAP, explicitly not data-gen (record_demos.py L109-120).

## 8. scripts/tools/replay_demos.py [SC]
- Imports: warp L9, isaaclab.app launch_simulation L16; require_kit=True L61; torch L77; isaaclab.utils.datasets L79.
- Mode: ACTION replay only (no state-playback mode): env.reset_to(initial_state, is_relative=True) L205, then env.step(recorded actions) L223. Idle action for exhausted envs L157/L329-332.
- Options: --validate_states (num_envs==1 only, L32-40, L322-326), --validate_success_rate L41-46 (success_term evaluated after last action L163-182; failed ids printed L361-363), --select_episodes, --reset_sim_buffer_each_episode.
- All recorders and terminations disabled for replay L293-294 (so replay doesn't write a dataset and cube-drop doesn't reset).
- compare_states L97-124: only "articulation" and "rigid_object" types; iterates runtime keys; per-element abs diff > 0.01 (single absolute tolerance, mixed units m/rad/quat/vel) -> prints mismatch; does NOT abort, does not count, not included in exit status. Only prints "matched"/"mismatched" per step L234-238.
- Possible shape issue (SC by reading, NV by execution): dataset state from get_next_state uses keep_dim=True (episode_data.py _index_nested -> data[index, None], shape (1,D)); runtime state indexed [env] -> (D,). compare_states L116-117 compares len() and raises ValueError on mismatch; the recorder tests' own compare_states index `[0]` on the dataset side (test_action_state_recorder_term.py L55), replay_demos does not. => --validate_states may raise for D != 1. Must be checked by execution before relying on it.
- Replay rate: no rate limiter; pause via keyboard B/N L316-319. No comparison of processed_actions, obs, or camera.

## 9. Existing tests [SC]
- source/isaaclab/test/cli/test_replay_demos_loop_termination.py (L84-114): extracts replay_episodes_loop via ast and runs with stubs (no sim); asserts exactly one env.step per recorded action and idle action never applied (regression: zero-quat idle crash on IK). Detects loop over-stepping only. state_validation disabled.
- source/isaaclab/test/utils/test_hdf5_dataset_file_handler.py (unit): file creation/.hdf5 suffix, env_args preservation on reopen/reset, write+load round-trip of initial_state, actions, seed, success, env_name. No corruption/tamper/schema checks.
- source/isaaclab/test/utils/test_episode_data.py (unit): add/stack/get_initial_state/get_next_action semantics.
- source/isaaclab/test/envs/test_action_state_recorder_term.py (integration, launch_test_simulation L6-8): only initial_state recorder correctness incl. partial reset (L85-129), tolerance 0.01. Does NOT test actions/states/processed_actions/obs timing.
- test_action_state_recorder_term_task_integration.py (IsaacContrib-Lift-Cube-Franka, L90-119): same initial_state check via gym wrapper.

## 10. Mimic annotate_demos.py / generate_dataset.py [SC]
- annotate_demos.py: imports isaaclab.app launch_simulation L13 (Kit). Loads input HDF5 L170-173; env via parse_env_cfg(env_name or --task) L194; success term removed from env and checked manually L197-203; recorders = MimicRecorderManagerCfg (ActionStateRecorderManagerCfg + datagen_info + subtask start/term signals) L155-161, L209-219; default export mode EXPORT_ALL (not overridden) but export only called for successfully annotated episodes L316-324.
- PreStepDatagenInfoRecorder L103-116: obs/datagen_info/{object_pose, eef_pose, target_eef_pose = env.action_to_target_eef_pose(action_manager.action)} — first place a "target EE pose" (commanded) sits next to actual eef_pose in one file.
- replay_episode L344-386: env.sim.reset, recorder reset, reset_to(initial_state) L365-369; steps every recorded action L371-382; success checked ONLY after last action L383-385. => Output dataset is a RE-SIMULATION: states/obs/processed_actions are regenerated, the original teleop states are not carried over or compared. No state comparison vs input.
- Auto mode L389-431: requires every subtask_term_signal to fire at least once (torch.any) and optionally start signals. Manual mode L434-539: operator presses S; count must equal expected; signals written as step functions L518-537.
- Exit code = successful count L542-545.
- Mimic env IDs (source/isaaclab_mimic/isaaclab_mimic/envs/__init__.py L17-208): Franka IK-Rel/IK-Abs Mimic, etc. NO SO101 Mimic env => SO101 IK-Abs data cannot go through Mimic as shipped.
- generate_dataset.py: seeds random/np/torch from datagen_config.seed L156-159 (not written per demo to file by generator; EpisodeData.seed unused). setup_env_config (datagen/generation.py L170-228): removes success & all terminations L202-211; recorder = mimic_recorder_config or ActionStateRecorderManagerCfg L215-217; export EXPORT_SUCCEEDED_FAILED_IN_SEPARATE_FILES if generation_keep_failed else SUCCEEDED_ONLY L223-226. data_generator.py L993-997 set_success + export. Source-demo index (selected_src_demo_ind) is used internally but not added to the episode (no add_to_episodes in data_generator.py) -> generated demos carry no provenance link to source demo IDs (SC by grep).

## 11. robomimic train.py + config [SC]
- scripts/imitation_learning/robomimic/train.py imports L46-75: argparse..traceback stdlib; gymnasium L56; h5py L57; numpy L58; psutil L59; robomimic.* L60-68; torch L65; DataLoader L69; `from isaaclab.app import launch_simulation` L71; `import isaaclab_tasks` L73, contrib.locomanip_pick_place L74, contrib.pick_place L75. Entry: `with launch_simulation(None, {"headless": True}): main(args)` (~L307-309).
- launch_simulation(None,...) (source/isaaclab/isaaclab/app/sim_launcher.py L558-640): scan() with no physics cfg -> needs_kit = ... or not has_physics (L318) -> "the default Isaac Sim / Kit runtime" (L485-486) -> Kit launcher started. isaaclab.app import itself pulls isaaclab_newton, isaaclab_ov, isaaclab_physx cfg modules (sim_launcher.py L25-29). => train.py AS SHIPPED requires Isaac Sim/Kit (SC by reading; NV by execution).
- Config lookup: gym.spec(task).kwargs["robomimic_<algo>_cfg_entry_point"] (train.py main ~L204-229) -> needs isaaclab_tasks registry. Franka IK-Rel / IK-Abs -> agents/robomimic/bc_rnn_low_dim.json.
- bc_rnn_low_dim.json: train.dataset_keys=["actions"], seq_length=10, hdf5_filter_key=null (all demos), hdf5_normalize_obs=false, seed=101, cuda=true; obs.low_dim=[eef_pos, eef_quat, gripper_pos, object] (under /data/demo_N/obs/); rollout.enabled=False.
- => robomimic trains on /data/demo_N/actions (RAW pre-step action = teleop/retargeter output, pre-scale/clip), NOT processed_actions, NOT states. Success attr not consulted by config (hdf5_filter_key null); NV whether robomimic itself reads "success".
- Optional --normalize_training_actions (normalize_hdf5_actions L78-121): copies file, global scalar min/max over all action dims -> [-1,1], writes normalization_params.txt; assumes demo_0..N-1 contiguous naming (L97).
- Env metadata from file: FileUtils.get_env_metadata_from_dataset (data attr env_args JSON: env_name, type=2, sim_args).
- SO101 IK-Abs has no robomimic entry point -> --task lookup fails for it (so101/__init__.py L28-35).

## 12. Limited-write / derivative components [SC]
- Recorder terms are chosen in env cfg (env_cfg.recorders); record_demos overwrites with ActionStateRecorderManagerCfg unless task registers demo_recorder_cfg_entry_point (record_demos.py L358-362). Export mode forced SUCCEEDED_ONLY L365.
- Dataset file on disk: plain HDF5, gzip; no signature/hash/checksum; handler flushes after each export (recorder_manager.py L547-551); file opened "w" at env creation (hdf5 handler L74) -> re-running with same --dataset_file truncates the previous file.
- scripts/tools/merge_hdf5_datasets.py L23-43: h5py copy of every data/<episode> renamed demo_<k> sequentially (group attrs e.g. success/num_samples/seed travel with the group); data.attrs env_args taken from FIRST input only L39-41; file-level attr format_version NOT copied and data.attrs total not written. NOTE: HDF5DatasetFileHandler.get_format_version returns 0 when attr missing (hdf5 handler L140-142) -> load_episode auto-converts root_pose wxyz->xyzw (L173-174, L192-193) on merged files that were already xyzw (SC by reading; NV by execution). No check that env_name/env_args of inputs match.
- scripts/tools/mp4_to_hdf5.py L93-163: copies whole data group, then for each mp4 creates new demo with actions, obs/eef_pos, eef_quat, gripper_pos, table_cam (frames from mp4), wrist_cam copied; attrs num_samples only (L127-130). New demos lack initial_state, states, success attr, processed_actions, other obs; no check frames count == num_samples. Same missing format_version issue (f_out file attrs not copied).
- Mimic-generated data: re-simulated by generator; success via generated_success; source demo index not recorded (section 10).
- annotate_demos output = re-simulation of input actions (section 10).

## 13. ROS on this path [SC by grep]
- IsaacLab: `grep rclpy|ros2` over source/ and scripts/ .py -> only source/isaaclab_tasks/isaaclab_tasks/contrib/deploy/gear_assembly/config/ur_10e/ros_inference_env_cfg.py (unrelated deploy task). None in isaaclab_teleop, managers, datasets, record/replay, mimic, robomimic scripts.
- IsaacTeleop: rclpy only in examples/teleop_ros2/ (Dockerfile, teleop_ros2_node.py, node_parameters.py, integration test). Not on the isaaclab_teleop path.

## 14. Documented workflow & stated limitations (quotes) [SC]
docs/source/features/imitation-learning/teleop_imitation.rst:
- L6-7 "Isaac Lab Mimic is only supported on Linux."
- L31 "The new demonstrations are evaluated to determine if they are successful, and if so, are added to the output dataset."
- L34-35 "The use of rigid body transformations requires that the embodiment's action space is defined in **task space**."
- L197-199 "Note that when using hand tracking, we recommend using the absolute action space variant of the task (``IsaacContrib-Stack-Cube-Franka-IK-Abs``)"; XR record cmd L260-269 (`isaaclab teleop record --task IsaacContrib-Stack-Cube-Franka-IK-Abs --viz kit --dataset_file ./datasets/dataset.hdf5 --num_demos 10 --xr`).
- L290 "Do not have extended pauses. ... It is not obvious for a policy why and when to pause"
- L292-293 "press the ``R`` key ... to discard the current demonstration and reset to a new starting position."
- Replay L297-304 (`isaaclab teleop replay ... --num_envs 1 --reset_sim_buffer_each_episode`); L306 "Collect 10 successful demonstrations".
- Annotate L357-362 (`--task Isaac-Stack-Cube-Franka-IK-Rel-Mimic-v0 --auto --input_file ... --output_file ...`); L408 "The output_file of annotate_demos.py is the input_file to generate_dataset.py."
- Train L503-506 (`robomimic/train.py --task IsaacContrib-Stack-Cube-Franka-IK-Rel --algo bc --dataset ./datasets/generated_dataset.hdf5`).
- L752-753 "If recording stops on the frame the success term triggers, it may not re-trigger during replay" / "Allow for some buffer at the end of recording"
- L757 "Physics in IsaacLab are not deterministically reproducible when using ``env.reset`` so demonstrations may fail on replay"
- L758 "Collect more human demos than needed, use the ones that succeed during annotation"
- L759 "All data in Isaac Lab Mimic generated HDF5 file represent a successful demo and can be used for training (even if non-determinism causes failure when replayed)"
- CLI mapping: `isaaclab teleop record/replay` -> scripts/tools/record_demos.py / replay_demos.py (source/isaaclab/isaaclab/cli/__init__.py L144-145).
docs/source/features/isaac_teleop.rst:
- L195-197 start/stop/reset "are used to begin and end demonstration recording, pause the robot, or reset the environment"; L257 "``should_reset`` -- ``True`` for exactly one frame after a "reset" command."
- L302-307 --xr (Kit XR path) vs without (IsaacTeleop owns OpenXR session via CloudXR, headless).
- L327-331 keys B start/resume, P "Pause teleoperation (robot holds position)", R reset.
- L574-579 (SO-101 joint teleop) "Pressing ``R`` both resets the environment **and pauses teleoperation**".
- L701-706 table: "``IsaacContrib-Stack-Cube-SO101-IK-Abs-v0`` with ``physics=isaacsim_physx`` ... absolute IK (clutch-rebased; IK tracks position, orientation soft-weighted). Gripper: right trigger (analog)."
- L1111-1118 retargeting_execution "Defaults to ``RetargetingExecutionConfig(mode="pipelined")`` with ``DeadlinePacingConfig(safety_margin_s=0.025)`` so retargeting can run on the IsaacTeleop worker instead of blocking the simulation loop."
- L1384-1386 "``robot_pov_cam`` is also a policy image observation, so the normal demonstration recorder stores the same view shown to the operator."; L1455-1456 recorded training view needs CameraCfg + mdp.image_rgb in observations.policy.
- L1718-1719 "When replaying a preset-configured dataset, pass the same selectors again. The HDF5 metadata stores the registered task ID, but not the command-line selector values"
- L1741-1750 workflow list, ending "Use the recorded data with Isaac Lab Mimic or other imitation learning frameworks."

## 15. Feasibility without Isaac Sim (GTX 1050 Ti) 
- HDF5DatasetFileHandler / EpisodeData: SC (reading) - import chain has no omni/isaacsim/warp/carb/pxr:
  - isaaclab/__init__.py: stdlib + importlib.util.find_spec only; isaacsim import only in uncalled bootstrap_kernel() L148-157.
  - isaaclab/utils/__init__.py L8-12: importlib, lazy_loader.
  - utils/datasets/__init__.py L15-17: utils.module.lazy_export (lazy_loader, stdlib L10-18).
  - hdf5_dataset_file_handler.py L8-17: json, os, numpy, torch, ..math (math.py L11-17: logging, math, numpy, torch, torch.nn.functional), h5py lazily.
  - episode_data.py: torch only.
  - Evidence: test_replay_demos_loop_termination.py (L16-23) and test_hdf5_dataset_file_handler.py (L5-16, pytest.mark.unit) import them without launching sim (handler test also imports isaaclab.test.utils; NV whether that pulls sim).
  - Required pip deps: numpy, torch (CPU ok), h5py, lazy_loader. Execution NOT_VERIFIED.
  - Caveat: RecorderManager (managers/recorder_manager.py L14-15) imports torch AND warp; it also needs a live env -> not usable standalone.
- robomimic train.py AS SHIPPED: needs Kit. `from isaaclab.app import launch_simulation` L71 (sim_launcher.py L25-29 import isaaclab_newton/isaaclab_ov/isaaclab_physx cfg modules), `import isaaclab_tasks` L73-75, `with launch_simulation(None, {"headless": True})` -> needs_kit True for cfg None (sim_launcher.py L318, L485-486). SC by reading.
  - Training core is robomimic (L60-68) + torch + h5py; with rollout.enabled=False the env is not constructed. A robomimic-only run with the JSON config (data=path) should avoid Isaac Sim -- NOT_VERIFIED (robomimic version/compat, and bc_rnn_low_dim.json "cuda": true; GTX 1050 Ti = sm_61, torch wheel support NOT_VERIFIED; CPU fallback by setting train.cuda=false NOT_VERIFIED).
- record_demos / replay_demos / annotate / generate: all require Kit (require_kit=True / launch_simulation with physics cfgs). Not feasible on this machine.
- A file-level offline checker (h5py+numpy only) can read: actions, processed_actions, states, initial_state, obs/*, attrs success/num_samples/seed, data.attrs env_args (sim_args dt/decimation), file attr format_version.

## 16. Q1-Q10 answers (see sections for refs)
Q1 Both recorded: actions (raw, pre_step) + processed_actions (post_step) vs states (post_step scene state) + obs/eef_pos,eef_quat. IK joint targets (joint_pos_des) not recorded. [SC]
Q2 actions = action_manager.action = raw tensor handed to env.step = retargeter output (SO101/Franka abs: [pos, quat xyzw, gripper]); pre-scale/clip. robomimic trains on "actions" (bc_rnn_low_dim.json dataset_keys) + obs eef_pos, eef_quat, gripper_pos, object. [SC]
Q3 No timestamps anywhere; alignment by index only; obs[t] = obs at end of step t-1, states[t] after action t; step_dt=0.05 (dt 0.01 x decimation 5) in env_args sim_args. Camera = policy obs terms (visuomotor), same index as obs; intra-step render timing (render_interval=2 vs decimation=5) NOT_VERIFIED. Retargeter pipelined mode may deliver stale/repeated frames without marker. [SC except noted]
Q4 action None (session not started/torn down/restart holdoff) -> not stepped, not recorded. Pause -> not stepped, not recorded, no gap marker. Tracking loss -> retargeter holds last pose -> recorded as normal action, no flag. Reset -> recorder_manager.reset() discards buffer. Reconnect -> lazy restart. Success counter evaluated also during paused loop iterations. [SC]
Q5 Clipping only if cfg.clip (not set on these tasks; SO101 forbids). Quat fallback/zero-norm hold silent, not recorded. processed_actions would show clip. No controller-failure flag. [SC]
Q6 Start: env.reset -> initial_state. End: manual success after num_success_steps consecutive (export success=True) or env termination (drop) -> discarded (SUCCEEDED_ONLY). Manual reset -> discarded. success attr per demo. Modes: NONE/ALL/SUCCEEDED_FAILED_SEPARATE (_failed file)/SUCCEEDED_ONLY; record_demos hard-codes SUCCEEDED_ONLY; mimic generate uses SEPARATE when generation_keep_failed. [SC]
Q7 Partially: abs tasks: actions pos/quat (base frame for SO101 / world for Franka? frames differ) vs obs eef_pos/eef_quat (frame per mdp.ee_frame_pos; NOT_VERIFIED frame) comparable; rel task needs integration. Mimic annotated adds datagen_info target_eef_pose vs eef_pose. [partly NV]
Q8 Stored: initial_state, states, actions, env_name, sim_args dt/decimation/render_interval/num_envs, format_version. Missing: seed (not set), Hydra selectors (doc L1718-1719), env cfg dump, isaaclab/isaacteleop/isaacsim versions, git hash, content hashes, wall-clock, teleop validity. Replay non-deterministic per docs L757. [SC]
Q9 replay_demos --validate_states: abs tol 0.01 per element, print-only, num_envs 1, possible shape bug (NV). --validate_success_rate final-step success. Annotate: final success + subtask signals; no state comparison. Tests: loop termination, handler round trip, episode data, initial_state recorder only. [SC]
Q10 recorder cfg in env cfg / record_demos overrides; HDF5 file unsigned; merge (env_args first file, no format_version -> legacy quat conversion risk NV), mp4_to_hdf5 (partial demos), mimic generated/annotated (re-simulated, no provenance). No ROS on path. [SC]

---

# 3. Isaac ROS Teleop / IsaacTeleop teleop_ros2 / MCAP record-replay / WebXR input recorder


47f33af3 is not a descendant of de761a03 (merge-base 7968ce10); package renamed isaacteleop→isaaccapture at 47f33af3.

## ROS topics
- launch isaac_ros_teleop.launch.py: teleop_ros2_node (:180-210), pose_reset_node (:214-228, only if pose_reset_config non-empty). Mode/hand_retargeter/mcap_replay_path not passed (:184-200) → controller_teleop + trihand, LIVE. rate_hz 60 (:78-82); transform_rotation [0.5,-0.5,-0.5,0.5] (:121-128); use_sim_time false (:171-178).
- teleop_ros2_node.py:93-112 publishers, default QoS 10: xr_teleop/ee_poses (NamedPoseArray header,name[],pose[],is_valid[] — msg:5-8), xr_teleop/hand, finger_joints (JointState), head_pose, root_twist, root_pose, controller_data (ByteMultiArray msgpack, "timestamp": time.time_ns() — messages.py:169), full_body (:348), /tf.
- Stamps: node clock now() after session.step() (teleop_ros2_node.py:227-236); XR DeviceDataTimestamp never copied into ROS msgs. Live trackers locate at host monotonic update time (deviceio_session.cpp:137-143; live_hand_tracker_impl.cpp:175-180; live_head_tracker_impl.cpp:45-52; live_controller_tracker_impl.cpp:340-343,379,400).
- Loop sleeps fixed period after work (teleop_ros2_node.py:270); no subscriptions; no robot-state feedback.
- pose_reset_node.cpp: subs SensorDataQoS on /xr_teleop/ee_poses (:237-242), /hand (:245-252), /controller_data (:254-261); service ~/reset (:263-270); publishes static TF world→base_link (:399-412); auto-anchor on first valid pair (:287-326), re-anchor while pinch/button combo held (:341-382).

## Recorder / dataset
- No rosbag2 anywhere (isaac_ros_teleop grep; IsaacTeleop git grep at de761a03 zero hits). No documented pipeline from xr_teleop/* topics to a learning dataset. README says "for robot data collection" (README.md:3,9) → external docs, NOT_VERIFIED.
- Existing dataset paths bypass ROS: IsaacTeleop examples/lerobot/record.py:73-79,84-102,179-200 (head/wrist only); LeRobot examples/isaac_teleop_to_so101 (TeleopSession; lerobot base.py:57,144-145; no rclpy); Isaac Lab record_demos.py HDF5 (data_collection_sim.rst:67-80).

## MCAP record/replay
- Records raw DeviceIO tracker state before retargeting; writer owned by DeviceIOSession (deviceio_session.cpp:85-92); every update incl. inactive frames with null data (live_hand_tracker_impl.cpp:182-187; controller :445-450; head :83-87). Channels via TeleopSession source names (teleop_session.py:986-1002; tracker_channels.hpp:26-29; recording_traits.hpp).
- FlatBuffers, embedded schema (tracker_channels.hpp:54-66). DeviceDataTimestamp {available, sample (local common clock, CLOCK_MONOTONIC), raw device} (timestamp.fbs:10-27); live trackers set (update_time, update_time, xr_time) — no device capture time. logTime = available time, per-channel sequence (tracker_channels.hpp:95-99). No hash/signature.
- Replay: SessionMode.REPLAY → deviceio.ReplaySession (teleop_session.py:1004-1007); ReplayDeviceIOFactory (replay_session.cpp:15-28); rest of retargeting pipeline unchanged → **headset-free replay through retargeters and teleop_ros2 (mcap_replay_path) is possible (SOURCE_CONFIRMED; runtime NOT_VERIFIED)**. Replay ignores recorded times, reads next record per channel each step (replay_hand_tracker_impl.cpp:40-63; controller :41-64); EOF → "data not found", null data (:48-52). Replayed data re-stamped with monotonic now (teleop_session.py:500-503) / ROS now.
- teleop_ros2 replay: README.md:170-187 (`-p mcap_replay_path:=...`); REPLAY skips CloudXRLauncher (teleop_ros2_node.py:285-289); CI generator mcap_generator.cpp:172-180. teleop_ros2 has no MCAP record option.
- WebXR client xrInputRecorder.ts: JSON Recording{version:1, frames[{timeMs,...}]} (:45-65), timeMs from predictedDisplayTime (:380-389); replay substitutes recorded input into frame passed to CloudXR tracking (adaptTrackingFrame :534-553; :18-23); pacing time/frame (:436-450); import checks monotonic timeMs (:559-588). No replay flag found; whether server can distinguish replay from live NOT_VERIFIED.
- 47f33af3: README example commands; schema-compat check before replay; timestamps/replay semantics unchanged.

## Lifecycle in teleop_ros2
- Outer loop with TeleopSession while rclpy.ok (:208-282); retry on "Failed to get OpenXR system" every 2 s (:271-280).
- No teleop control pipeline → ExecutionState.RUNNING every step (teleop_session.py:516-520). No clutch/deadman in teleop_ros2.
- Tracking loss: invalid sides → zero pose + is_valid=false (messages.py:52-61, 370-390); head_pose not published while invalid (:403-404); no staleness check. 47f33af3 adds HandTrackingGateRetargeter (hand_tracking_gate_retargeter.py:19-66).

---

# 4. XRoboToolkit (ARX R5, Galaxea R1 Lite via ROS 1, UR5e) → DataLogger → external LeRobot converter


Scope: read-only source audit. Labels: **SOURCE_CONFIRMED** (line refs given, read in the pinned checkout) / **NOT_VERIFIED** (inferred, external doc knowledge, or depends on runtime/deployment). No attack speculation.

Pinned sources used:
- XRoboToolkit-Teleop-Sample-Python @ `79e5cb8a56e3455515ce1b476e993c764ec58739` (commit date 2025-12-31). Paths below are relative to its root; `xtk/` = `xrobotoolkit_teleop/`.
- XRoboToolkit-PC-Service-Pybind (the `xrobotoolkit_sdk` binding, installed by `setup.sh:36-45`) @ `c64ccf6acd577a333e03b66fafe8efeeceb511b1` (HEAD at audit time, fetched to a local scratch checkout; not pinned by the teleop repo — setup.sh clones HEAD).
- zhigenzhao/openpi branch `dev/finetuning` @ `72a2f9bd1a738d9089486ca9a3fb130a8d7027c3`, file `examples/arx_r5/arx_dual/convert_dual_arm_data_to_lerobot.py` (the LeRobot converter linked from README.md:157-161).

---

## Part A — XRoboToolkit-Teleop-Sample-Python

### A.0 Topology (SOURCE_CONFIRMED)

Two different hardware code paths exist:

| Path | Entry script | Controller | Logging? |
|---|---|---|---|
| ARX R5 (single/dual), CAN | `scripts/hardware/teleop_dual_arx_r5_hardware.py`, `teleop_arx_hardware.py` | `xtk/hardware/arx_r5_teleop_controller.py` (subclass of `HardwareTeleopController`) | yes (DataLogger), RealSense cameras |
| Galaxea R1 Lite, **ROS 1 (rospy)** | `scripts/hardware/teleop_r1lite_hardware.py` | `xtk/hardware/galaxea_r1_lite_teleop_controller.py` (subclass of `HardwareTeleopController`) | yes (DataLogger), ROS CompressedImage cameras |
| Dual UR5e (RTDE) + Dynamixel head | `scripts/hardware/teleop_dual_ur5e_hardware.py` | `xtk/hardware/dual_arm_ur_controller.py` (standalone class, NOT a `HardwareTeleopController`) | **no logging at all** (no DataLogger import/use in either file) |
| Simulation (MuJoCo / placo) | `scripts/simulation/*` | `xtk/simulation/*` | **no logging** (grep: no `log`/`DataLogger` in `xtk/simulation/*.py`) |

Threads in `HardwareTeleopController.run()` (`xtk/common/base_hardware_teleop_controller.py:276-327`): `_ik_thread` (125-139), `_control_thread` (141-151), `_data_logging_thread` (153-164), `_camera_thread` (187-270). All share `self.placo_robot.state.q`, `self.active`, `self.gripper_pos_target` without a lock (no `Lock` in the file; only camera interfaces use locks).

### A.1 XR device -> XrClient (SOURCE_CONFIRMED)

- `xtk/common/xr_client.py:10` `xrt.init()`; poses `get_pose_by_name` 13-26 return `[x,y,z,qx,qy,qz,qw]` (docstring 15-16) for `left_controller`/`right_controller`/`headset`. Analog `get_key_value_by_name` 28-43 (trigger/grip float), buttons 45-71 (bool), `get_timestamp_ns` 73-75, hand tracking 77-92 (returns `None` if `is_active` false), motion trackers 106-128 (empty dict if none), body 130-146.
- Binding internals (pybind `bindings/py_bindings.cpp`): all values are process-global last-received state written by the PXREA SDK callback `OnPXREAClientCallback` (93-266) parsing a JSON state string (117-119). Controller pose/trigger/grip/buttons 120-147, head pose 150-156, `timeStampNs` 157-160 (headset-side timestamp from the JSON, device clock — NOT_VERIFIED which clock the headset uses).
- **Disconnect/tracking loss:** `PXREAServerDisconnect` (100-102) and `PXREADeviceMissing` (106-108) only `std::cout`; the globals are not cleared. So after a disconnect, `get_left_grip()` etc. keep returning the last value. There is no per-controller pose validity/tracking flag exposed (only hand `isActive`, 167/178). SOURCE_CONFIRMED for the binding at c64ccf6.
- **The teleop repo never reads the XR timestamp**: the only occurrence of `get_timestamp_ns` is its definition (grep over repo: `xtk/common/xr_client.py:73`). SOURCE_CONFIRMED.
- Network: the PICO headset talks to the "XRoboToolkit PC Service" (README.md:10), which the binding connects to via `PXREAInit` (py_bindings.cpp:273). Transport/auth of that service is closed-source/external — NOT_VERIFIED.

### A.2 Coordinate transform (SOURCE_CONFIRMED)

- `xtk/utils/geometry.py:4-10` `R_HEADSET_TO_WORLD = [[0,0,-1],[-1,0,0],[0,1,0]]` (fixed constant; headset/OpenXR-style y-up frame -> robot z-up world).
- `xtk/common/base_teleop_controller.py:82-113` `_process_xr_pose`: reorders quat to (w,x,y,z) (86-91), rotates position `R_headset_world @ xyz` (93), conjugates orientation by `R_quat` (95-101). **Relative (clutch) mapping**: on first active tick stores `ref_controller_xyz/quat` and returns zero delta (103-108); afterwards `delta_xyz = (xyz - ref) * scale_factor` (110), `delta_rot = quat_diff_as_angle_axis(ref, cur)` (111; `geometry.py:53-73`).
- Target EE pose = reference EE pose (captured from **Placo model after loading actual joint state**) + delta: `base_teleop_controller.py:193-195`, `apply_delta_pose` (`geometry.py:76-126`), set into Placo frame task (206-214).
- UR path duplicates this (`xtk/hardware/dual_arm_ur_controller.py:167-198`). Note: `init_ee_xyz`/`init_controller_xyz` are initialised to zero arrays, not `None` (131-134), so the "first activation" branch (190, 235) is only taken after a prior deactivation (260-265 sets them to `None`). SOURCE_CONFIRMED as code; runtime consequence NOT_VERIFIED.

### A.3 IK / retargeting (placo) (SOURCE_CONFIRMED)

- Setup `base_teleop_controller.py:115-178`: `placo.KinematicsSolver`, `solver.dt = self.dt` (123), frame task (soft, weight 1.0) or position task per manipulator (148-159), manipulability task soft 1e-2 (160-161), optional motion-tracker position task (164-176).
- Per tick `_update_ik` 180-227: `_update_robot_state()` (185; overwrite Placo q with **actual** joint positions), activation = `control_trigger` value > 0.9 (189-190) — this grip is the **deadman/clutch**. On release: reference poses cleared (215-219) but the effector task target is **not** reset (unlike the UR path `dual_arm_ur_controller.py:266-267`). `solver.solve(True)` 225 (integrates q in place); on `RuntimeError` only prints (226-227) — Placo `state.q` then keeps whatever it had.
- Gripper target from analog trigger via `calc_parallel_gripper_position` (`base_teleop_controller.py:346-367`), always, independent of grip/deadman.
- `_ik_thread` (`base_hardware_teleop_controller.py:125-139`) calls `_update_robot_state()` (129) then `_update_ik()` which calls it again (base 185), so `placo_robot.state.q` alternates between "actual" and "solved" within each IK period.

### A.4 Hardware command (SOURCE_CONFIRMED)

- **ARX R5** (`arx_r5_teleop_controller.py:179-190`): if `self.active[arm]` send `q_des = placo_robot.state.q[slice]` via `ARXR5Interface.set_joint_positions` (`interface/arx_r5.py:61-75`: `arm.set_joint_positions` + `set_arm_status(5)`); gripper `set_catch_pos` sent every tick regardless of active (186-190; `arx_r5.py:115-117`). Transport: `arx_r5_python.InterfacesPy(urdf, can_port, 0)` (arx_r5.py:31) over SocketCAN (`can1`, `can3`, controller 32-35). No return value checked; no ack.
- **Galaxea R1 Lite (ROS 1)** (`galaxea_r1_lite_teleop_controller.py:195-210`): if active, `controller.q_des = placo q` (198-199); gripper target always (201-204); **publishes every control tick** `publish_arm_control`/`publish_gripper_control` even when inactive (206-207) — i.e. re-publishes the last `q_des` (hold). Messages: `hdas_msg/motor_control` on `/motion_control/control_arm_{left,right}` and `/motion_control/control_gripper_{left,right}` (`interface/galaxea.py:17-22`, topics from controller 120-126), `header.stamp = rospy.Time.now()`, `frame_id "base_link"`/`"gripper_link"`, with kp/kd/t_ff/p_des/v_des (68-100). Chassis/torso `geometry_msgs/TwistStamped` on `/motion_target/target_speed_chassis`, `/motion_target/target_speed_torso` (galaxea.py:118, 226; controller 139-154), from joystick/X/Y buttons (controller 217-233). Queue size 1.
- **UR5e** (`interface/universal_robots.py:62-72`): `rtde_c.servoJ(q, v=0.5, a=1.0, t=0.017, lookahead=0.1, gain=300)` in an unthrottled loop per arm (`dual_arm_ur_controller.py:297-317`); Robotiq gripper via socket port 63352 (`universal_robots.py:51-52`). IPs hard-coded 192.168.50.55 / .195 (7-8). `servoJ` return value ignored.
- **Dynamixel head** (UR script only): headset orientation -> yaw/pitch (`dynamixel_head_controller.py:85-102`; on exception returns (0,0), 100-102) -> `setGoalPosition` (`interface/dynamixel.py:81-94`).

### A.5 Actual-state readback (SOURCE_CONFIRMED)

- ARX: `get_joint_positions()` / `get_joint_velocities()` from the CAN library (`arx_r5.py:119-139`); `[:6]` into Placo (`arx_r5_teleop_controller.py:173-177`). Converter indexes element 6 of `qpos` as gripper (`convert…py:117-118`), so the library returns >=7 values (NOT_VERIFIED from library source).
- Galaxea: `rospy.Subscriber(arm_state_topic, sensor_msgs/JointState, cb)` (`galaxea.py:23`), topics `/hdas/feedback_arm_{left,right}` (controller 123). Callback 54-64 stores `position[:6]`, `velocity[:6]`, gripper `position[6]`, and `timestamp = msg.header.stamp.to_sec()` (64). **First state message also initialises `q_des = qpos` (62-63)**. Chassis/torso JointState on `/hdas/feedback_chassis`, `/hdas/feedback_torso` (130-138, 236-242). Setup waits until every arm's `timestamp > 0` (controller 129-136) — the only liveness check; there is no staleness check afterwards.
- UR: `rtde_r.getActualQ()` (`universal_robots.py:88-89`), `getActualTCPPose` (91-92, unused by controller).

### A.6 Cameras (SOURCE_CONFIRMED)

- **RealSense** (`interface/realsense.py`): `update_frames` 93-166 called in a loop by `_camera_thread` (base_hw 198). Per camera `wait_for_frames(timeout_ms=500)` (108-109); stores `color`, `depth`, `timestamp_us = color_frame.get_timestamp()` (131), formats. On timeout/error the camera is **omitted** from the new dict (138-146 `continue`), and the dict is replaced wholesale (149-150), so a logged entry can silently lack a camera. Compressed JPEG copy with same `timestamp_us` (153-166). Note: librealsense `frame.get_timestamp()` returns milliseconds in the device/global time domain (external API doc; NOT_VERIFIED here) although the key is named `_us` and commented "microseconds" (131). Time domain (`get_frame_timestamp_domain`) is not recorded.
- **ROS camera** (Galaxea) (`interface/ros_camera.py`): `rospy.Subscriber(topic, sensor_msgs/CompressedImage, _color_callback)` (62-69); optional depth `Image` (71-73). Callback decodes JPEG, resizes to 424x240 (controller 182), re-encodes JPEG (90-107). **`msg.header.stamp` is ignored**; no receive time stored; only latest frame kept. Topics (controller 165-180): `/hdas/camera_wrist_left/color/image_raw/compressed`, `/hdas/camera_wrist_right/color/image_raw/compressed`, `/hdas/camera_head/left_raw/image_raw_color/compressed`, `/hdas/camera_head/right_raw/image_raw_color/compressed`.
- JPEG utils `xtk/utils/image_utils.py:12-45` (depth min-max normalised to 8-bit before JPEG, 28-36 -> depth metric scale lost).

### A.7 DataLogger and stored format (SOURCE_CONFIRMED)

- Logging thread `base_hardware_teleop_controller.py:153-164` at `log_freq` (50 Hz default; ARX 93, Galaxea 79); polls the B button each iteration (157, 166-185).
- Entry assembly `_log_data` 105-119: `{"timestamp": time.time() - self._start_time}` (110; `_start_time` set in `run()` 281, i.e. **host wall clock relative to program start, not episode start**, and not monotonic), then robot dict (112), then `"image"` dict if camera enabled and non-empty (114-117).
- `DataLogger` (`xtk/common/data_logger.py`): in-memory list (`add_entry` 24-31 — docstring claims a timestamp is added automatically, but it is not), `save()` 33-50 -> `pickle.dump(list_of_dicts)` to `<log_dir>/teleop_log_<YYYYmmdd_HHMMSS at logger construction>_<count>.pkl` (41). No metadata/header, no schema version, no checksum, no config (scale factor, R_headset_world, URDF, kp/kd) stored.
- Keys, ARX (`arx_r5_teleop_controller.py:192-209`): `qpos[arm]` (actual, CAN), `qvel[arm]` (actual), `qpos_des[arm]` = **current Placo `state.q` slice read from the logging thread** (197-200), `gripper_target[arm][joint]`; `image[<camera name>]{color(JPEG bytes), depth, timestamp_us, color_format, depth_format}` (211-234; names via `camera_serial_to_name`, 229-232).
- Keys, Galaxea (`galaxea_r1_lite_teleop_controller.py:235-248`): `qpos`, `qvel` (latest JointState values), `qpos_des` = `controller.q_des` (last value assigned for sending), `gripper_qpos`, `gripper_qpos_des`, `chassis_velocity_cmd`; `image[<name>]{color, depth}` — **no per-frame timestamp**. The JointState `header.stamp` held in `controller.timestamp` (galaxea.py:64) is **not logged**; torso command not logged.
- **Not logged in any path**: raw XR controller/headset pose, grip/trigger values, button states, XR `timeStampNs`, the `active` (deadman) flag, IK success/failure, Placo target pose, calibration refs, controller state/errors.
- Episode lifecycle: B rising edge toggles start/stop (`base_hw` 171-178); stop -> `save()` + `reset()`; right-stick click discards (180-183). On Ctrl+C / thread death, `run()`'s `finally` (322-327) sets stop and joins; **no save** is called, so an in-progress episode is lost. `save()` exceptions are caught and printed only (data_logger.py:47-50) and `reset()` runs regardless (178).

### A.8 Offline analysis `scripts/misc/test_data_log_analysis.py` (SOURCE_CONFIRMED)

Structure/printing only: loads pickle (38-57), key-set consistency across entries (124-143), prints robot fields (`qpos`, `qvel`, `qpos_des`, `gripper_qpos`, `gripper_qpos_des`, `gripper_target`; 154), image field (193-230), timestamp duration/mean-dt (232-266), optional image display (268-338). No range checks, no monotonicity check, no command-vs-actual comparison, no camera-age check.

### A.9 Downstream dataset (external converter) (SOURCE_CONFIRMED in openpi@72a2f9bd)

`convert_dual_arm_data_to_lerobot.py`:
- One pkl = one LeRobot episode (97-141), `fps=50` hard-coded (61) — the logged `timestamp` is **not used**; frames are assumed uniformly spaced.
- `state` = `qpos[left] ++ qpos[right]` (14 dims, gripper at 6/13 normalised `1 - x/4.9`) (112-118).
- `actions` = `qpos_des[left] ++ gripper_target_left ++ qpos_des[right] ++ gripper_target_right` (120-129) -> **action label = logged `qpos_des` (Placo IK solution) + trigger-derived gripper target**.
- Images by **serial number keys** `image["215222077461"]` etc. (132-134). Since XRoboToolkit commit `abc0677` (2025-08-19, "Refactor camera logging to use abstract method") the ARX logger keys images by camera **name** (`arx_r5_teleop_controller.py:227-232`), so the linked converter is not key-compatible with the pinned logger (it would need `"base"`, `"left_wrist"`, `"right_wrist"`). SOURCE_CONFIRMED by reading both; runtime KeyError NOT_VERIFIED by execution.
- No filtering of inactive/idle frames, no validation, `task` prompt hard-coded (106).
- No training code for XRoboToolkit itself exists in the teleop repo.

### A.10 Questions

**Q1 Commanded vs actual both recorded?** Partially. ARX: actual `qpos/qvel` and `qpos_des` both logged (`arx_r5_teleop_controller.py:195-200`) but `qpos_des` is the shared Placo `state.q` sampled asynchronously by the logging thread; the IK thread overwrites that same array with actual positions (`base_hw:129`, `base:185`) before solving, and `_send_command` only transmits when `active` (182-184). So the logged `qpos_des` is not guaranteed to equal the value transmitted (could be the pre-solve actual copy, or an IK solution computed while inactive and never sent). Galaxea: `qpos_des = controller.q_des` (240) is the last value placed in the outgoing message, which is closer to "commanded", though it is logged independently of the actual publish time. UR/sim: nothing logged. SOURCE_CONFIRMED (code structure); magnitude of mismatch NOT_VERIFIED.

**Q2 Action label?** No training pipeline in the repo. The README-linked external converter defines `actions = qpos_des + gripper_target` (openpi `convert…py:122-129`). XR input itself is not logged.

**Q3 Camera/action/state alignment?** Latest-value sampling at 50 Hz by one thread; one host `time.time()` per entry (`base_hw:110`). No per-stream acquisition stamps except RealSense `timestamp_us` (device/global domain, `realsense.py:131`); ROS camera `header.stamp` and JointState `header.stamp` are discarded/not logged (`ros_camera.py:90-107`; `galaxea.py:64` kept in memory only). No synchronizer, no staleness detection, no duplicate-frame detection. Converter ignores even the entry timestamp (fixed fps=50).

**Q4 Tracking loss / pause / reset / reconnect in logs?** Not represented. Deadman (`grip>0.9`, `base:189-190`) state not logged; XR disconnect leaves stale values in the binding (`py_bindings.cpp:100-108`); RealSense timeouts only printed (`realsense.py:138-146`) and the camera key disappears; Galaxea feedback staleness unchecked. Logging continues through pauses (idle frames recorded). No reconnect logic anywhere.

**Q5 Robot rejection/delay recorded?** No. ARX `set_joint_positions` returns nothing checked (`arx_r5.py:74-75`); rospy publish has no ack; UR `servoJ` result ignored (`universal_robots.py:64-71`); IK failure only printed (`base:226-227`). No latency fields.

**Q6 Episode start/stop/success decided by whom?** Operator only, via headset controller buttons: B toggles start/stop+save, right axis click discards (`base_hw:166-185`; README.md:125-131, 209-218). No success label; converter hard-codes the task string (openpi 106).

**Q7 Target vs actual comparable?** Joint space only, same units for ARX/Galaxea (`qpos` vs `qpos_des`), with the Q1 caveats. Cartesian target (Placo task pose) and XR source pose are not logged, so XR-intent vs executed cannot be compared.

**Q8 Enough raw info to re-verify?** No. Missing: raw XR stream and its timestamps, active flag, calibration/scale/`R_headset_world`, per-stream acquisition time (Galaxea), ROS header stamps, config. Images are re-encoded JPEG (ROS path decodes+resizes+re-encodes), depth normalised per-frame to 8-bit (`image_utils.py:28-36`).

**Q9 Any validation?** Only `test_data_log_analysis.py` structural printing (A.8) and the wait-for-first-message at setup (`galaxea_r1_lite_teleop_controller.py:129-159`). `quat_diff_as_angle_axis` prints a warning on invalid quaternion but proceeds (`geometry.py:67-68`).

**Q10 Which real component has limited write authority into the dataset?** (factual data-flow only)
- Galaxea R1 Lite path is a **ROS 1** node (`rospy.init_node("galaxea_r1_lite_teleop_controller", anonymous=True)`, controller 114). Its logged `qpos/qvel/gripper_qpos` come from whatever is published on `/hdas/feedback_arm_{left,right}` (JointState), and all logged images from whatever is published on the four `/hdas/camera_*/.../compressed` topics. Any ROS 1 node registered with the same master that publishes on those topics feeds the logger; the first JointState also seeds `q_des` (`galaxea.py:62-63`) and every JointState is fed into IK (`controller:190-193`). ROS 1 master/topic registration is unauthenticated by design (general ROS 1 property; deployment `ROS_MASTER_URI` not in repo — NOT_VERIFIED).
- ARX path: state comes from the CAN bus via `arx_r5_python` (in-process); cameras via USB RealSense in-process — no ROS topic boundary.
- XR input for all paths: the PC Service / PXREA SDK (external, NOT_VERIFIED transport).
- The pickle file itself is unauthenticated and loaded with `pickle.load` by the analysis script (49-50) and converter (108-109).

---

# 5. Survey of public ROS 2 / XR demonstration recorders


Paths relative to each repo root (shallow clones in a local scratch directory, not committed). SHA = `git rev-parse HEAD` of shallow clone; date = last commit date (committer).

## 1. OmMandhane/Phone2Act
- Remote: https://github.com/OmMandhane/Phone2Act.git  SHA 7a75b07382c477c4be755315e1e35977b1d75d1b  (2026-05-05). arXiv 2605.01948.
- XR: Android phone ARCore 6-DoF pose (APK). Phone -> rosbridge_server websocket (README.md L136-139, L176-177) publishes `Phone2Act/ar_pose` (PoseStamped) + `Phone2Act/volume` (planner L121-126). NOTE: rosbridge websocket = any network client can publish arbitrary ROS topics.
- ROS 2 (rclpy, ament_python).
- Dataset: LeRobot v2.0-style layout written directly (parquet + mp4 + meta/info.json, episodes.jsonl, tasks.jsonl) — `src/phone2act_core/phone2act_core/phone2act_universal_recorder.py` L240-279, L285-306.
- Recorder architecture: SEPARATE ROS 2 node `universal_recorder` subscribing to `/joint_states` (param `joint_topic`, L91,L131), `/phone2act/robot_feedback` (L132), `/phone2act/target_pose` (L133), `/phone2act/gripper_cmd` (L134). Cameras read in-process via cv2.VideoCapture (L45-73, L125-126), not ROS topics. => any node allowed to publish those 4 topics shapes the dataset.
- Action: `target_pose - robot_feedback` delta EE (xyz + wrapped rpy) + latest gripper cmd (L202-217). I.e. teleop target (planner output) minus measured pose.
- Observation state: `/joint_states.position` + robot_feedback EE pose + "simulated_gripper_state" = previous gripper command (L216, L233) (not measured).
- Sync: latest-value cache sampled by timer at fps=20 (L137, L167-194). No header stamps used/kept; message stamps discarded. Only staleness check: drop frame if target cmd older than 0.5 s wall-clock (L185-187) — (and only when target exists). Joint/feedback staleness NOT checked.
- Timestamps stored: `timestamp` = ROS clock now minus episode start (L218); no source stamps.
- Episode boundary: interactive `input()` ENTER to start, Ctrl-C to stop, y/n save prompt (L394-420). One episode per process.
- Validation: prints loop rate only (L172-173); no dt/frame-drop check; `annotation.human.validity` hardcoded 1 (L228). No hashes/integrity metadata.
- SROS2/access control: none documented (only README "Security" hit is Android Unknown Sources).
- Sim/mock: none; `template_hardware_bridge.py` is a stub for porting. Recorder needs 2 physical USB cams.

## 2. aadhithya14/Open-Teach
- Remote: https://github.com/aadhithya14/Open-Teach.git  SHA 32a7d44b33953066ff27312a7b2b4c294f4f52c5 (2026-01-24).
- XR: Meta Quest 3 Unity apps (VR/…); hand keypoints streamed over ZMQ (README L11).
- ROS: ROS 1 only where used (`import rospy` in openteach/ros_links/{ros_link,allegro_control,franka_allegro_control,kinova_allegro_control}.py L1-3; utils/publisher.py, subscriber.py). Transport between components is ZMQ, not ROS. No ROS 2.
- Dataset: raw per-stream HDF5 (`.h5` with gzip) + pickle `.metadata` per camera (openteach/components/recorders/robot_state.py L29,L70-81; image.py L41,L85-96); not LeRobot. Policy learning docs separate.
- Recorder architecture: separate recorder processes (data_collect.py, hydra) each polling a robot wrapper's `recorder_functions` at robot data_frequency (robot_state.py L20-24, L44-57). For Allegro, values come from rospy subscribers caching latest msg of joint state AND commanded joint state topics (franka_allegro_control.py L55-68); Franka arm uses deoxys controller reads with `time.time()` stamps (L158-165). Images via ZMQCameraSubscriber (image.py L26, L70).
- Action: not defined at record time; recorded streams include `commanded_joint_state` / `commanded_cartesian_state` (robot/bimanual.py L21) = controller input; action derived offline.
- Sync: none at record time — independent streams, each with own timestamps (ROS header stamps for Allegro ros_link.py L35/L47; wall-clock time.time() for Franka); alignment offline.
- Episode boundary: one process run per `demo_num`, Ctrl-C (KeyboardInterrupt) ends (robot_state.py L58-60; configs/collect_data.yaml `demo_num`).
- Validation: only records datapoints/duration/frequency metadata (recorders/recorder.py L4-12). No drop checks, no hashes.
- SROS2/access control: none (ROS 1; ZMQ unauthenticated).
- Sim: yes (allegro_sim / libero_sim, docs/teleop_data_collect.md L73) but sim path does not use ROS.

## 3. Quest2ROS/quest2ros
- Remote: https://github.com/Quest2ROS/quest2ros.git  SHA 7f03e9440af0efc3d105a9c6d991fd558935eee8 (2023-12-13).
- XR: Meta Quest app (closed-source APK) -> Unity ROS-TCP-Endpoint (README setup steps 2,6).
- ROS 1 (`import rospy`, scripts/ros2quest.py L2; catkin).
- Dataset: NONE. Only a demo node + msgs (OVR2ROSInputs, OVR2ROSHapticFeedback). No recorder. Not a testbed for dataset integrity by itself.
- Note: ROS-TCP-Endpoint accepts any TCP client that can reach tcp_port 10000 and lets it publish to ROS topics.

## 4. Taokt/Quest2ROS2
- Remote: https://github.com/Taokt/Quest2ROS2.git  SHA 07aaf65149c9e29103f1fc61deb466cef8a55cef (2026-03-06). HRI 2026 (arXiv 2601.18289).
- XR: Meta Quest 2/3 controllers via Quest2ROS app + `ros_tcp_communication` (fork of ROS-TCP-Endpoint) (README L4, L27-37).
- ROS 2 Humble (rclpy).
- Dataset: NONE (no rosbag/HDF5/LeRobot code; grep for record/dataset/hdf5/lerobot returns nothing). Teleop only: q2r2_bringup/robot_arm_controller_base.py subscribes quest pose/inputs (L112-123), publishes target PoseStamped (L127) + gripper action client (L130).
- Mock: `SimulationInput.py` publishes fake Quest controller data at 30 Hz on `/q2r_{side}_hand_pose` etc. (L52-62) — useful as a hardware-free XR source, but no recorder.
- SROS2: none.

## 5. Tony1984creator/quest-piper-vla-button-press
- Remote: https://github.com/Tony1984creator/quest-piper-vla-button-press.git  SHA 93c761711d4ab8138846dc84836106868df45a09 (2026-09-28).
- Portfolio repo. README describes Quest VR -> ROS 2 -> IK -> guarded command owner -> private Piper transport, and a 40-episode LeRobot "Quest VR dataset" (README "Completed evidence" table). BUT README "Public boundary": excludes "ROS/CAN/SDK control code"; "no public code can command a robot". No ROS node / recorder in tree (git ls-files: only stdlib contracts + tests).
- XR: Quest (claimed, code private). ROS 2: claimed, code private. Dataset: LeRobot (claimed; raw data not public).
- Public integrity-relevant code: `projects/lerobot_data_contract/core/episode_integrity.py` L10-57 — offline validator over (episode_index, frame_index, timestamp_s, global_index): checks fps>0, timestamp delta vs 1/fps within tolerance -> "timestamp_alignment_gap" (L37-49). No hash/provenance. `quest_piper_safety/core/safety_gate.py` = staleness gate for command candidates.
- Recorder architecture / action / sync: NOT inspectable (private). Not usable as testbed; useful only as prior-art example of an offline timestamp-contract check.

## 6. YAnG-0419/Convert_data ("convest")
- Remote: https://github.com/YAnG-0419/Convert_data.git  SHA 17bef2a83d1cbb609dcc1c00551845b03b424ad1 (2026-09-24).
- XR: NONE (teleoperator: GELLO leader arms + Wuji hands; schemas/gello_contract.yaml L3; grep quest/pico/xr/vr/glove -> no hits).
- ROS 2: consumes ROS 2 sqlite3 rosbag2 offline, reads SQLite read-only without installing ROS (README L3-5). The recorder itself (rosbag2 + `collection_state.json`) is not in the repo.
- Dataset: rosbag2 -> LeRobot v2.1 (Pi05) / ACT HDF5 / DP3 Zarr (src/convest/formats/{lerobot_v21,act_hdf5,dp3_zarr}.py).
- Trust boundary: upstream recording is rosbag2 subscribing to topics listed in gello_contract.yaml L7-47 (e.g. `/teleop/validated_arm_commands`, `/left/franka/joint_states`, `/cam0/color/image_raw`) => any permitted publisher enters the bag.
- Action: `validated_arm_action` = `/teleop/validated_arm_commands` (JointState, commanded, after a validator) + `/teleop/wuji/*/command` (gello_contract.yaml L11-26); state = measured `/left|right/franka/joint_states`, `/teleop/wuji/*/joint_states` (recipes/act.py L44-46, L89-93).
- Sync: offline causal/latest-before on a fixed fps grid using SOURCE HEADER stamps (sources/gello_rosbag2.py L146-151: zero header -> error, "receive-time fallback is disabled"); per-stream max_age (align.py L28-47); ACT nearest-neighbour with image/hand <=50 ms, arm <=20 ms (README ACT section). Receive times retained for trimming (gello_rosbag2.py L159-178, L189).
- Engagement gating: action frames invalid unless ArmCommandStatus active/ok and command newer than engagement transition (align.py L52-66).
- Episode boundary: per-bag + `collection_state.json` validation_report / milestones (recipes/act.py L115-125; README Pi05 section); gaps split into segments.
- Validation: `verify` checks dims, dtype, NaN/inf, all-zero actions, black frames, continuous timestamps, >1 rad jumps (README ACT section); src/convest/verify.py.
- Integrity metadata: config fingerprint sha256 (config.py L42), source bag SHA-256 (dp3_pipeline.py L31-36, L166-171), output file sha256 on resume (pipeline.py L63-80). Strongest provenance of all surveyed — but only post-hoc; nothing authenticates the publishers into the bag.
- SROS2: none. Runnable without hardware: yes on bags (sample episodes metadata in datasets/, but bags themselves not in repo — only metadata/trim_report JSON).

## 7. Interbotix/aloha (ROS 2 port of ALOHA)
- Remote: https://github.com/Interbotix/aloha.git  SHA 4fa6b2c4428f5334441a7bee5ab2b2e8071cff93 (2024-12-05). (also in ../repos/Interbotix__aloha)
- XR: NONE (leader-arm puppeteering).
- ROS 2 (package.xml L18 rclpy, L29 ament_python).
- Dataset: ACT HDF5 (`/observations/{qpos,qvel,effort,images/*}`, `/action`) scripts/record_episodes.py L225-320; attrs only `sim`, `compress` (L298-299).
- Architecture: recorder is IN the teleop loop process (record_episodes.py L184-195: get_action -> env.step -> append). But all inputs arrive via ROS 2 topics cached latest-value: follower `/follower_{side}/joint_states`, `/follower_{side}/commands/joint_group`, `/commands/joint_single` (aloha/robot_utils.py L118-135); cameras via `create_subscription(Image, topic, …)` (robot_utils.py L51); leader joints read from interbotix core `leader_bot.core.joint_states` (real_env.py L271-275), itself a /joint_states subscription. => topic publishers still shape the dataset.
- Action: LEADER joint positions (+ normalized gripper) (real_env.py L265-275). Obs: follower joint_states (real_env.py L138-165).
- Sync: latest-value at DT=1/FPS loop with sleep (record_episodes.py L185-195); header stamps of images captured (robot_utils.py L62-63) but NOT written to HDF5; no timestamps stored at all. Bug: diagnostic stamp uses `sec + sec*1e-9` (robot_utils.py L68).
- Validation: dt diagnosis; re-collect if mean freq < 30 Hz (record_episodes.py L215-217, L379-392). No per-frame drop/staleness check. No integrity metadata.
- Episode boundary: fixed `max_timesteps`, start via "opening ceremony" gripper-close gesture (L166-172); auto_record.sh loop.
- SROS2: none. Sim/mock: no (real hardware only in this repo).

## 8. astroyat/lerobot-ros
- Remote: https://github.com/astroyat/lerobot-ros.git  SHA 9e504ba0be4e4e222c0ae3dc51a47b0d3e94103d (2025-10-23).
- Repo contains only README, nav2 yaml, STL, media. ROS 2 Humble/Jazzy bridge for LeKiwi base (/cmd_vel, /odom, /scan); arm teleop "in development"; actual code lives in a lerobot fork branch (`astroyat/lerobot` ros2-latest, README install step 7) — not in this repo.
- XR: none. Dataset: none in repo. Recorder: n/a. Not a candidate.

## 9. eliasbitsch/MetaMove
- Remote: https://github.com/eliasbitsch/MetaMove.git  SHA 57d7d42068e127c33335817fe292b9ecf61b6fd0 (2026-09-27).
- XR: Meta Quest 3 Unity AR, hand tracking -> ros-tcp-connector PoseStamped/TwistStamped (README architecture, L22-50).
- ROS 2 Jazzy + MoveIt Servo; Python EGM bridge via rosbridge to ABB GoFa (README L20-56).
- Dataset: NO learning dataset. Only generic `ros2 bag record -a -o bags/session_…` in ros2/docker/README.md L82 (manual, all topics) and waypoint YAML teach files (`recorded_utc`, dpp_teach.py L99). No converter, no action/obs schema.
- Recorder: rosbag2 `-a` = subscriber to every topic (maximal trust surface). No sync/validation.
- Sim/mock: yes — egm-mock (bridge/egm-mock/egm_mock.py), fake_joint_state_publisher.py, metamove_sim_*.launch.py, ros2/test/e2e/controller_sim.py. Good XR+ROS 2 sim harness but no dataset writer.
- SROS2: none found.

## 10. wuphilipp/gello_software
- Remote: https://github.com/wuphilipp/gello_software.git  SHA 204f53a64bef89471a1e483b0f874f755fbd2d3a (2026-09-14). (also ../repos/wuphilipp__gello_software)
- XR: optional Quest agent via `oculus_reader` (ADB) — gello/agents/quest_agent.py L7, L21-27; selected with `--agent quest` (experiments/run_env.py L76-85, L156-158). This path is non-ROS (ZMQ robot/camera nodes, gello/zmq_core/).
- ROS: ROS 2 subtree `ros2/` (franka_gello_state_publisher, franka_fr3_arm_controllers, gripper manager) publishes GELLO joint states to Franka controllers — no recorder in ros2/ (no bag/record/dataset files).
- Dataset: non-ROS path only: one pickle per frame `<isoformat>.pkl` with obs + `control` (gello/data_utils/format_obs.py L9-22), keyboard start/stop (gello/utils/control_utils.py L72-123, KBReset). Offline converter demo_to_gdict.py. Not LeRobot, not ROS.
- Action: leader/agent joint command `agent.act(obs)` stored as obs["control"] (run_env.py L222; format_obs.py L15). Obs: follower joints from robot node.
- Sync: in-process loop, latest camera frame via ZMQ; per-frame wall-clock filename timestamp only.
- Validation: startup leader-follower diff check >0.5/0.8 rad (run_env.py L223-230). No integrity metadata.
- Sim: yes (MuJoCo sim_robot, configs/*_sim.yaml). XR + dataset exist but NOT on ROS 2; ROS 2 path has no dataset => not a single implementation.

## 11. iblnkn/rosetta
- Remote: https://github.com/iblnkn/rosetta.git  SHA 294136dc435a040d608d9efd773d70ae0b421d00 (2026-09-22). Apache-2.0; CI + ~50 unit tests.
- XR: NONE (grep quest/xr/vr/pico -> no hits). Teleop source in contracts = leader arm topic (contracts/so_101.yaml L39-47 `/leader_arm/joint_states`).
- ROS 2 (rclpy lifecycle node, rosbag2_py SequentialWriter).
- Dataset: rosbag2 (MCAP/sqlite) per episode -> `rosetta_port` -> LeRobot dataset via lerobot_rosetta (README step list; rosetta/robots/ros2/offline/port.py, bag_frames.py).
- Recorder architecture: SEPARATE ROS 2 node `episode_recorder` (episode_recorder_node.py L199) subscribing to every contract topic (L441-483), optional `record_all` = like `ros2 bag record -a` (L263-266), plus auto-discovered topics (L534+). QoS adapted to whatever publishers exist (L139-162). => the canonical "any permitted publisher shapes dataset" case; nothing checks publisher identity/GID.
- Bag timestamp = recorder receive time (`get_clock().now()`), header.stamp kept inside serialized msg (L598-612).
- Action: contract-defined; README example = commanded topic `/forward_position_controller/commands` aligned on `receive` timeline (README contract block); so_101 contract = leader `/leader_arm/joint_states` on `header` timeline. Obs: `/joint_states` follower.
- Sync (offline at port time): per-key resample policy hold / asof(tol_ms) / drop on selectable `header` or `receive` timeline (rosetta/frames/resample.py L55-68, L93-126; rosetta/robots/ros2/timelines.py L34-65). `hold` = no freshness gate (resample.py L126). Missing topic -> warning + zero-fill (bag_frames.py L102, L125).
- Episode boundary: ROS 2 action `/record_episode` (goal with prompt, max_duration_s) or `~/start_recording` / `~/cancel_recording` services, keyboard node (L354-392, L701-709; launch/episode_keyboard_launch.py). NOTE: these services/actions are themselves open ROS interfaces.
- Integrity metadata: bag metadata.yaml custom_data: `rosetta.contract_yaml` (full contract text), `lerobot.operator_prompt`, `rosetta.goal_id` (bag_metadata.py L34-42); per-topic msg counts (recorder L305, L614). Param text says "text + hash" (L274) but no digest code found under rosetta/ (grep sha/md5/digest: none). No signatures.
- Validation: contract schema validation; QoS/type conflict checks (L511-529); no fps/dt/drop audit.
- SROS2: not documented. Sim: generic (turtlebot3 contract; clock-reset handling for sim restart resample.py L111) — runnable against any sim publishing the topics.

## 12. ngres/leros2
- Remote: https://github.com/ngres/leros2.git  SHA c8ca08b550a34db1a4e87edaad468f4ad829524a (2026-08-14).
- XR: NONE in repo (generic ROS 2 teleop topics; example `lerobot_teleoperator_pose` consumes a pose topic — any XR publisher could feed it, but none shipped).
- ROS 2; LeRobot Robot/Teleoperator plugins (packages/lerobot_robot_ros2, lerobot_teleoperator_ros2).
- Dataset: two paths — (a) `lerobot-record` in-process via plugin subscriptions; (b) RECOMMENDED: plain rosbag2 (MCAP) recording, then `leros2-convert` -> LeRobot (README "Recording" section L96-103; src/leros2/scripts/convert.py).
- Recorder architecture: rosbag2 (external subscriber) — trust boundary = all publishers on configured topics.
- Action: teleop-config topics, README example = commanded `/cartesian_controller/target_pose` + `/gripper_controller/commands` (README L68-76); obs = `/joint_states`, `/cartesian_controller/current_pose`, images.
- Sync (convert.py L330-398): latest-value per topic (`_topic_data[topic] = msg`, L334); frame emitted when bag log_time advances >= 1/fps (L368-372) or on each `clock_topic` msg. Uses MCAP `log_time` (receive time) (L255-273); header stamps ignored; no staleness bound on any stream once all topics seen once (L360-365).
- Episode boundary: IN-BAND topics — `task_topic` String starts a new episode (L337-345); `event_topic` "exit_early"/"delete_episode"/"rerecord_episode" saves/deletes episodes (L347-358). => any publisher on those topics can split or delete episodes at conversion time.
- Validation: warns on missing topics via bag message counts (L213-253); truncated MCAP -> keep partial (L274-288). No dt/drop checks, no integrity metadata.
- SROS2: none. Hardware-free: yes if you have bags / sim publishing the topics (tests/image_node.py).

## 13. roahmlab/tidybot_ros  *** PRIME CANDIDATE ***
- Remote: https://github.com/roahmlab/tidybot_ros.git  SHA e32cb459514abe556a9a9a954d9131d0bb50c210 (2026-03-27). U. Michigan ROAHM Lab; ROS 2 port of TidyBot++.
- XR: WebXR smartphone/tablet teleop (README L64, L71, L196-206). Phone page (src/tidybot_policy/config/index.html, webxr-button.js) -> Flask-SocketIO server on 0.0.0.0:5000, `cors_allowed_origins="*"`, no auth, plain HTTP in code (tidybot_policy/phone_teleop_server.py L29-39, L55-61, L79-82) -> ROS 2 `/teleop_commands` (TeleopMsg) + `/teleop_state` (L118-121) -> phone_policy publishes `/tidybot/arm/target_pose` etc. (phone_policy.py L35-51). Socket events `save_episode` / `discard_episode` (L64-72) drive finalize.
- ROS 2 (rclcpp C++ recorder, rclpy policy nodes), Humble; Docker; cyclonedds/fastdds xml provided.
- Dataset: two rosbag2 (sqlite3) per episode (actions + obs) + MP4 per camera (synchronized_recorder.cpp L114-124, L390-411) -> `rosbag_to_hdf5` (TidyBot++ diffusion-policy HDF5, `/data/<bag>/actions [N,10]`, `obs/arm_pos`, `arm_quat`, `base_pose`… rosbag_to_hdf5.cpp L431-460) or `rosbag_to_parquet` / RLDS builder (src/external/rlds_dataset_builder).
- Recorder architecture: SEPARATE ROS 2 node `synchronized_recorder` subscribing `/joint_states` (L209), `/tidybot/camera_{base,wrist,ext}/color/raw` via image_transport (L228, L244, L260), action topics `/tidybot/base/target_pose`, `/tidybot/arm/target_pose`, `/tidybot/gripper/commands` (L275-291). Obs poses from TF lookups world->base, arm_base_link->bracelet_link at Time(0) (L566, L583). Start/stop/finalize via open services `/start_recording`, `/stop_recording`, `/finalize_recording` (L184-192), called by state_controller (state_controller.py L49-57).
- Action: teleop target (commanded) topics = phone_policy outputs (L275-291); obs = measured TF poses + finger_joint from /joint_states (L213-221).
- Sync / sampling: wall timer at fps (default 10 Hz, L159, L196); a write is TRIGGERED by each arrival of an action message (`pending_writes_++`, L278/L284/L290; consumed L538-550) — so action-topic publishers control sample count/rate. All streams latest-value; no staleness/age check on images or joint_states (only "not yet received" checks L651-672). Header stamps of obs poses OVERWRITTEN with recorder now (L568, L585); bag write time = recorder clock now (L800). Missing initial actions are seeded from observation (L614-640, L675-678).
- Timestamps stored: bag receive times only; HDF5 has none — converter pairs obs/action by index and only checks equal counts (rosbag_to_hdf5.cpp L172-177).
- Validation: time-jump reset of TF (L521-531); sample counter log; no fps/dt/drop checks, no integrity metadata/hashes.
- SROS2: none (README network config only mentions ROS_DOMAIN_ID and port 5000, README L256-257).
- Hardware-free: YES — `sim_mode:=gazebo` or `isaac` for phone teleop and recording (README L203-206, L221); Isaac Sim docker provided. A phone/browser is still needed as XR source (or scripted SocketIO client).

## 14. saiyuhang123/QuestArmTeleop (fork of agilexrobotics/QuestArmTeleop)
- Remote: https://github.com/saiyuhang123/QuestArmTeleop.git  SHA b75965b2943dc98c2aaadaf5d14c58b96a9a4096 (2026-09-17).
- XR: Meta Quest 2/3/3S via oculus_reader (ADB APK, src/oculus_reader/APK/) and a WebXR node (aiohttp + ssl, scripts/webxr_teleop_node.py L21-36; launch/*_webxr.launch.py).
- ROS 2 Humble (colcon; README).
- Dataset: NONE (grep rosbag/record/lerobot/hdf5/dataset over .py/.md/launch: no hits).
- Hardware-free: yes for teleop chain (`canopen_arm_fake_ik.launch.py`, `teleop_single_canopen_arm_fake_webxr.launch.py`, test/fake_canopen_arm_ik_e2e.sh). Useful as XR->ROS 2 source with fake arm; would need an external recorder (e.g. rosetta / rosbag2) to become a dataset testbed.
- SROS2: none.

## 15. unitreerobotics/xr_teleoperate
- Remote: https://github.com/unitreerobotics/xr_teleoperate.git  SHA 817fb00c63cde15e5f24a0f8fa08e1e33ed89d3b (2026-09-07). (also ../repos/unitreerobotics__xr_teleoperate)
- XR: Apple Vision Pro / PICO 4 Ultra / Meta Quest 3 via televuer (WebXR over HTTPS/WebRTC) (README L51, L150-154).
- ROS: NOT ROS. Uses unitree_sdk2py DDS channels directly (`rt/lowstate`, `rt/lowcmd`, `rt/arm_sdk`; teleop/robot_control/robot_arm.py L6, L19-21, L102). DDS (CycloneDDS) wire is ROS 2-compatible (unitree_ros2 exists) but no rclpy/ROS graph here.
- Dataset: custom per-episode `data.json` + images (teleop/utils/episode_writer.py L90-118, L129-144, L193-196); converted to LeRobot by separate unitree_IL_lerobot repo (not in tree).
- Architecture: IN-PROCESS: main loop computes IK and records same-iteration values (teleop_hand_and_arm.py L362-370, L429-431, L466-520); writer thread consumes a queue (episode_writer.py L55-58, L146-160). Obs state from DDS subscriber `rt/lowstate` (any DDS participant on the domain can publish it).
- Action: IK solution `sol_q` (commanded joint target) (L367, L431); obs = current arm q from lowstate (L362, L430). Hand/ee action = retargeted hand cmd.
- Sync: latest-value per loop; images from teleimager ZMQ, None -> warning and omitted (L440-465). Timestamps: none stored per item (only `idx`); time.time() only logged (episode_writer.py L201-203). info has fps nominal (L71).
- Episode boundary: XR controller/keyboard state machine with `--record` (L269, L306-312).
- Validation / integrity: none. SROS2: n/a.
- Sim: yes `--sim` Isaac (L87, L248-253, sim_state_topic.py).

## 16. ycheng517/lerobot-ros
- Remote: https://github.com/ycheng517/lerobot-ros.git  SHA dabe6c6c7637c2f139e1c9964864a64921893ba1 (2026-08-12).
- XR: NONE (gamepad 6-DoF + keyboard teleoperators, lerobot_teleoperator_devices/).
- ROS 2 Jazzy; LeRobot Robot plugin wrapping ros2_control / MoveIt Servo (README L1-17).
- Dataset: via stock `lerobot-record` (LeRobot dataset) — recorder is LeRobot's in-process loop; robot plugin subscribes `joint_states` latest-value (ros_interface.py L102-107) and reads cameras via LeRobot camera drivers (not ROS) (robot.py L96-117).
- Action: teleoperator output as sent (`send_action` returns clipped action actually sent, robot.py L119-125) = commanded. Obs: /joint_states.
- Sync: latest-value; no stamps kept (LeRobot frame timestamp = loop time). Camera failure -> None + log (robot.py L110-113).
- Sim: yes (Gazebo simulated SO-101 quickstart, README L30-60). SROS2: none.

## 17. OpenTeleVision/TeleVision (../repos)
- Remote: https://github.com/OpenTeleVision/TeleVision  SHA e6e25afdb16c1b326b5bf37bd0ae79919bf79f26 (2024-09-26).
- XR: Apple Vision Pro / Quest via Vuer WebXR (teleop/TeleVision.py). ROS: none (no rclpy/rospy in any .py). Dataset: HDF5 consumed by scripts/post_process.py, replay_demo.py L160, deploy_sim.py L94; the recording script itself is not in the tree. Not a ROS testbed.

## Summary (stars/forks via `gh api`, 2026-09-30)
| repo | stars | XR | ROS | dataset | recorder = topic subscriber? | action | sync |
|---|---|---|---|---|---|---|---|
| roahmlab/tidybot_ros | 33 | WebXR phone | 2 | rosbag2->HDF5/parquet/RLDS | yes (separate node) | teleop target topics | latest-value, write triggered by action msgs, stamps overwritten |
| OmMandhane/Phone2Act | 4 | ARCore phone via rosbridge | 2 | LeRobot v2.0 direct | yes (separate node; cams in-process) | target - measured EE delta | latest-value timer 20 Hz, 0.5 s cmd staleness |
| iblnkn/rosetta | 97 | none | 2 | rosbag2->LeRobot | yes (+record_all) | contract (leader/cmd topic) | offline hold/asof/drop, header|receive |
| ngres/leros2 | 9 | none | 2 | rosbag2(MCAP)->LeRobot | yes (rosbag2) | commanded topics | latest-value on log_time grid; in-band episode topics |
| YAnG-0419/Convert_data | 0 | none (GELLO) | 2 (bags) | rosbag2->LeRobot/ACT/DP3 | upstream rosbag2 | validated commands | header-stamp causal, max-age, sha256 provenance |
| Interbotix/aloha | 28 | none | 2 | ACT HDF5 | in-loop but topic-fed | leader joints | latest-value, no stamps saved |
| ycheng517/lerobot-ros | 216 | none | 2 | LeRobot (lerobot-record) | in-process LeRobot loop | sent command | latest-value |
| unitree xr_teleoperate | 1683 | AVP/PICO/Quest | none (unitree DDS) | JSON->LeRobot (ext) | in-process | IK sol_q | latest-value, no stamps |
| Open-Teach | 422 | Quest 3 | 1 (partly) + ZMQ | HDF5 per stream | separate procs | commanded (offline) | independent streams, stamps kept |
| gello_software | 550 | Quest (non-ROS path) | 2 (no recorder) | pickle/frame | in-process | agent command | latest-value |
| Taokt/Quest2ROS2 | 54 | Quest | 2 | none | – | – | – |
| saiyuhang123/QuestArmTeleop | 0 | Quest/WebXR | 2 | none | – | – | – |
| eliasbitsch/MetaMove | 0 | Quest 3 | 2 | generic `ros2 bag -a` only | yes | – | – |
| Quest2ROS/quest2ros | 43 | Quest | 1 | none | – | – | – |
| Tony1984creator/... | 0 | Quest (private) | 2 (private) | LeRobot (private) | n/a | n/a | offline ts check only |
| astroyat/lerobot-ros | 36 | none | 2 | none in repo | – | – | – |
| OpenTeleVision/TeleVision | – | AVP | none | HDF5 | n/a | n/a | n/a |

XR + ROS 2 + learning dataset in ONE public implementation: roahmlab/tidybot_ros (Gazebo/Isaac sim, strongest), OmMandhane/Phone2Act (hardware-only). Composable alternatives: QuestArmTeleop or Quest2ROS2 SimulationInput (XR->ROS 2, fake arm) + rosetta/leros2 (ROS 2 -> LeRobot).
