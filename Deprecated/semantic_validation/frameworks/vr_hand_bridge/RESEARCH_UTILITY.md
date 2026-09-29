# FRAMEWORK: VR-hand-bridge-ROS2

## Identity

- Repository: `https://github.com/mahmoud-maan/VR-hand-bridge-ROS2.git`
- Revision: `a5da3e09def32b2f0dc69d4199493243f40e1440` (2026-05-26), worktree clean, single commit
- Local checkout: `semantic_validation/targets/vr_hand_bridge_ros2`
- Frontend engine: **Godot 4.6** (`android/.build_version` → `4.6.rc1.mono`) with OpenXR
- Note: `README.md:89` instructs cloning `github.com/mahmoud-maan/vr-hand-bridge.git`, which is not this repository's own origin — a lineage/naming inconsistency worth recording.

## Architecture

```text
Quest (OpenXR via Godot OpenXR Vendors plugin)
  -> main.gd: XRServer.find_interface("OpenXR"), is_initialized()
  -> ws_streamer.gd: XRController3D node transforms
  -> WebSocket, plaintext JSON, ws://<host>:8765
     {"left_hand":{"pos":[x,y,z],"quat":[x,y,z,w]}, "right_hand":{...}}
  -> hand_ws_publisher.py (websockets + rclpy)
  -> /left_hand_pose, /right_hand_pose  [geometry_msgs/PoseStamped, frame_id "world"]
  -> hand_pose_subscriber.py (console print) and rviz2
```

## System Relevance

- Classification: **`XR_ROS_BRIDGE_ONLY`**
- Why: the pipeline terminates at a printing subscriber and RViz. `README.md:5` states it is "intended as a foundation for downstream applications such as robot teleoperation" — actuation is explicitly future work. XR input never influences a robot-control decision at this revision.

## Semantic Observability

| Axis | Finding | Evidence |
| --- | --- | --- |
| I1 tracking validity | **Absent, and the appearance of a gate is misleading.** `left_valid`/`right_valid` are set unconditionally to `true` whenever the node reference is non-null, then used in the send condition. No `XRController3D` tracking API (`get_tracker()`, `get_is_active()`, pose-validity flag) is consulted. Repo-wide grep for validity tokens: zero hits. | `ws_streamer.gd:22-38` (assignment), `:40` (gate) |
| I2 source identity | Left/right preserved as distinct JSON keys and distinct topics. No device id, session token, or handshake identity. | `ws_streamer.gd:42-51`; `hand_ws_publisher.py:67-68` |
| I3 source time | **Never carried.** No timestamp in the payload at all. `header.stamp` is assigned the ROS host clock at construction; `frame_id` unconditionally `"world"`. The subscriber never reads `header.stamp`. | `ws_streamer.gd:42-51`; `hand_ws_publisher.py:41-42`; `hand_pose_subscriber.py:10-30` |
| I4 session/generation | **Absent.** Disconnect is caught and logged only; no state to reset, no reconnect continuity check. | `hand_ws_publisher.py:83-91` |
| I5 invalidation/recovery | **Absent.** No watchdog; if the headset stops, the last `PoseStamped` simply remains the last value published on the topic. | absence confirmed by full read |
| Source visibility | **`FULL_SOURCE`** for app logic (GDScript) and the ROS bridge. The Godot OpenXR Vendors runtime binaries are git-ignored and fetched externally. | `.gitignore:8-9` |

## Native Decisions

None of research interest: no tracking gate, no validity gate, no deadman, no freshness check, no session handling, no recovery policy.

## Control Depth

- Last auditable downstream boundary: **`ROS_PUBLISHED`** (`/left_hand_pose`, `/right_hand_pose`), consumed only by a console printer and RViz.
- Original consumer: none for control.
- Physical driver dependency: **none anywhere.**
- Classification: **`TELEMETRY_ONLY` / `ROS_PUBLISHED`**.

## Testbed Adaptation

- Desktop Humble usable: yes; the ROS side is two small rclpy nodes.
- Can publish to Pi: yes trivially.
- Simulator: none; no in-repo synthetic WebSocket client, so a ~20-line client would have to be authored.
- Inert stub: unnecessary — the pipeline is inherently robot-free.
- Replay injection boundary: the WebSocket JSON payload, upstream of everything on the host side. But since the host side contains no semantic logic, an upstream-faithful replay would demonstrate essentially nothing beyond transport.

