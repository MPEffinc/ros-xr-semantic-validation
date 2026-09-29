# S5 evidence audit — do the S4 existing-defense results leave an independently defensible method gap?

**Scope.** This audit checks the S4 existing-defense campaigns against research protocol XRROS-S4-1.0.0 (SHA-256 `3a40337121f8d687dc68036ff2ffc85a1bc6eda275a700ba7d9e8119cd322969`). It was performed on 2026-09-29.

- It is a read-only review of committed results. No new trial was run.
- It does not start S6/S7 and proposes no new framework.
- All evidence is from a synthetic Docker source or the fake OpenVR API, running through the original consumers into MoveIt Servo and Gazebo.
- No real Quest/SteamVR semantics and no physical robot outcome are claimed.

**Decision rule (protocol section 10).**

- If at least one existing configurable baseline, given I_FULL, meets all relevant policy and practicality conditions, the tested conditions are NO_METHOD_GAP.
- A gap can be closed by ordinary metadata transport, property configuration, direct checking, a watchdog or re-arm logic. When that happens, the existing solution is acknowledged.
- B0 (the original path) failing, or an I_NATIVE starvation, is not a gap.

## 1. Evidence base (primary results; supplementary analyses are labelled)

| Case (stack) | Formal root | Valid / executed | Key outcome |
| --- | --- | --- | --- |
| D1 normal input (Docker) | `s4b_d1_formal_20260926T104931Z` | 48/50 | 0 false rejections in all valid defense arms. 2 B2 I_FULL trials invalid because of observation-association gaps (§3). |
| D2 invalid tracking (Docker) | `s4b_d2_formal_20260927T022400Z` | 47/50 | B1, B2-composed and B3 PASS in both regimes. B2-native FAIL (no neutralization). 3 B2-native invalid (§3). |
| D3 source silence (Docker) | `s4b_d3_formal_20260928T040232Z` | 50/50 | B1, B2-composed and B3 PASS. B2-native blocks the tick but does not neutralize. |
| D4 source age F100/F250/F500, historical and future stamps (Docker) | `s4b_d4_formal_20260928T053240Z` | 630/630 | I_FULL B1, B2-composed and B3 PASS. Supplementary: A050/F100 boundary straddles. B0 moved on every aged, historical and future stamp. |
| D4-L post-decision delivery delay (Docker, scoped) | `s4b_d4l_formal_20260928T105106Z` | 200/200 | B2-composed and B3 PASS. **B1 fails at L350 and L750: a placement effect** (its gate decisions were correct). |
| D5 reconnection and generation, R_EXPLICIT/R_AUTO (Docker) | `s4b_d5_formal_20260928T133632Z` | 50/50 | B1, B2-composed and B3 PASS both policies, with exact re-arm. |
| D6 validity recovery (Docker) | `s4b_d6_formal_20260928T142519Z` | 50/50 | B1, B2-composed and B3 PASS both policies. |
| C-ID binding (Docker, scoped) | `s4b_cid_formal_20260928T160547Z` | 120/120 | I_FULL B1, B2-composed and B3 PASS for all four kinds. |
| C-MON monitor/oracle failure (Docker, scoped) | `s4b_cmon_formal_20260928T180115Z` | 60/60 | Official ROSMonitoring measured **fail-open**: 20/20 FAIL. B2-composed health stop 20/20 PASS. Common heartbeat watchdog stops B1/B3 gate crashes 10/10. |
| W0–W5 (OpenVR fake, scoped) | `s4b_ovr_formal_20260928T192004Z` | 198/205 | B1 and B3 PASS W1–W3 and meet every defense-controlled W4/W5 criterion (supplementary S1–S3 corrections). **All arms fail R8 (fresh-reference displacement).** Official B2 fails through generated-executor stalls; B2-ST behaves like B1/B3. |
| C-ID / C-MON (OpenVR fake, scoped) | `s4b_ovr_cx_formal_20260928T223012Z` | 88/100 | B1, B3 and B2-ST C-ID PASS. B2-native fail-open. B2-composed ABSENT and DISCONNECT PASS. Watchdog stops gate crashes. Residual official-B2 failures are executor stalls. |

