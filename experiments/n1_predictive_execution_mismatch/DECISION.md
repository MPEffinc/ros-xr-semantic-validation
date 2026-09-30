# Decision — N1 predictive/twin display vs. executed ROS state

**Verdict: IMPLEMENTATION_GAP_ONLY → KILL** (2026-09-30)

- Naive prediction (operator input = future state) misleads for 6.6–10 s of each 10 s trial, with errors up to
  31 cm when MoveIt Servo's collision scaling or a CBF filter changes the command (50/50 valid Gazebo trials).
- Existing ingredients remove it:
  - known-pipeline forward model + flag-widened bound + stale stop (PD): 0.00 s at B0 in all 10 conditions
    (h 0.25 and 0.5 s);
  - post-filter twist + bound + stale stop: 0.00 s in every B0 and B2 cell at h 0.25 s.
- Every residual has an implementation-level cause, each removed by information already available:
  - input still in flight → operator inputs through the model;
  - silent Servo smoothing → final-command velocity;
  - collision scaling → Servo status flag + bound;
  - stale feedback → freeze.
- No structural failure (multi-point modification, discrete mode change, no single authoritative future) was
  reproduced.

| Question | Answer |
|---|---|
| Solved by existing methods? | **Yes**, in this simulation |
| Remaining failure? | Only the freeze-vs-mislead trade-off under constant stale feedback (B1) and a 0.14 s residual for one predictor (PD) in E/B2; both explained, neither structural |
| Next action | **Stop N1.** No new idea is proposed here. A new gap search is to be run as a separate, in-depth literature phase |

**Limits:** synthetic operator and display, no HMD/human; one UR5 plant; deterministic, known modifier
laws. XR-specific novelty was not claimed and cannot be claimed from this pilot.

Evidence: `docs/03`–`06`, `results/summary_all.csv`, `figures/misleading_heatmap.svg`,
raw-log hashes `results/formal_raw_sha256.txt`.
