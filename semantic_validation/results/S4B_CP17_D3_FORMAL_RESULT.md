# S4-B CP17: Docker D3 moving source-silence formal comparison

**Result: `D3_FORMAL_COMPLETE`. All 50 frozen trials were executed and all 50 are `VALID_FORMAL_TRIAL`.** The trials follow the prospective configuration XRROS-S4B-D3F1-1.0.0, frozen and pushed at `edec3d1ec018e3c5f2b3173180f3a4d088344f34` before the first trial. The research policy is XRROS-S4-1.0.0 (SHA-256 `3a40337121f8d687dc68036ff2ffc85a1bc6eda275a700ba7d9e8119cd322969`) and was not changed. The input is synthetic, sent over TCP to the original Docker_Teleop receiver, mapper and bridge, then MoveIt Servo, then Gazebo. This is **not** actual Quest tracking and **not** a physical-robot result. D1 (48/50) and D2 (47/50) are separate and are not pooled here. The CP16 Q6 setup cells are not repetitions.

## Execution

- **Evidence root:** `runs/s4b_d3_formal_20260928T040232Z/`.
- **Command:** `python3 inputs/run_formal.py --start 1 --end 50` ran once, in schedule order.
- **Retries:** 51 attempts were made. Exactly one frozen pre-barrier setup retry occurred. Trial `docker_b1_full_d3r02` failed before the start barrier with `servo_start_failed` (probe exit 13). No source sample, tick or outcome existed at that point. Its retry `…_setup02` reached the barrier and is the formal trial. The first attempt's raw data is retained.
- **Launches:** all 50 formal launches exited with 0. No row was rerun or replaced.
- **Evidence retained:** every attempt keeps these files, and all 51 stopped trial-owned `s4d3f_*` containers are kept:
  - `raw/<attempt>/`;
  - `commands.jsonl`, which holds the full Docker argv;
  - `attempts.jsonl`;
  - the runner stdout/stderr.
- **Manifest:** `runtime_evidence_manifest.sha256` (3,785 files; SHA-256 `942b5804…29cc1a`) verifies (`manifest_verification.txt`). `freeze_inputs.sha256` still verifies.
- **Primary analysis:** the frozen `analysis/d3_formal_audit.py --all` → `analysis/formal_summary.json` (SHA-256 `2cfaf712…12cc`). The frozen analyzer was not edited.

## Comparison validity

- **B0/shim equivalence:** all five repetitions PASS. Across them, the maximum source-index difference is 0.055134 ms and the maximum final six-joint difference is 0.001606 rad. The frozen limits are 5 ms and 0.02 rad.
- **Matched shim-vs-arm pairs:** all 45 are `PASS_SCHEDULE`. The maximum source offset is 0.442 ms.
- **Pre-fault allowed path at `docker:55`:** every pair PASS. The maximum joint difference is 0.00401 rad.
- **Moving at the silence trigger:** every trial was moving, at 0.150–0.254 rad/s.
- **Fixture:** every trial had the same fixture and a common host monotonic clock and boot ID.
- **Source-silence evidence:** every trial had 100 real source samples, 20 genuine no-byte slots and 300 independent ticks.
- **Receiver timeout observed:** the original receiver `stale_timeout` neutral was observed in every instrumented trial.
- **Exact joins:** the analyzer confirmed each of the following in every relevant trial:
  - every eligible active source ID to its Servo callback;
  - every original source and neutral publication to its Mapper consume;
  - in every B2 trial, every original event to its official property, status and guarded receipt.

## Policy results by arm (frozen primary analysis)

In the table below:

- The trigger is the arm's own last **real** source receipt plus 250 ms. For B1 that receipt is the source-side send; for the other arms it is the receiver receipt of `docker:55`.
- Latencies are min / median / max across 5 trials.
- "Ctl nonzero" is the last nonzero controller command after the trigger.
- Frozen limits: decision and request ≤ 50 ms, controller ≤ 300 ms, settle ≤ 1 s.

