# R11 — M12 on the real UR5e app path: does a fresh stamp mean fresh input? (protocol; frozen before formal runs)

**Question.** Can a command be judged fresh because its publish or receive stamp is fresh? How far does
the strongest existing fix go?

**Kind of result.** This is a **command-level** experiment: the decision at the enforcement point
before Servo is judged. EE motion is not used as evidence of a correct semantic decision.

## 1. Time and provenance along the path (code + instrumentation)

| Hop | What happens | Time available there |
|---|---|---|
| Source (synthetic `remote` driver feeder) | sends one 376 B packet every ~10 ms over TCP | send wall time (feeder log only; the harness side) |
| Monado `r_hub` | `r->latest = data` on every packet (`r_hub.c` L338–348) | **no receive time is stored** |
| Monado `r_device_get_tracked_pose` | returns `latest` regardless of the requested time; flags all VALID+TRACKED if `active`, else 0 (`r_device.c`) | none |
| xrizer v3 | each app call pumps one frame (`xrWaitFrame` → predicted display time), clears the per-frame pose cache, syncs actions, then `xrLocateSpace` at the **predicted display time** | requested (predicted) time, which is **not** an observation time |
| App (`quest_teleop.py`) | 20 Hz tick: reads pose and grip; builds the target; stamps `now()` at message build | API call time (not recorded); the stamp is the generation time |
| ROS | publish → (bridge) → gate → Servo | publish/receive times |
| Servo | `incoming_command_timeout` 0.5 s on `now − header.stamp` | stamp age |

**Consequences.**

- **The source update time cannot be observed** by the runtime, xrizer or the app on this path.
- Neither the OpenVR legacy API nor core OpenXR returns a sample time for the pose. The requested
  display time is a prediction target, not an observation.
- **The strongest per-app fix** can carry only:
  - the acquisition (read) time in the app clock;
  - the validity and tracking result;
  - a read sequence number.
- **The runtime-state check** knows whether input is active, but has no link to a sample.

## 2. Arms (the same age policy τ for A1 and A2)

| Arm | Information used | Where | Cost |
|---|---|---|---|
| A0 original | header.stamp, via Servo's own 0.5 s timeout (clocks matched: app `use_sim_time:=true`, R06/R07) | Servo | none |
| A1 generic stamp-age check | `now − header.stamp ≤ τ` at gate receive | gate before Servo | gate only |
| A2 strongest existing fix | app copy (`arms/quest_teleop_m12.py`, 6 changed lines) puts the acquisition time, read sequence, validity and tracking result into the command (`frame_id` carrier). Gate admits iff `now − acq ≤ τ`, `valid = 1` and `seq` strictly increasing. | app + gate (message schema change across the chain) | app diff + gate |
| A3 independent runtime state (optional) | libmonado evidence (M39 reader; fresh ≤ 50 ms, FOCUSED, IO_ACTIVE, ¬INPUTS_BLOCKED, latched) at gate receive; **no sample link** | gate | collector + gate, no app change |

**Chain.** App → `/m12/app_cmd` → `chain_bridge` → `/m12/bridge_out` → gate → `/servo_node/pose_target_cmds`.

- The bridge stands in for a generic republisher in the deployment. Normally it forwards messages
  unchanged (its best case for A1).
- It appends `|bid=N` to `frame_id` for the ground-truth join. Gates parse it **only for logging**.

## 3. Conditions (window 6.0–7.5 s; `scenarios/*.json`; bridge mode in `run_m12.py`)

| ID | Construction | Truth in the window |
|---|---|---|
| N_MOVE | normal: the hand moves in the window | fresh |
| N_STILL | the hand still in the window; the feeder keeps sending the same pose | fresh (a legitimate repeat) |
| DELAY | the bridge holds each message 0.25 s (sim), stamp unchanged | stale (transport delay; real old stamp) |
| CACHE | the bridge drops app messages and republishes the last pre-window message at 20 Hz with `stamp = now` | stale (cache republish; fresh stamp) |
| INACT_CACHE | runtime IO deactivation (`mnd_sched`); the app goes silent; the bridge keepalive republishes the last message every 50 ms with `stamp = now` after 0.1 s of silence | stale (value reuse while the runtime is inactive) |
| SRC_STALL | the feeder sends no packet in the window; Monado keeps returning its latest pose as tracked; the app publishes normally | stale (the source was not updated) |

