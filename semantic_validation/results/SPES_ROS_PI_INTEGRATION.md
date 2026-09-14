# Spes — accepted callback -> ROS 2 publisher -> actual DDS -> physical Raspberry Pi

**Run A (research adapter, canonical for §§2-5):** `spes_ros_pi_20260914T064625Z`
**Run B (pinned upstream ROS module, see §5A):** `spes_upstream_ros2_pi_20260914T065253Z`
**Run C (hardware-day orchestration dry-run, see §5B):** `spes_upstream_ros2_pi_20260914T073500Z`
**Discarded-but-preserved prior attempt:** `spes_ros_pi_20260914T064532Z` (DDS discovery race, see §7)
**Executed:** 2026-09-14 UTC, this session, on the real testbed.
**Pinned target:** `SpesRobotics/teleop` @ `c5d808155a87b584d6147a5943d4b87c34c92db0`,
`semantic_validation/targets/spes_teleop`, worktree clean before **and** after every run.

---

## 0. What Spes is and is not — read before citing anything below

**Spes is NOT a native XR->ROS framework, and this section must be read precisely.**

The Spes control path proper terminates at a Python callback (`Teleop.subscribe`,
`teleop/__init__.py:204-214`). Two distinct ROS hops were executed this session and they have
**different provenance**:

| Run | ROS publisher | Provenance |
| --- | --- | --- |
| **A** | `SpesRosCallbackAdapter` | **RESEARCH-CREATED** — `semantic_validation/harness/spes_ros_callback_adapter.py` |
| **B** | `teleop/ros2/__main__.py` | **PINNED UPSTREAM SPES PRODUCTION SOURCE**, unmodified |

Correction to earlier project framing: the pinned Spes repository **does** contain an optional
ROS 2 module with its own `rclpy` publisher (`teleop/ros2/__main__.py:88` creates the publisher,
`:141` publishes). Run B executed it for real. Earlier notes describing Spes's ROS output as
existing "only through a research-created adapter" understated the source inventory; the accurate
statement is below.

Even with Run B, Spes **still** must not be counted toward "native XR->ROS implementations",
because:

- the XR frontend is a **WebXR browser page**, and in both runs the source was a synthetic WSS
  packet injected *after* that frontend — so no native XR tracking decision was exercised;
- upstream's own ROS module is an **optional example entrypoint** that refuses to publish until a
  robot supplies `/current_pose` (`teleop/ros2/__main__.py:121`); it was only runnable here via
  upstream's own `--omit-current-pose` escape hatch;
- neither run observed a native downstream consumer.

Spes's roles are unchanged: `MOTIVATING_XR_CONTROL_CASE` and
`RESEARCH_ADAPTED_ROS_PROPAGATION_CASE`, with Run B adding
`UPSTREAM_OPTIONAL_ROS_MODULE_EXECUTED` as a source-provenance fact, not as a native-XR claim.

`PI_RECEIVED != NATIVE CONSUMER ACCEPTED`. The Pi endpoint's `accept_decision` field is hardcoded
to `ACCEPTED_NO_SEMANTIC_GATING`; it is an observation sink, not a controller.

---

## 1. Classification

| Axis | Value |
| --- | --- |
| Evidence level | **E2 `SYNTHETIC_RUNTIME`** |
| Replay subclass | **`BOUNDARY_LIMITED_REPLAY`** — injection is at the WSS packet, i.e. downstream of the WebXR browser frontend and of every native tracking/validity decision |
| Semantic disposition (I1 tracking validity) | **`N/A` at this boundary** — no tracking semantic exists in the accepted callback to preserve, transform, or drop |
| Semantic disposition (I3 source time) | **`DROPPED`** — the ROS header stamp is the desktop clock at publish, not a source timestamp |
| Downstream consequence | **`PI_RECEIVED`** |
| XR hardware used | **No** |
| Physical robot / driver / actuator used | **No** |
| Native XR->ROS framework | **No** — see §0. Run A's publisher is research-created; Run B's is an optional upstream module, but both were fed a synthetic post-frontend source |

