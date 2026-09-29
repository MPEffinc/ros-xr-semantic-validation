# PickNik — Quest-less convergence attempt (actual execution)

**Run id:** `picknik_questless_20260914T064253Z`
**Raw artifacts:** [`runs/picknik_questless_20260914T064253Z/`](runs/picknik_questless_20260914T064253Z/)
**Date (UTC):** 2026-09-14

## Final status

**`BLOCKED_EXTERNAL_DEPENDENCY`**

PickNik's own production publisher path (`RosPublishers` C#) could **not** be
executed, with or without a Quest, because the installed Unity editor has no
license entitlement. That blocker is reproducible and is quoted verbatim below.

What *was* executed is the **transport backend only** — the official
Unity-Technologies `ros_tcp_endpoint` that PickNik's project targets — driven by
a harness-authored ROS-TCP client. That is `E2 SYNTHETIC_RUNTIME` /
`BOUNDARY_LIMITED_REPLAY` evidence about the transport and the message schema.
**It is not evidence about PickNik's semantic handling.**

PickNik's strongest evidence therefore remains **`E1
SOURCE_DATAFLOW_CONFIRMED`**, re-verified today against the pinned revision.

---

## 1. Pinned source identity (confirmed)

| Item | Value |
| --- | --- |
| Repository | `https://github.com/PickNikRobotics/meta_quest_teleoperation.git` |
| `HEAD` in `targets/meta_quest_teleoperation` | `bbaef0762fdb0b429b8ea12a4ca65040748b41dd` |
| `frameworks/picknik/PINNED_REVISION` | `bbaef0762fdb0b429b8ea12a4ca65040748b41dd` |
| Match | **yes** |
| `manifest.yaml: pinned_revision` | `bbaef0762fdb0b429b8ea12a4ca65040748b41dd` — match |
| Commit date / subject | `2026-08-12 16:57:46 -0600` — `chore: Add BSD-3-Clause LICENSE file` |
| Worktree | clean before and after this session (`git status --porcelain` → 0 lines) |
| `UnityProject/Assets/ROSPublishers.cs` SHA-256 | `9fd803f080f5fd2c8ae1f01f1ffd1711f669f05da6a0d8a274cf5f95f454873a` |

Re-verification runs against this checkout, today:

- `picknik_deep_validation.py` → **33/33 PASS** (`deep_validation.jsonl`, `deep_summary.json`)
- `picknik_machine_check.py` → **10/10 PASS**, `failed: []` (`picknik_machine_check.jsonl`)
- `picknik_deep_validation_selftest.py` → 4/4 OK

---

## 2. ROS-TCP Endpoint — actually installed and actually run

### 2.1 Correction to the task premise

The task asked for the *PickNikRobotics/Unity-Robotics-Hub* endpoint. The pinned
project does **not** reference a PickNik fork. `UnityProject/Packages/manifest.json`
pins:

```
"com.unity.robotics.ros-tcp-connector":
  "https://github.com/Unity-Technologies/ROS-TCP-Connector.git?path=/com.unity.robotics.ros-tcp-connector"
```

i.e. upstream **Unity-Technologies**. The matching endpoint is therefore
Unity-Technologies `ROS-TCP-Endpoint`, which is what was used.

### 2.2 Was it actually installed? (verified, not inferred)

Initially **no**. The pre-existing workspace
`ros_env/ros2_ws/install/ros_tcp_endpoint` is a `colcon --symlink-install` result
whose `ros-tcp-endpoint.egg-link` points at `/workspace/ros_env/ros2_ws/build/...`,
a path that does not exist under the mount layout used here. Actual observed
failure:

```
AMENT=/ws/install/ros_tcp_endpoint:/opt/ros/humble
ModuleNotFoundError: No module named 'ros_tcp_endpoint'
```

So "the source is on disk" was **not** the same as "it is runnable". This is
exactly the inference the task warned against.

### 2.3 What was actually done

The already-vendored source (no network fetch was needed) was copied to a
scratch workspace and rebuilt non-symlinked inside an isolated container:

