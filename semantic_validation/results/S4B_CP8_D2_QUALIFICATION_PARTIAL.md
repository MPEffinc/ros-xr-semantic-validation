# S4-B CP8 Docker D2 qualification: partial, original B2 setup failure retained

This is **qualification, not formal B0–B3 comparison**. The CP8 freeze was pushed as `cd6f67950d956fc734f4f2cfb3c43f217ab6d1ab` before any CP8 Gazebo trial. Research policy XRROS-S4-1.0.0 remains SHA-256 `3a40337121f8d687dc68036ff2ffc85a1bc6eda275a700ba7d9e8119cd322969`; CP8 prospective procedure XRROS-S4B-D2Q2-1.0.0 remains SHA-256 `5bc34f2113b2d5bb734ab09d8fb422503067dc714a41e540fc89182e27f25ab6`. CP7-C's nine attempts and D1's original 48/50 valid result are not reclassified.

## Frozen first attempts actually executed

The scheduled trial commands and exit codes are in `runs/s4b_cp8_d2q2_20260927T013600Z/commands.jsonl` and `raw/<trial>/exit.json`. The frozen analyzer produced `analysis/cp8_qualification_summary.json`:

| Cell | Setup verdict | Evidence boundary |
| --- | --- | --- |
| B0 original, I_FULL | MEASUREMENT_QUALIFIED | 120-index D2 input, full start ACK, moving before fault, Servo/controller and Gazebo interval records; no per-source joint parent claimed |
| B0 observational shim, I_FULL | MEASUREMENT_QUALIFIED | 372 exact Servo callback joins; pair with B0 PASS: max source-index offset difference 0.045237 ms, max final-joint difference 0.001233 rad, same fixture and clock namespace |
| B1 I_NATIVE, I_FULL | MEASUREMENT_QUALIFIED (both) | 324 exact Servo callback joins per cell, actual motion before fault, complete resource capture; policy outcome not scored by setup analyzer |
| B2-native I_NATIVE, I_FULL | BLOCKED_MEASUREMENT (both) | `launch_exit=12`, no barrier/source trial; official monitor started, but observed process raised `TypeError: dict() got multiple values for keyword argument 'monotonic_ns'` at `d1_nodes.py:214` when logging pre-spin DDS match. This is an integration/observation implementation error, **not** a ROSMonitoring policy failure. |
| B2-composed I_NATIVE, I_FULL | NOT_RUN | Do not spend a frozen CP8 attempt on the same already localized crash. |
| B3 I_NATIVE, I_FULL | MEASUREMENT_QUALIFIED (both) | 20 `docker:56`–`docker:75` rejects per cell. Fourteen post-reject nonzero mapper timer publications per cell are now exactly parented to previously callback-applied `docker:55`, not the rejected samples. 372 exact Servo callback joins per cell. This is correct observation of outstanding cached control, not evidence that a rejected source generated a new command. |

The B0/shim equivalence and B3 correction are real CP8 results, but they do not compensate for B2's missing graph/barrier. The B3-native moving-before-fault joint excursion was 0.230221 rad and its interval settled 41.774 ms after fault; its generic stop request/reply and controller zero are separately recorded. These are synthetic Docker/Gazebo observations only. Source rejection, cached commands, stop actuation and Gazebo settling must not be conflated. No formal D2 verdict or cross-stack method-gap conclusion is available.

## Causal localization and next version

In both failed B2 first attempts, `monitor_<regime>_status.jsonl` contains official `started`, and the observed process reached the newly added DDS-match logging branch. `trace.log()` already inserts `monotonic_ns`; CP8 also unpacked a `match` dictionary containing that key, causing the deterministic duplicate-key exception before `monitor_dds_match.ready`, executor spin, original neutral generation, recorder ACK or sender start. The new pre-Gazebo component test did not execute this wrapper branch. The exact CP7 B2 prebarrier gap cause remains UNKNOWN; these CP8 failures give no evidence about it.

Do not alter CP8 frozen files or claim an unused setup retry succeeded. A subsequent prospective implementation must remove only the duplicate timestamp argument (or use a distinct `dds_match_monotonic_ns` field), add a regression that invokes the actual logging branch, freeze new code/analyzer/schedule **before** any further B2 Gazebo run, and requalify B0/shim because this remains the prospective startup integration configuration. The B2-native/composed path must then prove full original-publish→official property/status→downstream receipt association, including neutrals. If the new branch still fails, localize the next boundary using retained raw rather than repeating an unchanged setup.

## Evidence and preservation

- Root: `runs/s4b_cp8_d2q2_20260927T013600Z/`.
- Frozen code/config/fixture/preflight: `freeze_inputs.sha256` (verify from repository root); original source diff `analysis/source_diff_from_cp7.patch`.
- All eight executed first-attempt raw roots, including both failed B2 cells: `raw/docker_{b0,shim,b1,b2,b3}_*cp8d2setup01/`; no CP8 raw was overwritten.
- Actual trial command argv: `commands.jsonl`; all stdout/stderr and participant clock/controller/Servo/Gazebo records remain in each raw trial root.
- Frozen analyzer output: `analysis/cp8_qualification_summary.json`; runtime SHA-256 list: `runtime_evidence_manifest.sha256` (verify from repository root). No file exceeded GitHub's 100 MB single-file limit; no raw was intentionally excluded.