---

## 2. Path actually executed

```text
harness-authored WSS packet sequence            [SYNTHETIC SOURCE, research-created]
  -> wss://127.0.0.1:<ephemeral>/ws             [PINNED: teleop/__init__.py:298-311, uvicorn+FastAPI]
  -> Teleop.__update(message)                   [PINNED: teleop/__init__.py:220-285]
       pose-jump gate                           [PINNED: teleop/__init__.py:247-256]
       relative/absolute anchor + target maths  [PINNED: teleop/__init__.py:258-283]
  -> Teleop.__notify_subscribers(pose, message) [PINNED: teleop/__init__.py:216-218, 285]
       callback #1 ServerObserver._subscriber_callback   [RESEARCH: spes_hardware_server.py:231,240]
       callback #2 SpesRosCallbackAdapter.callback       [RESEARCH: spes_ros_pi_smoke.py:88]
  -> rclpy Publisher(PoseStamped, /robot_target_pose)    [RESEARCH: spes_ros_pi_smoke.py:75]
  -> actual ROS 2 Humble / rmw_fastrtps_cpp, ROS_DOMAIN_ID=74, ROS_LOCALHOST_ONLY=0
  -> dedicated research Ethernet: desktop enp3s0f1 10.10.10.1/24 -> Pi eth0 10.10.10.2/24
  -> semantic_robot_sink on physical Raspberry Pi `rosxr`                [OBSERVATION ENDPOINT]
       accept_decision = ACCEPTED_NO_SEMANTIC_GATING  (hardcoded)
X  no robot, no driver, no actuator, no native Spes consumer
```

Confirmed that the DDS traffic really crossed the dedicated link: on the Pi the only non-loopback
interface up during the run was `eth0 10.10.10.2/24` (`usb0` was down), and the desktop route to it
is `10.10.10.2 dev enp3s0f1 src 10.10.10.1`.

### Execution environment (actual)

- Desktop container image `ros-xr-humble:local`, ROS 2 Humble.
- `docker run --rm --network host --cap-drop ALL --security-opt no-new-privileges
  --user 1000:1000 -e ROS_DOMAIN_ID=74 -e RMW_IMPLEMENTATION=rmw_fastrtps_cpp
  -e ROS_LOCALHOST_ONLY=0 -e HOME=/tmp/spes-home -v /home/cclab/ros_xr:/repo`.
  Docker reached via `sg docker -c '<command>'` — the blocker recorded in
  `NEXT_PHASE_STATUS.md` ("Docker daemon socket inaccessible") is resolved by that path with **no**
  socket, group, or system modification.
- Pi sink launched over `ssh rosxr` with the same `ROS_DOMAIN_ID=74` /
  `RMW_IMPLEMENTATION=rmw_fastrtps_cpp` / `ROS_LOCALHOST_ONLY=0`, and
  `-p log_dir:=/home/cclab/spes_logs/spes_ros_pi_20260914T064625Z` — an **absolute** path.
  A leading `~` inside a ROS `-p name:=value` argument is not tilde-expanded and would create a
  literal `~` directory; the Pi home was checked after the run and contains no such directory.

### Actual input

30 WSS pose packets, `move=true`, `device="VR"`, `scale=1.0`, identity orientation, position
stepping `y = 0.00, 0.02, ... 0.58` m, sent at ~0.1 s intervals. The 0.02 m step is deliberately
below the pinned 0.05 m pose-jump tolerance (`teleop/__init__.py:250`) so every packet is accepted
by the production calculation rather than rejected by it.

---

## 3. Actual outputs — published vs received

