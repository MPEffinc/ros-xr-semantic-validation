# R11a — M12 follow-up: does any available signal reveal a prolonged source stall? (protocol; frozen before runs)

## Selected residual and question

**Selected residual.** In R11 every arm admitted all 84 source-stale commands of SRC_STALL (1.5 s,
3 trials per arm), including the strongest fix A2.

**This round's question** (different from R11's comparison of policies): during a **prolonged** source
stall, does **any** signal available on this path change, so that an existing check could separate
it from a legitimate still hand? R11 already showed content is identical for both (93/96 vs 90/96
consecutive repeats), so content is not the signal. The candidate signals are:

- the OpenVR pose validity and tracking result, carried by A2 with every command;
- the runtime client flags (FOCUSED, IO_ACTIVE, INPUTS_BLOCKED) used by A3;
- the app's acquisition-time and sequence progression.

## Design (strongest baseline kept: A2; independent baseline A3)

- **Condition** `SRC_STALL_LONG`: the M12 N_MOVE input with the feeder silent for **6.0–11.0 s (5 s)**.
  The truth hand keeps moving (segments W and C).
- **Arms and trials.** A2 and A3 × 3 = **6 formal trials** (`schedule_followup.csv`), on the R11
  stack unchanged (frozen R11 files).
  - Runner: `run_m12_followup.py`, a copy of `run_m12.py` with one added condition entry and the
    scenario directory `scenarios_followup/`.
- **Policies.** Thresholds unchanged from R11 (τ = 100 ms; truth = no feeder packet in the 100 ms
  before the bridge receives the message). **No criterion change.**

**Outputs** (`analysis/analyze_followup.py`):

- admitted / total stale_source, and fresh false blocks (as R11);
- the set of validity values and tracking-result codes carried in the stall window (A2);
- the set of runtime flag tuples in the stall window (A3);
- consecutive identical content;
- feeder packets in the stall (0 expected).

**Reading.**

- If validity, tracking result and runtime flags stay at their normal values throughout the 5 s
  stall, then **no existing signal on this path separates a source stall from a legitimate still
  hand**. Separating them would need a source sample time or sequence that the runtime does not
  keep (`r_hub.c` stores none). That would be an information-availability limit of this deployment,
  not a failure of A2's checks.
- If any signal changes, report which signal changed and when.
