# A02 — Evidence audit of M7, M8, M9 (2026-10-03)

**Scope.** Literature, code and upstream follow-up only; no experiment was run for these cases.

**Read levels.**

- **SOURCE**: pinned code read.
- **BINARY**: installed package inspected.
- **ISSUE**: issue/PR text read via the GitHub API.
- **SPEC-SUMMARY**: a spec page fetched through a summarising fetcher, so the wording is not verbatim.
- **NOT_READ**: known by title only.

## M7 — stale input combined with the latest transform

| Item | Content |
|---|---|
| Protected condition | A command derived from an input sample is transformed with the transform **valid at the sample time**, within a declared time bound |
| Attacker / fault | Fault (S0): asynchronous tf and input streams, dynamic frames (recentering, moving base). Network delay (S1) only stretches the gap. No attacker-specific mechanism found. |
| Path, generic | source sample (stamped) → wire → consumer looks up tf with `Time(0)` (latest) or the stamp → command |
| Path, this host's UR5e app | Commands are already in `base_link`, Servo's planning frame. Servo transforms a command only when the frames differ, and then with `lookupTransform(planning, command, rclcpp::Time(0))` (Servo 2.12.4 `servo.cpp` L565; SOURCE). **M7 is not exercised on this path.** |
| Path, M39 B1/C1 | Re-anchor uses the tf of the measured EE at `Time()` (latest) while the arm is held, so it measures the current state. This is the intended semantics; M7 does not apply. |
| Path, Quest2ROS2 / Docker_Teleop | Anchors use `lookup_transform(base, ee, Time())`, paired with the latest hand sample (A2 L153–155; A5 mapper L1531; SOURCE). There is no sample-time alignment. |
| Strongest existing method | Look up at the input's stamp with a bounded wait (tf2 `lookup_transform(target, source, time, timeout)`; tf2_ros 0.36.21 docstring: "time: The time at which to get the transform (0 will get the latest)"; BINARY), or tf2 `MessageFilter`. |
| Premise of that method | The stamp is the sample time and the clocks are mapped. **R11/M12 show that this premise fails on the audited real path:** the app stamp is the generation time, and no source time is available. |
| Applied in target implementations | Not applied: Servo `Time(0)`; Quest2ROS2 / Docker_Teleop `Time()`. |
| Author limitation / maintainer text | Nav2 issue #6320 "Explicit detection of Stale transformations" (open; updated 2026-09-22) and PR #6391 "Verifying tf staleness…" (open, not merged; updated 2026-10-02). The maintainer comment of 2026-09-18 lists further lookup sites, such as `clearAroundPose` and `getFootprintInRobotFrame` with a zero timestamp. **ISSUE.** Navigation stack, not teleop. |
| Paper | The tf design paper (Foote, TePRA 2013) is NOT_READ in this audit; no claim is taken from it. |
| Follow-up resolved? | Nav2: in progress, not merged. MoveIt Servo 2.12.4: unchanged (`Time(0)`). |
| Feasible verification here | A dynamic-frame test with commands in a frame different from `base_link` (a moving `quest` frame published with tf) on the existing Servo stack; it needs a scripted tf publisher. Resources: none beyond the current host. **Not run** (budget). |
| Relation to M39 / M12 | Stamped lookup needs a meaningful stamp. M12 showed the publish stamp carries no sample time on this path. So M7's strongest fix inherits M12's information limit unless the app carries the acquisition time (R11 A2). |
| Judgment | It stays KNOWN_METHOD (tf2 stamped lookup). The judgment that it is not applied in the targets is source-confirmed. Its effect size is still UNKNOWN on this host's path, because M7 is not exercised there. |

## M8 — left-hand topic carrying right-hand content

