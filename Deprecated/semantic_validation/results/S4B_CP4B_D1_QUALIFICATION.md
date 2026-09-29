# S4-B CP4-B Docker D1 qualification

Date: 2026-09-23 UTC. Prospective setup campaign XRROS-S4B-Q2-1.0.0 (SHA-256 fa20addad4c6020cac1bb728ba90403813c95dcebaf2f14091363259ccdf2ead), started only after the code/configuration freeze commit 137d0f319e2ac27384e04850290a8c546b63c074 was pushed. Original XRROS-S4-1.0.0 SHA-256 3a40337121f8d687dc68036ff2ffc85a1bc6eda275a700ba7d9e8119cd322969 is unchanged. These are setup/normal-input qualification trials, not formal repetitions or defense-performance results. CP3 setup01/02/03 remain failed; CP3 setup02 motion is not a valid B2 I_FULL result, and setup03 was a sender failure rather than a ROSMonitoring policy failure.

## Execution and evidence

Result root: [runs/s4b_cp4b_preflight_20260923T044458Z/](runs/s4b_cp4b_preflight_20260923T044458Z/). The directory began as preflight/freeze; its later raw/ children are distinct post-freeze integrated attempts. Exact Docker run/inspect/exec/stop argv are in commands.jsonl; trial invocations are in commands.txt. Each fresh trial-owned Gazebo-only container used pinned Humble image sha256:a880da84ea9821f0e07adecca52f5882c3f6982509d157a8a73792624f6445f2, network-none, ROS domain 181, non-root UID 1000 and no capabilities. The original Docker_Teleop revision was 64cbdde88bc52c6a80d37f994752e50f95ba537e. Genuine ROSMonitoring 3.0.0 revision d03aa5b44e29b76c0e108a098817bdf5aa98e322 supplied B2 generated monitor and TLOracle. Every complete trial used fixture SHA-256 20dcbc12db4f54f3660f00662ed554c220a5de35ba1b2116d40e727ba83c918b. No physical robot/driver, Quest, vendor edit or prior evidence edit.

Raw per trial is under raw/<trial>/: sent.jsonl, events.jsonl, lineage.jsonl, topics.jsonl, Servo callback payload, monitor/oracle verdicts where applicable, participant clock records, process stdout/stderr, graph/initial-joint ACK and exit.json. The failed pre-container attempt has create.stderr and commands.jsonl. analysis/q2_trial_metrics.json uses the frozen d1_qualification_audit.audit function on every complete hook-equipped root; analysis/q2_pair_metrics.json uses the frozen CP2 pair audit against B0. analysis/d1_setup_metrics.json is an earlier single-trial output, not the final aggregate. The frozen all-glob script could not parse a pre-container failure without lineage; stdout/qualification_audit_01.log retains its partial output. The complete-root aggregate and failed-create classification are both retained, without deleting any raw. runtime_evidence_manifest.sha256 lists every committed runtime result hash.

## Attempt ledger and bounded normal-path result

All ten complete setup runs recorded ordered source indices 0-119, a done marker, exit 0, readiness ACK then barrier release, active controllers/Servo, post-barrier controller output and >0.01 rad six-arm-joint excursion. B0 is original production; shim is observation only. All other rows are normal-input positive controls, not fault-policy tests.

| Arm | Attempt | Source-parent Servo-input publications / unique callback joins | Post-barrier controller outputs | Maximum joint excursion (rad) |
| --- | --- | ---: | ---: | ---: |
| B0 original | docker_b0_full_q2b0setup01 | no callback hook in B0 | 360 | 0.285908 |
| B0 shim | docker_shim_full_q2shimsetup01 | 372 / 851 total joins | 361 | 0.285181 |
| B1 I_FULL | docker_b1_full_q2b1fsetup01 | 372 / 846; gate 120/120 allow | 360 | 0.284673 |
| B1 I_NATIVE | docker_b1_native_q2b1nsetup01 | 372 / 888; gate 120/120 allow | 361 | 0.282257 |
| B2-native I_FULL | docker_b2_full_q2setup01 | 372 / 873; 839 true oracle events | 360 | 0.286643 |
| B2-native I_NATIVE | docker_b2_native_q2b2nsetup01 | 372 / 877; 872 true oracle events | 361 | 0.280337 |
| B2-composed I_FULL | docker_b2c_full_q2csetup02 | 372 / 780; 894 true oracle events | 360 | 0.285712 |
| B2-composed I_NATIVE | docker_b2c_native_q2c2nsetup01 | 372 / 942; 942 true oracle events | 360 | 0.284947 |
| B3 I_FULL | docker_b3_full_q2b3fsetup01 | 371 / 849 | 360 | 0.280919 |
| B3 I_NATIVE | docker_b3_native_q2b3nsetup01 | 372 / 928 | 360 | 0.282379 |

