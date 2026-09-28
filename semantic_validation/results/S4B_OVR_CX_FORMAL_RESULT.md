# XRROS-S4B-OVRCXF1-1.0.0 result — scoped OpenVR C-ID / C-MON coverage

**Primary result:** scored by the analyzer frozen at 932b771, without changes. Summary data: `runs/s4b_ovr_cx_formal_20260928T223012Z/analysis/formal_summary.json`.

- **Run:** 100 trials, run sequentially with no concurrent load. Every trial reached the barrier on its first attempt; no setup retry was needed.
- **Validity:** **88 VALID_FORMAL_TRIAL and 12 INVALID_COMPARISON.**
- **Controls:** 14 of 15 B0/shim pairs PASS (at most 0.478 ms).
- **Scope:** fake OpenVR only. MISSING_FIELD, MISSING_ID, C-ID B2-native and I_NATIVE are NOT_RUN (scoped).

## Invalid trials (retained)

| Trials | Reason |
| --- | --- |
| MISMATCH repetition 1: the shim, and through the pair gate B1, B3, B2-composed and B2-ST-composed | The shim's source polls were not completed inside the capture, so the whole block is invalid. |
| B2-composed NONRESPONSIVE r02, r05; B2-composed MISMATCH r03 | Official association incomplete. |
| B2-native DISCONNECT r03; B2-composed DUPLICATE_ID r03; B2-composed DISCONNECT r05 | Servo callback join incomplete (official-monitor burst). |
| B2-native DISCONNECT r05 | Source polls incomplete (official-path back-pressure). |

All invalid trials except the MISMATCH repetition-1 block involve the official Jazzy monitor.

## Primary policy outcome (valid trials)

| Condition | B1 | B3 | B2-composed (official) | B2-ST-composed (diagnostic, not ROSMonitoring) | B2-native (official) |
| --- | --- | --- | --- | --- | --- |
| C-ID MISMATCH | PASS 4/4 | PASS 4/4 | PASS 3/3 | PASS 4/4 | NOT_RUN |
| C-ID DUPLICATE_ID | PASS 5/5 | PASS 5/5 | PASS 1, FAIL 3 (official stall: stale latch, watchdog pre-stop, latency), invalid 1 | PASS 5/5 | NOT_RUN |
| C-MON ORACLE_ABSENT | — | — | PASS 5/5 (stops on official `unknown` 24–34 ms after the barrier) | — | — |
| C-MON ORACLE_DISCONNECT | — | — | PASS 4/4 (request 12.0–13.8 ms) | — | FAIL 3/3 (fail-open: control continued; not settled until about 5.2 s) |
| C-MON ORACLE_NONRESPONSIVE | — | — | PASS 2, FAIL 1 (monitor stall tripped the watchdog before the fault) | — | — |
| C-MON gate-process crash | PASS 4, FAIL 1 | PASS 5/5 | — | — | — |

**Timing, B1/B3/B2-ST:**
- They reject the injected sample with the registered reason (`STATE_COMMAND_MISMATCH` / `DUPLICATE_SOURCE_EVENT_ID`) 0.1–1.2 ms after acquisition.
- The common adapter requests the stop 3.8–5.4 ms after acquisition, and the robot settles in 324–394 ms.
- The injected sample is never delivered, and the held grip never restarts.
- Gate crash: the common 250 ms heartbeat watchdog stops B1/B3 254–259 ms after their last verdict. This is not ROSMonitoring.

**B1 gate-crash FAIL (r02).** It violates only the pre-fault joint-path rule: 0.092 rad from the shim at slot 149. That trial admitted and delivered all 100 pre-fault samples. The divergence starts during the original's large reference acquisition (polls 60–100), before any fault. It is simulator trajectory variance, not a defense decision; the frozen primary FAIL stands.

**Shim consequence (no defense):** the injected poll is delivered to Servo, and 349 later held-grip samples are delivered too.

## Interpretation (tested fake-OpenVR conditions)

- **C-ID.** Ordinary binding checks work at every placement once the acquired projection and the ingestion identity are available (I_FULL): B1 before use, B3 at publish, and the official oracle property (B2-ST, and official B2 whenever its monitor keeps up). Consistent with **NO_METHOD_GAP**, as in Docker.
- **C-MON.** On OpenVR the official monitor is again **fail-open** (B2-native).
  - An ordinary fail-closed integration (official `unknown` → common stop) solves ABSENT and DISCONNECT.
  - The common heartbeat watchdog solves gate crashes.
  - Consistent with **NO_METHOD_GAP**.
- **Residual official-B2 failures** have the same cause as in the W campaign: the generated `MultiThreadedExecutor()` monitor stalls on Jazzy. B2-ST separates that implementation/platform limitation from the method.
