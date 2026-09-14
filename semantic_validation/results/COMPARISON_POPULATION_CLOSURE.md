# Comparison-Population Closure

Generated 2026-09-14. Closes out the ten comparison-framework identities that
were still in a "not yet examined / source-only, runtime untried" state after
[FRAMEWORK_POPULATION_MATRIX.md](FRAMEWORK_POPULATION_MATRIX.md). **No framework
in this set is left unexamined.**

Scope note. This document covers only §15 and §18–§22 of the comparison
population. Docker_Teleop, OpenVR UR5e, Quest2ROS2, OpenArmX, Spes, PickNik,
VR-hand-bridge and Reachy are owned by other workstreams and are not touched
here.

Terminology is that of
[methodology/EVIDENCE_LEVELS_V2.md](../methodology/EVIDENCE_LEVELS_V2.md).
`SOURCE CONFIRMED`, `SYNTHETIC RUNTIME` and `NATIVE QUEST` are three different
things and are never collapsed. **No evidence in this document exceeds
`E2 SYNTHETIC_RUNTIME`.** No Quest, no PICO headset, no physical robot, no
actuator, no CAN bus, no vendor driver and no real robot IP was used anywhere.
Every runtime ran in a container with `--network none` and `ROS_DOMAIN_ID=73`.

## Summary

| # | Framework | § | Architecture family | I-axes touched | Strongest evidence | Final status |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | NVIDIA IsaacTeleop | 15 | OpenXR/DeviceIO → retargeting engine → rclpy | I1, I2, I3 | **E2 SYNTHETIC_RUNTIME**, 15/15 | `QUESTLESS_RUNTIME_COMPLETE` |
| 2 | leggedrobotics/unity_ros_teleoperation | 18 | Unity 6000.2 OpenXR + XR Hands → ROS-TCP → external endpoint | I1, I2, I3, I4, I5 | E1 `SOURCE_DATAFLOW_CONFIRMED` | `SOURCE_ONLY_COMPLETE` |
| 3 | NU-MECH/vr-hand-tracking | 18 | Unity Oculus Interaction → UDP text → rclcpp | I1, I2, I3, I4, I5 | **E2 SYNTHETIC_RUNTIME**, 5/5 | `QUESTLESS_PARTIAL_COMPLETE` |
| 4 | homebrewroboticsclub/vr-teleop | 18 | Unity 2022.3 OpenXR → rosbridge JSON over WebSocket | I1, I2, I3, I4, I5 | E1 `SOURCE_DATAFLOW_CONFIRMED` | `SOURCE_ONLY_COMPLETE` |
| 5 | XRoboToolkit-Teleop-ROS | 19 | PicoXR Robotics Service → `xr_msgs/Custom` → rclcpp | I1, I2, I3, I4 | **E2 SYNTHETIC_RUNTIME**, 7/7, plus a captured hard blocker | `QUESTLESS_PARTIAL_COMPLETE` |
| 6 | xiaoxiaoxh/vr-teleoperation | 20 | Unity Meta → JSON HTTP `/unity` → TeleopServer → direct Flexiv | I1, I2, I3, I4, I5 | **E2 SYNTHETIC_RUNTIME**, 5/5 (wire schema only) | `QUESTLESS_PARTIAL_COMPLETE` — control path `HARDWARE_ONLY_UNSAFE` |
| 7 | LTS0429/teleoperation | 21 | opaque APK → UDP text → rclcpp → (unconnected fake-hw MoveIt demo) | I1, I2, I3, I4, I5 | **E2 SYNTHETIC_RUNTIME**, 8/8 | `QUESTLESS_PARTIAL_COMPLETE` |
| 8 | AgileX QuestArmTeleop | 21 | opaque APK → ADB logcat text → rclpy → external CAN arm driver | I1, I2, I3, I4 | **E2 SYNTHETIC_RUNTIME**, 6/6 (representation layer only) | `QUESTLESS_PARTIAL_COMPLETE` |
| 9 | xArm Quest Teleop | 22 | *none of its own* — consumes the Quest2ROS frontend and wire contract | — | E1 lineage determination | `NON_INDEPENDENT` |
| 10 | Nakama VR_Teleop_Interface | 22 | claimed Unity + ROS 2 Humble + Franka; no code at the pinned ref | — | E0 `DISCOVERED` | `SOURCE_PATH_UNCONFIRMED` |

Six of the ten now carry an **actual runtime result** (1, 3, 5, 6, 7, 8) — all at
`E2 SYNTHETIC_RUNTIME`, none higher. Two are deliberate source-only
classifications with a stated reason (2, 4). Two are identity determinations that
need no runtime (9, 10). For xiaoxiaoxh (6) the runtime is confined to a
vendor-free wire-schema unit; its Flexiv control path is classified
`HARDWARE_ONLY_UNSAFE` and was not imported, built, launched or contacted.

---

## 1. NVIDIA IsaacTeleop (§15) — positive/safe-design comparator

- Identity: `NVIDIA/IsaacTeleop` current main `9fba23c4a3bd5b6de732cac77a47f471fca25276`;
  `isaac_ros_teleop@197f5cd9ff2cbd90533a93c67be2a661319048ba` gitlinks
  `IsaacTeleop@465ce637120ac35404f5f741a9f25f3f1a1a25ea` (`release/1.3.x`).
- Architecture family: native OpenXR/DeviceIO C++ live trackers → pure-Python
  retargeting engine (`TensorGroup`) → `examples/teleop_ros2` rclpy node.
- Prior state: [NVIDIA_POSITIVE_CONTROL.md](NVIDIA_POSITIVE_CONTROL.md) — 8/8
  machine-checked static on the linked release, 10/10 upstream pytest on current
  main. The **ROS output boundary itself had never been executed**; the
  `controller_aim_is_valid` gate was only string-matched in `messages.py`.

### Executed path

```
synthetic OptionalTensorGroup  (harness, at the retargeting-engine output)
  -> examples/teleop_ros2/python/tensor_group_helpers.py   UNMODIFIED
  -> examples/teleop_ros2/python/messages.py               UNMODIFIED
  -> real rosidl-generated teleop_ros2_interfaces/NamedPoseArray,
     geometry_msgs, sensor_msgs, std_msgs  (colcon-built in ros:jazzy-ros-base)
```

- Harness: [`harness/nvidia_ros_validity_gate.py`](../harness/nvidia_ros_validity_gate.py)
- Raw: `results/runs/nvidia_ros_validity_gate_20260914T064627Z/nvidia_ros_validity_gate.jsonl`
  (plus `colcon_build.log`, `stdout.txt`)
- Command:
  `docker run --rm --network none -e ROS_DOMAIN_ID=73 … isaac-teleop-jazzy:local`
  → `python3 harness/nvidia_ros_validity_gate.py --output <run>/…jsonl`
- Actual output: `{"status": "PASS", "trials": 15, "passed": 15, "failures": []}`

Dependency-boundary substitutions, both recorded in the run's `provenance`
record: the `isaacteleop` / `isaacteleop.retargeting_engine` package roots are
installed as namespace shims so the optional compiled `_schema` root import is
bypassed, and `examples/teleop_ros2/python` is put on `sys.path` exactly as the
upstream node does. No production module body was modified; SHA-256 of each
executed production file is in the provenance record.

### Confirmed