The first callback-column number counts source-parent Servo-input publications; the second counts unique exact publisher-payload to Servo-callback joins, including neutral publications. All source-parent publications in hook-equipped runs have exact unique callback joins. B2-composed I_FULL also had 113 unmatched **pre-barrier original-neutral** publications; B2-composed I_NATIVE had one unmatched **post-barrier original-neutral** publication. Thus whole-run callback completeness is not established for these arms. A specific source sample to Servo internal output, controller output or Gazebo joint sample remains UNKNOWN; controller/joint findings are interval-level only. ROS publication, Servo callback, controller output and simulated joint movement are different evidence levels.

B0/shim matched setup pair PASS: same fixture/clock, maximum source-index schedule difference 0.052406 ms (<5 ms), maximum final-joint difference 0.000727 rad (<0.02 rad). Every other setup pair vs B0 also met these limits: maximum source-index difference 0.051798-0.077827 ms; maximum final-joint difference 0.000196-0.005571 rad. These single-run setup comparability checks are not five-repeat formal results. B2 I_FULL readiness ACK showed original receiver publishing only the _mon envelope, official generated guard consuming it and publishing guarded output, lossless stripper as sole /received_pose_states publisher, mapper/bridge to Servo DDS matches, active controllers, increasing joint stamps, initial error 0.0000273 rad, negligible drift, and positive oracle response before barrier. Every complete run logged participant boot ID/time namespace and recorder/graph ACK; shared clock identity is not a per-hop latency measure.

## Preserved setup failure and retry

docker_b2c_full_q2setup01 failed **before container creation**: frozen launcher forms the Docker name from mode=b2 rather than variant=b2c, colliding with the preserved stopped B2-native container. The daemon error is in raw/docker_b2c_full_q2setup01/create.stderr. It generated no input or ROS/Gazebo data. We did not remove the stopped container or edit frozen code. A unique attempt ID q2csetup02 used the preregistered first setup-only retry and completed. B2-composed I_FULL has used 2 of maximum 3 Q2 attempts; all other Q2 cells used one. This was a name/setup conflict, not a functional policy failure. The all-glob analysis limitation is reported above, not hidden.

## Qualification and formal gate

| Gate | Disposition |
| --- | --- |
| Fixed D1 fixture, 120-source delivery, B0/shim equivalence | PASS for complete setup runs; failed create remains failed. |
| Original consumer, genuine B2 decision path, Servo callback, controller and Gazebo | Normal-path setup PASS within exact-callback and interval-downstream boundaries above. |
| ROS graph, recorder, initial pose and clock start ACK | PASS for complete setup runs; events.jsonl records ACK and barrier, not an inferred sleep. |
| Common stop/hold and safe re-arm in this exact Q2 configuration | UNKNOWN. B1/B3/B2-composed stop adapters logged ready and healthy_capture_complete; normal D1 triggered no stop or re-arm. Earlier Docker stop/monitor-health trials were separate configurations. B2-native deliberately has no composed adapter. |
| Formal latency/resource and exact source-output association | NOT QUALIFIED. Frozen Q2 did not collect preregistered 100 ms per-process/child CPU/RSS traces or all stage-local latency samples. Exact IDs end at Servo callback; event-level downstream parentage remains UNKNOWN. |
| D1 formal B0-B3 comparison | NOT_STARTED / BLOCKED_INTEGRATION: applicable stop/resource/association gates unresolved and separate five-repeat randomized formal configuration/schedule freeze not committed. |

The new campaign shows each normal-input arm can traverse original Docker control to Gazebo without a gross unintended block, including genuine B2. It does **not** show enforcement on invalid source states, stopping an already moving robot, or safe re-arm. A future scoped qualification/freeze would have to cover missing measurement and stop integration without changing the frozen S4 task policy, fixture or thresholds; any changed instrumentation needs B0/shim equivalence requalification. Per the current instruction, no automatic third campaign or formal trial was started. All 18 registered Docker/OpenVR formal cases remain NOT_READY; OpenVR observer equivalence and safe re-arm remain independently unresolved. S5 is INSUFFICIENT_EVIDENCE; no S6/S7 work.

No new runtime raw was excluded: largest file approximately 5.65 MB, raw tree approximately 79 MB. Only reproducible installed dependency/colcon trees remain local-only as documented, with paths, sizes and tree digests, in excluded_artifacts.md. No frozen protocol, prior raw or vendor source was changed.
