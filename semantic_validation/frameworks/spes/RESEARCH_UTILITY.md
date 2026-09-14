# FRAMEWORK: Spes (SpesRobotics/teleop)

**Finalized questless status: `QUESTLESS_RUNTIME_COMPLETE`** (assigned 2026-09-14).

## Identity

- Repository: `https://github.com/SpesRobotics/teleop.git`
- Revision: `c5d808155a87b584d6147a5943d4b87c34c92db0` (branch `main`), worktree clean
- Local checkout: `semantic_validation/targets/spes_teleop`
- XR frontend: **in repo** — a WebXR browser page served by the package itself
  (`teleop/index.html`), loaded in the headset browser. There is no Unity app and no APK.
- Transport: WSS (uvicorn + FastAPI) inside the same package (`teleop/__init__.py:298-311`)

## Architecture

```text
Meta Quest 3 browser, WebXR session                    [IN REPO: teleop/index.html]
  XRFrame.getPose(targetRaySpace, referenceSpace)      [index.html:264-278,283-388]
  controller-or-viewer selection, then JSON packet     [index.html:334-380]
  -> WSS /ws                                           [IN REPO: teleop/__init__.py:298-311]
  -> Teleop.__update: move gate, jump gate, anchors, target maths
                                                       [teleop/__init__.py:220-285]
  -> Teleop.__notify_subscribers(pose, message)        [teleop/__init__.py:216-218]
       |
       +-- application callback                        <- the package's own terminus
       +-- OPTIONAL upstream ROS 2 module              [IN REPO: teleop/ros2/__main__.py]
       |     publishes PoseStamped "target_frame" (:88,:141) + TF base_link->teleop_target (:103-114)
       |     gated on /current_pose from a robot (:121,:143-145)
       +-- RESEARCH adapter                            [semantic_validation/harness/spes_ros_callback_adapter.py]
```

## System Relevance

- Classification: **`HIGH_XR_ROS_CONTROL` as a motivating case, `NOT_A_NATIVE_XR_TO_ROS_COUNT`.**
- Roles: **`MOTIVATING_XR_CONTROL_CASE`** and **`RESEARCH_ADAPTED_ROS_PROPAGATION_CASE`**, plus
  **`UPSTREAM_OPTIONAL_ROS_MODULE_EXECUTED`** as of 2026-09-14.
- Why it must not be counted as a native XR->ROS implementation: the package's primary product is a
  callback, not a ROS stream; its ROS module is an optional example that cannot publish without a
  robot on `/current_pose`; and every runtime result obtained so far injects a synthetic packet
  *after* the WebXR frontend, so no native XR tracking decision has ever been exercised at the ROS
  boundary.

## Semantic Observability

| Axis | Finding | Evidence |
| --- | --- | --- |
| I1 tracking validity | **DROPPED before serialization.** The frontend picks a controller transform or a viewer fallback and serializes only pose/`move`/gripper/scale/device — no tracking field. Confirmed on actual Quest 3 hardware: during a controller-occlusion interval the pose stayed non-null with `emulatedPosition=true`, `source=CONTROLLER`, and the production packet omitted that semantic. | `index.html:334-380`; `results/SPES_QUEST_HW_RESULT.md`, `SPES_HW_QUANTITATIVE_SUMMARY.md` |
| I2 source identity | **Absent from the packet.** Handedness/viewer-fallback distinction exists in the frontend but is not serialized. | `index.html:334-355`, `:355-380` |
| I3 source time | **DROPPED, now confirmed from two independent publishers.** The packet has no frame time; the upstream ROS module re-stamps with `node.get_clock().now()`; the research adapter does the same and records `source_timestamp_preserved: false`. | `teleop/ros2/__main__.py:131,:103`; `harness/spes_ros_callback_adapter.py:83,110` |
| I4 session/generation | **Not bound to control state.** WSS connect/disconnect is observable server-side, but the relative/absolute anchors are not generation-bound. | `teleop/__init__.py:258-268`; `results/SPES_RECONNECT_RESULT.md` |
| I5 invalidation / re-arm | **`move` is the only explicit control flag; it is not a tracking invalidation.** `move=false` clears anchors and still notifies subscribers (`:231-235`) but no tracking/session invalidation field exists. On hardware, recovery from the emulated-tracking interval occurred 5/5 without any user release/re-press. | `teleop/__init__.py:231-235`; `results/SPES_QUEST_HW_RESULT.md` |
| Only native gate on the control path | **Pose-jump protection** (0.05 m / 35 deg). It is a continuity heuristic, not a tracking-validity gate. | `teleop/__init__.py:247-256` |
| Source visibility | **`FULL_SOURCE`** — frontend, transport, control maths and optional ROS module are all in repo. | — |

