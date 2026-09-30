# 08 — New Gap Search after KILL

Follows brief §10–14. Literature: `../literature/new_gap_matrix.md` (≈ 125 entries across three passes;
evidence levels per entry). All arXiv IDs named here were checked to exist on 2026-09-30. Candidate
formulations are **our inference (D)** unless a quote is attributed. "PROMISING" would not mean novelty is
confirmed; no candidate below reached it.

Excluded directions were respected (list in the brief). Where a candidate borders one, the border is stated.

## 1. Where the literature leaves XR + ROS jointly uncovered

1. **XR teleop systems synthesise robot state, not just display it.** Examples: EKF extrapolation on the
   headset in TeleXR (2506.01135); digital twins with objects held at their "last valid pose" (surgical VR
   twin 2609.25527); generative predictive displays (2605.09670).
   - The literature measures how usable these are.
   - Nobody bounds how far the rendered view may diverge from the robot's authenticated state.
2. **Telemetry authenticity is not physical truth.** Shen et al., "Seeing is Not Believing" (2609.08280) —
   "securing telemetry in transit does not guarantee it reflects physical reality" — propose signing at the
   sensor.
   - Their evaluation uses RViz, not XR.
   - Signing does not cover the stages *after* measurement (twin update, prediction, reprojection).
3. **Safety filters and shared autonomy change commands after the operator issues them** (BarrierIK
   2603.01705, SAPS 2606.15568, ByteDance VR+VLA 2511.00139). None of these papers analyses security or
   operator-visible consequences.
4. **Timing analysis for ROS 2 treats the human–machine interface as lowest criticality.** Yano & Azumi
   2607.04129 PP3; they state that a joint freshness/safety model "remains open" (TP2, TP5). In XR
   teleoperation, however, the HMI originates commands.
5. **The operator-facing layer is the least mature.** The quadruped teleop security survey (2602.23404)
   places operator-layer / VR defenses at TRL 3–5.

## 2. Candidates

Each candidate is refuted against generic solutions first (brief §13). Fields 1–13 of brief §12 follow.

### N1 — View-to-execution consistency bound for XR teleoperation

1. **Problem.** The operator commands against a *rendered* robot/scene state — twin, prediction,
   reprojection — that ROS 2 components produce and the XR client transforms. Nothing binds that rendering
   to (a) the robot's authenticated current state and (b) the command stream ROS 2 will actually execute
   after planners and safety filters.
2. **Motivating example.** A predictive display hides divergence by design: TeleXR pauses prediction "to
   avoid abrupt visual changes". Meanwhile a safety filter alters the executed command. The operator's
   next command is then based on a view that corresponds to neither the robot's state nor its future
   motion.
3. **Threat model.**
   - Faults: stale twin, extrapolation error.
   - Adversaries: an in-path party able to delay or reorder telemetry within an authenticated channel, or
     a component that alters the render pipeline.
   - Excluded: the operator's own device OS.
4. **Why security/safety.** Human-in-the-loop decisions are the last safeguard. Nagaraja et al.
   (2604.27267, paraphrase-level) note that tampering "can mask unsafe robot behavior, eliminating the
   human-in-the-loop safeguard".
5. **Why ROS.** The authenticated state, planners and safety filters live in ROS 2. The bound has to be
   computed against the executed command stream there.
6. **Why XR.** The divergence arises in XR-specific stages: headset-side prediction, reprojection, twin
   compositing at display rate.
7. **Strongest related work.**
   - Shen et al. 2609.08280: sensor signing.
   - Puppeteer-style command-vs-state ghost overlays.
   - Predictive-display literature.
   - Arya-style AR output policies: these cover app placement, not robot-state correctness.
8. **Strongest generic solution.** Signed telemetry + staleness indicator + command-vs-reported-state
   threshold with stop.
9. **Why it may not suffice.**
   - Signatures cover only measured samples, not derived rendered state.
   - A staleness badge does not bound spatial error in the *predicted* view.
   - Command-vs-state checks ignore the post-filter command the robot will execute next.
   - **Refutation risk:** a combination of (i) rendering predicted state only from signed samples with an
     explicit error envelope, (ii) the robot publishing its post-filter command, and (iii) rejecting commands
     whose view basis is outside an envelope may be a straightforward integration of known pieces.
