# S1 Existing-trace audit (2026-09-22)

## Result

**DONE.** This is an offline, read-only raw-evidence audit. It neither ran a Quest/ADB session nor started ROS, Gazebo, Docker, Pi, or bag playback. Inputs and new analysis artifacts are in [`runs/s1_trace_audit_20260922T075316Z/`](runs/s1_trace_audit_20260922T075316Z/); the input hashes in `input_manifest.sha256` match the P0 inventory values.

The independent audit is `analysis/audit.py` and `analysis/audit.json`: standard-library JSON/JSONL parsing plus SQLite opened `mode=ro` and local CDR decoding. Existing PickNik/Docker/OpenVR analyzers were also run into this new root as calculation-method checks; their source and outputs were inspected. Their input files were not modified.

## Raw reanalysis

| Framework | Provenance / boundary actually audited | Raw recalculation | Disposition |
| --- | --- | --- | --- |
| PickNik | ACTUAL_QUEST side-band + robot-free ROS observer | 22 loss intervals: 16 focus/pause/XR-interrupted, 3 left partial, and 3 non-excluded right `HW_PICKNIK_UNTRACKED_ROS_CONTINUES` | MATCH |
| Spes | ACTUAL_QUEST side-band + upstream ROS observer + Pi observation | 628 total, 591 controller, 113 emulated, 101 classified continuation; 5,197 unique ROS stamps all occur in 9,297 Pi records, hence 4,100 extras | MATCH |
| Quest2ROS2 | ACTUAL_QUEST adapted external transport + unchanged controller; separate SYNTHETIC ROS transport data | CDR bag: 5,098 right pose, 5,098 right input, 2,153 target messages with 272 distinct target positions. Visibility: 6,526 pose/input, gaps 30.295494896 s and 0.796048674 s, no app tracking state or phase marker | MATCH; `NO_TRANSITION_OBSERVED` retained |
| Docker_Teleop synthetic | SYNTHETIC newline-JSON replay → original ROS path → recorded Gazebo bag | Topic counts 1,067/1,042/1,067/934; D1 active signature 120 and exactly 120 non-zero target/Servo messages; D2 signature 84; D3 neutral 718. Existing offline FK output reproduces D1 0.134070 m and D2/D3 guarded max arm velocity 1.09e-10 rad/s | MATCH |
| Docker_Teleop actual | ACTUAL_QUEST official app → original ROS path → recorded Gazebo-only run | In t02 UTC window 07:33:35.417–07:33:40.414, decoded 299 received messages, all `tracked=true`, 278 teleop=true, 300 Servo messages/95 non-zero, 294 joint samples, max joint delta 0.3919556913 rad | MATCH for temporal co-observation only |
| OpenVR UR5e | FAKE_API OpenVR → original program → recorded Servo/Gazebo | W0 0/0/893/1.173248e-10; W1 543/537/910/1.536350/2.073817; W2 511/520/919/1.536454/2.056010; W3 0/0/930/3.592504e-11 (`ROS poses`/`Servo trajectory`/`joint samples`/`excursion`, then velocity) | MATCH |

### PickNik

The three right intervals are independently reproduced exactly: `7.917 s` (669 odom, 952 TF, stamp progression 7.911612 s, one transform), `3.874 s` (342, 464, 3.838758 s, one), and `21.302 s` (1,744, 2,555, 21.278419 s, one). Each has `isTracked=false`, tracking bits absent, then reacquisition, and no focus/pause/XR-session interruption by the recorded flags. This supports only: in that actual Quest/Unity/ROS-TCP run, robot-free observer publication continued during these side-band-recorded invalid states. It does not identify optical cause, an original control consumer, or robot movement.

### Spes

The audit extracts nested `header_stamp.sec/nanosec`, not a flat synthetic field. All 5,197 unique upstream ROS header stamps occur in the Pi log; `9297 - 5197 = 4100`. Neither log exposes a shared source-event ID linking one `controller_emulated_position=true` event to one ROS/Pi record. Therefore the maximum claim is **same continuous run co-observation**, not event-level causation or Pi controller acceptance.

### Quest2ROS2

The target-position change is raw-supported, but final CLIK consumer/robot evidence is absent. The visibility gaps are arrival-time gaps only. The raw has no frontend tracking-validity field and no action-phase marker, so `NO_TRANSITION_OBSERVED` is the correct classification. The separate 2026-09-07 synthetic transport summary/raw reports 7/7 stale/future ages published, source stamps re-timestamped, and source frames replaced with `bh_robot_base`; it is **SYNTHETIC source evidence**, not actual Quest tracking evidence.

### Docker actual Quest time axis

