# R10 — Existing controller-level stop methods on the M39 path (protocol; frozen before formal runs, 2026-10-03)

## 1. What JTC 4.42.1 offers (source at tag 4.42.1 / aacd842; installed `ros-jazzy-joint-trajectory-controller 4.42.1`)

**Hold and deceleration functions.**

- `set_hold_position()` (L1840) and `decelerate_to_hold_position()` (L1852) are **private** controller
  functions, not an external API.
  - `decelerate_to_hold_position` builds a constant-deceleration stop trajectory from the
    **measured** position and velocity: `t_stop = |v0|/a`, `p_hold = p0 + sign(v0)·v0²/(2a)`, with
    points every controller period.
- `decelerate_to_hold_position` is used only when `constraints.decelerate_on_cancel = true` (read-only
  parameter, set at load).
- It also requires:
  - every joint's `max_deceleration_on_cancel > 0`;
  - a URDF velocity limit;
  - a **velocity state interface** (L958–964).
- The installed binary contains the parameter and the fallback strings (`strings
  libjoint_trajectory_controller.so`).

**Paths that call either function:**

| Path | Function | Trigger |
|---|---|---|
| (a) action cancel | `goal_cancelled_callback` (L1441–1449) | the action goal is active and cancelled |
| (b) action goal | (L481–571) | path-tolerance violation or goal-time abort |
| (c) any trajectory | (L353–367) | `cmd_timeout > 0`, **after the last trajectory point** |
| (d) no-action branch | (L547–571) | tolerance violation |
| (e) activation/deactivation | (L1228) | — |

**The topic path Servo uses has no external stop trigger.**

- Servo publishes `JointTrajectory` on the topic; there is no action goal to cancel. On that path the
  only automatic route is (c), which acts only after the last point has passed. It does not shorten a
  catch-up toward points already sent.
- A new topic trajectory replaces whatever is executing, including a hold (`topic_callback` L1385–1398
  sets `rt_is_holding_ = false`), so Servo output arriving after a stop overrides it unless Servo is
  paused first.
- **A cancel response proves nothing on the topic path.** With no action goal, nothing is cancelled,
  so a "successful" cancel response says nothing about stopping.

**Deployment state.** In the M39 deployment, `ur5_arm_controller` has position command and
position + velocity state interfaces, no `constraints`, and `cmd_timeout` = 0 (default). So none of
(a)–(d) applies in the XR trials.

## 2. Arms of the XR stop pilot (same app, clock, evidence and input)

All arms run:

- the **unmodified** app with `use_sim_time:=true` (R06);
- the M39 start configuration and axis;
- the logging-only Servo (R09; no behaviour change measured);
- the same libmonado runtime evidence.

| Arm | Stop action on runtime deactivation |
|---|---|
| B0_CLOCK | none: Servo's own pose timeout (0.5 s sim) only |
| HOLD | M39 shared core: `pause_servo(true)` + JTC one-point hold at the measured joints (at once, on the pause ack, +0.1 s). This is the existing measured-state hold (P1b; same code as M39 B1/C1). |
| DECEL_TOPIC | same schedule, but each stop message is a constant-deceleration trajectory built **outside** JTC with the formula of `decelerate_to_hold_position` from measured positions **and velocities**, with a = 3.0 rad/s² (`ur5_moveit_config/joint_limits.yaml` max_acceleration). It is sent on the topic, so it reproduces the method externally and is **not** JTC's internal cancel path. |

- **Stop-only arms.** The stop arms never resume; there is no re-arm and no re-basing.
- **Native JTC deceleration.** It is reachable only via action cancel, so it is tested separately
  (§4) and not counted as an XR end-to-end result.

## 3. Conditions and schedule

**Conditions.** All use M39's `axis_mx` scripts; the fast segment always covers 7 cm of hand motion.

| ID | Fast segment | Onset | Note |
|---|---|---|---|
| I3 | hand 0.15 m/s (EE ≈ 0.075 m/s), 5.75–6.217 s | runtime IO off 6.0–7.5 s | M39 speed |
| I3h | half speed, 0.075 m/s, 5.75–6.683 s | 6.0 s | — |
| QF / QFh | the same scripts without deactivation | — | normal controls |

**Schedule.** 3 arms × 4 conditions × 3 = **36 formal trials** (`experiments/M39_stop/schedule_stop.csv`):

