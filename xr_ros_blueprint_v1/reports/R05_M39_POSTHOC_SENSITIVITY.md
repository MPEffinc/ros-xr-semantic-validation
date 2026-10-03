# R05 — M39 post-hoc sensitivity analysis (existing data only, 2026-10-03)

**This is a post-hoc analysis.**

- It was written after R04, and no new trial was run.
- It does not replace or edit R03, R04 or any frozen file.

| Item | Location |
|---|---|
| Script | `experiments/M39_pilot/posthoc/sensitivity_m39.py`. It imports the frozen `analysis/analyze_m39.py` unchanged and re-implements the original criterion variants. |
| Output | `experiments/M39_pilot/posthoc/sensitivity_out.json` |
| Original criteria | R03 as committed at `e3e3778`, before any Gazebo run (`git show e3e3778:xr_ros_blueprint_v1/reports/R03_M39_PILOT_REVISED_PROTOCOL.md`) |
| Final criteria | R03 at freeze `467c223` |

## C. Raw availability and hash check (done first)

- **The raw data is present and matches.**
  - `raw/formal`, `raw/preflight` and `raw/host_checks` hold 1149 files, the same count as
    `results/M39_RAW_SHA256.txt`.
  - `sha256sum -c` reports 0 mismatches and 0 missing.
- **The analysis code is the frozen one.** `FREEZE_SHA256.txt` matches every frozen code file,
  including `analysis/analyze_m39.py`.
- **Recoverability is not claimed.**
  - The raw data is local only (ignored by Git) on this host.
  - The hash list proves integrity of what is present. It does not make the raw data recoverable if
    this disk copy is lost.
- **Every value below is recomputed** from these raw files.

## A. The four criteria changed before freeze

Counts are passes over valid trials; one invalid attempt was excluded as in R04. Each variant changes
**one** criterion and keeps the others final, unless marked "all original".

### A1. Status 4 in qualification

| | |
|---|---|
| Original (e3e3778) | qualification requires 0 Servo statuses ≠ 0 from engage to END |
| Final | statuses {1, 2, 3, 5, 6} disqualify. Status 4 is allowed if the lag in segment A (with status 4) minus the lag in segment C (without it) is ≤ 1.0 mm. |
| Reason and data used | All IK branches of the app's fixed engage pose showed status 4. The data was the qualification runs c1 (sol2, −z) and c5 (sol4, −x) N0/QF, all B0 normal scripts, plus an offline vertex-distance estimate (forearm–wrist_2 14.8–16.9 mm). |
| Recomputable from raw | yes (qualification raw present) |

| Run | Statuses | Original rule | Final rule |
|---|---|---|---|
| c1 sol2 −z N0 | {4, 5} | fail | fail |
| c5 sol4 −x N0 | {0, 4} | fail | pass |
| c5 sol4 −x QF | {0, 4} | fail | pass |

**Effect on the conclusion.**

- Under the original rule, no candidate qualifies, so R03 would have been **BLOCKED_ENV** and no
  formal trial would have run.
- No per-arm results exist under the original rule. Arm outcomes are **not evaluable** under it.

**Formal trials are unaffected by this rule itself.** R03 §7, original and final, recorded status 4
in formal trials and did not mask it. See §B for what that leaves open.

**What the "≤ 1 mm lag difference" criterion is.** It compares two *different* motion segments
(A and C) in the same run. It is not a paired with/without-deceleration comparison of the same
motion. It must not be read as the causal effect of the deceleration, nor as a bound for formal
trials. R04 §1 phrased it as "with a tracking effect ≤ 0.33 mm"; that phrasing overstates it.
CONTEXT was corrected at `1c5b162`; R04 itself is left unchanged.

### A2. Settled time (5.9 s → 5.7 s)

| | |
|---|---|
| Original | settled check at 5.9 s, against the engage-referenced feeder mapping. The rotation-rate window was [5.0, 5.9]. |
| Final | 5.7 s, against the latest Servo-input target. The rotation-rate window is [5.0, 5.7]. |
| Reason | In QF/I3 the hand starts its fast segment at 5.75 s, so 5.9 s measures a moving arm. In N0, 5.9 s is quiet. |
| Recomputable | yes |

The change has two parts:

- **The time (checker-error fix).** Only the time change is evaluated here; the reference change is
  in A3.
  - **N0 formal trials:** Normal is 3/3 per arm at both 5.9 s and 5.7 s. The time change does not
    alter any formal judgment, because Normal is evaluated only in N0, where 5.9 s is quiet.
  - **QF qualification:** at 5.9 s (original reference) the error is 10.5 mm, because the arm is
    moving at 0.075 m/s. At 5.7 s it is 0.04 mm.

  This part is a **checker-error correction**. The original time did not measure "settled" for
  scripts that move at 5.75 s. The quiet window intended by the protocol did not change.
