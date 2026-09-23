# XR→ROS 연구 현황판

Last updated: 2026-09-23 (S4-B qualification closure). Reviewed S4-B qualification commit: `9829c2a74f7693cee05f5da337ccc6f2fb9a77a4`; S4-A commit: `226522d21e8c6bfb5cf2b523ea8b32d7423b4c5e`. This board's carrying commit is resolved with `git log -1 --format=%H -- semantic_validation/results/SEMANTIC_VALIDATION_STATUS.md`; local/remote equality is verified after push and reported in the handoff. This avoids embedding a self-referential commit SHA.

## Goal and current core question

Goal: a new XR→ROS defense-framework paper only if a demonstrable gap remains after fair existing-defense comparison. Current question: can existing source checks, genuine ROSMonitoring and controller-internal checks satisfy the preregistered task policy with equal source information? `NO_METHOD_GAP` remains a valid outcome.

## Stage board

| Stage | Status | Conditions / key result | Evidence and next action |
| --- | --- | --- | --- |
| S0 context/inventory | DONE | Git fast-forward to `81a8b60`; local actual Quest, synthetic/Gazebo raw roots, source revisions, images and Pi role checked read-only | `P0_INVENTORY.md`; commit/push this documentation and preserved reviewed raw evidence, then stop |
| S1 trace audit | DONE | Raw PickNik/Spes/Quest2ROS2/Docker/OpenVR recalculated offline; no mismatch in audited values, with causal/XR-semantic UNKNOWNs retained | `S1_TRACE_AUDIT.md`, `runs/s1_trace_audit_20260922T075316Z/`; commit SHA `5eb42b2909205829c5a8ec65bb398050ad24c927` |
| S2 Docker baseline | DONE | New synthetic input reached original receiver→mapper→bridge→MoveIt Servo→Gazebo. D1 moved; D2/D3 zeroed after settling; D4 old/fresh timestamps both accepted; D5 reconnect recaptured reference then moved | `S2_DOCKER_CONTROL_BASELINE.md`, `runs/s2_docker_baseline_20260922T080640Z/`; commit SHA `7d21e003475a96ebd2408cafc6e84d4f5aee6823` |
| S3 OpenVR baseline | DONE | New fake OpenVR W0–W3 runs used unchanged `quest_teleop.py`→MoveIt Servo→Gazebo. W1/W2 produced pose, controller trajectory, and simulated movement; W3 `bPoseIsValid=false` produced none. `Running_OutOfRange` is not read by the source. | `S3_OPENVR_CONTROL_BASELINE.md`, `runs/s3_openvr_baseline_20260922T083841Z/`; commit `1ffad59bcae0a5c9561f3509882d320be832d17e` |
| S4-A investigation/protocol | DONE | Official ROSMonitoring 3.0.0 source acquired/pinned; task policy, native/full-information B0–B3 arms, controls, repeats, metrics and decision rules preregistered. No defense installed or executed. | `S4_EXISTING_DEFENSE_PROTOCOL.md`, detached `.sha256`, `runs/s4a_preregistration_20260922T123356Z/`; carrying commit resolved as above |
| S4-B runtime qualification | PARTIAL | Official ROSMonitoring 3.0.0 PASS on Humble/Jazzy; custom-message allow/block and fail-open oracle error measured. Exact original-path IDs, Gazebo stop/re-arm and integrated barrier remain blocked. | `S4B_RUNTIME_QUALIFICATION.md`, `runs/s4b_qualification_20260922T142928Z/`; carrying commit resolved as above |
| S4-B qualification closure | PARTIAL | Docker source→bridge and OpenVR fake poll→pose lineage observed in shim; Docker stop+zero and official-monitor unknown→generic stop qualified in one synthetic trial. OpenVR pause+hold settled only at 1,203 ms (>1 s frozen limit); B0/shim source timing differed >5 ms; full graph ACK incomplete. | `S4B_QUALIFICATION_CLOSURE.md`, `runs/s4b_qualification_closure_20260922T151053Z/`; carrying commit resolved with `git log -1 --format=%H -- semantic_validation/results/SEMANTIC_VALIDATION_STATUS.md` after push |
| S4-B CP1 qualification continuation | RUNNING | ACKed B0/shim pairs: Docker source max 0.043 ms and final joint diff .003118 rad; OpenVR initial pair INVALID at 10.54 ms, setup-only timer-realigned pair max 4.812 ms and final diff .000072 rad. Stop variant frozen before trial; consumer lineage and OpenVR re-arm still unresolved. | `runs/s4b_cp1_qualification_20260922T234315Z/`; final report and commit pending |
| S4-B B0–B3 comparison | NOT_STARTED | NOT_READY: OpenVR halt/re-arm, formal B0-shim equivalence and complete start ACK remain blocked; consumer-level exact lineage is bounded. | Do not run comparison until explicit review/approval and blockers resolved |
| S5 cross-stack decision | TODO | No method-gap decision | Cannot start before S1–S4 reviewed |
| S6 conditional method | BLOCKED | Requires S5 residual-condition result and explicit approval | No framework implementation authorized |
| S7 conditional evaluation | BLOCKED | Requires S6 method and explicit approval | No evaluation authorized |

