# Evidence Ledger

Canonical actual-hardware run은 `spes_quest_hw_20260831T001349Z`, canonical autonomous suite는 `semantic_validation_20260831T153536Z`다. 이 ledger에서 actual XR hardware evidence는 F-SPES-HW-001/002뿐이다. 어느 finding도 `ACTUAL_ROBOT`이 아니며, Quest2ROS2 actual ROS transport는 이번 retry에서도 실행되지 않았다.

## Evidence-level contract

| Level | Meaning in this ledger |
| --- | --- |
| `STATIC` | 사람이 고정 source를 추적한 결과. |
| `MACHINE_CHECKED_STATIC` | 고정 commit의 source/schema/serialized reference를 checker가 검증. Runtime claim 아님. |
| `RUNTIME_SYNTHETIC` | 실제 production method/path를 synthetic source 또는 test double로 실행. Actual XR/ROS transport라는 뜻 아님. |
| `ACTUAL_ROS_RUNTIME` | Actual ROS graph/node/publisher/subscriber transport를 실행. 현재 새 finding 없음. |
| `ACTUAL_XR_HARDWARE` | Actual Quest semantic transition을 raw capture. Endpoint 범위를 별도 명시. |
| `ACTUAL_ROBOT` | Physical robot/actuator consequence. 현재 없음. |

`SOURCE_DATAFLOW_CONFIRMED`는 PickNik의 `MACHINE_CHECKED_STATIC` 안에서 serialized scene/action reference까지 연결했음을 나타내는 refinement다. `PUBLIC_ISSUE_SELF_REPORT`는 외부 motivation이며 self-generated evidence level이 아니다.

## F-SPES-HW-001

- **Claim:** Actual Quest 3 obstruction의 valid T1 5/5에서 controller pose가 non-null인 채 `emulatedPosition=true`가 됐고, selected source `CONTROLLER`, `move=true`, production control packet, actual Spes server update/target callback이 계속됐다.
- **Evidence level:** **`ACTUAL_XR_HARDWARE` → ACTUAL SPES SERVER CALLBACK**. Actual ROS/robot 아님.
- **Repository/revision:** `https://github.com/SpesRobotics/teleop.git@c5d808155a87b584d6147a5943d4b87c34c92db0`.
- **Paths:** upstream `teleop/index.html:264-278,328-380`; server `teleop/__init__.py:220-285`; observer `harness/spes_hardware_server.py`; analyzer `harness/reanalyze_spes_hw.py`.
- **Command:** `python3 semantic_validation/harness/reanalyze_spes_hw.py --output-dir <new-dir>`.
- **Raw:** [`experiment.jsonl`](../logs/quest_hw/spes_quest_hw_20260831T001349Z/experiment.jsonl), [`server.jsonl`](../logs/quest_hw/spes_quest_hw_20260831T001349Z/server.jsonl), independent [`reanalyzed.json`](../logs/reanalysis/reanalyze_spes_hw_20260831T152922Z/reanalyzed.json), [`comparison.json`](../logs/reanalysis/reanalyze_spes_hw_20260831T152922Z/comparison.json).
- **Verification:** `INDEPENDENT_REANALYSIS_PASS`; 129 major fields compared, 0 mismatch. Packet delta 403/359/360/358/359; server delta 403/359/361/357/360. Fresh production generation 4, no prior-client overlap, server-control offset 11942 constant. Existing correlation count 788 versus strict-window 777 is a documented non-decisive window difference.
- **Limitation:** One Quest 3/browser session, five valid trials, browser/runtime version not recorded. Controller-null viewer fallback and real disconnect not observed. Consequence stops at server callback.
- **Next evidence:** Independent Quest/session replication; separate targeted controller-null/disconnect protocol; no robot required.

## F-SPES-HW-002

- **Claim:** Valid T1 5/5에서 move release/re-press 없이 recovery 뒤 target processing이 continuous 또는 automatic re-anchor 후 resume됐다.
- **Evidence level:** **`ACTUAL_XR_HARDWARE` → ACTUAL SPES SERVER CALLBACK**.
- **Repository/revision/path:** Same Spes commit; classifier `instrumentation/quest-operator.js`; regression `harness/spes_classifier_regression.py`, `harness/spes_quest_operator_selftest.mjs`.
- **Command:** `python3 semantic_validation/harness/spes_classifier_regression.py --output-dir <new-dir>`.
- **Raw:** [`result.json`](../logs/classifier_regression/spes_classifier_regression_20260831T151624Z/result.json), hardware raw files above.
- **Verification:** Current classifier counts jump rejects only from loss detection. Actual T1-1=`RECOVERY_CONTINUOUS`; T1-2~5=`RECOVERY_JUMP_REJECT_THEN_REANCHOR`. T1-1 had one pre-loss reject and zero loss-window reject. One `INVALID_MOVE_RELEASED` was excluded; synthetic focus-invalid exclusion PASS.
- **Limitation:** Recovery label is derived from one run and server callback behavior, not operator intent or robot motion.
- **Next evidence:** Repeat with fixed classifier in an independent hardware session; compare explicit re-arm policy as defense in separate work.

