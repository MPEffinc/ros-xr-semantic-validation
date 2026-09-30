# 04 — Existing-Solution Combinations

Predictors (frozen, docs/02 §4): PA = fresh authoritative state + operator input; PB = + post-filter
command; PC = final executable command (Servo `JointTrajectory`) + error bound (r_nom = p95 of PC error in
N0/B0: **1.38 cm** at h = 0.25 s, 3.39 cm at 0.5 s) + intervention flag (bound + 0.10·h) + stale stop
(> 0.2 s → freeze); PD = PC's bound/flag/stale stop + forward model of every *known* modifier (delay, SA
law, CBF law) applied to operator inputs from the latest authoritative state.

Values: median over 5 seeds of misleading seconds per 10 s trial (in brackets: seeds with > 0.1 s).
Figure: `../figures/misleading_heatmap.svg`. Full table incl. mean/p95/max error, post-intervention and
stale-window error: `../results/summary_all.csv`.

## h = 0.25 s

| Cond | B0 PA | B0 PB | B0 PC | B0 PD | B2 PA | B2 PB | B2 PC | B2 PD |
|---|---|---|---|---|---|---|---|---|
| N0 | 0.00 (0) | 0.00 (0) | 0.14 (4) | 0.00 (0) | 0.88 (5) | 0.74 (5) | 0.14 (4) | 0.00 (1) |
| A | 0.36 (5) | 0.00 (0) | 0.18 (3) | 0.00 (0) | 1.26 (5) | 0.58 (5) | 0.12 (3) | 0.00 (0) |
| C | 0.64 (5) | 0.00 (0) | 0.08 (1) | 0.00 (0) | 1.50 (5) | 0.74 (5) | 0.06 (0) | 0.00 (0) |
| D | 0.48 (3) | 0.28 (3) | 0.06 (2) | 0.00 (0) | 1.40 (5) | 0.38 (5) | 0.06 (2) | 0.00 (0) |
| E | 0.04 (0) | 0.00 (0) | 0.00 (0) | 0.00 (0) | 1.00 (5) | 0.54 (5) | 0.00 (0) | **0.14 (5)** |
| F | 0.00 (0) | 0.00 (0) | 0.06 (1) | 0.00 (0) | 0.00 (2) | 0.76 (5) | 0.06 (1) | 0.08 (2) |
| AC | 0.82 (5) | 0.00 (0) | 0.08 (0) | 0.00 (0) | 1.70 (5) | 0.58 (5) | 0.06 (0) | 0.00 (0) |
| AD | 0.52 (5) | 0.20 (3) | 0.08 (1) | 0.00 (0) | 1.44 (5) | 0.22 (5) | 0.08 (0) | 0.00 (0) |
| CDF | 0.62 (5) | 0.00 (0) | 0.06 (0) | 0.00 (0) | 0.84 (5) | 0.76 (5) | 0.06 (0) | 0.00 (0) |
| ACDF | 0.60 (5) | 0.00 (0) | 0.06 (0) | 0.00 (0) | 1.56 (5) | 0.68 (5) | 0.06 (0) | 0.00 (0) |

Max error while displayed (median, cm) at B0: PA ≤ 2.4, PB ≤ 2.1, PC ≤ 2.6, PD ≤ 2.1, versus P0 up to 31.5.
PD's max excess over its own displayed bound was 0.3–0.6 cm at B0 (1.2 cm for E at B2).

## h = 0.5 s (secondary)

- PD: 0.00 s misleading in every condition at B0, and ≤ 0.02 s at B2.
- PC: 0.12–0.54 s (bound calibrated on N0; step changes grow with h).
- PB: 5.1 s in D/AD — Servo's collision stop is invisible to the post-filter command.

## B1 — constant 300 ms feedback delay

With the frozen stale stop (0.2 s), PC and PD are **frozen for 100 % of the trial**: no misleading time, but
the display never shows a prediction (task-interruption-by-design). PA/PB keep displaying and mislead
0.2–5.7 s (worst D/E). Without the stale stop (ablation, docs/05), PC misleads 0.5–1.8 s and PD 0.1–3.5 s,
worst in E (smoothing) and D/AD (collision scaling).

## Reading

1. Each existing ingredient removes a specific share of the mismatch; misleading time falls from 6.6–10 s (P0)
   to ≤ 0.18 s (PC) and 0.00 s (PD) at B0 in all ten conditions, including the full combination ACDF.
2. The **only** frozen-rule cells above 0.1 s for PD are E/B2 (0.14 s) — smoothing is a silent modifier (Servo
   status stays 0, so the intervention flag never fires) that PD does not model — and, for PC, the nominal
   step transitions (docs/05).
3. B1 exposes the classic freeze-vs-mislead trade-off: when feedback age permanently exceeds the stale
   threshold, a correct display must either freeze or show an unbounded guess.