- block shuffle with `Random(100 + rep)`;
- Latin arm rotation;
- fresh container per trial.

**Pre-flight** (§6, normal only):

- QFh qualification with B0_CLOCK;
- one excluded DECEL_TOPIC plumbing smoke on I3h;
- one excluded action smoke.

**Not run:** extra speeds or poses (budget).

## 4. Standalone JTC action verification (1B-V; not an XR path)

- **Stack.** Gazebo + JTC only: no XR runtime, app or Servo (`jtc_action/trial_action.sh`). The
  controller is spawned with `--param-file config/jtc_decel_on_cancel.yaml` (DECEL) or without it
  (HOLD).
- **Motion.** One FollowJointTrajectory goal moves the EE along −x at 0.075 m/s for 10 cm (IK path,
  20 ms points). The goal is cancelled 0.6 s after acceptance.
- **Trials.** DECEL × 3 and HOLD × 3 = **6 formal trials**.
- **Override probe (not formal).** One extra probe publishes a topic trajectory 0.3 s after the
  cancel, to observe whether it replaces the stop.
- **Measures:**
  - parameter readback;
  - cancel response code and its timing;
  - EE travel and time to standstill after the cancel request and response;
  - the JTC formula's predicted stop distance from the joint velocity at the cancel request.

## 5. Measures and fixed criteria

**Stop measures (I3, I3h).** All are continuous values.

- EE travel after onset;
- EE travel after onset + 0.1 s;
- time from onset to standstill (all joints ≤ 0.01 rad/s for 0.1 s);
- max EE speed after onset + 0.1 s;
- max joint speed after onset + 0.3 s;
- number of Servo trajectories after the first stop message (stop overridden);
- the latency chain (R09);
- collision scale and self distance in the stop window (R09).

**Criteria.**

| Criterion | Applies to | Rule |
|---|---|---|
| **R03 P_stop** (inherited unchanged) | every arm | S1: travel after onset + 0.1 s ≤ 5 mm; S2: joint speed after onset + 0.3 s ≤ 0.01 rad/s |
| **P_decel** (separate policy) | DECEL_TOPIC, judged by its own declared behaviour | EE travel after the first decel command ≤ JTC-formula predicted EE stop distance + 2 mm, **and** standstill within predicted t_stop + 0.3 s |
| **Normal** (QF, QFh) | — | no stop-arm trigger (false stop); settled error at 5.7 s and mapping increments vs the frozen app-command reference (R05 notes this reference's scope); descriptive tracking lag in the fast segment |

**Validity.**

- R03 §7: instrumentation-invalid trials are rerun, at most 2 times, and all attempts are kept.
- Masked statuses {1, 2, 3, 5, 6} are kept and flagged.
- **No criterion changes after formal data.**

**Reading.**

- Which existing method meets R03 P_stop at each speed.
- Whether deceleration-based stopping is achievable on the topic path.
- Which prerequisites each method needs:
  - velocity state;
  - acceleration limit;
  - Servo pause before the controller command;
  - an action interface for the native feature.
- Which confounds remain (status-4 slowdown, from R09).

## 6. Pre-flight record (2026-10-03 15:17–15:20, before freeze; raw `experiments/M39_stop/raw/preflight`, excluded)

| Run | Result |
|---|---|
| PF1 B0_CLOCK QFh (half-speed normal qualification, R03 §10.3 rule) | **pass**: statuses {0, 4}, status-4 lag effect +0.37 mm, settled 0.074 mm, app 20 Hz, valid |
| PF2 DECEL_TOPIC I3h (plumbing smoke) | trigger at +10.3 ms; 3 decel messages; 0 Servo trajectories after the first; predicted stop 0.29 mm / 22.5 ms. The R03 P_stop and P_decel computations run (values are not used for any decision). |
| PF3 action DECEL with override (plumbing + override probe) | param readback `constraints.decelerate_on_cancel = True`, `max_deceleration_on_cancel = 3.0`; cancel accepted (return code 0, 1.5 ms); JTC log: "Canceling active action goal because cancel callback received." A topic trajectory published 0.3 s after the cancel moved the EE 30.0 mm, so **a new topic command overrides the stop**. Joint speed at the cancel request was 0.185 rad/s. |