| Trial | Result |
| --- | --- |
| `ctrl_both_aim_valid` / `ctrl_left_aim_invalid` / `ctrl_both_aim_invalid` / `ctrl_right_absent` | `controller_aim_is_valid` gates the actionable EE path at runtime. An invalid aim yields `is_valid=False`, a zeroed placeholder pose, **and suppression of that side's TF** — `tf_count` drops 2 → 1 → 0. |
| `hand_both_wrist_valid` / `hand_left_wrist_invalid` / `hand_both_absent` | the same gate shape holds on the hand-derived EE path via `hand_wrist_is_valid`. |
| `head_valid` / `head_invalid` / `head_absent` | `head_is_valid` suppresses the **entire** head output (`build_head_output` returns `None`), so no `PoseStamped` and no TF is emitted at all. |
| `hand_msg_per_joint_validity_serialised` | on the hand-joint topic, per-joint validity *is* serialised into `NamedPoseArray.is_valid`, and invalid joints carry a zeroed pose. |
| `head_tracked_bit_not_read_and_not_serialised` | **key negative.** `HeadInput()` declares `BoolType("head_is_tracked")` alongside `head_is_valid` (`standard_types.py:119-120`), documented as "whether the pose is actively tracked (OpenXR TRACKED)". A repo-wide grep shows `is_tracked` is referenced **nowhere** in `examples/teleop_ros2`. At runtime, `is_valid=True, is_tracked=True` and `is_valid=True, is_tracked=False` produce **byte-identical** ROS output, and `NamedPoseArray` has no `is_tracked` field to carry it. |
| `controller_msg_timestamp_is_host_wall_clock` | the msgpack controller topic's `timestamp` is `time.time_ns()` at build time, not a source sample time; it carries `left_is_active`/`right_is_active` but **no** `aim_is_valid`. |
| `controller_topic_conflates_presence_with_validity` | a controller with `AIM_IS_VALID=False` is still reported `right_is_active=True` with its aim position on the wire. Presence and pose validity are different facts and only presence survives onto that topic. |
| `ee_header_stamp_is_caller_supplied` | the EE header stamp is whatever the node passes in (`self.get_clock().now()` upstream), never a source time. |

### Unconfirmed / not observed

Native DeviceIO, the OpenXR runtime, CloudXR, a real controller active/invalid
transition, an actual ROS publisher/DDS hop, and the Quest itself. The
`release/1.3.x` behaviour is **not** upgraded by this run: this is current main.

### Disposition

- I1: `G` on `VALID` (controller aim, hand wrist, head) — a real, executed gate,
  with TF suppression, and `is_valid` serialised on `NamedPoseArray`.
  **`D` on `TRACKED`** — now demonstrated at runtime, not just statically.
- I2: `P` (handedness as explicit `name` entries / separate fields).
- I3: `D`/`T` — host clock on both the EE header and the msgpack timestamp.
- I4: `D` — no session or generation field in any output message.
- I5: not exercised here (see the prior hold/zero/rebaseline retargeter tests).

- **Evidence level: `E2 SYNTHETIC_RUNTIME`.**
- **Final status: `QUESTLESS_RUNTIME_COMPLETE`.** The production validity gate on
  the actionable ROS path has now actually been executed against real ROS message
  types. NVIDIA remains a **partial** positive control, and this run sharpens why:
  it gates on `VALID` and discards `TRACKED`, so *valid-but-inferred* and
  *valid-and-actively-tracked* are indistinguishable downstream.
- Remaining non-Quest work: none required. An actual DDS hop would add
  `ROS_PUBLISHED`/`PI_RECEIVED` but no new semantic information.
- Quest-only question: what the native OpenXR path actually reports during a real
  occlusion — specifically whether `POSITION_VALID` stays set while
  `POSITION_TRACKED` clears, which is the exact case this design cannot represent.

---

## 2. leggedrobotics/unity_ros_teleoperation (§18)

- Identity: `0edde9493721651d1cc419679ca409b6591cab84`.
- Architecture family: Unity **6000.2.15f1** + OpenXR + Meta XR SDK v85 +
  `com.unity.xr.hands` 1.7.2 → leggedrobotics fork of the Unity ROS-TCP Connector
  → raw TCP to an **external** ROS-TCP-Endpoint.

### Why no runtime was attempted (deliberate source-only classification)

1. **There is no non-Unity half to run.** A full-tree search outside `Assets/`
   returns zero `.cs`/`.py`/`.c`/`.cpp`/`.h` files, and the repo contains **zero**
   `package.xml`, `CMakeLists.txt`, `setup.py` and zero launch files. The only
   non-Unity artefacts are `setup.sh`/`setup.bat`, git hooks, an `.slnx`, and a
   stripped `ovr-platform-util` binary. The ROS half is the external
   `leggedrobotics/ROS-TCP-Endpoint`, which is not vendored and not referenced by
   any submodule or manifest entry.
2. **The required editor is not installed.** `ProjectSettings/ProjectVersion.txt`
   pins `6000.2.15f1`; the only editor on this machine is
   `/home/cclab/Unity/Hub/Editor/6000.1.6f1` (verified by directory listing).
3. Even with a matching editor, every semantic decision in this repo is gated on
   `XRHandSubsystem`/`XRHand.isTracked` data that only a headset produces. There
   is no in-repo simulator: the sole generator, `LidarSpawner.cs:9-12,28-60`, is a
   `MonoBehaviour` producing *inbound* point clouds, and cannot exercise
   `HandPub`/`HeadsetPublisher`. Manufacturing runtime here would mean rewriting
   production code, which is out of bounds.

### Confirmed from pinned source

| Axis | Finding | Evidence |
| --- | --- | --- |
| I1 | `XRHand.isTracked` wraps the whole hand publish block; on `false` **nothing is published** (silent drop, no "invalid" message). The confidence gate is opt-in and **defaults off** (`_highConfidence = false`), so low-confidence frames publish by default. Neither `isTracked` nor `UpdateSuccessFlags` reaches the wire; the only per-joint proxy is an undocumented intensity channel, `1` on pose success vs `0` on failure. | `HandPub.cs:60,95,107,184,188,192,207,210,232,245,250,261` |
| I1 (head) | **No validity gate, and the untracked case is masked.** An all-zero (default) quaternion from an untracked device is rewritten to identity and published every frame, with a source comment acknowledging that this is the untracked signal. | `HeadsetPublisher.cs:126-129,141-144` |
| I2 | Right hand is hardcoded; the left hand is read only to choose a log string and is never published. Laterality exists only as topic names and `child_frame_id` strings. No device, operator or session id anywhere. | `HandPub.cs:61-63,206,210-215`; `HeadsetPublisher.cs:16-18,30,106,115,121` |
| I3 | **`D` — no timestamp exists anywhere.** Grep for `.stamp`/`TimeStamp`/`Clock.` across all 78 C# files in `Assets/RSL` returns zero hits; headers carry only `frame_id`, so every message ships `stamp = 0`, and ROS-TCP-Endpoint forwards verbatim without re-stamping. | `HandPub.cs:196-199`; `HeadsetPublisher.cs:67-73,92-93` |
| I3 (defect) | `headsetPoseMsg.header` is never assigned, so the published `PoseStamped` has neither `frame_id` nor stamp. | `HeadsetPublisher.cs:63,148` |
| I4 | **Absent.** ROS 2 headers have no `seq` and none is synthesized. Reconnect exists but carries no generation counter, so pre- and post-reconnect samples are indistinguishable. | `ROSManager.cs:87-89,107-112,117-123,126-130` |
| I5 | No outbound watchdog, deadman or staleness check. The only staleness-like code is **inverted and therefore dead** — `LastMessageReceivedRealtime - Time.time < 2.5` is always true because the left term is always ≤ `Time.time`, so `_stagnant` latches on the first `Update()` and never clears. Even correct it watches *inbound* traffic, drives a UI sprite, and gates no publishing. Publishing is a manual `PlayerPrefs`-persisted toggle, so it resumes silently after any loss. | `ROSManager.cs:81-88,142-145,175-181`; `StatusIndicator.cs:60-64` |