| Stage | Count | Source of the number |
| --- | --- | --- |
| WSS packets sent | 30 | harness |
| Pinned `Teleop.__update` invocations (`server_update_index` final) | **30** | `desktop/server.jsonl`, `desktop/adapter.jsonl` |
| Accepted production callbacks (`__notify_subscribers`) | **30** | `desktop/adapter.jsonl` |
| ROS `PoseStamped` publishes on `/robot_target_pose` | **30** | `desktop/adapter.jsonl` (one record written per publish) |
| Messages received by the Pi `semantic_robot_sink` | **30** | `pi_sink.jsonl`, `receive_count_for_topic` 1..30 |
| Correlated 1:1 with matching pose | **30 / 30** | `correlation.json` |
| Missing adapter events | **0** | `correlation.json` |
| Pose value mismatches (tolerance 1e-9 on x,y,z) | **0** | `correlation.json` |

`correlation.json` `result: PASS`; `summary.json` `status: PASS`.

Timing (all from the raw JSONL):

- Pinned-callback entry -> adapter `publish()` return: min 0.160 ms, median 0.183 ms, max 0.371 ms
  (single-process monotonic clock, so this delta is meaningful).
- Desktop publish wall time -> Pi receive wall time: 6578.5 / 6579.1 / 6579.5 ms
  (min/median/max). **This is not latency.** The desktop and Pi wall clocks are not synchronized —
  a direct comparison taken after the run showed the offset had itself changed to ~8.85 s, i.e. the
  Pi clock is free-running and drifting. The only defensible reading of this column is that the
  *spread* is ~1.0 ms across 30 messages, which bounds relative delivery jitter; the absolute value
  is clock offset, not transport delay.

---

## 4. How correlation was established — and its exact limit

A standard `geometry_msgs/msg/PoseStamped` **carries no injected correlation identifier.** The
adapter deliberately does not add one, because adding one would change the message the downstream
sees and would misrepresent what a Spes-derived ROS stream looks like. The Pi sink records this
explicitly: every one of the 30 Pi records has `sequence_or_correlation_id: null`.

Correlation was therefore established by three independent, *out-of-band* agreements, all of which
had to hold simultaneously:

1. **`header.stamp` as a de-facto join key.** The adapter logs, side-band, the exact
   `(sec, nanosec)` it stamped for each publish. All 30 adapter stamps are distinct, and all 30 Pi
   stamps are distinct. `analyze_spes_ros_pi.py` joins on that pair and found a unique partner for
   every adapter event. This is *incidental* uniqueness of a timestamp, **not** an identifier: two
   publishes inside the same nanosecond would be indistinguishable, and a re-stamping intermediary
   would destroy the join. It happens to be injective here; it is not guaranteed to be.
2. **Ordering.** The Pi's per-topic monotonic counter `receive_count_for_topic` runs 1..30 and its
   sequence of header stamps is identical to the adapter's publish order. No reordering, no
   duplication, no gap.
3. **Payload agreement.** For each joined pair the Pi's `position.{x,y,z}` equals the adapter's
   logged `accepted_target` to <1e-9, and `frame_id` is `spes_accepted_target` on all 30.

The side-band chain that is genuinely carried end to end in the *logs* (never in the ROS message)
is: `run_id` -> `adapter_local_event_id` (1..30) -> `server_update_index` (1..30, from the wrapped
pinned `__update`) -> `callback_monotonic_ns` -> `adapter_publish_monotonic_ns` ->
`ros_header_stamp` -> Pi `header_stamp` + `receive_count_for_topic` + `receive_monotonic_time`.

`adapter_local_event_id == server_update_index` for all 30 records, which confirms that exactly one
accepted callback (and therefore exactly one publish) was produced per pinned `__update` — no
coalescing and no duplicate emission.

**Limit:** because the join key is a timestamp and not an identifier, this establishes correlation
*for this run's observed data*, not an in-band traceability property of the message type. Any claim
of the form "the ROS message carries provenance" is false and must not be made.

---

## 5. Adapter provenance — pinned production vs research-created

This section is verified from source, not assumed.

### Pinned upstream Spes production code (must not be modified; unmodified here)