10. **Expected method.** A render-side envelope, computed from signed state, known prediction error and
    the published post-filter command, displayed as a geometric bound. The robot-side check refuses
    commands issued against an out-of-envelope view.
11. **Expected contribution.** A measurable divergence metric between rendered view and executed
    trajectory. Evidence on whether existing predictive displays violate it under faults and delays. A
    minimal enforcement mechanism, if needed.
12. **Minimum pilot.** Use a simulator plant (Gazebo, MoveIt Servo — images already local). Record the
    ground-truth robot state and a re-implemented predictive display (e.g. an EKF like TeleXR's). Inject
    delay, loss and filter intervention, and measure view-vs-truth error over time. **Before any novelty
    claim**, test whether the generic combination in §9 already keeps the error bounded.
13. **Kill condition.** The generic combination (signed state + rendering only from signed samples +
    published post-filter command + staleness stop) bounds the divergence in the pilot. Or the divergence
    only matters when it is already visible as a staleness badge (→ excluded "safety warning UI").

**Border with excluded directions:** close to "XR input timestamp checking" and "safety warning UI". It
stays distinct only if the object is the integrity of *rendered derived state* against *executed* state,
not input freshness or a display cue.

**Verdict: NEEDS PILOT.**

### N2 — Human-in-chain freshness/safety bound (from Yano & Azumi TP2/TP5, PP3)

- **Problem.** End-to-end cause-effect chain analysis stops at the HMI. In teleoperation the chain is
  robot sensor → ROS 2 → renderer → human decision → command → robot. No analysis gives the data age of
  what the operator saw when commanding, or ties it to a safety mode change.
- **Generic solution.** Carry the observation timestamp of the view in each command and reject commands
  whose basis is too old.
- **Refutation.** That is exactly "XR input validity / timestamp checking", which the closed S5 study
  already covered (freshness F100/F250/F500 met by existing baselines).
- **What would be new.** Only the formal RT-analysis model including a human stage. Human reaction time is
  not a schedulable task, so the model is weak.
- **Why XR / why ROS.** Weak — any teleop HMI works.
- **Kill condition:** met by S5 prior internal results.

**Verdict: WEAK** (collides with an excluded direction and prior internal evidence).

### N3 — Operator attribution of command modification (filter / blend / fault / attack)

- **Problem.** With BarrierIK- or SAPS-style shared autonomy, the executed command differs from the
  operator's. The operator cannot tell whether the cause is the safety filter, the policy blend or a fault.
- **Generic solutions.** Publish filter activation and blend weight (ROS topics) and visualise them; log
  them; runtime monitors on filter invariants.
- **Refutation.** Publishing and displaying the modification cause is a straightforward integration.
  Without a verification mechanism it is the excluded "safety warning UI".
- **Why XR.** Weak. Why ROS: medium.
- **Kill condition:** met unless the attribution must hold against a component that lies about its own
  activity, which reduces to N1 or to generic attestation.

**Verdict: WEAK.**

### N4 — Security of operator interventions used as learning signals (ROVE 2606.17011, APO-style labels)

- **Problem.** Takeover timing becomes an RL/IL label.
- **Refutation.** This is the excluded "generic training-data integrity". This repository's own
  `xr_demo_integrity` study closed with NO_REAL_THREAT_BOUNDARY for the collection path: the operator's
  input authority equals its influence on the robot.
- **Kill condition:** met.

**Verdict: KILL.**

### N5 — Adversarial manipulation of agreement-based arbitration (SAPS-style)

- **Problem.** If the arbitration weight grows when policy and operator agree, a steered policy could gain
  control weight gradually.
- **Generic solutions.** Bounded authority (cap the policy weight), CBF safety filter on the blended
  command, policy integrity (signed models).
- **Refutation.** A cap plus a safety filter bounds the physical effect regardless of the weight.
- **Why XR / why ROS.** Neither is essential; any shared-autonomy teleop works.
- **Kill condition:** met by a bounded-weight arbitration + CBF.

**Verdict: WEAK.**

### N6 — Effect-level authorization of an authenticated XR client (Yano & Azumi PP3; Picaros NDSS'24; SROS2)

- **Problem.** SROS2 decides who may publish, not which physical effects an authenticated
  low-criticality HMI partition may cause.
- **Generic solutions.** Command envelopes (joint/velocity/workspace limits), CBF safety filters, IFC
  (Picaros), per-role parameter bounds.
- **Refutation.** Effect bounds for teleop commands are standard safety limiting.
- **Border.** Close to the closed Authority Continuity study.
- **Kill condition:** met by envelope + filter.

**Verdict: KILL.**

### N7 — Multi-view consistency in the XR scene as a defense against forged telemetry

- **Problem.** The XR scene already fuses stereo camera, twin and point cloud. Shen et al. note that live
  multi-view forgery is "prohibitively expensive at scale".
- **Generic solution.** Multi-sensor consistency / secure state estimation (e.g. the secure safety filter
  2505.06845).
- **Refutation.** This is generic sensor fusion anomaly detection placed in the renderer. XR adds only
  where the check runs.
- **Kill condition:** met unless the check must use rendered (derived) views, which folds into N1.

**Verdict: WEAK.**

## 3. Summary table

| Candidate | Problem | Evidence | Strongest prior solution | Remaining gap | XR necessity | ROS necessity | Method novelty potential | Experimental feasibility here | Main risk | Verdict |
|---|---|---|---|---|---|---|---|---|---|---|
| N1 view-to-execution consistency | rendered derived state vs authenticated + post-filter executed state | A/B (TeleXR, twin, Shen et al., BarrierIK, SAPS); gap itself D | Shen et al. signing + staleness stop + command-vs-state ghost | bounding derived (predicted/twinned) view against executed trajectory | **medium–high** (headset-side prediction, reprojection) | **medium** (post-filter command, authenticated state in ROS 2) | uncertain — may be an integration | **medium**: Gazebo/MoveIt Servo sim available; no headset (render stage must be emulated → provenance label) | reduces to known pieces or to warning UI | **NEEDS PILOT** |
| N2 human-in-chain freshness | data age of the operator's view in RT analysis | A (Yano & Azumi) | view timestamp + reject (S5) | formal model with human stage | low | medium | low | high | excluded timestamp checking; S5 covers | WEAK |
| N3 modification attribution | why the executed command differs | A/B | publish + visualise filter/blend state | trustworthy attribution | low | medium | low | high | excluded warning UI | WEAK |
| N4 intervention-label integrity | takeovers as learning labels | A/B (ROVE) | generic data integrity | none beyond generic | low | low | low | — | excluded; prior NO_REAL_THREAT_BOUNDARY | KILL |
| N5 arbitration manipulation | policy gains control weight | A/B (SAPS) | bounded weight + CBF | none shown | low | low | low | medium | generic | WEAK |
| N6 effect-level authorization | physical effects of an authenticated HMI | A/B (Picaros, Yano) | envelopes + CBF + IFC | none shown | low | medium | low | high | standard safety limiting; Authority Continuity overlap | KILL |
| N7 multi-view consistency | forged telemetry vs multi-view XR scene | A (Shen et al.) | secure state estimation | placement only | low–medium | low | low | medium | generic fusion | WEAK |

## 4. Recommendation

Only **N1** survives the generic-solution test, and only provisionally. Its first task is to try to kill
it: a sim pilot that checks whether the generic combination (signed samples, prediction only from signed
state with an error envelope, published post-filter command, staleness stop) already bounds the
view-vs-execution divergence.

Honest limits for the pilot:
- No headset exists here, so the XR render stage would be a re-implemented predictive display fed by the
  simulator. Pilot results would therefore be UPSTREAM/SYNTHETIC-grade for the XR side, and could kill N1
  but not establish novelty.
- A real-headset follow-up would need the lab Quest and an operator.
