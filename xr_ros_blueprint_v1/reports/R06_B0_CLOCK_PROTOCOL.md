# R06 — B0_clock: separating the clock-setting confound from the M39 B0 stop result (protocol)

**Status.**

- Written and frozen on 2026-10-03, before any B0_clock formal trial. The freeze commit is the
  commit that adds this file together with `experiments/M39_clock/FREEZE_SHA256.txt`.
- One plumbing smoke ran before freeze (N0, excluded; §6).
- No R03/R04/R05 file is changed.

## 1. Question

In M39, unmodified B0 left a 10.2–13.5 mm EE catch-up residual when a runtime deactivation hit
mid-motion (I3). On that deployment, Servo's `incoming_command_timeout` (0.5 s) cannot trip:

- Servo runs on sim time (`use_sim_time: True`).
- The app stamps its commands with wall time (≈ 1.79·10¹² ms ahead).

This raises a question about where the residual comes from. Is it a property of that clock setting,
or does it remain when the clocks agree?

## 2. The only change (arm B0_CLOCK)

| Item | B0 (M39) | B0_CLOCK |
|---|---|---|
| App | installed `quest_teleop` entry point @170dad5 | same binary, **0 code lines changed** |
| App launch | no ROS parameter (wall clock) | `--ros-args -p use_sim_time:=true` (`experiments/M39_clock/harness/trial_clock.sh`, 1 line) |
| Everything else | — | identical: image, workspace, Servo config (timeout 0.5 s, collision checking, singularity thresholds), JTC, start configuration, scenarios (`M39_pilot/scenarios/axis_mx`), observer, collector, sched |

**Upstream basis.** The app repository's own `ur5_moveit/launch/simulated_robot.launch.py` defines
the app node with `parameters=[{'use_sim_time': True}]`. That node is commented out of its
LaunchDescription. M39 (like P1/F3) started the entry point directly without the parameter.

**Not added:** hold, re-arm, re-anchor, or any new timeout policy. The existing safety functions
(Servo collision/singularity checks, JTC) are unchanged.

## 3. Clock-match check (per trial; failure = instrumentation-invalid)

For every Servo-input command after 1.9 s, compute the offset: command `header.stamp` minus the sim
time at reception. Sim time comes from the observer's `/clock` samples, linearly interpolated.

**Requirement:** median |offset| ≤ 50 ms and max |offset| ≤ 200 ms.

Smoke result (excluded): median −39.9 ms, max 46.7 ms, n = 269.

## 4. Conditions and schedule (`experiments/M39_clock/schedule_clock.csv`)

- I3 × 3 and N0 × 3, interleaved: N0, I3, I3, N0, N0, I3.
- The scripts are M39's `axis_mx` I3/N0, unchanged.
- One fresh container per trial; sequential; no other experiment of ours running.

## 5. Measures

The inherited measures use the frozen M39 `analysis/analyze_m39.py` with B0 semantics, called from
`experiments/M39_clock/analysis/analyze_clock.py`. The new measures are in `analyze_clock.py`.

| Measure | Definition |
|---|---|
| **P_stop** (I3; inherited R03 final) | S1: EE travel after onset + 0.1 s ≤ 5 mm over [t_on + 0.1, t_end]; S2: max arm joint speed ≤ 0.01 rad/s over [t_on + 0.3, t_end] |
| **Normal** (N0; inherited R03 final) | no false stop; settled at 5.7 s vs Servo target; mapping increments vs the frozen app-command reference. R05: this reference checks consistency with the app's own mapping only. |
| Timeout fired (I3) | After the last Servo input before t_end, Servo trajectory output stops at least 0.2 s before t_end |
| Timeout timing | (a) the sim interval from the last command's stamp to the last Servo trajectory; (b) the same interval in wall time |
| Servo output | number of Servo trajectories in [t_on, t_end] and in the last 0.5 s of the window |
| JTC target | EE of the last Servo trajectory's first point (FK, `M39_pilot/harness/ur5_kin.py`) vs the EE at onset; EE at t_end vs that target |
| EE residual | travel after onset and after onset + 0.1 s (from P_stop) |
| Descriptive | P_resume/P_rearm events at reactivation (B0 semantics), Servo statuses, status-4 counts, app rate, real-time factor, load |

## 6. Validity (inherited R03 §7 and one addition)

- **Instrumentation-invalid:** R03 (i)–(vi), plus (vii) the clock-match check fails.
  - An invalid trial is rerun in the same slot, at most 2 times. All attempts are kept.
- **Masked (kept and reported):** statuses {1, 2, 3, 5, 6} in [t_on − 0.5, END] (or from 2.0 for
  N0). Status 4 is recorded per window, as in R05; its magnitude is not observable.
- **Not executable:** if (vii) fails in all 3 attempts of a slot, the parameter alone does not align
  the clocks on this stack. B0_clock is then **BLOCKED** (separate experiment needed). The scope is
  not widened.
- **No extension repetitions.**
- **The smoke `raw/smoke/smoke_B0_CLOCK_N0`** is excluded. It showed the clock match. It would have
  been instrumentation-invalid by (iii) (one `/joint_states` gap).

## 7. Reading rules (fixed before running)

| Outcome in valid I3 trials | Reading |
|---|---|
| Timeout fires and P_stop passes | The M39 B0 I3 residual depended on the deployment's clock setting. With matched clocks, the existing Servo timeout limits it on this path. |
| Timeout fires but P_stop fails | The residual **remains under matched clocks**. Servo's timeout and smoothHalt stop Servo output, but the JTC still executes the points already sent (catch-up). This is the M3 controller-level issue, independent of the clock setting. |
| Timeout does not fire although clocks match | Unexplained; recorded with traces; no fix attempted in this protocol |

- **N0** checks that the clock change does not break normal operation.
- **Separate reporting.** Results are reported apart from M39 B0/B1/C1 and do not overwrite any R04
  number. The original-deployment problem and any problem remaining under matched clocks are stated
  separately.

## 8. Limits

- Same single path, start configuration and synthetic transition as M39.
- 3 + 3 trials are exploratory.
- Status-4 deceleration is present and unquantified (R05 §B).
