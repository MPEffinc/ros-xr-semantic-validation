# R07 — B0_clock results (6 trials, 2026-10-03)

| | |
|---|---|
| Protocol | `R06_B0_CLOCK_PROTOCOL.md`, frozen at `e98e513` |
| Raw data | `experiments/M39_clock/raw/formal/` and `raw/smoke/` (ignored); per-file sha256 in `experiments/M39_clock/results/CLOCK_RAW_SHA256.txt` (136 files) |
| Measures | `experiments/M39_clock/results/b0_clock_and_m39_b0.json` (sha256 `ffba731c…`). The same `analyze_clock.py` was applied to the 6 B0_CLOCK trials and, for comparison only, to the existing M39 B0 I3/N0 trials (T08, T19, T42, T12, T23, T43). Those M39 values are unchanged from R04. |
| Attempts | 6/6 valid on the first attempt; masked 0; statuses {0, 4} only |
| Load | 1-min host load before each trial: 3.6–13.2 |
| Plant | real-time factor 0.70–0.72; app rate 20.0 Hz |

## Clock match (the only change: the app runs with `use_sim_time:=true`)

| | Command stamp − Servo sim time at reception |
|---|---|
| B0_CLOCK (6 trials) | median −35.6 to −36.0 ms, max \|·\| 40.7–44.3 ms → **matched** (criterion ≤ 50 / 200 ms) |
| M39 B0 (6 trials) | ≈ +1.79·10¹² ms (wall stamp vs sim clock) |

## I3 (runtime deactivation mid-motion): stop

| Measure | M39 B0 (T08, T19, T42) | B0_CLOCK (K02, K03, K06) |
|---|---|---|
| Servo pose timeout fired | **no**: Servo trajectories continue to t_end (75 in the window, 25 in its last 0.5 s) | **yes**, 3/3: Servo output stops 0.493–0.499 s (sim) after the last command's stamp, which is 0.645–0.659 s wall (31 trajectories in the window, 0 in its last 0.5 s) |
| EE of the last JTC target vs EE at onset | 14.7–15.6 mm | 14.0–15.5 mm |
| EE at t_end vs that last JTC target | 0.0 mm | 0.0 mm |
| EE travel after onset (total) | 14.7–15.6 mm | 14.0–15.5 mm |
| EE travel after onset + 0.1 s (P_stop S1, limit 5 mm) | 10.2–13.5 mm | 10.1–12.6 mm |
| Max joint speed after onset + 0.3 s (S2, limit 0.01 rad/s) | 0.051–0.064 rad/s | 0.050–0.057 rad/s |
| **P_stop** | **0/3** | **0/3** |

## N0 (normal operation)

Normal passes 3/3 for B0_CLOCK, with no masking. With matched clocks, the timeout never tripped
during continuous 20 Hz input.

## Descriptive: I3 reactivation (not part of the R06 question)

B0_CLOCK still resumes without a fresh press (160 admissions) and with a target jump. Target vs EE:
32.3–32.9 mm; M39 B0 I3: 31.9–32.6 mm. The clock change does not touch resume semantics.

## Reading (R06 §7, row 2: "timeout fires but P_stop fails")

- **With matched clocks** the existing Servo timeout works as designed: output stops about 0.5 s
  (sim) after the last command.
- **It does not reduce the residual on this path.** At the onset, the last commanded target is
  already 14–15.5 mm ahead of the EE (Servo tracking lag at 0.075 m/s). Servo keeps tracking that
  target until the timeout, and the JTC executes the points already sent. The EE ends exactly at the
  last JTC target.
- **So the M39 B0 I3 residual is not explained by the deployment's clock setting.** It remains under
  the clock setting the app repository itself specifies. This is the M3 catch-up problem at the
  controller level, which the controller hold in B1/C1 removed (R04: 1.6–2.8 mm and 0.0–0.1 mm).

**What does depend on the clock setting.** Whether Servo ever stops tracking the last target on its
own. Under the M39 deployment it never does. Here it would matter for a longer interruption, for
example a target that keeps drifting, or the stale-target-after-unpause issue handled by B1/C1. It
did not matter for this 10–15 mm residual.

## Separation of problems

| Problem | Original M39 deployment (wall stamps) | Matched clocks (B0_CLOCK) |
|---|---|---|
| Servo never times out; it tracks the last target indefinitely | present | **absent** (timeout fires 3/3) |
| Catch-up residual after a mid-motion interruption (I3) | 10.2–13.5 mm | **remains**: 10.1–12.6 mm |
| Resume without a fresh press, with a target jump | present | remains (descriptive) |

## Limits

- 3 + 3 trials.
- One path, one start configuration, one speed (0.075 m/s EE target speed).
- Status-4 deceleration is present and unquantified (R05 §B).
- The residual value depends on Servo's tracking lag at this speed. Whether a faster Servo gain or a
  different `incoming_command_timeout` would reduce it was **not** tested: that would add a new
  timeout policy, which R06 excludes.