## 2. Requirement-by-requirement classification

The classes used below are defined as follows:

- **METHOD**: an I_FULL existing baseline cannot satisfy the requirement.
- **PLACEMENT**: the right predicate sits at the wrong location.
- **METADATA**: required information is missing (I_NATIVE, or an original that ignores a native field).
- **INTEGRATION**: stop, watchdog or re-arm logic is missing.
- **APPLICATION**: the application's own logic is outside the defenses' stop/forward contract.
- **IMPLEMENTATION**: a runtime or platform defect of a specific implementation.
- **OBSERVATION**: an instrumentation limit.

| # | Requirement (protocol §5/§8) | Existing solution meeting it (I_FULL) | Non-method limitations observed | Class of residual |
| --- | --- | --- | --- | --- |
| 1 | Normal acceptance, 0 false rejections, ≥ 99% delivery (D1, W1) | B1, B3 (both stacks); B2-composed (Docker); B2-ST (OpenVR) | Official B2 on Jazzy: no decision, or stale false rejections from generated `MultiThreadedExecutor()` stalls. D1 B2 association gaps. | NO_METHOD_GAP; IMPLEMENTATION (Jazzy monitor); OBSERVATION (D1) |
| 2 | Docker validity (`isTracked`, teleop, generation) (D2, D5) | B1, B2-composed, B3 | B2-native has no neutralization | NO_METHOD_GAP; INTEGRATION (native) |
| 3 | OpenVR validity (connected, `bPoseIsValid`, result = 200, grip) (W2, W3, W5) | B1, B3; B2-composed PASS W2 4/4 plus 1 straddle; B2-ST | The original ignores `eTrackingResult` (W2 moves 5/5) but checks `bPoseIsValid` (W3). Official B2 latency on Jazzy. | NO_METHOD_GAP; METADATA (the original ignores a native field); IMPLEMENTATION |
| 4 | Unknown native information not translated to false (explicit emulation) | Every I_NATIVE cell reported UNOBSERVABLE, not FAIL | I_NATIVE lacks age, generation and ID | METADATA (not a method gap) |
| 5 | Freshness F100/F250/F500, historical epoch, +1 s future stamp (D4) | B1, B2-composed, B3 in every profile | Supplementary boundary straddle at A050/F100 | NO_METHOD_GAP |
| 6 | Age at every forwarding point, i.e. post-decision delay (D4-L) | B2-composed, B3 (consumer-side placements) | B1 source gate admitted in-budget samples that aged in transit | NO_METHOD_GAP; **PLACEMENT** (B1), not a predicate limit |
| 7 | Receipt silence with 250 ms watchdog, ticks distinct from samples (D3) | B1, B2-composed (official verdict on the health tick plus ordinary stop), B3 | B2-native does not neutralize; the original receiver/Servo timeouts are not credited | NO_METHOD_GAP; INTEGRATION |
| 8 | Invalidation leads to decision and neutralization ≤ 50 ms, no output by +300 ms, settled by +1 s (D2–D6, W4/W5, C-ID) | Composed B1, B2-composed and B3, via the common stop adapter (Docker zero twist; OpenVR pause plus measured-position hold) | Filters alone (B2-native) never neutralize | NO_METHOD_GAP; INTEGRATION |
| 9 | R_EXPLICIT and R_AUTO re-arm: dwell, release, rising edge, no held-grip restart (D5, D6, W4, W5) | Docker: B1, B2-composed, B3. OpenVR: B1, B3, B2-ST (exact re-arm poll; S2 supplementary for the R_AUTO dwell-jitter scorer defect) | The original has no latch: held-grip restart in W4/W5 | NO_METHOD_GAP |
| 10 | Fresh reference adds no displacement (W4/W5 R8) | **None on OpenVR**. Every arm, B0 included, moves 0.02–0.06 rad. Docker D5/D6 PASS, because the original mapper re-captures the reference. | OpenVR `quest_teleop.py` maps each engage to a fixed absolute target (0.4, 0, 0.3). Under R_AUTO it resumes with its old offset, so Servo catches up to the pre-fault target. The adapter contract ("stop/hold or forward only") forbids target transformation. | **APPLICATION**: missing recovery-reference logic in the original OpenVR program. Not a defense-method gap. A conventional fix belongs in the application (re-anchor to the current end-effector pose on engage). |
| 11 | Old generation / reconnection (D5, W5) | B1, B2-composed, B3; OpenVR B1, B3, B2-ST | none beyond #10 | NO_METHOD_GAP |
| 12 | Binding identity: missing field/ID, duplicate on new ingestion, state/command mismatch (C-ID Docker and OpenVR) | B1, B2-composed, B3 (Docker, 4 kinds); B1, B3, B2-ST (OpenVR, 2 kinds) | Official B2 stalls on Jazzy | NO_METHOD_GAP; IMPLEMENTATION |
| 13 | Monitor and oracle failure: absent, disconnect, non-responding; gate-process crash (C-MON Docker and OpenVR) | B2-composed (official `unknown` leads to a common stop); common 250 ms heartbeat watchdog for B1/B3 | **Official ROSMonitoring is fail-open** in all three oracle faults on both stacks. A non-responding oracle builds a multi-second backlog. | NO_METHOD_GAP via conventional fail-closed integration; INTEGRATION (native fail-open is a configuration/integration property, not a method limit) |
| 14 | Exact source-to-consumer linkage | Exact source ID to Servo input callback (Docker) and to Servo `poseCallback` (OpenVR, 450/450 etc.) | Per-sample Servo output, controller and joint parent remain UNKNOWN_INTERVAL_ONLY | OBSERVATION (instrumentation boundary) |
| 15 | Practicality: p95 added gate/transport ≤ 20 ms; CPU descriptive | B1/B3 in-process decisions 0.1–0.6 ms on OpenVR; Docker B2 oracle path ≈ 1–17 ms | Official Jazzy B2: hundreds of ms to seconds of stall, back-pressure onto the source, burst drops. Docker D1 exact added transport latency UNKNOWN (p95 included cached waiting). | NO_METHOD_GAP for B1/B3; IMPLEMENTATION (Jazzy monitor); OBSERVATION (D1 exact latency) |
| 16 | Modification burden (`git diff --numstat` per baseline) | Descriptive hand-written integration sizes (harness files, not vendor diffs): shared policy primitives about 330 LOC (`d1_contract`, `d5_rearm`, `d3_silence`, `cid_binding`); Docker nodes, stop adapter, gate and property about 970 LOC; OpenVR policy, production integration, stripper, stop adapter and property about 545 LOC; generated official monitor 805 LOC (not hand-written) | Per-baseline numstat separation and engineering time were **not** measured systematically | EVIDENCE INCOMPLETE (descriptive only; not a gap) |

