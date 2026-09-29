# XRROS-S4B-D5Q1-1.0.0 — prospective Docker D5 reconnect/generation setup qualification and design report

This campaign instantiates, and does not change, XRROS-S4-1.0.0 D5 (research protocol SHA-256 `3a40337121f8d687dc68036ff2ffc85a1bc6eda275a700ba7d9e8119cd322969`). It covers the registered D5 case and its two recovery policies, R_EXPLICIT (primary) and R_AUTO (secondary), with a 10 s post-barrier capture. The stop, settling and allowed-path thresholds are the originals. D4 (630/630) and the scoped D4-L (200/450, not a completed 450-row comparison) are unchanged and not pooled.

## Registered D5 input (`inputs/d5_fixture.py`)

The fixture runs at 20 Hz for 200 slots. Every real sample carries its own fresh stamp, source ID, generation and state.

| Slots | Phase | Content |
| --- | --- | --- |
| 0–19 | Idle | — |
| 20–35 | Reference | Gen 1, x=.20 |
| 36–55 | Active | Gen 1, x=.35 (moving) |
| 56 | Close | The **source closes TCP while moving** (t=2.8 s) |
| 56–69 | Disconnected | No bytes |
| 70 | New connection | **Generation 2**, 0.7 s after the close |
| 70–89 | Held grip | Gen 2 at the new reference pose x=.50 |
| 72 | Replay | **Old-generation sample presented after reconnect**: gen 1, x=.35, a fresh stamp so the generation alone distinguishes it |
| 90–93 | Release | Teleop release for 0.2 s |
| 94 | Rising edge | New reference, x=.50 |
| 110–129 | Subsequent movement | Valid movement to x=.65 (+.15 X) |
| 130–199 | Tail | Neutral tail |

## Shared recovery state machine (`inputs/d5_rearm.py`)

The same code is used by the B1 source gate, the official B2 TLOracle property (B2-native and B2-composed) and the B3 mapper check.

| Situation | Behavior |
| --- | --- |
| Any invalid event: disconnect, old generation, unbound or missing generation/stamp/state/connection, invalid tracking, stale or future age | Latches DISARMED. A neutral may pass. |
| Generation increase while ARMED | Disarms |
| R_EXPLICIT | Re-arms only after (a) 500 ms of continuously valid, fresh, current-generation input, then (b) a teleop release of at least 100 ms beginning after (a), then (c) a rising edge. Held grip never restarts. |
| R_AUTO | Re-arms with grip held once the 500 ms dwell is met |

Fresh reference capture uses the original mapper as is. The pinned `hand_pose_mapper.py` resets its position session when there is no active accepted message for more than 250 ms, or when teleop is false. A rejected-while-disarmed stream therefore always makes the first accepted active sample a new reference, with no added displacement.

**Information regimes.**

- **I_FULL:** the receiver wrapper observes the original receiver's own `_set_client`/`_drop_client` and attaches `receiver_connection {index, open}` to the in-process selected origin, meaning the I_FULL envelope and the B3 parent. B1 observes its own close.
- **I_NATIVE:** the ROS message is unchanged. Native arms get no generation, connection or time, so no re-arm is possible; they are UNOBSERVABLE by construction.

**Common stop adapter, D5 mode.** It stops on a defense rejection or on a lost verdict heartbeat. It resumes (`/servo_node/start_servo`) only on the defense's own first allowed teleop-true source decision while stopped, which each defense emits only after its own re-arm. The adapter contains no validity, generation or re-arm logic. B2-native keeps filter-only behavior and has no adapter.

## Declared implementation delta versus the D4LQ2 inputs

The full delta is in `preflight/d4lq2_to_d5q1_input_delta.txt`.

- **New files:** `d5_fixture.py`, `d5_rearm.py`, `d5_sender.py` (dispatched from `d1_sender.py` when `CASE_ID=D5`), `d5_monitor_rearm_preflight.py`.
- **`d1_nodes.py`:** receiver connection observation, the B3 D5 branch, and a teleop field in the B3 verdict log.
- **`d3_tloracle_property.py`:** a D5 full-regime branch.
- **`d1_stop_adapter.py`:** the D5 continuous mode.
- **`d4l_timing.py`:** 10 s capture and 500 ticks when `CASE_ID=D5`.
- **`d1_probe.py`:** the D5 200-slot schedule check.
- **Runner and scheduler:** `run_owned.py` and `run_qualification.py`, with `--rearm` and the `s4cp22d5q1_` prefix.

The vendor source, official monitor YAML/install, Servo hook, predicate thresholds and D4 paths are unchanged.

## Host and component preflight (before any Gazebo)

- **`analysis/test_d5_rearm.py`, 13/13 PASS.** It covers:
  - disconnect while moving;
  - rejection of old generations after reconnect, which also restarts the dwell;
  - acceptance of the new generation;
  - held grip under R_EXPLICIT;
  - a release shorter than 100 ms;
  - a release that happens during the dwell and does not count;
  - a correct release followed by a rising edge;
  - a dwell shorter than 500 ms;
  - R_AUTO re-arm;
  - invalid tracking, stale, future and disconnect faults;
  - missing generation, stamp or connection binding;
  - an invalid neutral latching;
  - a generation change without a disconnect;
  - full fixture timelines for both policies: R_EXPLICIT re-arms exactly at slot 94, and R_AUTO at slot 83, which is 500 ms after the replay reset.
