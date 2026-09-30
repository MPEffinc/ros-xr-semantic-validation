# 05 — Ablations and Residual Mechanisms

All numbers: median misleading seconds per 10 s trial (seeds with > 0.1 s), h = 0.25 s, from
`../results/summary_all.csv` (frozen analysis) unless marked **EXPLORATORY** (post-hoc, `../results/exploratory_posthoc.json`,
`scripts/n1_exploratory.py`; not used by the frozen decision rules).

## 1. Removing one ingredient at a time (frozen ablations)

| Ablation | Effect (B0 unless noted) | Interpretation |
|---|---|---|
| PD without delay model | A 0.28 (5), AC 0.16 (5), AD 0.16 (4), ACDF 0.10 (2); others 0 | known network delay must be propagated to the display |
| PD without SA model | no change at B0; F/B2 0.08 → 0.00 | SA blend here is slow; its share is small |
| PD without CBF model | no change | the filter's effect is also visible in fresh state within h |
| PD/PC without bound | PD D 0.32 (3), AD 0.08 (2); PD D/B2 0.48 (4) | the bound widening on Servo intervention flags is what covers collision scaling |
| PD/PC without intervention flag | identical to "without bound" | the flag's only role is widening the bound |
| PC without final command (falls back to post-filter twist) | PC 0.00 in all conditions at B0/B2 | at h = 0.25 s the post-filter twist + bound is as good; the final command matters for E (below) |
| PC/PD without stale stop | B1: PC 0.50–1.78 (5 each), PD 0.10–3.54 (E 3.54, AD 2.52, D 1.92); B2: PD A 0.58, D 0.70, E 0.96, F 0.90 | stale stop is what prevents misleading under stale feedback — at the price of freezing |

## 2. Where the residuals are (mechanism)

**R1 — operator input changes still in flight (PC in N0/A).** Every PC exceedance in N0/B0 falls at
t ≈ 0.24, 3.22, 4.26, 9.22 s, i.e. ≈ 0.24 s after each operator step (0, 3, 4, 9 s)
(`exploratory_posthoc.json`, `pc_excess_times_N0_B0`, all 5 seeds). The robot-side final command cannot yet
reflect an input the operator has already given; PD, which feeds the operator's own recent inputs through
the known pipeline model, shows 0.00 s. → *propagation of information the display already has.*

**R2 — silent, unmodelled modifier (PD in E/B2, 0.14 s, 5/5 seeds).** Servo smoothing reports status 0, so no
flag widens the bound, and PD does not model the filter. PC — which extrapolates the smoothed final command
and its velocity — shows 0.00 s in E at both B0 and B2. EXPLORATORY: seeding PD's forward model from the final
command instead of the measured state (PE) gives E/B2 0.14 (4) and F/B2 0.08 (1), 0 elsewhere; so the
information that removes R2 is the final command's *velocity trend*, not its position. Modelling the known
Butterworth filter (deterministic, parameters in the Servo config) or flagging "smoothing enabled" was not
run — **NOT_VERIFIED** that it removes R2, but both are standard.

**R3 — Servo collision scaling (D/AD).** Not modelled by PD; covered by the intervention flag + bound
(0.00 s at B0/B2 with bound, 0.32/0.48 s without). Servo's collision check is deterministic given scene and
state and could be modelled too (not run).

**R4 — feedback age beyond the stale threshold (B1).** Either freeze (100 % with the frozen 0.2 s threshold)
or mislead (0.1–3.5 s for PD without stale stop, worst where unmodelled Servo modifiers act: E, AD, D). This is
the standard latency/uncertainty trade-off of predictive displays; with every modifier modelled, the
remaining error would be bounded by plant-model error only (not run).

## 3. Structural-failure checks (Q3 candidates from the brief)

| Candidate mechanism | Reproduced? | Evidence |
|---|---|---|
| several controllers modify the command at different points | modifiers at 4 points (delay, SA, CBF, Servo) combined in ACDF: PD 0.00 s at B0 and B2 | no |
| prediction instant and execution authority structurally cannot coincide | the in-flight gap (R1) is closed by forwarding the operator's inputs through the known model | no |
| no single authoritative future trajectory definable under runtime interventions | PD with known laws + flag-widened bound stayed within its bound (max excess 0.3–0.6 cm at B0) | no |
| discrete mode transition not representable by a bound | Servo collision decelerate/hold (code 4) is discrete; flag-triggered bound covered it (D, AD: 0.00 s) | no |

No failure remained that the available information and standard handling (model known laws, propagate
final command and inputs, flag-widened bound, stale stop) did not remove; the only open cells (R2 E/B2,
R4 B1) point to unmodelled-but-deterministic components or to a latency trade-off.
