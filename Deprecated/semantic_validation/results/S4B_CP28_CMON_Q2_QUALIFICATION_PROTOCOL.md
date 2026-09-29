# XRROS-S4B-CMONQ2-1.0.0 — prospective C-MON setup re-qualification (probe ORACLE_ABSENT readiness fix)

This protocol supersedes XRROS-S4B-CMONQ1-1.0.0 for setup purposes only; the Q1 raw data and result are retained, see `S4B_CP28_CMON_Q1_QUALIFICATION_RESULT.md`. Root: `runs/s4b_cp28_cmonq2_20260928T174422Z/`.

**Changes from Q1:**

- The only input change is in `inputs/d1_probe.py`, and it applies only when `CMON_FAULT=ORACLE_ABSENT`. There, the official path's positive evidence is a forwarded `unknown` event instead of a `currently_true` one. The oracle-decision element of the calibration boundary chain is replaced by the guarded receipt. The full diff is in `preflight/cmonq1_to_cmonq2_input_delta.txt`.
- The runner/container/attempt name changes from `cmonq1` to `cmonq2`.
- The analyzer, schedule cells, fault injector, official monitor/oracle, stop adapter and thresholds are all unchanged.

**Execution:**

- All 12 cells run freshly, including a fresh B0/shim pair.
- At most two retries are allowed, and only before the barrier.
- The gate is the same as in Q1: every cell must be MEASUREMENT_QUALIFIED and the B0/shim pair must PASS.
- The design report and the 60-trial formal proposal in `S4B_CP28_CMON_Q1_QUALIFICATION_PROTOCOL.md` are unchanged.
