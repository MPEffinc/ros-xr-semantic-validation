# R25 — Late pre-stop trajectory with a distant target (protocol; frozen before formal runs)

**Purpose.** In R22 the injected late trajectory displaced the hold under CUR, but its target lay at the stop pose, so
the observed motion was 0 mm. R25 asks whether a late trajectory with a **distant** target moves the arm under CUR, and
whether MUX blocks it.

This is an **isolated fault injection** in Gazebo, not an external attack result. R22 is preserved unchanged.

## 1. Pre-flight finding: the stamped message is rejected (JTC 4.42.1)

PF1 (CUR) and PF2 (MUX) used snapshot e1f7201: the last Servo trajectory with capture time < 5.0 s, re-published
**unchanged** at onset + 150 ms. In both, the original header stamp ended **1.4 s in the past**.

- Under CUR the message reached the controller topic, but JTC rejected it: `Received trajectory with non-zero start time
  (24.287) that ends in the past (24.466)` (gazebo.log).
- EE travel after the injection was 0.0 mm (CUR) and 0.61 mm (MUX).

**An existing controller check therefore blocks a stamped trajectory delivered after its own horizon** (here the last
`time_from_start` was 0.18–0.19 s). A stamped late message can displace a hold only if it arrives within that horizon,
as in R22 (150 ms). The rejection evidence is pre-flight only (n = 1 per arm) plus the JTC log text.

## 2. Formal condition (frozen)

`M3_far/harness/far_injector.py`:

| Parameter | Value |
|---|---|
| Captured trajectory | the last multi-point Servo trajectory on the Servo output path with receive time **< 4.0 s after T0**: a pose inside the qualified I3 motion (start configuration and scenario as R10/R18), not an arbitrary joint target |
| Re-publication | once at **onset + 0.150 s** (onset 6.0 s), on the path Servo uses (CUR: the controller topic; MUX: `/m3/servo_out`) |
| Content | points and `time_from_start` unchanged; **`header.stamp = 0`** (start now). This models a writer with start-immediately semantics delivering a pre-stop message late. |
| Target difference (pre-flight) | EE distance between the pose at capture and the pose at injection: 27.7 mm (PF3) and 29.6 mm (PF4); max joint difference 0.057–0.060 rad |
| Age of the content at injection | ≈ 1.6 s (sim) |

All other settings follow R18: the arms, the scenario, the I3 runtime deactivation at 6.0 s and the existing safety
settings. `trial_far.sh` substitutes only the injector path in a /tmp copy of the frozen `trial_ord.sh`.

**Arms:** CUR (pause + direct repeated hold) and MUX (`topic_tools mux` as exclusive writer). **2 × 3 = 6 formal
trials** (`schedule_far.csv`).

## 3. Measures (`analysis/analyze_far.py` = frozen `analyze_ord.trial` + the following)

The three outcomes are reported separately:

- **controller reach:** the injected message on the controller topic;
- **hold displacement:** the injected trajectory is the last one the controller received, and there is no JTC
  rejection line in the logs;
- **actual motion:** EE travel after the injection, and P_stop (R03).

Also recorded:

- the target difference (EE and joint);
- the original stamp's end relative to now;
- JTC rejection lines.

Validity: R03 rules. Reruns: invalid instrumentation only, at most 2.

## 4. Pre-flight with the frozen condition (excluded; snapshot 33fa310; 07:38–07:40)

| Run | Reached controller | Last trajectory | JTC rejection | EE travel after injection | P_stop |
|---|---|---|---|---|---|
| PF3 CUR | yes | injected (13 points, +171 ms) | none | **22.6 mm** | fail (travel after onset+0.1 s 22.8 mm; joint speed 0.23 rad/s after onset+0.3 s) |
| PF4 MUX | no | 1-point hold (+109 ms) | — | 0.04 mm | pass |

No rule changed after the pre-flight.

## 5. Limits

- Gazebo only.
- One capture rule and one delay.
- The zero-stamp writer is a modelled semantics, not the observed Servo behaviour. Servo stamps its trajectories, and
  JTC rejects them once they end in the past.
- Direct controller-topic writers that bypass the mux are the permission premise tested separately (M19, R27).