```bash
docker run --rm --network none -e ROS_DOMAIN_ID=71 -v <scratch>/picknik_ws:/ws -w /ws \
  ros-xr-humble:local bash -lc \
  'source /opt/ros/humble/setup.bash && colcon build --packages-select ros_tcp_endpoint'
```

Result:

```
Finished <<< ros_tcp_endpoint [0.45s]
Summary: 1 package finished [0.60s]
MODULE /ws/install/ros_tcp_endpoint/lib/python3.10/site-packages/ros_tcp_endpoint/__init__.py
ros_tcp_endpoint default_server_endpoint
```

Endpoint identity: `Unity-Technologies/ROS-TCP-Endpoint`,
commit `54c1a64b6d5ef6ffa0a0431570bb74329b79b15b` ("Release 0.7.0 (ROS2)",
branch `main-ros2`). No upstream source was modified.

Running it produced actual server output:

```
[INFO] [UnityEndpoint]: Starting server on 127.0.0.1:10000
[INFO] [UnityEndpoint]: Connection from 127.0.0.1
[INFO] [UnityEndpoint]: RegisterPublisher(/left_controller_odom, <class 'nav_msgs.msg._odometry.Odometry'>) OK
[INFO] [UnityEndpoint]: RegisterPublisher(/right_controller_odom, <class 'nav_msgs.msg._odometry.Odometry'>) OK
[INFO] [UnityEndpoint]: RegisterPublisher(/tf, <class 'tf2_msgs.msg._tf_message.TFMessage'>) OK
```

---

## 3. Unity editor — the claim was WRONG, and the real blocker is different

The prior documents (`PICKNIK_HW_READY.md`, `PICKNIK_DEEP_VALIDATION.md`) state
that no Unity editor exists on this machine and that "the full editor install did
not complete". **That is no longer true and must be corrected.**

Actually found:

```
/home/cclab/Unity/Hub/Editor/6000.1.6f1/Editor/Unity     (93 MB binary, 14 GB tree)
$ /home/cclab/Unity/Hub/Editor/6000.1.6f1/Editor/Unity -version
6000.1.6f1
Data/PlaybackEngines/: AndroidPlayer  LinuxStandaloneSupport
```

This is exactly the editor version the project requires
(`ProjectVersion` = `6000.1.6f1 (d64b1a599cad)`), *with* the Android module.

An actual batch-mode execution was attempted against a disposable copy of the
pinned `UnityProject` (the canonical checkout was not touched):

```bash
/home/cclab/Unity/Hub/Editor/6000.1.6f1/Editor/Unity \
  -batchmode -quit -nographics \
  -projectPath <scratch>/picknik_unity/UnityProject \
  -logFile .../unity_batch_import.log
```

**Exact blocker output** (`unity_batch_import.log`, exit code 1):

```
[Licensing::Module] Error: Access token is unavailable; failed to update
[Licensing::Client] Error: Code 404 while processing request
  (status: Found 0 entitlement groups and 0 free entitlements matching requested entitlement ids)
[Licensing::Module] Error: 'com.unity.editor.headless' was not found.
Pro License: NO
No valid Unity Editor license found. Please activate your license.
```

So the blocker is **not** a missing editor and **not** a missing Android module.
It is a **Unity account entitlement / license activation**, which requires
credentials. No credentials were supplied, sought, or written anywhere. This is
an external dependency on the operator, not something the harness can resolve.

Consequences, all unexecuted as a result: EditMode/PlayMode tests, headless scene
execution, APK build, and therefore **any** execution of PickNik's
`RosPublishers.Update()` → `PublishOdomAndTf()` path.

Independent of the license, the repository still contains **0 test assemblies and
0 test C# files**, so even a licensed editor would need a harness-authored
play-mode driver scene; that is a second, smaller obstacle behind the first.

---

## 4. Backend-only runtime (what was actually executed)

### 4.1 Honesty statement — read this before any number below

