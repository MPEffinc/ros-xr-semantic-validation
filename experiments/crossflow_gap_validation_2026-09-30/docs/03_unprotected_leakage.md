# 03 — Unprotected Leakage Baseline (Stage 3)

**Status: NOT_RUN — no real paired dataset** (`02_dataset_pipeline.md` §1).

Not substituted by synthetic traffic: any classifier result on generated traces would measure the
generator, not XR–ROS teleoperation, and the README rule forbids deciding on synthetic data.

## GATE 2: UNDECIDED (no experimental evidence)

What is known from literature only (evidence levels in `../literature/defense_baselines.md`), and is
**not** an experimental result of this study:

- Encrypted robot traffic leaks robot operations (Tang et al. line of work, P1–P3).
- Encrypted VR traffic leaks user activity and identity (P6–P8).
- Hence single-flow leakage on *both* sides is established prior art; whether the combination adds
  information for XR–ROS teleoperation is not measured anywhere we found.

Planned design, kept for a future real session (not executed): per-flow A (XR media), B (XR input),
C (ROS command), D (ROS feedback) and combinations A+B, A+C, B+C, A+B+C, ALL; features = packet size,
direction, inter-arrival, counts, bytes, bursts, sliding-window rates; attackers = random forest and a 1D-CNN;
metrics = accuracy, macro-F1, confusion matrices, repeated session-separated splits, random-label sanity check.
