# FRAMEWORK: PickNik `meta_quest_teleoperation`

**Status (2026-09-14): `BLOCKED_EXTERNAL_DEPENDENCY`**
(previous: `SOURCE_ONLY` / `SOURCE_DATAFLOW_CONFIRMED`)

Latest report: [`PICKNIK_QUESTLESS_CONVERGENCE.md`](../../results/PICKNIK_QUESTLESS_CONVERGENCE.md)
Run: `results/runs/picknik_questless_20260914T064253Z/`

## Identity

- Repository: `https://github.com/PickNikRobotics/meta_quest_teleoperation.git`
- Revision: `bbaef0762fdb0b429b8ea12a4ca65040748b41dd` (2026-08-12), worktree clean,
  matches `PINNED_REVISION` and `manifest.yaml` — re-verified 2026-09-14
- Local checkout: `semantic_validation/targets/meta_quest_teleoperation`
- `UnityProject/Assets/ROSPublishers.cs` SHA-256 `9fd803f080f5fd2c8ae1f01f1ffd1711f669f05da6a0d8a274cf5f95f454873a`
- XR frontend: **in repo** (Unity 6000.1.6f1, OpenXR + XRI 3.1.1 + XR Hands 1.5.0)
- Transport bridge: **external** — upstream `Unity-Technologies/ROS-TCP-Connector`
  (git URL in `Packages/manifest.json`), **not** a PickNik fork
- Downstream consumer: external MoveIt Pro Objective, not in this checkout

## Architecture

```text
Meta Quest 3 (Android OpenXR, Oculus Touch profile)
  -> XRI Default Input Actions (devicePosition/deviceRotation/trackingState/isTracked)
  -> tracked-pose driver, m_IgnoreTrackingState: 0
  -> Left/Right Controller GameObject Transform            [tracking state ENDS HERE]
  -> RosPublishers.Update() @ 1/60 s  -> PublishOdomAndTf()
  -> ROS-TCP-Connector  -> ros_tcp_endpoint
  -> /left_controller_odom, /right_controller_odom [nav_msgs/Odometry]
     /tf [tf2_msgs/TFMessage]
  -> MoveIt Pro Objective                                  [EXTERNAL]
```

## System Relevance

- Classification: **`HIGH_XR_ROS_CONTROL`**
- Why: a first-party industrial vendor's own Quest teleoperation app, with the
  full XR frontend in the repository. It is the population's clearest
  **white-box-frontend** case, the complement of Quest2ROS2's black-box frontend.

## Semantic Observability

| Axis | Finding | Evidence |
| --- | --- | --- |
| I1 tracking validity | **`DROPPED` at the `Transform → Odometry/TF` boundary.** `trackingState`/`isTracked` are wired into the tracked-pose driver of the exact GameObjects the publisher reads, then have no representation downstream. | `XR Origin (XR Rig).prefab:131,156,314,339`; `SampleScene.unity:1144-1145`; `ROSPublishers.cs:326-327,384,394-416` |
| I2 source identity | Left/right preserved by topic and `child_frame_id` (`:404,:415`). Parent `frame_id` is a constant `"quest"` (`:105`) — no reference space, no session generation. Controller-vs-hand binding is not represented. | `ROSPublishers.cs:34-43,105,404,415` |
| I3 source time | **`TRANSFORMED` (re-stamped).** `GetRosTime()` returns `DateTime.UtcNow` at publish time (`:367-380`), assigned at `:394`. No source sample time input, no age check, no sequence. Odometry and TF share one `HeaderMsg` instance (`:124`). | `ROSPublishers.cs:124,367-380,394` |
| I4 session/generation | Transport generation is handled (2 s registration gate, reset on reconnect: `:68-74,:174-186,:290-293`) but never *expressed* in the payload. No XR-session generation concept at all. | `ROSPublishers.cs:68-74,174-186,290-293` |
| I5 invalidation/re-arm | **No deadman, no clutch, no focus/pause invalidation on the publish path.** Once `_registered` flips true, publishing is unconditional at 60 Hz. No `OnApplicationFocus`/`OnApplicationPause` hook exists. | `ROSPublishers.cs:290-293,318-340`; repo-wide absence |
| Source visibility | **`FULL_SOURCE` XR frontend + `FULL_SOURCE` publisher**; consumer external. | — |

## Native Decisions

