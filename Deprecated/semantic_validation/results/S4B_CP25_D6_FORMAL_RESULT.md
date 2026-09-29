# S4-B CP25: Docker D6 invalidation/recovery comparison (scoped)

**Result: `D6_SCOPED_FORMAL_COMPLETE` — 50/50 executed, 50/50 `VALID_FORMAL_TRIAL`.** The configuration is the frozen scoped XRROS-S4B-D6F1-1.0.0, pushed at `d0dc3263a61b408df53fd5580893bf3bc3b16a75` before the first trial. The research policy XRROS-S4-1.0.0 is unchanged. The I_NATIVE formal repetitions are registered as NOT_RUN; their setup evidence is in D6Q1. The input is synthetic `isTracked=false` data, not actual Quest tracking loss, and no physical robot was used.

## Execution and validity

Evidence is in `runs/s4b_d6_formal_20260928T142519Z/`:

- `raw/`: 50 trial directories;
- `attempts.jsonl` and `commands.jsonl`;
- the frozen `analysis/d6_formal_audit.py` and its output `formal_summary.json`;
- `runtime_evidence_manifest.sha256`, which verifies.

All 50 rows ran once in order. Every first attempt reached the start barrier and exited 0, and no trial was retried or rerun. The 5/5 B0/shim pairs PASS (maximum 0.302 ms and 0.0067 rad), as do the 40/40 matched schedules. The largest pre-fault joint difference is 0.0053 rad.

## Results (5 repetitions per cell)

Timings are measured from the first `tracked=false` observation to the decision, the explicit request and settling.

| Arm (I_FULL) | R_EXPLICIT | R_AUTO | Decision / request / settle | Re-arm |
| --- | --- | --- | --- | --- |
| B1 source gate | 5 PASS | 5 PASS | ≤0.06 / 1.7–5.1 / 20–36 ms | R_EXPLICIT on docker:96 every time. R_AUTO on docker:86 or 87, 500–550 ms after the first valid sample. |
| B2-composed | 5 PASS | 5 PASS | 2.4–16.7 / 5.1–18.7 / 29–47 ms | 96, or 86 (500.1–516.7 ms) |
| B3 receiving side | 5 PASS | 5 PASS | 4.4–13.9 / 6.4–17.0 / 25–49 ms | 96, or 86 (500.1–516.1 ms) |
| B2-native | 5 **FAIL** | 5 **FAIL** | 3.6–15.2 / **none** / 273–307 ms | 96 / 86 |

All 10 B2-native trials fail with `P2_NO_EXPLICIT_NEUTRALIZATION_REQUEST`. The official verdict did reject the invalid and held-grip input, but settling came only through the original timeout, and that is not credited to it.

Across all 40 I_FULL defense trials:

- no invalid sample (56–75) reached Servo;
- the held grip produced no command before the registered re-arm;
- the reference jump after re-arm was below 1e-9 rad;
- the subsequent +0.15 X movement took place, about 0.39 rad.

The detecting mechanism differs by arm: the source-side decision for B1, the official `currently_false` verdict for B2-composed, and the receiving-side decision for B3. In every case the common stop adapter performed the stop and the resume.

**Original path (shim).** It produced zero nonzero commands during the invalid and held windows. The original tracked gate already stops invalid input, and its mapper recaptures the reference, so no motion appears while the hand stays at the reference.

This fixture places the press at the current reference. That makes the original's immediate held-grip re-engagement (no dwell, no release/edge) **unobservable as motion**. It is not demonstrated as either compliant or non-compliant. Lost/reacquired-reference jumps did not occur in any arm.

**Overhead (descriptive).** Median observed CPU relative to the shim, per 10 s capture:

| Arm | R_EXPLICIT | R_AUTO |
| --- | --- | --- |
| B1 | +0.75 s | +0.79 s |
| B3 | +0.67 s | +0.88 s |
| B2-native | +2.89 s | +3.17 s |
| B2-composed | +3.42 s | +3.47 s |

Exact added latency is UNKNOWN.

## Interpretation and boundaries

With I_FULL information, the existing configurations B1, B3 and B2-composed met every registered D6 requirement under both recovery policies:

- stop on invalidation while moving;
- no motion from invalid samples;
- no held-grip restart before the registered re-arm;
- dwell-limited R_AUTO;
- jump-free re-reference;
- the subsequent movement.

B2-native filtering does not neutralize. For the tested synthetic Docker conditions, this is consistent with **NO_METHOD_GAP**.

What these results do not cover:

- formal native repetitions;
- other invalid durations;
- a press at a displaced pose;
- actual Quest tracking loss;
- OpenVR;
- physical robots.

S5 remains INSUFFICIENT_EVIDENCE.
