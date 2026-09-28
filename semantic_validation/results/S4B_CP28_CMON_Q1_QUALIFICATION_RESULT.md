# XRROS-S4B-CMONQ1-1.0.0 result — setup BLOCKED at ORACLE_ABSENT readiness (no policy score)

Root: `runs/s4b_cp28_cmonq1_20260928T173018Z/` (frozen at 93049d1). The runner executed the frozen schedule sequentially with no concurrent load. After cell 3's retries were exhausted, it stopped, so cells 4–12 are NOT_RUN. The audit is in `analysis/cmon_setup_summary.json`.

| Cell | Result |
| --- | --- |
| B0, I_FULL, no fault | MEASUREMENT_QUALIFIED (excursion 0.2856 rad) |
| Shim, I_FULL, no fault | MEASUREMENT_QUALIFIED (0.2841 rad) |
| B0/shim pair | PASS: 0.051 ms source timing difference, 0.0014 rad final joint difference |
| B2-native, I_FULL, ORACLE_ABSENT | BLOCKED_MEASUREMENT: no start barrier in the original attempt or in `_setup02`/`_setup03` (probe exit 12, `readiness_failed`) |
| Cells 4–12 | NOT_RUN |

**Root cause (from the retained raw data):**

- **What worked:** the ORACLE_ABSENT source-path ACK succeeded (`CMON_OFFICIAL_PATH_WITH_ORACLE_ABSENT`: property 0, status 1 `unknown`/forwarded, receipt 1). The official monitor forwarded all 3050 events as `unknown`/`forwarded`. This is the fail-open behavior, observed now in the integrated Docker path as well.
- **What blocked readiness:** the probe's B2 readiness step was not adapted to ORACLE_ABSENT. It still required at least one `currently_true` official event and an oracle-decision timestamp in the calibration boundary chain, and neither can exist when there is no oracle. This is a setup defect that occurs before the barrier. No policy outcome was observed or used.

**Remedy:** a separately versioned setup, XRROS-S4B-CMONQ2-1.0.0, with a probe-only fix. Q1 raw data and this result are kept unchanged.