- **The reference (feeder mapping → Servo target).** This is a **policy change**, treated in A3.

### A3. Mapping reference (feeder hand pose → the unmodified app's own command increments)

| | |
|---|---|
| Original | EE increment vs 0.5 × the feeder hand-position increment; body rotation vs the feeder hand-orientation increment |
| Final | EE increment vs the increments of the unmodified app's own Servo targets in the qualified B0 N0 run (`preflight/ref_increments.json`); settled check vs the latest Servo target |
| Reason and data used | In the qualification run c5 N0 (B0), the app's position target itself moved ≈ 13 mm while the hand only rotated (segment D). xrizer's OpenVR raw pose is offset from Monado's grip pose, so the feeder pose is not the pose the app sees. |
| Recomputable | yes |

| Arm | Normal (N0), original | Normal (N0), final | Live (N1+I2), original | Live (N1+I2), final |
|---|---|---|---|---|
| B0 | 0/3 | 3/3 | 0/6 | 3/6 |
| B1 | 0/3 | 3/3 | 0/6 | 6/6 |
| C1 | 0/3 | 3/3 | 0/6 | 6/6 |

**Mapping increments under the original reference fail in 45/45 valid trials.** In every arm, the
rotation and combined segments are off by ≈ 12.6 mm of position. The same offset appears in B0 N0
(no interruption) and in the qualification runs.

**Effect on the conclusion: yes.**

- Under the original reference, no arm meets the partial contract. B1's "full contract 15/15" and
  C1's "partial contract 12/12" do not hold.
- The original criterion fails identically for the unmodified app in normal operation. It therefore
  does not separate the arms; it measures the xrizer raw-pose offset.
- The R04 conclusions about B1 and C1 **depend on the final reference.**

**What the final reference does and does not establish.**

- It checks that after an interruption each arm's EE motion **reproduces the unmodified app's own
  command mapping** for the same scripted hand motion. That mapping includes the xrizer offset.
- It is **not** an independent check of the operator's intent or of coordinate-frame correctness.
  The app's mapping could itself be wrong (absolute anchor, raw-pose offset, frame choice), and the
  final criterion would inherit that.

### A4. L3 response latency (0.5 s → 1.0 s)

| | |
|---|---|
| Original | EE moves ≥ 2 mm along u within 0.5 s of 9.5 s |
| Final | within 1.0 s |
| Reason and data used | The normal plant latency in the B0 qualification runs was 0.38–0.43 s, and the smoke runs showed 0.41–0.43 s. |
| Recomputable | yes |

Measured L3 latency (s) in every valid trial where the arm moves after 9.5 s:

| Cell | Latencies | Cell | Latencies |
|---|---|---|---|
| B0 N0 | 0.391, 0.425, 0.422 | B1 N0 | 0.422, 0.404, 0.397 |
| B0 N1 | 0.440, 0.396, 0.416 | B1 N1 | 0.447, 0.386, 0.393 |
| B0 I1 | 0.435, 0.390, 0.401 | B1 I2 | 0.406, 0.418, 0.436 |
| B0 I2 | **0.648, 0.717, 0.644** | C1 N1 | 0.460, 0.408, 0.431 |
| B0 I3 | 0.402, 0.411, 0.439 | C1 I2 | 0.407, 0.436, 0.432 |
| C1 N0 | 0.374, 0.420, 0.398 | C1 I1 / I3 | 0.388–0.414 / 0.397–0.436 |

B1 in I1/I3 holds, so it has no latency, which is correct for those conditions.

| Arm | Live at 0.5 s | Live at 1.0 s |
|---|---|---|
| B0 | 3/6 | 3/6 |
| B1 | 6/6 | 6/6 |
| C1 | 6/6 | 6/6 |

**No judgment changes.**

- B0 I2 fails L3 at 0.5 s and passes at 1.0 s. Its Live already fails through L2: the absolute
  re-anchor jump is still in progress at 9.4–10.9 s.
- **The margin under 0.5 s is narrow.** The largest passing latency was 0.460 s (C1 N1), only 40 ms
  below the threshold. The 1.0 s threshold therefore did not decide any result. The 0.5 s threshold
  could have produced load-dependent failures, but did not in these 45 trials.

### A5. All original criteria together

The formal campaign would not have run (A1). Applied to the existing formal data anyway, A2 + A3 + A4
give **Normal 0/3 and Live 0/6 for every arm**. A3 dominates.

**Summary of A.**

