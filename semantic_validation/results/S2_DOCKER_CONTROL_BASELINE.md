# S2 Docker_Teleop original-control baseline

## Scope and evidence boundary

S2 reran the pinned Docker_Teleop ROS-side control chain using declared **SYNTHETIC** newline-JSON input. It did not run Quest/ADB, OpenVR, Pi, ROSMonitoring, a physical robot, driver, `robot_ip`, CAN, actuator, or `servo_test.launch.py`.

The demonstrated boundary is:

```text
synthetic TCP JSON → original quest_controller_receiver → original hand_pose_mapper
→ original servo_command_bridge → MoveIt Servo → Gazebo velocity controller → /joint_states
```

This is original downstream runtime/Gazebo evidence, not a reproduction of Quest optical tracking loss or physical actuation.

## Environment and isolation

- Repository at start: `5eb42b2909205829c5a8ec65bb398050ad24c927`, clean `main == origin/main`.
- Vendor worktree: `Noah727/Docker_Teleop@64cbdde88bc52c6a80d37f994752e50f95ba537e`, clean and mounted read-only.
- Image: `docker-teleop-humble:local`, `sha256:ce5200f1d8d5e163b5bd5400a434674a9a836834089332989773bf9a92e44f46`, amd64.
- The pre-existing `docker_teleop_sim` was already running the same original graph on host TCP 15005. It was not stopped or used. S2 instead used owned containers on domains 92/93/94 and localhost-only TCP ports 15006/15007/15008.
- Each S2 graph confirmed active `joint_state_broadcaster`, `joint_group_velocity_controller`, and `hande_position_controller`, with receiver, mapper, bridge, `servo_node`, `joint_states_filter`, `gz_ros2_control`, and rosbag recorder present. `servo_command_bridge` recorded successful `/servo_node/start_servo` auto-start.

The exact commands, IDs, network limits, and source hashes are in `runs/s2_docker_baseline_20260922T080640Z/{commands.txt,environment.txt,input_manifest.sha256}`.

## Inputs and clock treatment

All senders write every wire payload plus host `wall_time_ns` and `monotonic_ns` into their own JSONL. They set both hand poses, `right_teleop_enable=true`, `grip_value=1.0`, and vary the stated `isTracked`, pose X, TCP connection, and (D4) `timestamp` field.

Receiver/mapper/bridge headers and `/joint_states` are decoded from DB3. Phase windows are selected by receiver signature and **bag-storage ordering**; sender wall/monotonic clocks are not used to calculate latency or directly join to bag time. Thus this report makes no input-to-ROS latency claim.

## Measurements

All listed joint values are deterministic offline calculations from recorded `/joint_states`; Hand-E displacement is FK using the pinned URDF model. `guarded velocity` excludes the first six samples of the stated phase.

| Trial / run | Condition | Receiver / target / Servo result | Gazebo joint result |
| --- | --- | --- | --- |
| D0, primary pre-first-tracked idle | no control input; 63.996 s no-input prelude (includes the separately logged 2 s D0) | 3,840 receiver; 0 non-zero target/Servo | 3,762 samples; max delta `3.95e-9 rad`, max velocity `6.18e-11 rad/s` |
| D1 reference, primary | true, teleop, X=.10 | 48 / 0 / 0 non-zero | 47; idle-scale displacement `1.73e-11 m` |
| D1 active, primary | only pose changes to X=.35 | 72 / 71 / 71 non-zero; Servo max norm `.300000` | 69; max joint delta `.523171 rad`, max velocity `.625690 rad/s`, Hand-E displacement `.173848 m` |
| D2, primary | D1 active pose/teleop retained; `isTracked=false` only | 85 / 0 / 0 non-zero | 82; transition max velocity `.360894`, but guarded maximum `8.61e-11 rad/s`; Hand-E transition displacement `.001595 m` |
| D3, primary | no sender bytes for `.75 s` after D2; receiver timeout configured `.25 s` | 33 / 0 / 0 non-zero neutral records | 32; max velocity `8.61e-11 rad/s`, displacement `2.20e-11 m` |
| D4 old, independent `runtime_d4` | old source `timestamp=1.0`, reference X=.20 then active X=.35 | active: 72 / 71 / 71 non-zero; Servo max `.300000` | 70; max delta `.309688 rad`, displacement `.113224 m` |
| D4 fresh, independent `runtime_d4` | fresh source timestamp, reference X=.50 then active X=.35 | active: 73 / 72 / 72 non-zero; Servo max `.300000` | 71; max delta `.314255 rad`, displacement `.114015 m` |
| D5 first, independent `runtime_d5` | connection 1, reference X=.20 then active X=.35 | active: 72 / 71 / 70 non-zero; Servo max `.300000` | 70; max delta `.307874 rad`, displacement `.112654 m` |
| D5 reconnect, independent `runtime_d5` | connection 1 closed, `.7 s` idle, connection 2 reference X=.50 then active X=.35 | active: 73 / 72 / 71 non-zero; Servo max `.300000` | 71; max delta `.312470 rad`, displacement `.113452 m` |