Safety register: no launch files, no `robot_ip`, no `/dev/tty`, no CAN. The only
hardcoded endpoints are Unity-side connection defaults
(`ROSManager.cs:24-25`, `defaultIP = "10.42.0.1"`, port `10000`), overridden to
`localhost` in the shipped prefabs, with `m_ConnectOnStart: 0`.

- **Evidence level: `E1 SOURCE_DATAFLOW_CONFIRMED`** (partial — the ROS half is
  out of repo).
- **Final status: `SOURCE_ONLY_COMPLETE`.**
- Remaining non-Quest work: none of value. Building the external ROS-TCP-Endpoint
  and watching a stampless message arrive would demonstrate nothing this audit has
  not already established from source.
- Quest-only question: during a real hand-tracking dropout, does the consumer see
  silence (hand path) or a fabricated identity pose (head path), and how long does
  a `tf2` consumer keep treating the last `stamp = 0` transform as usable?

---

## 3. NU-MECH/vr-hand-tracking (§18)

- Identity: `NU-MECH-ENG-495/vr-hand-tracking@8b685f91727bba98cd28322f296fef30c3173309`.
- Architecture family: Unity Oculus Interaction (`IHand.WhenHandUpdated`) → plain
  UDP angle text on port 9000 → rclcpp regex parser → `std_msgs/Float32MultiArray`
  on `hand_joint_angles`. In-repo consumer is a Qt visualiser only; there is no
  robot consumer anywhere in the repository.

### Executed path

```
synthetic UDP datagram -> 127.0.0.1:9000
  -> hand_tracking_quest/hand_tracker_quest_node   UNMODIFIED upstream C++
  -> DDS (ROS_DOMAIN_ID=73, loopback, --network none)
  -> rclpy observer on /hand_joint_angles
```

- Harness: [`harness/nu_mech_udp_runtime.py`](../harness/nu_mech_udp_runtime.py)
- Build: `colcon build --packages-select hand_tracking_quest` in a
  `ros:jazzy-ros-base`-derived image (`xr-udp-jazzy:local`) — succeeded unmodified.
- Raw: `results/runs/nu_mech_udp_runtime_20260914T065103Z/` (`…jsonl`,
  `nu_mech_node_stdout.txt`)
- Actual output: `{"status": "PASS", "trials": 5, "passed": 5, "failures": []}`

Injection is at the UDP wire, i.e. **downstream** of the Unity
`IsTrackedDataValid` gate. Replay class `BOUNDARY_LIMITED_REPLAY`; no claim is
made about that gate's native behaviour.

### Confirmed

| Trial | Actual input | Actual output |
| --- | --- | --- |
| `t1_wellformed_packet_reaches_ros` | `10.5,-20.25,30.0,0.0,-45.75` | one `Float32MultiArray` with exactly those five values; `has_header = False` |
| `t2_validity_token_is_swallowed_as_an_angle` | `IsTrackedDataValid:0;10.5,-20.25,30.0,0.0,-45.75` | **six** values, `[0.0, 10.5, -20.25, 30.0, 0.0, -45.75]` |
| `t3_repeated_identical_packet_indistinguishable` | `1.0,2.0,3.0`, then the same 1 s later | two identical messages, nothing distinguishes them |
| `t4_stream_stop_emits_no_invalidation` | nothing, for 2 s | zero messages |
| `t5_numberless_packet_is_dropped_not_zeroed` | `HandLost` | zero messages |

The `t2` result is the sharp one. `parseJointAngles`
(`HandTrackerQuest.cpp:169-187`) applies `[-+]?[0-9]*\.?[0-9]+` to the **whole
datagram** with no key parsing, so any number anywhere becomes a joint angle.
There is no slot in which a tracking-validity bit could travel without corrupting
the payload — I1 is not merely dropped, it is **unrepresentable** at this wire.

`t5` is the I5 complement: an explicit loss report and a lost packet produce the
same observable (silence), because the else-branch logs
"No valid joint angles found" and publishes nothing
(`HandTrackerQuest.cpp:153-155`).

### Disposition

I1 `D` (unrepresentable at the wire; gated upstream in Unity only, per the prior
`IsTrackedDataValid` source finding) · I2 `D` · I3 `D` — and structurally so,
since `std_msgs/Float32MultiArray` has no `Header` at all · I4 absent ·
I5 absent downstream. Downstream consequence: `ROS_PUBLISHED`.

- **Evidence level: `E2 SYNTHETIC_RUNTIME`.**
- **Final status: `QUESTLESS_PARTIAL_COMPLETE`.** The ROS half is fully executed;
  the Unity half is not, and the framework has no robot consumer, so no control
  consequence is claimed or claimable.
- Remaining non-Quest work: none of value.
- Quest-only question: does `IsTrackedDataValid` gating in the Unity app actually
  stop the UDP stream on a real hand-tracking loss (silence), or does it keep
  sending the last angles?

---

## 4. homebrewroboticsclub/vr-teleop (§18)

- Identity: `2952d27b914d707da47ec5137d69198a6ce6d6df` (v1.1.0).
- Architecture family: Unity **2022.3.62f2** + OpenXR/Oculus + XR Hands 1.5.1 +
  legacy `UnityEngine.XR` `InputDevice`/`InputTracking` → hand-rolled
  rosbridge-v2 JSON over WebSocketSharp → a session gateway URL
  `ws://{ip}:{port}/ws/teleop/session/{sessionId}?token=…`. The ROS half is the
  external `homebrewroboticsclub/br-vr` (`teleop_fetch`) package.

### Why no runtime was attempted (deliberate source-only classification)

Same two blockers as Legged, independently verified: zero `.cs`/`.py`/`.cpp`
outside `Assets/`, zero `package.xml`/`CMakeLists.txt`/`setup.py`, zero launch
files — no non-Unity half exists; and the pinned editor `2022.3.62f2` is not
installed (only `6000.1.6f1` is). There is no simulator: grep for
`simulat|mock|fake|synthetic` across `Assets/Scripts` returns nothing, and the
`.hbr` dataset recorder is write-only with no playback path.

Note: the pinned tree is materially richer than
`frameworks/homebrew_vr_teleop/SOURCE_MAP.md` records; that note's line numbers
still resolve, but it misses the RTT safety gate, the NTP/ROS time sync, the
lifecycle event topic and the session-scoped websocket URL. The updated
`RESEARCH_UTILITY.md` supersedes it.

### Confirmed from pinned source