## Control Depth

- Last in-package boundary without a robot: `Teleop.__notify_subscribers` (`teleop/__init__.py:285`).
- Upstream ROS boundary: `PoseStamped` on `target_frame` plus TF `base_link -> teleop_target`
  (`teleop/ros2/__main__.py:141`, `:114`).
- Original downstream consumer: **not present in the repository** — upstream expects an external arm
  controller to consume `target_frame` and to publish `/current_pose`. `NATIVE_CONSUMER_UNAVAILABLE`.
- No physical driver, actuator, or robot has been, or may be, started by this project.

## Evidence ledger for Spes

| Result | Boundary | Level | Status |
| --- | --- | --- | --- |
| `SPES_QUEST_HW_RESULT.md` / `SPES_HW_QUANTITATIVE_SUMMARY.md` / `SPES_HW_REANALYSIS.md` | actual Quest 3 -> actual Spes server callback | hardware evidence **below E5** (no ROS boundary included) | **CANONICAL — preserve, do not regenerate.** 5/5 valid trials, `HW_EMULATED_CONTINUES` 5/5, recovery 5/5 without user re-arm |
| `SPES_RECONNECT_RESULT.md`, `SPES_FRESHNESS_RESULT.md`, `SPES_CONTROL_STATE_RESULT.md` | synthetic WSS -> pinned server | E2 `BOUNDARY_LIMITED_REPLAY` | complete |
| `SPES_INSTRUMENTATION_INTEGRITY.md`, `SPES_SEMANTIC_COLLISION.md`, `SPES_CLASSIFIER_REGRESSION.md`, `SPES_NETWORK_COMPOSITION.md` | instrumentation / analysis discipline | supporting | complete |
| **`SPES_ROS_PI_INTEGRATION.md` (new, 2026-09-14)** | synthetic WSS -> pinned server -> ROS 2 publisher -> actual Fast DDS -> physical Raspberry Pi sink | E2 `BOUNDARY_LIMITED_REPLAY`, consequence `PI_RECEIVED` | **Run A (research adapter) 30/30; Run B (pinned upstream `teleop.ros2`) 30/30** |

## What the 2026-09-14 session closed

The three items `results/NEXT_PHASE_STATUS.md` recorded as **not executed** because the Docker
daemon socket was inaccessible are now executed:

1. Synthetic Spes callback -> ROS publisher -> actual ROS 2/DDS: **executed**, twice, with two
   different publishers.
2. Pi reception for Spes specifically: **executed** — 30/30 on both runs, on the physically
   separate Raspberry Pi `rosxr` over the dedicated 10.10.10.0/24 Ethernet.
3. Correlation of `run_id` / local event ID / server update index / callback and publish monotonic
   times / ROS header stamp against Pi reception: **executed** — 30/30 matched, 0 missing, 0 pose
   mismatches, with the honest limitation that `PoseStamped` carries no in-band correlation ID and
   the join is by header stamp, ordering and payload, not by an identifier.

Docker access works via `sg docker -c '<command>'`; no socket, group, or system configuration was
modified. The preflight's `docker_daemon_access` check was updated to try that path and to record
which path succeeded.

## Quest hardware readiness (re-verified 2026-09-14)

`run_spes_hardware_preflight.py` `PASS` on all nine checks; `start_quest_experiment.sh` /
`status_quest_experiment.sh` / `stop_quest_experiment.sh` and `probe_spes_server.py` all executed
and passed. Trials and stop conditions are fixed in `EXPERIMENT_T1.md` (five valid raw transitions;
3-5 s degradation without focus loss; 1-2 s hold; 5-10 s post-recovery observation).

**One remaining development item, stated honestly:** the Quest orchestration runs the WSS server
and observer but does **not** yet attach a ROS publisher. Joining the hardware path to the ROS/Pi
path needs `SpesRosCallbackAdapter` wired into `spes_hardware_server.py` the way
`harness/spes_ros_pi_smoke.py:80-88` does, with that server run inside the ROS container. It is
small and fully specified, but it has not been executed.

## The one Quest-only open question

Whether an **actual** Quest 3 emulated-tracking interval propagates all the way to the physically
separate ROS endpoint with no distinguishing marker — i.e. the already-proven hardware half joined
to the now-proven ROS/DDS/Pi half in a single execution. Nothing else blocks it.

## Claim discipline reminder

`PI_RECEIVED != NATIVE CONSUMER ACCEPTED`. The Pi sink's `accept_decision` is hardcoded
`ACCEPTED_NO_SEMANTIC_GATING`. Do not describe any Spes result using `vulnerable`, `unsafe`,
`secure`, or `fail-safe`; state the E-level, the exact boundary, and the unresolved condition
instead.
