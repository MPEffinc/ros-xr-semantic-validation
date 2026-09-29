# XRROS-S4B-CMONQ2-1.0.0 result — setup BLOCKED again at ORACLE_ABSENT readiness (no policy score)

Root: `runs/s4b_cp28_cmonq2_20260928T174422Z/` (frozen at 55994ce). Cells were run sequentially with no concurrent load.

| Cell | Result |
| --- | --- |
| B0, no fault | MEASUREMENT_QUALIFIED (excursion 0.2847 rad) |
| Shim, no fault | MEASUREMENT_QUALIFIED (0.2840 rad) |
| B0/shim pair | PASS: 0.042 ms source timing difference, 0.0007 rad final joint difference |
| B2-native, I_FULL, ORACLE_ABSENT | BLOCKED_MEASUREMENT: no start barrier in the original attempt or in either setup retry |
| Cells 4–12 | NOT_RUN |

**Root cause (from an offline check of the retained raw data):**

- **Checks that now pass:** the Q2 fix works. The ACK is `CMON_OFFICIAL_PATH_WITH_ORACLE_ABSENT`, the boundary chain is ordered, a forwarded `unknown` event exists, and the graph, controllers and receiver release are all ready.
- **Remaining blocker:** the probe's participant-clock list still required `participant_clock_oracle.json` for every B2 trial. No oracle process exists under ORACLE_ABSENT, so that clock record can never be written. This is a second setup defect that occurs before the barrier, and no policy outcome was observed.

**Additional pre-execution finding** (from code review; no C-MON DISCONNECT trial has run yet):

- The frozen resource-capture check requires every expected label to be OBSERVED in every capture sample.
- Under ORACLE_DISCONNECT, the injected SIGKILL makes the oracle MISSING after the fault, so the check would invalidate the trial because of a record the fault itself removes. The brief forbids that.

**Remedy:** XRROS-S4B-CMONQ3-1.0.0, which carries both corrections. The Q2 raw data and this result are retained unchanged.