> These trials exercised the **ROS-TCP transport backend**. The injection point is
> the ROS-TCP socket, which is **downstream of every line of PickNik code**: the
> XRI input actions, the tracked-pose driver, the controller `Transform`, the FLU
> change-of-basis and `PublishOdomAndTf()` were all bypassed. PickNik's C#
> `RosPublishers` **was not executed**. Nothing here is evidence about PickNik's
> semantic handling. Replay subclass: **`BOUNDARY_LIMITED_REPLAY`**.
> Evidence level: **`E2 SYNTHETIC_RUNTIME`**.
> Downstream consequence reached: **`ROS_PUBLISHED`** (a dummy observer in the same
> container). Not `PI_RECEIVED`, not `NATIVE_CONSUMER_ACCEPTED`.

### 4.2 Setup

All three processes ran inside one `ros-xr-humble:local` container with
`--network none`, `ROS_DOMAIN_ID=71`, `RMW_IMPLEMENTATION=rmw_fastrtps_cpp`,
communicating over container loopback and container-local DDS:

```
picknik_rostcp_synthetic_client.py --> [TCP 127.0.0.1:10000] --> ros_tcp_endpoint
    --> ROS 2 publishers --> picknik_ros_observer.py (JSONL)
```

The client implements the wire protocol read by
`ros_tcp_endpoint/client.py:88-104` — `<uint32 LE len><destination utf-8>`
followed by `<uint32 LE len><CDR payload>` — and the `__publish` system command
with its trailing NUL byte (`server.py:120-127`). Message bodies are built with
`rclpy.serialization.serialize_message` for `nav_msgs/Odometry` and
`tf2_msgs/TFMessage`.

Reproduced faithfully from the pinned `ROSPublishers.cs`: topic names and child
frames (`:34-43`), `frame_id = "quest"` shared by Odometry and TF
(`:105`, `:124`), 1/60 s rate (`:33`, `:322`), the 2.0 s registration gate
(`:74`, `:184`, `:290`), a per-sample header stamp regenerated from host UTC wall
clock (`:367-380`, `:394`), zero twist (`:110-113`), and the left→right,
Odometry→TF ordering per tick (`:326-327`, `:405`, `:416`).

Not reproduced: the Unity coordinate conversion (poses are supplied already in
REP-103 FLU, i.e. upstream of the injection point).

### 4.3 Trial 01 / 03 — occlusion scenario (3 s tracked → 4 s "lost", pose frozen → 3 s tracked)

Delivery, both trials, identical:

| Topic | Sent | Received | Loss |
| --- | --- | --- | --- |
| `/left_controller_odom` | 600 | 600 | 0 |
| `/right_controller_odom` | 600 | 600 | 0 |
| `/tf` | 1200 | 1200 | 0 |

`ros2 topic list` inside the container after the run:
`/left_controller_odom`, `/right_controller_odom`, `/tf`, `/parameter_events`, `/rosout`.
`ros2 node list`: `/UnityEndpoint`, `/left_controller_odom_RosPublisher`,
`/right_controller_odom_RosPublisher`, `/tf_RosPublisher`,
`/picknik_semantic_validation_observer`.

During the harness-declared tracking-loss interval (`is_tracked=false`,
`tracking_state=0`, pose held constant):

| Trial | Topic | Received during loss | Distinct positions | Stamp monotonic | Stamp span |
| --- | --- | --- | --- | --- | --- |
| 01 | `/left_controller_odom` | 240 | 1 | true | 3.983 s |
| 01 | `/right_controller_odom` | 240 | 1 | true | 3.983 s |
| 03 | `/left_controller_odom` | 240 | 1 | true | 3.983 s |
| 03 | `/right_controller_odom` | 240 | 1 | true | 3.983 s |

Reading: the ROS header stamp advanced ~3.98 s across 240 consecutive messages
that all carried **one identical pose**. A consumer reading only the wire sees a
stream that looks fresh (advancing stamp, uninterrupted 60 Hz) while the pose
input is static. The observer's received records contain no
`is_tracked`/`tracking_state`/`isTracked`/`trackingState` field of any kind
(`tracking_field_present_in_received_records: false`) — the message types have no
such field.

### 4.4 Trial 02 — collision positive control (pose held fixed, only tracking ground truth flips)

