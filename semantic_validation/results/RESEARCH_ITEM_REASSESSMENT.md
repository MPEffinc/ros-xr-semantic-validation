# Research Item Reassessment

Date: 2026-09-07. Decision on entry: `GO — NOT STRONG GO`.

## 1. Is the research item well-founded at the population level?

**Yes, and better founded than before — but for a partly different reason than originally framed.**

The original framing leaned toward "safety-relevant XR semantics are lost on the way to ROS". The
audited population does not support that as a uniform story, and it does not need to. What the
population does support is sharper:

> Across independent XR→robot stacks, the *same* safety-relevant semantic is handled with
> incompatible contracts at each boundary — preserved here, re-derived there, gated on a
> proxy elsewhere, dropped in between — and the raw API notions being gated are not equivalent
> across XR runtimes.

Evidence for that statement now spans four XR APIs and multiple unrelated implementations:

- A gate that exists, propagates, and is enforced end-to-end but keys on **controller connection**
  rather than pose validity (Docker_Teleop, `HandPoseSender.cs:1242-1244` →
  `servo_command_bridge.py:123-125`).
- A gate that reads the weaker of two available OpenVR flags, so out-of-range tracking is
  indistinguishable from healthy tracking (OpenVR UR5e, `quest_teleop.py:49`), reproducing the
  `VALID`-vs-`TRACKED` gap previously seen only in NVIDIA's OpenXR path.
- Source time transported across one internal boundary and discarded at the next inside a single
  framework, leaving a freshness gate that measures the wrong clock (OpenArmX,
  `..._bridge_vr_node.cpp:510-525` vs `..._teleop_vr_node.py:356-376`).
- A control node with no validity concept at all, a default-armed latching toggle, and anchors
  that survive a transport disconnect (Quest2ROS2, `robot_arm_controller_base.py:89,220-221,
  334-384`), now demonstrated under actual ROS 2 transport.
- Genuine upstream gating in several systems (Reachy `IsPoseValid` + stability delay, NU-MECH
  `IsTrackedDataValid`, Legged `XRHand.isTracked`, Homebrew fallback gate, NVIDIA `VALID` +
  hold/zero/rebaseline), which keeps the study from being a one-sided defect hunt.

## 2. Paper shape

- **Shape A — cross-stack XR→ROS semantic contract study.** Best supported. Source-architecture
  breadth is real (12 families), the invariant axes discriminate meaningfully between systems, and
  two runtime demonstrations exist. Its weakness is that runtime coverage is 2 of 12 families.
- **Shape B — XR→robot semantic contract study with ROS as the principal cohort.** Also viable and
  slightly more honest about Reachy (non-ROS, direct WebSocket) and the vendor stacks, which are
  currently reported as adjacent cohorts. Choosing B would let the non-ROS and ROS 1 cases carry
  weight instead of being footnotes.
- **Shape C — narrower tracking/freshness semantic-loss study.** Fully supported today and could be
  written now, but it discards the most interesting material (gate-semantics mismatch,
  preserve-then-drop) in favour of the least novel claim.

**Recommendation: Shape A, with Shape B as the fallback** if the second runtime confirmation does
not materialise. Shape C is a retreat position, not a target.

## 3. Decision

**`GO — NOT STRONG GO` is maintained.**

Reasons it does not move up:

- No E5/E6 evidence exists. No Quest was connected in this session, and no actual XR transition was
  observed for any framework.
- The only actual-XR-hardware evidence in the project remains Spes, whose ROS boundary is a
  research adapter rather than the framework's own.
- Runtime confirmation exists for two families only, and both are E2 with synthetic sources.

Reasons it does not move down:

- The population is materially stronger than at the last checkpoint: three `HIGH_XR_ROS_CONTROL`
  systems now have auditable source **and** a native consumer reachable without any hardware
  (Quest2ROS2, Docker_Teleop, OpenVR UR5e), where previously the only reachable consumer was a
  research adapter.
- The `VALID`-vs-`TRACKED` gap replicated in a second, unrelated XR API materially improves the
  generality argument.
- Positive controls are intact and growing, which protects the claim from being a selection
  artefact.

## 4. What would justify `STRONG GO CANDIDATE`

All three, in order:

1. **A second independent runtime confirmation with a native consumer.** Docker_Teleop D1–D5 in
   Gazebo would provide this at E2 with `UPSTREAM_FAITHFUL_REPLAY` — a genuinely different
   architecture family from Quest2ROS2, with a simulator consequence rather than only Pi reception.
2. **A native XR-hardware transition on a framework whose own ROS boundary is exercised.** PickNik
   is the designated candidate; the blocker is a Unity editor and an authorised Quest, not the
   testbed.
3. **The gate-semantics question answered on hardware:** does optical occlusion actually change
   `OVRInput.GetConnectedControllers()` (Docker_Teleop) or the Unity `trackingState` bits
   (PickNik)? If occlusion leaves connection-derived flags true, the mismatch finding becomes a
   hardware-confirmed result rather than a source-level inference.

## 5. What must not be claimed today

- That any framework is `vulnerable`, `unsafe`, `secure`, or `fail-safe`.
- That a robot moved, an actuator executed, or a native robot controller accepted a command. In
  every run this session the original downstream controller was **absent**.
- That Pi reception is actionability. `PI_RECEIVED` is the ceiling for the sink.
- That source-architecture breadth (12 families) is runtime generality (2 families).
- That `emulatedPosition`, `isTracked`, `trackingState`, `IsTracked`,
  `GetConnectedControllers`, `bPoseIsValid`, `eTrackingResult`, `POSITION_VALID` and
  `POSITION_TRACKED` mean the same thing. The Docker_Teleop case is the standing counterexample.

## 6. Immediate next actions

1. Docker_Teleop Tier-2 adaptation (see
   [FRAMEWORK_TESTBED_ADAPTATION_PLAN.md](FRAMEWORK_TESTBED_ADAPTATION_PLAN.md)).
2. OpenVR UR5e fake-`openvr` runtime in a Jazzy container — trial V2 is the decisive one.
3. OpenArmX bridge-only UDP run for the preserve-then-drop I3 demonstration.
4. Install a Unity 6000.1.6f1-compatible editor to unblock PickNik; keep the Quest session
   robot-free and follow the T0/T1 protocol already written.