## Quest-less Potential

Low research yield. Everything the host side does is already fully determined by reading 60 lines of Python. Running it would confirm only that a stampless payload gets a host-clock stamp.

## Future Quest Test

Not worth a Quest session slot on its own. Its one distinctive property — a **Godot OpenXR** frontend rather than Unity or WebXR — would only matter if the study wanted to claim XR-runtime-family breadth, and even then the app performs no validity handling to observe.

## Research Value

- RQ: weak on control semantics; useful only as evidence about the **XR-runtime family distribution** in the public population (Godot OpenXR exists alongside Unity/Meta, WebXR, OpenVR, PICO).
- Invariants: I1/I3/I4/I5 all absent — which is itself a data point about how thin many public "XR→ROS bridge" projects are.
- White-box: yes.
- Independent architecture: yes by transport (Godot + WebSocket JSON), but with no control consumer it cannot count toward a control-path generality claim.
- Positive control: **no** — absence of a gate in a system that never commands anything is not evidence about gating design.

## Weaknesses

- No control consumer, so it cannot support any downstream-consequence claim.
- The `left_valid`/`right_valid` naming invites a false reading as a tracking gate; the audit must state explicitly that it is a null-reference check.
- Single-commit repository; README clone URL does not match origin.

## Final Role

- **`AUXILIARY_WIRE`**
- **`ADJACENT_NON_ROS`**: not applicable — it *is* ROS, but telemetry-only.

## Priority

**C** — keep in the population as a screened, documented data point on XR-runtime diversity and on the prevalence of telemetry-only bridges. Do not spend testbed time on it.

## Runtime Outcome (2026-09-14)

**Final status: `QUESTLESS_RUNTIME_COMPLETE`.**

Full report: `semantic_validation/results/VR_HAND_BRIDGE_RUNTIME.md`.
Run id `vr_hand_bridge_20260914T064240Z`. Evidence level **`E2 SYNTHETIC_RUNTIME`**.

The pinned `xr_hand_pipeline` package was built with colcon in an isolated ROS 2
Humble container (`--network none`, `ROS_DOMAIN_ID=72`) and the unmodified
`hand_ws_publisher` node was driven by a research WebSocket client
(`semantic_validation/harness/vr_hand_bridge_ws_trials.py`) using the exact
wire schema of `ws_streamer.gd:43-52`. 207 actual `PoseStamped` messages were
captured.

Measured:

- 1:1 pass-through, 100 frames in → 100 left + 100 right out, 49.495 Hz observed
  against a 50 Hz commanded rate; no buffering, decimation, or rate limit.
- `header.stamp` originates at the bridge (`hand_ws_publisher.py:41`), ~0.3 ms
  after the harness send and always before subscriber receipt (median
  `header.stamp − recv_wall = −274,590 ns` over all 207 messages). No wire time
  exists to preserve.
- `frame_id` is the unconditional literal `world` — the only frame id observed.
- **No validity or freshness gate exists in the path.** A frame carrying
  `timestamp_ns = 946684800123456789` (2000-01-01), `valid=false`,
  `left_valid=false`, `right_valid=false`, `tracking_state="UNTRACKED"` produced
  a normally-stamped, normally-valued pose on both topics, indistinguishable
  from the clean frame.
- Fault handling is structural only and is enforced by crashing the connection
  handler: missing `right_hand` → `KeyError` at `:89`, malformed JSON →
  `JSONDecodeError` at `:87`, non-numeric `pos` → `ValueError` at `:45`. All
  three close the connection with code `1011`; the node's own
  `except ConnectionClosed` at `:90-91` never fires.
- **Partial publication confirmed:** the missing-`right_hand` frame still
  published a left pose at `:88` before raising.
- Source loss is silent on the ROS side; the node survives, keeps both topics
  advertised, publishes no invalidation, and accepts an immediate stateless
  reconnect.

This upgrades the earlier source-only reading of `left_valid`/`right_valid`
from "misleading naming" to a measured fact: the tokens never reach the wire,
and the ROS side has no gate to mislead.

**No control consequence may be claimed.** The pipeline still terminates at a
printing subscriber and RViz; there is no robot consumer at this revision.
Priority remains **C** — the framework is now runtime-exhausted, and nothing
further can be learned from it without a Godot/OpenXR Quest session that would
still observe no validity handling.
