# XR→ROS 연구 현황판

Last updated: 2026-09-22. P0 review baseline before this documentation commit: `81a8b60a125d523820f7c2bc284302fbb1f59416`; the commit that carries this board is reported after push and must be checked with `git rev-parse HEAD`.

## Goal and current core question

Goal: determine whether a concrete XR semantic-state condition reaches an original downstream control consumer without preservation or equivalent revalidation, and only then assess whether existing defenses leave a demonstrable method gap. Current question: can the already captured evidence distinguish the source state, consumer acceptance, and Gazebo outcome cleanly enough to justify a fair existing-defense comparison?

## Stage board

| Stage | Status | Conditions / key result | Evidence and next action |
| --- | --- | --- | --- |
| S0 context/inventory | DONE | Git fast-forward to `81a8b60`; local actual Quest, synthetic/Gazebo raw roots, source revisions, images and Pi role checked read-only | `P0_INVENTORY.md`; commit/push this documentation and preserved reviewed raw evidence, then stop |
| S1 trace audit | DONE | Raw PickNik/Spes/Quest2ROS2/Docker/OpenVR recalculated offline; no mismatch in audited values, with causal/XR-semantic UNKNOWNs retained | `S1_TRACE_AUDIT.md`, `runs/s1_trace_audit_20260922T075316Z/`; commit SHA `5eb42b2909205829c5a8ec65bb398050ad24c927` |
| S2 Docker baseline | DONE | New synthetic input reached original receiver→mapper→bridge→MoveIt Servo→Gazebo. D1 moved; D2/D3 zeroed after settling; D4 old/fresh timestamps both accepted; D5 reconnect recaptured reference then moved | `S2_DOCKER_CONTROL_BASELINE.md`, `runs/s2_docker_baseline_20260922T080640Z/`; S2 commit SHA `PENDING_COMMIT`, must be remote-verified before S3 |
| S3 OpenVR baseline | TODO | Existing fake OpenVR→Servo→Gazebo evidence exists; no new runtime executed | `OPENVR_UR5E_DOWNSTREAM_RUNTIME.md`, `runs/openvr_ur5e_downstream_20260914T065659Z/` |
| S4 existing-defense comparison | TODO | No policy or comparison implementation/execution | Must be pre-registered before results are viewed/changed |
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
- ROSMonitoring: no comparison execution or runnable-state conclusion exists yet.

## Handoff instruction for the next worker

1. Read `SEMANTIC_VALIDATION_EXECUTION_PLAN_V2.md`, this board, and `P0_INVENTORY.md` first; check Git status before any work.
2. S2 Docker runtime is complete and now awaits external review. Do **not** start S3/S4 or any Quest/OpenVR/defense runtime automatically.
3. Read `S2_DOCKER_CONTROL_BASELINE.md` and its result root before any next action. Preserve its declared boundaries: synthetic input, Gazebo only, no source-to-bag latency join, no actual Quest tracking semantics, and no physical robot result.
4. After exactly one later approved stage, update this board and the plan if evidence changes, explicitly stage reviewed files, push, verify `HEAD == origin/main`, report, and stop.