## 3. D1/D2 gap review

**D1 (48/50).** Two B2 I_FULL trials failed the frozen all-property-to-receipt completeness rule. The CP7-A forensic audit (`S4B_CP7A_D1_OBSERVATION_GAP_AUDIT.md`) found the following:

- All 54 unjoined events were `safe=true` original `stale_timeout` neutrals with no source ID. 53 of them came **before** the barrier and one after.
- The official monitor writes `forwarded` status before it publishes. Status is therefore a forwarding intent, not a receipt.

These are observation/association gaps on original-generated neutral events, not source samples. In every valid defense arm, all steady-active samples were admitted with 0 false rejections. D3 onward handled original neutrals explicitly (`ORIGINAL_NEUTRAL` origin, calibration ACK, post-capture drain), and later Docker campaigns were complete (D3–C-MON, 1,160/1,160 valid).

**D2 (47/50).** Three B2-native invalid trials had the same signature: original `stale_timeout` neutrals logged after the 6 s source sequence, around barrier + 9.2 s, without a matching downstream receipt or status. These are lifecycle-boundary observation gaps.

- The valid subset is conclusive for the tested condition: B1, B2-composed and B3 PASS in 10 trials each (both regimes).
- B2-native FAILs only for the missing neutralization. That result is identical to D3/D4/D4-L and C-MON, where it was reproduced with complete data.

