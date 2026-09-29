# S4-B CP17 Docker D3 moving source-silence formal freeze

**No D3 formal trial has run at this checkpoint.** Research protocol XRROS-S4-1.0.0 (SHA-256 `3a40337121f8d687dc68036ff2ffc85a1bc6eda275a700ba7d9e8119cd322969`) is unchanged. This prospective formal configuration is `XRROS-S4B-D3F1-1.0.0`. It follows CP16 D3Q6 (protocol XRROS-S4B-D3Q6-1.0.0, SHA-256 `172b5d309d99e1b1e4ed2c3b805fc9093e772dcde89e50914f3899e38f5bfef0`; implementation freeze `13109a3d4ca18fa00d8a97be839afe39d33b67c4`; result commit `aba910237ad29cb37b41bfe9e7d9147d00b17f56`), whose ten setup cells were all MEASUREMENT_QUALIFIED. Q6 freeze (57 entries) and runtime (760 entries) manifests were re-verified. Q6 setup cells are **not** formal repetitions. D1 (48/50 valid), D2 (47/50 valid) and D3Q1–Q5 stay immutable and are not pooled with D3.

## Schedule and runtime

Formal root: `runs/s4b_d3_formal_20260928T040232Z/`. `schedule.csv` holds **50 distinct trial IDs** `docker_<arm>_<regime>_d3rNN`: five repetitions × ten arms (B0 original, B0 observational shim, B1, B2-native, B2-composed and B3, each B1–B3 under I_NATIVE and I_FULL). `inputs/make_schedule.py` shuffles arms within each repetition with `random.Random(20260922)`. The fixture is Q6's unchanged normalized 120-slot D3 fixture (SHA-256 `f44ab3df78d10e91c97a3622d8a2f532f7079f3d4e12f6b031fd76fb94a8af0d`): 20 Hz; teleop true and tracked true through `docker:55` while moving; **no bytes** in slots 56–75; transmitted tail 76–119 with teleop false; 300 independent 50 Hz health ticks; six-second scored window. F250 and R_EXPLICIT apply.

`inputs/run_formal.py` starts a new `s4d3f_*` container per attempt. It uses the image, read-only mounts, environment and Q6 `/code` and `/analysis` directories exactly as Q6 `run_owned.py` did, with `CASE_ID=D3`, `STOP_DIAG=0` and domain 181. It records all argv to `commands.jsonl` and every attempt to `attempts.jsonl`, and keeps stopped containers. **Setup retries are finite and allowed only before any outcome exists.** An attempt that ends with no `barrier.json` may be retried as `<id>_setup02` and then `<id>_setup03`, with identical parameters. The first attempt that reaches the start barrier is the formal trial, whatever its exit or outcome. It is never retried or replaced. The batch stops, leaving later rows NOT_RUN, if a cell exhausts its retries or if two consecutive rows exit nonzero after the barrier. Resuming then requires a documented cause.

## Frozen analyzer (`analysis/d3_formal_audit.py`)

**Validity layer.** The analyzer calls Q6's frozen `d3_qualification_audit.inspect`/`pair` unchanged on each formal root, using a temporary Q6-style symlink name. These functions check the fixture, 120/100/20 slots, 300 ticks with no fabricated source, full ACK with a common clock, 100 ms CPU/RSS and wait4 accounting, exact source→Servo callbacks, B2 calibration, exact official property/status/guarded receipt for **every** original event (including original neutrals), post-capture drain and receiver coverage. The formal layer adds the following checks:

- a unique receiver receipt for `docker:55` and `docker:76`;
- an observed original `stale_timeout` neutral;
- exactly one Mapper consume for every original source and neutral publication;
- exact verdict coverage for all 20 eligible active IDs, `docker:36..55`;
- exact Servo callbacks for those IDs;
- motion at the local trigger (>.001 rad/s);
- B3 300-tick and oracle 300-tick coverage;
- a unique official status matching the first oracle silence tick.

Any gap gives **INVALID_COMPARISON / policy UNKNOWN**. This covers instrumentation, clock and resource gaps, which are never called a defense failure. A cell with no attempt reaching the barrier is **BLOCKED_MEASUREMENT / NOT_SCORED**. If a repetition's B0/shim equivalence is not PASS (5 ms / 0.02 rad), or an arm's matched schedule against the shim is over 5 ms, that defense arm is INVALID.

**Policy layer (XRROS-S4-1.0.0 §5/§8, unchanged thresholds).** The local trigger is the last **real** source receipt at the defense location plus 250 ms. For B1 this is the source-side `send_ns(docker:55)`. For B2, B2c and B3 it is the original receiver receipt of `docker:55`. It is never the stall start, a tick or a cached publication. A defense arm is FAIL_POLICY on any of these conditions:

