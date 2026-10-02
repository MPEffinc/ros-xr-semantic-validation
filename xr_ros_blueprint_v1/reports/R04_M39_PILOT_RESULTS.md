# R04 — M39 stop/resume pilot: results (45 trials, 2026-10-03)

| | |
|---|---|
| Protocol | `R03_M39_PILOT_REVISED_PROTOCOL.md`, frozen at commit `467c223` (`experiments/M39_pilot/FREEZE.md`) |
| Raw data | `experiments/M39_pilot/raw/formal/` (ignored). Per-file sha256 is in `experiments/M39_pilot/results/M39_RAW_SHA256.txt` (1149 files, including the pre-flight and host checks). |
| Per-trial measures | `results/m39_campaign_trials.json` (frozen `analyze_m39.py campaign`, sha256 `3d1be52b…`) |
| Cell counts | `results/m39_summary.json`, from `analysis/summarize_m39.py`, which counts only. It was added after the freeze and computes no measure. |
| Logs | `results/m39_campaign.log` and `results/m39_runner.log` |
| Scope | One real app (OpenVR UR5e `quest_teleop.py` @170dad5) on xrizer v3 + Monado main, with synthetic input from the `remote` driver; MoveIt Servo 2.12.4 → JTC → Gazebo. No headset, no physical robot, no second app path, no compromised app. Executed transitions: runtime IO deactivation and operator release only. |

## 1. All attempts

- **Attempts.** 46 for 45 slots.
- **Instrumentation-invalid.** 1: `T01_B0_I1_r1`, with a `/joint_states` gap > 100 ms. It was rerun as
  `T01_B0_I1_r1_rerun1` (valid). Both attempts are kept.
- **Valid.** 45/45 slots.
- **Masked.** 0 trials. There were no Servo statuses in {1, 2, 3, 5, 6} in any trial.
- **Status 4.** DECEL_FOR_COLLISION was recorded in every trial: the forearm–wrist_2 proximity found
  in pre-flight, with a tracking effect ≤ 0.33 mm. It is descriptive and listed per measure in the
  JSON.
- **Extension rule (R03 §7).** No cell had disagreeing repetitions, so no extension trials were run.
- **Environment.**
  - Host load (1-min) before each trial was 6.4–18.7. This includes the other teams' 3 containers
    and our own Gazebo; no other experiment of ours was running.
  - App output rate: 20.0–20.3 Hz.
  - Collector inter-sample gaps ≤ 12.3 ms.
  - Gazebo real-time factor: 0.69–0.71.

## 2. Results per arm and condition (3 valid repetitions each)

| Cell | P_stop | P_resume | Live | P_rearm | Normal | Partial / full contract |
|---|---|---|---|---|---|---|
| B0 N0 | — | — | — | — | 3/3 | ✓ / ✓ |
| B0 N1 | 3/3 | **0/3** | 3/3 | n/a | — | ✗ / ✗ |
| B0 I1 | 3/3 | **0/3** | — | **0/3** | — | ✗ / ✗ |
| B0 I2 | 3/3 | **0/3** | **0/3** | **0/3** | — | ✗ / ✗ |
| B0 I3 | **0/3** | **0/3** | — | **0/3** | — | ✗ / ✗ |
| B1 N0 | — | — | — | — | 3/3 | ✓ / ✓ |
| B1 N1 | 3/3 | 3/3 | 3/3 | n/a | — | ✓ / ✓ |
| B1 I1 | 3/3 | NE (no resume) | — | 3/3 | — | ✓ / ✓ |
| B1 I2 | 3/3 | 3/3 | 3/3 | 3/3 | — | ✓ / ✓ |
| B1 I3 | 3/3 | NE (no resume) | — | 3/3 | — | ✓ / ✓ |
| C1 N0 | — | — | — | — | 3/3 | ✓ / ✓ |
| C1 N1 | 3/3 | 3/3 | 3/3 | n/a | — | ✓ / ✓ |
| C1 I1 | 3/3 | 3/3 | — | **0/3** | — | ✓ / ✗ |
| C1 I2 | 3/3 | 3/3 (2 resumes each) | 3/3 | **0/3** | — | ✓ / ✗ |
| C1 I3 | 3/3 | 3/3 | — | **0/3** | — | ✓ / ✗ |