| Element | Location |
| --- | --- |
| WSS endpoint that receives the packet and calls the control path | `targets/spes_teleop/teleop/__init__.py:298-311` (`__update(message["data"])` at :309) |
| Control calculation | `targets/spes_teleop/teleop/__init__.py:220-285` |
| Pose-jump gate (the only gate on this path) | `targets/spes_teleop/teleop/__init__.py:247-256` |
| Relative/absolute anchor handling | `targets/spes_teleop/teleop/__init__.py:258-268` |
| Subscriber registry | `targets/spes_teleop/teleop/__init__.py:204-214` (`self.__callbacks.append(callback)` at :214) |
| Subscriber dispatch | `targets/spes_teleop/teleop/__init__.py:216-218`, called at `:234` (the `not move` branch) and `:285` (the accepted-target branch) |

Git worktree of `targets/spes_teleop` was clean before the run and clean after it
(`environment.jsonl` `target_provenance` / `target_clean_after`).

### Research-created (this project; clearly labelled)

| Element | Location |
| --- | --- |
| The ROS adapter itself | `harness/spes_ros_callback_adapter.py` (whole file) |
| Non-invasive observer wrapping `__update` | `harness/spes_hardware_server.py:213-376` |
| Run driver: WSS client, rclpy node, container/Pi orchestration | `harness/spes_ros_pi_smoke.py`, `harness/spes_ros_pi_runtime.py` |
| Correlation analyzer | `harness/analyze_spes_ros_pi.py` |
| Pi observation sink | `~/ros2_ws/src/semantic_robot_endpoint/` on `rosxr` |

### Verified property 1 — the adapter publishes only AFTER the accepted pinned callback

`__notify_subscribers` (`teleop/__init__.py:216-218`) iterates `self.__callbacks` in registration
order and is invoked as the **final statement** of the accepted branch of `__update`
(`teleop/__init__.py:285`), i.e. after the pose-jump gate at `:247-256` and after
`self.__pose` has been assigned its final value at `:276-283`. The adapter's `callback` is
registered at `spes_ros_pi_smoke.py:88`, *after* `ServerObserver` registers its own subscriber at
`spes_hardware_server.py:231`. `rclpy` `publisher.publish(message)` is called at
`spes_ros_callback_adapter.py:94`, inside that callback. There is no other publish site in the
adapter. Therefore a ROS message can only exist if the pinned code already accepted the update and
computed a target.

This is also confirmed empirically by the counts: `server_update_index` equals
`adapter_local_event_id` on all 30 records — never a publish without a preceding pinned update.

### Verified property 2 — the adapter does not modify production payloads

Reading `spes_ros_callback_adapter.py:78-114` in full:

- `pose` is consumed read-only. `_pose_dict` (`:65-76`) only reads `pose[:3,:3]` and `pose[:3,3]`
  and calls `t3d.quaternions.mat2quat`; no assignment into `pose` occurs anywhere in the file.
- `params` (the production `message` dict) is read only via `params.get("move")` at `:113`. There is
  no `params[...] = ...`, no `.update(`, no `.pop(`, no `del` in the file.
- The only object mutated is the adapter's own freshly constructed `PoseStamped`
  (`self.pose_factory()` at `:82`).
- The adapter registers a *subscriber*; it does not replace, wrap, or monkey-patch any pinned
  method. (`ServerObserver` does wrap `__update` at `spes_hardware_server.py:232`, but it calls
  `self.original_update(message)` unchanged at `:314` and only records around it.)
- The adapter writes no tracking semantic and no source timestamp, and says so in its own records:
  `source_timestamp_preserved: false`, `tracking_semantic_added: false`,
  `production_schema_modified: false`.

### What the adapter demonstrably does NOT carry

The accepted Spes callback exposes a 4x4 target pose and the raw WSS message. It contains no
tracking-validity field, no `emulatedPosition`, no source identity, no source timestamp, and no
session generation. The adapter therefore cannot forward any of those, and the emitted
`PoseStamped` has only `header.stamp` = desktop clock at publish and
`header.frame_id = "spes_accepted_target"` (a research-chosen label, not an upstream frame).

---

## 5A. Run B — the PINNED UPSTREAM Spes ROS 2 module, executed end to end