Delivery: 360/360 left odom, 360/360 right odom, 720/720 TF, 0 loss.

Payload digests with the wall-clock stamp zeroed out
(`trial02_collision_detail.txt`):

| Side | Field | Samples | Dominant digest count | Distinct digests | Outlier seqs | `is_tracked` values sharing the dominant digest |
| --- | --- | --- | --- | --- | --- | --- |
| left | Odometry | 360 | 359 | 2 | `[1]` | `[False, True]` |
| left | TF | 360 | 360 | 1 | — | `[False, True]` |
| right | Odometry | 360 | 360 | 1 | — | `[False, True]` |
| right | TF | 360 | 360 | 1 | — | `[False, True]` |

So 3/4 streams are **byte-identical across the tracked → untracked → tracked
transition**, and the fourth is 359/360.

*The single outlier is disclosed rather than discarded:* it is always `seq == 1`,
the very first `nav_msgs/Odometry` serialization performed in the client process.
It was **not reproducible** in three isolated repeat harnesses (`ndiff 0` over 732
bytes, 4–5 repetitions each, including one that imports and calls the harness's
own `build_odometry`). The received field values for that sample were identical
to all others. Best available explanation is CDR buffer padding on the first
allocation; it is **not** explained further here and is **not** claimed to be a
semantic difference.

### 4.5 What these numbers do and do not support

Supported (E2, transport backend):

- The endpoint accepts PickNik's exact topic/type registrations and relays
  `nav_msgs/Odometry` and `tf2_msgs/TFMessage` to real ROS 2 topics with 0 loss
  at 60 Hz over 3 trials (3600 messages relayed in total).
- The `nav_msgs/Odometry` + `tf2_msgs/TFMessage` schema PickNik emits has no
  slot in which tracking validity could travel, demonstrated on an actual wire
  rather than only in a source model.
- A regenerated publication-time stamp makes a static input indistinguishable
  from a live one on freshness grounds at this boundary.

**Not** supported by these numbers:

- Anything about what PickNik's `Update()`/`PublishOdomAndTf()` actually does.
- Anything about what a Unity `Transform` does when a real Quest loses tracking.
- Any downstream consequence beyond `ROS_PUBLISHED` to a dummy observer.

---

## 5. Source re-verification of the two tracking/stamp claims

Re-read from the pinned file today (not copied from earlier documents).

### 5.1 Tracking state is not serialized into the ROS output

- `Update()` calls the same `PublishOdomAndTf(Transform, childFrame, odomTopic)`
  for both controllers with **no tracking predicate**:
  `ROSPublishers.cs:326-327`.
- The only gate before it is the transport registration gate `_registered`
  (`:290-293`) and the rate divider `_timeElapsed` (`:322-324`). Neither is a
  tracking gate.
- `PublishOdomAndTf()` reads the `Transform` unconditionally:
  `sourceTransform.GetPositionAndRotation(out tempPose.position, out tempPose.rotation);`
  — `:384`.
- The fields assigned before publishing are exactly: `_odomHeader.stamp` (`:394`),
  position x/y/z (`:396-398`), orientation x/y/z/w (`:399-402`),
  `_odomMsg.child_frame_id` (`:404`), TF translation (`:407-409`), TF rotation
  (`:410-413`), `_tfStamped.child_frame_id` (`:415`). No tracking field is
  assigned because the message types contain none.
- Repo-wide grep over `ROSPublishers.cs` for
  `isTracked|trackingState|InputTrackingState`: **0 hits**.
- The tokens do exist upstream, in the XRI rig that drives the published
  `Transform` — e.g. `m_TrackingStateInput` and `m_IgnoreTrackingState: 0` at
  `Assets/Samples/XR Interaction Toolkit/3.1.1/Starter Assets/Prefabs/XR Origin (XR Rig).prefab:131,156,314,339,515,556`
  — and the build scene's single `RosPublishers` component references those two
  GameObjects directly: `Assets/Scenes/SampleScene.unity:1144-1145`
  (`leftController: {fileID: 581284854}`, `rightController: {fileID: 821107281}`).
  **Confirmed disposition: `DROPPED` at the `Transform → Odometry/TF` boundary.**

