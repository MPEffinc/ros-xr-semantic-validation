# S4-B CP27 Docker C-ID binding-integrity formal freeze (scoped)

**No C-ID formal trial has run at this checkpoint.** The configuration is `XRROS-S4B-CIDF1-1.0.0`, which implements the C-ID Q1 design report as a scoped study. Research protocol XRROS-S4-1.0.0 is unchanged. Setup was C-ID Q1 (`068d23d`), with 20/20 qualified.

## Design

**Formal trials: 120.** In each of 5 repetitions, the order of the four kinds is shuffled with seed 20260922, and within each kind the six arms are shuffled as well:

- B0 and the shim;
- B1, B2-native, B2-composed and B3 under I_FULL.

**Not counted here:**

- I_NATIVE × 4 kinds × 5 repetitions is registered NOT_RUN, because it is UNOBSERVABLE by construction. Its setup evidence is in C-ID Q1.
- The old-generation kind **reuses** the D5 formal evidence and is not counted as a C-ID trial.

**Runtime:** about 1.9 h, run sequentially with no concurrent load.

## Runtime

`inputs/run_formal.py` is the D6 formal runner with these changes:

- the C-ID Q1 `/code` and `/analysis` directories;
- `CASE_ID=CID` and `CID_KIND`;
- the `s4cidf_*` container prefix.

The retry and stop rules are unchanged.

## Frozen scorer (`analysis/cid_formal_audit.py`)

**Validity.** The C-ID Q1 setup `inspect()` must pass, together with the B0/shim pair gate and the matched-schedule gate for each repetition and kind.

**Policy.**

| Rule | What must hold |
| --- | --- |
| P1 | No false rejection of samples 36–49 before the trigger. Pre-fault joint within 0.02 rad of the shim at slot 49. |
| P2 | The injected event is rejected with the kind's registered reason within 50 ms of its local arrival. The trigger is B1's creation of the sample, or the original receiver's receipt of the slot-50 stamp. |
| P2 | An explicit neutralization request within 50 ms, followed by a stop reply and a controller zero. |
| P2 | No controller output after trigger + 300 ms, and Gazebo settled by trigger + 1 s. |
| P3 | The injected event is never accepted, and no nonzero Servo command derives from it. Lineage is followed by the bound stamp, because the ID may be absent or reused. |
| P4 | No held-grip restart from samples 51–55. |

Mechanism attribution is kept separate, and the common stop adapter is never credited to native ROSMonitoring.

## Validation

`analysis/test_cid_formal_audit.py` passes 7/7 on temporary copies of setup raw. It covers:

- PASS for B1, B2-composed and B3 on every kind;
- FAIL for B2-native (no neutralization);
- the shim's consequence;
- an injected event that is accepted → P3;
- a wrong reason → P2;
- a normal false rejection → P1;
- a late or absent request → P2;
- a missing injected receipt → INVALID;
- BLOCKED and NOT_RUN.

A software preflight on the 18 setup I_FULL cells, labelled not formal, gives:

- PASS for every B1, B2-composed and B3 cell, with the correct reason and 0 injected commands reaching Servo;
- `P2_NO_EXPLICIT_NEUTRALIZATION_REQUEST` for B2-native.

An empty schedule gives 120 NOT_RUN. The setup raw is unchanged.

The freeze must be pushed and the SHAs must match before the first trial.
