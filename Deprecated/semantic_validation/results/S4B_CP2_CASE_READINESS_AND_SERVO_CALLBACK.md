# S4-B CP2: case readiness and Servo callback qualification

Date: 2026-09-23 UTC. Baseline commit: `e795aa3bc6b6b15f7c492949f065eb607b2502e3`.
Protocol: XRROS-S4-1.0.0, SHA-256 `3a40337121f8d687dc68036ff2ffc85a1bc6eda275a700ba7d9e8119cd322969` (unchanged). This is qualification, **not** a B0–B3 defense comparison. No Quest, physical robot, robot driver, new framework, or vendor edit was used.

## Scope and prior evidence reused

The prior [CP1 report](S4B_CP1_QUALIFICATION_CONTINUATION.md) already qualifies the original-path B0/shim pairs for Docker and OpenVR and official ROSMonitoring integration on Humble/Jazzy. Those tests were not repeated. CP1's OpenVR pause+fast-hold variant settled by 616.183 ms but its new-reference phase moved 0.201172 rad; safe re-arm remains blocked. The separate failed 1203.14 ms hold variant remains failed. This CP2 work investigates exact Servo callback acceptance and re-evaluates each registered case's readiness.

All new trial raw, copied harness, observation-only source, patch, build output, calculations and checksums are under [`runs/s4b_cp2_qualification_20260923T003626Z/`](runs/s4b_cp2_qualification_20260923T003626Z/). `commands.jsonl` records trial launcher commands. `analysis/pair_audit.py`, `analysis/callback_audit.py`, and `analysis/case_matrix.py` regenerate the cited JSON/CSV. Their inputs are JSONL; no earlier raw evidence was modified.

## Official Servo path and observation method

Docker used the installed Humble `ros-humble-moveit-servo` 2.5.9 package. A trial-owned `LD_PRELOAD` wrapper forwarded the original `moveit_servo::ServoCalcs::twistStampedCB` and recorded the full `TwistStamped` header and six values after the callback returned. Docker vendor revision remained `64cbdde88bc52c6a80d37f994752e50f95ba537e` and clean. The original B0 pair ran without that hook.

OpenVR used Jazzy `ros-jazzy-moveit-servo` 2.12.4. The interposition attempt [`raw/openvr_shim_payload01/`](runs/s4b_cp2_qualification_20260923T003626Z/raw/openvr_shim_payload01/) produced no callback record despite a running Servo/Gazebo trial; the method was not claimed to work. Local inspection of official tag `2.12.4` (`1ade0e9dcf50dbbbc3a984b995c786cf12736235`) showed `ServoNode::poseCallback` stores `latest_pose_` and `new_pose_msg_` before the processing loop. A **separate, trial-owned** copy of that official package was built with only the observation patch in `inputs/servo_node_observation.patch`. The vendor/OpenVR checkout (`170dad582d624f536359a3192a7f829669c2b031`) was not modified. Overlay library: `/tmp/s4cp2_servo_ws/install/moveit_servo/lib/libmoveit_servo_lib_ros.so.2.12.4`, 35,297,344 bytes, SHA-256 `dbee79dd5cfffc088719bfe87c679ae413bfd942f4b31db5ccc197b8966377b7`. This rebuildable binary was not copied to Git; the pinned source revision, patch and build logs are retained. The original B0 pair used unmodified Servo.

Both observers merely log incoming fields. They do not inspect native validity, source age or generation for allow/block decisions. The original input and output schemas were not changed. This is a B0-shim observation qualification only, not a new defense baseline.

## Exact lineage and evidence boundary

The audit keys include the complete ROS header stamp/frame and all Twist/Pose numeric fields. Each key was unique in the producer and callback logs; no approximate timestamp association is used for this join.

| Trial | Original Servo-input publications | Actual Servo callbacks | Unique exact field joins | Source-parent / original neutral | Qualified interpretation |
| --- | ---: | ---: | ---: | ---: | --- |
| `docker_shim_payload01` | 847 | 847 | 847 | 372 / 475 | Exact source or original-neutral parent → bridge publication → `ServoCalcs` callback in this observational run; B0 equivalence passes below. |
| `openvr_shim_overlay01` | 450 | 450 | 450 | 450 / 0 | Fake API poll → original pose publication → `ServoNode::poseCallback` in the overlay run, but B0 equivalence fails the frozen timing rule. Do not promote to an equivalent B0 result. |

The full callback payloads appear in `raw/docker_shim_payload01/servo_callback_payload.jsonl` and `raw/openvr_shim_overlay01/servo_callback_overlay.jsonl`. The source/sample/generation/native-state parent mapping is in each trial's `lineage.jsonl`; `callback_metrics.json` is recomputed from these records. A callback observation shows intake at that boundary. It does **not** show that a particular sample was subsequently selected by Servo's update loop, caused a specific Servo/controller output, or caused a particular Gazebo joint sample. These downstream per-sample parent links remain **UNKNOWN**. ROS publications, controller outputs, and joint movement are separately recorded in `topics.jsonl` but are not asserted to be exact children by temporal proximity.

## Frozen B0 versus observation equivalence

The reused CP1 calculator checks fixture identity, common boot/time namespace, source-index schedule (maximum ≤5 ms), final named-joint error (≤0.02 rad), positive motion (>0.01 rad), and launch exit. It does not hide unsuccessful pairs. All completed trial pairs are in `analysis/pair_metrics.json`.

