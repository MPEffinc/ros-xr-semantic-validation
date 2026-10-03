# R26 — Results: M7 admitted delay (R24, 18/18 valid) and distant late trajectory (R25, 6/6 valid), 2026-10-04

R21 and R22 are preserved unchanged. Both runs executed `git archive` snapshots of their freeze commits (a810226 and
cb0eca9) with per-trial hash checks.

**Raw data** (ignored; sha256 lists under `results/`):

| Experiment | Raw directory | Hash list |
|---|---|---|
| M7_admit | `experiments/M7_admit/raw` | `M7A_RAW_SHA256.txt` |
| M3_far | `experiments/M3_far/raw` | `FAR_RAW_SHA256.txt` |

## 1. M7 admitted delay (R24): configured command-level experiment

The premise held this time. Every delayed message was admitted at the unchanged τ = 100 ms.

| Arm | Delayed messages admitted | Age of delayed messages | H error of delayed messages (median / max, mm) | F error of delayed messages (median / max, mm) |
|---|---|---|---|---|
| L (latest tf) | **90/90** | 58–69 ms | **6.44–6.77 / 9.85–10.35** | 0.39–0.48 / 1.41–1.69 |
| S (`header.stamp`) | **90/90** | 60–69 ms | 0.003 / ≤ 0.008 | **6.79–7.46 / 10.09–10.81** |
| R (`represented_at`) | **90/90** | 57–69 ms | 0.002 / ≤ 0.008 | **6.66–7.30 / 9.99–10.65** |

**Whole runs.**

- The fresh messages are the same as in R21: L has an H error of about 3.1–3.3 mm, and S/R have F errors of about
  3.7–3.9 mm.
- The age of fresh messages was 24–41 ms, except in one DYN control trial.
  - In A01 (R, DYN, r1), one age spike (up to 243 ms) blocked **5 fresh messages** by age. This is a false block in a
    fault-free condition, counted as observed.
  - No tf_unavailable blocks occurred.

**Reading.**

- An admitted 30 ms delay **doubles the latest-tf error for the hold task**: the median rises from about 3.2 mm to
  6.4–6.8 mm, with a maximum of about 10 mm. The extra error is the frame motion over the added delay.
- Time-indexed tf (S or R) keeps the hold error at ≤ 0.01 mm under the delay. For follow semantics the ranking
  reverses, by the same amount.
- S and R coincide here because the bridge keeps the stamp. The difference between them appears only under
  restamping (R21).
- The age check admits these messages. It bounds the transport age only, not which time the transform should use, so
  **freshness admission and time-correct transformation are separate requirements**.
- An accurate transform of an old representation does not establish continued authorization.

**Limits.**

- Configured experiment: one translation-only frame at 0.157 m/s peak.
- Generation-time semantics; command level only.
- Not a frontend incident.

## 2. Distant late trajectory (R25): isolated fault injection in Gazebo

| Arm | Reached controller topic | Hold displaced (last trajectory = injected; no JTC rejection) | EE travel after injection | Target difference (EE / max joint) | P_stop |
|---|---|---|---|---|---|
| CUR | **3/3** | **3/3** | **22.5–23.2 mm** | 28.5–29.1 mm / 0.056–0.058 rad | **0/3** (22.5–23.3 mm after onset+0.1 s; 0.19–0.24 rad/s after onset+0.3 s) |
| MUX | 0/3 | 0/3 (last = 1-point hold at +102–108 ms) | 0.0–0.04 mm | 28.8–29.8 mm / 0.056–0.058 rad | 3/3 (≤ 0.25 mm) |

**Pre-flight findings (excluded, n = 1 per arm).** The same captured trajectory re-published with its **original
stamp** ended about 1.4 s in the past.

- JTC 4.42.1 rejected it: "non-zero start time … ends in the past".
- EE travel was 0.0 mm (CUR) and 0.61 mm (MUX).

**Reading.**

- **Three layers stand between a late pre-stop message and motion:**
  1. **JTC stale-end check (existing, built in).** A stamped trajectory delivered after its own horizon is rejected
     (≈ 0.18–0.19 s for Servo trajectories here). R22's 150 ms injection was inside the horizon and was accepted, but
     its target was at the stop pose (0 mm).
  2. **The content of the message.** A message accepted within the horizon displaces the hold, and the motion it
     causes depends on how far its target is.
  3. **Writer mediation.** If the message carries start-now semantics (stamp 0), or is accepted for any other
     reason, then under CUR it displaces the hold and **moves the arm toward a target ~29 mm away (22.5–23.2 mm,
     P_stop 0/3)**. With the exclusive writer (MUX) it never reaches the controller.
- The R22 "0 mm" was therefore a property of that message's content, not of the CUR design. The CUR design has no
  ordering guarantee. The existing JTC check covers only stamped messages delivered after their end time.
- **Not covered:**
  - writers that publish on the controller topic directly (the permission premise; R27/R29);
  - the action interface;
  - mux re-arm.

**Limits.**

- Gazebo; one capture rule (< 4.0 s) and one delay (onset + 150 ms).
- The zero-stamp writer is a modelled semantics: Servo itself stamps its trajectories.
- Isolated fault injection, not an attack result.
