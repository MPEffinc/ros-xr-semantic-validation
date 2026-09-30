# 03 — Naive Predictive Display (Baseline P0)

Formal campaign: 50 trials (10 conditions × 5 seeds), all **valid**.
- Reset residual ≤ 0.0020 rad.
- ≥ 480 operator ticks and ≥ 300 Servo outputs per trial (`../results/summary_trials.csv`).
- Raw logs: 44 MB, git-ignored; sha256 in `../results/formal_raw_sha256.txt`.
- Analysis output sha256: `../results/analysis_sha256.txt`.

Code and data:
- Campaign command: `scripts/run_campaign.sh` (log `results/raw/campaign.log`: all `rc=0`, `SWAP_OK` for E, `CAMPAIGN_DONE`).
- Analysis: `scripts/n1_analyze.py … --ablations`.
- Summary: `scripts/n1_summarize.py` → `../results/summary_all.csv`.
- Figure: `../figures/misleading_heatmap.svg`.

## P0: operator input taken as the future robot state (h = 0.25 s, B0 fresh)

| Condition | mean e (cm) | max e (cm) | misleading s / 10 s (median) | seeds > 0.1 s |
|---|---|---|---|---|
| N0 | 1.8 | 2.6 | 7.52 | 5/5 |
| A delay 150 ms | 2.8 | 3.8 | 8.00 | 5/5 |
| C CBF filter | 6.4 | 11.1 | 9.96 | 5/5 |
| D obstacle (Servo collision scaling) | 11.6 | 31.2 | 8.68 | 5/5 |
| E Servo smoothing | 6.2 | 12.7 | 9.16 | 5/5 |
| F shared autonomy | 2.6 | 8.7 | 6.64 | 5/5 |
| AC | 6.0 | 11.0 | 10.02 | 5/5 |
| AD | 12.0 | 31.5 | 8.90 | 5/5 |
| CDF | 5.7 | 11.1 | 9.94 | 5/5 |
| ACDF | 5.7 | 11.0 | 10.02 | 5/5 |

## What this shows (and does not show)

- The naive display misleads for most of every trial. The error grows with every downstream modifier:
  - up to 31 cm when Servo's collision scaling stops the arm while the display keeps extrapolating operator input;
  - about 11 cm when the CBF caps the reach at 0.15 m against a commanded 0.25 m.
- Even N0 misleads, because the pipeline lags the input by about 0.25 s (Servo + JTC + Gazebo) and P0 has no
  feedback. P0 also accumulates the per-trial operator bias drift.
- Task interruption happens in the robot, independent of the display (`../results/summary_trials.csv`). The
  final x error exceeds 5 cm (C, D, E, F variants) in:

  | Condition | Trials |
  |---|---|
  | C | 5/5 |
  | AC | 5/5 |
  | E | 4/5 |
  | D | 3/5 |
  | AD | 3/5 |
  | F | 3/5 |
  | CDF | 1/5 |
  | ACDF | 1/5 |

  Servo halt (status 5) occurred in 0/50 trials. These are intended modifications, not failures.
- As stated in `01_problem_definition.md`, **the existence of this mismatch is not a research gap.** It is
  the known predictive-display problem and serves only as the baseline for docs/04.
