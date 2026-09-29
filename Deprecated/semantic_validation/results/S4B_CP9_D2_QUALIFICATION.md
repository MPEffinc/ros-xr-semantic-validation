# S4-B CP9 Docker D2 integrated setup qualification

**Status: D2_SETUP_COMPLETE, formal D2 NOT_STARTED.** Frozen prospective XRROS-S4B-D2Q3-1.0.0 configuration was pushed at `b06308ef1a453256cbb1a71f2c3341b3b325af6a` before Gazebo. The research protocol XRROS-S4-1.0.0 and its SHA-256 `3a40337121f8d687dc68036ff2ffc85a1bc6eda275a700ba7d9e8119cd322969` were unchanged. CP7/CP8 outcomes and original D1 48/50 valid remain separate.

## Setup incident retained

The first B0 invocation exited before trial creation because the new result root lacked an empty `raw/` directory (`preflight/setup_attempt01_failure.md`). No Gazebo/container/source bytes were created. Creating that directory did not alter frozen code, fixture or schedule; the same registered B0 ID was then used. This is a setup failure, not policy evidence. No functional trial was discarded or rerun for a favorable verdict.

## Registered first-attempt results

The frozen `analysis/cp9_qualification_audit.py` reports `D2_SETUP_COMPLETE` for all ten scheduled cells (`analysis/cp9_qualification_summary.json`): B0 original, B0 observational shim, B1, B2-native, B2-composed and B3 under the registered I_NATIVE/I_FULL regimes. All ten have 120 planned source indices, moving pre-fault D2 onset at `docker:56`, full graph/recorder/controller/clock ACK, complete resource capture, Servo/controller records and Gazebo joint-state interval evidence. A setup PASS **does not score D2 defense-policy success**. The setup output explicitly says `policy_verdict=NOT_SCORED_BY_SETUP_AUDIT` and `formal_trials=NOT_STARTED`.

B0/shim equivalence passed on the new integration configuration: same fixture/clock namespace, maximum source-index offset difference **0.056417 ms** (limit 5 ms), maximum final per-joint difference **0.003672 rad** (limit 0.02 rad). Exact Servo callback joins were 372/372 in the shim; original B0 has no shim instrumentation. B1 had 324 exact callback joins in each information regime. B2-native and B2-composed had 372 exact callback joins per cell. Their original monitor-input `publish()` attempts and returns were respectively **882/882**, **914/914**, **826/826**, **844/844**; the frozen audit found no unexplained official property/status/output association issue, including generated original-neutrals. B2-native I_NATIVE had 882 official property/status records and 822 guarded output receipts; the difference includes filtered invalid inputs and is not labelled missing delivery. Official internal post-verdict publish time is still UNKNOWN.

B3 I_NATIVE and I_FULL each recorded the 20 rejected D2 source IDs `docker:56`–`docker:75`, 372 exact Servo callback joins and 14 post-reject nonzero mapper timer commands correctly parented to the previously original-callback-applied `docker:55`. These represent outstanding cached control, not a new command from a rejected source. Stop request/reply, last post-trigger nonzero controller output and Gazebo settling remain separate records. For illustration only, the single setup B2-native I_NATIVE interval settled 294.216 ms after fault, whereas B2-composed I_NATIVE settled 33.805 ms; **neither is a formal five-repeat efficacy estimate** and the common stop adapter must not be credited to ROSMonitoring itself.

## Evidence boundary and next gate

This is synthetic input through the original Docker receiver→mapper→bridge→MoveIt Servo→Gazebo path; it is not actual Quest tracking loss or physical robot actuation. Source→original callback→Servo callback association is exact where the trace records unique IDs; specific Servo output, controller output or joint sample parentage is not inferred from time proximity. Gazebo movement/settling are interval-level consequences. The genuine ROSMonitoring 3.0.0 filter/oracle was in the B2 decision path; B2-native and B2-composed are kept distinct.

The next authorized gate is a **separate prospective formal freeze** of five-repeat D2 trial IDs, random seed/schedule, identical fixture and initial state, unchanged policy thresholds, complete failure retention, and formal analyzer. Do not promote these setup records to formal comparison. Then execute every registered B0–B3 cell, including potential policy failures and invalid comparisons, without selection. D3 and other cases remain independently unqualified. No S5 method-gap decision follows from this qualification alone.

## Files and integrity

- Root: `runs/s4b_cp9_d2q3_20260927T020700Z/`.
- Frozen code/config/input/preflight: `freeze_inputs.sha256` (verify from repository root); trial commands: `qualification_schedule.csv`, `commands.jsonl`.
- All ten trial raw roots: `raw/docker_*_cp9d2setup01/`, each with stdout/stderr, lineage, official monitor property/status when applicable, Servo callback, controller/joint, resource, clock and exit records.
- Frozen setup verdict: `analysis/cp9_qualification_summary.json`; post-runtime SHA-256: `runtime_evidence_manifest.sha256` (verify from repository root).
- No credential or >100 MB individual file was found, and no CP9 raw was excluded from the result commit.
