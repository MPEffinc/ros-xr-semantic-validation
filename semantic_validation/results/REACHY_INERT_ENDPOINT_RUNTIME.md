# Reachy VR Quest — Inert Daemon Endpoint and Client-Side Blocker

## Scope

- Upstream repository: `HRI-EU/reachy-vr-quest`
- Pinned revision: `242120ee9e356e4a4f2117ee56c8b340c9b7ec64` (2026-05-26, branch `main`)
- Local checkout: `semantic_validation/targets/reachy_vr_quest`
- Run id: `reachy_vr_quest_20260914T064240Z`
- Evidence level: **`E1 SOURCE_DATAFLOW_CONFIRMED`** for the gate/transport
  findings; the only executed component is a research-authored inert endpoint,
  whose self-test is explicitly **not** framework evidence.
- **No Reachy daemon, no robot, no Quest, no APK, no real endpoint of any kind
  was contacted.** The only network activity was loopback traffic between two
  research-authored processes on `127.0.0.1:8000`.

This is not a ROS stack. Its command path is Unity C# -> WebSocket -> the
Reachy daemon HTTP/WS API.

## 1. Inert local endpoint (built and executed)

`semantic_validation/harness/reachy_inert_target_endpoint.py` implements a
stand-in for the daemon target endpoint the pinned client talks to:

- path `/api/move/ws/set_target`
  (`ReachyDaemonTargetWebSocketClient.cs:18` `DefaultTargetPath`; pinned config
  default `Assets/Config/ReachyTeleopConfig.asset:15`
  `daemonTargetWebSocketUrl: ws://localhost:8000/api/move/ws/set_target`);
- RFC 6455 handshake and frame decode implemented on the Python standard
  library — **no client library, no outbound socket of any kind**;
- every received frame is written verbatim to JSONL with wall and monotonic
  time, connection id, per-connection and global sequence, byte length, raw
  text and parsed JSON, each tagged
  `action: "LOGGED_ONLY_NOTHING_COMMANDED"`;
- a hard bind guard refuses any non-loopback bind address.

Bind guard, executed:

```text
$ reachy_inert_target_endpoint.py --host 0.0.0.0 --port 8099 ...
REFUSED: bind host 0.0.0.0 is not loopback. This endpoint may only ever be
reachable from the local machine.
bind-guard rc=1
```

### Endpoint self-test (harness-only evidence)

`semantic_validation/harness/reachy_inert_endpoint_selftest.py` sends frames
shaped as the pinned daemon DTO (`ReachyDaemonPayloadDtos.cs:15-22`:
`target_head_pose.m` 16 floats, `target_antennas`, `target_body_yaw`).

| Step | Result |
| --- | --- |
| connect to `/api/move/ws/set_target` | `HTTP/1.1 101 Switching Protocols`, `path_matches_pinned_target_path: true` |
| 20 frames at 20 Hz | 20/20 recorded, 1.0036 s window |
| clean close | `WS_CLOSE`, `frames_on_connection: 20` |
| reconnect + 1 frame | second `101`, frame recorded as `global_frame_seq: 21` |
| endpoint totals | `connections: 2, frames: 21, bytes: 3589, http_requests: 0` |

**Provenance warning, stated in the harness file itself:** these frames are
`SYNTHETIC_HARNESS_AUTHORED_NOT_PINNED_UNITY_CLIENT`. This step proves the
endpoint is a working, inert, loopback-only recorder. It proves **nothing**
about the pinned client's gate behaviour and must never be cited as Reachy
runtime evidence.

## 2. Sending side: what it is, and the hard blocker

The sending side is **Unity C#** (`Assets/Scripts/Runtime/**/*.cs`,
`MonoBehaviour`-derived, depending on `UnityEngine`, Meta Movement SDK, OVR
plugin types, `Newtonsoft.Json` and `WebSocketSharp`). It cannot be compiled or
executed outside a Unity editor/player.

An actual execution attempt was made, not assumed. The project was copied to a
scratch directory (pinned worktree untouched) and driven in batch mode:

```bash
/home/cclab/Unity/Hub/Editor/6000.1.6f1/Editor/Unity \
  -batchmode -nographics -quit -projectPath <scratch copy> \
  -testPlatform EditMode -runTests -testResults test_results.xml
```

Exit code `1` after 8 s. Exact terminal output from
`results/runs/reachy_vr_quest_20260914T064240Z/unity_batchmode_attempt.log`:

```text
[Licensing::Module] Error: Access token is unavailable; failed to update
[Licensing::Client] Error: Code 404 while processing request
  (status: Found 0 entitlement groups and 0 free entitlements matching
   requested entitlement ids)
[Licensing::Module] Error: 'com.unity.editor.headless' was not found.
Pro License: NO
No valid Unity Editor license found. Please activate your license.
```

Three independent blockers, in order of hardness:

