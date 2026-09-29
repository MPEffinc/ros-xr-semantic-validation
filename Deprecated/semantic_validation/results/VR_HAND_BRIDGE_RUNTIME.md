# VR-hand-bridge-ROS2 WebSocket-to-ROS Runtime

## Scope

- Upstream repository: `mahmoud-maan/VR-hand-bridge-ROS2`
- Pinned revision: `a5da3e09def32b2f0dc69d4199493243f40e1440` (worktree clean, single commit)
- Local checkout: `semantic_validation/targets/vr_hand_bridge_ros2`
- Runtime: isolated `vr-hand-bridge-humble:local` container (derived from
  `ros-xr-humble:local`, adds only `python3-pip` + `websockets==12.0`, which the
  pinned package imports but does not declare)
- `ROS_DOMAIN_ID=72`, `ROS_LOCALHOST_ONLY=1`, `--network none`
- Run id: `vr_hand_bridge_20260914T064240Z`
- Evidence level: **`E2 SYNTHETIC_RUNTIME`**
- Trace provenance: `SYNTHETIC_CANONICAL_EVENT`
- No Quest, no Godot/OpenXR frontend, no robot, no actuator. This repository
  contains no physical driver dependency at all; its only launch file
  (`ros2_ws/src/xr_hand_pipeline/launch/hand_pose.launch.py:19-40`) starts the
  bridge, a printing subscriber, and RViz.

Exercised production path:

```text
synthetic WebSocket JSON frame (research harness)
-> production hand_ws_publisher.py (unmodified, pinned)
-> actual ROS 2 geometry_msgs/msg/PoseStamped
   on /left_hand_pose and /right_hand_pose
-> research subscriber (observation only)
```

The injection point is the production WebSocket wire boundary
(`hand_ws_publisher.py:80-89`), upstream of every host-side transformation and
of the ROS publish. Because the host side contains no semantic gate (below),
this is an `UPSTREAM_FAITHFUL_REPLAY`-style injection with respect to the ROS
bridge only; the Godot frontend's own logic was not executed and no claim is
made about it.

The bridge source was copied byte-identically into the build workspace and not
modified: `sha256 41822041ce1c756946688ffa44fc8ba11ae758d65ba2596f81b27e92e1d63e2c`
for `hand_ws_publisher.py` in both the pinned target and the build tree.

## Wire schema (cited, not invented)

Producer (`ws_streamer.gd:43-52`) and consumer (`hand_ws_publisher.py:87-89`,
`:45`, `:52`) agree on exactly:

```json
{"left_hand":  {"pos": [x, y, z], "quat": [x, y, z, w]},
 "right_hand": {"pos": [x, y, z], "quat": [x, y, z, w]}}
```

There is **no source-timestamp field, no sequence number, no validity flag, no
device/session identity, and no frame identifier on the wire.** The
`left_valid` / `right_valid` variables in `ws_streamer.gd:24-40` are local to
the Godot sender and are set unconditionally to `true` whenever the node
reference is non-null (`:35`, `:40`); they are never serialized. Consequently a
"deliberately old source timestamp" cannot be expressed in this schema. Trial B
below supplies such a field as an *extra* key in order to establish whether the
bridge reads any freshness or validity signal at all.

## Build

```bash
source /opt/ros/humble/setup.bash
colcon build --packages-select xr_hand_pipeline --event-handlers console_direct+
# Summary: 1 package finished [0.52s]
```

Full output: `results/runs/vr_hand_bridge_20260914T064240Z/build.log`.

The container ran as `--user $(id -u):$(id -g)` with `HOME` pointed at a
writable mounted directory, which is required or colcon fails on `log/`.

## Trials and measured results

207 actual `PoseStamped` messages were received across the run (104 on
`/left_hand_pose`, 103 on `/right_hand_pose`).

