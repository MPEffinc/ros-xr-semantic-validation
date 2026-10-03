# R09 — M39 collision-slowdown measurement (protocol, frozen before formal runs, 2026-10-03)

**Purpose.** Quantify MoveIt Servo's collision velocity scale and self-collision distance on the frozen M39 path,
per arm and per judged window, with a logging-only Servo build. This is a **measurement replication** of M39
conditions. It does not re-judge R04 and does not estimate the causal effect of the slowdown.

## 1. Where the scale is computed and applied (MoveIt Servo 2.12.4, pinned source)

- `collision_monitor.cpp` `checkCollisions()` runs in its own thread at `collision_check_rate` (10 Hz).
  - It computes the self-collision distance d (unpadded scene; ACM applied).
  - The scale is `exp(log(1000)/0.01 · (d − 0.01))` for d < 10 mm and 0 on contact.
  - It writes `collision_velocity_scale_`.
- `servo.cpp` `getNextJointState()` (L494–528) uses the scale:
  - the status is 4 if 0 < scale < 1, and 5 if scale == 0;
  - the joint position step is multiplied by the scale (L526–528); `smoothHalt` velocities likewise
    (L676).
- **Pause behaviour.** `pause_servo(true)` calls `setCollisionChecking(false)`, which stops the
  monitor thread. The last scale value is kept, unchanged, until the monitor is restarted on unpause
  (`servo_node.cpp` L159–178, `servo.cpp` L180–183). Status is not published while paused.

## 2. Method chosen (priority 2 of the round)

| Priority | Method | Decision |
|---|---|---|
| 1 | Direct scale record from existing output | not available: Servo publishes only the status code (no magnitude) |
| 2 | **Separate build with minimal logging** | **chosen** |
| 3 | Distance recomputation from recorded joints | not needed |

**The chosen build.**

- `experiments/M39_decel/instr/moveit_servo_2.12.4_m39_logging.patch` (99 lines), applied to the
  pinned 2.12.4 source.
- It adds three log calls and one header, writing to a file named by `M39_SERVO_LOG`:
  - each monitor cycle: scale, self distance, scene distance, collision flags;
  - each control cycle that processes a command: the scale used and the status;
  - monitor start/stop.
- It is built with colcon in Release mode and used as an overlay. **No parameter or logic is
  changed; collision and singularity protection stay on.**

**Instrumentation-effect check** (probes P02–P07, B0 N0, 3 stock + 3 instrumented, interleaved;
`experiments/M39_decel/results/probe_instr_vs_stock.json`):

| Measure | Stock | Instrumented |
|---|---|---|
| Servo output period, median / p95 / max (ms) | 20.0 / 21.6–21.8 / 23.9–25.8 | 20.0 / 21.5–21.9 / 24.3–30.6 |
| Tracking lag, segment A (mm) | 6.44–6.56 | 6.49–6.72 |

In both variants: app rate 20.0 Hz, collector max gap 10.4–11.6 ms, Normal 3/3, increment error
≤ 0.88 mm. **No behaviour change was detected at this resolution.** The 30.6 ms maximum period
occurred once.

## 3. Formal measurement

- **Arms and conditions.** The frozen M39 arms B0/B1/C1 (`M39_pilot/arms`, harness unchanged
  except the Servo overlay), with conditions N0, N1, I1, I2, I3 (`axis_mx`). The start
  configuration is unchanged from M39.
- **Repetitions.** 2 per cell = **30 formal trials** (`experiments/M39_decel/schedule_decel.csv`),
  ordered by block shuffle (`Random(90 + rep)`) and Latin arm rotation.
- **Validity.** R03 §7: instrumentation-invalid trials are rerun, at most 2 times, and all attempts
  are kept. A missing or empty `servo_scale.jsonl` is also instrumentation-invalid.
- **Quantities** (`analysis/analyze_decel.py`):
  - per judged window (pre-event [5.5, 6.0]; stop [t_on+0.1, t_end]; each resume [t_r, t_r+0.3];
    increments [9.4, 14.9]; L3 [9.5, 11.0]; all):
    - monitor scale (min/mean) and self distance (min/mean);
    - applied scale (min/mean, fraction < 1, fraction < 0.9);
    - target–EE distance (mean/max);
    - EE speed max;
  - the monitor running/stopped spans;
  - the latency chain: onset → collector saw → arm decision → pause call/ack → first hold → last
    Servo trajectory in the window → standstill.
- **R03 measures** are recomputed for these replications and reported **separately from R04**. They
  do not overwrite it.

## 4. Interpretation limits (fixed)

- **Where the scale is unknown.** While the monitor is stopped (pause), the recorded scale is the
  last pre-pause value; it is not a measurement during the pause. Absence of applied cycles (no
  command processed) means no scaling was applied in that window, not that the scale was 1.
- **No causal claim.** Scale values per window do not establish the causal effect on EE travel or
  latency. Any cross-arm comparison of travel stays descriptive.
- **Scope.** Same single path, start configuration and synthetic transitions as M39.