1. **No activated Unity Editor licence on this machine.** The editor exits
   before opening the project. `~/.config/unity3d/Unity/licenses/packages` is
   empty; no `.ulf` is present. Activation requires user credentials and is
   outside this session's mandate.
2. **Editor version mismatch.** Only `6000.1.6f1` is installed
   (`/home/cclab/Unity/Hub/Editor`); the project pins `6000.3.9f1`
   (`ProjectSettings/ProjectVersion.txt`). Opening it with `6000.1.6f1` would
   be a downgrade the editor does not support, and any upgrade path rewrites
   pinned project files.
3. **Unresolvable package graph without network package resolution.** No
   `Library/` package cache exists (`.gitignore:2`), and
   `Packages/manifest.json` requires `com.meta.xr.sdk.all: 201.0.0` plus
   `com.meta.xr.sdk.movement` from a GitHub URL. `Assets/Oculus` is 20 KB of
   settings assets only — the SDK is not vendored.

Therefore the source-side validity gate **could not be driven against the inert
endpoint**, and no runtime claim about it is made. The EditMode test suite
under `Assets/Tests/Editor/` (including `ReachyBatchTestRunner.cs`) is likewise
unreachable for the same reason.

## 3. Source-only characterisation of the gate logic (E1)

Re-verified against the pinned revision, with line citations.

### 3.1 `IsPoseValid`, the stability delay, and provider readiness

`Assets/Scripts/Runtime/Tracking/MetaBodySkeletonProvider.cs`:

- `:36` `[SerializeField] private float validBodyTrackingDelay = 0.5f;`
- `:86-97` each `Update()`: `bool providerValid = _source.IsPoseValid();`
  (Meta Movement `MetaSourceDataProvider`). While valid and not yet stable the
  timer accumulates `Time.smoothDeltaTime`; at `>= validBodyTrackingDelay`,
  `_poseStable = true` (`:91`). Any invalid frame resets both immediately
  (`:95-96`). This is a genuine 0.5 s debounce with instantaneous invalidation.
- `:99-110` — **the pose is applied to the runtime transforms unconditionally**,
  outside that branch. `_poseStable` does not gate `ApplyPoseToRuntimeTransforms`
  or `ApplyHandStitch`.
- `:145-148` `IsBodyTrackingActive() => _source != null && _source.IsPoseValid()
  && _poseStable;` — the combined validity + stability predicate.
- `:152-205` `SkeletonReady` is a one-shot initialisation latch. It is set
  `true` even on the two failure paths: provider not found (`:168-172`) and
  skeleton-pose timeout (`:192-196`).

### 3.2 The decisive finding: the validity gate has no call sites

A repository-wide grep for `IsBodyTrackingActive` returns **exactly one hit —
its own definition** at `MetaBodySkeletonProvider.cs:145`. Nothing calls it:
not the builder, not the publisher, not the transport, not the tests, not the
scenes.

It cannot be called through the abstraction either:
`Assets/Scripts/Runtime/Reachy/IReachySkeletonProvider.cs:5-11` declares only
`SkeletonReady`, `TryGetTransform`, `IsLeftHandTracked`, `IsRightHandTracked`.
The publisher holds the provider **as that interface**
(`ReachyHeadCommandPublisher.cs:28`), so `IsPoseValid`/`_poseStable` are not
reachable from the send path at all.

Likewise `_poseStable` is written at `:91`, `:96`, `:154` and read at exactly
one place, `:147` — inside the uncalled method.

### 3.3 What actually gates the outgoing WebSocket command

`ReachyHeadCommandBuilder.TryBuildPayload` returns `false` only for:

| Check | Line |
| --- | --- |
| `provider == null \|\| !provider.SkeletonReady` | `:27-28` |
| `CenterCamAnchor` transform missing | `:30-31` |
| head reference transforms missing | `:33-34` |
| either shoulder transform missing | `:36-40` |
| degenerate shoulder geometry (`sqrMagnitude < 1e-6`) | `:42`, `:103-104` |
| degenerate head reference frame | `:49-58` |

All are **presence and geometry** checks. None consults tracking validity.

`IsLeftHandTracked()` / `IsRightHandTracked()` are consulted only at
`ReachyHeadCommandBuilder.cs:196` and `:211`, and only to decide whether an
**antenna angle** is computed; when false the antenna value stays at its
default and the payload is still built and sent. Both also return `true` when
the corresponding `OVRHand` reference is null
(`MetaBodySkeletonProvider.cs:137`, `:142`).

`ReachyHeadCommandPublisher.PublishOnce()` (`:112-134`) sends whenever
`TryBuildPayload` succeeded: it serialises via `ReachyDaemonTargetAdapter.ToJson`
(`:118-119`) and calls `sender?.SendMessageToServer(json)` at `:132`.
`PublishRoutine` (`:136-147`) waits once for `SkeletonReady` and then calls
`PublishOnce()` forever at `Config.sendRateHz`, with no further condition.

