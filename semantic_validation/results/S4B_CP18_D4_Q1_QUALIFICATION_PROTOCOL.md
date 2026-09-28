# XRROS-S4B-D4Q1-1.0.0 — prospective Docker D4 source-freshness setup qualification

This is a new, prospective Docker D4 **setup** campaign. Research protocol XRROS-S4-1.0.0 (SHA-256 `3a40337121f8d687dc68036ff2ffc85a1bc6eda275a700ba7d9e8119cd322969`) remains normative and unchanged. D1 (48/50), D2 (47/50) and the D3 formal result (50/50 valid; B3 I_FULL 4/5 frozen, 5/5 supplementary) are immutable and are not reinterpreted here.

## Registered D4 input

The motion shape is the registered Docker fixture at 20 Hz:

| Indices | Phase | Teleop | Position |
| --- | --- | --- | --- |
| 0–19 | Idle | false | x=.20 |
| 20–35 | Reference | true | x=.20 |
| 36–55 | Active | true | x=.35, y/z unchanged |
| 56–119 | Tail | false | — |

The capture is six seconds after the start barrier. Tracked is true and the generation is 1.

Each sample has its own host `CLOCK_MONOTONIC` creation time `sample_ns`. From that, the fixture derives its own stamp `source_timestamp_ns` (`inputs/d4_age.py`). The wire JSON `timestamp` equals the stamp divided by 1e9. Seven conditions are registered:

| Condition | Stamp |
| --- | --- |
| `A000` | `sample_ns − 0` |
| `A050` | `sample_ns − 50 ms` |
| `A150` | `sample_ns − 150 ms` |
| `A350` | `sample_ns − 350 ms` |
| `A750` | `sample_ns − 750 ms` |
| `H1P0` | The literal historical epoch value 1.0 s (the same stamp for every sample). This is a synthetic epoch anomaly, **not** a 1.0 s age offset. |
| `FUT1S` | `sample_ns + 1 s`, a clock-contract violation |

## Registered freshness profiles and decision rules

The profiles are F100, F250 and F500. The trial owner sets `XR_FRESHNESS_NS`, and `d1_contract.d1_allow` reads it. One value drives the B1 source gate, the official B2 TLOracle property and the B3 mapper. There is no per-baseline threshold.

The runtime predicate for a teleop-true sample:

- age = `now − source_timestamp_ns`, using the original stamp and never a regenerated ROS header;
- age < −5 ms → `FUTURE_TIME`;
- age > F → `STALE_SOURCE`;
- equality with F is allowed.

Ungripped samples are intentional neutral. The analyzer's expectation adds the registered 1 ms clock-uncertainty band at both F and −5 ms. Decisions inside that band are UNKNOWN and are not scored.

I_NATIVE interfaces carry no source time with a validated clock mapping, so a native defense cannot use age. For freshness, that is UNOBSERVABLE, not a method failure.

## Declared implementation delta versus Q6

`inputs/` is a byte-identical copy of the Q6 inputs (`preflight/q6_inputs_copied.sha256`), plus the following changes:

1. `d4_age.py` is new.
2. `d1_sender.py` produces the D4 fixture. It keeps all 120 slots real. A B1 I_FULL rejection withholds bytes and logs the rejecting verdict.
3. `d1_contract.py` reads the freshness profile from the environment. The default is 250 ms, and the predicate is otherwise unchanged.
4. `servo_callback_drain.py` joins on the recorded per-sample stamp rather than assuming it equals `sample_ns`.
5. `d1_probe.py` checks the D4 source schedule and stamp instead of D3's 100-real/20-silent schedule.
6. `run_owned.py` adds the condition and profile environment, D4 naming and the `s4cp18d4q1_` container prefix.
7. `d4_monitor_freshness_preflight.py` and `run_qualification.py` are new.

The following are unchanged:

- the receiver, mapper and bridge wrappers;
- the official monitor YAML and generated install;
- the oracle property file;
- the stop adapter;
- the tick publisher, which is retained as the Q6 health stream;
- the Servo hook `.so`;
- calibration, the resource sampler and the post-capture lifecycle.

The analyzer (`analysis/d4_setup_audit.py`) reuses Q6's unchanged checks for the official tick and source association, calibration, post-capture drain, CPU/RSS and lifecycle. It replaces only the fixture check, the source→Servo callback join, which now compares the recorded stamp, and the motion positive control.

## Setup schedule, retry and gate

`qualification_schedule.csv` fixes 20 first-attempt cells:

- **A000/F250:** all ten configurations (B0, shim, and B1, B2-native, B2-composed and B3 under I_NATIVE and I_FULL). A positive-control motion of more than .01 rad is required for each.
- **A750/F250:** B0 and shim, with motion required, plus the four I_FULL defenses, where motion is not required.
- **Profile/condition paths:**
  - B1 full at A150/F100;
  - B3 full at A350/F500, with motion required;
  - B2-composed full at H1P0/F250;
  - B2-native full at FUT1S/F250.

Each cell allows at most two setup-only retries (`_setup02`, `_setup03`), and **only** if an attempt ended before the start barrier. All raw data is retained.

B0/shim pairs at A000 and A750 must meet the frozen limits of 5 ms source-index timing and 0.02 rad final six-joint difference. Every cell must be MEASUREMENT_QUALIFIED. That requires:

- the D4 fixture and stamps;
- the full ACK and a common clock;
- 300 ticks;
- complete CPU/RSS;
- exact source→Servo callbacks and receiver source/stamp coverage;
- B2 calibration and official association;
- post-capture drain;
- motion where it is registered.

Setup PASS is not a freshness-policy score. A separate five-repetition formal schedule and policy analyzer must be frozen and pushed before any D4 formal outcome. A failing setup is preserved. A correction needs a causal hypothesis and a new prospective version, never an unchanged repeat.