| Trial | Input | ROS output | Server connection |
| --- | --- | --- | --- |
| P0_RATE | 100 well-formed frames at a 20 ms commanded period | 100 left + 100 right, observed **49.495 Hz** on `/left_hand_pose` over a 2.0207 s send window | stays open |
| A_NORMAL | one well-formed frame | 1 left + 1 right published | stays open |
| B_STALE_AND_INVALID_EXTRA_FIELDS | well-formed frame plus `timestamp_ns = 946684800123456789` (2000-01-01), `stamp`, `valid=false`, `left_valid=false`, `right_valid=false`, `tracking_state="UNTRACKED"` | 1 left + 1 right published, values and stamps indistinguishable from A | stays open |
| C_MISSING_RIGHT_HAND | `{"left_hand": {...}}` only | **1 left published, 0 right**; `KeyError: 'right_hand'` at `hand_ws_publisher.py:89` | closed by server, `code=1011` |
| D_MALFORMED_JSON | `{not json` | 0 published; `json.decoder.JSONDecodeError` at `:87` | closed by server, `code=1011` |
| E_NON_NUMERIC_POS | `pos: ["a","b","c"]` | 0 published; `ValueError: could not convert string to float: 'a'` at `:45` (via `:88`) | closed by server, `code=1011` |
| F_RECOVERY | one well-formed frame on a fresh connection after C/D/E | 1 left + 1 right published | stays open |

Bridge process state after all trials: `BRIDGE_ALIVE_AFTER_TRIALS=yes`;
`/left_hand_pose` and `/right_hand_pose` still advertised.

### Header stamp origin

Every observed message carried `frame_id = "world"` (the only frame id observed
in the run) and a non-zero stamp (`header_stamp_is_zero_count = 0`).

| Trial | Topic | `header.stamp` (ns) | minus harness send wall (ns) | inside send window |
| --- | --- | ---: | ---: | --- |
| A_NORMAL | left | 1789368404555010852 | +288,728 | yes |
| A_NORMAL | right | 1789368404555117590 | +395,466 | yes |
| B | left | 1789368405556290972 | +460,756 | yes |
| B | right | 1789368405556457562 | +627,346 | yes |
| F_RECOVERY | left | 1789368406561588876 | +265,551 | yes |
| F_RECOVERY | right | 1789368406561651661 | +328,336 | yes |

Across all 207 messages, `header.stamp - subscriber_receive_wall_clock` had
median `-274,590 ns` (min `-626,351`, max `-143,043`): the stamp is always
generated slightly *before* the subscriber sees the message, i.e. at
publication time on the bridge host.

This is the direct runtime confirmation of `hand_ws_publisher.py:41-42`: the
stamp is `node.get_clock().now()` (bridge wall clock at construction) and the
frame is the literal `'world'`. **No wire-carried time exists to preserve, and
none is derived.** Semantic disposition for I3 is therefore not `PRESERVED` or
`REVALIDATED` but `N/A on the wire` + `bridge-clock re-stamp` on output.

### Pose transformation (confirmed at runtime)

Godot-to-ROS remap at `hand_ws_publisher.py:46-48` executed as written: input
`pos = [1.0, 2.0, 3.0]` produced `position = (-3.0, -1.0, 2.0)`
(`x = -godot_z`, `y = -godot_x`, `z = godot_y`).

## Runtime findings

1. **Output presence/rate.** One inbound JSON frame produces exactly one
   `PoseStamped` on each of the two topics, 1:1, with no buffering, no
   decimation and no rate limiting. 100 frames in, 100 + 100 out; 49.495 Hz
   observed against a 50 Hz commanded rate.
2. **Header stamp origin is the bridge, not the wire.** The stamp is the
   bridge's own ROS clock at message construction
   (`hand_ws_publisher.py:41`), measured above as ~0.3 ms after the harness
   send and consistently before subscriber receipt.
3. **`frame_id` is the unconditional literal `'world'`**
   (`hand_ws_publisher.py:42`). No reference-frame provenance is carried on the
   wire and none is derived from the input.
4. **No validity gate and no freshness gate exist anywhere in the ROS-side
   path.** Trial B carried an explicitly invalid and 26-year-old declared source
   time and still produced a normally-stamped, normally-valued pose on both
   topics. The bridge reads only `data['left_hand']`, `data['right_hand']`,
   `hand['pos']`, `hand['quat']`; every other key is ignored.
5. **Input validation is structural only, and is enforced by crashing the
   connection handler, not by rejecting the message.** All three fault classes
   raise an uncaught exception inside `handle_client`. The `except
   ConnectionClosed` at `:90-91` does not cover them, so the node's own
   "Quest disconnected" log line is never emitted; the traceback surfaces from
   the `websockets` library instead.
