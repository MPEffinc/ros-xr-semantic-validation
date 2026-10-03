# R16 — M12 through real republisher code: Docker_Teleop receiver @64cbdde (protocol; frozen before formal runs)

**Level.** Backend/component only. The real receiver code (`ros_backend1.1/src/receiver/quest_controller_receiver.py`
@64cbdde) and its message package are built and run unmodified for B0. The input is a **synthetic packet producer**:
no Quest frontend, not a second real XR path. The upstream has no license (`package.xml` `<license>TODO</license>`),
so only an edit script is stored for B1, never a copy of the code.

## 1. What the original receiver keeps and loses (code, @64cbdde)

| Field / behaviour | Original receiver |
|---|---|
| Input per packet (JSON line) | `right_hand.{isTracked,pos,rot}`, `controls.{right_teleop_enable,…,source}`, `timestamp` (Unity `Time.time`) |
| `timestamp` | **never read** (dropped) |
| Packet receipt time | kept internally as `_last_packet_time_monotonic`, used **only** for the stale timeout; **not published** |
| Packet count/sequence | only a per-window log counter; **not published**; no sequence field is read |
| Session / reconnect | a new TCP client replaces the old one; no session identity is published |
| Cache | latest-wins state, republished at 60 Hz (`_publish_loop`) with `header.stamp = now()` on every publish |
| Stale neutralization | if the latest packet is older than 0.25 s, the published state is the **neutral** state (`teleop_enable = False`, `source = '*stale_timeout'`) |
| Output schema | `teleop_bridge_msgs/ReceivedPoseStates`: state fields, `source` string, `header.stamp` = publish time; **no provenance** of the packet |

**Consequence for B0.** Downstream, the only time is the publish stamp. A generic stamp-age check can be run, but the
packet's age, order and duplicates are **not checkable** from the output. "Not checkable" (the information is absent)
is reported apart from "checked but failed".

## 2. Arms

| Arm | Producer | Receiver | Gate |
|---|---|---|---|
| B0 | original schema (no seq/session; `timestamp` present) | **original code**, `ros2 run receiver quest_controller_receiver` | generic stamp age ≤ 100 ms on `/received_pose_states` |
| B1 | **adds** `seq` (per session) and `session` | the original code + a 21-line edit (`patch/apply_receiver_provenance.py`, marked `M12-B1`) publishing `m12r_prov_msgs/ReceivedPoseStatesProv` on `/received_pose_states_prov` | provenance gate (below) |

**The B1 typed schema.** `ReceivedPoseStatesProv` embeds the **same** `ReceivedPoseStates` and adds:

- `neutral`;
- `rx_count` and `rx_stamp` (packet receipt, receiver clock);
- `src_seq_valid`, `src_seq`, `src_session`;
- `src_time_valid`, `src_time` (producer clock, not compared).

Payload and provenance travel in one message, so there is no side-stream pairing and no `frame_id` carrier.

**B1 gate** (`harness/r_gate.py`; TAU = 100 ms, receiver/gate wall clock, same container):

- **Neutral:** classified `neutral_stop`, forwarded as a stop/hold, **never as motion**. This is the declared
  policy for safe neutral commands: they are not new observations, they are permitted only as stop.
- **Motion:** admitted iff `rx_stamp` age ≤ TAU.
  - When seq/session are present: within a session the source seq must not decrease, and an equal seq with a new
    `rx_count` is a duplicate packet (blocked). A new session resets the expectation.
  - **Missing provenance** in a session that had it: fail-closed (primary). The fail-open decision is also logged.

**Cost recorded.**

- producer: +2 fields;
- receiver: +21 lines, plus 1 new message package (3 files);
- gate: a new node;
- deployment: one extra topic, and consumers must subscribe to the typed topic.

**Boundary.** Real code: the receiver, plus its message package for B0. Our adapters: the edit script, the provenance
message package, the producer and the gate.

## 3. Conditions (12 s runs; window events in s after T0; producer 60 Hz; hand x moves 0.05 m/s from 2 to 10 s)

| ID | Construction | Truth classes created |
|---|---|---|
| N_MOVE | normal | fresh |
| N_STILL | constant pose | fresh (legitimate repeat) |
| CACHE_GAP | producer silent 5.0–5.2 s (< 0.25 s, so no neutralization) | stale_gap (republished cache with fresh stamps) |
| NEUTRAL_GAP | producer silent 5.0–6.0 s | stale_gap for ≈ 0.1–0.25 s, then neutral |
| RECONNECT_DUP | TCP close at 5.0, reconnect at 5.3 (B1: new session, seq restart at 0); 7.0–7.2: resend the packet originally sent at 6.0 (duplicate) | neutral during the gap, fresh after reconnect, stale_dup |
| MISSING_DUP | 5.0–8.0: packets without seq/session/timestamp; 7.0–7.2: duplicate of the 6.0 packet | stale_dup, and missing provenance |

**Formal trials.** 2 arms × 6 × 3 = **36** (`schedule_r.csv`).

## 4. Ground truth and measures (fixed; hidden from gates)

Ground truth comes from the producer send log on the same container clock. Each gate record is classified:

- **neutral:** the receiver published its neutral state;
- **stale_gap:** no producer send within 100 ms before the record;
- **stale_dup:** the latest send before the record was a duplicate resend;
- **fresh:** otherwise.

The class is matched by time to the latest send. **This time-based matching is used only for ground truth, never by
a gate.**

**Measures:**

- per class: motion admitted / total (primary and fail-open);
- the block reasons;
- false blocks of fresh motion.

**Invalid:**

- setup/rc failure;
- missing logs;
- a producer gap > 100 ms outside the designed gaps.

Reruns at most 2; all attempts are kept.

## 5. Limits

- Only the receiver hop. The mapper, bridge and Servo are not run.
- A synthetic producer: the real Unity sender sends no seq, so B1's producer change is an assumption about a
  modifiable frontend.
- Packet receipt time ≠ sensing time.
- No S2: a component that rewrites provenance is not defended.

## 6. Pre-flight (excluded; snapshot e06c713; 02:35–02:37)

- **Build.**
  - The receiver, `teleop_bridge_msgs` and `m12r_prov_msgs` were built in `docker-teleop-humble:local` (ROS 2 Humble)
    from the pinned upstream @64cbdde (clean HEAD verified).
  - Receiver source sha256 `9fa3a58c…`; patched B1 copy `5f80a59e…`.
- **PF1 B1 RECONNECT_DUP:** fresh 803/803 admitted; stale_gap 0/9 admitted (`rx_age`); stale_dup 0/12 admitted
  (`seq_regress_or_duplicate`); neutral 4 classified `neutral_stop`. Producer 59.7 Hz.
- **PF2 B0 CACHE_GAP:** fresh 820/820; stale_gap **7/7 admitted** (stamp age only; provenance absent).