| Axis | Finding | Evidence |
| --- | --- | --- |
| I1 | `InputDevice.isValid` + `CommonUsages.isTracked` with a `devicePosition` fallback, plus `InputTracking.GetNodeStates`, feed a three-way mode decision (`controllers` / `hands` after a grace period / `none`). **The decision is computed, named, and then withheld from the wire.** `modeStr` is written into the *local* `.hbr` recording but never into the published `PoseArray` or `JointState`; on the "none" branch the publisher emits **identity poses at the origin**, byte-identical to a genuine hand-at-origin pose. | gate `:391-392,402,404-405,410-413`; substitution `:429-433,632-634,646`; `modeStr` computed `:551`, recorded `:571`, absent from `:435-437,542-549` (all `QuestRosPoseAndJointsPublisher.cs`) |
| I2 | `JointState.name` carries explicit `L_`/`R_` prefixes, so laterality *is* on the wire for joints. `PoseArray` identity is positional only (`[head, left, right]`), documented nowhere in the payload. The session id lives in the websocket URL and is **not** in any message. | `:452,460,463,470-475,499-503,508-538`; `:415-433`; `RosbridgeImageSubscriber.cs:216` |
| I3 | **`P`, and this is where Homebrew is materially stronger than the rest of §18.** `RosHeader()` writes a real `stamp` from `GetEstimatedRosUnixTimeNs()` — local Unix time plus an NTP offset plus a ROS-clock offset — onto both `/quest/poses` and `/quest/joints`, and the rosbridge publish path wraps the message verbatim without re-stamping. Caveats: it is a **send-time** estimate, not the pose's native sample time (no OpenXR `predictedDisplayTime` is ever consulted); the `ntpTimeSynchronized`/`rosTimeSynchronized` flags are withheld exactly as the validity flag is, so a consumer cannot tell a disciplined stamp from a free-running one; and `secs` is cast to `int` (Y2038 truncation). | `:725-736,848-855`; sync `:95-113,222-223,1376-1377`; flags recorded locally only `:563-569`; `RosbridgeImageSubscriber.cs:1423-1445` |
| I4 | Partial, and the best in this set. Server-issued `sessionId` + bearer token in the URL, a per-session reset hook, full state reinitialization on session start, and an out-of-band lifecycle topic publishing `session_active`/`pause`/`resume`/`disconnect` with a reason and `ts_unix_ms`. But **no per-message sequence or generation number**, and the session id is not in any payload — a consumer reading the pose topics alone cannot attribute a sample to a session, and must correlate against a best-effort `String` topic that is skipped entirely when the socket is closed, i.e. exactly when it matters. | `RosbridgeImageSubscriber.cs:204,216,218`; `QuestRos…:226-229,750-804,1335-1344,1384-1389`, skip `:755-756` |
| I5 | Substantially present — and the gap is precise. A real RTT deadman: 5-sample preflight gate, then a continuous monitor that on 2 consecutive samples ≥ 200 ms **or** 2 consecutive ping failures publishes a `disconnect`/`ping_exceeded` lifecycle event, raises an error screen, stops recording and disconnects. Plus inbound image watchdogs (3 s first-frame, 5 s silence, 10 s connect) and lifecycle pause on app background. Re-arm is explicit and operator-driven (double-press X to start, Y to stop), guarded against re-entry. **But the deadman has no tracking term.** Nothing watches `useControllers`/`useHands` going false; that case is handled by emitting origin-identity poses forever while the session stays active. | params `:49-68`; preflight `:1356-1366,1397+`; monitor `:1651-1708,1690-1703`; stop `:1500-1528`; watchdogs `RosbridgeImageSubscriber.cs:63-73,122-123,251,703,42,529-530,543-613`; pause `:356-360,371-375`, `QuestRos…:788-804`; re-arm `:233-236,226-229`; gap `:429-433` |

Safety register: no launch files, no `robot_ip`, no CAN, no `/dev/tty`, no vendor
SDK. Hardcoded values are client-side, UI-overridable connection defaults
(`RosbridgeImageSubscriber.cs:17`; `TeleopAuthManager.cs:12`;
`TeleopHelpRequestsManager.cs:13`). The only fixed external endpoints actually
contacted are the NTP hostnames at `QuestRos…:95-113`.

- **Evidence level: `E1 SOURCE_DATAFLOW_CONFIRMED`.**
- **Final status: `SOURCE_ONLY_COMPLETE`.**
- Remaining non-Quest work: none of value without the external `br-vr` package
  and a matching editor.
- Quest-only question: with both controllers and hands lost mid-task, does the
  RTT-validated, correctly-stamped stream of **origin-identity poses** continue
  indefinitely, as the source implies? That is a single, well-posed headset
  experiment and it is the highest-value Quest question in §18.

---

## 5. XRoboToolkit-Teleop-ROS (§19)

- Identity: `XR-Robotics/XRoboToolkit-Teleop-ROS@a516bb28061030a0fb5a73367241bcaa883eaf02`.
- Architecture family: proprietary PicoXR Robotics Service (`PXREARobotSDK`)
  device-state JSON → `picoxr/talker` → `xr_msgs/Custom` on `/xr_pose` → an ARX
  arm example consumer (external hardware; **not** built or launched).

### Step 1 — the hard blocker, captured

`colcon build --packages-select picoxr` with no PICO SDK present, upstream
unmodified:

```
CMake Error at CMakeLists.txt:46 (message):
  robot sdk not found.  Please install robot sdk first.
```

(`results/runs/xrobotoolkit_20260914T065454Z/attempt2_picoxr_no_sdk.log`.)
Upstream probes `/opt/apps/roboticsservice/SDK` then
`/opt/apps/picobusinesssuite/SDK/clientso/64` and `FATAL_ERROR`s otherwise.

A second, independent upstream blocker was also captured
(`attempt1_unmodified_build.log`): `ros2/xr_msgs/CMakeLists.txt:14` calls
`rosidl_generate_interfaces()` but only does
`find_package(rosidl_generator_cpp)`, which does not define that macro on ROS 2
Jazzy — `Unknown CMake command "rosidl_generate_interfaces"`. The message package
does not build as shipped.

### Step 2 — executed path with an inert local substitute

```
synthetic PICO device-state JSON records (local file)
  -> INERT LOCAL SUBSTITUTE for PXREARobotSDK.h + libPXREARobotSDK.so
     (harness/xrobotoolkit_stub/ — no device discovery, no socket, no PICO code;
      PXREAInit only replays the file into the upstream callback)
  -> picoxr/talker   UNMODIFIED ros2/picoxr/src/publisher.cpp
  -> DDS (ROS_DOMAIN_ID=73, loopback, --network none)
  -> rclpy observer on /xr_pose  (xr_msgs/Custom)
```

Both substitutions are dependency-boundary only and are recorded in the run's
`provenance` record together with the SHA-256 of `publisher.cpp` and of every
stub file: (a) the inert SDK, installed at the exact path upstream probes; (b)
`find_package(rosidl_default_generators)` injected via
`CMAKE_PROJECT_xr_msgs_INCLUDE` rather than by editing upstream CMake.

- Harness: [`harness/xrobotoolkit_publisher_runtime.py`](../harness/xrobotoolkit_publisher_runtime.py)
  and [`harness/xrobotoolkit_stub/`](../harness/xrobotoolkit_stub/)
- Raw: `results/runs/xrobotoolkit_20260914T065454Z/`
- Actual output: `{"status": "PASS", "trials": 7, "passed": 7, "failures": []}`

### Confirmed

| Trial | Actual result |
| --- | --- |
| `t0_all_synthetic_records_reach_ros` | 5 service records → 5 `xr_msgs/Custom` on `/xr_pose` |
| `t1_source_timestamp_preserved_verbatim` | `timeStampNs` `111222333444555` and `111222333555555` arrive **verbatim** as `timestamp_ns` (`publisher.cpp:130`). Unlike every re-stamping bridge in this study, XRoboToolkit does carry a source time onto the ROS message. |
| `t2_stale_source_timestamp_published_unchanged` | a timestamp of `1000000000000` (≈1970) is published unchanged, with `head_status` still `1`, no warning, no age guard. Freshness is **carried but never enforced** on this path. |
| `t3_head_status_preserved_from_service` | head `status` 1 / 0 / 2 arrive as 1 / 0 / 2 (`publisher.cpp:142`) |
| `t4_controller_status_overwritten_with_constant_3` | **key finding, now runtime-confirmed.** Two records carrying controller `status` 1 and 0 respectively both arrive with `left_status = right_status = 3`. `publisher.cpp:167` assigns `controller_msg.status = 3` unconditionally, discarding `ctrl_j["status"]`, which is present in the same JSON object and read for no other purpose. |
| `t5_absent_controller_and_head_use_minus_one_sentinel` | absence *is* representable: missing `Controller` → both statuses `-1` (`:178-179`); missing `Head` → status `-1` (`:144`) with an **all-zero pose array**, i.e. a legal-looking pose paired with a sentinel status. |
| `t6_no_device_or_session_identity_on_the_topic` | `xr_msgs/Custom` fields are exactly `head, input, left_controller, right_controller, timestamp_ns` — no device id, no session id, no sequence. The stub's `deviceID` is available to the callback (`:121`) and is not copied. |

