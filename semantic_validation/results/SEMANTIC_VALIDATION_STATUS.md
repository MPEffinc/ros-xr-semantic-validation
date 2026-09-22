# XR→ROS 연구 현황판

Last updated: 2026-09-22. P0 review baseline before this documentation commit: `81a8b60a125d523820f7c2bc284302fbb1f59416`; the commit that carries this board is reported after push and must be checked with `git rev-parse HEAD`.

## Goal and current core question

Goal: determine whether a concrete XR semantic-state condition reaches an original downstream control consumer without preservation or equivalent revalidation, and only then assess whether existing defenses leave a demonstrable method gap. Current question: can the already captured evidence distinguish the source state, consumer acceptance, and Gazebo outcome cleanly enough to justify a fair existing-defense comparison?

## Stage board

| Stage | Status | Conditions / key result | Evidence and next action |
| --- | --- | --- | --- |
| S0 context/inventory | DONE | Git fast-forward to `81a8b60`; local actual Quest, synthetic/Gazebo raw roots, source revisions, images and Pi role checked read-only | `P0_INVENTORY.md`; commit/push this documentation and preserved reviewed raw evidence, then stop |
| S1 trace audit | TODO | No raw reanalysis performed | Inputs enumerated in `P0_INVENTORY.md`; requires a new result root and one committed audit report |
| S2 Docker baseline | TODO | Existing synthetic and actual Quest→Gazebo evidence exists; no new runtime executed | `DOCKER_TELEOP_DOWNSTREAM_RUNTIME.md`, `runs/docker_teleop_e2e_20260914/`, `runs/hw_docker_native_20260917T071824Z/` |
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
2. Do **not** start S1 until the commit from this board is externally reviewed. Do not start a new Quest/Gazebo/ROS runtime now.
3. For S1, work only from the recorded hashes in `P0_INVENTORY.md`; write all new analysis and logs under a new result root, preserve inputs, and distinguish source/ROS/Pi/consumer/Gazebo evidence.
4. After exactly one stage, update this board and the plan if evidence changes, explicitly stage reviewed files, push, verify `HEAD == origin/main`, report, and stop.
