# S3 OpenVR original-path control baseline

Status: **DONE** (2026-09-22, fake-API/Gazebo-only evidence)

## 1. Purpose and evidence boundary

S3 reran the existing OpenVR UR5e Gazebo path to check what the unchanged
original production program does with two distinct **fake OpenVR API** fields.
The tested path was:

```
fake openvr.py -> unchanged quest_teleop.py -> /servo_node/pose_target_cmds
  -> MoveIt Servo -> /ur5_arm_controller/joint_trajectory -> Gazebo /joint_states
```

This is neither a Quest, ALVR, nor SteamVR experiment.  It provides no actual
Quest tracking-state, physical robot, driver, `robot_ip`, CAN, actuator, or
external-network evidence.  ROS pose publication, controller trajectory, and
Gazebo simulated joint motion are reported separately below.

## 2. Environment and original source

| Item | Recorded value |
| --- | --- |
| Target | `semantic_validation/targets/openvr_ur5e_jazzy` |
| Target revision / state | `170dad582d624f536359a3192a7f829669c2b031`, clean before execution |
| Original program | `src/quest_bridge/quest_bridge/quest_teleop.py` |
| Program SHA-256 | `0dba77d83288b3d56bf681fdbb03b51b5b508125dee84e3046e24da2890c99d6` |
| Base image | `openvr-jazzy-sim:local`, `sha256:73c0291d95477d2ac1b5aa33bc23dcc9ae9887ea97016633fdc9f126fd34b7a6` |
| Isolated runtime | network `none`, all Linux capabilities dropped, `no-new-privileges`, `ROS_DOMAIN_ID=99`, `rmw_fastrtps_cpp` |

The base image did not contain `/ws/install`.  The preserved `openvr_sim`
container did, and its installed `quest_teleop.py` had the exact SHA-256 above.
Without stopping or modifying that container, S3 created a local, temporary
filesystem snapshot (`sha256:98dc013a56a52fec11192853987470c51141aa16cd334568c3ad3607d2558edc`)
and ran the isolated trial container from it.  No vendor or target source was
modified.  Full commands and environment are in
[`commands.txt`](runs/s3_openvr_baseline_20260922T083841Z/commands.txt) and
[`environment.txt`](runs/s3_openvr_baseline_20260922T083841Z/environment.txt).
After evidence collection, only the S3 container and its temporary snapshot
image were removed; the preserved `openvr_sim` container remained running.

Static inspection of the exact program shows a right-hand `bPoseIsValid` gate
before it publishes `PoseStamped`; it does not read `eTrackingResult`.
[`production_gate_source_excerpt.txt`](runs/s3_openvr_baseline_20260922T083841Z/analysis/production_gate_source_excerpt.txt)
preserves the inspected lines.

## 3. Inputs, execution, and clocks

The existing unmodified `run_trial.sh` launched a fresh Gazebo, controller, and
MoveIt Servo session for each trial, switched Servo to pose-command mode, and
captured four ROS topics for 14 seconds.  The W1/W2/W3 fake module emitted the
configuration line in each production-node stderr log. W0 deliberately did not
start production teleoperation.

The first W0 invocation stopped before starting Gazebo because the newly bound
result root was not writable by the container UID. Only that new result root's
mode was adjusted and W0 was rerun; no W0 raw trial directory existed from the
failed attempt. The retained `stderr/W0.stderr` records the pre-start error.

| Trial | Fake `bPoseIsValid` | Fake `eTrackingResult` | Grip / source motion | Intended role |
| --- | --- | --- | --- | --- |
| W0 | n/a (no production node) | n/a | none | Gazebo/Servo idle baseline |
| W1 | true | `Running_OK` | true; z step `0.001`, 300 steps | valid baseline |
| W2 | true | `Running_OutOfRange` | true; z step `0.001`, 300 steps | tracking-result-only input change from W1 |
| W3 | false | `Running_OK` | true; z step `0.001`, 300 steps | validity-gate check |

The two W1/W2 launch commands have equal declared fake motion and all
environment values except `OPENVR_FAKE_TRACKING_RESULT`.  Their capture begins
at different points in that generated motion (first captured pose z: W1
`0.3010000467 m`, W2 `0.3464999676 m`); therefore S3 does **not** claim a
sample-for-sample or time-aligned trajectory comparison.  Initial captured
joint states differed by at most `4.9044406e-06 rad`.  Capture elapsed time is
Python monotonic time; message header stamps are ROS time and are not joined as
a single clock domain.

## 4. Measured downstream results

The independent JSON-only calculation is in
[`recomputed_metrics.json`](runs/s3_openvr_baseline_20260922T083841Z/analysis/recomputed_metrics.json).
The existing analyzer was separately rerun under
[`analysis/`](runs/s3_openvr_baseline_20260922T083841Z/analysis/).

