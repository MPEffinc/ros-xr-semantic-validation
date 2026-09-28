# S4-B CP25 Docker D6 invalidation/recovery formal freeze (scoped)

**No D6 formal trial has run at this checkpoint.** The formal configuration is `XRROS-S4B-D6F1-1.0.0`, which implements the D6Q1 design report as a scoped study. The research policy XRROS-S4-1.0.0 is unchanged. Setup evidence is D6Q1, frozen at `d5fd00b` and 14/14 qualified.

## Design

- **Trial count:** 50 trials, 10 per repetition over 5 repetitions. The seed 20260922 shuffles the arms within each repetition. Estimated runtime is about 1 hour, run sequentially with no concurrent load.
- **Arms:** B0 and the shim (both policy-independent), plus B1, B2-native, B2-composed and B3 under I_FULL, each with R_EXPLICIT and R_AUTO.
- **Registered NOT_RUN:** the I_NATIVE arms under both policies, 5 repetitions each. The native interface lacks the freshness and generation that the registered recovery rule requires. The D6Q1 setup documents their behavior.

## Runtime

`inputs/run_formal.py` is the D5 formal runner with the D6Q1 `/code` and `/analysis`, `CASE_ID=D6` and the `s4d6f_*` prefix. The retry and stop rules are unchanged.

## Frozen scorer (`analysis/d6_formal_audit.py`)

The scorer is derived from the frozen D5 scorer. Validity is judged by the D6 setup `inspect()`, the B0/shim pair gate and the matched schedule gate. The policy rules are:

| Rule | Requirement |
| --- | --- |
| P1 | Normal input is not rejected before the trigger, and the pre-fault joint stays within 0.02 rad. |
| P2 | The trigger is the first `tracked=false` sample (docker:56): its creation for B1, or the original receiver's receipt otherwise. The decision and the explicit request each come within 50 ms. A stop reply and a controller zero follow. There is no controller output from +300 ms until re-arm, and the robot settles within 1 s. |
| P3 | The invalid samples 56..75 are all rejected and never reach Servo. |
| P4 | Nothing is allowed or moving before re-arm. Under R_EXPLICIT, re-arm happens on docker:96. Under R_AUTO, re-arm comes at least 500 ms (minus a 1 ms band) after the first valid evaluation following the last invalid one. |
| P5 | The joint jump from re-arm to the first docker:112 callback is below 0.01 rad. |
| P6 | Samples 112..131 are allowed, move the robot, and are resumed by the defense's own decision. |

Mechanism attribution is kept separate. The common stop adapter is never credited to native ROSMonitoring.

## Validation

`analysis/test_d6_formal_audit.py` passes 8/8 on temporary copies of D6Q1 setup raw. It covers:

- the passing cells and the B2-native FAIL;
- accepted invalid input → P3;
- a held-grip re-arm → P4;
- a short R_AUTO dwell → P4;
- a normal false rejection → P1;
- a late or absent request → P2;
- a missing first-invalid receipt → INVALID;
- BLOCKED and NOT_RUN rows.

A software preflight on setup raw also passed, labelled as not formal: every I_FULL arm passes except B2-native, which fails for the missing explicit neutralization. An empty schedule gives 50 NOT_RUN. The D6Q1 raw is unchanged.

## Gate

The freeze must be pushed and the SHAs aligned before the first trial.