## V-SPES-INST-001 — instrumentation integrity

- **Claim:** Tested operator/logger/server-observer instrumentation does not change production pose serialization, send conditions, `Teleop.__update` result, callbacks, exceptions, or private control state.
- **Evidence level:** **`RUNTIME_SYNTHETIC` non-interference validation**; not a semantic finding.
- **Repository/revision/path:** Spes commit above; `harness/spes_payload_equivalence_matrix.mjs`, `harness/spes_instrumentation_integrity.py`, `harness/spes_hardware_server.py`.
- **Command:** `PYTHONPATH=/tmp/ros_xr_semantic_deps python3 semantic_validation/harness/spes_instrumentation_integrity.py`.
- **Raw:** [`summary.json`](../logs/instrumentation_integrity/spes_instrumentation_integrity_20260831T152759Z/summary.json), [`integrity.jsonl`](../logs/instrumentation_integrity/spes_instrumentation_integrity_20260831T152759Z/integrity.jsonl), final-suite [`summary.json`](../logs/semantic_validation_20260831T153536Z/artifacts/instrumentation_integrity/dedicated/summary.json).
- **Verification:** `INSTRUMENTATION_NON_INTERFERENCE_PASS`; frontend 7 exact-byte/send cases, server 12 differential cases; experiment fields absent from `type:"pose"`; source/generated operator SHA-256 both `5aacab70...`; target clean.
- **Limitation:** Deterministic browser/WebXR doubles and direct server method calls do not prove zero device timing overhead or all concurrency interleavings.
- **Next evidence:** Preserve the same differential gate before every new hardware build/run.

## F-SPES-001

- **Claim:** Actual frontend code maps synthetic controller-valid, controller-emulated, and controller-null/viewer-fallback states with the same numeric pose/control values to indistinguishable downstream production representations.
- **Evidence level:** **`RUNTIME_SYNTHETIC`**.
- **Repository/revision/path:** Spes commit above; `teleop/index.html:264-278,328-380`; `harness/spes_semantic_collision.mjs`.
- **Command:** `node semantic_validation/harness/spes_semantic_collision.mjs --output <jsonl>`.
- **Raw:** [`spes_semantic_collision.jsonl`](../logs/no_quest/no_quest_20260830T142000Z/spes_semantic_collision.jsonl).
- **Limitation:** Viewer fallback hardware activation was not observed; synthetic collision alone is not Quest evidence.
- **Next evidence:** Targeted actual controller-null capture with source/packet/server correlation.

## F-SPES-002

- **Claim:** WSS disconnect does not reset control anchors; near reconnect is immediately actionable and far reconnect is actionable after one reject and automatic re-anchor.
- **Evidence level:** **`RUNTIME_SYNTHETIC`** over actual local HTTPS/WSS and actual server method in canonical no-Quest run.
- **Repository/revision/path:** Spes commit; `teleop/__init__.py:168-172,246-285,297-315`; `harness/spes_no_quest_runtime.py`.
- **Command:** `PYTHONPATH=/tmp/ros_xr_semantic_deps python3 semantic_validation/harness/spes_no_quest_runtime.py --result-dir <new-dir>`.
- **Raw:** [`near`](../logs/no_quest/no_quest_20260830T142000Z/spes_runtime/spes_reconnect_near.jsonl), [`far`](../logs/no_quest/no_quest_20260830T142000Z/spes_runtime/spes_reconnect_far.jsonl).
- **Limitation:** Actual Quest browser reconnect/session loss and ROS/robot were not run. Final sandbox rerun was `SKIP_ENV` because local sockets were prohibited; it neither repeats nor invalidates the canonical PASS.
- **Next evidence:** Actual Quest WSS loss with XR session/transport generation and anchor state captured together.

## F-SPES-003

