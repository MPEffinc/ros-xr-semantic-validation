# Timestamp semantics of candidate real apps (code review, 2026-10-02)

**Question.** The F1/F2 interval checks assume that a command's `header.stamp` is the **time of the
XR sample it was derived from**, on a clock the evidence path shares. Which real apps meet this
without modification?

Four times are kept distinct:

- **S**: XR sample time, i.e. the pose/action time in the runtime;
- **G**: command generation time;
- **P**: publish time;
- **R**: consumer receive time.

All findings are SOURCE_CONFIRMED at the pinned commits used in audits A1–A6, unless marked.

| App | Header stamp written | Relation to S | Clock domain of the stamp | Re-publish / cache gets a new stamp? | Interval premise met unmodified? |
|---|---|---|---|---|---|
| **OpenVR UR5e** `quest_teleop.py` (A1) | `self.get_clock().now()` in the same 50 Hz timer callback that just polled `getDeviceToAbsoluteTrackingPose(..., 0, ...)` (L43, L81) | **On SteamVR:** predicted-0 poses, so S ≈ G ≈ P within the callback (sub-ms). **On xrizer: S is not G.** xrizer locates every pose at `display_time` (`input/devices.rs` L92–98), which is set once at init and replaced only by `WaitGetPoses` (`openxr_data.rs` L190). This Background app never calls `WaitGetPoses`, so **every pose is located at the init-time XrTime**, while the stamp is `now()`. | ROS node clock, i.e. system time (no `use_sim_time`), the same host clock as a collector on that host | Each poll gives a new stamp, but **the grip value can be a held/cached state** (ALVR edge-only forwarding, K6). The stamp then certifies nothing about the input's age. | **SteamVR:** pose timing yes; deadman timing **no** (cached). **xrizer:** **no**. |
| **IsaacTeleop** `teleop_ros2` (candidate 2) | `self.get_clock().now()` after `session.step()` (`teleop_ros2_node.py` L235–244; `messages.py` L50, L311, L367, …) | S is whatever time `step()` sampled at (not traced: NOT_VERIFIED); G ≈ P | ROS clock. The code comment says it follows `/clock`, so with `use_sim_time` the stamp is **sim time**, not the evidence clock | It publishes every loop and carries per-pose `is_valid` (L53–61). Invalid samples are stamped fresh. | **No** under sim time; NOT_VERIFIED otherwise. It is also Monado-incompatible (NVX1). |
| Quest2ROS2 (A2) | The controller restamps `now()` when it **receives** the pose (L304); the input stamp is ignored | output stamp ≈ R at the mapper, not S | ROS clock of the mapper host | yes: every callback stamps a new time, including after reconnect with an old anchor | **No.** Only receive time is available. |
| PickNik (A3) | `DateTime.UtcNow` at publish on the **Quest** (L367–380) | ≈ P on the headset, not S | **Quest wall clock** (different host; offset unknown) | yes (60 Hz, a frozen pose with fresh stamps while unfocused; R0) | **No.** Different clock domain, and the stamps are fresh for frozen data. |
| Docker_Teleop (A5) | Unity sends `Time.time`; the receiver ignores it and stamps `now()`; the mapper and bridge restamp again | final stamp ≈ R at the bridge | ROS clocks; mixed wall and sim time across hops | yes, at every hop | **No** |
| Spes (A4) | No stamp in the WebSocket packet. ROS stamps the publish time. | ≈ R at the server | server clock | yes | **No** |
| OpenArmX (A6) | The APK sends `ts_ns` (meaning NOT_VERIFIED), copied to `PoseStamped`, and `≤0` is replaced by `now()`. The teleop node then **discards** it and uses `time.monotonic()`; the output carries no stamp. | output: none | — | — | **No** |

## Consequences

1. **No audited real app satisfies the generation-interval premise unmodified.** Three reasons
   recur:
   - the stamp is a receive or publish time;
   - it is on a different clock domain (headset or sim time);
   - it is freshly applied to cached or frozen data.

   The OpenVR UR5e app on SteamVR comes closest for pose timing, but its deadman value can be stale
   through ALVR. On xrizer the premise fails outright.
2. **Narrower guarantee available without app changes: receive-time state.** The gate can ensure
   that at the consumer's receive time R, the runtime reports the bound client's input as active, and
   that the evidence is ≤ 50 ms old. That corresponds to ARR with the freshness rule F computed from
   R. It does **not** bound how old the command's content is. It catches neither commands generated
   during an interruption that arrive after it, nor duplicates, unless they arrive during the
   interruption. F2 quantifies what ARR misses relative to GEN_ARR/INTERVAL.
3. **Changes needed for generation-interval checking** (any one app):
   - **(a)** stamp each command with the XR **sample** time of the inputs it uses, converted to a clock
     shared with the evidence path (OpenXR `XR_KHR_convert_timespec_time`, offered by Monado main);
   - **(b)** keep the stamp unchanged end to end, so no hop restamps (this affects Quest2ROS2,
     Docker_Teleop, OpenArmX and Spes);
   - **(c)** for deadman/button inputs, stamp with the action's `lastChangeTime` or the sync time.
     A stamp on a cached value is not evidence;
   - **(d)** for duplicate and order checks, use a monotonic stamp or sequence.

   These are app or middleware changes per implementation, in the same places as the direct-delivery
   edits in `docs/04_RETROFIT_SITES.md`. **The "zero app changes" advantage of the independent path
   holds only for receive-time state, not for generation-interval checking.**
4. **For the functional real-app run (brief step 4)**, only a receive-time-state claim is admissible
   for the OpenVR UR5e app. On xrizer the pose content is additionally invalid (located at a fixed
   time), so a functional run would need xrizer to drive frames or update `display_time`. That would
   be a deployment-component change, reported separately.
