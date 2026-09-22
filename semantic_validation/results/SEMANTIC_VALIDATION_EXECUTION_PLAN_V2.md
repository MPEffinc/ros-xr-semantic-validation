# XR→ROS 의미 보존·방어 연구 실행 계획 v2 (local working plan)

## Status and authority

**STATUS: CONTEXT_REVIEWED; no new runtime experiment started.** This local plan is based on the inventory and the currently present evidence. `DEFENSE_FRAMEWORK_EXECUTION_PLAN_V1.md` remains a useful GitHub draft, not a binding plan. Before each later stage, read this file and `SEMANTIC_VALIDATION_STATUS.md`; after a stage commit/push, stop for external review before proceeding.

## Research goal and claim discipline

Question: when XR semantic context (validity, actively tracked versus inferred/emulated, source time/frame, session generation, invalidation/re-arm state) crosses an XR→ROS→control boundary, is it preserved or independently revalidated before the **original** downstream consumer accepts it? If a concrete, reproducible residual condition remains after fair comparison to existing defenses, does a new method provide an independent benefit?

The evidence levels are never merged: static source; synthetic/fake/replay; actual Quest source state; ROS/Pi reception; original consumer acceptance; Gazebo simulated consequence; physical robot. `PI_RECEIVED` is observation only. A system `POSITION/ORIENTATION` transition, Unity `isTracked`, WebXR `emulatedPosition`, and OpenVR `bPoseIsValid`/`eTrackingResult` are distinct observations.

## Existing evidence and current method-gap hypothesis

- Docker_Teleop synthetic replay proves that its original ROS-side `isTracked` gate halts D2/D3. The 2026-09-17 actual Quest/Gazebo trace has device mode transitions while the connection-derived production field stayed true, but this is not yet a causal or optical-loss claim.
- OpenVR UR5e fake replay proves `bPoseIsValid=false` is gated, while `Running_OutOfRange` is not read and reaches Gazebo equivalently to `Running_OK`. It is not native Quest/ALVR evidence.
- PickNik and Spes provide actual Quest anchors but lack demonstrated original robot-control consumers. Quest2ROS2 reaches an unchanged controller after an external compatibility adaptation but has opaque XR semantics and no original CLIK consumer.

Thus there is **no approved novel-method claim**. Existing source-side gate, ROSMonitoring, and direct controller checks are comparison baselines only. If fair later tests show them sufficient, record `NO_METHOD_GAP` and do not implement a framework.

## Sequential stages and gates

| Stage | Objective and allowed work | Success evidence / failure disposition |
| --- | --- | --- |
| S0 Context and preservation inventory | Git, local raw existence/SHA/format, target revisions, Docker/Pi read-only state; create plan and status board | DONE only with committed inventory/documents and remote SHA confirmation. Completed by the P0 inventory commit. |
| S1 Existing-trace audit | Reanalyze only existing PickNik/Spes/Quest2ROS2/Docker/OpenVR records. No runtime. Recalculate time windows, clock domains, exclusions and published metrics from hashed inputs into a new result root. | A committed `S1_TRACE_AUDIT.md`, commands, input hash manifest, stdout/stderr and explicit UNKNOWN/exclusions. Mismatch or missing inputs is BLOCKED/INVALIDATED, not silently repaired. |
| S2 Docker_Teleop original-path baseline | In a new result root, reproduce only the Gazebo-only original receiver→mapper→Servo chain with declared synthetic input; compare neutral/valid/invalid, delayed arrival, reconnect where supported. | Original source revision, image digest, commands, ROS capture/bag, Gazebo `/joint_states`, raw stdout/stderr; input provenance explicitly synthetic. Never use driver launch or `robot_ip`. |
| S3 OpenVR original-path baseline | Reproduce W0–W3 using the documented fake dependency upstream of unmodified `quest_teleop.py` in a new result root. | Same evidence structure; distinguish `bPoseIsValid` and `eTrackingResult`; no native Quest/SteamVR claim. |
| S4 Existing-defense comparison protocol and execution | First pre-register one policy per condition: trusted state source, freshness budget, source/receive clocks, disconnect/recovery and acceptable inference. Then compare unprotected original path, source-state gate harness, actual ROSMonitoring if runnable, and controller-side direct check with identical input/policy. | Per-case original-consumer/Servo/Gazebo outputs plus false accept/reject and timing. If ROSMonitoring cannot run, record environment reason—not method failure. |
| S5 Cross-stack decision | Compare only conditions with valid evidence across Docker/OpenVR; reuse PickNik/Spes trace in analysis without inventing a consumer. | `S5_CROSS_STACK_DECISION.md` identifies a specific independent residual condition or `NO_METHOD_GAP`; otherwise no method implementation. |
| S6 Conditional method design | Start only after S5 shows an unresolved functional/practical gap and separate approval. Implement outside upstream source and compare fairly. | Mechanism, trust/coverage/limits, raw logs, baseline comparison; otherwise NOT_STARTED. |
| S7 Conditional evaluation | Evaluate confirmed method on independent original paths using fixed policies and latency/resource measures. | Reproducible code/logs and bounded claims; otherwise NOT_STARTED. |

## Required per-stage evidence package

Each stage must use a new named result root and save: exact command and environment/image/commit; input provenance plus SHA-256; stdout/stderr; ROS topic/bag and Gazebo outputs where used; analysis command/result; exclusions/failure reason; evidence level; and a status-board update. Raw data is append-only: never overwrite the prior root. Explicitly inspect candidate files for size, credentials, APKs/caches and relevance before `git add`; document excluded raw with local path and SHA-256.

## Safety and stop rules

- No Quest re-run is planned before existing data reuse and the two existing Gazebo paths are audited/reproduced.
- No physical robot, driver, `robot_ip`, CAN, actuator, network/firewall change, Docker-socket permission change, or upstream source modification is authorized by this plan.
- Do not launch Docker_Teleop `servo_test.launch.py`; use only the documented Gazebo-only path. Do not fabricate missing PickNik/Spes/Quest2ROS2 controllers.
- At every stage boundary: commit explicitly selected files, push, verify local HEAD equals `origin/main`, report SHA/files/logs/key evidence, then stop for ChatGPT review. Do not advance automatically.