### 5.2 The header stamp is publication time, not XR sample time

- `GetRosTime()` builds the stamp from `DateTime.UtcNow` at call time, with no
  argument and no source-time input: `:367-380`
  (`DateTime now = DateTime.UtcNow;` at `:370`).
- It is called once per publish, inside `PublishOdomAndTf()`: `_odomHeader.stamp = GetRosTime();`
  — `:394`.
- `_tfStamped` is constructed sharing the *same* `HeaderMsg` instance as the
  Odometry message (`:124`, `header = _odomHeader`), so the TF stamp and
  `frame_id` are the same regenerated wall-clock value; only `child_frame_id`
  differs per side (`:404`, `:415`).
- There is no age check, no sequence number, no source timestamp parameter
  anywhere on the path. **Confirmed disposition: I3 `TRANSFORMED` (re-stamped);
  no freshness gate.**

Additional detail re-verified this session and worth recording: `frame_id` is a
constant `"quest"` (`:105`) — no reference-space or session-generation identity —
and both controllers share one reusable `TransformStampedMsg` (`:125-126`), so TF
carries exactly one transform per publish.

Mechanical corroboration: `picknik_machine_check.py` 10/10 PASS and
`picknik_deep_validation.py` 33/33 PASS against this checkout today.

---

## 6. Capture path, tested and ready for the Quest day

The capture tooling was **run, not just reviewed**: `picknik_ros_observer.py`
captured all three trials, writing 600/600/1200 records in trial 01 and 03 and
360/360/720 in trial 02, with zero drops.

**Topics to capture (exactly these three):**

```
/left_controller_odom     nav_msgs/msg/Odometry
/right_controller_odom    nav_msgs/msg/Odometry
/tf                       tf2_msgs/msg/TFMessage    (filtered to child_frame_id in
                                                     {left_controller_odom, right_controller_odom})
```

**Observer command line (verified working):**

```bash
export ROS_DOMAIN_ID=71
python3 semantic_validation/harness/picknik_ros_observer.py \
  --output semantic_validation/results/runs/<run-id>/hw_<trial-id>_ros_observer.jsonl
```

(It refuses to overwrite an existing file, and flushes line-by-line, so a kill
mid-trial still leaves a usable log. Stop it with SIGINT/SIGTERM; it writes a
final `observer_stopped` record carrying the per-topic counts.)

**Endpoint command line (verified working):**

```bash
ros2 run ros_tcp_endpoint default_server_endpoint \
  --ros-args -p ROS_IP:=<desktop ip on the Quest's wifi> -p ROS_TCP_PORT:=10000
```

**Trial IDs:** `hw_t01` … `hw_t05`, one per occlusion cycle, plus `hw_baseline`
for the pre-trial tracked reference.

**Stop condition:** five valid `valid → invalid → reacquired` intervals recorded
in the Quest side-band log with no overlapping focus/pause/XR-display
interruption; or 20 minutes elapsed, whichever comes first. If no
`valid → invalid` transition occurs, the outcome is `HW_NO_LOSS_OBSERVED` — not a
failure of the hypothesis.

**Success criterion for the decisive measurement:** for each valid interval,
`picknik_hw_analyze.py` (self-test 4/4 OK) must classify it into exactly one of
`HW_PICKNIK_UNTRACKED_ROS_CONTINUES` / `HW_PICKNIK_NO_DOWNSTREAM_DURING_LOSS` /
`HW_PICKNIK_PARTIAL_DOWNSTREAM_OBSERVATION`, with
`distinct_ros_transforms` reported. The run is *valid* if ≥ 5 intervals classify
without `INVALID_FOCUS_OR_XR_SESSION`.

**Still required on the Quest day, and not satisfiable by the harness:** a Unity
editor **license activation** (§3), then the APK build, install and launch.