| Trial | Production poses | Servo→controller trajectories | `/joint_states` | Max joint excursion (rad) | Max abs joint velocity (rad/s) | Result |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| W0 | 0 | 0 | 877 | `1.0095391e-10` | `5.6454912e-05` | idle baseline; no production input/output |
| W1 | 593 | 582 | 814 | `1.5353169` | `2.4101508` | production command accepted; simulated movement observed |
| W2 | 502 | 526 | 868 | `1.5360969` | `2.2163160` | production command accepted; simulated movement observed |
| W3 | 0 | 0 | 775 | `7.9910478e-10` | `5.6453049e-05` | `bPoseIsValid` gate suppressed downstream control |

No `/servo_node/status` messages were captured in these trials; that is
`NOT_OBSERVED`, not proof that Servo had no internal status or fault.  The
harness logs show `ur5_arm_controller active`, `servo_node present`, and
capture completion for every trial.  W1/W2/W3 node teardown includes an
`rcl_shutdown already called` exception after capture/cleanup; it did not
prevent the recorded downstream JSON from being produced.

### W1 versus W2

W1 and W2 had the same final published target: `base_link`, position
`[0.4, 0.0, 0.4499999761581421]` and identical orientation.  Their last
captured joint states differed by at most `0.0007799864 rad`.  Thus the raw
runtime supports the limited statement that `Running_OutOfRange` continued
through this unchanged production program and its observed Servo/Gazebo path
when `bPoseIsValid=true`.  It does not support a claim that the full,
time-aligned trajectories were identical.  See
[`w1_w2_endpoint_comparison.json`](runs/s3_openvr_baseline_20260922T083841Z/analysis/w1_w2_endpoint_comparison.json).

### W3 validity gate

With the fake API set to `bPoseIsValid=false`, raw captures contain zero
production poses and zero Servo→controller trajectories, while the Gazebo
joint values remain at idle-scale variation comparable to W0.  This verifies
the program's direct `bPoseIsValid` gate for this fake API input only.

## 5. Original-path scope actually verified

For W1/W2, raw data verifies all of: the unchanged original program published
ROS pose targets; a controller trajectory topic was observed; and Gazebo
`/joint_states` changed substantially.  W0/W3 establish the corresponding
no-production-command/idle controls.  No rosbag was produced: the existing
harness records topic contents in JSON captures instead.  No conclusion about
physical robot motion follows from Gazebo.

## 6. Comparison with the 2026-09-14 fake OpenVR run

| Trial | Historical 2026-09-14 result | S3 result | Assessment |
| --- | --- | --- | --- |
| W0 | 0 poses, 0 trajectories, `1.173248e-10 rad` max excursion | 0, 0, `1.0095391e-10` | functional match |
| W1 | 543 poses, 537 trajectories, `1.536350 rad` | 593, 582, `1.5353169` | functional match; counts/peak velocity vary with fresh-session capture scheduling |
| W2 | 511 poses, 520 trajectories, `1.536454 rad` | 502, 526, `1.5360969` | functional match; counts/peak velocity vary with fresh-session capture scheduling |
| W3 | 0 poses, 0 trajectories, `3.592504e-11 rad` | 0, 0, `7.9910478e-10` | functional match; both idle-scale only |

The S3 runtime is a new fake-input baseline, not an actual-Quest replication
of the historical run.

## 7. Existing behavior, unknowns, and later checks

- Existing behavior: the original program directly gates on `bPoseIsValid`.
- Existing behavior: `eTrackingResult` is not read by that program; the fake
  `Running_OutOfRange` W2 input nevertheless reached observed Gazebo movement.
- UNKNOWN: whether any actual OpenVR/SteamVR/ALVR source reports an equivalent
  condition, how it maps to Quest semantics, and whether the condition is
  safety-relevant in physical operation.
- UNKNOWN: Servo internal status and acceptance timing beyond the captured
  topic observations.
- S3 does not establish a new-defense need. Any S4 comparison must first
  pre-register trusted state sources, freshness/clock policy, recovery policy,
  and comparable original-path measurements.

## 8. Evidence inventory and integrity

Result root:
[`runs/s3_openvr_baseline_20260922T083841Z/`](runs/s3_openvr_baseline_20260922T083841Z/)

| Evidence | SHA-256 |
| --- | --- |
| W0 downstream JSON | `51f5cc47eda52213b158692b4cbda816c8300e4ec500306a75035548c854b8c7` |
| W1 downstream JSON | `8dbfa9df714e21addc15956b5cb600ca94a5dc8379fd1dc9a5aefd50885decbd` |
| W2 downstream JSON | `7d5e048c19cf30d72496c3bdab931990638af951ac9455d5fe67e1619795d457` |
| W3 downstream JSON | `8fa94a94ca318c4eee663335fa519d609935dea9b041c966dd87a42201b0ef2a` |
| Input source/harness manifest | `d6f7790e6785578a4a6fefc5d9b6a19d94d9eacd91b5de8be02f98ab908851c6` |
| Full S3 evidence manifest | `4619bd50380b01c9824232d9387d5568fec0aba68d461466faa4deb3e93cdac0` |

All S3 raw logs, JSON topic captures, stdout/stderr, analysis scripts, and
outputs are small repository files and are included in this commit. No
credentials, private keys, APKs, build/cache directories, or large binary
artifacts are included. The temporary local Docker snapshot image is not a
research raw artifact and is not committed to Git.
