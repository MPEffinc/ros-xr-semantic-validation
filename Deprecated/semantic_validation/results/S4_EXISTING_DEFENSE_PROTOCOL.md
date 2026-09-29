# S4-A: existing-defense comparison protocol

Protocol ID: **XRROS-S4-1.0.0**. Registered 2026-09-22 UTC against research
commit `1ffad59bcae0a5c9561f3509882d320be832d17e`. S4-A: **DONE**;
S4-B: **NOT_STARTED**. This is a protocol and source/feasibility investigation,
not a defense implementation or a defense runtime result.

## 1. Purpose, freeze, and authority

The eventual research objective is a new defense-framework paper **if the
evidence warrants it**. S4 asks whether existing source checks, ROSMonitoring,
or direct validation already satisfy a stated teleoperation policy when given
the required information. A missing field, a different policy, an unavailable
dependency, or a failed integration is not proof of a new method gap.

This file is the complete normative protocol. Its SHA-256 is stored in
`S4_EXISTING_DEFENSE_PROTOCOL.sha256` and the status board, outside the hashed
file to avoid self-reference. The commit containing that digest is the freeze
point. S4-B must verify the digest before implementation and each run. Preserve
this version after any S4-B results exist. An unavoidable change requires a
new version/file, a public reason and a separate preregistration commit before
affected results; it cannot replace unsuccessful cases or thresholds. Report
both versions and all attempts. Dependency locks, generated configuration and
instrumentation patches must be frozen before the first comparative trial;
they may instantiate this protocol, not change its policy or endpoints.

S4-B requires the user's review/approval after this commit. No S4-B monitor,
oracle, adapter, gate, Gazebo experiment, or new framework was implemented or
run during S4-A. Existing containers were queried only for image/Python/ROS
directory/dependency metadata. Existing source and evidence were not edited.

## 2. S0–S3 evidence and remaining questions

Read with `P0_INVENTORY.md`, `S1_TRACE_AUDIT.md`,
`S2_DOCKER_CONTROL_BASELINE.md`, and `S3_OPENVR_CONTROL_BASELINE.md`.

| Evidence | Confirmed boundary | Limitation relevant to S4 |
| --- | --- | --- |
| S0/S1 | Inventory and offline audit of actual Quest, synthetic and fake traces | PickNik lacks a demonstrated original robot consumer; Spes Pi is an observer; Quest2ROS2 has an adapted transport and opaque XR state. These are not S4 runtime consumer substitutes. |
| S2 Docker | Synthetic TCP → original receiver/mapper/bridge → Servo → Gazebo; tracked-false and receiver-stale neutralization; old/fresh source timestamp acceptance; reconnect reference recapture | D3 sender stall followed D2 invalidation, so it did not independently test stopping while moving. D4 used fixed phase timestamps and opposite signed displacements in one session. No source-to-command ID or source/bag latency join. |
| S3 OpenVR | Fake API → unchanged original `quest_teleop.py` → Servo/controller → Gazebo; W1/W2 moved, W3 gated | W1 first captured z=.3010000467, W2=.3464999676. Same final pose and near endpoints do not imply synchronized trajectories. No actual Quest/ALVR/SteamVR evidence. |

S4-A independently opened all three S2 SQLite bags read-only, inspected input
JSONL markers/wire records and input/analysis code, and read the four S3 raw
JSON captures. S3 counts reproduce 0/593/502/0 production poses and 0/582/526/0
controller trajectories. This is a focused design audit, not a second full S1
audit. The 254-file hash inventory and raw inspection output are in
[`runs/s4a_preregistration_20260922T123356Z/`](runs/s4a_preregistration_20260922T123356Z/).
The historical reports remain unchanged; the qualifications above guide the
new controlled experiments.

## 3. Original checks and API meanings

### 3.1 Docker_Teleop

Pinned `Noah727/Docker_Teleop@64cbdde88bc52c6a80d37f994752e50f95ba537e`,
local `semantic_validation/targets/docker_teleop` (clean at inspection).
Within `ros_backend1.1/src`:

- `receiver/receiver/quest_controller_receiver.py`: `_parse_payload` reads
  `hand.isTracked`; `_store_payload` records local `time.monotonic()`;
  `_publish_loop` substitutes neutral state after `stale_timeout_sec` (.25 s
  default), then makes new ROS header stamps. JSON `timestamp` is not read.
  `_drop_client` clears the socket/client bookkeeping but does not itself
  synchronously clear all latest pose state; receipt timeout remains relevant.
- `teleop_bridge/teleop_bridge/mapping/hand_pose_mapper.py`: tracks local
  receipt age, combines tracked/teleop state, captures relative references,
  emits zero twist when the input is inactive. Engagement edges and inactive
  paths affect reference state; this is not a generation-ID isolation proof.
- `teleop_bridge/teleop_bridge/servo_bridge/servo_command_bridge.py`: separate
  local receipt timeout and `require_tracked` gate, then new ROS output stamp.
  Neither restamping nor repeated publication proves a fresh source sample.
