# S4-B CP21 Docker D4-L post-gate delivery-delay formal freeze (scoped design)

**No D4-L formal trial has run at this checkpoint.** Research protocol XRROS-S4-1.0.0 (SHA-256 `3a40337121f8d687dc68036ff2ffc85a1bc6eda275a700ba7d9e8119cd322969`) is unchanged. This formal configuration is `XRROS-S4B-D4LF1-1.0.0`, a **scoped study** under the user's minimum-sufficient-evidence scaling policy.

Setup is fully qualified. D4LQ1 was frozen at `b1ab8bf`; its frozen audit qualified 5/15 cells and is immutable. D4LQ2 (frozen at `f8a0324`, analyzer-only reconnect-rule correction, runtime byte-identical) re-audited the retained raw at 15/15 MEASUREMENT_QUALIFIED. The B0/shim pairs pass at L750 (0.053 ms, 0.0029 rad) and L000 (0.052 ms, 0.0033 rad). D4 formal (630/630) and earlier results are not pooled.

## Design report (required before freeze)

### Registered candidate matrix

The full matrix is 5 delays (L000/L050/L150/L350/L750) × 18 arms × 5 repetitions = **450 trials, about 7.5 h**. The 18 arms are the same as in D4: B0, shim, 4 I_NATIVE arms, and 4 I_FULL defenses × 3 profiles.

### Essential Gazebo evidence

Per repetition, 40 trials:

| Trials | What | Why it is required |
| --- | --- | --- |
| 10 | B0 + shim at every delay | Positive controls. The pair gate and the allowed-path reference depend on the delay, because capture is 4.8 s + delay + 2 s. |
| 5 | B1 I_FULL at every delay (runtime F250) | The central placement comparison. B1 decides on age < 5 ms, so it sees no delay. |
| 21 | B2-native, B2-composed and B3 I_FULL at 7 delay/profile cells | Receiving-side detection, mechanism attribution and equal information, at the discriminating cells below. |
| 4 | I_NATIVE B1/B2/B2-composed/B3 at L750 | Confirms that no native defense can see the maximum delay. |

The seven delay/profile cells:

| Cell | Role |
| --- | --- |
| L000/F100 | Accept at the strictest profile (positive control) |
| L050/F100 | Boundary; the cached-copy band seen in D4 |
| L150/F100 | Reject |
| L150/F250 | Accept |
| L350/F250 | Reject |
| L350/F500 | Accept |
| L750/F500 | Reject even at the loosest profile |

### Combinations judged redundant, with reasons

- **B1 I_FULL under F100/F500 (10 per repetition).** The runtime is profile-invariant, because the source gate always sees age ≈ 0 (< 5 ms in all D4 A000 runs and host tests). The consumer-level result for each profile is computed **offline from the same run** and labelled `INFERRED_*`. The analyzer refuses the inference if any B1 decision is older than 99 ms.
- **B2-native, B2-composed and B3 at the other 8 delay/profile cells (24 per repetition).** Freshness is monotone in F: acceptance at F implies acceptance at every F′ > F, and rejection at F implies rejection at every F′ < F. When age is already over budget on arrival, the trigger (the receipt) and the stop path do not depend on F. These cells are registered as `NOT_RUN_INFERRED_BY_MONOTONICITY`.
- **I_NATIVE at L000–L350 (16 per repetition).** The native ROS interface carries no source time, so a native defense cannot observe age at any delay. D4 showed this directly in 140/140 trials, and L750 re-confirms it under delay. These are registered as `NOT_RUN_SCOPED_UNOBSERVABLE_BY_CONSTRUCTION`.

### Proposed campaign

**200 formal trials** (40 × 5 repetitions), randomized with seed 20260922: delay blocks are shuffled within each repetition, and arms within each block. The estimated runtime is **3.5 h**, sequential, with no concurrent load.

### Claims supported and excluded

The scoped design supports claims about:

- B1's placement effect;
- detection by receiving-side B2-composed and B3, and the missing neutralization in B2-native;
- the boundary at L050/F100;
- equal-information comparison at the tested cells;
- consumer-level source age.

It excludes direct runtime evidence for the 50 NOT_RUN combinations per repetition. Those are either inferred and labelled, or scoped out. The full registered 450-cell D4-L comparison is therefore **not** claimed complete.

## Runtime

`inputs/run_formal.py` runs the D4 formal runner logic with the D4LQ2 `/code` and `/analysis` directories read-only. It sets `CASE_ID=D4`, `AGE_CONDITION=A000`, `XR_DELIVERY_DELAY` and `XR_FRESHNESS_NS`, and names containers `s4d4lf_*`.

The retry and stop rules are the same as in D1–D4:

- **Retries:** at most two, and only for an attempt that ends without a start barrier.
- **Formal trial:** the first attempt that reaches the barrier is the formal trial.
- **Stop conditions:** the run stops if a cell exhausts its retries, or after two consecutive post-barrier nonzero exits.

## Frozen scorer (`analysis/d4l_formal_audit.py`)

**Validity.** The frozen D4LQ2 setup audit covers the FIFO delivery, the idle-time reconnect rule and delay-scaled ticks. The scorer adds three requirements:

- the defense's copy of the stamp must equal the recorded one;
- decision coverage over the 36 teleop samples must be exact;
- the per-repetition/delay B0/shim pair and each arm's schedule against its shim must pass.

**Policy.** This changes one element prospectively, based on D4's post-freeze finding. The expectation is now **per decision**:

- **Trigger:** the local trigger is `max(arrival, stamp + F + 1 ms)` of the first clearly over-budget sample.
- **Boundary stops:** a stop caused only by an in-band rejection is `UNKNOWN_BOUNDARY_STRADDLE`.
- **Consumer level:** the source age at each sample's **first** exact Servo callback is judged. A nonzero over-budget sample reaching the consumer is a FAIL. For B1 the label is `…_PLACEMENT_EFFECT_POST_DECISION_DELAY`.
- **Thresholds:** the 50 ms / 300 ms / 1 s and 0.02 rad limits are unchanged.
- **Attribution:** mechanisms are attributed separately, and I_NATIVE is UNOBSERVABLE.

Exact added latency is UNKNOWN. Joint causation is interval-only.

**Pre-formal validation.** `analysis/test_d4l_formal_audit.py` passes 7/7 on temporary copies of D4LQ1 setup raw. The tests cover:

- the B1 placement FAIL, with correct gate-local decisions and profile inference;
- refusal of the inference when a B1 decision is too old;
- the B2-composed/B3 receiving-side PASS and the B2-native no-neutralization FAIL;
- accept cases and I_NATIVE UNOBSERVABLE;
- relabelling a run to a stricter profile exposing false acceptance and consumer over-budget;
- the prospective boundary straddle;
- early release or a downstream restamp → INVALID;
- the NOT_RUN registry (24/10/16) and BLOCKED/NOT_RUN states.

An empty schedule yields 200 NOT_RUN. The D4LQ1 raw still verifies.

## Before the first trial

`freeze_inputs.sha256` records the hashes. The freeze must be committed and pushed, and SHA alignment verified, before the first trial.
