# Trust Boundaries

A boundary is listed only if it exists in the audited code or its documented deployment. For each one we
record who can write across it, what that writer is *entitled* to influence, and what it can actually
influence in the recorded dataset. A boundary is **integrity-relevant** only if the dataset influence can
exceed the entitled influence (e.g. change a recorded field without changing what the robot did).

Classification used: `NONE` (no separation — same process/authority), `UNAUTH` (separation exists but no
authentication, so any reachable party has full authority; already known/generic), `FULL_WRITE` (writer
holds the whole dataset; equals the published data-poisoning threat model), `LIMITED` (a real, narrower
authority exists).

## 1. Boundary table

| ID | Path | Boundary | Writer | Entitled influence | Dataset influence | Class | Evidence |
|---|---|---|---|---|---|---|---|
| TB1 | P1, P2 | XR client (headset or browser WebXR) → CloudXR runtime | the operator's XR client | XR poses / buttons | only through the commands they cause; the robot executes them and the recorder stores what was sent and measured | LIMITED, but **dataset influence = robot influence** | SOURCE_AUDIT §1 A1–A9, §3 WebXR recorder |
| TB1a | P1, P2 | CloudXR WSS proxy on all interfaces, port 48322, self-signed cert | whoever pairs a client | as TB1 | as TB1 | pairing/auth NOT_VERIFIED | IT `cloudxr/wss.py:660-666` |
| TB1b | P1, P2 | WebXR client "Load Recording…" replaces live input with a recorded JSON stream | the operator's client | as TB1 | as TB1 (server cannot tell replay from live: NOT_VERIFIED) | same as TB1 | IT `xrInputRecorder.ts:18-23, 534-553` |
| TB2 | P1 (leader-arm variant) | `so101_leader` plugin process → CloudXR tensor channel | local plugin process | leader joint stream | as TB1 | non-XR; auth NOT_VERIFIED | LR `common.py:471-493` |
| TB3 | P1, P2, P3 | retargeting / processor steps / IK / recorder | same Python process | — | everything | NONE | LR `xr_controller_processor.py:38` (global registry); Isaac Lab single Kit process |
| TB4 | P1 | dataset directory on disk before push | local user owning `cfg.dataset.root` | — | entire dataset | FULL_WRITE | LR `dataset_writer.py:258-265`, `lerobot_dataset.py:685-716` |
| TB5 | P1 | Hugging Face Hub repo | HF token holder | — | entire dataset (tag `v3.0` recreated on push) | FULL_WRITE | LR `lerobot_dataset.py:646-726` |
| TB6 | P2 | HDF5 tools (`merge_hdf5_datasets.py`, `mp4_to_hdf5.py`), Mimic generation | tool operator | — | whole files (by design) | FULL_WRITE | Isaac Lab audit §12 |
| TB7 | P4 | phone → Flask-SocketIO `0.0.0.0:5000`, CORS `*`, no auth; `save_episode`/`discard_episode` events | any host that can reach port 5000 | — | teleop commands (→ robot) and episode save/discard | UNAUTH | tidybot `phone_teleop_server.py:29-82` |
| TB8 | P4 | ROS 2 DDS graph (no SROS2 in repo or docs) | any participant in the domain | — | any topic, any service (start/stop/finalize) | UNAUTH | tidybot README network section; no security config found |
| TB8′ | P4 **if** SROS2 were deployed (not upstream-documented) | per-topic publish permissions | e.g. camera driver, joint-state publisher, TF broadcaster, teleop policy | its own topics | see §2 | LIMITED (hypothetical deployment) | DERIVED_HYPOTHESIS |
| TB9 | P3 | ROS 1 master (Galaxea) | any node on the master | — | recorded state `/hdas/feedback_arm_*` and camera topics | UNAUTH | XRoboToolkit `galaxea.py:17-64` |
| TB10 | IT MCAP | MCAP file → replay into retargeting (teleop_ros2 `mcap_replay_path`) | whoever supplies the file | raw tracker data | none in any audited dataset path (teleop_ros2 has no recorder; LeRobot does not use MCAP) | not on a dataset path | SOURCE_AUDIT §3 |

## 2. What a LIMITED writer can do (TB1 and the hypothetical TB8′)

**TB1 (XR input provider).** Every recorded action is derived from XR input and then *executed*; the
recorded observation is the robot's measured response. An XR-input writer therefore produces a demonstration
that is physically consistent with what the robot did. That is exactly an operator (or data provider)
choosing what to demonstrate — the threat model of the published poisoning work (SilentDrift "data
provider", 2609.26868 teleoperation demonstrations). It does not create a mismatch between recorded meaning
and executed behaviour. (DERIVED_HYPOTHESIS from the code paths above; not experimentally tested.)

**TB8′ (per-topic ROS 2 permissions, tidybot recorder).**

| Writer (topic permission) | Also consumed by the controller? | Can change a dataset field without changing robot behaviour? |
|---|---|---|
| teleop policy (`/tidybot/arm/target_pose`, `/tidybot/gripper/commands`, `/tidybot/base/target_pose`) | yes, same topics (`moveit_ee_pose_ik.cpp:48`, `base_server.py:41`) | no: label and command are the same message. It also gates sampling (`pending_writes_`), but the rate is fixed by the timer (`:517-550`) |
| camera driver (its image topic) | not by the controller | yes for its own images, which is its own data (a lying sensor). Stale frames are recorded as current (no age check) |
| `/joint_states` publisher | IK/controllers use joint state | recorded gripper state comes from it; the change also reaches control |
| any `/tf` broadcaster | recorded `arm_pose`/`base_pose` come from TF lookups (`:562-590`); the IK node takes robot state from `/joint_states` (`moveit_ee_pose_ik.cpp:70-72`) but also holds a TF buffer for planning-frame conversion (`:21-38`), so whether an injected transform also reaches control is NOT_VERIFIED; `/tf` is produced by `robot_state_publisher` from `/joint_states` (`launch_isaac_sim.launch.py:9, 69-71`) | **possibly yes**: ROS 2 permissions are per topic, not per TF frame, so a node allowed to broadcast *any* frame may be able to overwrite the recorded frames (DERIVED_HYPOTHESIS; not tested) |

The TF case is the only place found where a component with narrow, real authority might change a
recorded field beyond its entitlement. It is a ROS 2 authorization-granularity property (topic-level, not
frame-level), it does not involve XR data, and it would be visible to a joint-state-vs-TF consistency check
because `/joint_states` is unchanged. It also requires an SROS2 deployment that upstream does not document.

## 3. Summary

- **XR-specific boundaries (TB1, TB1a, TB1b):** the writer's dataset influence equals its robot influence.
  No XR-specific integrity boundary was found in P1/P2.
- **All other real separations are UNAUTH (TB7–TB9) or FULL_WRITE (TB4–TB6).** UNAUTH endpoints are a
  generic, already-reported class (prior internal: Quest2ROS2/rosbridge/HORUS; `../Deprecated/` reports).
  FULL_WRITE equals the published data-poisoning threat model (LIMITATION_MATRIX C1).
- **One LIMITED, ROS-specific candidate** (TF broadcaster under a hypothetical SROS2 deployment of the
  tidybot recorder) remains to be assessed in PHASE 3.
