# FRAMEWORK: HRI-EU/reachy-vr-quest

## Identity

- Repository: `https://github.com/HRI-EU/reachy-vr-quest.git`
- Revision: `242120ee9e356e4a4f2117ee56c8b340c9b7ec64` (2026-05-26, branch `main`)
- Local checkout: `semantic_validation/targets/reachy_vr_quest`
- Frontend engine: **Unity `6000.3.9f1`** + Meta XR SDK `201.0.0` + Meta Movement
  (body tracking), Quest target
- Source map: `SOURCE_MAP.md`; pinned revision: `PINNED_REVISION`

## Architecture

```text
Quest (Meta Movement body tracking via MetaSourceDataProvider)
  -> MetaBodySkeletonProvider          (IsPoseValid + 0.5 s stability debounce)
  -> ReachyHeadCommandBuilder          (head matrix, antennas, body yaw)
  -> ReachyDaemonTargetAdapter         (yaw -> radians, row-major 4x4)
  -> ReachyDaemonTargetWebSocketClient (WebSocketSharp worker thread)
  -> ws://<daemon>:8000/api/move/ws/set_target   [Reachy daemon; robot-facing]
```

Not a ROS stack. It expands the comparison family rather than the ROS
population: a direct Unity-to-robot-daemon WebSocket control path.

## System Relevance

- Classification: **`DIRECT_ROBOT_CONTROL_PATH`** (potentially robot-facing;
  never contacted in this project)
- The endpoint is a real control API, so this is one of the few non-ROS
  frameworks in the population where the last auditable boundary is an actual
  robot command channel rather than telemetry.

## Semantic Observability

| Axis | Finding | Evidence |
| --- | --- | --- |
| I1 tracking validity | **Computed and then discarded.** `MetaSourceDataProvider.IsPoseValid()` is debounced by `validBodyTrackingDelay = 0.5f` into `_poseStable`, combined in `IsBodyTrackingActive()` — which has **zero call sites in the entire repository**. It is also absent from `IReachySkeletonProvider`, so the publisher (which holds the provider as that interface) cannot reach it. Pose transforms are updated unconditionally regardless of `_poseStable`. | `MetaBodySkeletonProvider.cs:36`, `:86-97`, `:99-110`, `:145-148`; `IReachySkeletonProvider.cs:5-11`; `ReachyHeadCommandPublisher.cs:28` |
| I2 source identity | `TRANSFORMED`. Per-hand `IsLeftHandTracked()`/`IsRightHandTracked()` affect **antenna values only**, never whether a payload is sent; both return `true` when the `OVRHand` reference is null. No device/session id on the wire. | `ReachyHeadCommandBuilder.cs:196`, `:211`; `MetaBodySkeletonProvider.cs:137`, `:142` |
| I3 source time / freshness | **Absent.** The daemon DTO carries `target_head_pose.m`, `target_antennas`, `target_body_yaw` and nothing else — no timestamp, no sequence. A target queued before a disconnect is indistinguishable from a fresh one when the 5-deep queue drains. | `ReachyDaemonPayloadDtos.cs:15-22`; client `:137-149`, `:436+` |
| I4 session / generation | Internal only. `_workerGeneration` correctly invalidates stale transport callbacks but is never transmitted. | `ReachyDaemonTargetWebSocketClient.cs:255`, `:287`, `:394`, `:411`, `:421`, `:457-459` |
| I5 invalidation / re-arm | **Absent.** The worker loop exits on close and does not auto-reconnect; the publisher coroutine keeps building and enqueueing payloads while the transport is down; a manual `StartClient()` resumes sending with no re-arm and no validity condition. | `:308-361`, `:392-431`, `:239`; `ReachyHeadCommandPublisher.cs:136-147` |
| Source visibility | **`FULL_SOURCE`** for all application/control/transport logic. Meta XR SDK and Movement SDK are external packages, not vendored. | `Packages/manifest.json`; `Assets/Oculus` is 20 KB of settings only |

## Native Decisions

The send decision is `ReachyHeadCommandBuilder.TryBuildPayload`
(`:27-58`), whose only failure conditions are **transform presence and
geometric degeneracy**: provider null or `!SkeletonReady` (`:27-28`), missing
`CenterCamAnchor` (`:30-31`), missing head reference transforms (`:33-34`),
missing shoulders (`:36-40`), degenerate shoulder separation (`:42`, `:103-104`),
degenerate head frame (`:49-58`). `SkeletonReady` is a one-shot init latch that
is set `true` even on its two failure paths
(`MetaBodySkeletonProvider.cs:168-172`, `:192-196`).