- **Claim:** Production pose packet/server path carries no source time and accepts delayed single/trajectory samples without a source-age guard.
- **Evidence level:** **`RUNTIME_SYNTHETIC`**.
- **Repository/revision/path:** Spes commit; `teleop/index.html:355-380`, `teleop/__init__.py:220-285`; `harness/spes_no_quest_runtime.py`.
- **Command:** Same no-Quest runtime command.
- **Raw:** [`normal`](../logs/no_quest/no_quest_20260830T142000Z/spes_runtime/spes_freshness_normal.jsonl), [`delayed single`](../logs/no_quest/no_quest_20260830T142000Z/spes_runtime/spes_freshness_delayed_single.jsonl), [`delayed trajectory`](../logs/no_quest/no_quest_20260830T142000Z/spes_runtime/spes_freshness_delayed_trajectory.jsonl).
- **Limitation:** Controlled application queue, not TCP reorder or actual Quest source-age fault.
- **Next evidence:** Correlate actual XR frame time, packet time, and server time in a hardware age-fault protocol.

## F-SPES-004

- **Claim:** Explicit `move=false` clears anchors, but tracking/source invalidation is not coupled to it; a hidden far controller→viewer transition becomes actionable after automatic re-anchor.
- **Evidence level:** **`RUNTIME_SYNTHETIC`**.
- **Repository/revision/path:** Spes commit; `teleop/__init__.py:231-285`; `harness/spes_no_quest_runtime.py`.
- **Command:** Same no-Quest runtime command.
- **Raw:** [`near re-arm`](../logs/no_quest/no_quest_20260830T142000Z/spes_runtime/spes_control_near_rearm.jsonl), [`far re-arm`](../logs/no_quest/no_quest_20260830T142000Z/spes_runtime/spes_control_far_rearm.jsonl), [`hidden switch`](../logs/no_quest/no_quest_20260830T142000Z/spes_runtime/spes_control_hidden_switch.jsonl).
- **Limitation:** Actual source switch was not observed on Quest.
- **Next evidence:** Separate hardware viewer-fallback protocol with move/re-arm transition capture.

## F-SPES-005

- **Claim:** Old-source application queues lack source-generation metadata and can become actionable after geometric recovery/re-anchor.
- **Evidence level:** **`RUNTIME_SYNTHETIC` — EXPLORATORY**.
- **Repository/revision/path:** Spes commit; `harness/spes_no_quest_runtime.py`.
- **Command:** Same no-Quest runtime command.
- **Raw:** [`stall switch`](../logs/no_quest/no_quest_20260830T142000Z/spes_runtime/spes_network_stall_switch.jsonl), [`old generation`](../logs/no_quest/no_quest_20260830T142000Z/spes_runtime/spes_network_old_generation_replay.jsonl).
- **Limitation:** Does not establish TCP reorder, generic network vulnerability, or real reconnect composition.
- **Next evidence:** Do not upgrade unless an actual application queue/reconnect trace motivates it.

## F-Q2R-001

