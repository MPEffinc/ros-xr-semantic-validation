# S4-B CP5-B: Docker D1 Q3 runtime measurement qualification

Status: **PARTIAL / D1 formal comparison BLOCKED**. This is a prospective XRROS-S4B-Q3-1.0.0 qualification campaign, not formal B0–B3 defense comparison, an actual Quest experiment, or physical robot evidence. The research policy XRROS-S4-1.0.0 SHA-256 `3a40337121f8d687dc68036ff2ffc85a1bc6eda275a700ba7d9e8119cd322969` was not changed. Q3 SHA-256 is `af491bc111997851d6f179b29108a8f5c59e7450a101d068ca884c62e13460d8`. Q3 code/config/fixture/analyzers were frozen and pushed at `825d740da6cc553a849878830f7aab13c11423c5` **before** this campaign's first Gazebo run. `input_manifest.sha256` still verifies after all runs. Earlier CP3/Q2 raw, verdicts and retries remain separate.

Result root: `runs/s4b_cp5b_measurement_20260923T054101Z/` (`R`). Exact trial-owned Docker commands, environment and exits are in `R/commands.jsonl`, `environment.txt` and `R/raw/<trial>/environment.stdout`, `environment.stderr`, `exit.json`; `inputs/run_owned.py` and `inputs/launch.sh` are the frozen invocation source. `R/qualification_schedule.csv` has all 16 named cells. Trial stdout/stderr, 120-index source wires, lineage, official monitor/oracle verdicts, Servo callback payload, ROS topics (`/joint_group_velocity_controller/commands`, `/joint_states`), 100ms resource samples, start ACK and boot/time-namespace metadata are kept in each `R/raw/<trial>/`. Fixed analysis outputs are `R/analysis/*_measurement.json`, `*_stop.json`, `q3_normal_setup_metrics.json`, `q3_all_normal_pair_metrics.json`; SHA-256 manifest is `R/runtime_evidence_manifest.sha256`. No Quest/ADB/OpenVR, physical robot or robot driver ran. The original vendor checkout was untouched; active lab containers were not stopped or changed. New trial containers used `--network none`, ROS domain 181, no added capabilities.

## Ten normal-path setup attempts (first and only attempt per cell)

All ten had child launch exit 0, common start ACK, 120/120 consecutive source indices, unchanged normalized D1 fixture, active controller, source-derived control on the original path and measured Gazebo excursion >0.01 rad (range **0.282268–0.286039 rad** across the nine hook-equipped arms; B0 **0.284110 rad**). Exact source-parent→Servo callback joins were **372/372** for each of the nine instrumented shim/defense arms; B0 original has no source-ID callback shim and is assessed through the separately qualified B0/shim pair. The full Q3 resource analyzer's categories below are retained, not overridden by a favorable movement result.

| Arm / regime | Active source→Servo callback p95 ms | Resource capture | Exact B2 full envelope→oracle→downstream receipt |
| --- | ---: | --- | ---: |
| B0 original / full | UNKNOWN (unmodified B0) | COMPLETE | N/A |
| B0 observational shim / full | 63.028 | **UNKNOWN**: one ended sender snapshot | N/A |
| B1 / I_NATIVE | 56.871 | COMPLETE | N/A |
| B1 / I_FULL | 59.416 | **UNKNOWN**: one ended sender snapshot | N/A |
| B2-native / I_NATIVE | 77.806 | COMPLETE | native event-to-source oracle join UNKNOWN |
| B2-native / I_FULL | 64.671 | **UNKNOWN**: one ended sender snapshot | 870/870 |
| B2-composed / I_NATIVE | 55.735 | COMPLETE | native event-to-source oracle join UNKNOWN |
| B2-composed / I_FULL | 56.526 | COMPLETE | 956/956 |
| B3 / I_NATIVE | 60.280 | **UNKNOWN**: one ended sender snapshot | N/A |
| B3 / I_FULL | 56.022 | COMPLETE | N/A |

All four official-monitor normal setups had only `safe=true` property decisions and `forwarded` filter events: B2-native I_FULL 870/870, I_NATIVE 880/880; B2-composed I_FULL 956/956, I_NATIVE 875/875. These are normal-input setup positives, **not** evidence of invalid-state rejection. The full-envelope event ID and payload binding join the oracle observation to downstream `monitor_output_received`; the latter is downstream receipt, **not** exact generated-monitor internal forwarding time. For I_NATIVE the original wire lacks validated source age/generation and the official property log lacks a unique source ID, so per-source oracle event time remains UNKNOWN. `R/analysis/*_measurement.json` leaves specific source→Servo output/controller output/joint parent UNKNOWN; their interval-level output and motion are separate evidence. The p95 numbers include 20Hz source-to-repeated-command waiting and are **not** an added-gate p95 estimate or a formal practicality result.

The frozen CP2 pair audit on Q3 raw classed B0/shim **PASS**: same fixture/clock, maximum matched source-index schedule difference **0.056285 ms** (<5ms), maximum final per-joint difference **0.001510 rad** (<0.02rad), excursions 0.284110/0.285620 rad. All other normal arms vs B0 also met these setup pair gates: maximum source offset difference 0.050865–0.303770 ms and maximum final joint difference 0.000072–0.001929 rad. This is a one-run setup comparability check, not five formal repetitions. See `R/analysis/q3_all_normal_pair_metrics.json`.