| Item | Content |
|---|---|
| Protected condition | Each message's payload and identity come from the device and arm that the topic names |
| Attacker / fault | Fault (S0): a shared mutable message object plus asynchronous serialization. A compromised app (S2) could swap frames consistently, which this check cannot catch (U37). |
| Path | PickNik `ROSPublishers.cs` reuses one `Odometry`/`TFMessage` instance for both controllers (L76–90, L386–416) → ROS-TCP-Connector v0.7.0 `Publish()` queues the reference and serializes later on the sender thread (`RosTopicState.cs` L211–216, `TopicMessageSender.cs` L47–62, L109–117) → endpoint → the closed MoveIt Pro consumer. SOURCE (A3). PRIOR_INTERNAL R0: on a real Quest 3, 54 % of left messages carried the right frame. |
| Author assumption contradicted by code | The PickNik comment: "ros_tcp_endpoint serializes synchronously inside Publish(), so reuse is safe" (`ROSPublishers.cs`, InitializeReusableMessages comment; SOURCE). The connector code queues by reference. |
| Strongest existing method | Allocate per publish, or deep-copy before `Publish()` (the standard immutable-message practice). Downstream checks: frame/topic consistency (detects this fault), plus a device id / immutable payload. |
| Applied in target | No, at PickNik HEAD `bbaef07`. That is still upstream HEAD on 2026-10-03 (`git ls-remote`); no later commit. |
| Follow-up resolved? | ROS-TCP-Connector: latest release v0.7.0 (2022-02-03); `main` is not ahead of v0.7.0 (GitHub compare, `ahead_by = 0`). No upstream change to reference-queued serialization. PickNik open issues (#2, #4, #5) do not mention it. **Unresolved upstream at check.** |
| Feasible verification here | Not runnable (R08: Unity OpenXR has no Linux player; no Quest). A unit-level test of the connector's queueing is possible in a Unity Editor play-mode test without XR. That would be a component test, not the real path. |
| Relation to M39 / M12 | A binding error is a provenance failure (which device or sample a command came from). R11's A2 sequence field does not identify the device. The device identity would need its own field. |
| Judgment | Stays **IMPLEMENTATION_GAP** (root fix known, not applied, upstream unchanged). Not a method gap. |

## M9 — head pose substituted when the controller pose is missing

| Item | Content |
|---|---|
| Protected condition | Motion commands come only from the approved input device; a missing controller pose stops control instead of switching source |
| Attacker / fault | Fault (S0): controller tracking or detection loss. S3 (environment, e.g. lighting or occlusion) can induce it. |
| Path | Spes `index.html` L337–346: a null controller pose silently falls back to the viewer (head) pose while `move` is held; the packet `device` stays `'VR'` (L377), so the server cannot distinguish them (SOURCE, A4). WebXR `XRPose.emulatedPosition` exists to mark emulated positions (W3C WebXR Device API §9.1; SPEC-SUMMARY) and is not read by Spes (A4). |
| Strongest existing method | An explicit pose-source identity in the packet (controller / hand / viewer), a refusal to command from the viewer pose in controller mode (stop instead), and `emulatedPosition` / tracking flags consumed at the server. |
| Applied in target | No, at Spes HEAD `c5d8081` (still upstream HEAD on 2026-10-03). |
| Upstream report | Spes issue #14 (open, 2025-11-01), "On Quest 3 browser the controllers are not detected and Teleop falls back to headset pose". The reporter describes the `detectDeviceType` path (the device treated as a phone; HMD pose used). The maintainer (2025-11-18) could not reproduce it. **ISSUE.** This is a related but distinct trigger: device-type detection rather than per-frame null pose. Issue #15 (closed, unmerged PR "Quest3 xrstate") has no stated relation. |
| Follow-up resolved? | No. The issue is open and no fix commit exists. |
| Feasible verification here | Spes is WebXR. A desktop WebXR runtime on Linux was not assumed (F1 APP_COMPATIBILITY), and no Quest is attached. Not runnable. A WebXR emulator in a browser would be a stand-in, not the real path. |
| Relation to M39 / M12 | A source-identity failure. M39's B1 treats a missing controller as pose-invalid → stop, which is the opposite policy. R11's A2 (validity + sequence) would not detect a silent source switch, because the substituted pose is valid. |
| Judgment | Stays **IMPLEMENTATION_GAP**. An independent user report exists (unconfirmed by the maintainer). |

## New candidates from this audit (recorded only)

**Pose-source identity as a provenance field.** The same field would let a consumer reject M8 (wrong
device) and M9 (wrong source) together.

| Basis | Counter-evidence | Minimal check |
|---|---|---|
| M8 and M9 both lose device or source identity before the consumer, and R11's A2 provenance (time, sequence, validity) does not carry identity | Each has a simple per-app root fix (allocation; explicit fallback policy). A shared field is useful only if several apps adopt it. | On a real frontend (needs a Quest): inject a source switch and check whether identity + validity at the gate blocks it while normal operation passes |
