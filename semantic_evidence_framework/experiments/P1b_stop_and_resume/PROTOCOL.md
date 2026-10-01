# P1b — controller-level stop on release, and cached-deadman consequence with a moving hand

Pre-registered on 2026-10-01 after P1 (`../../results/P1_RESULTS.md`), before any P1b scheduled
trial. P1's frozen files are not modified. P1b uses copies with the changes listed here.

**Smoke trials, excluded from results:**

- `S0_SMOKE` (hand still, release at 6 s) with HOLD. It is not a schedule case.
- Smoke 1 exposed a gate logging crash (an `array.array` field passed to JSON), which happened after the first
  hold was published. It was fixed with `list(...)`, and smoke 2 passed with 2 holds logged.

## Changes from P1 (and why)

| Change | Reason |
|---|---|
| New defense **HOLD** (I_ALVR). Same disarm rule as PAUSE, plus a one-point `JointTrajectory` at the *measured* joint positions (`time_from_start` 20 ms, zero velocity) sent to `/ur5_arm_controller/joint_trajectory`, re-sent once 0.1 s later. | P1 C1: residual motion is downstream of Servo. This tests a controller-level stop. |
| New case **C2M** = P1 C2, but the hand keeps moving at +0.10 m/s until 11.0 s | In P1, a stationary hand after resume let Servo's singularity stop mask the consequence. |
| Position-only oracles | P1 showed the EE orientation still converging (rotation criterion confounded) |

## Cells and oracles

| Case | Cells | Oracle (unchanged thresholds) |
|---|---|---|
| C1 release (identical scenario to P1) | B0, PAUSE, HOLD | VIOLATION if max EE displacement over [6.6, 12.4] s > 5 mm. Also reported descriptively: EE x at 6.5/6.6/6.8/7.0/7.5 s. |
| C2M deact + cached grip, moving hand | B0, REARM_V, REARM_C | VIOLATION if max EE displacement over [8.0, 12.4] s > 5 mm |

C3 (the false-block control for REARM_V) is not repeated. P1 C3 stands.

**Schedule.** 6 cells × 3 repetitions = 18 trials, seed 20261002, rep-major and shuffled
(`schedule.csv`), about 13 min.

**Retry and expansion rules.** As in P1.

**Interpretation, fixed in advance.**

- If HOLD passes C1 while B0 and PAUSE do not, the release residual is closed by a controller-level
  stop. That is an existing mechanism (INTEGRATION placement).
- If B0 violates C2M and both REARM arms pass, the cached-deadman consequence is physically
  reproduced on the ROS side. The P1 C3 control then separates the evidence regimes.