Run id `spes_upstream_ros2_pi_20260914T065253Z`. Driver:
`semantic_validation/harness/spes_upstream_ros2_pi.py` (research-created orchestration only).

### What ran

`python3 -m teleop.ros2 --omit-current-pose --host 127.0.0.1 --port 4453 --ros-args -r
target_frame:=/robot_target_pose`, executed from the pinned checkout inside `ros-xr-humble:local`
with `ROS_DOMAIN_ID=74`. Only upstream's own CLI flags and a standard ROS topic remap were used.
The pinned worktree was clean before and after.

**The `/current_pose` gate and how it was satisfied honestly.** Upstream refuses to publish while
`current_robot_pose_message is None` (`teleop/ros2/__main__.py:121`); that value normally comes
from a robot publishing `/current_pose` (subscription at `:143-145`). Rather than fabricate a fake
robot publisher, the run used upstream's **own** `--omit-current-pose` flag (`:46`, applied at `:83-86`), which upstream provides for exactly this case. No `/current_pose` message was
fabricated, no robot, driver, or controller was started, and the flag is upstream behaviour, not a
modification.

### Counts

| Stage | Count |
| --- | --- |
| Synthetic WSS packets sent | 30 |
| `PoseStamped` observed on `/robot_target_pose` by an independent in-container ROS subscriber | **30** |
| Received by the Pi `semantic_robot_sink` | **30** |
| Observed desktop stamps also found on the Pi | **30 / 30** |
| Desktop header stamps unique / Pi header stamps unique | yes / yes |

`summary.json` `status: PASS`.

### What Run B adds over Run A

- The ROS publisher is **upstream production code**, so the `PoseStamped` shape is upstream's
  choice, not the research adapter's. Observed `frame_id` on the Pi is **`link_base`** — hardcoded
  by upstream at `teleop/ros2/__main__.py:132`, not derived from any XR reference frame.
- Upstream re-stamps with `node.get_clock().now()` at `:131` (and `:103` for TF). This independently
  confirms, from production source rather than from the research adapter, that **no source
  timestamp survives to ROS** (I3 `DROPPED`).
- The upstream message carries no tracking-validity field, no source identity and no session
  generation — the Pi recorded `semantic_metadata: null` and `sequence_or_correlation_id: null` on
  all 30 records, exactly as in Run A.
- Upstream also broadcasts TF `base_link -> teleop_target` (`:103-114`). This run deliberately
  pointed the sink at `/tf_unused_by_this_run`, so **TF reception was not observed** and no claim
  is made about it.

### What Run B does NOT add

It is still a synthetic post-frontend source, so it is still E2 `BOUNDARY_LIMITED_REPLAY` and still
provides no native XR evidence. It is not an E5 upgrade.

---

## 5B. Hardware-day orchestration dry-run — fresh execution

Run id `spes_upstream_ros2_pi_20260914T073500Z` was executed after the hardware-day procedure
was frozen. It used the same pinned upstream module and physical Pi observation endpoint as Run B,
with 30 synthetic post-browser WSS packets at 0.1 s intervals.

The actual path completed:

```text
synthetic WSS input
-> pinned production Spes server/control path
-> pinned teleop/ros2 rclpy publisher
-> /robot_target_pose PoseStamped
-> Fast DDS domain 74 over the dedicated Ethernet
-> physical Pi semantic_robot_sink
```

Observed counts were **30 WSS sent / 30 desktop ROS publishes / 30 Pi receives**. All 30 desktop
header stamps were unique and found on the Pi; all desktop/Pi poses were equal, ordered, and used
the upstream `link_base` frame. The target checkout was clean before and after at
`c5d808155a87b584d6147a5943d4b87c34c92db0`.

`validate_spes_native_ros_pi_run.py` assigned explicit immutable correlation labels
`spes_upstream_ros2_pi_20260914T073500Z:packet-001` through `:packet-030` in the evidence file.
These are research-side trial IDs joined by ordered input index and the unique upstream ROS header
stamp; they are not fields added to the production message. Production still emitted
`sequence_or_correlation_id: null` at the Pi.

