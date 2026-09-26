# CP7-C Docker D2 qualification: partial, no formal comparison

Date: 2026-09-27. Frozen research policy: XRROS-S4-1.0.0, SHA-256 `3a40337121f8d687dc68036ff2ffc85a1bc6eda275a700ba7d9e8119cd322969`. Prospective setup protocol: XRROS-S4B-D2Q-1.0.0, SHA-256 `20f1ee4ad71443df1abb4b2b72c85249576714f496dd7771f5f64cb706a7e101`. Pre-runtime freeze commit: `9d2e4f6b1267af29d7d9f3fe611108163bcc25b8`. Neither protocol, frozen input, analyzer, vendor checkout nor earlier raw evidence was changed after the freeze.

## Scope and evidence boundary

This was **qualification**, not a B0–B3 formal comparison or defense efficacy estimate. The synthetic D2 source plan has 120 indices at 20 Hz; indices 56–75 change only `isTracked` to false while pose and teleop remain comparable. The path is the original Docker_Teleop receiver/mapper/bridge, MoveIt Servo, Gazebo-only controller and `/joint_states`; the non-vendor observation/defense wrappers and genuine official ROSMonitoring are separate. No Quest, physical robot or driver was used. The Q4 normal-path components and CP7-B host preflight were reused, not promoted to D2 proof.

Result root: `runs/s4b_cp7c_d2_qualification_20260926T185100Z/`. Its `freeze_inputs.sha256` has 40 entries and SHA-256 `08bf95724317921fe565266a9016d8fae23392ff6380135c120520d6b51566e4`. `qualification_schedule.csv` preregistered ten first setup cells, at most two setup-only retries per cell, with no functional-result retry. `commands.jsonl` has the exact container invocations; `raw/<trial>/` contains sent input, process stdout/stderr, lineages, Servo callback, controller/joint recordings, clock, barrier and resource logs. `analysis/d2_qualification_summary.json` is the **frozen** setup analyzer output; post-freeze diagnostics are separately named `analysis/postfreeze_*.py` and `analysis/postfreeze_*.json`. `runtime_evidence_manifest.sha256` hashes 624 result files, re-verified with `sha256sum -c` (exit 0); manifest SHA-256 `018c3f2af3d40c6b8a5e51b04cdbc1f789da1a75adb3f1ed95ff47ce22bcd403`. No formal schedule was frozen or run.

The vendor checkout remains `Noah727/Docker_Teleop@64cbdde88bc52c6a80d37f994752e50f95ba537e`; the official ROSMonitoring checkout is `autonomy-and-verification-uol/ROSMonitoring@d03aa5b44e29b76c0e108a098817bdf5aa98e322` (3.0.0). Trial-owned `s4cp7d2_*` containers used ROS domain 181, network none and the Gazebo-only launch. The frozen sender and launcher source files are `inputs/d1_sender.py` and `inputs/run_owned.py`; their exact hashes are in `freeze_inputs.sha256`. No laboratory container, network, Docker socket permission or vendor source was modified.

## Executed setup cells

All **nine executed first attempts** exited 0 and had 120 planned/sent source indices, whole-graph start ACK, controller output, actual pre-fault Gazebo motion, clock/resource capture and joint-state recording. The qualification table does not equate source send, original consumer, Servo callback and Gazebo joint effect. `MEASUREMENT_QUALIFIED` below is the frozen setup analyzer label, **not** a policy PASS.

| Cell | Frozen setup label | Pre-fault max joint speed (rad/s) | Fault-to-settle (ms) | Exact Servo callback joins | Additional limitation |
| --- | --- | ---: | ---: | ---: | --- |
| B0 full | MEASUREMENT_QUALIFIED | 0.196721 | 41.636 | N/A (unmodified B0) | interval outcome only |
| B0 observational shim | MEASUREMENT_QUALIFIED | 0.197211 | 56.909 | 372 | B0/shim pair PASS |
| B1 I_NATIVE | MEASUREMENT_QUALIFIED | 0.186063 | 30.834 | 324 | 13 nonzero callbacks from earlier accepted sample `docker:55` after detection |
| B1 I_FULL | MEASUREMENT_QUALIFIED | 0.195993 | 19.076 | 324 | same 13 cached-sample callbacks |
| B2-native I_NATIVE | BLOCKED_MEASUREMENT | 0.204256 | 297.316 | 372 | 1 unmatched pre-barrier original monitor-input publication |
| B2-native I_FULL | MEASUREMENT_QUALIFIED | 0.192373 | 279.650 | 372 | exact monitor-event association complete in this setup |
| B2-composed I_NATIVE | BLOCKED_MEASUREMENT | 0.198440 | 46.075 | 372 | 58 unmatched pre-barrier original monitor-input publications |
| B2-composed I_FULL | BLOCKED_MEASUREMENT | 0.198932 | 31.965 | 372 | 1 unmatched pre-barrier original monitor-input publication |
| B3 I_NATIVE | **INVALID_COMPARISON after post-freeze audit** | 0.219182 | 36.551 | 372 payload joins, but source parent invalid at reject | 14 nonzero callbacks falsely labelled as rejected source samples by the observer |
| B3 I_FULL | NOT_RUN / BLOCKED_INSTRUMENTATION | — | — | — | known structural B3 lineage defect before starting this scheduled cell |

