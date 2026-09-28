# S4-B CP23: Docker D5 reconnect/generation isolation comparison (scoped)

**Result: `D5_SCOPED_FORMAL_COMPLETE`. All 50 trials executed, and all 50 are `VALID_FORMAL_TRIAL`.** The configuration is the frozen scoped XRROS-S4B-D5F1-1.0.0, pushed at `14b56a8062ec0e6c615c4b835498e77d719b327b` before the first trial. Research policy XRROS-S4-1.0.0 is unchanged.

The I_NATIVE formal repetitions (4 arms × 2 policies × 5) are registered NOT_RUN. They are unobservable by construction, and their setup evidence is in D5Q1. The input is synthetic, over the original Docker path to Servo and Gazebo. There is no actual Quest reconnect and no physical robot. D1–D4-L are not pooled.

## Execution and validity

**Evidence.** Everything is under `runs/s4b_d5_formal_20260928T133632Z/`:

- `raw/`: 50 trial directories, 651 MB;
- `attempts.jsonl` and `commands.jsonl`;
- the frozen scorer `analysis/d5_formal_audit.py` and its output `formal_summary.json`;
- `runtime_evidence_manifest.sha256`: 3,784 files, verified.

**Run conduct.** All 50 rows ran once, in order. Every first attempt reached the start barrier and exited 0. There were no retries, no reruns and no concurrent workload.

**Equivalence checks.**

- All 5 B0/shim pairs PASS, with a maximum of 1.243 ms and 0.0042 rad.
- All 40 matched schedules PASS.
- The maximum pre-fault joint difference against the shim is 0.0076 rad.

## Results (5 repetitions per cell)

| Arm (I_FULL) | R_EXPLICIT | R_AUTO | Disconnect → decision / request / settle | Re-arm |
| --- | --- | --- | --- | --- |
| **B1 source gate** | 5 PASS | 5 PASS | 0 / 0.6–5.0 / 19–37 ms | R_EXPLICIT always on docker:94; R_AUTO on docker:83–84, 500–550 ms after the first valid gen-2 sample following the replay |
| **B2-composed** (official monitor + ordinary stop) | 5 PASS | 5 PASS | 2.6–16.9 / 4.9–21.4 / 31–55 ms | R_EXPLICIT on 94; R_AUTO on 83 (500.1–517.4 ms) |
| **B3 receiving side** | 5 PASS | 5 PASS | 2.5–15.7 / 7.3–21.0 / 31–47 ms | R_EXPLICIT on 94; R_AUTO on 83 (500.1–516.6 ms) |
| **B2-native** (official filter only) | 5 **FAIL** | 5 **FAIL** | 1.0–17.6 / **none** / 240–272 ms | 94 / 83 |

All B2-native failures are `P2_NO_EXPLICIT_NEUTRALIZATION_REQUEST`. The official verdict blocked the disconnected copies, the old generation and the held grip, and it re-armed correctly. Settling came about 250 ms later, only through the original receiver/bridge timeout, which is not credited.

**Consequences in every I_FULL defense trial, all 40:**

- no gen-1 replay (docker:72) reached Servo;
- the held grip produced no nonzero command before the registered re-arm;
- the reference jump after re-arm was below 1e-9 rad;
- the subsequent +0.15 X movement happened, about 0.39 rad, with all 60 derived callbacks nonzero;
- there were no false rejections before the disconnect.

**Mechanism attribution.** The mechanisms are reported separately:

- B1's source-side decision;
- the official ROSMonitoring `currently_false` verdict (B2-composed);
- B3's receiving-side decision;
- the common stop adapter, which carries out the stop and the resume and is not credited to native ROSMonitoring.

The resume always followed the defense's own first allowed teleop decision after re-arm. Re-arm came 1.36–1.38 s (R_AUTO) or 1.90–1.91 s (R_EXPLICIT) after the disconnect.

**Original path (shim).** In every repetition the original path let 3 replay-derived nonzero commands and 49–50 held-grip gen-2 commands reach Servo before any release or edge. The original therefore accepts the old generation and restarts immediately on held grip. That is exactly the gap the registered policy targets.

**Overhead (descriptive).** Median observed-CPU deltas against the shim over the 10 s capture:

| Arm | CPU delta |
| --- | --- |
| B1 | +0.7 / +0.9 s |
| B3 | +0.8 / +0.8 s |
| B2-native | +2.8 / +2.8 s |
| B2-composed | +3.2 / +3.7 s |

The two values are R_EXPLICIT / R_AUTO. The exact added gate latency is UNKNOWN.

## Interpretation and boundaries

Under I_FULL, where the source sample carries its generation and the receiver's observed connection state is carried with it, ordinary existing configurations met every registered D5 requirement under **both** recovery policies:

- a direct source gate (B1);
- a direct receiving-side check (B3);
- the official ROSMonitoring verdict with ordinary stop/resume integration (B2-composed).

The requirements met were:

- a stop on disconnect while moving;
- rejection of the old generation;
- no held-grip restart under R_EXPLICIT;
- a dwell-limited automatic restart under R_AUTO;
- a fresh reference with no jump;
- the subsequent valid movement.

The original path and the native interface lack this information. B2-native filtering alone does not neutralize.

For these tested synthetic Docker conditions, the result is consistent with **NO_METHOD_GAP**. The added cost is a conventional state machine and metadata transport.

What this does not cover:

- formal I_NATIVE repetitions;
- other disconnect or reconnect timings;
- authenticated generations, since the source is trusted;
- actual Quest or ALVR reconnects;
- OpenVR;
- physical robots.

S5 remains INSUFFICIENT_EVIDENCE.