| Pair | Fixture/clock | Max source offset difference | Max final joint difference | Positive motion | Result |
| --- | --- | ---: | ---: | --- | --- |
| Docker `docker_b0_payloadpair01` / `docker_shim_payload01` | same/same | 0.059467 ms | 0.002445 rad | 0.286955 / 0.284510 rad | **PASS** |
| OpenVR `openvr_b0_overlaypair01` / `openvr_shim_overlay01` | same/same | 5.718223 ms | 0.000415 rad | 1.534816 / 1.535231 rad | **INVALID_COMPARISON** (>5 ms) |
| OpenVR `openvr_b0_overlaypair03` / `openvr_shim_overlay01` | same/same | 5.384078 ms | 0.000292 rad | 1.534939 / 1.535231 rad | **INVALID_COMPARISON** (>5 ms) |

`openvr_b0_overlaypair02` failed before recorder/source input because the trial launcher was edited while its read-only bind mount was being read (`/code/launch.sh: line 60: xt: command not found`). Its stderr and `exit.json` are preserved; it is a setup error, not control or policy evidence. No further retry was made after the final completed invalid pair. The 5 ms rule was not changed or selectively waived. The observed OpenVR output agreement does not repair invalid source timing. A fresh, pre-frozen observation method or timing qualification is required before formal OpenVR comparisons use this overlay.

## Case-by-case preregistered readiness

`analysis/case_readiness.csv` contains all **18** Docker/OpenVR case rows and, for each, the required native state, lineage, Servo/controller point, stop/re-arm, clock/barrier, current evidence, missing condition, verdict and reason. `analysis/case_matrix.py` regenerates it. The grouped summary below does not replace those rows.

| Cases | Current verdict | Decisive missing prerequisites |
| --- | --- | --- |
| Docker D0/D1 and OpenVR W0/W1 | **BLOCKED** for formal four-baseline comparison | Original idle/positive-control diagnostics exist, but equal-information B1/B2/B3 implementations, fixture/config freeze, and all-participant start ACK are not qualified. OpenVR overlay additionally fails equivalence. |
| Docker D2/D3/D4/D4-L/D5/D6 | **BLOCKED** | Per-case shared stop/re-arm, full-information state binding, age/delay/recovery policies, and exact output parent or UNKNOWN-safe metric handling are not installed/qualified. Docker callback join alone is insufficient. |
| OpenVR W2/W3/W4/W5 | **BLOCKED** | OpenVR observer equivalence is invalid; full-information B1/B2/B3 and stop integration absent. W4/W5 additionally need a jump-free re-anchor after CP1's 0.201172 rad reference movement. |
| Both stacks C-ID/C-MON | **BLOCKED** | Atomic state envelope/adversarial binding fixtures and official monitor-health-to-common-stop integration in the full graph are absent. Earlier official monitor fail-open evidence remains valid but is not a comparison result. |

**READY count: 0/18.** This does not mean each original system fails the policy. It means no complete, preregistered B0–B3 cell has all required observation, fair-state delivery, start, repeated-trial and positive-control gates qualified. Limited diagnostics remain separate from formal results. No comparison success rate, latency distribution, method-gap conclusion or S5 decision is calculated.

## Qualification disposition and next bounded work

| Qualification item | Current status and evidence |
| --- | --- |
| Docker original/shim equivalence | **PASS** in CP1; new Servo-observer B0 pair **PASS** here. |
| OpenVR original/shim equivalence | CP1 standard shim pair **PASS**; new Servo-overlay B0 pair **INVALID_COMPARISON** twice here. These are different observer configurations. |
| Docker source→Servo callback linkage | **PASS** for the 847 uniquely joined observed publications in this trial; per-sample Servo output/controller/Gazebo parent **UNKNOWN**. |
| OpenVR fake poll→Servo callback linkage | Exact 450 joins observed in overlay, but equivalence to B0 is **INVALID_COMPARISON**; per-sample downstream parent **UNKNOWN**. |
| Docker stop/re-arm | Prior qualified moving-state stop and reference handling remain bounded to their tested trial; full registered R_EXPLICIT/R_AUTO four-baseline integration **BLOCKED**. |
| OpenVR stop/re-arm | Stop-only fast-hold met 1 s; jump-free re-arm **BLOCKED** by CP1 raw. No new variant or runtime was executed here. |
| Clock/common barrier | The paired trial harness records boot ID, monotonic clock, graph/controller/recorder checks and release. Full B1/B2/B3 participants and final-state envelope are not present, so an all-baseline ACK is **UNKNOWN/BLOCKED**. |
| Official ROSMonitoring | Prior Humble/Jazzy generator/integration and custom filter tests **PASS**; no defense-performance comparison or complete full-graph health stop was run here. |

Next independent preparation is: design a nondefensive OpenVR callback observer that meets the already frozen 5 ms rule; implement and precommit the common B1/B2/B3 state envelope and start ACK; qualify a generic OpenVR re-anchor/stop variant *before* using it; and instrument per-command selection/output where the protocol's event-level metric requires it. Failure trials and all setup changes must remain visible. Until at least one complete case is READY, Phase B fixture freeze and Phase C formal B0–B3 trials are not authorized. S5 remains `INSUFFICIENT_EVIDENCE`; no claim of novel method necessity follows.