| Arm / regime | Frozen result (n=5) | Silence decision (ms) | Neutral request (ms) | Ctl nonzero (ms) | Gazebo settled (ms) |
| --- | --- | --- | --- | --- | --- |
| B0 original | control, not scored | — | — | — | 40.4–62.7 (sender-proxy trigger) |
| B0 observational shim | control, not scored | — | — | 0 / 6.3 / 11.1 | 43.1 / 51.7 / 56.1 |
| B1 I_NATIVE | **5 PASS** | 1.31 / 2.22 / 2.89 | 2.53 / 4.02 / 4.29 | 0 | 21.4 / 28.6 / 34.6 |
| B1 I_FULL | **5 PASS** | 0.91 / 1.82 / 22.46 | 2.13 / 3.60 / 25.01 | 0 / 0 / 9.3 | 21.9 / 32.2 / 44.6 |
| B2-native I_NATIVE | 5 UNOBSERVABLE | none (native ticks carry no receipt) | none | 6.7 / 21.0 / 24.7 | 45.5 / 62.7 / 66.9 |
| B2-native I_FULL | **5 FAIL_POLICY** (`NO_EXPLICIT_NEUTRALIZATION_REQUEST`) | 0.93 / 1.19 / 1.39 (official `blocked`/`currently_false`) | none | 22.8 / 26.0 / 26.8 | 61.5 / 68.5 / 73.8 |
| B2-composed I_NATIVE | 5 UNOBSERVABLE | none | none | 4.9 / 19.2 / 26.4 | 40.7 / 64.7 / 73.4 |
| B2-composed I_FULL | **5 PASS** | 0.33 / 0.63 / 1.50 (official verdict) | 2.71 / 2.95 / 5.05 | 0 | 28.4 / 29.7 / 37.1 |
| B3 I_NATIVE | 5 UNOBSERVABLE | none | none | 0 / 6.7 / 7.9 | 38.1 / 45.6 / 58.2 |
| B3 I_FULL | **4 PASS, 1 FAIL_POLICY** (r03, see below) | 0.36 / 0.51 / 0.94 | 0.94 / 1.87 / 6.04 | 0 | 25.4 / 29.6 / 34.0 |

**Mechanism attribution.** Each mechanism is reported separately:

- **B1 (source-side detection):** every B1 stop request was triggered by `B1_SOURCE_SIDE_SILENCE_DETECTION`.
- **B2-composed I_FULL (official verdict):** every stop was triggered by the official ROSMonitoring/TLOracle verdict `currently_false` on a health tick, with a matching `blocked` status. The stop itself was delivered by the common stop adapter. It is **not** native ROSMonitoring actuation.
- **B2-composed health/watchdog:** no B2-composed stop came from the health or heartbeat watchdog.
- **B3 (receiving-side detection):** every B3 stop was triggered by B3's receiving-side detection.
- **Silence tracking:** in every observed silence decision, the tracker stayed bound to `docker:55`, and its trigger was exactly receipt + 250 ms. Ticks and cached publications never refreshed the source receipt.
- **Original receiver timeout:** its neutral appeared 0.4–17.2 ms after its own trigger in every instrumented arm. It is never credited to a defense.
- **Servo incoming-command timeout:** UNOBSERVABLE (no internal event is logged). Servo-input publications continued with a maximum gap of about 17.9 ms after the trigger, so the 250 ms Servo timeout condition was not reached through input absence.

**B2-native vs B2-composed.** These results are the same pattern as D2. B2-native I_FULL detected the silence (the official verdict blocked the tick) but issued no explicit neutralization. Settling within 1 s came after the original receiver timeout and is not credited. B2-composed I_FULL is the same monitor plus ordinary stop integration, and it passed.

**I_NATIVE arms.** The native ROS messages carry no source-receipt time or ID, so the I_NATIVE B2, B2-composed and B3 arms are UNOBSERVABLE. This is not a method failure. They also had no active false rejection. B1 I_NATIVE passes because the source-side gate observes its own transmissions.

**Commands and false rejections after the trigger:**