**Not exercised, deliberately:** the Pi `semantic_robot_sink` leg. The trials ran
`--network none` on purpose; adding the Pi would only produce a `PI_RECEIVED`
reception label for harness-generated traffic and would not touch the PickNik
blocker.

---

## 7. Confirmed vs unconfirmed

**Confirmed by execution this session:**

- Pinned identity `bbaef07…41dd` matches `PINNED_REVISION` and `manifest.yaml`; worktree clean.
- `ros_tcp_endpoint` (Unity-Technologies `54c1a64`) builds, starts, accepts PickNik's
  registrations and relays to ROS 2 — verified by running it, after the on-disk
  install was found broken.
- A Unity `6000.1.6f1` editor with the Android module **is** installed here; the
  earlier "no Unity editor" statement is wrong.
- Unity refuses to run: no license entitlement (exact output in §3).
- 3600/3600 messages relayed with 0 loss across 3 backend trials.
- 3/4 streams byte-identical across a tracked↔untracked flip at a fixed pose;
  the 4th 359/360.
- ROS header stamp advanced 3.983 s over 240 messages carrying one frozen pose.
- Source: tracking state absent from the publish path; stamp is `DateTime.UtcNow`
  at publication (file:line in §5).

**Unconfirmed / not observed:**

- What PickNik's `Update()` loop does at runtime — never executed.
- What a Unity `Transform` does under real Quest tracking loss: freeze, infer,
  partially update, or reset.
- Which binding (`XRController` vs `XRHandDevice`) actually drives the Transform.
- Whether `ros_tcp_endpoint` behaves the same under the ROS-TCP-Connector's own
  C# serializer as under `rclpy`'s (the CDR bytes were produced by `rclpy`).
- Any downstream MoveIt Pro consumer behaviour.

---

## 8. The exact remaining Quest-only question

> **H-PICKNIK-1.** On a real Quest 3 running the pinned `SampleScene`, when the
> tracked controller's XRI `isTracked` goes false and/or the `trackingState`
> Position/Rotation bits clear, does the `Left Controller` / `Right Controller`
> GameObject `Transform` keep being published — and if so, does
> `/left_controller_odom`, `/right_controller_odom` and `/tf` continue at 60 Hz
> with (a) a frozen pose, (b) an inferred/extrapolated pose, or (c) not at all —
> while the ROS header stamp keeps advancing?

Only the Unity `Transform` half of that is Quest-only. Everything on the ROS side
of it is already instrumented and tested. The single gate in front of it is the
**Unity editor license activation**, which needs the operator's Unity account.

---

## 9. Artifacts

All under [`runs/picknik_questless_20260914T064253Z/`](runs/picknik_questless_20260914T064253Z/):

| File | Content |
| --- | --- |
| `RUN_MANIFEST.txt` | pinned SHAs, endpoint commit, image digest, domain id, network mode |
| `unity_batch_import.log` | the Unity license blocker, verbatim |
| `trial0{1,2,3}_endpoint.log` | `ros_tcp_endpoint` server output |
| `trial0{1,2,3}_rostcp_client.jsonl` | every frame pushed onto the ROS-TCP socket + harness ground truth |
| `trial0{1,2,3}_ros_observer.jsonl` | every message that actually arrived on ROS 2 |
| `trial0{1,2,3}_analysis.json` | delivery, per-phase and semantic-check results |
| `trial02_collision_detail.txt` | per-side digest counts for the collision control |
| `trial0{1,2,3}_topic_list_*.txt`, `_node_list.txt` | live ROS graph during the trials |
| `deep_validation.jsonl`, `deep_summary.json` | 33/33 source re-verification |
| `picknik_machine_check.jsonl` | 10/10 source re-verification |

Harness code:

- `harness/picknik_rostcp_synthetic_client.py` (new)
- `harness/picknik_rostcp_analyze.py` (new)
- `harness/run_picknik_rostcp_backend.sh` (new)
- `harness/picknik_ros_observer.py` (existing, now runtime-proven)

Non-interference: the pinned checkout was never written to; the Unity attempt ran
against a scratch copy; the vendored endpoint source was copied, not modified.
No credentials or tokens were created, stored, or requested.