### Unconfirmed / not observed

Everything upstream of the service JSON: the PicoXR frontend, the PICO Robotics
Service, and therefore **what any `status` value natively means**. The ARX
example consumer was not built or launched, so no downstream control behaviour is
observed. The PICO SDK itself was never obtained or run.

### Disposition

I1: head status `P`; controller status **`D` — overwritten with constant `3`**,
now demonstrated at runtime; presence/absence `P` via the `-1` sentinel ·
I2 `T` (laterality only; `deviceID` dropped) · I3 **`P` on the message, never
revalidated** · I4 absent · I5 not observable at this boundary.
Downstream consequence: `ROS_PUBLISHED`.

- **Evidence level: `E2 SYNTHETIC_RUNTIME`**, with an accompanying reproducible
  `BLOCKED_EXTERNAL_DEPENDENCY` for the unsubstituted build.
- **Final status: `QUESTLESS_PARTIAL_COMPLETE`.** The open bridge/publisher half
  is executed; the opaque PicoXR/ARX boundary is where it stops, exactly as
  planned.
- Remaining non-Quest work: none without the proprietary SDK.
- Quest/PICO-only question: what does the Robotics Service actually put in
  `Controller.status`, and does any real value of it correspond to loss of
  tracking — which is unanswerable here precisely because `publisher.cpp:167`
  destroys it.

---

## 6. xiaoxiaoxh/vr-teleoperation (§20)

- Identity: `1d29f9f35f77ec5024f6837a0a3d790cc37b7bd1`.
- Architecture family: Unity Meta controller `Transform` + `OVRInput` → JSON HTTP
  POST `/unity` (FastAPI, port 8082) → `TeleopServer` → HTTP to a bimanual Flexiv
  robot server → **direct Flexiv RDK motion commands**. An rclpy publisher exists
  in parallel and never sees the Unity payload.

### Safety determination made first, and what it permitted

A full transitive-import trace was done before anything was executed. The
findings that set the boundary:

- The **only** `import flexivrdk` in the repository is at module scope in
  `real_world/robot/single_flexiv_controller.py:8`. `FlexivController.__init__`
  (`:24-43`) constructs `flexivrdk.Robot(robot_ip, local_ip)` and
  `flexivrdk.Gripper`, then calls `clear_fault()`, `robot.enable()`, busy-waits on
  `isOperational()` and sets an NRT motion mode. **There is no dry-run or
  simulation flag anywhere.**
- `BimanualFlexivServer.__init__` (`bimanual_flexiv_server.py:25-35`) constructs
  two of those against `192.168.2.110` / `192.168.2.111` and then immediately
  calls `gripper.move(0.1, 10, 0)` on **both** arms. Construction *is* actuation.
- Every entry point constructs it as its first action: `teleop.py:29`,
  `tests/test_robot_server.py:41` (which then closes a real gripper to 0.02 m at
  `:60-61`), `bimanual_flexiv_server.py:157-170`, and
  `bimanual_robot_publisher.py:171`. Motion APIs:
  `single_flexiv_controller.py:95` `sendJointPosition`, `:103`
  `sendCartesianMotionForce`; `bimanual_flexiv_server.py:87,99,110,120,145-146`.
- `TeleopServer.run()` (`teleop_server.py:71-77`) unconditionally spawns
  `process_cmd`, which issues `/move_tcp/left|right` (`:260,269`) and
  `/move_gripper*` (`:185,191,204,210`) to the configured robot server.
- `Makefile:21-31` runs the project container `--privileged` with host networking.

**None of the above was imported, constructed, built, launched or contacted.**
No socket was opened toward any robot address.

The trace did, however, identify a unit with **zero in-repo imports and zero
ROS/vendor imports in its entire transitive chain**: `common/data_models.py`,
whose module-scope imports are only pydantic, numpy, enum and typing. That is the
exact pydantic model FastAPI uses to parse the `/unity` body, so exercising it
reproduces the production parse bit-for-bit while being physically incapable of
reaching anything. That, and only that, was run.

### Executed path

```
synthetic Unity JSON payload (harness)
  -> common/data_models.py :: UnityMes / HandMes   UNMODIFIED upstream pydantic models
  -> (stop. Nothing downstream of the parse is executed.)
```

- Harness: [`harness/xiaoxiaoxh_wire_schema_runtime.py`](../harness/xiaoxiaoxh_wire_schema_runtime.py)
- Raw: `results/runs/xiaoxiaoxh_wire_schema_20260914T070606Z/xiaoxiaoxh_wire_schema_runtime.jsonl`
- Container: `--network none`. The harness asserts at startup that none of
  `flexivrdk`, `pyrealsense2`, `rclpy` is in `sys.modules` and **aborts** if any
  is; the assertion is recorded in the `provenance` record.
- Actual output: `{"status": "PASS", "trials": 5, "passed": 5, "failures": []}`

### Confirmed

| Trial | Level | Actual result |
| --- | --- | --- |
| `t1_wire_schema_field_inventory` | E2 | `UnityMes` is exactly `{timestamp, valid, leftHand, rightHand}`; `HandMes` is exactly `{q, pos, quat, thumbTip, indexTip, middleTip, ringTip, pinkyTip, squeeze, cmd}`. **No session, no sequence, no generation, no device/source id, no frame id.** I2 and I4 are absent by construction. |
| `t2_valid_false_payload_parses_identically` | E2 | a payload with `"valid": false` parses successfully and its every actionable field — `pos`, `quat`, `cmd`, `squeeze` — is **identical** to the valid message. Declaring invalidity changes nothing that a consumer would act on. |
| `t3_sender_sets_valid_unconditionally` | E1 machine check | `Cotroller_collect` ends with an unconditional `message.valid = true;` (`HandDataCollector.cs:310`), and the file calls **none** of `GetControllerPositionValid`, `GetControllerOrientationValid`, `IsDataValid`, `IsDataHighConfidence`, `GetActiveController`, `IsTracked` — confirmed by scan, zero hits. The app-level `valid` flag is **not** native tracking evidence. |
| `t4_wire_valid_and_timestamp_are_never_read` | E1 machine check | a scan of every non-`third_party` Python file in the repo finds **zero** readers of `.valid` and **zero** readers of `mes*.timestamp`. The two semantic fields the wire does carry are consumed by nothing. |
| `t5_timestamp_is_unity_time_since_app_start` | E1 machine check | the sender uses Unity `Time.time` and no epoch clock (`DateTimeOffset`/`UtcNow`/`UnixTimeMilliseconds` all absent). `timestamp` is seconds since app start on the headset: not an epoch, not a tracking capture time, and not comparable to any receiver clock — so even a consumer that wanted to check freshness could not, from this field alone. |

### Additional source findings (E1, not executed)

- `message` is a **static singleton** and `reset()` clears only `valid` and the
  two `cmd`s (`HandDataCollector.cs:70-72,109`) — `pos`/`quat` keep the previous
  frame's values, so a collection failure re-sends a stale pose rather than
  nothing.