- **Claim:** Unchanged Quest2ROS2 arm callback consumes 10 ms–10 s old and 1 s future stamps without age validation and regenerates output at callback-time `now`; a 3 s stale trajectory reaches the publish test double. **Reproduced 2026-09-07 over actual ROS 2 transport with the actual pinned production node:** 7/7 age cases published, no age gate observed at that boundary.
- **Evidence level:** **E2 `SYNTHETIC_RUNTIME`, now with actual ROS 2 transport + actual production node.** The earlier `BLOCKED_ENV` limitation is resolved. Downstream consequence is `NATIVE_CONSUMER_ACCEPTED` (the framework's own `RightArmController` accepted input and published its control target); it is **not** E5/E6 because the source is synthetic, and **not** an actuator claim.
- **Repository/revision/path:** `https://github.com/Taokt/Quest2ROS2.git@07aaf65149c9e29103f1fc61deb466cef8a55cef`; `q2r2_bringup/robot_arm_controller_base.py:166-208,211-306`; node `q2r2_bringup.right_arm_controller.RightArmController`, in `/q2r_right_hand_pose`, out `/bh_robot/right_arm_clik_controller/target_frame`.
- **Command:** `PYTHONPATH=/tmp/ros_xr_semantic_deps python3 semantic_validation/harness/quest2ros2_stale_restamp.py --output <jsonl>`; actual transport `sg docker -c "python3 semantic_validation/harness/run_quest2ros2_ros_runtime.py"`.
- **Raw:** callback-only [`quest2ros2_stale_restamp.jsonl`](../logs/no_quest/no_quest_20260830T142000Z/quest2ros2_stale_restamp.jsonl); actual transport [`transport_summary.json`](../logs/quest2ros2_ros_runtime/quest2ros2_ros_runtime_20260907T050835Z/transport_summary.json), [`transport.jsonl`](../logs/quest2ros2_ros_runtime/quest2ros2_ros_runtime_20260907T050835Z/transport.jsonl), [`summary.json`](../logs/quest2ros2_ros_runtime/quest2ros2_ros_runtime_20260907T050835Z/summary.json); prior blockers [`20260831T150939Z`](../logs/quest2ros2_ros_runtime/quest2ros2_ros_runtime_20260831T150939Z/summary.json), [`20260907T050818Z`](../logs/quest2ros2_ros_runtime/quest2ros2_ros_runtime_20260907T050818Z/summary.json).
- **Limitation:** The pose source is a synthetic publisher, not the Quest2ROS2 Unity/Quest frontend, whose XR-side semantics remain unaudited. The original CLIK controller and gripper action server were absent (`Waiting for gripper action server`), so the framework's own downstream controller never consumed the target; a dummy subscriber observed it. Container ran with `--network none`; no robot or driver.
- **Next evidence:** Actual XR producer for the same node; and, separately, an inert stand-in for the CLIK controller to observe the next consumer boundary.

## F-Q2R-002

- **Claim:** Different synthetic input frame IDs (`xr_controller_A/B`, old/new reference-space cases) are not preserved by the callback output, which uses the configured base frame. **Reproduced 2026-09-07 over actual ROS 2 transport:** 7/7 trials `source_frame_preserved=false`, all substituted with configured `bh_robot_base`.
- **Evidence level:** **E2 `SYNTHETIC_RUNTIME`, now with actual ROS 2 transport + actual production node.**
- **Repository/revision/path/command/raw:** Same as F-Q2R-001.
- **Limitation:** Arbitrary software frame labels are not an actual OpenXR reference-space transition. The frame sweep demonstrates the boundary's transformation policy, not an observed XR reference-space change.
- **Next evidence:** Capture the actual producer frame contract from the Quest2ROS2 frontend (currently a black box).

## F-PICKNIK-001

- **Claim:** In the enabled Quest/OpenXR Unity scene, controller position/rotation and `trackingState` reach the exact left/right tracked-pose GameObject Transform drivers; `RosPublishers` then reads only Transform, drops tracking state/source time at the Odometry/TF boundary, and stamps with `DateTime.UtcNow`.
- **Evidence level:** **`MACHINE_CHECKED_STATIC — SOURCE_DATAFLOW_CONFIRMED`**. No Unity/Quest/ROS runtime.
- **Repository/revision:** `https://github.com/PickNikRobotics/meta_quest_teleoperation.git@bbaef0762fdb0b429b8ea12a4ca65040748b41dd`.
- **Paths:** `UnityProject/Assets/ROSPublishers.cs:286-293,318-416`; enabled `SampleScene.unity`; nested complete/XRI rig prefabs; `XRI Default Input Actions.inputactions`; OpenXR settings; `harness/picknik_deep_validation.py`.
- **Command:** `python3 semantic_validation/harness/picknik_deep_validation.py --output <jsonl> --summary <json> --probe-adb`.
- **Raw:** [`summary.json`](../logs/picknik/picknik_deep_20260831T151950Z/summary.json), [`deep_validation.jsonl`](../logs/picknik/picknik_deep_20260831T151950Z/deep_validation.jsonl), [`hw_staging_manifest.json`](../logs/picknik/picknik_deep_20260831T151950Z/hw_staging_manifest.json).
- **Verification/upgrade:** 33/33 deep checks, legacy 10/10, self-tests 4/4 PASS; target clean; production publisher byte-identical in disposable staging.
- **Corrected prior wording:** `isTracked/trackingState` are present repository-wide. Only the publisher boundary fails to serialize/gate them; repository-wide absence is disproved.
- **Limitation:** Unity executable/test/CI/APK absent, ADB devices 0, current-shell ROS absent. Real loss state, Transform behavior, Odometry/TF progression, and downstream actionability are `BLOCKED_ENV/BLOCKED_HW`.
- **Next evidence:** Prepared robot-free PickNik Quest side-band + actual Odometry/TF dummy observer protocol in [`PICKNIK_HW_READY.md`](PICKNIK_HW_READY.md).

## F-NVIDIA-001

- **Claim:** Production-linked release preserves controller activity and position/orientation `VALID` conjunction, and gates selected ROS aim output; invalid release representation may use identity substitution.
- **Evidence level:** **`MACHINE_CHECKED_STATIC`**.
- **Repository/revisions:** `https://github.com/NVIDIA-ISAAC-ROS/isaac_ros_teleop.git@197f5cd9ff2cbd90533a93c67be2a661319048ba`; gitlink `https://github.com/NVIDIA/IsaacTeleop.git@465ce637120ac35404f5f741a9f25f3f1a1a25ea` (`release/1.3.x`).
- **Paths:** `src/core/live_trackers/cpp/live_controller_tracker_impl.cpp`, `src/core/schema/fbs/controller.fbs`, `examples/teleop_ros2/python/messages.py` at gitlink revision.
- **Command:** `PYTHONPATH=/tmp/ros_xr_nvidia_deps python3 semantic_validation/harness/nvidia_positive_control.py --output <jsonl>`.
- **Raw:** [`nvidia_positive_control.jsonl`](../logs/nvidia/nvidia_revalidation_20260831T150323Z/nvidia_positive_control.jsonl), [`source_provenance.jsonl`](../logs/nvidia/nvidia_revalidation_20260831T150323Z/source_provenance.jsonl).
- **Verification:** Linked release machine checks 8/8 PASS.
- **Limitation:** `VALID` is not `TRACKED`; native tracker/OpenXR/ROS runtime was not executed.
- **Next evidence:** Native fixture/hardware trace of exact VALID/TRACKED/activity through ROS output.

## F-NVIDIA-002

- **Claim:** Current-main generic retargeters hold/zero/clear smoothing on invalid pose and rebaseline the next valid relative sample.
- **Evidence level:** **`RUNTIME_SYNTHETIC`** using upstream pure-Python tests.
- **Repository/revision/path:** Executed local `NVIDIA/IsaacTeleop@9fba23c4a3bd5b6de732cac77a47f471fca25276`; semantic files SHA-equivalent to remote main `334978b0ee73ce3e9102a22bd4c889d8b77dcf82`; `src/python/isaacteleop/retargeters/se3_retargeter.py`, upstream validity tests.
- **Command/raw:** Same NVIDIA harness and raw log as F-NVIDIA-001.
- **Verification:** SE3 validity tests 5/5 plus hand gate tests 5/5 PASS.
- **Limitation:** Do not transfer current-main behavior to linked release. No native DeviceIO/OpenXR, ROS transport, Quest, or robot execution.
- **Next evidence:** Separate native runs for linked release and main, with exact flag/output correlation.

## F-NVIDIA-003

- **Claim:** Inspected controller tracker uses `VALID` but not `POSITION_TRACKED/ORIENTATION_TRACKED`; internal query/update timestamp does not remain first-class in the actionable ROS path, and no source-age or reconnect-generation guard was found.
- **Evidence level:** **`MACHINE_CHECKED_STATIC`**.
- **Repository/revisions/paths/command/raw:** Same NVIDIA revisions and artifacts; additionally `src/core/schema/fbs/timestamp.fbs` and current-main ROS message builder.
- **Limitation:** Absence in inspected path is not actual inferred-state/freshness runtime behavior.
- **Next evidence:** Same-frame OpenXR location flags, internal timestamp, retargeter output, ROS header, and reconnect generation trace.

## External comparator — NVIDIA issue #731

- **Status:** **`PUBLIC_ISSUE_SELF_REPORT`**, not a ledger finding or independent reproduction.
- **Observation reported externally:** Quest 3/CloudXR occlusion, extrapolated/inferred behavior, recovery snap, SO-101 lurch, validity-based mitigation.
- **Boundary:** This work did not obtain/reanalyze its raw telemetry or reproduce the robot run. It preempts broad novelty claims about first occlusion/lurch/validity-gate observation, while motivating the semantic-boundary question.
- **Analysis:** [`NVIDIA_VS_SPES_ANALYSIS.md`](NVIDIA_VS_SPES_ANALYSIS.md).

## Current synthesis

- Invariant mapping: [`INVARIANT_MATRIX.md`](INVARIANT_MATRIX.md).
- Trivial-fix threat: [`TRIVIAL_FIX_THREAT.md`](TRIVIAL_FIX_THREAT.md).
- Decision: **GO — NOT STRONG GO**, because a second independently reproduced runtime/hardware actionable confirmation is absent. See [`RESEARCH_DECISION.md`](RESEARCH_DECISION.md).
- Final suite: [`summary.jsonl`](../logs/semantic_validation_20260831T153536Z/summary.jsonl): 11 PASS, 0 FAIL, 2 SKIP_ENV, 1 BLOCKED_HW. Nested/current socket restrictions are environment results, not negative findings.
