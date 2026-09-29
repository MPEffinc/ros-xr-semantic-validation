# S4-B CP27: Docker C-ID source state/command binding comparison (scoped)

**Result: `CID_SCOPED_FORMAL_COMPLETE` — 120/120 executed, 120/120 `VALID_FORMAL_TRIAL`.** The configuration is the frozen scoped XRROS-S4B-CIDF1-1.0.0, pushed at `f22adc4002e887edce7f7b295e83118913828ccf` before the first trial. Research policy XRROS-S4-1.0.0 is unchanged. I_NATIVE formal repetitions are registered NOT_RUN. The old-generation kind reuses the D5 formal evidence and is not counted here. The input is synthetic, with a trusted source; there is no actual Quest and no physical robot.

## Execution and validity

**Evidence.** All files are in `runs/s4b_cid_formal_20260928T160547Z/`:

- `raw/`: 121 attempt directories;
- `attempts.jsonl` and `commands.jsonl`;
- the frozen `analysis/cid_formal_audit.py` and its output `formal_summary.json`;
- `runtime_evidence_manifest.sha256`, which verifies.

**Retry.** 121 attempts were made. Exactly one frozen pre-barrier setup retry occurred. Row 101, `docker_b2c_full_MISMATCH_cidr05`, reported `servo_start_failed` (probe exit 13) before any source sample existed. `_setup02` is its formal trial, and the first attempt is retained. All 120 formal attempts exited 0. No row was rerun or replaced.

**Comparison validity.** All 20 B0/shim pairs pass (maximum 0.133 ms, 0.0032 rad). All 80 matched schedules pass. The largest pre-fault joint difference against the shim is 0.0088 rad.

## Results (5 repetitions per cell; one fault injected at slot 50 while moving)

| Arm (I_FULL) | MISSING_FIELD | MISSING_ID | DUPLICATE_ID | MISMATCH |
| --- | --- | --- | --- | --- |
| B1 source gate | 5 PASS | 5 PASS | 5 PASS | 5 PASS |
| B2-composed (official verdict + ordinary stop) | 5 PASS | 5 PASS | 5 PASS | 5 PASS |
| B3 receiving-side | 5 PASS | 5 PASS | 5 PASS | 5 PASS |
| B2-native (official filter only) | 5 FAIL | 5 FAIL | 5 FAIL | 5 FAIL |

**Rejection reasons.** Every defense rejected the injected event with the kind's registered reason: `MISSING_REQUIRED_FIELD`, `MISSING_SOURCE_EVENT_ID`, `DUPLICATE_SOURCE_EVENT_ID` or `STATE_COMMAND_MISMATCH`.

**Timing.** Measured from the injected sample's local arrival:

| Arm | Decision | Neutralization request | Settled |
| --- | --- | --- | --- |
| B1 | ≤ 0.10 ms | 0.2–5.2 ms | 19–38 ms |
| B2-composed | 1.9–17.3 ms | 2.6–21.0 ms | 22–52 ms |
| B3 | 5.1–16.8 ms | 6.1–21.1 ms | 25–52 ms |

**B2-native.** All 20 failures are `P2_NO_EXPLICIT_NEUTRALIZATION_REQUEST`. The official verdict blocked the injected event with the correct reason, and no injected command reached Servo. Settling came only through the original timeout, after 280–312 ms.

**Across all 80 defense trials:**

- no injected event was accepted at any evaluation, and no nonzero Servo command derived from it;
- there was no held-grip restart (R_EXPLICIT latch) and no false rejection of normal input before the injection.

**Cached repeats and duplicates.** The duplicate check operated on **new ingestion** only. Cached republications of accepted samples, repeated 2–3 times per sample at 60 Hz, were never flagged. This held for every accepted sample in every trial; any flag would have been a P1 false rejection.

**Original path (shim).** The shim accepted every injected fault. In every repetition of every kind, 3 nonzero commands from the injected sample and 15–16 from the subsequent held samples reached Servo. In MISMATCH, this includes the x=.65 command that conflicts with the bound state.

**Mechanism attribution.** The three passing arms detected the fault in different places:

- B1: its source-side binding decision;
- B2-composed: the official ROSMonitoring `currently_false` verdict;
- B3: its receiving-side binding decision.

In every case the common stop adapter actuated the stop.

**Overhead (descriptive).** Median observed CPU delta against the shim, per 6 s capture:

| Arm | CPU delta |
| --- | --- |
| B3 | +0.21 s |
| B1 | +0.27 s |
| B2-native | +1.84 s |
| B2-composed | +1.89 s |

The exact added latency is UNKNOWN.

## Interpretation and boundaries

With I_FULL information, an ordinary binding contract closes C-ID in these tested synthetic Docker conditions:

- a capture-time reference hash over the source ID, generation, stamp, state and intended command;
- a check value recomputed from the command actually forwarded;
- duplicate detection on new ingestion.

Existing configurations enforce it, rejecting before actuation and neutralizing:

- a direct source gate (B1);
- a direct receiving-side check (B3);
- official ROSMonitoring with ordinary stop integration (B2-composed).

The old-generation kind was already established by D5 formal.

For these conditions the result is **NO_METHOD_GAP**. The original path and native interface lack the binding information. B2-native filtering does not neutralize.

What this does not cover:

- an adversarial source forging the binding (the source is trusted by protocol);
- other injection timings;
- formal native repetitions;
- OpenVR;
- actual Quest or physical robots.

S5 remains INSUFFICIENT_EVIDENCE.
