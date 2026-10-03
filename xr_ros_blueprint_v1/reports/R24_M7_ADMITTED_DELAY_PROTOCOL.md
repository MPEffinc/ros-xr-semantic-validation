# R24 — M7 admitted delay (protocol; frozen before formal runs)

**Purpose.** R17/R21 intended "delay within the age budget" but the condition failed. The baseline converter age
(R17 DYN: 25–41 ms, p99 39 ms) plus the 80 ms delay gave 107–124 ms, so every delayed message was blocked by age.

R24 keeps the age rule unchanged (τ = 100 ms on `now − header.stamp`, sim). It reduces the delay so that delayed
messages are admitted, and measures the transform-time effect on them. R21 and the R17 files are preserved unchanged.

## 1. Configuration

The R17 chain is reused unchanged: the app, the representation adapter, the converter arms L/S/R, the scripted
frame and the ground truth. All are executed from the frozen M7_frame files in the same snapshot.

The only difference is the bridge (`M7_admit/harness/m7_bridge_admit.py`):

- **DELAY is D = 30 ms** (sim);
- the window is unchanged (6.0–7.5 s after T0);
- `header.stamp` and `represented_at` are kept.

`harness/trial_m7a.sh` substitutes the bridge path in a /tmp copy of the frozen `trial_m7.sh`.

**Delay value, frozen before the formal runs.**

- Expected age = baseline 25–41 ms + 30 ms = 55–71 ms, which leaves ≥ 29 ms margin to τ.
- Pre-flight (below) measured 59–73 ms.
- τ and D are not changed after the formal runs.

## 2. Conditions and schedule

| ID | Bridge |
|---|---|
| DYN | PASS (control, same session type) |
| DYN_ADELAY | DELAY 30 ms in the window |

3 arms (L latest tf, S `header.stamp` tf, R `represented_at` tf) × 2 × 3 = **18 formal trials** (`schedule_m7a.csv`,
`Random(240 + rep)`).

## 3. Measures (`analysis/analyze_m7a.py` = frozen `analyze_m7.trial` + a split of the delayed messages)

- **Delayed messages (bridge label `delayed`):**
  - count; admitted / blocked by reason (age, tf_unavailable);
  - converter age (min / median / max);
  - H and F errors of the admitted delayed messages.
- **All admitted messages:** H/F errors over the run and the window; blocks by reason; the age of fresh messages.

**Meaning of the times:**

- `header.stamp` = transport stamp, which here equals the representation time, because the bridge does not restamp.
- `represented_at` = the app generation time (not a source sample time).

Arms S and R are therefore expected to coincide here. This condition separates **delay** from **restamping** (R21).

## 4. Validity and stopping rule

- Validity: R17 rules (frozen `analyze_m7` validity).
- **Premise check:** if fewer than all delayed messages are admitted in a trial, that trial still counts as valid and
  the blocks are reported. If the premise fails in the majority of trials, the admitted-delay result stays
  **unverified**. There are no further redesign runs in this round.
- Reruns: invalid instrumentation only, at most 2 per slot.

## 5. Pre-flight (excluded; snapshot 6e5000f; 07:07–07:09)

| Run | Delayed admitted | Delayed age | Fresh age | H error of delayed messages (median / max) | F error of delayed messages (median / max) |
|---|---|---|---|---|---|
| PF1 L | 30/30 | 59–73 ms | 24–43 ms | 6.99 / 9.70 mm | 0.33 / 1.38 mm |
| PF2 R | 30/30 | 59–69 ms | 25–38 ms | 0.002 / 0.006 mm | 6.88 / 10.18 mm |

No rule changed after the pre-flight.

## 6. Limits

- One translation-only motion.
- Generation-time semantics; command level only.
- A configured experiment, not a frontend incident.
- Accurate transform of an old representation does not establish freshness or continued authorization. The 100 ms
  transport-age rule is the only freshness rule here.
