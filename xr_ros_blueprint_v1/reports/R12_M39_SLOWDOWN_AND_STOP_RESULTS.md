# R12 — M39 collision-slowdown measurement (R09) and existing stop methods (R10): results (2026-10-03)

## Part A — collision scale and self distance (R09; frozen e3091fd; 30/30 valid, 0 reruns)

| | |
|---|---|
| Raw data | `experiments/M39_decel/raw/` (ignored): 137 MB, 822 files including probes; sha256 in `experiments/M39_decel/results/DECEL_RAW_SHA256.txt` |
| Per-trial measures | `experiments/M39_decel/results/decel_trials.json` |
| Method | A logging-only MoveIt Servo 2.12.4 build. This is a **direct record of the internal scale** computed (10 Hz) and applied (per control cycle). It is not a recomputation. |
| Instrumentation check | 3 + 3 normal probes, stock vs instrumented: no difference in output period, app rate, tracking lag or Normal (R09 §2) |

### A1. Scale and distance

The scale computed by the collision monitor is `exp(690.8·(d − 0.01))` for d < 10 mm.

| | All trials | Start configuration (pre-event [5.5, 6.0]) |
|---|---|---|
| Applied scale | **0.8945–1.0** | mean 0.994 |
| Self-collision distance (forearm–wrist_2) | minimum **9.839 mm** | 9.99 mm |

**Per-window exposure, by arm (mean applied scale; fraction of applied cycles < 0.9):**

| Arm / condition | Stop window | Resume window(s) | Increments [9.4, 14.9] |
|---|---|---|---|
| B0 I1 / I2 | 0.995 (70 cycles) | 0.996 | I1: 1.0 / 0 %; I2: **0.925 / 20 %** |
| B0 N1 | 0.995 | 0.984–0.986 | **0.925 / 13–15 %** (back at the start configuration after the absolute re-anchor) |
| B0 I3 | 1.0 | 1.0 | 1.0 / 0 % |
| B1 (all) | no applied cycles (paused) | 0.992–0.993 | 0.999 / 0 % |
| C1 (all) | no applied cycles (paused) | 0.995–1.0 | 0.9996–1.0 / 0 % |

**Pause and the monitor.** During every B1/C1 hold the collision monitor was **stopped** (logged
`cm_stop` at the pause; the monitor-running spans in the JSON). No scale was computed during holds.
The value present at unpause was the pre-pause value until the next 100 ms monitor cycle.

**Reading.**

- The status-4 slowdown on this path is **small but not zero**: at most a 10.5 % reduction (1 − 0.8945) of the
  per-cycle step, and most of the time ≤ 1 %.
- Its exposure is **arm-dependent**: B0 after its absolute re-anchor spends 13–20 % of increment
  cycles below 0.9; B1 and C1 spend 0 %.
- **No causal claim is made.** This records the scale that was applied; it does not estimate how
  much EE travel or latency would differ without it.
- **The status code alone could not show this.** R05's "magnitude unobservable" is now resolved
  **for this path and these conditions** by direct logging.

### A2. Latency chain (ms after onset = IO-off return; I1/I2/I3)

| Arm | Collector saw | Arm decision | Pause call | First hold | Pause ack | Standstill |
|---|---|---|---|---|---|---|
| B0 | 0.0–4.9 | — | — | — | — | I3: 544–550 (Servo keeps tracking; output until ≈ 1.49 s) |
| B1 | 0.0–5.1 | 6.9–18.4 (app tick, pose-invalid) | 7.5–18.8 | 7.3–18.7 | 63.7–118.7 | 113–312 |
| C1 | 0.2–6.2 | 1.2–7.7 (evidence) | 1.6–8.2 | 1.5–8.1 | 57.9–80.6 | 4–99 |

- The Servo `pause_servo` acknowledgement takes 58–119 ms. The ordered core sends the first hold
  before the ack, then re-holds at the ack and at +0.1 s.