B0/shim normalized fixture, time namespace and source schedule match; maximum index timing difference was 0.048022 ms (<5 ms), maximum final joint difference 0.001528 rad (<0.02 rad). This pair result does not qualify B3 lineage. Stop-adapter request/reply/zero entries are present in B1, B2-composed and B3 setups; B2-native has no composed health interlock. The reported settling is interval-level Gazebo evidence, not an exact per-source-to-joint causal join. Earlier cached nonzero callbacks must not be counted as new false-source commands.

## Post-freeze audit of B3 parent attribution

The frozen analyzer labelled B3 I_NATIVE `MEASUREMENT_QUALIFIED` and listed 14 nonzero callbacks under false sample IDs. The independent read-only `postfreeze_lineage_audit.py` found 20 rejected source IDs and 14 nonzero mapper publications after rejection that carry the *rejected* ID in the observation wrapper. At the first rejection (`docker:56`), the original mapper timer emitted `mapper:466` with `tracked=true`, nonzero linear x ≈0.09236, while the wrapper labelled its parent `docker:56` (`isTracked=false`). The last accepted source recorded by the wrapper was `docker:55`. The same pattern persists through labels `docker:60`. Exact actual command parent after a rejected callback is **UNKNOWN**; temporal proximity or the preceding accepted ID is not a substitute for an instrumented state read.

Static cause: in frozen `inputs/d1_nodes.py`, `Mapper._on_pose_states` assigns `self.selected = consume('mapper', msg)` *before* B3 validation and returns on reject. The original mapper `_on_pose_states` is consequently not called, but its independent `_publish_loop` timer can still emit from cached prior state. The wrapper's `Publisher(..., lambda: self.selected)` then binds that emitted command to the newly rejected sample. This is an **observation lineage defect**, not demonstrated B3 policy failure, and was not repaired or hidden after the freeze. The payload-level Servo callback join can be exact while its inherited **source-parent attribution is invalid**. B3 I_FULL would use the same frozen wrapper, so the remaining cell was not executed after this structural defect became known. A prospective observation correction would have to preserve accepted/last-applied source ID across rejects, log rejection separately, re-run B0/shim equivalence and all affected D2 setup gates under a separately frozen version. No such campaign is authorized or claimed here.

## Post-freeze audit of B2 monitor gaps

`postfreeze_monitor_gap_audit.py` independently compares original monitor-input publish logs with official property/status IDs or canonical payload hashes. B2-native I_NATIVE: 892 logged original publish attempts, 891 property and 891 status rows; 1 unmatched at **−4666.515 ms** relative to barrier. B2-composed I_NATIVE: 912, 854, 854 respectively; all 58 unmatched between **−4968.733 and −4033.402 ms**. B2-composed I_FULL: 905, 904, 904; one unmatched at **−4857.924 ms**. B2-native I_FULL: 874/874/874 with no unmatched IDs. Thus all D2 B2 gaps identified here precede input start and ACK release; no invalid source sample was identified as the unmatched event. The receiver wrapper logs *before* calling the DDS publisher, so a logged original publish attempt does not by itself prove monitor subscription receipt. The exact missing stage (publisher call, DDS delivery, subscriber callback or observer recording) remains UNKNOWN. Startup timing is a plausible but unproven cause. These are setup/measurement gaps, not established ROSMonitoring policy failures; the frozen all-event completeness criterion was not silently relaxed.

This D2 observation differs from CP7-A D1 r05's post-capture neutral gap; neither history is rewritten. No D1 supplemental campaign was justified or executed: original D1 remains 50 executed, 48 valid, 2 INVALID_COMPARISON, 45/45 B0-shim pairs PASS.

## Readiness, failed/unknown work and next action

- D2: **BLOCKED_INTEGRATION / INVALID_COMPARISON** for full B0–B3 formal comparison. Positive motion and B0/shim equivalence passed in setup, but three B2 information cells have all-event association gaps, B3 I_NATIVE has invalid exact parent attribution and B3 I_FULL was intentionally not run. No five-repeat formal schedule or policy outcome was scored. A later version requires a causally justified monitor-readiness/observation correction and B3 source-parent correction, preflight, freeze, B0/shim requalification and all mandatory case-specific checks; existing first attempts stay visible.
- D3: **BLOCKED_INTEGRATION**, no new runtime or formal trial. CP7-B fixed the no-byte stimulus but B2/B3 fair source-silence/tick detection and independent attribution from receiver/Servo timeout are not qualified. D2 movement does not qualify D3 moving-stall handling.
- OpenVR: no CP7 runtime; prior observer equivalence and jump-free re-arm blockers remain.
- S5: **INSUFFICIENT_EVIDENCE**. No invalid-state defense ranking or method-gap conclusion follows from these setup observations. B2-native versus B2-composed and I_NATIVE versus I_FULL must remain separate. Actual Quest state and physical robot outcome remain untested here.

No credential, key, cache/build artifact or >100 MB result file is included in this checkpoint. Raw result size is approximately 79 MiB across 566 files; largest file is under 6 MB. No experiment result was excluded for favorable selection. The frozen inputs and prior results remain append-only.
