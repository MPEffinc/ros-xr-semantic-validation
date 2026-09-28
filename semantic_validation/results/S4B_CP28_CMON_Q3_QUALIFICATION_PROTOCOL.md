# XRROS-S4B-CMONQ3-1.0.0 — prospective C-MON setup re-qualification (oracle-absent participant list; killed-oracle resource exemption)

This protocol supersedes CMONQ2 for setup purposes only. The Q1/Q2 raw data and results are retained. Root: `runs/s4b_cp28_cmonq3_20260928T175202Z/`.

## Changes from Q2 (the diffs are in `preflight/`)

1. **Probe participant clocks.** `inputs/d1_probe.py` no longer requires an `oracle` participant clock, but only when `CMON_FAULT=ORACLE_ABSENT`. The monitor clock is still required.
2. **Oracle disconnect resource check.** `analysis/cmon_setup_audit.py` gets a new rule that applies only to ORACLE_DISCONNECT. When the frozen resource check reports an incomplete capture, it is recomputed as follows:
   - every expected label must be OBSERVED in every capture sample;
   - the one exception is the oracle strictly after the proven injection time;
   - the oracle must be OBSERVED in every capture sample before the injection.

   Any other missing label still makes the capture incomplete.

   This rule is tested on the host in `analysis/test_cmon_resources.py`, 3/3 pass: exemption applies; the oracle missing before the kill stays incomplete; another label missing stays incomplete.
3. **Names.** The runner, container and attempt names change to `cmonq3`.

Everything else is unchanged, including the schedule cells, fault injector, official monitor/oracle, stop adapter and the gate. All 12 cells are rerun freshly, including a fresh B0/shim pair, with at most two retries and only before the barrier. The design report and the 60-trial formal proposal remain those in `S4B_CP28_CMON_Q1_QUALIFICATION_PROTOCOL.md`.
