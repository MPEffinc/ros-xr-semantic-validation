# S4-B CP9 prospective D2 logging repair: preflight and freeze

Status at this freeze: **HOST PREFLIGHT PASS; CP9 GAZEBO QUALIFICATION NOT_STARTED**. This is XRROS-S4B-D2Q3-1.0.0, separate from CP8's two `BLOCKED_MEASUREMENT` B2 first attempts. CP8's B0/shim/B1/B3 evidence is retained but not automatically transferred to this integration configuration. Original D1 remains 50 executed/48 valid/two INVALID_COMPARISON. The unchanged research protocol is XRROS-S4-1.0.0, SHA-256 `3a40337121f8d687dc68036ff2ffc85a1bc6eda275a700ba7d9e8119cd322969`.

## Defect and controlled change

Both CP8 B2-native regimes reached official monitor `started` and the new DDS-match branch, then failed before barrier/sender because `trace.log()` added `monotonic_ns` while `d1_nodes.py` unpacked another `monotonic_ns`. CP9 uses `dds_match_monotonic_ns` for the measured match instant and a pure observation helper that logs the event and persists the match marker only after successful logging. The exact helper was exercised with a logger reproducing the collision, and AST inspection confirmed the production branch passes a non-reserved key. No original vendor source, official ROSMonitoring source, oracle property, DDS topic/QoS, defense predicate or D2 fixture changed. The CP8 and CP9 code difference is in `runs/s4b_cp9_d2q3_20260927T020700Z/analysis/source_diff_from_cp8.patch`.

## Actual preflight

All commands and outputs are in `runs/s4b_cp9_d2q3_20260927T020700Z/{commands.txt,preflight/}`. Direct DDS-match helper: 3/3 PASS, including rejection of the old duplicate-key shape. Mapper cache-parent A–H: 8/8 PASS. Analyzer positive/negative fixtures: 4/4 PASS. D2 sender/property socket-pair and static Python AST: PASS. CP8 failed B2 raw remains `BLOCKED_MEASUREMENT` under the new monitor-call audit; CP8 corrected B3 native parentage is a PASS positive control. The official ROSMonitoring/TLOracle no-Gazebo native/full neutral 20/20 component tests from CP8 are reused unchanged; they do not prove original-receiver/Gazebo delivery.

The new [prospective procedure](S4B_CP9_D2_QUALIFICATION_PROTOCOL.md) has SHA-256 `0ab41779bf3ea02c7ed8d1be688f381a3e1c50186a460b17135d13103ca99765`. The ten setup trial IDs, one initial plus two setup-only retries per cell, code, analyzer, read-only source revisions, input and schedule are fixed in this root and `freeze_inputs.sha256`, committed/pushed before first CP9 Gazebo run. `campaign_ledger.json` records CP8 as immutable and CP9's prediction. Resolve the carrying freeze commit from `git log -1 --format=%H -- semantic_validation/results/S4B_CP9_D2_PREFLIGHT_FREEZE.md` after push rather than self-hashing.

## Next exact gate

Run the frozen B0 and observational shim D2 cells first, confirm the original 5 ms/0.02 rad pair bounds and full graph/clock/recorder ACK. Then execute B1, genuine B2-native/composed and B3 in both information regimes sequentially using `qualification_schedule.csv`. For B2, confirm every original-neutral publish attempt has a DDS-call return, official property/verdict and downstream receipt or an explicitly explained block; a process marker alone is not delivery. If all ten setup cells pass, separately freeze the five-repeat formal D2 configuration before formal trials. No setup result scores defense efficacy, and source-to-specific-joint parentage remains UNKNOWN.