- In two B1 trials, one Servo trajectory issued before the pause took effect followed the first hold
  (`last_servo_traj` 7.7–11.3 ms).

### A3. R03 judgments of the replications (reported separately; R04 is unchanged)

| Cell (2 replications) | Result |
|---|---|
| B0 I1 / I2 / N1 | P_stop 2/2; P_resume 0/2 (jumps 47.9 / 47.9 + 87.9 / 40.0 mm) |
| B0 I3 | P_stop 0/2 (10.9, 13.4 mm) |
| B1 I1 / I2 / N1 / N0 | all pass as in R04 |
| B1 I3 | **P_stop 1/2.** D23: travel 1.82 mm (S1 pass), but max joint speed after onset + 0.3 s was **0.0104 rad/s** against the 0.01 limit (S2 fail). It was decaying through 0.0104 → 0.0094 at 6.302 → 6.312 s, after a detection at the app tick (+18.4 ms) and one Servo trajectory after the first hold. |
| C1 | partial contract 2/2 everywhere; P_rearm 0/2 in I1/I2/I3 (as in R04) |

- **B1 is borderline on S2.** R04's B1 I3 passed 3/3 (0.0036–0.0073 rad/s). The replication shows
  B1's stop sits near the S2 limit, because its detection is tied to the 20 Hz app tick. This is a
  **threshold-adjacent replication failure, not a new mechanism**. The criterion is not changed.

## Part B — JTC 4.42.1 stop functions: reachability (R10 §1) and standalone action verification

| | |
|---|---|
| Trials | 6/6 rc 0 (DECEL × 3, HOLD × 3). Raw in `experiments/M39_stop/raw/action`; measures in `results/action_trials.json`. |
| Stack | standalone Gazebo + JTC only; **not** an XR end-to-end result |

**Configuration and cancel handling.**

- With DECEL, `constraints.decelerate_on_cancel = True` and `max_deceleration_on_cancel = 3.0` read back
  from the running controller.
- Every cancel was accepted (return code 0, response ≤ 2 ms). JTC logged "Canceling active action
  goal because cancel callback received" in 6/6 trials.

**Stopping (EE 0.075 m/s; max joint speed at the cancel request 0.183–0.185 rad/s; JTC-formula
prediction 2.22–2.28 mm, t_stop ≈ 0.061 s):**

| Config | EE travel after the cancel request | Time to standstill (≤ 0.01 rad/s for 0.1 s) |
|---|---|---|
| decelerate_on_cancel (a = 3.0) | 2.28 / 3.73 / 4.47 mm | 0.226 / 0.234 / 0.257 s |
| default (hold on cancel) | 1.24 / 2.09 / 4.43 mm | 0.118 / 0.121 / 0.123 s |

**Reading.**

- **The native feature exists in the installed binary and runs on the action path.** With this
  deployment's acceleration limit, it did not stop the EE in less distance than the hold and it took
  about 0.1 s longer to standstill. The travel distributions overlap (3 vs 3).
- **On the topic path that MoveIt Servo uses, this feature cannot be reached** (code, R10 §1). The
  pre-flight probe PF3 showed that a topic trajectory sent 0.3 s after the cancel replaced the stop
  and moved the EE 30.0 mm.
- **Interface change needed to use it on the XR path:** Servo would have to command the arm through
  the FollowJointTrajectory action, or a stop node would need to own an action goal. Neither is the
  current Servo topic interface.

## Part C — stop methods on the XR path (R10; frozen f3b26bb; 36/36 valid, 0 reruns, 0 masked)

| | |
|---|---|
| Raw data | `experiments/M39_stop/raw/formal` (ignored): 141 MB total, 952 files including action and pre-flight; sha256 in `results/STOP_RAW_SHA256.txt` |
| Measures | `results/stop_trials.json` |

### C1. Runtime deactivation mid-motion (3 trials each; values as min–max)