- Tracking gate: none on the publish path.
- Validity gate: none.
- Deadman/clutch: none in this app (button state is published as raw booleans;
  gating, if any, is the host-side behavior tree's).
- Freshness: none — the stamp is regenerated, which actively destroys freshness
  information rather than merely omitting it.
- Recovery: n/a.

## Control Depth

- Last auditable in-source boundary: `ros.Publish(odomTopicName, _odomMsg)` /
  `ros.Publish(tfTopicName, _tfMessage)` — `ROSPublishers.cs:405,416`.
- Original consumer: a MoveIt Pro Objective, outside the checkout.
- Physical driver dependency: none in this repository (it is the headset app).
- Classification achieved: **`TRANSPORT_ONLY`** — the transport backend has been
  executed; the framework's own publisher has not.

## Testbed Adaptation — status: **ATTEMPTED, BLOCKED**

| Question | Answer (2026-09-14, verified by execution) |
| --- | --- |
| Desktop Humble usable? | Yes. |
| `ros_tcp_endpoint` actually installed? | **Initially no** — the pre-existing `ros_env/ros2_ws` install is a broken `--symlink-install` egg-link (`ModuleNotFoundError: No module named 'ros_tcp_endpoint'`). Rebuilt non-symlinked from the vendored `Unity-Technologies/ROS-TCP-Endpoint@54c1a64` and then **run successfully**. |
| Unity editor present? | **Yes** — `6000.1.6f1` at `/home/cclab/Unity/Hub/Editor/6000.1.6f1/Editor/Unity`, with `AndroidPlayer` and `LinuxStandaloneSupport`. This **corrects** the earlier "no Unity editor" claim in `PICKNIK_HW_READY.md` / `PICKNIK_DEEP_VALIDATION.md`. |
| Unity editor runnable? | **No.** `No valid Unity Editor license found. Please activate your license.` / `Found 0 entitlement groups and 0 free entitlements`. Exit 1. Requires the operator's Unity account. |
| In-repo simulator / play-mode test? | **None.** 0 test assemblies, 0 test C# files. Even a licensed editor would need a harness-authored driver scene. |
| Production path preserved? | Yes — the pinned checkout was never written to; the Unity attempt used a scratch copy. |
| Replay injection boundary | The ROS-TCP socket — **downstream of all PickNik code**. `BOUNDARY_LIMITED_REPLAY`. |

## Quest-less Potential — partially achieved, on the wrong half

One run exists: `results/runs/picknik_questless_20260914T064253Z/`, three trials,
all in a `--network none` Humble container at `ROS_DOMAIN_ID=71`.

- 3600/3600 messages relayed, 0 loss, at 60 Hz, on the real
  `nav_msgs/Odometry` + `tf2_msgs/TFMessage` topics PickNik uses.
- Frozen-pose interval: 240 consecutive messages per controller carrying **one**
  pose while the ROS header stamp advanced **3.983 s**.
- Fixed-pose collision control: 3 of 4 streams byte-identical across a
  tracked ↔ untracked flip; the 4th 359/360 (single first-serialization outlier,
  disclosed in the report).

**This is `E2 SYNTHETIC_RUNTIME` about the transport backend, not about PickNik.**
It says the schema has nowhere to put tracking validity and that a regenerated
stamp hides staleness — it says nothing about PickNik's `Update()` loop, which
has never been executed.

## Future Quest Test

- T0: baseline, both controllers tracked, 10 s.
- T1 (decisive): occlude one controller 3–5 s **without** losing headset focus.
  Question: does the GameObject `Transform` freeze, infer/extrapolate, or reset —
  and does the 60 Hz Odometry/TF stream continue regardless?
- Side-band: `PickNikTrackingSidebandLogger.cs` records `isTracked`,
  `trackingState`, Transform, focus/pause and XR display state at 60 Hz. It never
  imports a ROS namespace and never calls `Publish()`.
- ROS side: `picknik_ros_observer.py` on
  `/left_controller_odom`, `/right_controller_odom`, `/tf` — **runtime-proven**
  as of this run.
- Analysis: `picknik_hw_analyze.py` (self-test 4/4 OK).
- Stop condition: 5 clean `valid → invalid → reacquired` intervals, or 20 min.
- Prerequisite that the harness cannot supply: **Unity editor license activation**.

## Research Value

- RQ: high and structurally distinctive — the only **vendor-authored, white-box
  XR frontend** in the population. It is the case where "the developer had the
  tracking bit in hand and it still did not reach ROS" can be shown at file:line.
- Invariants: I1 (dropped at an identifiable line), I3 (actively re-stamped),
  I2 frame provenance (constant `"quest"`), I5 (no gate at all).
- White-box/black-box: **`PRINCIPAL_WHITEBOX`**.
- Independent architecture: yes — Unity/ROS-TCP, distinct from Spes WebXR/WSS,
  from Quest2ROS2's external app, and from Docker_Teleop's bespoke TCP.
- Generality contribution: pairs with Quest2ROS2 to show the same ROS-side
  disposition arises whether or not the frontend is auditable.

## Weaknesses

- **Cannot be executed here.** The blocker is a commercial license entitlement,
  not a technical gap, and it gates every runtime claim about this framework.
- No in-repo tests or simulator, so there is no cheap questless path even with a
  licensed editor — a driver scene would have to be authored.
- The transport-backend run does not transfer: it bypasses 100% of PickNik's code.
- The final MoveIt Pro consumer is absent, so `NATIVE_CONSUMER_ACCEPTED` is
  unreachable from this checkout.

## Final Role

- **`PRINCIPAL_WHITEBOX`** for the XR-frontend-visible drop (source level)
- **`AUXILIARY_WIRE`** for the `ros_tcp_endpoint` boundary (now executed)

## Priority

**A** — highest-value *source* evidence in the population, but runtime-blocked
behind an operator action (Unity license). Do not spend further autonomous effort
on runtime here until that license exists; the source claims are already at their
ceiling.