- a false rejection among eligible active IDs;
- a silence decision or stop request before the trigger;
- a silence tracker that is not bound to `docker:55` with the exact trigger, or that counts a non-source event as a receipt;
- no decision, or a decision more than 50 ms after the trigger;
- no explicit neutralization request, or one more than 50 ms after the trigger;
- a missing stop reply or controller zero;
- any nonzero Servo command parented to a post-silence source without re-arm;
- a nonzero controller command after trigger+300 ms;
- Gazebo not settled by trigger+1 s;
- a pre-fault (`docker:55`) joint position more than 0.02 rad from the shim's.

Post-fault final joint divergence is an outcome, not a gate. For I_NATIVE B2-native, B2-composed and B3, the native ROS interface carries no source-receipt time or ID. If such an arm makes no decision and no request, and has no false rejection or restart, it is **UNOBSERVABLE**, not a method failure; the violations that would apply are still listed. B1 I_NATIVE sees its own transmissions and is scored. B0 and the shim are controls and are not scored.

The analyzer reports seven mechanisms separately and credits none of them to another:

1. B1 source-side detection.
2. The official ROSMonitoring/TLOracle verdict, as a monotonic property time plus the matching `blocked`/`currently_false` status. Status wall time is not subtracted from monotonic time.
3. B2-composed health or watchdog triggers.
4. B3 receiving-side detection.
5. The original receiver timeout. It is reported, never credited.
6. The existing Servo incoming-command timeout. It has no internal log, so it is UNOBSERVABLE; the Servo-input publication gap is reported.
7. Common stop-adapter actuation, which is never attributed to native ROSMonitoring.

Settling without a qualifying request is FAIL_POLICY. The analyzer counts cached prior-source nonzero Servo callbacks after the trigger, but does not relabel them. Source-to-first-callback p95 is descriptive only; the exact added gate/transport latency and the monitor's internal publish time remain UNKNOWN. Controller output and joints are interval observations with no per-source causal parent.

## Pre-formal validation

`analysis/test_d3_formal_audit.py` ran 14 tests, all PASS. Each test mutates a **temporary copy** of Q6 setup raw:

| Fixture | Case | Result |
| --- | --- | --- |
| A | Valid moving-state silence, B1/B2c/B3 full | PASS_POLICY |
| B | Original timeout only (B2-native full) | FAIL_POLICY, NO_EXPLICIT_NEUTRALIZATION_REQUEST, although it settled |
| B | B3 I_NATIVE | UNOBSERVABLE |
| C | Explicit request | Attribution kept separate |
| D | Tick-refreshed tracker | FAIL |
| D | Tick fabricated as a source | INVALID |
| E | Late nonzero controller command | FAIL |
| E | Restart from a post-silence source | FAIL |
| F | Missing Servo callback | INVALID |
| G | Missing guarded receipt or tick status | INVALID |
| H | Missing original-neutral property or Mapper consume | INVALID |
| I | Clock boot-ID or resource-sample gap | INVALID/UNKNOWN |
| J | No request, a +120 ms request, or a −100 ms request | FAIL (request absent, over 50 ms, or premature) |

Additional tests covered active false rejection (VALID + FAIL, not INVALID), BLOCKED/NOT_RUN, the pair and equivalence gates (Q6 pair reproduces 0.039295 ms), and the constants.

`analysis/preflight_on_setup.json` records the scorer run on the ten Q6 setup roots. It is labelled **SOFTWARE_PREFLIGHT_ON_QUALIFICATION_RAW_NOT_FORMAL** and is not a formal result. An empty 50-row `--all` returned 50 NOT_RUN. Q1's official monitor install hash check PASS. Python compile PASS. Q6 raw was re-verified unchanged after the tests.

Frozen inputs are listed in `runs/s4b_d3_formal_20260928T040232Z/freeze_inputs.sha256`: both protocols, the Q6 manifests and all mounted Q6 `/code` and `/analysis` files, the formal inputs/analysis/schedule, and this report. Runtime versions are in `environment.txt`. This freeze must be committed and pushed, and local HEAD, `origin/main` and remote main must be equal, before the first formal Gazebo trial. If a post-freeze analyzer defect is found, it gets a separately labelled supplementary analysis and never a rewrite. A genuine implementation problem gets a new prospective campaign. S5 remains INSUFFICIENT_EVIDENCE; S6/S7 are not started.
