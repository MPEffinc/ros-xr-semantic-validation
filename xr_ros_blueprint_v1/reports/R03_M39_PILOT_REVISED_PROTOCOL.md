# R03 — M39 stop/resume pilot, revised protocol (revises R01 after R02)

**Status (2026-10-03).**

- R01 is kept unchanged as the draft. This document replaces it for execution.
- §§1–9 and §11–14 were written before any Gazebo qualification run.
- §10 records the pre-flight. The protocol becomes frozen only with the freeze commit named in
  `experiments/M39_pilot/FREEZE.md`. Any later change to a rule needs a new protocol version.
- Code: `experiments/M39_pilot/` (arms, harness, tests, pre-flight tools).

## 1. Question

On one real XR→ROS path, take the strongest existing per-app fix (B1) and a ROS-side transition
component that changes no app (C1). Under the same scripted runtime and operator transitions:

- Which parts of a declared stop/resume contract does each one meet?
- What does each one fail?
- What does each one cost?

The baseline is the unmodified path (B0).

**Scope of any claim.** One real app (OpenVR UR5e `quest_teleop.py` @170dad5), synthetic runtime
input (Monado `remote` driver), and Gazebo. The trusted components are monado-service, the
collector, the arms, Servo, JTC and Gazebo. Nothing here generalizes to:

- a real headset;
- a physical robot;
- a compromised app;
- a second app path.

## 2. Stack (identical for every arm)

| Component | Version | Note |
|---|---|---|
| App | `quest_teleop.py` @170dad5 (B0, C1). B1 runs a copy of it. | unmodified for B0/C1 |
| OpenVR runtime | xrizer 0989a7f + 3 deployment patches (image `f3-xrizer-bgpump:0989a7f-v3`, `XRIZER_F3_LEGACY_ON_TEMP=1`) | app tick ≈ 20 Hz (pump) |
| OpenXR runtime | Monado main 045931d | unmodified |
| Consumer | MoveIt Servo 2.12.4 (P1 workspace config `ur_servo.yaml`, pose mode) → JTC 4.42.1 → Gazebo | unmodified |
| Start configuration | one JTC trajectory to the pre-flight joint configuration, before the runtime starts (§10) | deployment setup, same for all arms |

**Facts read from code that every arm inherits.**

- **Servo's `incoming_command_timeout` never trips on this path.** Servo uses sim time
  (`use_sim_time: True`), but the app stamps commands with wall time. `now − stamp` is therefore
  negative, so Servo keeps tracking its last pose target indefinitely (`servo_node.cpp`
  L291–317 @2.12.4). Its `new_pose_msg_` flag is not cleared, so after an unpause Servo would
  again track whatever `latest_pose_` holds.
- **JTC holds the measured state on a one-point trajectory** (P1b).

## 3. Arms

### 3.1 What each arm can observe (information table)