- `TeleopServer.process_cmd` `peek()`s the newest buffered message every cycle
  (`teleop_server.py:136`) with no freshness test, so if Unity stops sending it
  **keeps re-applying the last message indefinitely**. `latest_timestamp` is set
  to `0.` at `:58` and never read or updated.
- I5: arming is a **toggle on a discrete button press** (`cmd == 2` flips
  `*_tracking_state`, `teleop_server.py:229-249`, from
  `OVRInput.GetDown(RawButton.Y/B)`), not a held clutch — once armed, motion
  continues with no further operator input. `squeeze` drives gripper width only,
  not a deadman. The single automatic disarm is a 0.3 m **positional jump** test
  (`:252-267`): a discontinuity check, not a validity or freshness check, which a
  slowly drifting invalid pose passes every cycle. `/move_tcp/*` is sent with
  `timeout=0.001` and `ReadTimeout` deliberately swallowed (`:87-94`), so
  command-delivery failures are invisible.
- The `/unity` endpoint is unauthenticated FastAPI bound to a LAN address
  (`teleop_server.py:31,76`); `HttpClient.PostAsync` is fire-and-forget with no
  await (`HandDataCollector.cs:227`), so out-of-order delivery is undetectable.

### Disposition

I1: **present on the wire as `valid`, set unconditionally by the sender, read by
no consumer — `D` at both ends**, now runtime-confirmed for the parse half and
machine-checked for the read half · I2 absent (positional `leftHand`/`rightHand`
only, and `LRinverse` can silently swap them, `HandDataCollector.cs:303-308`) ·
I3 present but unusable and unread · I4 absent · I5 toggle-armed with no
tracking-derived or freshness-derived disarm. Downstream consequence:
`NO_OUTPUT` — this run stops at the parse.

- **Evidence level: `E2 SYNTHETIC_RUNTIME`** for the schema trials;
  `E1 MACHINE_CHECKED_STATIC` for `t3`/`t4`/`t5`, labelled per trial in the raw
  record and never merged upward.
- **Final status: `QUESTLESS_PARTIAL_COMPLETE`, with the control path classified
  `HARDWARE_ONLY_UNSAFE` and permanently out of bounds for this testbed.** The
  vendor-free wire-schema half is executed; the Flexiv half is not, and must not
  be without a purpose-built, separately source-audited inert robot server and a
  host with no route to `192.168.2.0/24`.
- Remaining non-Quest work, if ever wanted: `TeleopServer` itself is importable
  and constructible without any vendor module (its chain reaches ROS
  `geometry_msgs` via `common/space_utils.py:1-4` and stops there), and `__init__`
  opens no socket. A `fastapi.testclient` exercise of the `/unity` route — with
  `run()` and `process_cmd` never invoked, `robot_server_ip` on loopback, and no
  route to the robot subnet — would extend this result to the real route handler
  and `RingBuffer`. It was not done here because the parse boundary already
  answers the semantic question and the marginal evidence does not justify the
  marginal risk.
- Quest-only question: none of research value. The sender consults no native
  tracking API at all, so a headset would produce the same unconditional
  `valid = true` it produces synthetically. That absence is itself the finding.

---

## 7. LTS0429/teleoperation (§21)

- Identity: `lts0429/teleoperation@65ce76c9b92d843f8201c212179dde1652d4ac93`.
- Architecture family: opaque `Teleoperator.apk` → plain-text UDP on port 5005 →
  `meta_quest_client/udp_client` (rclcpp) → `PoseStamped` on
  `/headset`, `/left_hand`, `/right_hand` plus `/tf`. A vendored MoveIt Servo demo
  exists in the repo but is unconnected and configured for a **fake-hardware**
  Panda; it was not built or launched.

Safety pre-check before any execution: a full-repo grep for `robot_ip`, IPv4
literals, `can0`/socketcan, `/dev/tty*`, `serial`, and vendor SDKs
(`piper_sdk`, `arx`, `can_utils`, ethercat, rtde) returned **zero hits**. The
frontend APK in the checkout is a 133-byte git-LFS pointer whose object was never
fetched, so there is no binary to run even accidentally.

### Executed path

```
synthetic UDP datagram -> 127.0.0.1:5005
  -> meta_quest_client/udp_client   UNMODIFIED upstream C++
  -> DDS (ROS_DOMAIN_ID=73, loopback, --network none)
  -> rclpy observer on /headset, /left_hand, /right_hand, /tf
```

- Harness: [`harness/lts0429_udp_runtime.py`](../harness/lts0429_udp_runtime.py)
- Build: `colcon build --packages-select meta_quest_client` — succeeded unmodified.
- Raw: `results/runs/lts0429_udp_runtime_20260914T065407Z/` (canonical; see
  `RUN_SEQUENCE.md` there for the two superseded exploratory runs)
- Actual output: `{"status": "PASS", "trials": 8, "passed": 8, "failures": []}`

### Confirmed

| Trial | Actual input | Actual output |
| --- | --- | --- |
| `t1_full_packet_publishes_three_poses_and_tfs` | full 6-token packet | 1 pose on each of the three topics, TF children `headset`/`left_hand`/`right_hand`, every `frame_id` the hardcoded literal `"world"` |
| `t2_header_stamp_is_receiver_clock` | same | wire carries no timestamp field; `header.stamp` lands within 500 ms of the observer's wall clock; the TF stamp is copied from the pose stamp (`udp_client.cpp:162,171`) |
| `t3_stale_resend_is_restamped_fresh` | byte-identical packet resent 2 s later | identical pose, stamp advanced > 1 s. **A downstream age check on `header.stamp` measures host receive latency only, never source age.** |
| `t4_pos_without_rot_is_dropped_silently` | `…Pos` tokens only, no `…Rot` | nothing published, no TF. The publish condition is a string-presence test (`:59,64,69`), not a validity test |
| `t5_unknown_validity_tokens_ignored…` | full packet **plus** `Tracking:LOST;Confidence:0.0` | all three poses published normally. The token chain (`:51-56`) has no default branch — **there is no extension point by which a frontend could signal invalidation to this node** |
| `t6_stream_stop_emits_no_invalidation` | nothing, for 2 s | zero poses, zero TFs; no watchdog, no zeroing publish |
| `t7a_nan_token_is_accepted_and_published` | `LeftHandPos:0.1,NaNvalue,0.3;…Rot:0,0,0,1` | `std::stod` accepts the `NaN` prefix, `vals.size()==3` passes, and a **non-finite pose reaches both the topic and `/tf`** with no validity annotation |
| `t7b_nonnumeric_token_halts_the_receiver_thread` | `LeftHandPos:0.1,abc,0.3;…` | node stdout: `terminate called after throwing an instance of 'std::invalid_argument' / what(): stod`. **The whole process aborts.** `std::stod` at `:98`/`:128` is unguarded, the exception escapes `udp_server()` on the receive thread, and a single non-numeric field in one datagram ends the bridge outright — with no ROS-side error signal and no lifecycle notification to any consumer |

### Disposition

I1 absent on the wire, frontend `U` (opaque) · I2 `T` (token name → topic and
`child_frame_id` only) · I3 `D`, re-stamped with the receiver clock · I4 absent ·
I5 absent. Downstream consequence: `ROS_PUBLISHED`.

- **Evidence level: `E2 SYNTHETIC_RUNTIME`.**
- **Final status: `QUESTLESS_PARTIAL_COMPLETE`.** This is a genuine upgrade from
  the framework's prior `E0/E1` opaque classification: the host half is now fully
  executed and characterised. The frontend remains `OPAQUE_FRONTEND` and no
  frontend semantics are invented.