- Cached prior-source nonzero Servo callbacks after the trigger numbered 0–2 per trial. They are reported and not relabelled.
- No nonzero command came from a post-silence source.
- There was no explicit false rejection among the valid active IDs 36–55, except the single B3 I_FULL r03 verdict below.

## Post-freeze analyzer finding: B3 I_FULL r03

The frozen result stays `docker_b3_full_d3r03` = FAIL_POLICY (`NORMAL_ACTIVE_FALSE_REJECTION`). Detection took 0.65 ms, the request 1.87 ms, and settling 32.0 ms; all of these pass.

The raw evidence shows what was rejected: one **cached repeat** of `docker:55`. B3 evaluated it **0.54 ms after** the local silence trigger, at a source age of 251.06 ms, and applied `STALE_SOURCE`. That sample is no longer fresh under F250. The frozen denominator counts any verdict whose parent is IDs 36–55, whenever it was made. XRROS-S4-1.0.0 §8 defines normal input as valid and **fresh**.

A separately labelled supplementary recount is in `analysis/supplementary_fresh_eligible.py` → `supplementary_fresh_eligible.json` (`SUPPLEMENTARY_POST_FREEZE_NOT_PRIMARY`). It counts only verdicts made before the trigger with age ≤ 250 ms. In that recount, r03 becomes PASS_POLICY and no other trial changes. The primary result is not rewritten. B3 I_FULL is therefore 4/5 PASS under the frozen analyzer and 5/5 under the supplementary definition, and both are reported.

## Latency and overhead (descriptive only)

**Latency.** Source-to-first-Servo-callback p95 per trial is roughly 10–43 ms. Paired p95 deltas against the same-repetition shim have these medians:

| Arm | Native (ms) | Full (ms) |
| --- | --- | --- |
| B1 | −7.3 | −0.4 |
| B2-native | +15.7 | +14.1 |
| B2-composed | +11.4 | +16.0 |
| B3 | +0.1 | +1.2 |

These include waiting for repeated commands. They are **not** the exact added gate/transport latency, which remains UNKNOWN, as does the monitor's internal post-verdict publish time. The registered ≤20 ms practicality target is therefore neither passed nor failed.

**CPU.** Total observed participant CPU over the six-second capture:

- B0: 6.44–6.73 s.
- Shim: median 6.89 s.

Paired deltas against the shim, as medians:

| Arm | Native (s) | Full (s) |
| --- | --- | --- |
| B1 | +0.43 | +0.38 |
| B3 | +0.50 | +0.32 |
| B2-native | +2.15 | +2.03 |
| B2-composed | +2.40 | +2.10 |

**RSS.** Median per-process-tree peaks:

| Process tree | Median peak RSS |
| --- | --- |
| Official monitor | ~85 MiB |
| Oracle | ~20 MiB |
| Stop adapter | ~57 MiB |
| B1 gate | ~11 MiB |
| Observed nodes | ~67–69 MiB |

These peaks come from different processes at different times and are not summed. Per-label figures are in each trial's JSON.

## Interpretation and boundaries

With identical synthetic moving source-silence input and full information (I_FULL), three existing configurations met the frozen D3 stop policy in all valid trials, except the one B3 frozen-scorer classification explained above:

- B1, the source gate;
- B2-composed, official ROSMonitoring plus ordinary stop integration;
- B3, direct receiving-side validation.

The original Docker path itself neutralizes within ~40–63 ms through its receiver timeout. B2-native filtering alone does not issue an explicit neutralization. For D3 in this synthetic Docker setting, the result is consistent with **NO_METHOD_GAP for the tested condition**: ordinary watchdog and stop integration closes the B2-native gap.

These results do not generalize to actual Quest, OpenVR or physical robots. No per-source parent for a specific controller command or joint sample is claimed.

S5 remains INSUFFICIENT_EVIDENCE: D1 and D2 are partial, and D4–D6, C-ID, C-MON and OpenVR are not yet formally compared. S6 and S7 are not started.