Operational checks also passed:

- rerunning the orchestrator with the same run ID exited `1` and refused to overwrite the run;
- rerunning the validator against its existing output exited `1` and refused to overwrite it;
- post-run process counts were zero for both the desktop test container and Pi
  `semantic_robot_sink`;
- no Quest, robot, driver, controller, or actuator was used.

This fresh run remains `E2 BOUNDARY_LIMITED_REPLAY` and its terminal consequence remains only
`PI_RECEIVED`. It validates the Quest-free production-server-to-native-publisher-to-Pi leg and
hardware-day orchestration; it does not join that leg to an actual Quest input.

---

## 6. Confirmed vs unconfirmed

### Confirmed by this run

1. The pinned Spes WSS server, `Teleop.__update`, its pose-jump gate and its target calculation
   execute for real inside a ROS 2 Humble container, with the pinned worktree unmodified.
2. Every accepted production callback produced exactly one ROS 2 `PoseStamped` publish: 30/30.
3. All 30 publishes crossed actual ROS 2 / Fast DDS over the dedicated 10.10.10.0/24 Ethernet and
   were received by an observation node on a physically separate computer: 30/30, ordered,
   no loss, no duplication, pose-identical.
4. The research adapter publishes strictly after the pinned acceptance decision and does not mutate
   the production pose or message (source-verified, §5).
5. The emitted ROS message carries no correlation identifier and no tracking semantic — confirmed
   on the receiving side, where `sequence_or_correlation_id` and `semantic_metadata` are `null` on
   all 30 records of both runs.
6. (Run B) The **pinned upstream** optional ROS 2 module `teleop/ros2/__main__.py` also ran for
   real and delivered 30/30 to the same Pi endpoint, with `frame_id` hardcoded to `link_base` and
   the header re-stamped from the desktop clock — an upstream-source confirmation that no source
   timestamp and no tracking semantic reach ROS.

### NOT confirmed by this run (do not claim)

1. Nothing about **native XR** behaviour at the ROS boundary. Run B does show that an upstream Spes
   ROS publisher exists and runs, but it was fed a synthetic post-frontend source and required
   upstream's `--omit-current-pose` flag because no robot was present. Do not restate either run as
   "Spes natively delivers XR data to ROS".
2. Nothing about XR tracking-state propagation. The source was synthetic and entered *after* the
   browser/WebXR frontend, so every native tracking decision was bypassed —
   `BOUNDARY_LIMITED_REPLAY`.
3. Nothing about downstream acceptance or actionability. The Pi sink has no gate, no controller and
   no actuator; `PI_RECEIVED` only.
4. No latency claim across hosts — the wall clocks are unsynchronized (§3).
5. No TF claim. Upstream broadcasts `base_link -> teleop_target`, but the sink was pointed away
   from `/tf` in both runs, so no TF message was observed.
6. No E5/E6 upgrade of any kind.

---

## 7. Honest record of the first attempt

The first execution (`spes_ros_pi_20260914T064532Z`, preserved in full) published 30 and the Pi
received **4**. Cause: cross-host DDS discovery had not completed when the harness began sending,
so the first 26 publishes left before the remote reader was matched. This is a transport/discovery
artifact of the harness, **not** a semantic finding, and must never be cited as message loss.

Fix applied to `spes_ros_pi_smoke.py`: `--require-subscribers` blocks on
`publisher.get_subscription_count()` reaching the required count (plus a 1 s settle) before the
first WSS packet is sent. The canonical run used `--require-subscribers 1`. Both run directories
are kept so the artifact is auditable.

---

## 8. Quest hardware readiness — actually re-executed this session