- Remaining non-Quest work: none of value.
- Quest-only question: does the APK emit anything at all on tracking loss, and if
  so in what token — noting that `t5` proves the host would ignore it whatever it
  is.

---

## 8. AgileX QuestArmTeleop (§21)

- Identity: `agilexrobotics/QuestArmTeleop@145b80360cf2c5f2e63179086d0aab2cb563826c`.
- Architecture family: opaque `teleop-debug.apk` (4,865,715 bytes, real binary)
  launched over **ADB**, poses exfiltrated through **Android logcat** lines tagged
  `wE9ryARX` → `oculus_reader.py` → `pub_pose` → `pub_delta_pose` →
  `arm_ik_pose_node` (Pinocchio/CasADi) → `JointState` on `/control/joint_states`
  consumed by the out-of-repo `agx_arm_ctrl` **CAN** driver for AgileX
  Piper/Piper-X/Nero arms.

### Safety register (nothing below was invoked)

All six launch files start the physical arm driver —
`teleop_single_piper`, `teleop_single_piper_x`, `teleop_single_nero`,
`teleop_double_piper`, `teleop_double_piper_x`, `teleop_double_nero` — with
`can_port: can0` / `can_left` / `can_right`, and **four of them set
`auto_enable: "true"`**, which energises the arm on launch.
`pub_delta_pose.py:78,187` publishes actuator commands to `/control/joint_states`
from inside the same node that reads the headset. Constructing `OculusReader()`
has device side effects: ADB discovery, **silent APK install**
(`oculus_reader.py:100-118`) and app launch (`:49`). `pub_pose.py:35` constructs
it in `__init__` with no injection point, so `pub_pose` is not runnable on
synthetic input without patching production code — which was not done.

None of this was executed. Host-side source/build status only, as directed.

### Executed path (representation layer only)

```
synthetic logcat payload strings (harness)
  -> OculusReader.process_data   (upstream @staticmethod, body byte-identical,
     loaded without executing oculus_reader.py's module body, so ppadb is never
     imported and the OculusReader constructor is never reachable)
  -> buttons_parser.parse_buttons   (upstream module, imported as-is)
```

- Harness: [`harness/agilex_wire_parser_runtime.py`](../harness/agilex_wire_parser_runtime.py)
- Raw: `results/runs/agilex_wire_parser_20260914T065929Z/agilex_wire_parser_runtime.jsonl`
- Actual output: `{"status": "PASS", "trials": 6, "passed": 6, "failures": []}`
- The provenance record asserts, and the container enforces: no ADB, no APK
  install or launch, no ROS, no DDS, no CAN, no arm driver, no launch file,
  `--network none`.

### Confirmed

| Trial | Actual result |
| --- | --- |
| `t1_wellformed_record_parses` | `l:<16 floats>|r:<16 floats>&R,L,rightTrig 0.9,…` → two 4×4 matrices, right translation `[0.3, 0.4, 0.5]`, the documented button keys |
| `t2_representation_carries_no_validity_time_or_sequence` | the parsed record is exactly two `(4,4)` ndarrays plus a flat button dict of 15 keys. **Not one key matches `valid`/`track`/`conf`, `time`/`stamp`/`ts`, or `seq`/`session`/`gen`.** I1, I3 and I4 are *structurally absent* at this wire, independently of what the opaque APK knows |
| `t3_short_matrix_silently_dropped` | a 15-float matrix yields an empty dict — the only integrity check is "exactly 16 values parsed" (`oculus_reader.py:168`) |
| `t4_missing_side_is_absence_not_invalidity` | a side that stops tracking is represented by the **absence of its key**, not an invalidity flag; `pub_pose.py:116-118` turns that into an early return, i.e. silence rather than invalidation |
| `t5_repeated_record_is_indistinguishable_after_parse` | a record replayed 250 ms later parses to an identical object. Combined with the overwrite-only `last_transforms` cache (`:194-195`), a frozen source is indistinguishable from a live one at and after this boundary |
| `t6_record_without_separator_returns_none_none` | `process_data` returns `(None, None)` (`:144-145`); `read_logcat_by_line` writes that pair straight into `last_transforms` (`:193-195`), so a parse failure is **not** isolated from the publisher |

### Disposition

I1 structurally absent on the wire, frontend `U` · I2 laterality only
(`'l'`/`'r'`) · I3 structurally absent · I4 structurally absent · I5 not
observable here; the source shows only a host-side A/B button clutch
(`pub_delta_pose.py:194-213`) with **no path by which tracking loss clears the
clutch flag**. Downstream consequence: `NO_OUTPUT` — this run is the
representation layer only and publishes nothing.

- **Evidence level: `E2 SYNTHETIC_RUNTIME`**, bounded to the wire representation.
- **Final status: `QUESTLESS_PARTIAL_COMPLETE`.** Host-side source/build status
  plus a safe unit-level runtime on the two pure upstream functions. The frontend
  remains `OPAQUE_FRONTEND`; no frontend semantics are invented.
- Remaining non-Quest work: none that is safe. Running `pub_pose` on synthetic
  input would require patching production code to inject a source, and every
  other host node is either an actuator-command publisher or requires the
  out-of-repo `agx_arm_description` URDF.
- Quest-only question: does the APK stop emitting a side's `l:`/`r:` pair on
  tracking loss, or does it keep emitting the last matrix? Only the first
  behaviour would give the host any chance of noticing, and even then only as
  silence.

---

## 9. xArm Quest Teleop (§22) — lineage determination

- Identity: `RuiyuWANG/xarm_quest_teleop@822057949c339c4e83ee659a8ffc0addb70474a7`.
- No runtime attempted or needed: this is an identity question, and the repo's
  entry points auto-launch a physical arm (see the safety register below).

### Evidence

**It contains no XR frontend of its own.** A search for `*.cs`, `*.unity`,
`*.prefab`, `*.apk`, `AndroidManifest.xml`, `*.asmdef` and `*.gradle` over the
whole checkout returns **zero files**. The repo is Python plus two catkin
packages.

**It instructs installing and running the other lineage member's software.**
`README.md:20` requires "Meta Quest 2 running the **Quest2ROS app**";
`README.md:42` declares `quest2ros` as a required catkin dependency;
`README.md:113` runs the upstream bridge node verbatim — `rosrun quest2ros
ros2quest.py`; `README.md:112` uses the same ROS-TCP-Endpoint on the same port
`10000` as Quest2ROS2 (`quest2ros2/README.md:99,102-104`). `install.sh` does not
vendor `quest2ros`; it must be supplied externally.

**The ROS wire contract is identical on both sides**, symbol for symbol:
`quest2ros/OVR2ROSInputs` and `OVR2ROSHapticFeedback`
(`src/io/quest2.py:15`, `ros_link/teleop_msgs/msg/OVR2ROSInputsStamped.msg:2`
vs `quest2ros2/Files_for_msg_pkg/msg/OVR2ROSInputs.msg:1-7`,
`q2r2_bringup/robot_arm_controller_base.py:4`); the eight
`/q2r_{left,right}_hand_{pose,twist,inputs,haptic_feedback}` topics
(`src/configs/quest2_config.py:4-12` vs `q2r2_bringup/ros2quest.py:25-52`); and
all six input fields `button_lower`, `button_upper`, `thumb_stick_horizontal`,
`thumb_stick_vertical`, `press_index`, `press_middle`
(`src/io/quest2.py:107-117` vs `Files_for_msg_pkg/msg/OVR2ROSInputs.msg:2-7`).
Quest2ROS2's own README notes the APK hard-codes the package name `quest2ros`,
which is precisely the contract xarm_quest_teleop consumes unchanged.