**Conclusion for §3.** Neither D1 nor D2 hides a policy failure of an I_FULL existing baseline. Both gaps are OBSERVATION class, and their substantive requirements (#1, #2, #8) are met with complete data in later cases. A supplementary D1/D2 re-run is not needed to decide S5. It would only complete the D1/D2 tables themselves.

## 4. Separated limitation classes (not method gaps)

- **PLACEMENT.** A source-side gate (B1) cannot see delay introduced after its decision (D4-L). A consumer-side check (B3) or the in-path filter plus stop (B2-composed) solves it.
- **METADATA.**
  - I_NATIVE cannot observe age, generation, identity or (for OpenVR B2) any state; these are UNOBSERVABLE by construction.
  - The original OpenVR program ignores the native `eTrackingResult`.
  - The Docker original does not read source time.
  - Each of these is solved once the field is delivered and checked.
- **INTEGRATION.**
  - Every B2-native failure comes from a filter with no explicit neutralization.
  - The official monitor is fail-open under oracle faults.
  - Both are solved by ordinary stop and watchdog integration: the common stop adapter, the 250 ms heartbeat, and treating `unknown` as a stop.
- **APPLICATION.** The OpenVR absolute re-reference mapping (#10) is an application recovery-reference defect. A defense limited to stop/forward cannot remove it.
- **IMPLEMENTATION.** The officially generated ROSMonitoring monitor on Jazzy rclpy (`MultiThreadedExecutor()`, hardcoded in `generator.py`) stalls at 50 Hz. A one-line single-threaded variant (B2-ST, separately named, not ROSMonitoring) meets the same criteria as B1/B3. The same generated code on Humble showed ≤ 10 ms envelope-to-oracle latency.
- **OBSERVATION.** Per-sample Servo output to joint parentage is UNKNOWN. The D1/D2 neutral-association gaps and the D1 exact added-latency figure also fall here.

## 5. S5 decision

For every tested synthetic Docker and fake-OpenVR condition, at least one existing configurable baseline with I_FULL meets all relevant policy criteria. In most cases several do: B1 or B3 with the common stop adapter, B2-composed on Humble, and B2-ST on Jazzy.

The one requirement no arm meets is the OpenVR fresh-reference criterion (#10). It fails identically for the unmodified original and is caused by the application's own mapping, not by what a defense can observe or decide.

**S5 = NO_METHOD_GAP for the tested conditions.** No independently defensible method gap remains. In line with §10, this audit acknowledges the existing solutions that closed each failure:

- metadata transport (I_FULL envelope, binding hash);
- task property configuration (official TLOracle property);
- direct source/receiving checks;
- a common watchdog and fail-closed monitor-health stop;
- R_EXPLICIT/R_AUTO re-arm logic.

**Not established by this study:**

- real XR tracking semantics and native inference;
- physical robot outcomes;
- other fault times, crash loops and oracle restart;
- I_NATIVE comparisons beyond UNOBSERVABLE;
- per-baseline modification cost;
- any reliability guarantee (five repetitions per cell).

**Recommended follow-ups (not S6/S7):**

1. An application-level re-anchor fix for the OpenVR teleop program, measured separately.
2. An upstream issue for ROSMonitoring's generated executor on Jazzy.
3. Systematic per-baseline LOC and engineering-time accounting.
4. An optional, prospectively registered D1/D2 completion using the D3+ association handling.
