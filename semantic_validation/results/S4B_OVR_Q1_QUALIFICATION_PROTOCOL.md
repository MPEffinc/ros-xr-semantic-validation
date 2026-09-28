# XRROS-S4B-OVRQ1-1.0.0 — prospective OpenVR setup qualification (blocker resolution) and design

This applies XRROS-S4-1.0.0 (SHA-256 `3a40337121f8d687dc68036ff2ffc85a1bc6eda275a700ba7d9e8119cd322969`) without changing it.

- **Root:** `runs/s4b_ovr_q1_20260928T184158Z/`.
- **Stack:** fake OpenVR API → the original, unedited `quest_teleop.py` (vendor commit `170dad582d624f536359a3192a7f829669c2b031`) → Jazzy MoveIt Servo (pose mode) → `ur5_arm_controller` → Gazebo.
- **Image:** `s4b-rosmonitoring-jazzy:20260922`, image ID `e45048ddcac4d189e9315b870fb471ac925f7c2faa2c8e3c888498be15e6ff26`.
- **Isolation:** trial-owned containers, network none, all capabilities dropped, `no-new-privileges`, UID 1000, ROS domain 181.

No Quest, SteamVR, ADB or ALVR is used, and no physical robot is involved.

## Registered blockers and how this setup addresses them

| Blocker (from CP1/CP2) | Resolution registered here |
| --- | --- |
| Readiness barrier | `inputs/ovr_probe.py` checks the full W1/W2 gate of section 7 and releases a single barrier only when every check passes: joint window, fixed OpenVR initial vector ±0.0001 rad, speed and drift, DDS matches on every edge, active controllers, successful Servo pose-mode reply, participant clocks, resource sampler, stop adapter, and for B2 an end-to-end official-path calibration. The original `QuestTeleop` timer object is held at poll index 0 until that barrier in every arm. |
| Observer equivalence | The CP2 B0/overlay pair differed by more than 5 ms. The suspected cause is CPU load from the vendor Gazebo launch: GUI under xvfb plus a 1000×1000, 30 Hz software-rendered camera. The harness launch `inputs/ovr_gazebo.launch.py` is the vendor launch with `-s` (server only) and a world copy with the unused camera sensor and Sensors system removed; the diffs are in `preflight/vendor_*_to_harness_*.diff`. This applies identically to every arm including B0. It is not part of the control path, and no vendor file is edited. A fresh B0/shim pair is required: ≤ 5 ms matched poll timing and ≤ 0.02 rad final joint difference. |
| Callback observation | Non-B0 arms use the CP2 observational Servo overlay: a `poseCallback` payload log with no gate change. `ovr_setup_audit.py` requires every Servo-input publication to join exactly one callback by header stamp and pose, and every callback to join exactly one publication. On the retained CP2 raw data it reproduces 450/450. |
| Trajectory/Gazebo evidence | The recorder logs `/servo_node/pose_target_cmds`, `/ur5_arm_controller/joint_trajectory`, `controller_state` and named `/joint_states` for 12 s after the barrier. |
| Safe stop/hold | `inputs/ovr_stop_adapter.py` is a common adapter for B1, B2-composed and B3. It uses the CP1-qualified stop form: `pause_servo` true, then five measured-position `JointTrajectory` holds. It stops on a defense rejection, on official health `unknown`/`error`, or when the 250 ms verdict heartbeat is missed. It resumes only on the defense's own first allowed grip decision after re-arm (D5 continuous semantics). It has no XR predicate. |
| Recovery reference | The original program's reference logic is **measured, not repaired**. On every grip engage it maps to the fixed absolute base target (0.4, 0, 0.3) plus scaled displacement. After a defense stop and re-arm, the new reference is therefore expected to move the arm back toward that target. The protocol forbids an adapter that transforms pose targets ("accepts only stop/hold or forwards allowed commands"). This behavior will be reported as missing application recovery-reference logic, not as a method gap. W4/W5 include a 0.2 s constant-pose new-reference window (polls 250–259) so the fresh-reference displacement is separable from later motion. |
| Official ROSMonitoring in the path | The generated **official** monitor (`ovr_full_guard`, from `inputs/ovr_rosmonitoring.yaml`) is built on Jazzy (`monitor_build/`). It filters the I_FULL envelope with the real TLOracle/Reelay property `inputs/ovr_tloracle_property.py`. Reelay 25.0.0 is installed from the cp312 wheel (SHA-256 `8cfee7a58814b04f126aec3e41c7d3c9a185702995d3f031033b91d853fa060c`, equal to the PyPI digest) into trial-local `deps/`; the image is unchanged. |