The primary bag's D4/D5 tails are preserved but not used as the fair tests: D1 had already moved the robot near its workspace boundary, so their active output was attenuated. The fresh/old and reconnect measurements above are the fresh-initial-pose, comparable runs.

## Interpretation by condition

- **D0/D1:** original receiver accepted synthetic TCP, the original mapper emitted target twist, the original bridge emitted Servo twist, and Gazebo joint movement was recorded. This confirms the complete permitted original downstream path.
- **D2:** the input differs from D1 active only in `isTracked`. The original path emitted zero mapper and bridge output. The first transition samples contain deceleration, so S2 does not claim instantaneous zero inertia; after six samples, recorded arm velocity is at numerical idle scale.
- **D3:** sender stall exceeds the configured receiver timeout. The receiver publishes its neutral state, with zero target/Servo output and idle-scale joints during the neutral window. The evidence does not estimate an exact arrival-to-timeout latency across clocks.
- **D4:** static source inspection finds no receiver access to JSON `timestamp`; receiver headers are created at publication time. In a new, active-control run, old `timestamp=1.0` and fresh source timestamps both yielded essentially the same observed acceptance class (71/72 non-zero target and Servo samples, `.300000` maximum twist, `.113224/.114015 m` FK displacement). This shows no source-time age gate at this boundary for this controlled synthetic input; it does not establish a clock-contract defect beyond that path.
- **D5:** receiver logs show first peer close then second peer acceptance. Mapper logs show a new reference capture for the second connection, and the subsequent active input again reaches Servo and Gazebo. This tests reconnection/re-arm behavior only. It neither proves full session isolation nor establishes a safety vulnerability.

## Comparison with 2026-09-14 evidence

The prior bag (`43537a...a1fea`) reported D1 `.134070 m`, D2/D3 gated halt after settling, D4 source time not preserved, and D5 reference capture only. S2 agrees on the gate and timeout behavior. The new D1 displacement is `.173848 m`, reasonably not numerically identical because its active duration was 1.2 s rather than the prior 2.0 s and simulator initial/configuration timing differs. S2's D2 includes a visible transition deceleration (`.360894 rad/s`) then `8.61e-11 rad/s` after six samples; the prior extraction similarly warned against an instantaneous halt claim.

S2 extends—not retroactively reinterprets—the older D4/D5 evidence with new active-control comparisons. It does not merge these synthetic results with actual Quest traces.

## Existing defense, UNKNOWNs, and follow-up gates

The existing original defense verified here is the source-side `isTracked`/stale state gate: it prevents non-zero mapper/bridge output for D2 and receiver-neutral D3. It does not retain or age-check the supplied source `timestamp` after the receiver. Existing code/source observations and this runtime do not answer whether that gate represents actual Quest optical/system tracking semantics.

UNKNOWN: actual Quest state mapping; end-to-end source-to-bag latency; physical robot consequence; all internal session-state reset properties; all policies/false accept-reject rates for ROSMonitoring or controller-side defenses. S3 may only begin after review of this commit; S4 must pre-register trust source, freshness budget, clock policy, disconnect/recovery rule, and comparison metrics. No novel-defense-method necessity is concluded here.

## Evidence files and integrity

- Root: `semantic_validation/results/runs/s2_docker_baseline_20260922T080640Z/`.
- Offline decoder/result: `analysis/analyze_s2.py` / `analysis/s2_analysis.json`.
- Primary D0--D5 DB3: `bags/s2_docker_bag/s2_docker_bag_0.db3`, 10,506,240 bytes, SHA-256 `794074ab0e737ee837fae77bb705b98d1e9dffd5fc66f496562b9c0bdd99aa86`. It is readable SQLite/rosbag2 storage, but has no `metadata.yaml` because the first, logged teardown command had a quoting defect; it remains an included raw artifact rather than being replaced.
- D4 DB3: `runtime_d4/bags/d4_timestamp_pair/d4_timestamp_pair_0.db3`, 5,505,024 bytes, SHA-256 `e1575668859d880e77ab673ccf37c44ff1837e6426f59473f6a3ad4ad2c5d420`, with metadata.
- D5 DB3: `runtime_d5/bags/d5_reconnect/d5_reconnect_0.db3`, 2,367,488 bytes, SHA-256 `d2e975a7e6794d9a56621118c1090d2a50fa7b44b20c675ff4562a696b7a47f7`, with metadata.
- Input logs: `inputs/transmitted_retry.jsonl` (`9e7d...5ed66`), `runtime_d4/inputs/transmitted.jsonl` (`524f...8155`), `runtime_d5/inputs/transmitted.jsonl` (`254a...a47f7`). The first sandbox-blocked sender attempt is retained separately with its stderr and only two D0 markers.

No raw evidence was excluded: each new DB3 is below 11 MB, no APK/cache/binary build output was selected, and all selected files are research logs, scripts, or reports.

`git diff --check` reports trailing whitespace in a few captured Gazebo/MoveIt logger lines. Those lines are unmodified raw stdout/stderr, so they are retained rather than normalized; this is a formatting warning, not a source or analysis change.
