# Framework Research-Utility Audit

Date: 2026-09-07. Baseline decision on entry: `GO — NOT STRONG GO`.

This audit re-evaluates the whole framework population against the actual research item, using
four **independent** axes rather than a single INCLUDED/EXCLUDED bit. Per-framework records are in
`semantic_validation/frameworks/<name>/RESEARCH_UTILITY.md`; the cross-framework tables are in
[FRAMEWORK_POPULATION_MATRIX.md](FRAMEWORK_POPULATION_MATRIX.md) and
[FRAMEWORK_LINEAGE_MATRIX.md](FRAMEWORK_LINEAGE_MATRIX.md).

## 1. What changed in this session

Six frameworks were audited against pinned source for the first time: **Docker_Teleop**,
**OpenVR UR5e (Jazzy)**, **Quest2ROS2** (re-audited as a core system, not an artefact of an old
classification), **OpenArmX**, **VR-hand-bridge-ROS2**, and **Nakama**.

Two runtime results were produced, both robot-free:

1. **Quest2ROS2 actual ROS 2 transport** (recovered from the previous session and committed):
   the pinned production node under actual DDS, 7/7 age cases published with no age gate, 7/7
   source stamps replaced, 7/7 input frames replaced. See
   [QUEST2ROS2_ROS_RUNTIME.md](QUEST2ROS2_ROS_RUNTIME.md).
2. **Quest2ROS2 in-repo simulator → production node → DDS → physical Pi**: 619 published, 619
   received. See [QUEST2ROS2_SIMULATIONINPUT_PI.md](QUEST2ROS2_SIMULATIONINPUT_PI.md).

Neither is E5/E6. The decision does not move.

## 2. The central correction: "no gate found" is not the interesting axis

The most useful result of re-auditing is that the population does **not** split cleanly into
"unsafe frameworks that drop semantics" and "safe frameworks that gate". It splits along a
different and more publishable line: **where the semantic is lost, and whether the thing being
gated actually means what the gate's author assumed.**

Three concrete patterns, each from a different framework and each source-verified:

- **Docker_Teleop — the gate exists, propagates end-to-end, and may not mean what it appears to.**
  `isTracked` is serialised in the wire payload and re-checked server-side before any twist is
  forwarded (`servo_command_bridge.py:123-125`). But its value is derived from
  `OVRInput.GetConnectedControllers()` — controller **connection**, not pose validity or tracking
  quality (`HandPoseSender.cs:1242-1244`). A controller that is optically occluded remains
  connected. This is the sharpest available instance of a semantically mismatched gate.

- **OpenArmX — the same field is preserved at one internal boundary and dropped at the next.**
  The C++ bridge parses `timestamp_ns` off the wire and writes it into `PoseStamped.header.stamp`
  when positive (`openarmx_teleop_bridge_vr_node.cpp:510-525`). The consuming teleop node then
  discards `header.stamp` entirely and re-stamps with `time.monotonic()` at callback entry
  (`openarmx_teleop_vr_node.py:356-376`), so its 0.3 s freshness gate measures ROS-callback
  latency rather than end-to-end age. Source time is transported and then thrown away *inside one
  framework*, which is a stronger argument than any cross-framework comparison.

- **OpenVR UR5e — a real validity gate that reads the weaker of two available flags.**
  `bPoseIsValid` gates the entire publish path (`quest_teleop.py:49`), but `eTrackingResult` is
  never read, so `Running_OutOfRange` / `Calibrating_InProgress` are indistinguishable from
  `Running_OK`. This reproduces, in the OpenVR API family and an unrelated implementation, exactly
  the `VALID`-versus-`TRACKED` gap previously documented only for NVIDIA IsaacTeleop's OpenXR path.

That third point matters for generality: the gap is now visible in **two different XR APIs and two
unrelated codebases**, which is a much better basis for a cross-architecture claim than repeating
the same finding within one API family.

## 3. Quest2ROS2 reassessment

Quest2ROS2 was not excluded by prior classification and should not have been treated as settled.
Re-audit confirms it is a **core** system, and specifically the population's best
`PRINCIPAL_BLACKBOX`:

- `SYSTEM_RELEVANCE = HIGH_XR_ROS_CONTROL`, `SEMANTIC_OBSERVABILITY = BLACK_BOX_XR_FRONTEND`
  plus full host-side source.
- Host side has **no** tracking-validity concept at all (repo-wide grep, zero hits), never reads
  `header.stamp`, and replaces the input `frame_id`.
- Arming is a **default-on latching toggle**, not a hold-to-drive deadman
  (`robot_arm_controller_base.py:89,220-221,356-358`).
- Filter state and pose anchors persist across a transport disconnect and are cleared only by an
  operator button press (`:334-384`), so a client that reconnects and resumes streaming continues
  from a stale anchor. A 2.0 s "Signal Lost" watchdog **exists in the repository**
  (`CheckTCPconnection.py:83-89`) but is a standalone diagnostic and is not wired into the control
  path — the author saw the need and did not connect it.
- Both prior synthetic freshness findings (stale/future stamp acceptance, frame replacement) are
  now reproduced on actual ROS 2 transport with the actual node.

## 4. Spes role, stated precisely

Spes remains the strongest **motivating XR-hardware case** and is **not** a native XR→ROS
implementation. Its ROS output exists only through a research adapter written by this project.
Roles: `MOTIVATING_XR_CONTROL_CASE` and `RESEARCH_ADAPTED_ROS_PROPAGATION_CASE`. It must not be
counted toward "native XR→ROS implementations".

## 5. PickNik status

Unchanged and still the primary white-box Quest target: `isTracked`/`trackingState` reach the
controller Transform, and `RosPublishers` drops them at the Odometry/TF boundary while re-stamping
with wall clock. The backend (ROS-TCP Endpoint, Pi observer) is ready; the blocker is a compatible
Unity editor plus an authorised Quest, not the testbed.

## 6. Research-claim utility matrix

| Framework | What it can support | What it cannot support | Why useful | Main limitation |
| --- | --- | --- | --- | --- |
| **Quest2ROS2** | native-ROS-side black-box behaviour under actual DDS; I3 source-time drop and I2 frame replacement; default-armed toggle semantics; stale-anchor-across-reconnect as a source-visible design gap | any claim about Quest-side tracking semantics; any actuation claim | external validity — a widely referenced public Quest→ROS 2 stack, not a research adapter | XR frontend and transport bridge are both outside the repository |
| **Docker_Teleop** | a complete XR→ROS→MoveIt Servo→Gazebo path with a real, source-visible validity gate; neutral-state recovery as a positive design pattern; the gate-semantics mismatch question | that occlusion actually trips the gate (must be tested on hardware) | the best simulator-backed, full-source principal target | ARM64 base image vs x86_64 host; real-hardware launch path exists in-tree and must be avoided |
| **OpenVR UR5e** | `VALID` vs `TRACKED` gap in a second XR API; grip deadman with explicit re-anchor; Gazebo-only, zero hardware risk | production-grade representativeness | independent XR-runtime family (OpenVR/SteamVR) | low-maturity single-commit repo; needs a separate Jazzy environment |
| **OpenArmX** | I3 preserve-then-drop inside one framework; freshness gate measured on the wrong clock; a latched override that bypasses the operator deadman | anything about the PICO frontend; the IK/joint-command half at runtime | sharpest single-framework I3 evidence; distinct UDP/PICO family | closed `openarmx_arm_driver`; frontend in a separate APK repo |
| **Spes** | actual Quest 3 hardware transition to an actual application-server callback; ROS/DDS/Pi propagation through a research adapter | native XR→ROS implementation count; actuation | strongest motivating hardware evidence in the project | ROS side is not native to the framework |
| **PickNik** | tracking state reaching the Transform and being dropped at the Odometry/TF publisher | any runtime or hardware behaviour yet | primary white-box Quest candidate | Unity editor + authorised Quest unavailable |
| **NVIDIA** | partial positive control: explicit `VALID` gating, invalid-pose hold/zero/rebaseline | that inferred-but-valid poses are blocked | the safe-design comparator | `TRACKED` bits not preserved; native runtime not run |
| **Reachy, NU-MECH, Legged, Homebrew** | positive controls: source-visible gates that suppress output when tracking/provider state is bad | downstream consequence claims | they prevent the study from only sampling systems with gaps | no included control consumer (or unconfirmed) |
| **xiaoxiaoxh** | source-visible direct-robot control path with no consumed tracking gate | any runtime result | high-risk downstream makes it a strong future case | runtime deliberately withheld until an audited inert stub exists |
| **XRoboToolkit, LTS0429, AgileX, xArm** | wire/host-path observations; ecosystem breadth | independent native confirmation | context only | opaque frontends; xArm shares Quest2ROS lineage |
| **VR-hand-bridge** | XR-runtime diversity (Godot OpenXR); prevalence of telemetry-only bridges | anything about control semantics | cheap breadth data point | no control consumer at all |
| **Nakama** | nothing at this identity | everything | methodological warning about README-based population counting | code lives in a third-party fork; `SOURCE_PATH_UNCONFIRMED` |

