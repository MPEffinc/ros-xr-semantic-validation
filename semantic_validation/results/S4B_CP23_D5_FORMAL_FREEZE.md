# S4-B CP23 Docker D5 reconnect/generation formal freeze (scoped)

**No D5 formal trial has run at this checkpoint.** The configuration is `XRROS-S4B-D5F1-1.0.0`, a scoped study that implements the D5Q1 design report. Research policy XRROS-S4-1.0.0 is unchanged.

The setup is qualified:

- **D5Q1** (`8497e1a`): 12/14 qualified. It is preserved together with its two B3 logging-crash cells and the recorded runner-retry defect.
- **D5Q2** (`247d4d2`): 6/6 qualified.

## Design (from the D5Q1 design report)

- **Candidate matrix:** 100 trials.
- **Formal campaign:** **50 trials**, 10 per repetition over 5 fresh-state repetitions. Seed 20260922 shuffles the arms within each repetition.
  - B0 and shim: policy-independent, and they ignore the policy environment.
  - B1, B2-native, B2-composed and B3 under I_FULL, each with R_EXPLICIT and R_AUTO.
- **Registered NOT_RUN:** the four I_NATIVE arms under both policies, 5 repetitions each, labelled `NOT_RUN_SCOPED_UNOBSERVABLE_BY_CONSTRUCTION_SETUP_EVIDENCE_IN_D5Q1`.
- **Estimated runtime:** about 1 h, sequential, with no concurrent workload.

## Runtime

`inputs/run_formal.py` uses the D5Q2 `/code` and `/analysis`, read-only. It sets `CASE_ID=D5`, `AGE_CONDITION=A000`, `XR_REARM_POLICY` and F250, and names containers `s4d5f_*`. The retry rule is the same as in D1–D4-L: retries only before the barrier, at most two, and the first attempt that reaches the barrier is the formal trial. The runner stops the batch if a cell exhausts its retries, or after two consecutive post-barrier nonzero exits.

## Frozen scorer (`analysis/d5_formal_audit.py`)

**Validity.** The frozen D5 setup `inspect()` must pass. On top of it, the scorer requires:

- exact decision coverage for 36..55, 70..89, 72 and 110..129;
- a unique observation of the original receiver drop;
- a B0/shim pair within 5 ms and 0.02 rad;
- an arm schedule within 5 ms of the shim.

**Policy, for I_FULL defenses.** The scorer checks six properties:

| Check | Requirement |
| --- | --- |
| P1 | No rejection of 36..55 decided **before** the local disconnect trigger. Exact callbacks for those samples. Pre-fault joint within 0.02 rad of the shim. |
| P2 | Local trigger: the B1 source close, or the original receiver drop. Decision and explicit neutralization request ≤ 50 ms after the trigger. Stop reply and controller zero. No controller output from trigger + 300 ms until the defense re-arms. Settled by trigger + 1 s. |
| P3 | The gen-1 replay (docker:72) is rejected at every evaluation and never reaches Servo. |
| P4 | Nothing is allowed or moves before the re-arm. R_EXPLICIT: the re-arm happens on docker:94. R_AUTO: the re-arm comes at least 500 ms (minus the 1 ms band) after the first valid gen-2 evaluation that follows the replay. |
| P5 | Reference jump < 0.01 rad between the re-arm and the first docker:110 callback. |
| P6 | Subsequent movement 110..129 is allowed, moves, and is resumed by the defense's own decision. |

**Controls and reporting.**

- B0 and the shim are controls. Their replay-induced and held-grip consequences are reported.
- The final pose against the shim is reported descriptively only, because the shim's own trajectory contains the forbidden replay motion.
- Attribution is kept separate for B1 source-side decisions, the official `currently_false` verdict, B3 receiving-side decisions and the common stop adapter.
- The exact added gate latency is UNKNOWN.

**Defect found before the freeze.** The first software preflight, run on setup raw, marked every receiving-side arm P1 FAIL. The cause was cached `docker:55` copies re-evaluated after the drop, which were correctly rejected as `DISCONNECTED`. P1 was restricted to decisions before the trigger. This fixed the D3/D4 failure class prospectively, before any formal outcome existed.

**Validation.** `analysis/test_d5_formal_audit.py` passes 8/8 on temporary copies of the setup raw:

- PASS cells, the B2-native FAIL, and the shim consequence;
- an accepted replay → P3;
- a held-grip re-arm under R_EXPLICIT → P4;
- an early R_AUTO re-arm → P4;
- a normal false rejection → P1;
- a late or absent request → P2;
- a missing drop observation → INVALID;
- the BLOCKED and NOT_RUN states.

The empty schedule gives 50 NOT_RUN, and the setup raw is unchanged.

The freeze must be pushed and the SHAs aligned before the first trial.
