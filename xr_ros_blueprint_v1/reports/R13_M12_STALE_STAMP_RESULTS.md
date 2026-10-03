# R13 — M12 on the real UR5e app path: results (R11 72 trials + R11a follow-up 6 trials, 2026-10-03)

## Run summary

| | |
|---|---|
| Protocols | R11 (frozen 7388f4d), R11a (frozen d4b2fc0) |
| Raw data | `experiments/M12_stamp/raw/` (ignored): formal + pre-flight 1760 files, follow-up 138 files, 265 MB in total; sha256 in `experiments/M12_stamp/results/M12_RAW_SHA256.txt` and `M12_FOLLOWUP_RAW_SHA256.txt` |
| Measures | `experiments/M12_stamp/results/m12_trials.json`, `followup_trials.json` |
| Validity | 72/72 and 6/6 valid on the first attempt; no Servo masking statuses |
| Level | **command level**: the admission decision before Servo is judged. Real app (A2 is a 6-line app copy), synthetic source, real runtime IO transition, deployment-component fault injection in the bridge. No compromised-app (S2) claim. |
| Correction | The commit message of 6afeadc says "0/4851 false blocks" for A2. The correct count is **0/4508** fresh messages. |

## 1. Admission by ground-truth class (3 trials per cell, summed)

| Condition (truth class) | A0 original (Servo stamp timeout) | A1 stamp age ≤ 100 ms | A2 acquisition time + seq + validity | A3 runtime state |
|---|---|---|---|---|
| DELAY 250 ms (stale_delay) | admitted 90/90 (all Servo-effective) | **0/90** | **0/90** | 90/90 |
| CACHE republish, fresh stamp (stale_cache) | 84/84 | 84/84 | **0/84** | 84/84 |
| INACT_CACHE keepalive while runtime inactive (stale_keepalive) | 81/81 | 81/81 | **0/81** | **0/81** |
| SRC_STALL 1.5 s (stale_source) | 84/84 | 84/84 | **84/84** | **84/84** |
| R11a SRC_STALL_LONG 5 s (stale_source) | — | — | **294/294** | **294/294** |

**Fresh false blocks**, over all conditions (N_MOVE, N_STILL and the fresh messages outside the
injection windows):

| A0 | A1 | A2 | A3 |
|---|---|---|---|
| 0/4510 | 0/4508 | **0/4508** | 21/4508 |

**Where A3's 21 false blocks came from:**

- the **first command at engage** in every trial (t ≈ 2.01 s), 18 cases: a runtime "not ok" before
  the session was focused stays latched until the first command;
- the **first command after reactivation** in INACT_CACHE, 3 cases: the latch spans the deactivation.

Both follow from A3's fail-closed latch design and were reproducible. No false block occurred in
the N_MOVE/N_STILL windows.

**Block reasons.**

| Arm | Condition | Reasons |
|---|---|---|
| A2 | DELAY | acquisition age 90 |
| A2 | CACHE | acquisition age 79; sequence not increasing 5 (the first republishes within τ) |
| A2 | INACT_CACHE | acquisition age 80; sequence 1 |
| A1 | DELAY | stamp age 90 |
| A3 | INACT_CACHE | evidence 87 (81 stale + 6 fresh false blocks: 3 at engage, 3 after reactivation) |

**Normal ages.** Stamp age p50 was 33–35 ms (max 41 ms) in every arm. A2's acquisition age matched
it, because the stamp and the acquisition time are taken in the same app tick.

## 2. Answer to the question

**A fresh publish or receive stamp does not establish fresh input on this path.**

- A1, which checks stamp age with the same τ, admitted 100 % of cache republishes, keepalive reuse
  while the runtime was inactive, and source-stalled commands.
- It caught only the class that carries a genuinely old stamp: transport delay.
- A0, with matched clocks, admitted everything, because Servo's 0.5 s timeout is longer than the
  250 ms delay.

**The strongest existing fix on this path (A2) resolves every class it has information for.** A2 is
standard provenance practice: carry the acquisition time, read sequence and validity with the
command, check age, monotonic sequence and validity before the consumer.

- **Resolved:** delay, cache republish with fresh stamps, and value reuse while the runtime is
  inactive: 255/255 blocked, with 0 false blocks in normal operation, including a still hand
  (N_STILL).
- **Cost:**
  - 6 app lines;
  - a gate;
  - a message-schema change across the chain (here carried in `frame_id`), so every republisher must
    preserve the field;
  - the acquisition time comes from the **app**, so its trust is the app's (S2 out of scope).
- **Clock error:** about 33–41 ms of apparent age in normal operation (sim-clock propagation), well
  inside τ = 100 ms.

**The independent runtime check (A3) covers only runtime inactivity.** With no sample link it cannot
see delay or cache republishing, and it does not see source stalls. That is consistent with
F3/R04: runtime activity ≠ fresh app content.

## 3. The remaining condition: source stall (R11a cause check)

During a 5 s source stall (no feeder packet at all; truth hand moving):

- **App level:** OpenVR validity stayed 1 and the tracking result stayed 200 (Running_OK) for every
  command (3/3 A2 trials).
- **Runtime level:** client flags stayed FOCUSED, IO_ACTIVE, not INPUTS_BLOCKED (6/6).
- **Content:** identical in 97/98 consecutive pairs, the same as a legitimately still hand (N_STILL
  93/96).
- **Admission:** A2 and A3 admitted 294/294 stale commands.

**Cause (code + observation).**

- The Monado `remote` driver keeps `latest` with no receive time and reports it as tracked whenever
  `active` is set (`r_hub.c` L338–348, `r_device.c`).
- xrizer locates at the predicted display time. The OpenVR legacy API returns no sample time.

**No information on this path separates a stalled source from a still hand.** This is an
**information-availability limit of this deployment** (a synthetic driver without sample time and a
legacy API without sample time). It is **not** an implementation failure of A2. Whether a real
headset runtime exposes a usable sample time or tracking-loss signal in the equivalent situation is
UNKNOWN here (no headset).

## 4. Classification for the matrix

| Item | Classification |
|---|---|
| Delay with an old stamp | solved by a generic age check (A1) and by A2 |
| Cache republish / keepalive with fresh stamps | solved only with provenance carried from the acquisition point (A2). A generic stamp check (A1) cannot solve it on this path. |
| Value reuse while the runtime is inactive | solved by A2 or A3 |
| Source stall with a runtime that keeps reporting tracked | **not separable** with the information available on this path; would need a source sample time or sequence from the runtime or driver (not available unmodified) |
| Not tested | valid-but-untracked / inferred poses (the remote driver cannot produce them); reordering; a compromised app or bridge rewriting provenance (S2) |
| Method gap? | **No method gap is claimed.** The failing class is an information-availability limit. The successful classes use known provenance practice. |