## 7. Selection-bias self-check

1. **Did we only pick frameworks that show problems?** No — and this session strengthened that.
   Docker_Teleop propagates and enforces a validity flag and fails to a neutral state; OpenVR UR5e
   gates on `bPoseIsValid`; Reachy, NU-MECH, Legged and Homebrew all gate upstream. The audit
   explicitly records these as design patterns, not as absence of findings.
2. **Did source availability distort the population?** Partly, and it is now labelled rather than
   hidden. Four systems (LTS0429, AgileX, XRoboToolkit, OpenArmX's frontend) are APK/vendor
   black boxes; Quest2ROS2's frontend is external. These are retained with `BLACK_BOX_*`
   observability instead of being dropped, which is why Quest2ROS2 can serve as the black-box
   principal.
3. **Did we count shared lineage as independence?** Explicitly guarded. xArm Quest is excluded
   from independent counting (shared Quest2ROS frontend); PickNik and Legged are recorded as two
   applications over one shared Unity ROS-TCP boundary, not two boundary designs.
4. **Does ROS-2-only sampling overstate generality?** It would, so the study keeps ROS 1 and
   non-ROS cases separate: xArm (ROS 1) and Reachy (direct WebSocket, no ROS) are reported as
   comparison cohorts and never folded into the ROS 2 principal count.
5. **Did we mix telemetry with control?** The control-depth axis exists precisely to prevent this.
   VR-hand-bridge, NU-MECH and Legged are `TELEMETRY_ONLY`/`ROS_PUBLISHED` and are never cited
   alongside Docker_Teleop or OpenVR UR5e, which reach `NATIVE_CONSUMER`.
6. **Was Pi reception overstated?** No. Every Pi result in this session is labelled `PI_RECEIVED`
   with `ACCEPTED_NO_SEMANTIC_GATING`, and the sink's own startup banner repeats that it performs
   no validation.
7. **Are tracking semantics equivalent across frameworks?** They are demonstrably **not**, and this
   is now a finding rather than an assumption: WebXR `emulatedPosition`, Unity
   `isTracked`/`trackingState`, Meta `OVRHand.IsTracked`, `OVRInput.GetConnectedControllers`,
   OpenVR `bPoseIsValid`/`eTrackingResult`, and OpenXR `POSITION_VALID`/`POSITION_TRACKED` are six
   different things. Docker_Teleop's connection-derived `isTracked` is the clearest warning against
   treating them as one concept.

## 8. Population summary

- Screened identities with verified repository + pinned revision: **18**.
- Distinguishable architecture families with inspected source: **12**.
- `HIGH_XR_ROS_CONTROL` with auditable source and a reachable native consumer **without hardware**:
  **3** (Quest2ROS2, Docker_Teleop, OpenVR UR5e).
- Frameworks with runtime evidence to date: **2** (Spes via research adapter, Quest2ROS2 natively).
- Positive controls retained: **5** (NVIDIA partial, Reachy, NU-MECH, Legged, Homebrew) plus
  Docker_Teleop's recovery behaviour.
- Excluded / dropped at current identity: Nakama (`SOURCE_PATH_UNCONFIRMED`), xArm (lineage),
  LTS0429 and AgileX (opaque, no auditable semantics).