The 100ms sampler did preserve process/descendant PID/start-tick identity, CPU ticks, RSS and missing status for each participant. However, **four normal runs** (shim/full, B1/full, B2-native/full, B3/native) have one `sender=MISSING` sample inside the barrier→capture interval. The sender had finished its 120th transmission near the 6-second capture end; the next sampler snapshot occurred after process exit. The frozen analyzer therefore returns `UNKNOWN_INCOMPLETE_CAPTURE` and `sender.cpu_percent=null`, not zero or an interpolated value. Repeating these cells until the exit/sample race happens to look complete would be outcome selection, not an allowed environment-only retry. This is an instrumentation/measurement closure failure, **not** a B1/B2/B3 policy failure or evidence of a defense-method gap. Other participant traces and the six complete normal resource captures remain useful bounded setup evidence, but the registered across-arm CPU/RSS comparison is incomplete. The frozen Q3 analyzer and code were not altered after observing it.

## Six distinct ordinary-stop diagnostics

An explicit `QUALIFICATION_STOP` at the common barrier+2.25s was sent to the **same generic** Docker stop adapter in B1, B2-composed and B3, each I_NATIVE/I_FULL. It is not a source validity/freshness/oracle verdict; B2-native behavior was not modified or scored as composed stop. Every run independently showed nonzero controller output and joint velocity during the preceding 100ms, a successful `/servo_node/stop_servo` reply, a controller zero command, no continuing nonzero output after 300ms and a measured 0.5s joint settled window by 1s. The separate stop criteria pass even though B2-composed/full also has one ended-sender resource sample. A `stop_servo` success reply alone was never used as halt proof.

| Diagnostic | Trigger→request ms | Last post-trigger nonzero controller ms | First settled-window end ms | Stop result |
| --- | ---: | ---: | ---: | --- |
| B1 I_NATIVE | 1.739 | 1.659 | 527.274 | PASS_STOP_SETUP |
| B1 I_FULL | 3.391 | none observed | 521.774 | PASS_STOP_SETUP |
| B2-composed I_NATIVE | 2.575 | none observed | 521.777 | PASS_STOP_SETUP |
| B2-composed I_FULL | 0.181 | none observed | 521.875 | PASS_STOP_SETUP; CPU capture still UNKNOWN |
| B3 I_NATIVE | 1.703 | 1.148 | 527.233 | PASS_STOP_SETUP |
| B3 I_FULL | 2.839 | none observed | 522.504 | PASS_STOP_SETUP |

The existing Q2/closure evidence about B2-native fail-open under oracle failure is unchanged. This Q3 campaign did **not** inject oracle failure, tracking invalidity, stale age, receipt stall, reconnect or re-arm. It demonstrates a general stop actuator when deliberately requested, not a policy's ability to detect or block those cases. It also does not establish individual source→Gazebo causality.

## Analysis error and validity decision

The copied `d1_qualification_audit.py` assumes `lineage.jsonl` exists and raises `FileNotFoundError` on **unmodified B0**, which deliberately has no shim lineage. The first error and reproduced stderr are retained in `R/stderr/b0_legacy_audit_attempt.log`. It is an analysis-selection error, not a trial child failure. No frozen code or raw was rewritten; B0's source schedule, controller output and joint excursion were assessed with the previously frozen CP2 pair audit, while `q3_measurement_audit.py` correctly records B0's exact callback lineage as unavailable.

All 16 scheduled Q3 cells ran once; no setup retries or additional qualification campaign were created. Q3 proves the new instrumentation can coexist with normal original control/Gazebo movement and the ordinary stop contract in these synthetic trials. It does **not** close the across-arm CPU/RSS requirement, nor exact native B2 oracle event↔source association. Therefore **Docker D1 formal B0–B3 comparison remains NOT_STARTED / BLOCKED_MEASUREMENT**; no formal schedule freeze, five repetitions, defense ranking or S5 decision is authorized from this evidence. Other Docker cases still require their own stale/delay/stall/recovery/event-level gates; OpenVR retains its separate observer-equivalence and jump-free re-arm blockers. No independent registered case is READY for formal four-baseline comparison on current evidence.

Next work requires a separately prospective, versioned measurement fix **only if approved as a new qualification campaign**: capture finite sender CPU at exit (or predeclare a lifetime denominator and bounded counter uncertainty), while preserving original source fixture/thresholds and including the existing Q3 failures. It must be preflighted and frozen before any new runtime. For B2 I_NATIVE event-level latency, either establish an exact nondefensive ID in the actual path under a fair information regime or leave it UNOBSERVABLE; timestamp proximity is not a substitute. Do not retroactively mark Q3 resource gaps PASS or weaken XRROS-S4-1.0.0. S6/S7 were not started.

Credential/private-key pattern scan found no candidate in new code/report; no Q3 raw single file exceeds 50 MB. The entire Q3 raw tree (approximately 137 MB on disk) and analysis are included in the checkpoint. Reproducible local-only `R/deps/` and `R/monitor_ws/install/` were excluded; exact per-file path/size/SHA-256 and their source wheels/generated code are recorded in `R/excluded_artifacts_sizes.tsv`, `R/excluded_artifacts.sha256` and `R/input_manifest.sha256`. No raw outcome was excluded.
