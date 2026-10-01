# 03 — Taxonomy and defense matrix (draft v0, 2026-10-01)

**Basis.** The following sources feed this draft:

- OpenXR items (`../literature/OPENXR_ITEMS.md`);
- six audits (`../audit/A1`–`A6`);
- the R0 reanalysis of prior real-Quest data;
- S5 results (PRIOR_INTERNAL).

**Status of cells.** Cells are draft. "?" means NOT_VERIFIED and is never gap evidence. No pilot
result of this study is included yet. P1 will fill rows T2, T3 and T5.

## 1. Taxonomy (meaning and transition conditions)

| ID | Category | Applicability condition it supports | Transitions that change it |
|---|---|---|---|
| T1 | Tracking validity | The pose used was actively tracked, not inferred or last-known. | track loss/regain (E-TRACK), valid-but-untracked |
| T2 | Session / lifecycle / input activity | Input is from a focused session with an active action. | focus loss/regain, pause, menu (E-DEACT), session end |
| T3 | Permission linkage (deadman, clutch, toggle) | Operator permission holds *now* and was granted in the current interval. | release, deactivation, cache hold-over, auto-resume |
| T4 | Time, order, causality | The command derives from a sample that is fresh and ordered; old intervals are not replayed. | delay, reorder, restamp, reconnect |
| T5 | Space / anchor / calibration | The pose and the transform or offset multiplied with it belong to the same interval. | E-ORIGIN (runtime recenter), E-CALIB (app anchor), E-DRIFT, E-TF-FORGE |
| T6 | Input ↔ device ↔ arm ↔ command binding | A command for arm *k* derives from device *k*'s sample. | profile change, hand↔controller switch, role swap, message reuse |
| T7 | Ownership / control authority | The sender holds control of the target. | handoff, lease end (authority_continuity, PRIOR_INTERNAL) |
| T8 | Control mode and arbitration | The command is interpreted in the active mode (relative/absolute, AIM/GRIP, home motion). | mode switch, override, scripted motion |
| T9 | Feedback / display state | The operator sees state consistent with execution. | stale feedback (N1, PRIOR_INTERNAL) |
| T10 | Required multi-input relations | Combined inputs (left+right, head+hand, rate+pose) come from compatible samples. | asynchronous packets, fan-out |
| T11 | Common enforcement / watchdog / protection faults | The enforcing element is alive and fail-closed. | monitor crash or hang, bridge death (S5 C-MON, PRIOR_INTERNAL) |

## 2. Evidence delivery by implementation (from the audits)

Cell legend:

- **R** — read at the source.
- **F** — forwarded on the wire.
- **C** — consumed by the ROS mapper or gate.
- **–** — not present.
- **?** — not verified.

| Evidence | OpenVR UR5e (+ALVR) | Quest2ROS2 | PickNik | Spes (WebXR) | Docker_Teleop | OpenArmX |
|---|---|---|---|---|---|---|
| action active / focus | R (ALVR, pose action only), F –, C – | ? (closed app), F –, C – | R in Unity, F – (R0: frozen stream while unfocused) | – (no `visibilitychange`) | – (search miss) | ? (APK), F – |
| tracked (≠ valid) | lost at ALVR (`Running_OK` constant) | F – | F – (XRI keeps last pose) | `emulatedPosition` not read | `isTracked` := *connected* | F – |
| valid / present | F (`bPoseIsValid`), C | F – | F – | null → **head-pose fallback** | F (bool), C at 3 hops | F – (receive-time freshness, C) |
| deadman level vs edge | edges only at ALVR → cached level | latched toggle (starts ON) | press edge + level Bool; host ? | latched toggle (gripper), `move` level | grip level each frame, C | grip level, C; IK override latched |
| sample time | replaced by `now()` | ignored, restamped | publish-time Quest clock | none | dropped at receiver | dropped at node |
| origin change + effective time | ALVR recenter at receipt, `changeTime` dropped | – | – | – (no `reset`) | – | ? |
| applied transform version | app offset (local), no epoch | anchor + 20-sample filter, no epoch | Unity world incl. Camera Offset | anchor = last command | anchor on engage/regain | absolute calib from unsynchronised packets |
| device ↔ arm binding | right role, polled | topic + `mirror` (unchecked) | **shared mutable message** (R0: 54 % left msgs carry the right frame) | single controller; head substitution | per-hand topics | ASCII L/R label; `rate` fanned out |

