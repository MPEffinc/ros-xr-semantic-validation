# R01 — First experiment, DRAFT protocol (not frozen, not run): scoped M39 pilot on the real UR5e path

**Status.** This is a draft written on 2026-10-03.

- It is not frozen and nothing has been executed.
- It becomes frozen only after §9 pre-flight qualification, and only after the decision to run it.
- Sources: `cases/C01_…`, `cases/C02_…`, `audits/A01_…`, internal P1/P1b/F1–F3 results.

## 1. Research question

On a real XR→ROS teleop path, compare two ways of meeting a declared stop/resume contract:

- the **strongest per-app fixes**;
- a **ROS-side transition component** that changes no app.

Do both meet the contract under identical conditions? What is left over, and at what integration
cost?

Two parts are new relative to P1/P1b/F3:

- a physical outcome **not masked by the Servo singularity stop** (U46);
- the first execution of the M5 fix (re-anchor to the measured EE + fresh press) on a real app.

## 2. Protection policy (declared; violations are judged only against it)

| ID | Policy | Threshold |
|---|---|---|
| P_stop | After an interruption onset (runtime input deactivation, or grip release), EE travel beyond onset + 100 ms is limited | ≤ 5 mm, and joint speed ≤ 0.01 rad/s by onset + 300 ms |
| P_resume | When motion resumes, the commanded target is continuous with the **measured** EE at resume (no reference jump) | max distance between the first post-resume Servo target and the EE at resume ≤ 5 mm; EE travel in the first 300 ms ≤ hand displacement × scale + 5 mm |
| P_rearm | After a **runtime** interruption, motion resumes only after a fresh deadman press (release then press). Not required after the operator's own release/press. | binary |
| Normal (no false stop) | During uninterrupted grip-held motion, the EE tracks the scaled hand motion | tracking error ≤ 10 mm (median); no hold issued |

P_rearm is a **policy choice**. Automatic resume is also in use (Safe-ROS U44, OpenArmX), so
results are reported both with and without P_rearm.

## 3. Attacker, privileges and trust boundaries

- **Actors:** S0 (benign transitions: menu or focus loss, deactivation, release) only. No network
  attacker and no compromised app. S2 is out of scope (design: `semantic_evidence_framework/docs/07`).
- **Trusted:** monado-service (main `045931d`, unmodified), the collector, the transition component,
  Servo, JTC, Gazebo.
- **Untrusted for this pilot:** none. The app is honest but unmodified, so it is mistake-prone.
- **Pilot limitation:** everything runs in one container under one uid, as in F1–F3.

## 4. Arms (same input script, same evidence, same freshness, same initial state)

| Arm | What changes | Where |
|---|---|---|
| **B0** | nothing: the original `quest_teleop.py` → Servo → JTC | — |
| **B1 strongest per-app fixes** | **App copy** (a documented diff of `quest_teleop.py`): (a) on pose-invalid **or** release, set disengaged and require a release → press edge before publishing again (fresh press); (b) at engage, re-anchor to the **measured** EE pose (tf `base_link→wrist_3_link`) instead of the absolute constant (0.4, 0, 0.3); (c) publish `/teleop/engaged` (Bool). **Deployment node** `hold_on_disengage`: when `/teleop/engaged` falls, call Servo `pause_servo(true)` and send a JTC one-point hold at the measured state (re-sent after 0.1 s, as in P1b); on rise, `pause_servo(false)`. | app + one node |
| **C1 ROS-side transition component (no app change)** | Sits between the app and Servo (the app is remapped as in F3). **Interruption** = runtime evidence `¬(FOCUSED ∧ IO_ACTIVE ∧ ¬INPUTS_BLOCKED)` (libmonado collector, as in F3) **or** command silence > 100 ms. On interruption: pause Servo, send a JTC hold at the measured state, drop commands. **Resume** when evidence is active and commands flow for ≥ 100 ms: compute re-basing `Δ = EE_measured − target_first` (position; orientation as a relative rotation), apply `target' = target ∘ Δ` to all later commands until the next interruption, then unpause. | one node, no app change |
| (B1h, if the pre-flight budget allows) | B1 with fix (a)/(b) only, no hold node | isolates the hold contribution |

**Equal conditions across arms.** Same remote-driver input script, same xrizer v3 image, same
Monado build, same start joint state (§9), same Servo/JTC configuration, same evidence source and
freshness (50 ms) for any arm that uses runtime evidence, same capture window, and the same host
load recording.

**Information asymmetry, stated rather than hidden.** B1 sees the button edges (inside the app). C1
does not: libmonado exposes no input values and this app publishes no button topic. C1 therefore
**cannot** implement P_rearm, and this is reported as an information limit, not as a C1 failure.

## 5. Conditions (scripted with the Monado `remote` driver)

| ID | Script | Purpose |
|---|---|---|
| N0 | grip held, hand moves 0.05 m/s along the pre-qualified axis for 3 s | normal control (no false stop); tracking |
| N1 | grip held, move; **operator release** for 1.5 s while the hand moves 7 cm; press again; move | legitimate clutch (P_resume; P_rearm not required) |
| I1 | grip held, move; **runtime deactivation** 1.5 s (`mnd_sched` IO toggle) while the hand moves 7 cm; grip stays held; reactivate | the F3 scenario without the confound (P_resume, P_rearm) |
| I2 | as I1, plus a scripted release and press 1.0 s after reactivation | P_rearm satisfiable by a fresh press |
| I3 | fast motion 0.15 m/s; runtime deactivation onset mid-motion | P_stop (residual catch-up, M3) |