- **`analysis/test_d5_sender.py`, 5/5 PASS**, using a real TCP loopback that accepts two connections:
  - The first connection carries docker:0–55, and the second carries generation 2 plus the gen-1 replay at 72.
  - The transport log is exact.
  - B1 I_FULL withholds 70–89 under R_EXPLICIT and 70–82 under R_AUTO. B1 I_NATIVE and B0 withhold nothing.
  - A negative fixture is detected.
- **Genuine official monitor + TLOracle component test** (`preflight/official_full_{R_EXPLICIT,R_AUTO}_rearm/`), both PASS. The disconnected cached copy, gen-2 held grip and gen-1 replay are blocked, the dwell restarts after the replay, and the release is forwarded as neutral.
  - **R_EXPLICIT:** held grip stays blocked after the dwell, and the rising edge after 150 ms of release is forwarded (`R_EXPLICIT_REARMED_ON_RISING_EDGE`).
  - **R_AUTO:** re-arms at the 500 ms dwell with grip held.
  - The single sample at the jitter-sensitive 500 ms boundary is unscored by design.
- **Other checks:** the empty schedule returns NOT_RUN.

The original receiver timeout (250 ms) remains independent and is reported, not credited. The exact source→Servo callback lineage uses the D4LQ2 join on the recorded stamp. The B3 and receiver-wrapper integration is exercised first in the Gazebo setup cells below.

## Design report (minimum-sufficient scaling)

**Complete candidate matrix.** 10 arms × 2 recovery policies × 5 repetitions = 100 Gazebo trials. The arms are B0, the shim, and B1/B2-native/B2-composed/B3 under I_NATIVE and I_FULL.

**Essential evidence.** Policy-dependent runtime exists only where a re-arm state machine runs, which is the I_FULL arms.

| Group | Trials per repetition | Role |
| --- | --- | --- |
| B1, B2-native, B2-composed and B3 I_FULL × R_EXPLICIT and R_AUTO | 8 | Disconnect stop, old-generation rejection, held-grip prevention, dwell, fresh reference, subsequent movement, and mechanism attribution for each policy |
| B0 and shim | 2 | Positive controls and the allowed-path reference. They are policy-independent because the original has no re-arm logic. |

**Redundant for formal repetition.**

- B0 and the shim across both policies: their configuration is byte-identical under either policy value.
- The I_NATIVE B1/B2/B2-composed/B3 arms under both policies: the native interface carries no generation, connection or time. No re-arm machine runs, so the policy is irrelevant, and D4 already showed native UNOBSERVABLE in 140/140 trials.

The native arms are run **once in setup qualification** to document the consequence. In the formal campaign they are registered `NOT_RUN_SCOPED_UNOBSERVABLE_BY_CONSTRUCTION`.

**Host versus Gazebo.** The state machine, all edge-case timings, the binding errors and the sender transport are established host-only or at the component level, as above. Gazebo is reserved for the real control path: disconnect-to-stop timing, the Servo stop/start cycle, the absence of held-grip or replay motion, fresh-reference displacement, subsequent movement, settling, and CPU/RSS.

**Proposed D5 formal campaign.**

- **Trials:** 10 per repetition × 5 fresh-state repetitions = **50 trials**, about 1 h, sequential and with no concurrent load. This is a scoped design: the registered I_NATIVE formal repetitions are NOT_RUN.
- **Supported claims:** the D5 policy for I_FULL B1, B2-composed and B3 under both recovery policies; the distinct behavior of B2-native; and the original B0 consequence.
- **Unsupported claims:** formal native repetitions; other disconnect and reconnect timings; generation authentication, since the source is trusted; actual Quest reconnects; physical robots.

## Setup schedule, retry and gate

`qualification_schedule.csv` lists 14 first-attempt cells:

| Cells | Count |
| --- | --- |
| B0/shim | 2 |
| I_FULL B1/B2/B2-composed/B3 × R_EXPLICIT/R_AUTO | 8 |
| I_NATIVE B1/B2/B2-composed/B3 | 4 |

Every cell must move, because every path ends with the valid +.15 movement. At most two retries are allowed per cell, and only before the barrier.

The B0/shim pair must meet the 5 ms and 0.02 rad limits. Each cell must be MEASUREMENT_QUALIFIED under `analysis/d5_setup_audit.py`, which checks:

- the fixture and generation schedule;
- the exact transport sequence, and the original receiver's observed close and new connection;
- the receiver-wrapper connection observation;
- 500 ticks;
- CPU/RSS;
- exact callbacks;
- B2 association, calibration and drain.

Setup is not a policy score. A separate formal schedule and scorer must be frozen and pushed before any D5 formal outcome.