`ReachyHeadCommandPublisher.PublishOnce()` sends whenever the build succeeded
(`:112-134`, send at `:132`); `PublishRoutine` waits once for `SkeletonReady`
then loops forever at `Config.sendRateHz` (`:136-147`).

**Conclusion (E1): the tracking-validity gate does not control the outgoing
network command on this revision.** This is the framework's principal research
value — a computed-but-unconsumed validity signal on a path whose endpoint is a
real robot daemon API.

## Control Depth

- Last auditable boundary in-repo: `TRANSPORT_SENT` to
  `/api/move/ws/set_target`.
- Original consumer: the Reachy daemon — **not in this repository, never
  contacted, and its own re-validation behaviour is entirely unknown.**
- Physical driver dependency: none in-repo, but the configured endpoint is
  robot-facing. Never point this client at a real daemon in this project.

## Testbed Adaptation

- Inert endpoint: **built and executed** —
  `semantic_validation/harness/reachy_inert_target_endpoint.py`. Loopback-only
  (hard bind guard refuses non-loopback), stdlib RFC 6455, no outbound socket,
  every frame logged verbatim as `LOGGED_ONLY_NOTHING_COMMANDED`. Self-test
  `reachy_inert_endpoint_selftest.py` recorded 21/21 frames across 2
  connections including a reconnect.
- Sending side: **not runnable here.** See blocker below.
- In-repo `Tools/mock_reachy_router.py` is a ZMQ ROUTER for the legacy
  `ReachyZmqDealerClient`, not for the daemon WebSocket path.

## Hard Blocker (actual execution attempt, 2026-09-14)

`Unity 6000.1.6f1 -batchmode -nographics -quit -runTests` on a scratch copy of
the project exited `1` in 8 s:

```text
[Licensing::Client] Error: Code 404 ... Found 0 entitlement groups and 0 free
  entitlements matching requested entitlement ids
Pro License: NO
No valid Unity Editor license found. Please activate your license.
```

Compounding blockers: only `6000.1.6f1` is installed while the project pins
`6000.3.9f1` (`ProjectSettings/ProjectVersion.txt`), and there is no `Library/`
package cache for `com.meta.xr.sdk.all: 201.0.0` / the git-sourced
`com.meta.xr.sdk.movement`. Logs:
`semantic_validation/results/runs/reachy_vr_quest_20260914T064240Z/unity_batchmode_attempt.log`.

## Research Value

- RQ: **strong**. A real Meta Movement validity bit plus a real 0.5 s debounce
  are computed and then not consulted by the sender, on a direct robot-daemon
  control path. This is a sharper instance of the study's central pattern than
  any telemetry-only bridge can provide.
- Independent architecture: yes — non-ROS, Unity/WebSocketSharp, direct daemon
  API; distinct lineage from the Unity/ROS-TCP and WebXR families.
- White-box: yes for all application logic.
- Positive control: **candidate, not yet demonstrated** — demonstrating it
  requires driving the pinned client, which is currently blocked.

## Weaknesses

- No runtime evidence of any kind for the client; everything above is E1.
- The daemon's own validation is unknown, so no end-to-end claim is possible
  even if the client were run.
- Unity licence + version + SDK package graph make this the most
  execution-expensive framework in the population.

## Final Role

- **`PRINCIPAL_NON_ROS_COMPARATOR`**
- **`ADJACENT_NON_ROS`**: yes.

## Priority

**B** — high claim value, high execution cost. Worth a slot only if a licensed
Unity `6000.3.9f1` with the Meta packages becomes available; at that point the
inert endpoint is already built and the experiment is a short one (valid pose,
invalid pose, recovery delay, reconnect, all against `127.0.0.1:8000`).

## Status (2026-09-14)

**`BLOCKED_EXTERNAL_DEPENDENCY`.**
Full report: `semantic_validation/results/REACHY_INERT_ENDPOINT_RUNTIME.md`.
Deliverable achieved: inert endpoint built, executed, and proven inert.
Gate characterisation stands at **`E1 SOURCE_DATAFLOW_CONFIRMED`** with the
zero-call-site finding for `IsBodyTrackingActive`. No `TRANSPORT_SENT` and no
downstream consequence may be claimed for this framework.