## Confirmed facts versus open facts

| Confirmed within stated boundary | Not confirmed / must not infer |
| --- | --- |
| PickNik actual Quest state side-band and robot-free ROS observer raw are local; feasibility report identifies continued Odometry/TF during three non-excluded invalid right-controller intervals | Original PickNik robot consumer, MoveIt consumption, or physical motion |
| Spes actual Quest→server→upstream ROS→Pi trace is local; Pi extra records prevent strict 1:1 delivery count | Pi as controller/actuator or strict lossless delivery |
| Quest2ROS2 actual app reached unchanged `RightArmController` via isolated external CDR adaptation | Native XR tracking state, unmodified external bridge compatibility, CLIK/robot consequence |
| Docker synthetic path and OpenVR fake path reached original MoveIt Servo plus Gazebo; Docker actual app/Gazebo run raw is local | Synthetic/fake outcomes as native Quest semantics; Gazebo as physical robot |
| Pi has a sourceable Humble workspace with `semantic_robot_sink`, but no sink/ROS process was running during this review | Pi has an original framework controller installed or can produce a control-result claim |

## Existing-defense disposition

- Docker_Teleop: synthetic `isTracked=false` is gated to zero output; its field is connection-derived, so adequacy for actual optical/system tracking semantics remains unproven.
- OpenVR UR5e: direct `bPoseIsValid=false` check gates; `eTrackingResult` is dropped in the tested original program, so this particular direct check does not distinguish `Running_OK` from `Running_OutOfRange`.
- PickNik/Spes/Quest2ROS2: current paths do not provide a demonstrated original final robot controller for a defense consequence claim. Pi receipt is not a substitute.
- ROSMonitoring: official master `d03aa5b44e29b76c0e108a098817bdf5aa98e322`, package 3.0.0, generated and passed its official ROS 2 integration test in isolated Humble and Jazzy containers. A Docker_Teleop custom-message filter allowed `tracked=true` and blocked `tracked=false`. Oracle absence, disconnect and 50 ms response timeout were measured fail-open; this is qualification evidence, not a B2 performance result.

## S4-A design corrections and frozen policy

- S2 D3 stalled after invalidation; this closure tested a moving-state stall. S2 D4 used phase-held timestamps and opposite directions; S4-B uses per-sample stamps and same-direction fresh-initial-state pairs. Historical raw/reports are preserved.
- S3 W1/W2 capture phase differed; S4-B needs source index zero, recorder readiness ACK and joint-state tolerance before a common barrier.
- Primary freshness 250 ms, mandatory 100/500 ms sensitivity cases; receive silence 250 ms. Primary explicit recovery re-arm and separate automatic recovery policy both preregistered. No results-based selection.
- Protocol ID XRROS-S4-1.0.0. SHA-256: `3a40337121f8d687dc68036ff2ffc85a1bc6eda275a700ba7d9e8119cd322969`; authoritative verification file: `S4_EXISTING_DEFENSE_PROTOCOL.sha256`. No S4-B results exist at freeze time.

## Handoff instruction for the next worker

1. Read `SEMANTIC_VALIDATION_EXECUTION_PLAN_V2.md`, this board, and `P0_INVENTORY.md` first; check Git status before any work.
2. S4-A is complete. S4-B runtime qualification is PARTIAL and B0–B3 comparison is NOT_STARTED. The current continuous-execution instruction permits progression only through qualified conditions, at most S5; do not start S6/S7.
3. Read `S4_EXISTING_DEFENSE_PROTOCOL.md` and verify its detached SHA-256 before approved S4-B work. Read S2/S3 input/analysis and the S4-A feasibility logs. Never amend the frozen policy after observing S4-B results.
4. Preserve evidence boundaries: Docker synthetic, OpenVR fake API, ROS publication, original callback/consumer, Servo output and Gazebo joints are distinct. Actual Quest semantics and physical robot outcomes remain unverified.
5. ROSMonitoring Humble/Jazzy runtime is qualified. Read `S4B_QUALIFICATION_CLOSURE.md` and its raw root: Docker exact lineage reaches bridge publication and generic stop+zero settles in one trial; OpenVR lineage reaches production pose only, hold misses the frozen 1 s settling bound, and B0/shim source timing violates the 5 ms pair gate. Complete DDS/Servo readiness ACK and OpenVR recovery remain unresolved. Do not promote shim or toy carrier evidence to unmodified B0.
6. For any separately approved later stage, explicitly stage reviewed evidence, push, verify `HEAD == origin/main == remote main`, report and stop.