| Input | B0 | B1 (app copy) | C1 (ROS node) |
|---|---|---|---|
| Pose validity (`bPoseIsValid`) | app uses it (skips the tick) | yes | no (sees only the app's command stream) |
| Grip button level/edge | app uses the level | yes, edges taken only from valid & active ticks | **no**: libmonado exposes no input values, and the app publishes no button topic |
| Runtime client flags (FOCUSED, IO_ACTIVE, INPUTS_BLOCKED; 5 ms collector; ≤ 50 ms freshness; latched between polls) | no | **yes** (the same FIFO and reader as C1, an added cost) | yes |
| App command stream | — | own | yes (remapped `/m39/app_cmd`) |
| Measured EE (tf `base_link→wrist_3_link`), `/joint_states` | no | yes | yes |
| Servo `pause_servo`, JTC topic | no | yes | yes |
| Ground-truth button state (feeder script) | judging only | **never given to any arm** | **never given** |

### 3.2 Shared low-level code (counted once, used by B1 and C1)

`harness/m39_transition.py` and `harness/m39_evidence.py` implement the ordered transition chain:

1. **Suppress.** The caller stops publishing (B1) or forwarding (C1).
2. **Servo pause.** `pause_servo(true)`. The call waits for the service and is logged with its ack.
3. **Controller hold.** A JTC one-point hold at the measured joints. It is sent at once, again on
   the pause ack, and again 0.1 s later.
4. **Hold confirmed.** HELD once every arm joint speed is ≤ 0.01 rad/s for 0.1 s.
5. **Queue cleanup.** Servo's stale `latest_pose_` is overwritten by step 7 while Servo is still
   paused. Servo clears its smoothing and rolling window on unpause. The arms drop commands while
   not ACTIVE.
6. **Re-reference to the measured EE.** Done by each arm.
7. **Valid re-admission.** Each arm's own rule. The first, already re-referenced, target is
   published.
8. **Resume.** After 40 ms (2 Servo periods), `pause_servo(false)`. The arm becomes ACTIVE on the
   ack.

### 3.3 B1: strongest per-app fix (`arms/quest_teleop_b1.py`, diff vs original: +67 / −7 lines, every change marked)

- **(a) Any interruption** disengages, stops publishing and starts the ordered stop. That is:
  - pose invalid, or the right controller absent;
  - runtime evidence not ok, including a latched sub-tick deactivation;
  - a grip release.
- **(b) Fresh press required** after a pose-invalid or evidence interruption. The press counts only
  if a grip=false reading is taken on a tick where the pose is valid **and** the evidence is ok,
  followed by grip=true.
  - Readings from invalid or inactive ticks are ignored, because they read false (§10.1). A naive
    edge detector would take reactivation for a fresh press.
  - After an operator release, the release itself is that valid reading.
- **(c) Engage only from HELD.** The anchor is the **measured** EE (tf) instead of the constant
  (0.4, 0, 0.3) and `robot_home_rot`. The target is
  `p = p_anchor + 0.5·(h − h_engage)`, `R = R_anchor · (Q_engage⁻¹ · Q)`. This is the app's own
  formula with the anchor replaced.
- **(d)** The first target goes through the shared ordered resume.
- **Deliberate strengthening relative to R01.** B1 also receives the same runtime evidence as C1.
  Pose-invalid alone missed 3/3 sub-tick (30 ms) deactivations in the probe (§10.1). The cost is
  recorded.

### 3.4 C1: ROS-side transition component (`arms/c1_transition.py`; app unchanged)

- **Interruption** = evidence not ok (latched between 5 ms ticks), **or** app command silence
  > 100 ms. It stops forwarding and starts the shared ordered stop.
- **Re-admission** = HELD, evidence ok, and app commands flowing (every gap ≤ 100 ms) for ≥ 100 ms.
  **C1 cannot observe a fresh press.**
- **Re-basing** (an adapter to this app's command semantics):
  - offsets: `dp = p_EE − p_first`, `C = R_EE · R_first⁻¹`;
  - applied to every later command until the next interruption: `p' = p + dp`, `R' = C·R`.
  - This equals `R_EE · (R_first⁻¹ R)`, the same body-frame composition the app uses. Positions
    stay additive in `base_link` and are **not** rotated by C.
  - **Host check, two-axis rotations.** C1's code gives 0.000 mm / 0.000° against the
    fresh-re-anchor mapping. A full SE(3) left product would give 7.99 mm, and a right correction
    2.28° (`tests/rebase_math_run3.json`).

### 3.5 Integration cost (recorded per arm)

- lines changed or added, with files and sites;
- configuration items: remaps, FIFOs, services, topics, the tf frame;
- the information sources each arm needs (table 3.1);
- shared code, kept separate from code unique to each arm.

## 4. Conditions (scripted, `make_scenarios.py`; times in s after T0; axis `u` from §10)

All conditions share one hand timeline:

| Time | Segment | Hand motion |
|---|---|---|
| 2.0 | grip press | engage |
| 3.0–5.0 | A | translate 0.04 m/s along u (8 cm) |
| 5.0–6.0 | quiet | the pre-event window |
| 6.25–7.25 | W | translate 0.07 m/s (7 cm) + rotate 0.2 rad/s about hand-local y |
| 9.5–10.5 | C | translate 0.04 m/s (4 cm) |
| 11.0–12.0 | D | rotate +0.2 rad/s about hand-local x |
| 12.5–13.5 | E | translate 0.04 m/s + rotate −0.2 rad/s about local x |
| 15.5 | — | capture ends |

| ID | Transition actually executed | Purpose |
|---|---|---|
| N0 | none | normal operation; mapping; no false stop |
| N1 | **operator release** 6.0–7.5 (the hand moves during the release), press at 7.5 | legitimate clutch: P_stop, P_resume, Live (P_rearm not applicable) |
| I1 | **runtime IO deactivation** 6.0–7.5 (`mnd_sched`); grip held throughout; no new press ever | P_stop, P_rearm (hold must persist), P_resume where a resume occurs |
| I2 | I1 + operator release 8.5–8.8, press at 8.8 | P_rearm satisfiable; Live after a valid re-press |
| I3 | I1, but W's translation is 5.75–6.217 at 0.15 m/s, so onset is mid-motion | P_stop under motion (catch-up residual) |

Only these transitions are claimed:

- runtime IO deactivation (the libmonado `toggle_client_io_active`);
- operator release.

**Not claimed:** focus loss, inputs-blocked by another client, and tracking loss. Tracking loss
was probed only (§10.1). It looks identical to IO deactivation at the OpenVR API.

## 5. Timeline points (each logged separately, CLOCK_REALTIME wall_ns + CLOCK_MONOTONIC mono_ns)

1. **Injection effective time (onset).**
   - I*: `mnd_sched` return of the IO toggle.
   - N1/I2: the first feeder packet with the changed grip.
   - The arm's detection time is **never** used as the onset.
2. **State observed.** The collector line, or the app tick that saw pose-invalid or release.
3. **Arm decision.** The `interrupt`, `b1_engage` and `c1_readmit` log lines.
4. **Servo/controller processing.** `pause_call`/`pause_ack`, holds, and Servo status.
5. **Joint/EE response.** `/joint_states` (sim stamp + wall reception) and tf EE (100 Hz).

Sim time (`/clock`, decimated) is logged against wall time, giving the real-time factor. Decisions
use wall time only.

## 6. Policies and operational definitions (thresholds fixed here)

Notation:

- `t_on` / `t_end`: onset and end of the primary interruption (6.0 / 7.5 s).
- `t_fp`: ground-truth fresh press (N1: 7.5; I2: 8.8; I1/I3: none).
- EE: tf `wrist_3_link` in `base_link`.

The **partial contract** is {P_stop, P_resume, Normal, Live}. The **full contract** is the partial
contract + P_rearm. Both are reported.

| Policy | Applies to | Pass rule |
|---|---|---|
| **P_stop** | N1, I1, I2, I3 | S1: `max |p_EE(t) − p_EE(t_on+0.1)|` over `[t_on+0.1, t_end]` ≤ 5 mm; **and** S2: max arm joint speed over `[t_on+0.3, t_end]` ≤ 0.01 rad/s |
| **P_resume** | every resume event inside `[t_on, END]`. Resume events: B0 = the first Servo input after `t_end` (and after `t_fp` if a release intervened); B1/C1 = each `first_target_published` after an interruption | R1: the first Servo-input target after the resume is within 5 mm and 2° of the measured EE at that time; **and** R2: EE travel in the first 300 ms ≤ 0.5 × hand travel over `[t_r − 0.05, t_r + 0.3]` + 5 mm. A trial passes if all its resume events pass. **Not evaluable (NE)** if no resume event occurs (e.g. B1 in I1/I3). |
| **Normal** | N0 (all arms); for B1/C1 also no arm interrupt between engage + 0.5 s and `t_on` in every condition | No arm interrupt/hold after engage + 0.5 s (N0); settled tracking at 5.9 s within 5 mm / 2° of the engage-referenced mapping; mapping increments (below) pass |
| **Mapping increments** | N0, N1, I2 (all arms); I1/I3 descriptive | Between checkpoints 9.4 → 10.9 (translation), 10.9 → 12.4 (rotation) and 12.4 → 14.9 (combined): position increment vs `0.5·Δh` ≤ 5 mm; body-frame rotation increment `R_EE(a)⁻¹R_EE(b)` vs `Q(a)⁻¹Q(b)` ≤ 2° |
| **Live** (no permanent block after a valid re-press) | N1, I2 | L1: re-admitted ≤ 1.0 s after `t_fp` (B1/C1 `active`; B0 first Servo input); L2: mapping increments pass; L3: EE moves ≥ 2 mm along u within 0.5 s of 9.5 s. A hold that persists after a valid re-press is a **normal-operation failure**, not a success. |
| **P_rearm** (full contract only) | I1, I2, I3 | Permission level: no re-admission before `t_fp` (I1/I3: before END). For B1/C1, re-admission = an `active` event; for B0, any Servo input after `t_on`. Physical (reported): EE displacement from `p_EE(t_end)` over `[t_end, min(t_fp, END)]` ≤ 5 mm and 2°. |

**Further rules.**

- **N1 release hold.** The hold during an N1 release is the correct behaviour, not a false block.
- **P_resume in I2.** C1 resumes at 7.6 s with no press and is judged at every resume. B1 resumes
  at 8.8+ s.
- **No silent fallback.** If an arm cannot resume (unpause failure, evidence gap), the outcome is
  recorded as such.

## 7. Masking and validity (fixed before any formal trial)

**Masked, kept and reported.** A trial is marked `masked` if Servo status ∈ {1, 2, 3, 5, 6} occurs:

- in `[t_on − 0.5, END]`;
- or, for N0, in `[2.0, END]`.

The code, time and arm are recorded. Each policy measure whose window contains the status is
marked `masked`. Its pass/fail value is still reported, and it is counted separately. Status 4
(DECEL_FOR_COLLISION) is recorded.

**Outcomes, never removed** (with the cause attributed: arm, condition or evidence path):

- evidence gaps;
- fail-closed blocks;
- arm timeouts;
- unpause failures;
- singularity or collision statuses caused by an arm or a condition.

**Instrumentation-invalid** (a setup or measurement problem, rerun allowed). Only these:

- (i) a setup rc ≠ 0: bring-up timeout, start configuration not qualified (EE > 2 mm / 1° or not
  settled);
- (ii) the app client never FOCUSED by T0 + 2.0 (runtime/app path dead);
- (iii) a gap > 100 ms in the observer's EE or `/joint_states` samples inside `[1.5, END]`;
- (iv) a feeder packet gap > 100 ms;
- (v) for I*, `mnd_sched` res ≠ 0 or |return − target| > 5 ms;
- (vi) app output rate < 15 Hz in `[3.0, 5.9]` (the environment pump; same app loop in all arms).

**Reruns and extensions.**

- An invalid trial is rerun in the same slot, at most 2 times. All attempts are kept and listed.
- **Extension.** If the 3 valid repetitions of a cell disagree on any binary outcome (P_stop,
  P_resume, P_rearm, Normal, Live, masked), the cell gets 2 more repetitions, once only (label
  `EXT`). They are reported separately and combined.
- **No other trial is added, removed or rerun.**

## 8. Schedule

- 3 arms × 5 conditions × 3 repetitions = **45 trials**, in fresh containers, sequential, with no
  other load of ours.
- **Order.** Within each repetition block, the condition order is shuffled (`random.Random(39 + rep)`).
  Within each (condition, repetition), the arm order is the Latin rotation of [B0, B1, C1] by
  `(cond_index + rep) % 3`.
- **Recorded per trial:**
  - host load before and after;
  - container load (1 s);
  - app rate;
  - the collector's inter-sample gaps;
  - the evidence age at each decision;
  - the real-time factor.
- **Kept:** command, controller and joint/EE traces.

## 9. Analysis

`analysis/analyze_m39.py` is frozen with the protocol. It computes every §6 measure, §7 flag and
denominator per arm and condition:

- pass;
- fail;
- not evaluable;
- masked;
- instrumentation-invalid.

**Descriptive only:**

- jumps in mm and degrees;
- residual travel;
- stop and resume latencies at each timeline point;
- hold counts;
- evidence ages.

## 10. Pre-flight record

### 10.1 B1 detection check (done; `preflight/probe_detect_summary.json`)

The probe is an app-rate replica of the app's OpenVR reads that logs every tick (valid,
trackingResult, grip).

| Executed transition | What the app sees |
|---|---|
| IO off 1.5 s and 0.2 s | pose invalid (result 201) and grip false from the first tick after the toggle (45.6 ms) to the first tick after reactivation (45.6 ms). On that first valid tick the grip reads **true** (held), with no false/valid transient. |
| IO off 30 ms × 3 (sub-tick) | **not seen at all** (0 invalid ticks; tick period 50.0 ms) |
| Release + press **during** IO off | invisible to the app. It reads grip true at reactivation, so B1 conservatively requires another press. |
| Controller tracking loss (probe only) | the same signature as IO off (invalid, grip false) |

**Consequence for B1.**

- Pose-invalid alone covers deactivations ≥ 1 tick but misses sub-tick ones.
- Reading the grip on invalid ticks would fake a fresh press.

B1 therefore gets the runtime evidence (latched) and valid-tick-only edges. In the F3 recorded runs,
the app's last command came ≤ 44 ms before IO off and the first ≤ 45 ms after IO on, consistent
with this.

### 10.2 Implementation check (done; host only, deterministic; `tests/host_checks_summary_run3.json`)

Fake Servo/JTC/tf and a fake OpenVR replaying traces:

| Case | Input | Result |
|---|---|---|
| B1-T1 | recorded probe trace + collector | one engage; interrupt at 6.009 s; 0 commands after; awaits a fresh press at every later valid tick |
| B1-T2 | I2 synthetic | 0 commands 6.05–8.8; re-engage at 8.812; first target = measured EE (0.000 mm / 0.000°); published ≥ 35 ms before unpause |
| B1-T3 | N1 + 20 ms IO blip | re-engage at 7.514 after the release/press; the blip at 11.01 is latched → interrupt at 11.013; no commands after |
| C1-F3 | recorded F3 commands + collector | interrupt at 8.008; 0 forwarded in the window; re-admit at 9.658 (raw jump 61.6 mm with this fake EE) → first forwarded target = EE |
| C1-SIL | F3 commands with a 200 ms drop | `command_silence` at 5.061; re-admit at 5.311 |

All pass. Two bugs found and fixed before this run, both in the shared core (logged):

- the pause request was sent before the service existed;
- JSON logging of an array type.

### 10.3 Start configuration and axis (selection rule fixed before Gazebo runs)

**Offline IK** (`preflight/path_check.py` → `preflight/path_check.json`):

- 8 IK solutions of the app's engage pose.
- Every IK solution and translation axis was checked over the union workspace any arm can command:
  - d ∈ [−5, 125] mm along u;
  - EE orientation `H·Ry(a)·Rx(b)`, a, b ∈ [0, 0.2] rad;
  - the reported values are max cond(J) and the wrist-singularity margin.

**Rule.**

1. Keep solutions with every link origin ≥ 0.05 m above the ground, which excludes elbow-at-ground
   solutions 1, 3, 5, 6.
2. Keep union-path max cond ≤ 14 (Servo's lower threshold is 17, hard stop 30).
3. Try candidates in ascending max cond:

| Order | Solution | Axis | Max cond |
|---|---|---|---|
| 1 | sol2 | −z | 11.25 |
| 2 | sol2 | +z | 11.42 |
| 3 | sol2 | +y | 11.66 |
| 4 | sol2 | −x | 12.00 |
| 5 | sol4 | −x | 12.02 |
| 6 | sol4 | +z | 12.08 |

**Gazebo qualification** (B0 app, **normal scripts only**: N0 and QF, which is I3's input with no
deactivation). A candidate passes iff:

- start setup qualifies;
- 0 Servo statuses ≠ 0 from engage to END;
- EE rotation rate ≤ 0.5°/s in [5.0, 5.9];
- the §6 Normal settled check and the mapping increments pass;
- the app rate is ≥ 15 Hz.

The first passing candidate is used. **No interruption condition is run for selection.**

**Budget.** ≤ 6 candidates × 2 runs, ≤ 30 min. If none passes, the result is **BLOCKED_ENV**. A
different arm model would need a separate protocol.

**Smoke (excluded from results).** One N1 run each for B1 and C1 on the chosen candidate, as a
full-stack plumbing check. Any fix is recorded, and the smoke is repeated.

### 10.4 Result

Recorded in `experiments/M39_pilot/FREEZE.md`.

## 11. Decision rules

| Observation | Reading |
|---|---|
| B1 meets the full contract in all valid, unmasked trials | the stop/resume combination on this path is **solved by existing per-app fixes** (with their cost) |
| C1 meets the partial contract but fails P_rearm | a common component gives partial coverage. A fresh press needs button evidence the runtime does not expose (an information limit, and a concrete requirement). |
| C1 matches B1 on the partial contract with fewer app-side changes | necessary but not sufficient for a system contribution. It needs a second, structurally different path (not available). |
| A B1 failure from a bug or race | find the root cause, check whether existing techniques fix it, keep the first failure, record the fixed version separately. **It is not by itself evidence that a new method is needed.** |
| A masked or plant-caused failure in both arms | not interpretable for the arm question; recorded |

## 12. What 3 repetitions cannot show

- the absence of rare failures;
- universal safety;
- a distribution of timing.

This is exploratory, with deterministic scripted input.

## 13. Differences from R01 (summary)

- B1 has runtime evidence, valid-tick edges, a HELD-gated re-anchor and the ordered resume.
- There are partial and full contracts, plus the Live and mapping-increment criteria.
- Masked trials are kept, not invalidated.
- The neutral pre-flight selects on normal trajectories only.
- The SE(3) re-basing is specified and tested.
- Timeline points are separated.
- B1h is dropped.

## 14. Not done here

- B1h and a second app are excluded by scope.
- No sheets are used.
