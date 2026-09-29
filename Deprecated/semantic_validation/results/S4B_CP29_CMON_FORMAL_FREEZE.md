# XRROS-S4B-CMONF1-1.0.0 — prospective scoped Docker C-MON formal freeze

This freeze applies XRROS-S4-1.0.0 C-MON (research protocol SHA-256 `3a40337121f8d687dc68036ff2ffc85a1bc6eda275a700ba7d9e8119cd322969`) without changing it.

- **Formal root:** `runs/s4b_cmon_formal_20260928T180115Z/`.
- **Setup basis:** C-MON Q3 (`S4B_CP28_CMON_Q3_QUALIFICATION_RESULT.md`). The formal runner mounts the frozen Q3 `inputs/` and `analysis/` read-only as `/code` and `/analysis`, so the formal trials run exactly the qualified code.

## Schedule (minimum-sufficient design, unchanged from the Q1 design report)

`schedule.csv` has 60 trials: 5 repetitions × 12 cells, with seed 20260922 used to shuffle cell order within each repetition. The 12 cells are:

- B0 and shim, no fault;
- B2-native and B2-composed I_FULL × ORACLE_ABSENT, ORACLE_DISCONNECT, ORACLE_NONRESPONSIVE;
- B2-native and B2-composed I_NATIVE × ORACLE_DISCONNECT;
- B1 and B3 I_FULL gate-process failure.

The valid bound source continues throughout every trial (120 slots at 20 Hz). Faults are injected at slot 45 while the arm is moving.

**Registered NOT_RUN (scoped):**

- I_NATIVE × {ORACLE_ABSENT, ORACLE_NONRESPONSIVE} for B2-native and B2-composed. The health path (official status plus adapter) is the same code in both regimes, and DISCONNECT is tested in both.
- I_NATIVE B1/B3 gate failure. The crash model and the watchdog are regime-independent.

**Expected runtime:** about 30 min, run sequentially with no concurrent CPU load.

## Scorer (`analysis/cmon_formal_audit.py`)

- **Validity** uses the frozen Q3 `inspect()`, the per-repetition B0/shim pair (5 ms, 0.02 rad), and a check that every arm uses the same normalized fixture as the shim with source offsets ≤ 5 ms.
- **Local trigger T and detection allowance A:**
  - ORACLE_ABSENT: T = start barrier, A = 0.
  - ORACLE_DISCONNECT: T = proven SIGKILL time, A = 0.
  - ORACLE_NONRESPONSIVE: T = proven SIGSTOP time, A = 50 ms (the official oracle timeout).
  - B1/B3 gate failure: T = the gate's last verdict record, A = 250 ms (the common heartbeat budget). A verdict record after the injected failure invalidates the trial.
- **M1:** no neutralization request before T − 1 ms. For faults injected during motion, the slot-44 joint vector must be within 0.02 rad of the shim's.
- **M2:**
  - neutralization request ≤ T + A + 50 ms;
  - stop reply and controller zero;
  - no nonzero controller output after T + A + 300 ms;
  - Gazebo settled by T + A + 1 s.
  - A request within ±1 ms of the bound, with no other violation, is UNKNOWN_BOUNDARY_STRADDLE.
- **B2-native** is scored under the same rule. Its fail-open or fail-closed behavior is measured, not presumed.
- **Attribution is recorded separately for each trial:**
  - official ROSMonitoring status and oracle_error counts;
  - forwarded or undelivered source events after T, and publish-to-receipt latency;
  - B2-composed monitor-health stop through the common stop adapter;
  - the common verdict-heartbeat watchdog (not ROSMonitoring);
  - unrequested halts from the original receiver, mapper or Servo timeouts.

## Preflight

- **Scorer tests, 5/5 pass** (`analysis/test_cmon_formal_audit.py`). They use the retained Q3 setup raw as a fixture: all 12 cells valid; composed and gate arms PASS with the correct attribution; native arms FAIL with measured fail-open forwarding. They also include synthetic boundary-band and premature-stop checks.
- **Empty-schedule audit:** 60 NOT_RUN, recorded in `preflight/empty_schedule.stdout`.

## Execution rules

- At most two setup-only retries per cell, and only when no barrier was reached. A trial that reached the barrier is final.
- Execution stops after two consecutive post-barrier nonzero exits.
- Q1, Q2 and Q3 setup raw data are excluded from the formal results.