- `UnityApp/Assets/Scripts/HandPoseSender.cs`: controller path obtains the
  wire `isTracked` from `GetConnectedControllers`; `packet.timestamp=Time.time`.
  That Unity application-relative clock is not Unix time. S2's Unix-like
  timestamps are synthetic and cannot establish the actual sender clock age.

### 3.2 OpenVR original program

Pinned upstream revision `170dad582d624f536359a3192a7f829669c2b031`, local
`semantic_validation/targets/openvr_ur5e_jazzy` (clean). In
`src/quest_bridge/quest_bridge/quest_teleop.py`, the 50 Hz callback checks right
controller role and `bPoseIsValid`, reads grip and captures a reference on its
first valid grip packet. It does not test `eTrackingResult` or
`bDeviceIsConnected`; it restamps generated `PoseStamped` with ROS now. Grip
release resets `first_packet` only inside the valid-pose branch. Invalid pose
alone does not explicitly clear that reference. Init exceptions exit; no
explicit connection generation, reconnect handshake, or invalidation re-arm
state machine is present. These are source observations, not recovery-runtime
results. W3 starts invalid and cannot alone prove invalidation while moving.

### 3.3 Native semantics and source-side observation points

| Source | Available observation point / semantic | Registered use / boundary |
| --- | --- | --- |
| Unity XR | `TryGetFeatureValue(CommonUsages.isTracked)` and `trackingState` at pose acquisition; feature availability must be logged | Unity's tracked indication and tracked components are separate. No claim that Docker's connection-derived boolean is this API indication. Unavailable features are UNKNOWN. [Unity isTracked](https://docs.unity3d.com/ScriptReference/XR.CommonUsages-isTracked.html), [trackingState](https://docs.unity.com/en-us/engine/6000.0/script-reference/unityengine/xr/commonusages/trackingstate). |
| OpenVR | `TrackedDevicePose_t` returned from the same pose poll carries validity, result enum and connection flag; grip is a separate call | Require validity AND connected AND `Running_OK` for the strict position-control task. `Running_OutOfRange` is a distinct result; do not rename it optical loss or emulated position. [Valve pose API](https://github.com/ValveSoftware/openvr/wiki/IVRSystem%3A%3AGetDeviceToAbsoluteTrackingPose), [Valve driver semantics](https://github.com/ValveSoftware/openvr/blob/master/docs/Driver_API_Documentation.md). |
| WebXR | `XRFrame.getPose` result or null; `XRPose.emulatedPosition` on that pose | true denotes computed positional offset such as an arm/neck model. It is not equivalent to OpenVR OutOfRange. Strict task disallows it; no Spes original-consumer runtime is invented. [W3C WebXR](https://www.w3.org/TR/webxr/#dom-xrpose-emulatedposition). |
| Quest system | Existing system mode log `POSITION/ORIENTATION` | Diagnostic co-observation only; no established per-command application/API join. Excluded as a runtime authorization signal in this protocol. |

The strict task disallows explicitly identified inferred/emulated position.
OpenVR `Running_OK` and Unity tracked components are only the evidence their
APIs expose; neither is asserted to exclude every internal prediction model.
No shared boolean replaces these native fields. Docker's synthetic `isTracked`
policy has only a wire-contract meaning. Native Unity/WebXR policies here are
semantic scope records, not extra S4-B runtime cases on absent consumers.

## 4. ROSMonitoring: identity, implementation, feasibility

Research identity:

1. Angelo Ferrando, Rafael C. Cardoso, Michael Fisher, Davide Ancona, Luca
   Franceschini, Viviana Mascardi, *ROSMonitoring: A Runtime Verification
   Framework for ROS*, TAROS 2020, LNCS 12228, pp. 387–399,
   [DOI 10.1007/978-3-030-63486-5_40](https://doi.org/10.1007/978-3-030-63486-5_40).
2. Maryam Ghaffari Saadat, Angelo Ferrando, Louise A. Dennis, Michael Fisher,
   *ROSMonitoring 2.0: Extending ROS Runtime Verification to Services and
   Ordered Topics*, FMAS 2024, EPTCS 411, pp. 38–55,
   [DOI 10.4204/EPTCS.411.3](https://doi.org/10.4204/EPTCS.411.3),
   [paper v1](https://arxiv.org/html/2411.14367v1). That paper describes partial
   ROS 2 support without message ordering; do not apply that limitation to a
   newer implementation without inspection.

The [authors' tool page](https://autonomy-and-verification.github.io/tools/ros-mon)
links to the [official repository](https://github.com/autonomy-and-verification-uol/ROSMonitoring).
Its code was actually fetched for source review in
`/tmp/rosmonitoring_s4a_20260922`; no install/generation/tests/runtime were run.

| Item | Exact selection and findings |
| --- | --- |
| Primary B2 implementation | Official master `d03aa5b44e29b76c0e108a098817bdf5aa98e322`, commit date 2026-06-29; `pyproject.toml` package version **3.0.0**, MIT. This is a current official implementation, not an assertion of a third published paper. |
| Historical ROS 2 branch | `c150bdd5538283246c1523827645a3b46eaeb12b`; README calls it development and tested on Galactic/Ubuntu 20.04. Record for provenance; no automatic fallback or pooled results with master. |
| Mechanism | YAML generator → ROS 2 Python monitor; imported message classes serialized to JSON → external WebSocket oracle → verdict and optional topic filter. `action: log` is observation, `action: filter` plus remapping is enforcement. |
| Types | Config supplies installed message/service classes. `PoseStamped`, `TwistStamped`, and local `ReceivedPoseStates` are candidates, not yet verified type support in our generated monitors. Nested/array fields must pass serialization tests. `PoseStamped` alone lacks source validity/result/session/time provenance. |
| Correlation | One oracle can process multiple interfaces. Current code supports ordered buffering using header/stamp/fallback observation time; this does not create event identity or establish clock equivalence. Need explicit IDs, payload linkage and clock contract. |
| Temporal properties | Bundled TL/Reelay oracle supports temporal property/abstraction hooks; RML/Prolog is another supplied backend. Generator is not itself an XR policy. Deadlines during silence need a clock/tick or external watchdog; passive topic observation cannot be assumed to stop control. |
| Filtering and failure | In `generator.py` `_oracle_verdict`, absent oracle or send/recv exception returns allowed/unknown. Negative verdicts block topic propagation; unknown is not negative. This is a static implementation finding requiring later runtime verification, not an inherent limitation of runtime verification. |
| Humble | Existing container Python 3.10.12; upstream current test-plan records Humble tests (author report, not rerun here). Python requirement >=3.9 fits. Our container has PyYAML 5.4.1, below required >=6.0; queried websocket-client/websockets/reelay absent. Not ready as installed. |
| Jazzy | Existing container Python 3.12.3, Jazzy directory; `python3 -m pip` unavailable. No local dependency/build/runtime proof; Jazzy compatibility UNKNOWN. Do not call this incompatible merely because pip is absent. |
| Required integration | Isolated dependency environment; pinned package/dependency locks; topic remapping; state transport and sequence binding; task-specific oracle property; monitor-health and neutralization integration. Custom message serialization/QoS, generated packaging, WebSocket API and timing need qualification. |

Inspected official source and license are preserved as text under
`runs/s4a_preregistration_20260922T123356Z/upstream/`, with file hashes in the
evidence manifest. Key source locations: `generator.py` `_connect_oracle`,
`_event`, `_wire_event`, `_oracle_verdict`, `_handle_event`, `_topic_callback`;
`events.py` `source_time`, `OrderedEventBuffer`; `config.py` type and ordering
configuration; `docs/test_plan.md` upstream tests. The current generator has
ROS 2 topics/services and ordered processing; local runtime qualification is
still required.

B2 will use the official generator/runtime and, as first choice, its bundled
TLOracle/Reelay with a task-specific property and abstraction. No home-written
replacement monitor may be labelled ROSMonitoring. If the genuine implementation
cannot be qualified, mark B2 `BLOCKED_ENV` with commands/dependency errors and
keep B1/B3 results separate. A custom direct predicate can be a separately
named baseline, but does not satisfy B2 or establish a ROSMonitoring failure.
Missing dependencies may be prepared in isolated S4-B environments after
approval; no host/network/socket changes are authorized by this protocol.

## 5. Task policy, trust, clocks, and re-arm

Task: gripped relative Cartesian teleoperation of the existing simulated arm.
Policy success is an engineering test criterion, not physical safety
certification or evidence of novelty.

Trust assumption: for functional comparison, the declared synthetic/fake
generator and its state transport are trusted. This does not resist a source
that lies about state or time. Each record retains native API namespace,
native fields, run/trial ID, generation ID, source sequence, raw pose/grip,
source sample time, send time, receipt time and command lineage where available.
State and pose must come from the same sample. A missing association cannot be
filled by nearest-timestamp matching and called causation.

| Policy component | Fixed rule |
| --- | --- |
| Docker validity | wire `isTracked=true`, teleop requested, connection generation current; false is forbidden. This is a synthetic message contract only. |
| OpenVR validity | `bDeviceIsConnected=true`, `bPoseIsValid=true`, result=200 (`Running_OK`), grip pressed. Result=201, invalid, disconnected or unavailable required state is forbidden. |
| Explicit emulation | Disallow when the native API explicitly reports it. Unknown native inference information is not silently translated into false; no runtime inference claim for the two stacks. |
| Freshness | Primary F250: age <=250 ms. Sensitivity F100 and F500: <=100 and <=500 ms. Run all three on timestamp/delay cases; report all. These are task candidates (two/five/ten Docker 20 Hz input periods; .25 s matches existing receive timeout), not values derived from human safety or optical physics. |
| Future time | More than +5 ms beyond the verified common clock is forbidden; [-5 ms,0] allowed as measurement tolerance. Equality at thresholds is allowed. Age straddling uncertainty bounds is UNKNOWN. |
| Receipt silence | Local monotonic last-source-event age >250 ms neutralizes regardless of freshness profile. Repeated cached ROS publication must not reset source receipt age. Register explicit no-bytes and delayed-bytes separately. |
| Invalidation | Stop accepting affected/new motion commands on first locally observed invalid state, expired age, disconnect, invalid generation, or unbound required state; revoke outstanding control and request neutralization. Source fault and monitor fault are distinct triggers. |
| R_EXPLICIT (primary) | Latch disarmed on fault. Recovery requires 500 ms continuously valid/fresh current-generation source plus grip/teleop release observed for >=100 ms after recovery, then a new rising edge. Capture a new reference on that edge; first reference creates no added displacement. No held-grip automatic restart. |
| R_AUTO (secondary) | After 500 ms continuously valid/fresh current-generation source, allow automatic restart with grip held, but recapture reference before further displacement. Required on recovery/reconnect cases, reported separately; cannot pick whichever favors a baseline. |
| Ordinary ungripped state | Intentional non-control, not a false rejection. Initial engagement likewise requires valid reference acquisition. Fault reset controls are not robot-driver reset commands. |

Use **one host kernel monotonic clock**, no container time namespace offset,
for the synthetic source, delay injector, gate, oracle timing wrapper and
consumer trace. Verify common clock ID/boot ID/offset before runs; maximum
observed offset uncertainty 1 ms. Record each participant's clock metadata and
pairwise calibration. If that contract fails, time-based judgments are UNKNOWN
and the affected timing comparison is INVALID, not a defense failure.

Keep `t_sample`, `t_send`, `t_receive`, `t_decision`, `t_forward`,
`t_consume`, `t_neutral_request`, `t_last_nonzero`, and `t_settled` distinct.
ROS wall/sim header stamps and rosbag storage times are recorded verbatim with
clock labels. Do not subtract them from monotonic values. Use `/clock` plus
observer-monotonic associations for simulator analysis and report uncertainty.
CPU time is process CPU time, not simulation time. The original Docker
`Time.time` field has no host epoch: native age remains UNKNOWN unless a
separate validated mapping is supplied. The controlled source-age experiment
declares its own synthetic clock contract and preserves both raw and mapped
values. OpenVR has no per-sample timestamp in the tested pose struct: sample
monotonic time is harness instrumentation, never claimed as a native field.

At every forwarding point, record the current age as well as the age at source
decision. A source-side gate cannot know a delay imposed **after** its decision;
report that architectural placement effect separately from expressiveness of
its predicate. Source generation and API status are never authenticated merely
by being in a ROS message.

## 6. B0–B3 locations and fair information

Two information regimes are mandatory. **I_NATIVE** supplies only information
the original interface actually contains. **I_FULL** supplies all required
native fields and source time/generation/sequence from the identical source
sample to every configurable defense, without an upstream allow/deny label.
I_NATIVE missing data is `UNOBSERVABLE`, not a method failure. B0 remains
unmodified in both regimes: in I_FULL the measurement sidecar records state
but B0 does not suddenly gain a validation algorithm.

| Baseline | Location / proposed S4-B integration | Changes and readiness |
| --- | --- | --- |
| B0 original | Docker original receiver→mapper→bridge; OpenVR original `quest_teleop.py`; original Servo and controller | No policy/source change. Observational probes/remaps must pass an instrumentation-equivalence check. Existing S2/S3 environments available, new readiness barrier still needed. |
| B1 source gate | Docker before TCP production receiver, OpenVR after fake API acquisition before production pose use | Source harness gate only, preserving raw native fields in its log. Original consumer unchanged. Explicitly model post-gate delay. A block triggers a separately logged neutralization request, not just silent input dropping. |
| B2 ROSMonitoring | Actual generated ROS 2 filter inserted by remapping at Docker receiver→mapper / OpenVR production pose→Servo boundary; genuine oracle is in the decision path | YAML/property/transport integration required. I_FULL uses a lossless event envelope with original payload and source state, then strips it after the actual upstream filter to restore original consumer message type. No policy decision in serializer/stripper. No vendor edit for this path. I_NATIVE uses original payloads and reports unobservable fields. |
| B3 direct validation | In the receiving callback immediately before Docker mapper accepts a pose; for OpenVR, a reviewed local overlay of original `quest_teleop.py` before target publish | Equivalent source state, clock, and policy predicates supplied directly. For a truly final Servo-consumer check, a separate Servo callback overlay would need its own declared variant; do not call a ROS relay controller-internal. Vendor checkout stays immutable; save overlay diffs and rebuilt artifact hashes. Not implemented. |

For I_FULL, monotonically increasing IDs propagate through observation-only
probes from source parse to cached source selection and generated command.
Record every generated command's selected source ID (including repeated
commands). For B2, the envelope contains that selected source ID and original
payload. Run state-only invalidation events and a 50 Hz common tick so the
oracle can detect silence; ticks do not count as source updates or commands.
Atomic envelope is primary. An unjoined asynchronous sideband is a separate
unqualified transport, not adequate I_FULL. Generic ordering does not repair
a bad join. All adapters and data added are included in modification cost.

Primary B2 configuration is `action: filter`, ordering disabled (no artificial
reorder delay), oracle response timeout 50 ms and common 50 Hz health/tick
events. UNKNOWN/error/no verdict must be reported by B2-native as it actually
behaves; B2-composed treats that health event as a stop request. A missing gate
heartbeat for 250 ms triggers the common watchdog for B1/B2/B3. This is an
ordinary additional health interlock, explicitly not attributed to the native
ROSMonitoring filter. Freeze the oracle property mapping and test expected
verdicts before comparative motion. An ordered diagnostic, if run, uses exactly
20 ms on all interfaces and is reported separately, never chosen as a better
replacement for the primary result.

For the primary envelope, outer event time is the verified synthetic clock;
the original ROS header remains nested unchanged with its own clock label.
The oracle uses the current verified monotonic time for decision-age checks,
not only the age calculated when an envelope was enqueued. Repeated controller
outputs from one cached sample use distinct child-command IDs and are not
duplicate source samples; replaying a previously consumed source-event ID as
a new source update is the C-ID duplicate case. Missing mandatory metadata may
be rejected operationally, but its effect on unavailable native information
is still classified UNOBSERVABLE rather than a method failure.

ROSMonitoring's filter alone drops new commands and does not promise to cancel
an already accepted trajectory. Therefore report two B2 modes: **B2-native**
(upstream filter behavior, diagnostic) and **B2-composed** (primary practical
baseline, upstream filter plus ordinary watchdog/neutralization integration).
B1 and B3 get the same stop service/adapter contract and fault budget. That
adapter accepts only stop/hold or forwards allowed commands; it may not
independently enforce validity/age/re-arm and mask a failed monitor. Common
monitor-health timeout may stop on missing verdicts; log this separately from
a property violation. Include a passthrough adapter control B0-shim to measure
transport overhead/equivalence. Report the native fail-open behavior honestly,
and allow a conventional fail-closed integration to solve it without calling
that solution a new framework.

Stop actuation must be qualified for each existing Servo version: Docker zero
twist plus confirmed halt; OpenVR pose path requires confirmed pause/halt or
measured-position hold that also revokes the controller's pending trajectory.
Never forward a zero absolute pose as a stop. Exact service/message and
controller behavior are S4-B setup prerequisites; inability to prove stop
delivery is BLOCKED_INTEGRATION, not an assumed stop or novelty result.

## 7. Cases and controlled trajectories

All time schedules below are host monotonic relative to a common trial-start
barrier; record simulation progress separately. Unless stated, valid source,
current generation, identity quaternion, no reset/gripper actuation, and
single source. All frame transformations/configuration remain those of the
pinned originals. Fixture hashing includes pose sequence, field values, sample
indices, offsets and phases; per-run absolute epoch is recorded separately.

Docker fixture: 20 Hz, right-hand reference (.20,.20,.30), then .35 X with Y/Z
unchanged and teleop true; left-hand payload held fixed to the same harmless
reference across all pairs. 1 s idle, .8 s reference, 1 s active, 2 s tail.
Reinitialize to the same arm state before each paired subtrial. Old and fresh
phases do not share a moved robot, and do not reverse direction. Source time
is regenerated per sample before the controlled age offset is applied.

OpenVR fixture: 50 Hz, raw reference (1,2,3), identity rotation; advance z by
.001 per sample for 300 steps, then hold, identical to the declared S3 shape.
Freeze step index at zero until readiness and reference acquisition are
acknowledged. Capture before startup, then 1 s idle, 1 s reference, 6 s ramp,
2 s final hold and 2 s tail (12 s after the barrier). W2/W3 use identical source
poses/index schedule even when rejected; freeze only pre-trial, never extend a
rejected case to manufacture a favorable endpoint. B0 W2 keeps original behavior.

| ID | Stack / change from valid control | Expected task-policy outcome |
| --- | --- | --- |
| D0 | Docker no sender/control | Idle; not a false reject. |
| D1 | Docker valid reference and active displacement | Admit and move. |
| D2 | After 1 s active, change only `isTracked` false for 1 s | Reject new motion, neutralize and settle; separate deceleration interval. |
| D3 | After 1 s active, cease bytes for 1 s while last tracked/teleop remains true | Stop after receipt timeout; prevents S2's already-invalid confound. |
| D4 | Independent identical motion, source age at creation offset 0, .05, .15, .35, .75 s, plus historical value 1.0 as an explicit synthetic epoch anomaly | F100/F250/F500 each evaluated by measured age; fresh samples accepted, over-budget blocked; no reference-zero shortcut. Add +1 s future stamp as a rejected clock-contract case. |
| D4-L | Same fresh sampled trajectory, queue delivery by 0, .05, .15, .35, .75 s **after** the B1 source decision; source stamp unchanged | Judge age at consumer as well as each gate. Distinguish delivery delay from old-but-prompt source stamps. Test current-time restamp does not conceal true age. |
| D5 | Moving connection closes; new generation after .7 s; initial pose .50 X then +.15 X; stale old-generation sample is also presented after reconnect | Old generation rejected in I_FULL; R_EXPLICIT held grip cannot restart; R_AUTO can re-reference after dwell. Separate fresh reference from subsequent motion. |
| D6 | Valid→invalid for 1 s→valid held teleop for .8 s→release .2 s→press at current reference→+.15 X | Both registered recovery policies, no jump caused solely by lost/reacquired reference. |
| W0 | OpenVR no production teleop | Idle. |
| W1 | OpenVR valid=true, connected=true, result=200, grip=true | Admit reference/ramp. |
| W2 | Same W1 sequence, only result=201 | Strict policy blocks despite valid=true. |
| W3 | Same W1 sequence, only valid=false | Block. |
| W4 | 1 s valid ramp→1 s invalid→.8 s recovered grip held→.2 s release→press/new reference→2 s ramp | Recovery/re-arm comparison; invalidation while moving rather than static W3 only. |
| W5 | Same W4 timing with disconnect/connection-generation change instead of validity loss | Explicit connection semantics and fresh-reference behavior; fake only. |
| C-ID | Each stack I_FULL: absent required field, missing/duplicate binding ID, state-command mismatch and old generation | Reject or classify unobservable before actuation; retain every log; no nearest-neighbor causal claim. |
| C-MON | B2-native/B2-composed: oracle absent at startup, oracle disconnect during active input, nonresponding oracle; matched B1/B3 gate-process failure diagnostic | Record native behavior and common watchdog effect separately. Runtime failure mode is not assumed from static code. |

W4/W5 use a 12 s post-barrier capture as well, with the unlisted remainder
held neutral. D5/D6 use a 10 s post-barrier capture so recovery and the final
2 s active-plus-settling window fit. D4-L capture lasts base fixture plus the
registered delay plus 2 s, identical across baseline arms at that delay.
Other Docker cases use 6 s post-barrier capture, padding the tail with neutral.
Delayed queues are FIFO; do not burst-drain early or restamp at release.

### W1/W2 readiness and comparability gate

Fixed initial arm vectors, ordered shoulder_pan, shoulder_lift, elbow,
wrist_1, wrist_2, wrist_3: Docker `[0,-1.57,1.57,0,1.57,0]` from
`ros_backend1.1/src/ur_hande_description/config/initial_positions.yaml`;
OpenVR `[0,0,1.4232,.243,4.6863,1.6315]` from
`src/ur5_description/urdf/initial_positions.yaml`. The latter is the Gazebo
description fixture, not the separate MoveIt all-zero example file. Keep the
existing Servo incoming-command timeouts (.25 s Docker `servo_gz.yaml`, .5 s
OpenVR `ur_servo.yaml`) unchanged and report them separately from the proposed
250 ms source-silence watchdog; a new policy must not be credited with an
existing downstream timeout.

1. Fresh trial-owned Gazebo/controller/Servo processes; no reuse of a moved arm.
   Pin image ID, source revision, launch, controller/Servo parameters and QoS.
2. All recorder subscriptions and publisher/subscriber matches acknowledged;
   record three increasing `/joint_states` stamps and active controllers;
   verify Servo accepts the chosen command type with successful service reply.
3. Before the barrier, arm velocity <.001 rad/s and per-joint drift <.0001 rad
   over .5 s. Initial six-arm-joint positions must be within .0001 rad of the
   fixed per-stack neutral fixture. Exclude gripper only with named justification.
4. Source logs index=0 and reference event; recorder returns a ready ACK. Then
   release the single start barrier. No fixed `sleep 2` substitutes for ACK.
5. Verify whole expected source index range in input and association logs.
   A rejected W2 has zero admitted commands but must have complete source
   input. Missing the first indices invalidates the timing/trajectory pair.

Keep all invalid attempts. At most two setup-only retries per cell with the
same parameters; exhausted cell is BLOCKED. A functional policy failure is
never retried away. Any per-command latency lost because of an observation
gap is UNKNOWN. Source timing differences >5 ms for matched scheduled samples
make the trajectory pair INVALID; report scheduling overhead rather than
silently normalizing a materially different input.

## 8. Measurement and decision rules

Record separate stages; downstream joint motion alone cannot identify which
message an original consumer accepted.

| Metric | Location / required records | Clock and rule |
| --- | --- | --- |
| Normal acceptance and false rejection | Source-ID manifest, gate verdict, admitted payload, original callback/probe | Score eligible source samples and source-derived commands separately. Normal means valid, fresh, armed/current generation and inside steady active phase, excluding specified reference/dwell/release. Target 0 false rejects and >=99% observed eligible input delivery; missing capture is UNKNOWN, not a reject. |
| Forbidden acceptance | Gate and consumer callback selected source ID, command lineage | 0 forbidden new motion commands consumed after local invalid-state decision; in-flight commands classified by actual source/decision timestamps, not relabelled valid. Unknown association prevents event-level scoring. |
| Source-to-consumer linkage | Atomic source/state ID with payload hash, generation, selected cached input ID and child command counter | No counts/stamp coincidence substituted for a join. Hash transport invariance plus callback ID trace; sampling instrumentation must not gate B0. |
| Detection/decision/block | Source, receive, predicate, forward, original callback logs | Common monotonic; record stage-local and end-to-end latencies separately. Decision and neutralization request <=50 ms after local trigger (or timeout expiration); report all violations. |
| ROS publication | Docker `/received_pose_states` (`teleop_bridge_msgs/msg/ReceivedPoseStates`), `/target_twist_states` (`TargetTwistStates`); OpenVR `/servo_node/pose_target_cmds` (`geometry_msgs/msg/PoseStamped`) | Header and bag time preserved. Topic publication is not consumer receipt. Record input/output of every remap and monitor. |
| Servo/control output | Docker `/servo_node/delta_twist_cmds` (`TwistStamped`) is **Servo input**, `/joint_group_velocity_controller/commands` (`Float64MultiArray`) is output; OpenVR `/ur5_arm_controller/joint_trajectory` (`JointTrajectory`) | Capture controller output as well as pose/twist input. Instrumented consumer receipt is required for exact acceptance; response topic alone is a bounded indirect observation. Validate actual names/types/QoS before trials. |
| Neutralization | Stop request/reply, last nonzero control command, pending trajectory state | From trigger to no continuing motion command <=300 ms; receipt-timeout case trigger is last real source receipt+250 ms, not stall start. Zero twist threshold 1e-6 component magnitude; pose holds judged by target change/trajectory velocity, never by absolute pose being nonzero. |
| Gazebo outcome | `/joint_states` (`sensor_msgs/msg/JointState`), named six arm joints; optional FK with hashed URDF | Motion positive control max excursion >.01 rad; active nonzero control must accompany it. Settled: abs velocity <.001 rad/s and per-joint drift <.0001 rad over .5 s; achieve by trigger+1 s. Also report displacement integrated during settling without excluding it. |
| Allowed-path preservation | Identically scheduled normal fixture through B0-shim vs defense | After aligning by source index, final per-joint difference <=.02 rad; all counts/trajectories still reported. Failed positive control invalidates blocked-case movement attribution. |
| Timing/resource overhead | Source/gate/consumer process traces; process and child CPU counters sampled every 100 ms; RSS and wall runtime | CPU% = CPU seconds/wall seconds*100 (100%=one core); give incremental vs B0-shim and total. Latency min/median/p95/max and per-trial max. p95 added gate/transport latency <=20 ms is the registered practicality target, not novelty. CPU is descriptive, no invented threshold. |
| Modification burden | `git diff --numstat` against each pinned original, generated/config/adapter/property code separately | Actual hand-written added/deleted LOC, generated LOC, files/nodes/dependencies and engineering time if logged. Unlogged labor UNKNOWN. No runtime-only cost comparison that omits state transport. |

The numbers above are predeclared simulator engineering thresholds, chosen
to separate S2/S3 idle noise (<1e-9 rad excursion) from ~1.5 rad OpenVR motion
and to permit measured deceleration. They are not universal safety bounds.
If these thresholds cannot be achieved in setup, report infeasible/invalid
conditions; do not loosen them after a blocked-motion result.

Five independent fresh-initial-state repetitions for every primary case,
baseline and information regime, including W0/D0 controls. Apply F100/F250/F500
to D4/D4-L; use F250 elsewhere. Apply R_EXPLICIT/R_AUTO to D5/D6/W4/W5;
use R_EXPLICIT elsewhere. B2-native diagnostics and B0-shim are retained
separately from B2-composed and B0. Randomize baseline order within each
case/profile/repetition using seed 20260922, and commit the full schedule
before the first outcome. Reuse identical input fixtures across baseline arms.
No optional stopping. Report per-trial data, worst case and distributions;
zero failures in five trials is limited evidence, not a reliability guarantee.

Classifications: PASS_POLICY, FAIL_POLICY, BLOCKED_ENV,
BLOCKED_INTEGRATION, INVALID_COMPARISON, UNOBSERVABLE, UNKNOWN. A threshold
violation with complete comparable evidence is FAIL_POLICY even if another
baseline also fails. A healthy monitor's policy success and a crashed monitor's
recovery success are separate claims. Do not replace an unavailable B2 with a
custom implementation and mark it PASS.

## 9. S4-B execution sequence (planned only)

1. After explicit review, verify this digest and sources; create fresh
   `runs/s4b_<UTC>/` with commands, environment, input manifest, fixtures,
   stdout/stderr, bags, monitor/oracle logs, process metrics, analysis and
   exclusions. Save current Git/container state before changing owned resources.
2. Prepare isolated Humble/Jazzy dependencies and pin exact versions. Generate
   actual ROSMonitoring packages and qualify type serialization, QoS/remaps,
   oracle verdict filtering, ordering and oracle-failure behavior on robot-free
   fixtures. No qualification output is a Gazebo defense result. If B2 cannot
   qualify, document blocker and do not silently change implementation version.
3. Implement only the registered ordinary gate/property/transport/observation
   adapters in new harness/overlay paths. Verify passthrough B0-shim, original
   source integrity, clock/ID binding, timer behavior without messages, and
   actual stop API/hold cancellation. Compare ordinary controller-side checks
   with full state fairly. Freeze patches, fixture hashes and execution schedule.
4. Docker: reuse S2 Gazebo-only launch in an owned isolated container/domain
   and loopback port; receiver→mapper→bridge→Servo→Gazebo. Never
   `servo_test.launch.py`, robot driver, `robot_ip`, CAN or physical actuator.
   Execute D0–D6, C-ID/C-MON under the registered matrix, recording all attempts.
5. OpenVR: reuse S3 original Gazebo/controller/Servo launches and the external
   fake API dependency; use the new readiness barrier and source-index log.
   Run W0–W5, C-ID/C-MON. No Quest/ADB/ALVR/SteamVR session. The base image lacks
   `/ws/install` as documented in S3; reuse a verified build in an owned
   environment without interrupting existing `openvr_sim` processes.
   Existing launch entry points are `ros2 launch ur5_description gazebo.launch.py`,
   `ros2 launch ur5_controller controller.launch.py is_sim:=True`, and
   `ros2 launch ur5_moveit_config ur5_servo.launch.py`. Docker uses S2's
   `inputs/start_gazebo_only.sh` as the reviewed launch reference including
   `ros2 launch servo_test_config servo_gz.launch.py`. These are planned commands,
   not S4-A executions; create S4-B-owned output paths and the specified barrier.
6. Analyze raw with stage-separated metrics, contemporaneous command-ID joins,
   recorded-clock validation and independent count checks. Write all failures
   and unknowns, state environment costs, update board, explicitly commit/push,
   verify HEAD/origin/main/remote main, report and stop before S5.

## 10. Method-gap decision rules

If at least one existing configurable baseline with I_FULL meets all relevant
policy and practicality conditions, report **NO_METHOD_GAP for those tested
conditions**. If ordinary metadata transport, task property configuration,
direct checking, watchdog or re-arm logic closes a failure, acknowledge that
existing solution and its measured integration cost. B0 failure alone cannot
justify a new framework. Neither can feeding a defense an impoverished I_NATIVE
message while giving a proposed method full state.

A remaining candidate requires a reproducible I_FULL policy failure with
identical source data, policy, clocks, controls and functioning integration;
separate expression limits, placement effects, provenance trust, runtime bugs,
and performance costs. Re-check an ordinary source/controller fix and the
real ROSMonitoring property/integration before claiming a method limitation.
Transport identity loss or post-gate delay may be a candidate condition, not a
new-method conclusion. Physical harm, native tracking causality and broad
cross-stack generalization remain outside this synthetic/fake experiment.
S5, after review, decides whether any independently defensible gap remains.

## 11. Current unknowns and readiness

S4-B readiness: **NOT_READY**. Protocol is frozen for review; prerequisites
remain: user approval, isolated dependency locks and actual ROSMonitoring
qualification on both distros, complete sample-ID observation/transport,
matching OpenVR capture start, proven Servo/controller neutralization and
reference re-arm integration, and clock calibration. These are setup tasks
for the authorized S4-B phase, not work silently performed in S4-A.

UNKNOWN: real XR-to-synthetic semantic correspondence; monitor runtime/overhead
and serialization under these exact ROS types; actual source-to-command latency;
effect of oracle failures and recovery; native inference details; physical
robot outcome. Runtime feasibility is not disproven by not executing it here.

The new evidence package contains source-review snapshots, read-only metadata,
input hashes and offline inspection. No new input was sent to a controller,
no defense was installed, and no new simulation was launched. Existing S0–S3
artifacts are unchanged. All selected files are small text/JSON/code research
artifacts; upstream license is retained. The unmodified upstream checkout in
`/tmp` is a retrieval cache, not excluded experimental raw; selected inspected
files, immutable revisions and hashes are committed for reproduction.
