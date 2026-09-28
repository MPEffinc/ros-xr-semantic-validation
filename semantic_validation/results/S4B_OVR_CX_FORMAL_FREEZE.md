# XRROS-S4B-OVRCXF1-1.0.0 — prospective scoped OpenVR C-ID / C-MON formal freeze

This freeze applies XRROS-S4-1.0.0 (SHA-256 `3a40337121f8d687dc68036ff2ffc85a1bc6eda275a700ba7d9e8119cd322969`) without changing it.

- **Formal root:** `runs/s4b_ovr_cx_formal_20260928T223012Z/`.
- **Setup basis:** C-X Q1 (`S4B_OVR_CX_Q1_QUALIFICATION_RESULT.md`), plus the registered analyzer-only Q2 re-audit. Q2 qualified all 16/16 setup cells and the B0/shim pair PASSed (`analysis/cx_q2_reaudit_summary.json`).
- **Code mounted:** the runner mounts the frozen C-X Q1 inputs, the OpenVR Q1 monitor build, and the OpenVR Q1 dependencies.

## Schedule

The formal schedule has **100 trials**: 20 cells × 5 repetitions. Seed 20260922 shuffles the cell order within each repetition. The design is the one registered in `S4B_OVR_CX_Q1_QUALIFICATION_PROTOCOL.md`:

| Family | Cells |
| --- | --- |
| C-ID | {MISMATCH, DUPLICATE_ID} × {B0, shim, B1, B2-composed, B3, B2-ST-composed} |
| C-MON | B0, shim, B2-composed × {ABSENT, DISCONNECT, NONRESPONSIVE}, B2-native × DISCONNECT, B1 gate crash, B3 gate crash |

**Registered NOT_RUN:**
- C-ID MISSING_FIELD and MISSING_ID;
- C-ID B2-native;
- I_NATIVE;
- the native-regime C-MON cells.

**Estimated runtime:** about 80 minutes, run sequentially with no concurrent load.

## Scorer (`analysis/cx_formal_audit.py`)

The scorer passes 4/4 tests on the C-X Q1 setup raw. The empty schedule gives 100 NOT_RUN.

**Validity:**
- C-X Q2 `inspect()` for every trial;
- the B0/shim pair per repetition and family;
- each arm within 5 ms of the shim schedule.

**C-ID rules** (T = acquisition of poll 150):
- **P1:** pre-fault samples are admitted and delivered, and the joints at slot 149 are within 0.02 rad of the shim.
- **P2:** the injected sample is rejected for the registered reason within 50 ms. The neutralization request comes within 50 ms, with a stop reply and a hold. No Servo motion occurs after T+300 ms, and the arm settles by T+1 s.
- **P3:** the injected sample is not delivered.
- **P4:** polls 151–499 are not delivered, i.e. no held-grip restart.

**C-MON rules** (the Docker C-MON formal rule, with trigger T and allowance A):

| Fault | T | A |
| --- | --- | --- |
| ABSENT | barrier | 0 |
| DISCONNECT | proven kill | 0 |
| NONRESPONSIVE | proven stop | 50 ms |
| Gate crash | last verdict record | 250 ms |

- **M1:** no stop before T−1 ms, and the slot-149 joint path is within bounds.
- **M2:** the stop request comes by T+A+50 ms, with a stop reply and a hold. No Servo motion occurs after T+A+300 ms, and the arm settles by T+A+1 s.
- B2-native is scored under the same rule and is measured, not presumed.

**Boundary band:** a delay within ±1 ms of the limit is scored UNKNOWN_BOUNDARY_STRADDLE.

**Attribution classes:**
- DEFENSE_DECISION;
- OFFICIAL_MONITOR_NO_DECISION / LATENCY / LATE_DECISION_STALE_LATCH;
- OFFICIAL_MONITOR_STALL_TRIPPED_COMMON_WATCHDOG (the official Jazzy monitor stalled for more than 250 ms, so the common heartbeat stopped control before the registered trigger);
- B2_NATIVE_HAS_NO_STOP_INTEGRATION / B2_NATIVE_FAIL_OPEN_CONTINUED;
- COMMON_STOP_ADAPTER.

**Q1 fixture behavior (setup evidence only):**
- **C-ID:** B1, B3 and B2-ST reject both kinds within 0.1–1.2 ms, request the stop within 4–5 ms, and PASS.
- **C-MON:** B2-composed ABSENT PASSes, stopping on B2_MONITOR_HEALTH at 24 ms. The B1 and B3 gate crashes PASS through the watchdog. B2-native fails open. Official B2-composed DISCONNECT/NONRESPONSIVE were pre-stopped by the watchdog because of monitor stalls.

## Execution

- A setup is retried only when no barrier was reached, at most twice per cell.
- A run stops after two consecutive nonzero exits after the barrier.
- The setup raw data are excluded from the formal results.
