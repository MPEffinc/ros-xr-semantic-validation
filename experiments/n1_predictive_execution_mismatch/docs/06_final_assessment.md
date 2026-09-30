# 06 — Final Assessment

## Answers to the refutation questions

**Q1 — Does a proper combination of existing components substantially bound the mismatch? YES.**
- The naive display misled for 6.6–10 s of every 10 s trial, with errors up to 31 cm.
- Every combination that used fresh authoritative state brought that down to fractions of a second.
- Against the frozen rules (docs/02 §5):
  - **PD** (known-pipeline forward model + flag-widened bound + stale stop): 0.00 s at B0 in all 10 conditions,
    at h = 0.25 s and h = 0.5 s. At B2 it was ≤ 0.08 s everywhere except E, where it was 0.14 s.
  - **PC** without the final-command term (post-filter twist + bound + stale stop, a frozen ablation):
    0.00 s in every B0 and B2 cell at h = 0.25 s, 0/5 seeds above 0.1 s, at most 0.49 cm over its bound.
  - The strict single-predictor reading of Q1 is therefore met at h = 0.25 s (B0, B2) by that pre-registered
    variant.
  - The primary PD misses the threshold in one cell (E/B2) by 0.04 s.
- **Under constant 300 ms feedback delay (B1)** every bounded predictor freezes (with stale stop) or misleads
  (without it). This is the standard freeze-vs-mislead trade-off, not a new failure.

**Q2 — Are the residuals resolved by implementation-level propagation? YES, for every residual identified.**
- R1 — input still in flight. Fixed by feeding the operator's own inputs through the known pipeline model (PD).
- R2 — silent smoothing. Removed by using the final command's velocity trend (PC: 0.00 s in E). Modelling the
  filter is standard but was **not run**.
- R3 — collision scaling. Covered by Servo's status flag widening the bound.
- R4 — stale feedback. Handled by the stale stop, trading freeze time.

**Q3 — Is there a repeated structural divergence that no combination removes? NO.**
- Four modifiers acting at different pipeline points (ACDF), a discrete Servo mode (collision decelerate/hold)
  and a silent filter were all bounded once the available information was propagated (docs/05 §3).

## Scope limits (what this pilot does *not* show)

- **No real HMD and no human operator.** The operator is scripted and the display is a model, so
  XR-specific effects are untested. Examples: reprojection, operator reaction to a freeze, and user trust.
  No XR-specific claim is made in either direction.
- **One plant (UR5 in Gazebo) and one 1-D reach scenario at 0.08 m/s.** Faster motion, contact tasks and
  mobile bases were not tested.
- **Some pipelines were not tested:**
  - learned policies with non-deterministic or unknown modification laws, where PD's "known law" assumption
    fails by construction;
  - planners that replan discretely (MoveIt planning was not in the loop; Servo is not a planner).
- **Two items were not run** (NOT_VERIFIED, noted in docs/05):
  - modelling Servo's smoothing and collision check;
  - a fused PC+PD predictor.

## Verdict

**IMPLEMENTATION_GAP_ONLY → N1 is KILLED as a research item.** The prediction–execution mismatch is real and
large for a naive display. It is eliminated in this pilot by the normal engineering combination:
- fresh authoritative state;
- propagation of known modifiers or of the post-filter / final command;
- an error bound widened on reported interventions;
- stale-freeze.

The residuals trace to missing propagation of information that already exists, or to the known
latency/freeze trade-off. None is a mechanism that needs a new method.

The one direction the pilot could not reach, modifiers whose laws are *unknown* to the display (e.g. a
learned policy), is not pursued here. Per the brief, no new idea is generated after a KILL. A new gap search
belongs to a separate, deeper literature review.
