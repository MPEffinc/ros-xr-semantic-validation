# S4-B CP19: Docker D4 source-freshness formal comparison

**Result: `D4_FORMAL_COMPLETE` — 630/630 executed, 630/630 `VALID_FORMAL_TRIAL`.** The frozen configuration XRROS-S4B-D4F1-1.0.0 was committed and pushed at `43b5f7bc5480ae3e720caab1201c4f7d6e5e9824` before the first formal trial. Research policy XRROS-S4-1.0.0 (SHA-256 `3a40337121f8d687dc68036ff2ffc85a1bc6eda275a700ba7d9e8119cd322969`) is unchanged.

The evidence is **synthetic** input through the original Docker receiver/mapper/bridge → MoveIt Servo → Gazebo path. It is not actual Quest data and not a physical robot. D1, D2 and D3 are separate and not pooled. The D4Q1/D4Q2 setup cells are not formal repetitions.

## Execution and validity

**Evidence location:** `runs/s4b_d4_formal_20260928T053240Z/`. The directory contains:

- `raw/<trial>/`, 630 directories, 5.8 GB;
- `commands.jsonl` and `attempts.jsonl`;
- runner stdout/stderr;
- the frozen `analysis/d4_formal_audit.py`, whose output is `analysis/formal_summary.json`;
- `runtime_evidence_manifest.sha256`, 47,872 files, verified.

**Run conduct:**

- All 630 rows ran once, in schedule order.
- Every first attempt reached the start barrier and exited 0.
- No setup retry was needed.
- No row was rerun or replaced.
- All `s4d4f_*` containers are stopped and retained.

**Comparison validity:**

- All 35 B0/shim pairs PASS. The maximum source-index difference is 0.288 ms and the maximum final six-joint difference is 0.0056 rad.
- All 560 matched arm-vs-shim schedules PASS.

**Disclosed deviation.** The D4-L host-regression suite (TCP loopback only, no Gazebo) ran on the host from about 05:40:30 to 05:44:20 UTC. That overlaps formal rows 9–18, all in repetition 1 under A050:

- `b0_full_F250`, `b1_full_F100`, `b1_full_F250`;
- `b2_full_F100`, `b2_full_F250`, `b2_full_F500`;
- `b3_full_F100`, `b3_full_F250`;
- `shim_full_F250`, `b1_native_F250`.

These trials are valid and are **not** reclassified. Their timing and CPU values were measured under this additional host load. Since then, the rule is that no concurrent workload runs during a timing-sensitive campaign.

## Frozen primary policy results

Each I_FULL cell below counts PASS/FAIL over 5 repetitions. Conditions are source age 0, 50, 150, 350 or 750 ms, historical epoch 1.0, or +1 s future.

| Arm | Profile | A000 | A050 | A150 | A350 | A750 | H1P0 | FUT1S |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| B1 source gate | F100/F250/F500 | 5/0 each | 5/0 | 5/0 | 5/0 | 5/0 | 5/0 | 5/0 |
| B2-native (official filter only) | F100 | 5/0 | 5/0 | **0/5** | **0/5** | **0/5** | **0/5** | **0/5** |
| B2-native | F250 | 5/0 | 5/0 | 5/0 | **0/5** | **0/5** | **0/5** | **0/5** |
| B2-native | F500 | 5/0 | 5/0 | 5/0 | 5/0 | **0/5** | **0/5** | **0/5** |
| B2-composed | F100 | 5/0 | **2/3** | 5/0 | 5/0 | 5/0 | 5/0 | 5/0 |
| B2-composed | F250, F500 | 5/0 | 5/0 | 5/0 | 5/0 | 5/0 | 5/0 | 5/0 |
| B3 receiving-side | F100/F250/F500 | 5/0 each | 5/0 | 5/0 | 5/0 | 5/0 | 5/0 | 5/0 |

- **B2-native FAILs (60):** every one is `NO_EXPLICIT_NEUTRALIZATION_REQUEST`. The official verdict blocked every over-budget event, with no false acceptance and no forbidden motion, but it never requested a stop. This matches D2 and D3.
- **I_NATIVE:** B1, B2, B2-composed and B3 under I_NATIVE are **UNOBSERVABLE** in all 140 trials. Their native interfaces carry no source time.
- **B0 original:** moved in 35/35 trials (0.28–0.29 rad), including 750 ms-old, historical and future stamps. The original path does not read the source timestamp.
- **Native consequences:** in the over-budget conditions, the native arms let about 60 over-budget samples reach nonzero Servo commands per trial, by the analyzer's own age. This is reported as a consequence, not as a native-defense failure.

