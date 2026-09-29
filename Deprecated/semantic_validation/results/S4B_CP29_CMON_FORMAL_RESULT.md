# XRROS-S4B-CMONF1-1.0.0 result — scoped Docker C-MON monitor/oracle-failure comparison

This is the primary result, scored by the analyzer frozen at e86d364 without modification.

- **Roots:** `runs/s4b_cmon_formal_20260928T180115Z/` (formal), `analysis/formal_summary.json` (scored summary).
- **Execution:** 60 trials, run sequentially with no concurrent load, starting 2026-09-28T18:05:01Z. No setup retry was needed.
- **Validity:** 60/60 `VALID_FORMAL_TRIAL`, 0 invalid, 0 blocked.
- **Controls:** the B0/shim pair passed in all 5 repetitions (≤ 0.055 ms, ≤ 0.0033 rad). All 50 arm-versus-shim schedule checks were `PASS_SCHEDULE` (≤ 0.29 ms). Slot-44 joint vectors were within 0.011 rad.
- **Scope:** the 30 registered cells listed in the freeze are NOT_RUN. This is a scoped study.
- **Freeze check:** `freeze_inputs.sha256` still verifies after the run.

In every trial the valid bound source continued through the fault (120/120 received). The fault was injected at slot 45 while the arm was moving; under ORACLE_ABSENT it was present from the start.

## Policy outcome (5 repetitions each)

| Arm / regime / fault | Result | Neutralization request after T (ms) | Detection and stop attribution |
| --- | --- | --- | --- |
| B2-native I_FULL ORACLE_ABSENT | FAIL 5/5 | none | Fail-open: 360 events forwarded `unknown`; control continued (last nonzero output 2.80–2.83 s after T) |
| B2-native I_FULL ORACLE_DISCONNECT | FAIL 5/5 | none | Fail-open: about 401 `oracle_error`; 219–220 source events forwarded `unknown`; control continued until the source's own motion ended (449–472 ms) |
| B2-native I_FULL ORACLE_NONRESPONSIVE | FAIL 5/5 | none | Fail-open with degradation: each event waited for the 50 ms oracle timeout; 69–70 events forwarded with up to 5.78–5.87 s publish-to-receipt delay; 149–151 source events never delivered; delayed commands moved the arm until the end of capture (0.424 rad excursion versus 0.284 for the shim); not settled by T + 1.05 s |
| B2-native I_NATIVE ORACLE_DISCONNECT | FAIL 5/5 | none | Same fail-open behavior as I_FULL |
| B2-composed I_FULL ORACLE_ABSENT | PASS 5/5 | 7.6–8.0 | Official `unknown` status → composed monitor-health stop (common stop adapter); no motion |
| B2-composed I_FULL ORACLE_DISCONNECT | PASS 5/5 | 8.5–13.6 | Same path; controller zero; settled within 43 ms |
| B2-composed I_FULL ORACLE_NONRESPONSIVE | PASS 5/5 | 53.5–64.8 (limit 100) | Same path, after the official 50 ms oracle timeout |
| B2-composed I_NATIVE ORACLE_DISCONNECT | PASS 5/5 | 7.4–12.7 | Same path |
| B1 I_FULL source-gate process failure | PASS 5/5 | 253.0–257.1 (limit 300) | Common 250 ms verdict-heartbeat watchdog, **not ROSMonitoring** |
| B3 I_FULL receiving-check failure | PASS 5/5 | 254.8–258.8 (limit 300) | Same common watchdog |

For every native failure, the scorer's attribution is `NO_HALT_CONTROL_CONTINUED_FAIL_OPEN`. No trial halted through an unrequested original receiver timeout, mapper reset or Servo timeout, because the valid source kept publishing.

## Interpretation (tested synthetic Docker conditions only)

- **Official ROSMonitoring on its own is fail-open.** This is now measured at runtime rather than inferred from static code. The official filter treats an absent, disconnected or non-responding oracle as `unknown` and forwards the event. With a non-responding oracle it adds a 50 ms wait per event, which becomes a multi-second backlog, dropped events and delayed actuation.
- **An ordinary fail-closed integration solves the tested failures.** The composed configuration pairs the official filter with a stop adapter that treats `unknown` as a stop request. The common verdict-heartbeat watchdog handles B1/B3 gate crashes.
- These are conventional integration elements. The first is the monitor-health handling the S4 protocol anticipates; the second is an ordinary interlock. Neither is a new framework.
- For C-MON this is consistent with **NO_METHOD_GAP**. The observed gap is a missing health/stop-integration gap in the native deployment, not a limitation of runtime verification as a method.

**Not supported by this result:**

- other fault times, crash loops, oracle restart or recovery;
- host-level or network failures;
- I_NATIVE ABSENT/NONRESPONSIVE and native gate cells (NOT_RUN);
- OpenVR;
- physical devices;
- any reliability guarantee (zero failures in five trials is limited evidence).