## 3. Defense matrix (per item)

Columns follow brief §5:

- **Need** — information needed to judge.
- **Avail** — does it exist, and is it delivered?
- **Src / trust** — where it comes from and the trust condition on it.
- **Expressible** — can an existing defense express it in principle?
- **Handled** — does the implementation or configuration handle it?
- **Det / Block** — detect only, or block before execution.
- **Where / bypass** — enforcement point and bypass path.
- **Cost** — latency, normal-task impact, configuration.
- **Level** — evidence level.

| # | Item | Need | Avail | Src / trust | Expressible (existing) | Handled | Det / Block | Where / bypass | Cost | Level |
|---|---|---|---|---|---|---|---|---|---|---|
| M1 | Tracking-invalid pose drives the robot (T1) | tracked flag per sample | lost in 5/6 implementations (only Docker sends a bool, meaning *connected*) | runtime → app; app-reported | **yes**: field transport plus a direct check or monitor (S5 #2/#3, NO_METHOD_GAP) | no (all six) | block if gated before the consumer | gate before the consumer; bypass = any app that drops or forges the field (A3 out of scope) | 0.1–0.6 ms decision (S5) | SOURCE_CONFIRMED (delivery); PRIOR_INTERNAL (defense) |
| M2 | Focus loss leaves a fresh-looking frozen stream (T2) | focus / action-active | exists at the source; **not on the wire** in any of the six | runtime → app | **yes** if delivered (same as M1). Without it, a frozen-pose heuristic false-blocks a stationary hand. | no | — | gate | ? | SOURCE_CONFIRMED; **R0** (real-device data shows a 60 Hz frozen stream with fresh stamps) |
| M3 | Release leaves motion until the consumer timeout (T3) | deadman level at the consumer | level delivered (OpenVR) | app | yes: hold/pause on release, or a shorter timeout | partial (Servo 0.5 s timeout) | block of *new* commands; the executing target persists ≤ timeout | Servo; none | Servo-level pause/timeout do **not** reduce 35–45 mm of residual motion: it is downstream (JTC + plant lag). Controller-level stop untested (P1b). | EXPERIMENT_CONFIRMED (P1, synthetic source) |
| M4 | Cached deadman across deactivation (T3 × T2) | deadman level **and** whether an inactive interval intervened | ALVR forwards edges only; the spec forbids an edge across inactivity → the level is stale | ALVR client | **yes**: (a) release-on-inactive at the source (1 site); (b) re-arm after an interruption at the ROS side (S5 R_EXPLICIT) | no | block (re-arm) | ALVR client or ROS gate | (b) without the cause evidence: false block 3/3 on a 100 ms glitch; with action activity: 0 forwarded on C2 and full progress on C3 | EXPERIMENT_CONFIRMED at command level (P1); premise (SteamVR/Quest stale grip) NOT_VERIFIED; physical C2 masked by a Servo singularity stop |
| M5 | Resume with an old anchor (T5 × T3) | re-anchor on resume | — | app | yes: re-anchor on engage (S5 #10) | Quest2ROS2 on toggle only; Docker/OpenArmX/Spes yes; OpenVR no | — | app | — | PRIOR_INTERNAL (APPLICATION); **not re-proposed** |
| M6 | Origin change during engagement mixes intervals (T5) | change event + effective time + transform | present in OpenXR (`changeTime`); dropped by ALVR; absent in the other five | runtime | partly: (a) an epoch/event forwarded → re-anchor or re-arm; (b) a jump guard (Spes, 5 cm/35°) as a heuristic | Spes heuristic only | (a) block; (b) block above the threshold | app or gate | B0 moves 180/15 mm. (b) misses the 3 cm change and false-blocks 3 m/s (host). With the epoch: gate 0 mm (re-press, 1 leaked command in 1/3); app retrofit 0 mm (15 lines, app-specific) | EXPERIMENT_CONFIRMED (P1, synthetic source) |
| M7 | Latest-transform lookup paired with older sample (T5 × T4) | stamped lookup | tf2 offers it | tf | **yes**: `lookupTransform(…, stamp)` | Servo 2.12.4 uses `Time(0)`; Quest2ROS2/Docker use `Time()` for the EE anchor (intended) | — | consumer | none | SOURCE_CONFIRMED; effect not measured |
| M8 | Left/right message contamination (T6) | per-message device identity | `child_frame_id` partly corrupted | app | detect frame ≠ topic only; a correct-frame swap is undetectable on the ROS side | no | detect (partial) | ROS gate; the root fix is in the app | fix: per-publish allocation | **R0 on real-device data**; SOURCE_CONFIRMED |
| M9 | Head-pose substitution under the controller clutch (T6) | pose-source identity | not sent (`device` stays `VR`) | browser app | yes, if a source field is sent | jump guard re-anchors, then follows the head | — | app | — | SOURCE_CONFIRMED (A4) |
| M10 | Shared rate / override fan-out across arms (T6 × T8) | per-arm scope | — | bridge / node | yes (scoping) | no | — | node | — | SOURCE_CONFIRMED (A6) |
| M11 | Latched override bypasses the deadman (T8 × T3) | override provenance and lifetime | TRANSIENT_LOCAL latched | ROS participant | yes (QoS, SROS2 permission, timeout) | no | — | node | — | SOURCE_CONFIRMED (A6) |
| M12 | Stale or restamped time (T4) | source stamp | dropped in 6/6 | app | yes (S5 D4 freshness at the consumer) | receive-time only (Docker, OpenArmX) | block | consumer | — | SOURCE_CONFIRMED; PRIOR_INTERNAL |
| M13 | Enforcement element fault (T11) | health | — | gate | yes (heartbeat, fail-closed `unknown`) | Docker: Servo halts only if the bridge dies | block | consumer | — | PRIOR_INTERNAL (S5 C-MON), pinned versions only |
| M14 | Authority / lease (T7) | lease epoch per command | — | bridge | yes (sequencer + lock-delay) | — | — | — | — | PRIOR_INTERNAL (authority_continuity) |
| M15 | Unauthenticated bridge (A1 attacker) | — | — | — | standard TLS/auth/SROS2 | no (Spes bundles a key; OpenArmX UDP accepts any sender) | — | — | — | known class; not a research gap |

## 4. Patterns the draft already shows (to be tested, not assumed)

1. **The evidence exists at the source but is dropped at the app→wire or middleware boundary.** This
   holds for T1, T2, T5-epoch and T4-stamp in essentially every implementation audited. Where it is
   delivered, S5 shows that ordinary checks suffice (PRIOR_INTERNAL).
2. **The cause is lost along with the field.** Several distinct causes (deactivation, tracking loss,
   disconnect) collapse onto one signal (`bPoseIsValid`, silence, or a frozen stream). A ROS-side
   checker with equal information then has to trade residual permission against false blocks. This
   is a METADATA limit, not a checker limit. P1 measures it.
3. **Binding is implicit**: topic name, label or role, with no per-sample device identity. The one
   real-device dataset shows that the implicit binding broke (R0).
4. **Each retrofit is implementation-specific**, because it sits in a different place in each
   implementation: ALVR client, Unity script, browser JS, UDP bridge, or ROS mapper. This is the brief
   §8 condition 2 to evaluate.