**Injection labels.** All injections are labelled as deployment-component fault injection (bridge) or
synthetic-source behaviour (feeder). The runtime IO toggle is a real runtime transition. **No
compromised-app (S2) claim** is made.

**Not run, with reasons:**

- **valid-but-untracked / inferred pose:** the remote driver sets flags all-or-nothing (code), so it
  cannot be produced at runtime here;
- **reordering/retransmission:** arm and condition budget.

## 4. Ground truth, thresholds, validity (fixed)

**Thresholds.**

- **τ** = 100 ms (sim clock) for both A1 and A2. Pre-flight rule, written before the pre-flight: if
  the normal pre-flight's **maximum** stamp age or acquisition age exceeds 70 ms, τ = that maximum +
  50 ms (rounded up to 10 ms), applied to A1 and A2 alike. The final value is recorded in §6 before
  freeze.
- **Clock error.** All nodes use sim time. The app-stamp minus Servo-sim-time offset was −36 ms median
  (R07); it is re-measured in the pre-flight.

**Ground truth** (never given to a gate). A message at the gate is stale iff either:

- the bridge injected it (delay, cache or keepalive); or
- the feeder sent no packet in the 100 ms before the bridge received the app message
  (`stale_source`).

Otherwise it is fresh.

**Outcomes per arm and condition.**

- stale admitted / stale total, by class;
- fresh blocked / fresh total (whole run and window), which gives the false-block rate in N_MOVE and
  N_STILL;
- block reasons;
- for A0: stale commands that Servo would act on (stamp age < 0.5 s, derived);
- descriptive: consecutive identical pose content in the window (what a value-change heuristic would
  flag; **not** used as a freshness criterion).

**Validity.**

- **Instrumentation-invalid:**
  - R03 (i)–(v);
  - the app rate (bridge-forwarded fresh messages in [3.0, 5.9]) < 15 Hz;
  - bridge or gate logs missing;
  - a feeder gap > 100 ms outside the designed stall.

  An invalid trial is rerun at most 2 times. All attempts are kept.
- **Kept and reported:** Servo masking statuses.

## 5. Schedule

- 4 arms × 6 conditions × 3 repetitions = **72 formal trials** (`schedule_m12.csv`).
- Block shuffle with `Random(120 + rep)`; Latin arm rotation; fresh container per trial.

**Reading.**

- What a fresh stamp can and cannot vouch for.
- Which stale classes each information level separates.
- The cost and placement of each arm.
- What no arm can separate (the SRC_STALL vs N_STILL pair).

## 6. Pre-flight record (filled before freeze)

Raw data: `experiments/M12_stamp/raw/preflight`. Excluded; 16:00–16:04.

| Run | Purpose | Result |
|---|---|---|
| PF1 A2 N_MOVE | A2 provenance plumbing and normal ages | 268 fresh / 268 admitted; stamp and acquisition age p50/p95/max = 33.0 / 37.2 / 41.0 ms. Acquisition time and stamp coincide, because the app builds the message in the same tick right after the read. Flagged `joint_state_gap` (would be a rerun). |
| PF2 A1 N_MOVE | A1 normal ages | 270 / 270 admitted; stamp age 34 / 39 / 39 ms |
| PF3 A3 SRC_STALL | feeder-stall plumbing; A3 | 28 messages labelled `stale_source` in the window, 28 admitted; 30 consecutive identical contents in the window. A3 blocked 1 fresh message once (an evidence edge). |
| PF4 A0 CACHE | bridge cache injection | 27 `stale_cache` messages injected in the window, all admitted (A0) |

**τ decision (rule of §4).** The normal maximum age was 43 ms (≤ 70 ms), so **τ = 100 ms** is kept for
A1 and A2. The clock offset (app stamp vs gate sim time) is about 33–43 ms of apparent age in
normal operation.