## Placements (identical policy `inputs/ovr_policy.py` over the shared `d5_rearm.Rearm`)

**OpenVR validity rule:** connected, `bPoseIsValid`, result = 200, grip; plus F250 freshness, future-time check, generation, and R_EXPLICIT/R_AUTO re-arm.

- **B1 (source gate):** after fake-API acquisition and before the original code uses the pose. The gate polls once; only an allowed acquisition is replayed into the original callback. It wraps the same timer object's callback, so period and phase are unchanged.
- **B3 (publish-point check):** inside the original callback, immediately before the target publish. The original logic, including reference capture, still runs.
- **B2 (official filter):** one lossless envelope per poll carrying the acquired sample's bound native state. The envelope is pose-bearing if the original published a pose, otherwise state-only; these are the protocol's state-only invalidation events. The official monitor filters `/s4b/ovr/envelope_mon`, and a stripper (transport hash check only) restores the original `PoseStamped` for Servo.
- **B2-native:** the filter alone. **B2-composed:** the filter plus the common stop adapter.

## Pre-freeze component evidence (no Gazebo, no Servo)

- `analysis/test_ovr_policy.py`: 8/8 pass. It covers the W0–W5 schedules and grip/API consistency; W2/W3 blocking of every grip sample; W4 R_EXPLICIT (re-arm on the rising edge at poll 250) and R_AUTO (poll 225); W5 disconnect plus generation 2; unbound and stale samples.
- Production component runs in `preflight/component_*`:
  - shim W1: 450 publications.
  - B1 W4: publications 50–149 and 250–499, blocked 150–239.
  - B3 W4: 40 blocked publishes, polls 200–239.
  - B1 W2 and B3 W3: zero publications.
  - B2 W5: blocked 150–239.
- **Finding: official monitor stalls on Jazzy.**
  - In the B2 W4 component run, the official monitor's callback arrivals stalled up to 447 ms. The oracle therefore judged 6 pose samples and 11 state samples STALE (over 250 ms old). The resulting latch kept the path blocked from poll 250 to 499.
  - Diagnostics isolate the cause to the officially generated `MultiThreadedExecutor()` on Jazzy rclpy:
    - a plain single-threaded subscriber on the same topic saw p99 0.32 ms;
    - disabling DDS shared memory did not help;
    - restricting to 4 CPUs made it worse;
    - `num_threads=2` processed only 131/626 and 284/626 events;
    - a one-line single-threaded-executor copy processed 626/626 events at 20.0 ms spacing, with a maximum gap of 20.9 ms.
  - The official generator hardcodes this executor, with no option (`generator.py:928`). The same generated code on Humble/Docker showed at most 10 ms envelope-to-oracle latency.
  - Therefore:
    - **B2 remains the unmodified official monitor**, and its Jazzy throughput behavior is part of the measured result.
    - A separately named **B2-ST** diagnostic (`inputs/ovr_full_guard_st.py`; diff in `preflight/official_to_b2st_monitor.diff`) is registered. It is **not ROSMonitoring**. Its only purpose is to separate an implementation/platform limitation from the method.
- **Disclosure of an operator error.** While tidying, I deleted the first diagnostic run directories with `rm -rf preflight/diag_*/`. This also removed the first executor-copy directory. The printed results of those first runs are:
  - default: p99 238 ms, maximum 375 ms;
  - UDP: maximum 454 ms;
  - 4 CPUs: maximum 3060 ms;
  - plain subscriber: p99 0.32 ms;
  - `num_threads=2`: 131 events;
  - single-threaded: maximum 20.8 ms.

  All diagnostics were rerun and retained in `preflight/diag_*`, with summaries in `preflight/diag_rerun_gap_report.txt`. The reruns reproduce the finding: single-threaded 626 events, maximum 20.9 ms; official default maximum 1175 ms. Two empty directories from a failed rerun attempt (a mount path created as root) are also retained.

## Q1 setup cells (`qualification_schedule.csv`; setup only, not a policy score)

| Case | Cells |
| --- | --- |
| W1 | B0, shim, B1, B2-native, B2-composed, B3, B2-ST-composed |
| W4 R_EXPLICIT | B0, B1, B2-composed, B3, B2-ST-composed |
| W2 | B2-composed |

There are 13 cells in total. At most two setup retries are allowed, and only when no barrier was reached. The gate is that every cell is MEASUREMENT_QUALIFIED (`analysis/ovr_setup_audit.py`) and the fresh B0/shim pair is PASS. After Q1, a scaled formal design (W0–W5, R_EXPLICIT/R_AUTO, and C-ID/C-MON OpenVR coverage) will be reported and frozen separately.
