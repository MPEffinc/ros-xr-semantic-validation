# XRROS-S4B-OVRQ1-1.0.0 result — OpenVR setup: 12/13 qualified, B0/shim PASS (no policy score)

Root: `runs/s4b_ovr_q1_20260928T184158Z/` (frozen at 92240c6). All 13 cells ran sequentially with no concurrent load (10.0 min). Every cell reached the barrier on its first attempt, so no retry was used. The audit is `analysis/ovr_setup_summary.json`.

## Blockers resolved in setup

- **Observer equivalence.** The fresh B0/shim W1 pair is **PASS**: maximum matched poll-timing difference 0.144 ms (0 of 600 indices over 5 ms), final joint difference 0.00007 rad. The CP2 pairs had failed at 5.4–5.7 ms. The headless harness is therefore sufficient, and the original B0 path is unchanged.
- **Callback observation.** In every non-B0 cell, every Servo-input publication joined exactly one Servo `poseCallback` and vice versa:
  - W1 shim, B1, B2-composed, B3 and B2-ST-composed: 450/450;
  - W4 B1, B3 and B2-ST-composed: 350;
  - W4 B2-composed: 100;
  - W2: 0.
- **Readiness barrier.** Every cell had a full ACK: participant clocks on one boot, DDS edges, controllers, Servo pose mode, stop adapter, and for B2 the end-to-end official calibration.
- **Resources.** CPU/RSS capture was complete in every cell.
- **Stop/resume integration.** In W4 setup cells:
  - The common adapter's stop request came 4.2–4.6 ms after the poll-150 fault.
  - Resume came at 2.00 s after that fault (poll-250 re-arm) for B1, B3 and B2-ST-composed.
  - Motion from poll 150 to 200 was 0.012–0.019 rad, i.e. deceleration only.

## Setup observations (not formal outcomes)

- **New-reference motion.** After re-arm, the constant-pose new-reference window (polls 250–262) moved 0.059–0.061 rad in B1, B3 and B2-ST-composed. This is the original absolute re-reference mapping: the arm is pulled back toward (0.4, 0, 0.3). B0 moved 0.058 rad in the same window.
- **Original path (B0) under W4.** It kept moving 0.235 rad during the invalid second, because Servo kept tracking its last target. It then restarted with the grip held (0.192 rad in polls 200–240).
- **Official B2-composed under W4.** It stopped at 4.5 ms but never resumed. Official-monitor stalls made the oracle judge samples stale, and the latch then rejected the recovered valid input.

## Blocked cell (retained, not retried)

**B2-native W1 is `BLOCKED_MEASUREMENT` (`B2_OFFICIAL_ASSOCIATION_INCOMPLETE`).**

- The unmodified official monitor processed polls 0–199. After barrier + 4.45 s it processed nothing more for the remaining roughly 7.5 s of capture, although the process stayed alive. 560 of 760 envelopes therefore have no official status, and only 149 poses reached Servo.
- The recorder, production, oracle and stripper logs are intact. This is a post-barrier processing halt of the official Jazzy monitor, the same `MultiThreadedExecutor` phenomenon as in the component diagnostics. It is not a recorder defect.
- The frozen Q1 audit classifies it as blocked, and that classification stands. The formal design will register this prospectively as a B2 outcome class (official-monitor processing loss), not as invalidity, provided the independent recording path is intact.