**Denominators per policy** (valid, unmasked trials):

| Arm (pass / applicable) | P_stop | P_resume (pass / evaluable) | Live | P_rearm | Normal |
|---|---|---|---|---|---|
| B0 | 9/12 | 0/12 | 3/6 | 0/9 | 3/3 |
| B1 | 12/12 | 6/6 (6 NE) | 6/6 | 9/9 | 3/3 |
| C1 | 12/12 | 12/12 | 6/6 | 0/9 | 3/3 |

## 3. Physical numbers (ranges over the 3 repetitions)

| Measure | B0 | B1 | C1 |
|---|---|---|---|
| Resume, runtime case (I1): first Servo target vs measured EE | **47.9 mm, 11.46°** | no resume (hold kept) | 0.00 mm, 0.00° |
| EE travel in the first 300 ms after resume (I1; allowed 5 mm) | **20.0–23.1 mm** | — | 0.0 mm |
| Resume, operator re-press (N1): target vs EE | **40.0 mm** (absolute re-anchor to (0.4, 0, 0.3)), 0° | 0.00 mm | 0.00 mm |
| I2 second resume (B0 absolute re-anchor after the press) | 87.9 mm, 11.4° | — | — |
| Stop under motion (I3): EE travel after onset + 100 ms | **10.2–13.5 mm** | 1.6–2.8 mm | 0.0–0.1 mm |
| I3: max joint speed after onset + 300 ms (limit 0.01 rad/s) | 0.051–0.064 rad/s | 0.0036–0.0073 rad/s | ≤ 0.0001 rad/s |
| Arm detection delay after onset: I* | — | 9–21 ms (pose invalid, at the app tick) | 3–10 ms (evidence) |
| Arm detection delay after onset: N1 | — | 5–11 ms (release) | 60–64 ms (100 ms command-silence rule) |
| Re-admission after a valid press (N1, I2) | 0.003–0.01 s | 0.203–0.209 s | 0.158–0.188 s |
| Response latency to the first hand motion after the press (L3) | 0.40–0.72 s | 0.39–0.45 s | 0.41–0.46 s |
| Mapping increments after resume (translation, rotation, combined) | ≤ 1.0 mm / 0.61° (N1, I1); I2 first segment 6.9–8.1 mm / 6.1–6.6° | ≤ 0.99 mm / 0.46° | ≤ 1.07 mm / 0.52° |
| EE motion before any fresh press (I1, I3) | 72–88 mm, 16.2° | **0.0 mm, 0.0°** | **40.0 mm, 11.4°** (follows the hand without a press; no jump) |
| Normal (N0): increment error, false interrupts | ≤ 0.74 mm / 0.39°, — | ≤ 0.87 mm / 0.44°, 0 | ≤ 0.76 mm / 0.48°, 0 |

**Why B0 fails Live in I2.**

- B0 re-admitted at once (L1 0.01 s) and responded (L3 0.64–0.72 s).
- At 8.8 s its absolute re-anchor jump (87.9 mm) was still being executed during the first increment
  window (9.4–10.9 s).
- So the Live failure is a consequence of B0's resume jump, not a permanent block.

## 4. What the results show (per the frozen decision rules, R03 §11)

1. **B0 resume jump, now physically unmasked.** On this path and start configuration, the
   unmodified app's resume jump is executed by the robot. After a runtime deactivation (grip held
   through it), the app resumes with no fresh press and its old offset. The target jumps 47.9 mm and
   11.5°, and the EE moves 20–23 mm within 300 ms.
   - F3's 35 mm command-level jump was masked by the singularity halt; here it is not. This run's
     47.9 mm also includes the position shift that the 0.2 rad hand rotation causes through
     xrizer's raw-pose offset.
   - After an operator release, the app re-anchors to its fixed absolute pose: a 40 mm jump back to
     the start.
   - Under motion, the stop leaves 10–14 mm of catch-up residual. That is M3: Servo keeps tracking its
     last target, and on this path its timeout never trips (sim-time vs wall-stamp).
2. **B1 meets the full contract in every valid trial** (all 15 trials in its 5 cells). B1 is the strongest
   existing per-app fixes: a fresh press from valid ticks, a re-anchor to the measured EE, runtime
   evidence, and the ordered pause → hold → re-reference → publish → unpause.
   - No B1 bug or race appeared in the formal runs. The two bugs found earlier were in the shared
     core (pause before service, log serialisation). They were found by the host checks and fixed
     before freeze.
   - By rule, this is **"solved by existing per-app fixes on this real path"**, at the cost in §5.
