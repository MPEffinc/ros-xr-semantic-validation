# 01 — Problem Definition (N1)

## Not the question

"A digital twin can differ from the real robot pose" is known (predictive-display literature; TeleXR
2506.01135; `../../crossflow_gap_validation_2026-09-30/docs/08_new_gap_search.md` §1). It is not tested here.

## The structure under test

```
operator input u_op(t) ──► XR-side predictor ──► displayed future pose  p̂(t+h)
        │
        └─► [network delay] ─► shared autonomy (blend) ─► safety filter (barrier)
               ─► MoveIt Servo (collision / singularity / joint-limit scaling, optional smoothing)
               ─► final executable command (JointTrajectory) ─► ros2_control ─► Gazebo robot
               ─► actual pose p(t+h)
```

**Question.** Which point of the control pipeline must the prediction draw on for p̂(t+h) to stay
consistent with p(t+h)? And does the normal combination of existing techniques make it consistent
enough? The existing techniques are:
- authoritative state
- freshness validation
- post-filter or final-command propagation
- an error bound
- stale-freeze
- intervention flags

## Quantities

- h — display look-ahead (prediction horizon), fixed per run and pre-registered.
- e(t) = ‖p̂(t+h) − p(t+h)‖ — end-effector position error.
- Also: max e, trajectory deviation, e right after interventions, e under stale state.
- **Misleading duration** — time during which e exceeds the displayed bound, or a bound is not
  displayed, while e > ε_task.
- Freeze ratio and task interruption.

## Hypotheses

- **H0 (kill hypothesis, expected by default).** Predictor C bounds e (with an honest bound) in every
  condition, and residual misleading duration is ≈ 0 or explained by an implementation omission.
  Predictor C = fresh authoritative state + final executable command + error bound + stale stop +
  intervention flag.
- **H1.** Some condition makes C misleading repeatedly, and the cause is structural. Candidate causes:
  a modification decided *after* the prediction instant within the horizon h, or a discrete mode
  change that no continuous bound represents.

## Verdict options

KILL / IMPLEMENTATION_GAP_ONLY / NEEDS_REAL_XR_VALIDATION / METHOD_GAP_CANDIDATE (not novelty).

No real HMD is used. The XR display is a synthetic predictive-display model, so XR-specific novelty
cannot be claimed from this pilot.