**Rejection cases (60 trials per I_FULL arm).** Values are min / median / max ms after the local trigger.

| Arm | Decision | Neutral request | Gazebo settled | False accept / forbidden callbacks | Attribution |
| --- | --- | --- | --- | --- | --- |
| B1 | 0.03 / 0.04 / 0.07 | 0.24 / 3.17 / 5.36 | 0.3 / 9.1 / 16.1 | 0 / 0 | B1 source-side decision |
| B2-native | 2.17 / 8.98 / 17.38 | none | 0.13 / 10.4 / 17.1 | 0 / 0 | — |
| B2-composed | 2.11 / 9.44 / 17.26 | 3.22 / 13.21 / 22.41 | 0.51 / 9.9 / 16.8 | 0 / 0 | Official `currently_false` verdict; actuation by the common stop adapter, not native ROSMonitoring |
| B3 | 1.41 / 13.16 / 18.18 | 2.11 / 15.37 / 22.74 | 0.32 / 8.6 / 16.9 | 0 / 0 | B3 receiving-side decision |

**Acceptance cases** (45 per I_FULL arm):

- zero false rejections;
- motion and the allowed-path check against the shim within 0.02 rad, with the one exception below.

## Post-freeze analyzer finding (supplementary; primary unchanged)

**Affected trials.** The 3 B2-composed A050/F100 FAILs (r01, r02, r05) are `UNEXPECTED_NEUTRALIZATION…` + `ADMITTED_MOTION_ABSENT` + `ALLOWED_PATH…`.

**What happened.** Because the receiver republishes at 60 Hz, the cached copies of each 50 ms-old sample reach **100.0–100.6 ms** of source age at the official oracle. That is inside the registered ±1 ms uncertainty band around F100. The strict predicate (> 100 ms) rejected those copies, and the composed stop followed 1.0–1.5 ms later.

**Why the frozen label is wrong.** XRROS-S4-1.0.0 §5 defines ages that straddle the uncertainty bound as UNKNOWN. The frozen scorer, however, expects a rejection only when *every* evaluation of a sample is over budget, so it labels these stops "unexpected".

**Supplementary recount.** `analysis/supplementary_boundary_band.py` → `supplementary_boundary_band.json`, labelled `SUPPLEMENTARY_POST_FREEZE_NOT_PRIMARY`. It uses a per-decision expectation and marks a stop caused solely by an in-band rejection as **UNKNOWN_BOUNDARY_STRADDLE**. Only these 3 trials change. B2-composed A050/F100 is therefore:

- **2 PASS / 3 FAIL** under the frozen primary analyzer;
- **2 PASS / 3 UNKNOWN** under the supplementary analyzer.

Both are reported. The same boundary also caused 107 UNKNOWN-band decisions among B2-composed acceptance trials, which are not scored.

## Latency and overhead (descriptive only)

Paired median p95 source→first-Servo-callback deltas against the shim:

| Arm | Delta |
| --- | --- |
| B1 | +1.0 to +2.9 ms |
| B3 | +0.5 to +5.3 ms |
| B2-native | +9.7 to +15.4 ms |
| B2-composed | +8.4 to +13.5 ms |

These include cached-command waiting. They are **not** the exact added gate latency, which remains UNKNOWN, as does the monitor's internal publish time.

Median observed-CPU deltas against the shim, per 6 s capture:

| Arm | CPU delta |
| --- | --- |
| B1 | +0.3 to +0.6 s |
| B3 | +0.2 to +0.6 s |
| B2-native | +1.7 to +2.0 s |
| B2-composed | +1.7 to +2.5 s |

Per-process RSS is in each trial's JSON.

## Interpretation and boundaries

When source timestamps are already old at creation and delivered promptly, three I_FULL configurations enforced F100, F250 and F500 with zero false acceptance and zero false rejection of fresh input:

- B1 at the source;
- B2-composed, the official monitor plus ordinary stop integration;
- B3 at the receiving side.

They also stopped within the 50 ms / 300 ms / 1 s limits. The historical-epoch and future-stamp anomalies were handled the same way. The original path and all I_NATIVE configurations cannot observe source age. B2-native blocks stale events but does not neutralize.

For these tested synthetic Docker conditions, this is consistent with **NO_METHOD_GAP**: ordinary metadata transport plus a direct check or composed stop suffices.

What this does not show:

- It does not test delay introduced **after** the source decision. That is D4-L, where B1's placement matters.
- It does not generalize to actual Quest clocks, OpenVR or physical robots.
- It claims no per-source joint causation.

S5 remains INSUFFICIENT_EVIDENCE.
