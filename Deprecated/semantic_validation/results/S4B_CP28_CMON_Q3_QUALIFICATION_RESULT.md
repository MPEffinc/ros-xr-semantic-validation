# XRROS-S4B-CMONQ3-1.0.0 result — C-MON setup COMPLETE (no policy score)

Root: `runs/s4b_cp28_cmonq3_20260928T175202Z/` (frozen at dcd4202). All 12 cells ran sequentially with no concurrent load (5.5 min). No setup retries were needed. The audit is in `analysis/cmon_setup_summary.json`, status `CMON_SETUP_COMPLETE`.

| Cell | Status | Excursion (rad) |
| --- | --- | --- |
| B0 / shim, no fault | MEASUREMENT_QUALIFIED / MEASUREMENT_QUALIFIED | 0.283 / 0.281 |
| B2-native / B2-composed I_FULL ORACLE_ABSENT | QUALIFIED / QUALIFIED | 0.2855 / 0.0 (composed stopped at start) |
| B2-native / B2-composed I_FULL ORACLE_DISCONNECT | QUALIFIED / QUALIFIED | 0.2845 / 0.1843 |
| B2-native / B2-composed I_FULL ORACLE_NONRESPONSIVE | QUALIFIED / QUALIFIED | 0.424 / 0.1964 |
| B2-native / B2-composed I_NATIVE ORACLE_DISCONNECT | QUALIFIED / QUALIFIED | 0.2832 / 0.1876 |
| B1 / B3 I_FULL gate-process failure | QUALIFIED / QUALIFIED | 0.2194 / 0.2202 |
| B0/shim pair | PASS: 0.051 ms, 0.0019 rad | |

**Setup observations** (these informed the formal scorer design; they are not formal outcomes):

- **Official filter only (B2-native).** The official monitor forwarded every event after the fault as `unknown` (fail-open).
  - Under ORACLE_DISCONNECT, control continued until the source's own motion phase ended.
  - Under ORACLE_NONRESPONSIVE, each event waited for the 50 ms oracle timeout. This built a backlog: publish-to-receipt latency reached about 5.8 s, and about 150 source events were never delivered. Delayed commands kept moving the arm until the end of capture (excursion 0.424 rad).
- **Official filter plus stop adapter (B2-composed).** The adapter stopped on the first official `unknown` status: 4.5 ms after the kill (I_FULL), 10.2 ms after the kill (I_NATIVE), 61.8 ms after the SIGSTOP, and 6.9 ms after the start barrier when the oracle was absent.
- **Gate-process failures (B1/B3).** The common 250 ms verdict-heartbeat watchdog stopped control about 256 ms after the last verdict record.