## 6. Measurements (all timestamped on one CLOCK_REALTIME; Servo also logs sim time)

| Level | Measured |
|---|---|
| Command | app output targets; arm-component output; Servo input; jump at resume (first post-resume target vs the last pre-interruption target, and vs the measured EE) |
| Controller | `pause_servo` calls and results; JTC hold messages; Servo status codes; JTC `controller_state` errors |
| Joint / EE | `/joint_states` (position, velocity); EE pose from tf at 100 Hz; travel after onset; settle time; EE jump at resume; tracking error in N0 |
| Integration cost | B1 diff lines and files (app + node); C1 lines; per-arm configuration items; decision latency |

## 7. Confound controls (the trial is invalid if any applies)

1. **Singularity / collision stop.** Any HALT_FOR_SINGULARITY (2), HALT_FOR_COLLISION (5) or
   DECELERATE_FOR_SINGULARITY (1/3) between 0.5 s before the first event and the end of evaluation.
   DECELERATE_FOR_COLLISION (4) is recorded. If it is present in all trials, the scene is checked in
   pre-flight and the status is reported.
2. **Orientation not settled.** EE rotation rate > 0.5 °/s in the 1 s before the first event. This
   was the P1 confound.
3. **App rate.** Below 15 Hz in the pre-event window. The xrizer pump runs at about 20 Hz in F3.
4. **Evidence path.** A collector gap > 50 ms outside designed events; collector → component
   latency is logged.
5. **Clock.** All wall times come from one container. Sim-time vs wall-time drift is logged and not
   used for decisions.
6. **Load.** The load average is recorded. There are no other experiments of ours concurrently;
   other teams' containers are noted.

## 8. Trials, time and environment

- **Pilot size.** 3 arms × 5 conditions × 3 repetitions = **45 trials** (+9 if B1h is included).
  - F3 was highly repeatable: 35.0 mm in 6/6 runs. With deterministic scripted input, repetitions
    mainly expose timing variance.
  - A cell whose repetitions disagree on a binary policy outcome is extended to 5.
- **Time.** About 100 s per trial (F3 bring-up plus 20 s capture), so about 75 min plus pre-flight
  (§9, about 30 min). Runs are sequential with no other load of ours.
- **Environment.** It exists:
  - image `f3-xrizer-bgpump:0989a7f-v3`;
  - the P1 workspace;
  - Monado main build;
  - lavapipe.

  No GPU change and no headset are needed.

## 9. Pre-flight qualification (required before freeze)

1. **Start configuration.** Before the app engages, drive the JTC to a joint configuration whose
   wrist_3 pose equals the app's engage target (0.4, 0, 0.3, `robot_home_rot`). Use IK from MoveIt.
   Apply it identically in all arms (deployment-level setup, logged).
   - If no non-singular configuration exists, pick the motion axis (±x, ±y, ±z) whose B0 N0/I1 runs
     show no singularity status.
2. **Qualification runs.** Run N0 and I1 under B0 for each candidate axis, 1 run each. Select the
   first axis with 0 invalidating statuses and settled orientation.
3. **Blocker.** If no axis qualifies, R01 is **BLOCKED_ENV**: the app's fixed absolute engage pose
   cannot be used confound-free. Two alternatives:
   - (a) a different UR5 base placement in the Gazebo world (deployment change, same for all arms);
   - (b) a kinematically different arm model, which is a larger change.
4. **Implementation.** Write the B1 app diff and the C1 component. Unit-test them host-only against
   recorded F3 streams.

## 10. Validity and decision rules (to be frozen with the protocol)

| Outcome | Interpretation |
|---|---|
| B1 meets P_stop, P_resume, P_rearm and Normal in all valid trials | **solved by existing per-app fixes on a real path** (M5/M3 confirmed physically). The cost is recorded as diff size and sites. |
| C1 meets P_stop, P_resume and Normal without app change, but not P_rearm | a common component gives **partial** coverage. Fresh-press resume needs button evidence the runtime does not expose. This is an observation limit and a concrete requirement. |
| C1 matches B1 on P_stop/P_resume with fewer app-side changes | **a necessary but not sufficient** condition for a system contribution. Sufficiency needs a second, structurally different real path. None is available (BLOCKED_ENV), so the claim stays open. |
| B1 fails through ordering between its fixes (e.g. a leaked command between unpause and re-anchor) | a residual integration problem. This is evidence *for* a contract-level component, if C1 does not show the same failure. |
| Both fail P_resume or P_stop for reasons unrelated to the arms (plant, controller tuning) | not interpretable for the arm question. Record it and change nothing post hoc. |
| Any arm shows a false stop in N0 or N1 | a normal-operation failure of that arm; reported with counts |

## 11. What this adds beyond existing results

| Gap in existing results | What this pilot adds |
|---|---|
| F3 measured a 35 mm **command** jump that was masked physically | a confound-free physical resume outcome on the same real path |
| M5's strongest fix was never executed | it is executed and measured, with its cost |
| No app-agnostic resume handling was tested | ROS-side re-basing + hold is tested |
| — | the information boundary (fresh press) is measured instead of asserted |

**What it cannot add:** a second real path, real headset transitions, a physical robot, or S2.