3. **C1 meets the partial contract without changing the app** (P_stop, P_resume, Normal, Live; 12/12
   trials with interruptions).
   - It re-bases correctly through translation, rotation and combined motion (increments
     ≤ 1.07 mm / 0.52°, matching B1).
   - It removes the jump in every case, including B0's absolute re-anchor after an operator re-press,
     which it re-bases.
   - **It fails P_rearm in 9/9 runtime-interruption trials.** It re-admits 0.20–0.25 s after
     reactivation without a press, then follows the hand (40 mm / 11.4° without any press in I1/I3).
     It cannot observe the button on this path. This is an information limit: libmonado exposes no
     input values, and this app publishes no button topic. Under the full contract, it is a failure.
   - C1 also detects an operator release 50 ms later than B1 (the 100 ms silence rule). P_stop
     still passed, because the release happened at rest.
4. **C1 versus B1, on the decision rule "C1 matches B1 on the partial contract with fewer app-side
   changes."** This holds here, so the necessary condition is met. **It is not sufficient for a
   system contribution:**
   - only one app path exists;
   - B1 is cheap for this app;
   - C1 needs an app-specific command-semantics adapter;
   - the full contract still needs the app (or a button on the wire).

## 5. Integration cost (counted from the frozen code)

| | B1 (per-app) | C1 (ROS-side) |
|---|---|---|
| App change | `quest_teleop.py` copy: +67 / −7 lines (1 file; sites: pose-validity branch, grip branch, engage/anchor, target formula, resume call) | none (one topic remap) |
| Own component | — | `c1_transition.py` 106 lines |
| Shared low-level code (counted once) | `m39_transition.py` 146 lines + `m39_evidence.py` 35 lines | same |
| Information needed | pose validity, button (app-internal), runtime evidence FIFO into the **app process**, tf, Servo pause service, JTC topic | app command stream, runtime evidence FIFO, tf, Servo pause, JTC; **knowledge of the app's command semantics** (positions additive in `base_link`, rotation `R_anchor·R_rel`) |
| Configuration items | app launched with `M39_EV_FIFO`, `M39_ARM_LOG`; the evidence collector bound to the client name | remap `/servo_node/pose_target_cmds → /m39/app_cmd`; the same collector |
| What it cannot do here | — | fresh-press re-arm (P_rearm) |

The ordering and acknowledgment chain (§3.2 of R03) is the same code in both arms. **This pilot
does not measure whether it would be cheaper to reuse across apps**, because there is no second app.

## 6. What remains unknown (environment and scope)

- **Real transitions are not covered.** We ran only synthetic transitions: runtime IO deactivation
  and operator release, on the `remote` driver and Gazebo. Not covered:
  - focus loss to another client;
  - INPUTS_BLOCKED from an overlay;
  - real tracking loss;
  - headset menus.
- **The probe's detection gap was not run in trials.** The probe showed that pose-invalid misses
  sub-tick (30 ms) deactivations, and that a release/press during a deactivation is invisible to the
  app. B1's latched evidence covers the first case. The formal trials did not exercise either.
- **One start configuration.**
  - The forearm–wrist_2 proximity (status 4) is present in all IK branches of the app's engage pose.
  - Its effect was measured as small, but it is not absent.
  - Other speeds, poses and arm models are untested.
- **What 3 repetitions cannot show:**
  - the absence of rare failures, such as a race between unpause and a leaked command under heavier
    load;
  - universal safety;
  - timing distributions.
- **Not covered at all:** a second real app path, a compromised app, or a physical robot.

## 7. Questions this leaves

- Is there a real app path where buttons travel on the wire (Quest2ROS2, PickNik, Docker_Teleop
  publish them)? On such a path a ROS-side component could also enforce a fresh press. Would the same
  component then meet the full contract without app changes?
- Does a second, structurally different app need a different command-semantics adapter? Twist apps
  need none for re-basing, but need a hold. What does that cost compared with a per-app B1?
- Do real headset transitions (focus loss, menus, tracking loss) reach the app as pose-invalid
  within one tick, as the IO toggle does here?