The raw system log contains right-controller `ORIENTATION` at 16:33:33.145 and transitions at 16:33:39.904 `POSITION`, 16:33:39.915 `ORIENTATION`, and 16:33:40.110 `POSITION`. The bag header/storage timestamps align to the recorded UTC t02 window, while `/joint_states` were windowed by bag storage time because their header clock is not a demonstrated wall-clock join. Thus the raw supports time-bounded co-observation of system-level mode events, application `tracked=true`, continuing Servo output, and simulated joint change. It does **not** equate `ORIENTATION` with Unity `isTracked=false`, OpenXR state, optical loss, or a causal motion result.

### OpenVR

W1 and W2 finish at the same `z=0.449999976` pose endpoint and retain identical frame/orientation payloads. Their maximum per-joint excursion difference is `1.04e-04 rad` against about `1.54 rad` movement. W3 has no production pose or Servo trajectory and remains within W0 idle magnitude. This verifies the recorded fake-API behavior: `bPoseIsValid=false` was gated, while `Running_OK`/`Running_OutOfRange` were indistinguishable at this tested program→Servo→Gazebo boundary. It makes no Quest/ALVR/physical-robot claim.

## Existing-document comparison

| Existing document | Result | Difference / impact |
| --- | --- | --- |
| `PICKNIK_QUEST_FEASIBILITY_20260917.md` | MATCH | All three quoted intervals and counts reproduce. |
| `SPES_QUEST_NATIVE_ROS_FEASIBILITY_20260917.md` | MATCH | All quoted counts and the 4,100 Pi extra-record limitation reproduce. |
| `QUEST2ROS2_QUEST_FEASIBILITY_20260917.md` | MATCH | Counts/gaps and `NO_TRANSITION_OBSERVED` reproduce; raw does not strengthen tracking attribution. |
| `DOCKER_TELEOP_DOWNSTREAM_RUNTIME.md` + joint extraction | MATCH | Counts, phase signatures, D1 displacement and guarded D2/D3 halt match. D4/D5 remain reference-capture observations, not motion-after-stale/reconnect tests. |
| `GPT_HANDOFF_20260917.md` Docker t02 metric excerpt | PARTIAL_MATCH | 299/299, 278, 300/95, 294 and 0.3919556913 reproduce. Endpoint-delta was not independently recalculated in S1, so it remains unverified here. |
| `OPENVR_UR5E_DOWNSTREAM_RUNTIME.md` | MATCH | W0–W3 raw counts/excursions/velocities and W1–W2 endpoint comparison reproduce. |

No MISMATCH was found in the audited values. `UNKNOWN` is preserved where raw cannot show source-to-command causation, native frontend state, final original consumer, or physical robot behavior.

## Cross-evidence matrix

| Framework | Input | source semantic directly observed | ROS | original consumer | Servo/Gazebo | Pi | strongest bounded claim / UNKNOWN |
| --- | --- | --- | --- | --- | --- | --- | --- |
| PickNik | ACTUAL_QUEST | Unity side-band `isTracked`/state | yes | no | no | no | invalid-state intervals co-occur with robot-free ROS; downstream consumer unknown |
| Spes | ACTUAL_QUEST | WebXR emulated-position side-band | upstream ROS yes | no | no | yes, observation | same-run co-observation; 1:1 causal join unknown |
| Quest2ROS2 | ACTUAL_QUEST adapted bridge | no, black-box | yes | `RightArmController` target | no | no | actual app reaches original controller; tracking semantics unknown |
| Docker_Teleop | SYNTHETIC | supplied `isTracked` | yes | mapper/bridge | yes, recorded Gazebo | no | tested `isTracked` gate and simulated result |
| Docker_Teleop | ACTUAL_QUEST | system mode log, not app semantic equivalence | yes | mapper/bridge | yes, Gazebo-only | no | time-bounded control continuation with app tracked true |
| OpenVR UR5e | FAKE_API | supplied valid/result fields | yes | MoveIt Servo | yes, Gazebo | no | valid gate / tracking-result drop under fake input |

## S2/S3 prerequisites and method-gap decision

S2/S3 must retain the new-root/command/stdout/stderr/hash protocol; explicitly prove clock-domain treatment; and rerun only the documented Gazebo-safe paths after external approval. S4 must pre-register a source-state/freshness/recovery policy before comparing source gate, ROSMonitoring, and controller check. Current method-gap decision: **아직 판단 불가**. The audit verifies bounded observations, not a common end-to-end condition or a need for a novel framework.

## New files, exclusions, and integrity

All S1 outputs are text/JSON, under 1 MiB, and contain no APK/build/cache. Credential/private-key pattern scan found no match. No generated artifact was excluded. Initial failed analysis logs are retained to document a pre-input path-construction error; final result is `stdout/audit_final5.stdout` / `analysis/audit.json`.
