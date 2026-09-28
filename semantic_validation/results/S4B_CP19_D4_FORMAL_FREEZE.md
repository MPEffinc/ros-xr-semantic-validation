# S4-B CP19 Docker D4 source-freshness formal freeze

**No D4 formal trial has run at this checkpoint.** Research protocol XRROS-S4-1.0.0 (SHA-256 `3a40337121f8d687dc68036ff2ffc85a1bc6eda275a700ba7d9e8119cd322969`) is unchanged. This formal configuration is `XRROS-S4B-D4F1-1.0.0`.

It follows the complete D4 setup qualification:

- D4Q1, frozen at `d2ae0ed`: 18/20 MEASUREMENT_QUALIFIED. The two B1 transport cells were blocked and are preserved in `S4B_CP18_D4_Q1_QUALIFICATION_PARTIAL.md`.
- D4Q2 (XRROS-S4B-D4Q2-1.0.0, frozen at `e7bcb266e446d847b561f244568b16bc3c98ef94`): 5/5 MEASUREMENT_QUALIFIED. This includes the corrected B1 rejection cells and a fresh A750 B0/shim pair (0.054561 ms, 0.000989 rad).

The setup cells are not formal repetitions. D1 (48/50), D2 (47/50) and D3 (50/50; B3 I_FULL 4/5 frozen, 5/5 supplementary) are not pooled with D4.

## Schedule and runtime

The root is `runs/s4b_d4_formal_20260928T053240Z/`. `schedule.csv` contains **630 trial IDs** `docker_<arm>_<regime>_<condition>_<profile>_d4rNN`. It covers five repetitions of seven registered conditions:

| Condition | Source stamp |
| --- | --- |
| A000 | age 0 ms |
| A050 | age 50 ms |
| A150 | age 150 ms |
| A350 | age 350 ms |
| A750 | age 750 ms |
| H1P0 | Literal historical epoch value 1.0 s |
| FUT1S | +1 s future |

Each condition block has 18 arms:

- **Profile-independent (6):** B0 original, B0 observational shim, and B1/B2-native/B2-composed/B3 I_NATIVE. These run with the default environment and `profile_applies=0`, because their predicates have no source-time input. Their configurations are byte-identical under any profile.
- **Profile-dependent (12):** B1/B2-native/B2-composed/B3 I_FULL × F100/F250/F500.

`inputs/make_schedule.py` uses `random.Random(20260922)` to shuffle the condition order within each repetition, then the arm order within each block. All samples carry their own stamps, as in the D4Q1 fixture.

`inputs/run_formal.py` runs the D3 formal runner logic with the D4Q2 `/code` and `/analysis` read-only. It adds `CASE_ID=D4`, `AGE_CONDITION` and `XR_FRESHNESS_NS`, and uses containers named `s4d4f_*`. The retry and stop rules are the same as D3's:

- **Retries:** at most two, and only for an attempt that ends without a start barrier.
- **The formal trial:** the first attempt that reaches the barrier is the formal trial, whatever its outcome, and it is never replaced.
- **Stop conditions:** the run stops if a cell exhausts its retries, or after two consecutive post-barrier nonzero exits.

The expected runtime is about 11 hours, run sequentially.

## Frozen scorer (`analysis/d4_formal_audit.py`)

### Validity

The scorer runs the frozen D4Q2 `d4_setup_audit.inspect` on each attempt. That check covers:

- the fixture and stamps;
- the sender transport and reconnect explanation;
- the ACK and common clock;
- 300 ticks;
- 100 ms CPU/RSS and wait4;
- exact source→Servo callbacks on the recorded stamp;
- receiver source and stamp coverage;
- B2 calibration and official association;
- post-capture drain.

Motion is a validity gate only for B0 and the shim.

The formal layer adds three requirements:

- exact per-event coverage of all 36 teleop-true decisions;
- the defense's own copy of the stamp equals the independently recorded stamp (`SOURCE_STAMP_NOT_PRESERVED_TO_DEFENSE` otherwise);
- a unique receipt for the first over-budget sample.

A B0/shim pair in the same repetition and condition must be within 5 ms and 0.02 rad. Each arm's schedule against its shim must be within 5 ms. A gap in any of these is **INVALID_COMPARISON / UNKNOWN**. A cell with no attempt reaching the barrier is **BLOCKED_MEASUREMENT**.

### Policy

Every teleop-true decision is judged against the **source age at that decision**: decision time minus the recorded stamp. Receipt age and the ROS header are never used.

- **Expectation:** accept if −5 ms ≤ age ≤ F, both bounds inclusive. Anything within ±1 ms of a bound is UNKNOWN and is not scored.
- **Failures counted:** false acceptance, false rejection, and nonzero Servo callbacks parented to an over-budget sample.
- **Where rejection is expected:**
  - The local trigger is the first over-budget sample observable at the defense's location. For B1 this is its creation. For B2, B2c and B3 it is the receiver receipt, or stamp + F + 1 ms if the sample only crosses the budget while cached.
  - Both the decision and the explicit neutralization request must come ≤ 50 ms after the trigger, and neither may come before it.
  - The stop needs a reply and a controller zero.
  - There must be no nonzero controller command after trigger + 300 ms.
  - Gazebo must settle by trigger + 1 s.
- **Where acceptance is expected:**
  - There must be no false rejection and no stop request.
  - Exact callbacks must exist for docker:36..55.
  - Motion must exceed 0.01 rad.
  - The final joints must be within 0.02 rad of the same repetition/condition shim.

**I_NATIVE arms** are **UNOBSERVABLE** for freshness. They are FAIL_POLICY only on an observable false rejection or an allowed-path failure. The analyzer still reports, by its own age computation, how many over-budget samples reached nonzero Servo commands.

**Attribution** is kept separate for:

- B1 source-side decisions;
- the official ROSMonitoring `currently_false` verdict;
- B2-composed health/watchdog;
- B3 receiving-side decisions;
- the common stop adapter, which is never credited to native ROSMonitoring.

The following are not measured or claimed:

- exact added gate/transport latency and the monitor's internal publish time (UNKNOWN);
- a per-source controller or joint parent (the analysis is interval-only);
- protection against delay after the source decision, which is the separate D4-L case.

### Pre-formal validation

`analysis/test_d4_formal_audit.py` passes 11/11 tests on temporary copies of D4Q1/D4Q2 setup raw. The D4Q1 copies get a synthetic `connect` transport record; this is a labelled test adaptation. The tests cover:

- fresh accept PASS for I_FULL and UNOBSERVABLE for I_NATIVE;
- stale reject PASS with official-verdict and B1 attribution, including H1P0;
- B2-native blocking without neutralization → FAIL;
- relabelling the profile from F500 to F250 on accepted A350 data → FAIL, with false acceptance and forbidden callbacks;
- a mutated false acceptance;
- a false rejection in I_FULL and in I_NATIVE;
- a downstream-regenerated stamp → INVALID;
- a request that is late, premature or absent;
- an unexpected stop in the fresh case;
- missing guarded receipt, clock and unexplained-reconnect gaps → INVALID/UNKNOWN;
- BLOCKED and NOT_RUN cells.

The empty schedule returns 630 NOT_RUN. The D4Q1/D4Q2 runtime manifests still verify.

## Before the first trial

`freeze_inputs.sha256` records the hashes. The freeze must be committed and pushed, and SHA alignment verified, before the first formal trial. A post-freeze analyzer defect gets a separately labelled supplementary analysis and never a rewrite. S5 remains INSUFFICIENT_EVIDENCE.