| Check | Command actually run | Result |
| --- | --- | --- |
| Adapter schema self-test, inside the ROS container | `python3 harness/spes_ros_callback_adapter.py --self-test` | `PASS` |
| Full hardware preflight | `python3 harness/run_spes_hardware_preflight.py` | `PASS`, all 9 checks |
| Orchestration start | `./start_quest_experiment.sh spes_quest_readiness_20260914T0650Z 4443` | `SERVER=RUNNING`, `BACKEND=systemd_user`, `QUEST_URL=https://10.80.79.38:4443/` |
| Live endpoint probe (auto-run by start) | `harness/probe_spes_server.py` | `PASS` — `https`, `production_wss`, `experiment_wss` all true |
| Orchestration status | `./status_quest_experiment.sh` | reports PID/RUN_ID/QUEST_URL/unit correctly |
| Orchestration stop | `./stop_quest_experiment.sh` | `SERVER=STOPPED` |

Preflight sub-checks all `passed: true`: `prepare_instrumented_frontend`,
`frontend_control_payload_equivalence`, `quest_operator_hud_audio_left_control`,
`server_observer_actual_update`, `https_production_wss_experiment_wss_ack`,
`uvicorn_websocket_backend`, `python_syntax`, `upstream_target_clean_fixed_revision`,
`docker_daemon_access`.

One preflight change was made this session: `docker_daemon_access` previously always reported
`ROS_DUMMY_SINK_BLOCKED` because it invoked bare `docker info`. It now falls back to
`sg docker -c 'docker info'` and records which path succeeded
(`access_path: "SG_DOCKER"`). No socket permission, group membership, or system configuration was
changed. The check is advisory and does not gate the preflight verdict.

`launch_spes_quest_experiment.sh` is a thin compatibility shim
(`launch_spes_quest_experiment.sh:7`) that execs `start_quest_experiment.sh`; it works.

**Trials and stop conditions for the final hardware day** (already documented, unchanged):
`frameworks/spes/EXPERIMENT_T1.md` — produce a 3-5 s controller degradation without focus loss,
hold 1-2 s after the first native transition, recover, observe 5-10 s, repeated for **five valid
raw transitions**. `frameworks/spes/EXPECTED_OBSERVABLES.md` defines the correlation join fields
and restates that `PoseStamped` carries no experiment ID.

**Topics for the final hardware day:** `/robot_target_pose` (`geometry_msgs/msg/PoseStamped`) only,
`ROS_DOMAIN_ID=74`, Pi sink `-p tf_topic:=/tf_unused_by_this_run` and an absolute
`-p log_dir:=/home/cclab/spes_logs/<run_id>`.

**Gap the hardware day must close in development, stated plainly:** the Quest orchestration
(`start_quest_experiment.sh` -> `spes_hardware_server.py`) does **not** currently attach the ROS
adapter — it runs the WSS server and observer only. Joining the hardware path to the ROS/Pi path
requires wiring `SpesRosCallbackAdapter` into `spes_hardware_server.py` the same way
`spes_ros_pi_smoke.py:80-88` does, and running that server inside the ROS container. That is a
small, fully specified integration, but it is not zero: it has not been executed, so it is listed
here as remaining work rather than claimed as ready.

---

## 9. The exact remaining Quest-only question

> When an **actual** Meta Quest 3 controller enters the emulated/inferred tracking interval
> (`emulatedPosition=true`, `source=CONTROLLER`, `move=true`) while the WebXR frontend keeps
> streaming, does a ROS publisher attached to the same pinned accepted callback proven here —
> either the research adapter (Run A) or upstream `teleop.ros2` (Run B) — continue emitting
> `PoseStamped` on `/robot_target_pose` across that interval, and does the
> physically separate Pi sink continue receiving it, with no marker on the ROS side distinguishing
> emulated-tracking messages from actively-tracked ones?

The hardware half of this is already answered and **must not be re-run**: the existing canonical
result (`SPES_QUEST_HW_RESULT.md`, `SPES_HW_QUANTITATIVE_SUMMARY.md`, `SPES_HW_REANALYSIS.md`)
records 5/5 valid Quest 3 trials in which the controller pose stayed non-null with
`emulatedPosition=true`, the production packet omitted that tracking semantic, the pinned server
target callback continued (5/5 `HW_EMULATED_CONTINUES`), and recovery occurred 5/5 without user
release/re-press.

