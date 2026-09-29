# XRROS-S4B-OVRF1-1.0.0 result — scoped OpenVR W0–W5 existing-defense comparison

**Primary result:** scored by the analyzer frozen at 6961fa0 without modification.

- **Roots:** `runs/s4b_ovr_formal_20260928T192004Z/`; scores in `analysis/formal_summary.json`.
- **Execution:** 205 trials, run sequentially with no concurrent load. All 205 reached the barrier on their first attempt; no retries.
- **Validity:** **198 `VALID_FORMAL_TRIAL`, 7 `INVALID_COMPARISON`.**
- **Controls:** all 30 B0/shim pairs PASS (≤ 0.357 ms, ≤ 0.00044 rad).
- **Scope:** I_NATIVE and the redundant cells listed in the freeze are NOT_RUN. This is a scoped study.
- **Evidence limits:** fake OpenVR API only; no Quest/SteamVR tracking loss; no physical robot.

## Invalid trials (retained; frozen validity rule)

| Trial | Reason | Observed cause |
| --- | --- | --- |
| B2-composed W4 R_AUTO r01, W4 R_AUTO r05, W5 R_AUTO r02 | Source polls 0–599 not completed inside the capture | The production timer stalled for up to 333 ms. The official monitor path back-pressured the source process, so the source schedule itself changed. |
| B2-composed W4 R_EXPLICIT r01, W1 r03, W5 R_AUTO r02 | Servo callback exact join incomplete | After an official-monitor stall, the stripper re-published in bursts (under 1 ms apart), and some poses never produced a Servo callback. |
| B2-native W1 r03 | Positive-control motion absent | The official monitor processed almost nothing. |
| **B2-ST-composed** W5 R_EXPLICIT r04 | Servo callback exact join incomplete | The first 100 stripper poses (polls 50–149) produced no Servo callback, although they were published at a normal 20 ms spacing. This is an unexplained delivery-path anomaly and is reported as such. |

## Primary policy outcome, 5 repetitions per cell (valid trials)

| Case | B0 (original) | B1 | B3 | B2-native | B2-composed | B2-ST-composed (diagnostic, not ROSMonitoring) |
| --- | --- | --- | --- | --- | --- | --- |
| W1 valid | control | PASS 5/5 | PASS 5/5 | PASS 3, FAIL 1, invalid 1 | PASS 1, FAIL 3, invalid 1 | PASS 5/5 |
| W2 result = 201 | **FAIL 5/5**: the original ignores `eTrackingResult` (moves about 1.5 rad) | PASS 5/5 (request 4.4–4.8 ms) | PASS 5/5 | FAIL 5/5 (no neutralization) | PASS 4, straddle 1 (49.4 ms) | NOT_RUN |
| W3 `bPoseIsValid` = false | **PASS 5/5**: the original's own check | PASS 5/5 | PASS 5/5 | NOT_RUN | PASS 3, FAIL 2 (official latency) | NOT_RUN |
| W4 R_EXPLICIT | FAIL 5/5 | FAIL 5/5, R8 only | FAIL 5/5, R8 only | FAIL 5/5 | FAIL 4, invalid 1 | FAIL 5/5, R8 only |
| W4 R_AUTO | — | FAIL 5/5 | FAIL 5/5 | NOT_RUN | FAIL 3, invalid 2 | FAIL 5/5 |
| W5 R_EXPLICIT | FAIL 5/5 | FAIL 5/5 (R8, plus R1 in r01) | FAIL 5/5 (same) | NOT_RUN | FAIL 5/5 | FAIL 4, invalid 1 |
| W5 R_AUTO | — | FAIL 5/5 | FAIL 5/5 | NOT_RUN | FAIL 4, invalid 1 | FAIL 5/5 |

**Timing of the timely defenses** (B1, B3, B2-ST-composed) in W4/W5:

- invalidation decision 0.1–0.6 ms after the poll-150 acquisition;
- common-adapter neutralization request 3.1–5.1 ms after it;
- settled 324–434 ms after the fault;
- no forbidden sample delivered;
- R_EXPLICIT re-arm exactly at poll 250, with resume 3.1–4.9 ms after it.

**Original path (B0)** in W4/W5: no invalidation; Servo motion continued past T + 300 ms; not settled by T + 1 s (about 5.1 s); held-grip restart reached Servo; R8.

## Supplementary analysis (post-outcome, separately labelled; `analysis/supplementary_summary.json`)

Three scorer defects were found after the run.

- **S1: R_AUTO delivery denominator.** It included the released polls 240–249, on which the original never publishes, so ≥ 99% delivery was unreachable.
- **S2: R_AUTO re-arm poll.** The registered rule is time-based: 500 ms continuously valid. The scorer instead fixed poll 225. Timer jitter makes 226 the first poll that meets the dwell in many trials.
- **S3: slot-149 comparison in W5 r01.** The W5 r01 shim itself deviated from B0 by 0.159 rad at slot 149, while every arm matched B0 within 0.0001–0.003 rad. The R1 joint violation there is a control anomaly.

With only these corrections (38 trials change their violation lists; 0 change PASS/FAIL), **every one of the 60 valid B1, B3 and B2-ST-composed W4/W5 trials fails only R8**, the added displacement at a fresh reference:

- R_EXPLICIT, new reference: 0.03–0.06 rad within polls 250–260.
- R_AUTO, held-grip auto restart: 0.02–0.04 rad within polls 225–240.

All defense-controlled criteria pass: decision, neutralization, settling, forbidden delivery, re-arm and recovered admission/delivery.

## Attribution

1. **Original OpenVR path.**
   - It reads `bPoseIsValid`, so W3 is blocked by the original itself.
   - It ignores `eTrackingResult`, so W2 moves.
   - It has no latch: after recovery it restarts with the grip held.
   - It has no explicit neutralization. After it stops publishing, Servo keeps tracking the last target for about 5 s.
2. **Ordinary source gate (B1) and publish-point check (B3) with the common pause-plus-hold adapter.** These solve every tested defense-controlled requirement on OpenVR within about 5 ms.
3. **R8 displacement: missing recovery-reference logic in the application, not a method limitation.** R8 fails in every arm, including B0. The original `quest_teleop.py` maps every engage to the fixed absolute target (0.4, 0, 0.3). Under R_AUTO it continues with its old offset, so the resumed Servo catches up to the pre-fault target. No stop/forward-only defense can remove this displacement without transforming targets, and the protocol forbids the adapter from doing that.
4. **Official ROSMonitoring on Jazzy (B2).**
   - The failures are attributed to the officially generated `MultiThreadedExecutor()` monitor:
     - no decision by capture end (up to 597 unprocessed envelopes in a trial);
     - decisions arriving over 50 ms late (up to 7.6 s);
     - stale-decision latches that rejected valid and recovered input;
     - back-pressure onto the source;
     - bursts that dropped Servo inputs.
   - The single-threaded diagnostic copy, B2-ST, which changes only the executor line, performs like B1/B3: W1 5/5, W4 R_EXPLICIT R8 only.
   - This separates an **implementation/platform limitation of the generated monitor under Jazzy rclpy** from the runtime-verification method. For this case the result is consistent with NO_METHOD_GAP.
   - B2-native additionally lacks explicit neutralization.

**Not supported by this result:** real SteamVR tracking-loss semantics; physical robots; I_NATIVE; other fault times; any reliability guarantee (5 repetitions per cell).