6. **Partial publication is observable.** In trial C the left pose was
   published at `:88` *before* the missing-`right_hand` `KeyError` was raised at
   `:89`. A structurally invalid frame can therefore still place one actual
   `PoseStamped` on a topic.
7. **Loss of the source is silent on the ROS side.** After a handler crash the
   node keeps running and keeps advertising both topics; nothing is published to
   mark the fault, and the last pose published simply remains the last value on
   the topic. There is no watchdog, no timeout, no invalidation message, and no
   transport-generation or session concept (`hand_ws_publisher.py:83-91`).
8. **Reconnect is unconditional and stateless.** A new connection is accepted
   immediately after each fault (trial F) and resumes publishing with no
   re-arm, no handshake, and no identity check. Four separate "Quest connected"
   log lines were produced from the harness alone.

## Invariant disposition

| Invariant | Disposition | Basis |
| --- | --- | --- |
| I1 tracking state | `DROPPED` (never present on the wire) | schema above; trial B ignored `valid`/`tracking_state` |
| I2 source identity | `TRANSFORMED` — left/right preserved as distinct topics only; no device, session, or handshake identity | `:67-68`, `:88-89` |
| I3 source time / freshness | `DROPPED` on the wire; output carries a bridge-clock re-stamp | `:41`; stamp table above |
| I4 session / transport generation | `DROPPED` — no generation, no reset on reconnect | `:83-91`; trial F |
| I5 invalidation / re-arm | `DROPPED` — no watchdog, no re-arm, last value persists | trials C/D/E/F |

Downstream consequence: **`ROS_PUBLISHED`**. Nothing beyond that was observed
and nothing beyond that exists in this repository.

## No control consequence may be claimed

At this revision the pipeline terminates in
`hand_pose_subscriber.py:26-31`, which only `print()`s the pose, and in RViz.
**There is no robot consumer, no controller, no driver, and no actuator
anywhere in the repository.** `README.md:5` describes teleoperation as future
work. Therefore no control, safety, or actuation consequence of any kind may be
derived from this run, and the absence of a gate here is *not* evidence about
gating design in systems that do command a robot.

## Alternative explanations and limits

- `websockets` is imported but undeclared by the pinned package; version 12.0
  was supplied at the dependency boundary. Under the distribution package
  (`python3-websockets 9.1`) the legacy handler signature differs and the
  bridge's one-argument `handle_client` would not be invoked as written. The
  behaviour reported here is therefore conditional on a `websockets >= 10`
  runtime, which matches the library's current API and the code as written.
- The observed 49.495 Hz reflects the harness's own `asyncio.sleep` pacing plus
  scheduling, not a bridge-imposed rate. The claim supported is 1:1 pass-through,
  not a throughput limit.
- Only loopback transport inside one container was exercised; no cross-host DDS
  and no Pi endpoint were involved in this run.
- The Godot/OpenXR frontend was never executed. Nothing here characterises what
  the Quest-side application does with OpenXR tracking state.

## Evidence files

- `semantic_validation/harness/vr_hand_bridge_ws_trials.py`
- `semantic_validation/results/runs/vr_hand_bridge_20260914T064240Z/build.log`
- `.../bridge.log` (node stdout, including the three tracebacks)
- `.../harness.log`
- `.../trials.json` (measured summary)
- `.../ros_messages.jsonl` (all 207 received messages)
- `.../ws_events.jsonl` (every frame sent, with wall/monotonic send times)
- `.../bridge_state.txt`, `.../environment.txt`, `.../run_in_container.sh`

## Boundary

Confirmed: `WEBSOCKET_JSON_RECEIVED -> ROS_PUBLISHED`, with the stamp, frame,
gate and fault behaviour classified above.

Not confirmed and not claimed: Godot/OpenXR frontend behaviour, actual Quest
behaviour, cross-host ROS transport for this stack, any downstream consumer
acceptance, any robot command, any actuator effect.

## Status

**`QUESTLESS_RUNTIME_COMPLETE`** — the entire ROS-side half of this framework
was built and executed unmodified against synthetic wire input, and every
semantic question the repository can answer was answered at runtime. The
remaining half (Godot/OpenXR on Quest) is out of scope for a robot-free,
headset-free testbed and, because the framework has no robot consumer, carries
no control consequence to pursue.
