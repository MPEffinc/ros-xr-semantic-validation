# R21 — M7 dynamic frame and transform time: results (R17; 36/36 valid, 2026-10-04)

| | |
|---|---|
| Protocol | R17, frozen 0e73ba2; executed from a `git archive` snapshot, hash-verified per trial |
| Raw data | `experiments/M7_frame/raw/` (ignored); sha256 in `results/M7_RAW_SHA256.txt`; measures in `results/m7_trials.json` |
| Level | **command level** (the converted target before Servo); a **new experimental configuration** (scripted moving frame + representation adapter), not a naturally occurring app problem, not a second app path |
| Validity | 36/36 valid on the first attempt; adapter representation error ≤ 0.010 mm in every trial (the tf lookup at t_g matched the script) |

## Errors (mm; per trial median / max over admitted messages; ranges over 3 trials)

| Condition | Arm | H (hold the world target at its representation time) | F (follow the frame now) | Blocked |
|---|---|---|---|---|
| STATIC | L / S / R | 0 / 0 | 0 / 0 | 0 |
| DYN | **L** (latest tf) | **3.07–3.16 / 5.3–5.8** | 0.37–0.40 / 1.4–1.7 | 0 |
| DYN | S (header.stamp) | 0.002–0.003 / ≤ 0.008 | 3.6–3.8 / 5.9–6.2 | 0 |
| DYN | R (represented_at) | 0.002–0.003 / ≤ 0.009 | 3.7–3.8 / 6.0–6.2 | 0 |
| DYN_DELAY | L / S / R | same pattern as DYN on the admitted messages | — | **30/30 delayed messages blocked by age in every arm** |
| DYN_RESTAMP | **L** | 3.3–3.4 / **70.8–81.3** (window median 12.8–14.6) | 0.35–0.41 / 1.6–1.9 | 0 |
| DYN_RESTAMP | **S** | 0.003 / **66.4–80.8** (window median 12.7–16.2) | 3.37–3.38 / 6.1–6.4 | 0 |
| DYN_RESTAMP | **R** | **0.003 / ≤ 0.009** (window ≤ 0.004) | 3.9–4.0 / **70.6–78.0** | 0 |

**Further observations:**

- **The DYN_DELAY premise did not hold.** The design intended a delay "within the 100 ms age". The app stamp already
  arrives about 35 ms old (sim-clock propagation, R13), so the 80 ms bridge delay put every delayed message over 100
  ms and the **age check blocked all of them (90/90 per arm)**. The condition therefore measures age blocking, not the
  tf-time effect. The criteria were not changed; this is reported as a design-premise failure.
- **DYN_RESTAMP:** 26–27 restamped messages per trial had `represented_at` older than 100 ms. A representation-time
  age check would block them. The transport-stamp age check admitted them all.
- **S in the restamp window behaves like F.** S tracked the frame now (F window error median 0.003–0.004 mm,
  max ≤ 0.31 mm), because the fresh stamp equals the conversion time. For H it is wrong by the frame motion since
  the cached representation time.
- **S on restamped messages** waited ≈ 20 ms (p95) for tf at the fresh stamp, because the latest tf was not yet
  available. The other cases waited ≤ 0.2 ms.

## Reading by task semantics

- **H (a command meant as a world target fixed when it was expressed).**
  - **Transforming at the representation time is correct**, using standard time-indexed tf2 lookup. It holds through
    delay and through cache/restamp, **provided the representation time travels in its own field** (R).
  - Using the transport `header.stamp` (S) is equivalent until a republisher re-stamps it. It then fails as badly as
    using the latest tf (up to 81 mm here).
  - **Latest tf (L)** carries a systematic error equal to the frame motion over the pipeline latency (about 3 mm at
    0.157 m/s here).
- **F (a command meant relative to the moving frame now).** **Latest tf is the intended behaviour** and is the most
  accurate (≤ 1.9 mm). R and S are "wrong" for F by the same frame motion, and badly so for re-stamped cache content
  (R: up to 78 mm).
- **Classification.**
  - M7 is **solved by the existing stamped/time-indexed tf2 method** when two conditions hold: the task semantics are
    declared H, and the representation time is preserved separately from the transport stamp.
  - The remaining risks are **semantic declaration** (which time means what) and **stamp preservation through
    republishers** (restamping breaks S). They are not a missing method.
  - The time here is the **generation time**. No source sample time is available on this path (R13/R19).
- **Limits:**
  - one translation-only frame motion (A = 0.05 m, 0.5 Hz);
  - a scripted tf on one host clock;
  - command level only;
  - no oracle time was given to any arm. The script was used only for scoring.
