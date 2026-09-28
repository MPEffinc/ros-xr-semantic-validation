# XRROS-S4B-OVRCXQ1-1.0.0 result — 14/16 qualified, B0/shim PASS (no policy score)

- **Run:** root `runs/s4b_ovr_cx_q1_20260928T220949Z/`, frozen at 544c7d5. The 16 cells ran sequentially with no concurrent load. Every cell reached the barrier on its first attempt, so no setup retry was used.
- **Audit:** results are in `analysis/cx_setup_summary.json`.
- **B0/shim pair (MISMATCH fixture): PASS.** The largest source-timing difference was 0.150 ms and the final joint difference was 0.00004 rad.

## Blocked cells

Both blocked cells show records that were missing because of the injected fault itself. The frozen Q1 audit counted them as observation gaps.

**B2-native ORACLE_DISCONNECT: `B2_OFFICIAL_ASSOCIATION_INCOMPLETE`.**

- Two envelopes published 50.3 ms and 30.0 ms before the proven SIGKILL (polls 147 and 148) were still in the official monitor's queue at the kill.
- They were therefore sent to the dead oracle and returned as official `unknown`/`oracle_error`, with no property row.
- The frozen audit's 20 ms pre-fault window did not allow for the monitor's queue lag.

**B1 gate crash: `SERVO_CALLBACK_EXACT_JOIN_INCOMPLETE`.**

- After the crash, the gate passes input through. The common heartbeat stop was requested at barrier + 3.26 s.
- The four pass-through poses published from that instant (polls 162–165) produced no Servo `poseCallback`.
- Every earlier publication joined exactly one callback.
- These drops are a consequence of the stop response, not a recorder gap.

## Observations from the qualified cells (setup only, not scored)

| Fixture | Arm | Excursion (rad) |
| --- | --- | --- |
| MISMATCH / DUPLICATE_ID | B0, shim | 1.534 |
| MISMATCH / DUPLICATE_ID | Defense arms (stopped at the poll-150 fault) | 0.878–0.880 |
| C-MON ORACLE_ABSENT | B2-composed (stopped at start) | 0.0 |
| C-MON ORACLE_NONRESPONSIVE | B2-composed | 0.865 |

In the ORACLE_NONRESPONSIVE cell, 536 envelopes had no official status by the end of capture.

## Remedy

XRROS-S4B-OVRCXQ2-1.0.0 is an analyzer-only re-audit of these retained raw files; no new trial is run. It is registered in `S4B_OVR_CX_Q2_REAUDIT_PROTOCOL.md` before it runs.