**Source-level conclusion (E1, not runtime):** on the pinned revision the
`IsPoseValid()` + 0.5 s stability result does **not** control the outgoing
`/api/move/ws/set_target` command. Once `SkeletonReady` latches and the required
transforms exist, payloads are built from whatever pose values the runtime
transforms currently hold — which are updated unconditionally at
`MetaBodySkeletonProvider.cs:99-110` — and are sent at the configured rate.
This is a computed-but-unconsumed semantic signal, structurally similar to the
`left_valid`/`right_valid` pattern already recorded for VR-hand-bridge, but
here the discarded signal is a *real* Meta Movement validity bit plus a real
debounce, not a null check.

### 3.4 Transport lifecycle (source only)

`ReachyDaemonTargetWebSocketClient.cs`:

- `:137-149` `SendMessageToServer` enqueues into a bounded queue
  (`maxQueuedMessages = 5`, `:31`), evicting the **oldest** when full; it never
  inspects payload content.
- `:308-361` the worker loop drains to the newest payload
  (`TryDequeueLatestOutgoing`, `:436+`) and sends it.
- `:392-431` `OnOpen`/`OnError`/`OnClose` only flip `_isAlive`/`_isConnecting`
  and raise `ConnectionStateChanged`. The worker loop exits on close and
  **does not auto-reconnect**; a restart requires `StartClient()` (`:239`),
  reached from `Start()` when `autoStart` (`:93-97`, default `false`, `:26`) or
  from `TrySetEndpoint` (`:151-171`).
- The publisher's coroutine keeps calling `PublishOnce()` while the transport is
  down, so payloads accumulate in the 5-deep queue and the newest survivor is
  sent on the next successful send. There is no source timestamp, sequence
  number, or generation marker in the daemon DTO
  (`ReachyDaemonPayloadDtos.cs:15-22`), so the receiver cannot distinguish a
  fresh target from one queued before a disconnect.

## 4. Invariant disposition (E1)

| Invariant | Disposition | Basis |
| --- | --- | --- |
| I1 tracking validity | **`DROPPED` at the send boundary** — computed (`IsPoseValid` + 0.5 s debounce) but never consulted by any sender | `:86-97`, `:145-148` with zero call sites; `IReachySkeletonProvider.cs:5-11` |
| I2 source identity | `TRANSFORMED` — per-hand tracking affects antenna values only; no device/session id on the wire | builder `:196`, `:211`; DTOs `:15-22` |
| I3 source time / freshness | `DROPPED` — no timestamp or sequence in the payload; a queued pre-disconnect target is indistinguishable from a fresh one | `ReachyDaemonPayloadDtos.cs:15-22`; client `:137-149`, `:436+` |
| I4 session / transport generation | `PRESERVED` internally only — `_workerGeneration` guards stale callbacks (`:255`, `:287`, `:394`, `:411`, `:421`, `:457-459`) but is never sent to the daemon | as cited |
| I5 invalidation / re-arm | `DROPPED` — no auto-reconnect, and on manual restart publishing resumes with no re-arm and no validity condition | `:308-361`, `:392-431`; publisher `:136-147` |

Downstream consequence: **`UNKNOWN`.** No frame from the pinned client was ever
sent anywhere. The inert endpoint's 21 recorded frames came from the research
self-test only and therefore support no disposition at all.

## 5. What was not observed

- The pinned Unity client never ran; no `TRANSPORT_SENT` evidence exists for it.
- Whether the Reachy daemon itself re-validates a target (freshness, limits,
  watchdog) is entirely unknown — the daemon was never contacted and is not in
  this repository. Any absence noted above is an absence **on the client side
  only** and says nothing about end-to-end system behaviour.
- No Quest, no APK build, no Meta Movement runtime, no body-tracking data.

## Evidence files

- `semantic_validation/harness/reachy_inert_target_endpoint.py`
- `semantic_validation/harness/reachy_inert_endpoint_selftest.py`
- `semantic_validation/results/runs/reachy_vr_quest_20260914T064240Z/inert_endpoint.jsonl`
- `.../selftest.json`, `.../selftest_stdout.log`, `.../endpoint_stdout.log`
- `.../bind_guard_check.log`
- `.../unity_batchmode_attempt.log`, `.../unity_batchmode_attempt_console.txt`
- `.../unity_installed_editors.txt`

## Status

**`BLOCKED_EXTERNAL_DEPENDENCY`** — the inert endpoint deliverable was built
and executed, but the sending side is Unity C# and the editor refuses to start
with `No valid Unity Editor license found`, compounded by a pinned-version
mismatch and an unvendored Meta XR SDK package graph. The gate characterisation
therefore stands at `E1 SOURCE_DATAFLOW_CONFIRMED`, with the concrete,
citable result that the `IsPoseValid` + 0.5 s stability gate has **zero call
sites** and cannot reach the outgoing WebSocket command path on this revision.