| Measure | I3: B0_CLOCK | I3: HOLD | I3: DECEL_TOPIC | I3h: B0_CLOCK | I3h: HOLD | I3h: DECEL_TOPIC |
|---|---|---|---|---|---|---|
| **R03 P_stop** | **0/3** | 3/3 | 3/3 | **0/3** | 3/3 | 3/3 |
| EE travel after onset + 0.1 s (mm) | 10.22–12.05 | 0.04–0.13 | 0.00–0.05 | 4.96–5.75 | 0.00–0.36 | 0.01–0.07 |
| EE travel after onset (mm) | 14.75–15.37 | 1.01–1.35 | 1.09–1.91 | 6.70–7.75 | 0.62–1.69 | 0.84–1.62 |
| Max joint speed after onset + 0.3 s (rad/s) | 0.053–0.064 | ≤ 0.0001 | ≤ 0.0001 | 0.026–0.030 | ≤ 0.0003 | ≤ 0.0001 |
| Time from onset to standstill (s) | 0.538–0.571 | 0.050–0.099 | **0.019–0.031** | 0.456–0.469 | 0.017–0.113 | 0.031–0.051 |
| Servo trajectories after the first stop message | — | 0, 0, 1 | 0 | — | 0 | 0 |
| P_decel (own policy) | — | — | 3/3 | — | — | 3/3 |

- **P_decel prediction.** The predicted decel distance was 0.45–0.48 mm at the I3 speed and
  0.10–0.28 mm at I3h, with predicted t_stop of 13–29 ms.
- **Why B0_CLOCK fails at half speed.** S1 travel sat at or just above 5 mm (4.96, 5.17, 5.75), and
  S2 failed in all three (Servo keeps tracking until its 0.5 s timeout).
- **Excluded metric.** The "max EE speed" values for B0_CLOCK (190–450 mm/s) come from irregular tf
  sample timing, not physical speed. They are not used.

### C2. Normal controls (QF, QFh; 18 trials)

- Stop arms triggered in 0/12 trials (no false stop).
- In all 18 trials: settled error ≤ 0.10 mm and app 20 Hz; mapping increments pass (R05: with the
  app-command reference).
- The fast-segment tracking lag was the same in every arm (QF 14.6–15.6 mm; QFh 10.7–11.3 mm).

### C3. Reading (per the R10 reading rules)

- **Resolved by an existing method on this path.** At both speeds, a controller-level stop at the
  measured state (HOLD), or a constant-deceleration stop built from the measured state with the
  deployment's 3.0 rad/s² limit (DECEL_TOPIC), meets R03 P_stop in 12/12 trials.
  - DECEL_TOPIC reached standstill fastest (19–51 ms). At this speed and acceleration limit the
    deceleration takes about 20–30 ms, so it behaves almost like a hold.
  - This is the same resolution P1b/M39 found, now at a second speed and with matched clocks.
- **Prerequisites:**
  - **runtime interruption evidence:** the same collector; detection 1–10 ms after the IO toggle;
  - **Servo must be paused before or together with the controller command.** Otherwise new topic
    trajectories override the stop (PF3; one HOLD trial had one Servo trajectory after the first
    hold);
  - **measured joint velocity:** DECEL only;
  - **an acceleration limit:** DECEL only.
- **Not available on this interface.** JTC's internal `decelerate_on_cancel`. It is reachable only
  through an action goal (Part B).
- **Not removed by matched clocks or by halving the speed.** B0's catch-up residual: 10–12 mm at the
  M39 speed, 5–6 mm at half speed.
- **Remaining confounds:**
  - **Status-4 slowdown:** small (applied scale ≥ 0.8945; Part A). Its effect is not causally
    separated.
  - **Scope:** a single path, start configuration and acceleration value. Only two speeds.
  - **Not tested:** other acceleration limits; a real robot's dynamics.