**The delta is entirely downstream of those topics**: `src/robots/xarm.py` (xArm7
service adapter), `src/teleop/quest_xarm_teleop_sync.py` (deadman, scaling, roll
lock, Cartesian servo), `src/io/quest2.py` (a thin client over the *upstream*
topics), `ros_link/teleop_msgs/` (the one genuine protocol addition — `Stamped`
wrappers that embed `quest2ros/OVR2ROSInputs` as a field type, for
`message_filters` sync), `ros_link/cloudgripper_teleop/scripts/quest_stamped_node.py`
(re-publishes `/q2r_*` → `/q2r_*_stamped`), plus a RealSense/imitation-learning
data-collection and evaluation stack.

### Safety register (nothing run)

`src/configs/teleop_config.py:21-28` hardcodes
`roslaunch xarm_bringup xarm7_server.launch robot_ip:=192.168.1.241 …`;
`:17` hardcodes `tcp_ip:=192.168.0.181`; and `:10-11` set
`auto_launch_quest = True`, `auto_launch_robot = True` — **any bare run of the
teleop or collector scripts attempts to connect to a physical arm.**
`src/tests/test_robot_node.py:24` carries the same live-arm IP inside a "test".
Motion paths: `src/robots/xarm.py:338,477,525` (`/xarm/motion_ctrl`,
`velo_move_line_timed`, `move_servo_cart`); full service set at
`src/configs/robot_config.py:11-21`.

- **Evidence level: `E1`** (lineage determination from pinned source on both sides).
- **Final status: `NON_INDEPENDENT`** — as expected. It shares the Quest2ROS
  opaque frontend **and** the wire contract. For XR-frontend-lineage counting,
  xArm Quest Teleop and Quest2ROS2 collapse to **one** frontend identity; they are
  siblings, not independents.
- Remaining non-Quest work: none. Its genuinely novel surface is the xArm control
  and data-collection layer, which is a robot-control question, not an XR-semantic
  one, and is not safely runnable here.
- Quest-only question: none of its own. Any frontend question is the Quest2ROS
  question, already tracked under that identity.

---

## 10. Nakama VR_Teleop_Interface (§22) — identity determination

- Identity as pinned: `nakama-lab/VR_Teleop_Interface@aebf6394a16d9ee9b95aaa209c59f9788cb038bb` (`main`).

### At the pinned revision: confirmed zero implementation

Complete file inventory (11 files, excluding `.git`), verified directly:
`README.md`, `LICENSE`, `.gitignore`, `.github/workflows/ci.yml`,
`docs/genaral_diagram.md`, and six `docs/SequenceDiagrams/*.md`. There is no
`.cs`, `.py`, `.cpp`, `.launch`, `package.xml`, `CMakeLists.txt`, Unity project or
Dockerfile. `ci.yml:19-24` builds a `Dockerfile` that does not exist in the tree
and checks the repo out to `src/franka_ros2` — a vestigial copy of the upstream
franka_ros2 workflow that cannot build anything here; `ci.yml:4-6` triggers only
on branches `humble`/`develop`, neither of which exists.

### Correction to the prior finding

The existing `frameworks/nakama/RESEARCH_UTILITY.md` states that no other branch
exists "locally **or on this origin**". The second half is wrong: it is an
artifact of the single-branch clone refspec. `git ls-remote --heads --tags
origin` (read-only, no fetch) returns:

```
42423499131e8d77df1bb281b30f71ff105a4e1d  refs/heads/aorus_zed
05cf127ab981c9bbfc7d22387778680ab1346e9c  refs/heads/cubi
aebf6394a16d9ee9b95aaa209c59f9788cb038bb  refs/heads/main
18a374facc4bf4afa224b603a44d64edc100c578  refs/heads/unity_vr
```

(no tags). Three implementation branches do exist on this origin. Their contents
are **unverified** — they were not fetched — but their SHAs are now pinned above.
The README compounds the ambiguity: its own branch table
(`README.md:81-83,92`) links every implementation branch to a **different
account's fork**, `JuanR5/VR_Teleop_Interface`, including a deep link to
`blob/unity_vr/Assets/scripts/sshRunner.cs`. Which of the two is authoritative is
unresolved.

For the record, the claimed system (`README.md:5,10-14,29-32,127-131`) is a
Franka Research 3 with gripper and a Botasys SenseONE F/T sensor, a ZED2 stereo
camera, and a Quest 2 over ROS 2 Humble + Unity + Docker, with topics
`controller_movement` (Twist), `gripper_command`, `zed2_unity` stereo images and
`rumble_output`. That contract is **unrelated** to the Quest2ROS `/q2r_*` family,
so if an implementation is ever pinned it would be a genuinely independent
lineage.

- **Evidence level: `E0 DISCOVERED`.**
- **Final status: `SOURCE_PATH_UNCONFIRMED`** — but for a narrower and more
  actionable reason than previously recorded. The correct statement is "pinned to
  a ref that holds no implementation", not "no code exists". Semantic
  observability and control depth remain NOT AUDITABLE at this revision.
- Remaining non-Quest work, if this identity is ever promoted out of `DROP`:
  re-pin to `unity_vr@18a374fa` for the XR frontend and `cubi@05cf127a` for the
  Franka control side, cross-check against `JuanR5/VR_Teleop_Interface` to decide
  which is upstream, then re-audit. Note the Franka branch is a physical-robot
  control path and inherits the standard hardware boundary.
- Quest-only question: none until an implementation ref is pinned.

---

## Cross-cutting observations

**One design carries a validity bit to the ROS wire; none carries a tracked
bit.** NVIDIA is the only framework in this set that serialises validity into the
ROS message (`NamedPoseArray.is_valid`) *and* suppresses the TF for an invalid
side — both now executed, not inferred. Even NVIDIA declares
`head_is_tracked` in its own schema and then never reads or transmits it, so
*valid-but-inferred* is indistinguishable from *valid-and-actively-tracked*
everywhere in this population.

**Two distinct failure shapes for I1 at the serialization boundary.** In NU-MECH
and AgileX the validity bit is *unrepresentable* — the wire format has no field
for it, and in NU-MECH's case a validity token is actively corrupted into a joint
angle. In Legged, Homebrew and xiaoxiaoxh the bit is *computed and then
discarded*: Homebrew is the sharpest citation, since it computes a `modeStr`
naming the tracking mode, writes it to a local recording, and omits it from the
published message while substituting origin-identity poses on the wire.

**I3 splits the population three ways, all now runtime-checked where runnable.**
Dropped and re-stamped with the receiver clock (LTS0429, NU-MECH structurally,
NVIDIA's EE header); never present at all (Legged — every header ships
`stamp = 0`); or carried verbatim and never enforced (XRoboToolkit, where a
1970-era timestamp publishes unchanged; Homebrew, which carries a real NTP/ROS
stamp but of send time, not sample time, and withholds its own sync-quality
flags).

**I4 is absent almost everywhere.** Only Homebrew has any session concept, and it
lives in a URL and an out-of-band best-effort topic rather than in the payload —
so a consumer reading the pose topics alone still cannot detect a reconnect.

**Opacity is not the same as unexaminable.** Three of the four repositories
previously written off as opaque (LTS0429, AgileX, XRoboToolkit) yielded real
runtime evidence once the examination was aimed at the open half — the host
parser, the representation layer, or the publisher behind an inert SDK
substitute — while leaving the frontend boundary explicitly unclaimed.