| Change | Kind | Changes the R04 conclusion? |
|---|---|---|
| Settled time | checker-error fix | no |
| L3 threshold | — | no |
| Status-4 qualification rule | environment-qualification decision | without it, BLOCKED_ENV |
| Mapping reference | evaluation policy | **yes.** The R04 arm conclusions rely on it. |

## B. Servo status 4 (DECELERATE_FOR_COLLISION) in the formal trials

### What it is (code, MoveIt Servo 2.12.4)

- `servo.cpp` L495–501. Status 4 is set whenever the collision-monitor velocity scale lies strictly
  between 0 and 1. The scale is `exp(690.8 · (d − 0.01))` for self-collision distance d < 10 mm
  (`collision_monitor.cpp`).
- The scale multiplies the joint position step (L528) and the velocities (L676). It **slows**
  motion; it does not stop it.
- **Statuses 2 and 5** (HALT_FOR_SINGULARITY / HALT_FOR_COLLISION) halt motion. **Statuses 1 and 3**
  scale motion for singularity. These were the masking codes; none occurred in any formal trial.
- **The status carries no magnitude.** A scale of 0.999 and one of 0.01 both report 4.
- **Servo publishes no status while paused** (`servo_node.cpp` L346–350 `continue` before L427). The
  absence of status 4 during a B1/C1 hold is therefore **not** evidence that the proximity is gone.

### When it occurred (all 45 valid trials; spans of status-4 samples)

| Arm / condition | Status-4 spans (s) | Overlap with judged windows (status-4 samples) |
|---|---|---|
| all arms, N0 | 2.0 → 6.5–6.6 | settled window [5.5, 5.7]: 9–11 in every trial; none later |
| all arms, I3 | 2.0 → 6.0–6.05. C1: one sample at 7.71–7.72. | settled 10. P_stop window: 0. C1 P_resume window: 1. |
| B0, I1 | 2.0 → 7.70–7.77 | P_stop window [6.1, 7.5]: 70; P_resume window: 10–13 |
| B0, N1 | 2.0 → **15.5** (to the end) | P_stop 70; P_resume 15; increments [9.4, 14.9]: 275; L3 window: 75 |
| B0, I2 | 2.0 → 7.7, then 9.2–9.3 → **15.5** | P_stop 70–71; P_resume 9–10; increments 275; L3 75 |
| B1, I1/I3 | 2.1 → 6.0 (then paused: no status) | settled 10 only |
| B1, N1/I2 | 2.1 → 6.0, then 7.6–8.9 → 9.9 | P_resume 10; increments 26; L3 21 |
| C1, I1/N1/I2 | 2.2 → 6.0, then 7.7 → 9.8–9.9 (I2 has 3 spans) | P_resume 13 per event; increments 20–26; L3 15–21 |

In every condition except I3, status 4 appears whenever the arm is near the start configuration.
B0 returns to the start configuration after its absolute re-anchor (N1, I2), so its exposure is
roughly 10× that of B1/C1 in the increment and L3 windows.

### What the current data can and cannot support

- **Can:** no hard stop, singularity scaling or joint-bound status (codes 1, 2, 3, 5, 6) occurred in
  any formal trial. **The physical outcomes were not masked by a hard stop.**
- **Can:** command-level measures are unaffected by Servo scaling: the target-vs-EE jump at resume
  (B0 47.9 mm / 40 mm; B1/C1 0.00 mm) and P_rearm admissions.
- **Cannot:**
  - The deceleration magnitude in any window. The scale and distance were not logged and cannot be
    derived from the status.
  - Whether the deceleration changed B0's 300 ms resume travel (20–23 mm), B0's catch-up residual,
    or any arm's L3 latency.
- **Not removed.** "Not masked by a hard stop" ≠ "the deceleration's influence is removed."
  - The exposure differs strongly by arm (see the table above), so a slowdown would act unequally.
    For example, it could shorten B0's measured resume travel; the direction is a hypothesis.
  - The pre-flight lag comparison (A vs C) is between different segments and is not a causal
    estimate for any formal trial.

**What would settle it** (not done): log the collision-monitor scale or self-collision distance, or
replay the recorded joint states through MoveIt's collision check, or run a paired configuration
without the proximity.

## Consequences for R04's claims

- **Unchanged:**
  - B0's command-level resume jump and its unmasked execution;
  - B0's I3 residual (no status 4 inside its P_stop window);
  - the P_rearm results (permission level: B1 9/9, C1 0/9, B0 0/9).
- **Conditional:**
  - B1 "full contract 15/15" and C1 "partial contract 12/12" hold under the final mapping reference
    (consistency with the unmodified app's own command mapping), not under the original
    feeder-pose reference.
  - Physical travel and latency values carry an unquantified status-4 slowdown with arm-dependent
    exposure.
