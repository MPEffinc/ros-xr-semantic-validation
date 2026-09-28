# XRROS-S4B-OVRF1-1.0.0 — prospective scoped OpenVR W0–W5 formal freeze and design report

This applies XRROS-S4-1.0.0 (SHA-256 `3a40337121f8d687dc68036ff2ffc85a1bc6eda275a700ba7d9e8119cd322969`) without changing it.

- **Formal root:** `runs/s4b_ovr_formal_20260928T192004Z/`.
- **Setup basis:** OpenVR Q1 (`S4B_OVR_Q1_QUALIFICATION_RESULT.md`). The formal runner mounts the frozen Q1 code read-only (`/code`, `/analysis`, official monitor install, trial-local deps), so the formal trials run exactly the qualified code.
- **Evidence scope:** fake OpenVR API only. No Quest/SteamVR tracking-loss experiment and no physical robot.

## Design report (minimum-sufficient scaling)

**Candidate matrix:** 6 cases × {B0, shim, B1, B2-native, B2-composed, B3, B2-ST-composed} × {R_EXPLICIT, R_AUTO for W4/W5} × {I_FULL, I_NATIVE}. This is about 112 cells, or 560 trials.

**Essential cells, 41 per repetition × 5 = 205 trials:**

| Case | Arms | Why |
| --- | --- | --- |
| W0 | B0, shim | Idle control. With no grip, no defense has a decision to make. |
| W1 | B0, shim, B1, B2-native, B2-composed, B3, B2-ST-composed | False rejection, delivery, allowed path. Official-monitor throughput is observable here. |
| W2 (result = 201) | B0, shim, B1, B2-native, B2-composed, B3 | The original ignores `eTrackingResult`, so B0 is expected to move. Tests blocking and explicit neutralization. |
| W3 (`bPoseIsValid` = false) | B0, shim, B1, B2-composed, B3 | The original's own check; tests defense neutralization. |
| W4 R_EXPLICIT | all 7 | Invalidation while moving, stop, latch, re-arm, fresh reference. |
| W4 R_AUTO | B1, B2-composed, B3, B2-ST-composed | Only the policy-dependent arms. |
| W5 R_EXPLICIT | B0, shim, B1, B2-composed, B3, B2-ST-composed | Disconnect plus harness generation. |
| W5 R_AUTO | B1, B2-composed, B3, B2-ST-composed | Only the policy-dependent arms. |

**Redundant cells, registered NOT_RUN (scoped):**

- W0 defense arms: no decision to score.
- W3 B2-native: the original never publishes, so the native filter has nothing to filter.
- B2-ST in W2/W3: throughput does not matter where blocking starts at the first grip sample.
- B2-native in W5 and in all R_AUTO cells: its missing stop integration is already established in W1, W2 and W4 (and in every Docker case).
- R_AUTO B0 and shim: independent of the re-arm policy, so they reuse R_EXPLICIT.
- All of I_NATIVE:
  - B2's native payload is `PoseStamped`, which carries no state, so it is UNOBSERVABLE by construction.
  - B1 and B3 native API fields give the same validity/result/connection decisions, except for source time and generation, which are UNOBSERVABLE.
- C-ID and C-MON OpenVR coverage: registered as a separate campaign after this freeze.

**Host-only versus Gazebo:** policy, fixture and component behavior are host/container-only (8/8 policy tests plus component runs). Policy outcomes need Gazebo.

**Runtime:** about 46 s per trial, so roughly 2.6 h for 205 trials, run sequentially with no concurrent CPU load.

**Claims supported:**

- normal acceptance and false rejection per arm;
- the original's `result`/`bPoseIsValid` handling;
- invalidation-to-neutralization timing;
- held-grip restart;
- re-arm correctness under R_EXPLICIT and R_AUTO;
- fresh-reference displacement;
- the effect of the official Jazzy monitor's executor throughput, separated from the B2-ST diagnostic.

**Claims excluded:** real SteamVR semantics; physical robot outcomes; other fault times; I_NATIVE; any reliability guarantee.

## Scorer (`analysis/ovr_formal_audit.py`, tests 5/5 on the Q1 setup raw)

**Validity:**

- The frozen Q1 `inspect()`.
- One prospectively registered B2 exception: envelopes that never received an official status by capture end are a measured B2 outcome (official-monitor processing loss), not invalidity. This requires every envelope that did receive a status to have exactly one property row and a matching receipt.
- The per-repetition, per-case B0/shim pair (5 ms, 0.02 rad).
- Every arm against the shim at ≤ 5 ms matched poll timing.

**Policy:**

- **W1:** N1 no valid grip sample 50–499 not admitted; N2 ≥ 99% delivered to a Servo callback; N3 no neutralization; N4 final joint position within 0.02 rad of the shim.
- **W2/W3:** F1 no forbidden pose delivered (B0: none reaches Servo input); F2 excursion ≤ 0.01 rad. Defense arms additionally need F3: poll-50 rejection and neutralization request ≤ 50 ms after acquisition, plus stop reply and hold. B2-native records `F3_NO_EXPLICIT_NEUTRALIZATION`.
- **W4/W5,** with T = acquisition of poll 150:
  - R1: pre-fault samples admitted and delivered; slot-149 joints within 0.02 rad of the shim.
  - R2: poll-150 rejection ≤ 50 ms.
  - R3: neutralization request ≤ 50 ms, with stop reply and hold.
  - R4: no Servo motion command (|velocity| > 1e-6, adapter holds excluded) from T + 300 ms until resume. Without a resume, the window ends at capture end for stop-integrated arms, or at the registered re-arm poll for B0 and B2-native.
  - R5: settled by T + 1 s.
  - R6: no forbidden grip sample delivered (R_EXPLICIT 150–249, R_AUTO 150–224).
  - R7: re-arm exactly at the registered poll (250 for R_EXPLICIT, 225 for R_AUTO) with resume ≤ 50 ms; all recovered samples admitted; ≥ 99% delivered.
  - R8: fresh reference adds ≤ 0.01 rad within [T(250), T(260)], and for R_AUTO also within [T(225), T(240)].
- **Boundary band:** ±1 ms around each 50 ms bound gives UNKNOWN_BOUNDARY_STRADDLE.
- **Attribution per violation:**
  - ORIGINAL_*;
  - OFFICIAL_MONITOR_NO_DECISION / LATENCY / LATE_DECISION_STALE(_LATCH);
  - APPLICATION_ABSOLUTE_REFERENCE_MAPPING (R8);
  - COMMON_STOP_ADAPTER;
  - B2_NATIVE_HAS_NO_STOP_INTEGRATION;
  - DEFENSE_DECISION.

**Q1 fixture behavior** (setup evidence, not outcomes):

- W1: B1, B2-composed, B3 and B2-ST-composed PASS. B2-native FAILs, attributed to OFFICIAL_MONITOR_NO_DECISION (the halt).
- W4: B1, B3 and B2-ST-composed fail only R8 (APPLICATION_ABSOLUTE_REFERENCE_MAPPING). B2-composed fails R7 (OFFICIAL_MONITOR_LATE_DECISION_STALE_LATCH). B0 fails R2–R6 and R8.
- W2: B2-composed fails F3 (OFFICIAL_MONITOR_LATENCY, 111 ms).

The empty-schedule audit gives 205 NOT_RUN.

## Execution

Setup retries are allowed only without a barrier, at most two per cell. Execution stops after two consecutive post-barrier nonzero exits. Q1 setup raw data are excluded from the formal results.