These runs supply the other half — that an accepted callback propagates 1:1 to a physically
separate ROS endpoint, through both a research adapter (Run A) and the pinned upstream ROS module
(Run B) — under a synthetic source. **The two halves have not been joined in a single execution.**
Joining them requires an authorized Quest 3 plus the small, fully specified wiring noted at the end
of §8; every other component has now been executed for real.

---

## 10. Artifacts

```
semantic_validation/results/runs/spes_ros_pi_20260914T064625Z/
  summary.json                 machine-readable verdict and counts
  correlation.json             30/30 matched, 0 missing, 0 mismatches
  environment.jsonl            target provenance, safety register, exact commands
  desktop/adapter.jsonl        30 research-adapter publish records (side-band correlation chain)
  desktop/server.jsonl         pinned-__update observation records
  desktop/summary.json         desktop-side smoke summary
  pi_sink.jsonl                30 Pi reception records (copied back from the Pi)
  pi_sink.stdout.txt           Pi sink console output
  container.stdout.txt / container.stderr.txt
  analyze.stdout.txt

semantic_validation/results/runs/spes_upstream_ros2_pi_20260914T065253Z/   (Run B, §5A)
  summary.json                 30 sent / 30 published / 30 received, PASS
  desktop.jsonl                WSS send records + independent desktop ROS observations
  pi_sink.jsonl                30 Pi reception records, frame_id link_base
  environment.jsonl            provenance + safety register (no fabricated /current_pose)
  client.py                    the in-container WSS client / observer used by Run B
  container.stdout.txt / container.stderr.txt / pi_sink.stdout.txt

semantic_validation/results/runs/spes_upstream_ros2_pi_20260914T073500Z/   (Run C, §5B)
  summary.json                 fresh 30/30/30 PASS
  desktop.jsonl / pi_sink.jsonl
  correlation_validation.json explicit run/trial IDs and shutdown/overwrite checks
  environment.jsonl / client.py / process logs

semantic_validation/results/runs/spes_ros_pi_20260914T064532Z/   (preserved failed attempt, §7)

semantic_validation/harness/spes_ros_pi_runtime.py               (new, research-created driver, Run A)
semantic_validation/harness/spes_upstream_ros2_pi.py             (new, research-created driver, Run B)
semantic_validation/harness/validate_spes_native_ros_pi_run.py   (Run C artifact validator)
semantic_validation/harness/spes_ros_pi_smoke.py                 (extended: pose count, discovery wait)
semantic_validation/harness/run_spes_hardware_preflight.py       (docker check now sg-aware)
```

Pi-side originals remain at `rosxr:/home/cclab/spes_logs/spes_ros_pi_20260914T064625Z/` and
`rosxr:/home/cclab/spes_logs/spes_upstream_ros2_pi_20260914T065253Z/`, with the fresh Run C copy at
`rosxr:/home/cclab/spes_logs/spes_upstream_ros2_pi_20260914T073500Z/`.

No secrets, keys, or tokens are present in any artifact. The self-signed cert/key used by the
pinned Spes server are the upstream repository's own test materials and were not added, copied, or
regenerated by this work.

---

## 11. Final questless status

**`QUESTLESS_RUNTIME_COMPLETE`**

Justification: every component of the Spes path that can be executed without a Meta Quest has now
been executed for real — the pinned WSS server and control calculation, **both** ROS publishers
(the research adapter in Run A and the pinned upstream `teleop.ros2` module in Run B), actual
ROS 2/Fast DDS transport, the dedicated Ethernet, and reception on a physically separate Raspberry
Pi — each with a 30/30 published-to-received result and the pinned worktree unmodified. The Quest
orchestration, preflight and live probe were also re-executed and pass. The remaining open item
(§9) is gated on Quest hardware; the one non-Quest gap is the small adapter-into-hardware-server
wiring stated plainly at the end of §8, which is specified but not yet executed. The status does
**not** assert native XR->ROS behaviour, which Spes does not have.
