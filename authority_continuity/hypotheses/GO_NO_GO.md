# GO / NO-GO

## Gate after PHASE 5 (2026-09-29)

| Question | Evidence | Status |
|---|---|---|
| Code-level authority boundaries confirmed? | audit F1–F8 | SOURCE_CONFIRMED |
| Adversarial gap (Q-SEC)? | No authentication at all; acknowledged by maintainers; standard remedies | **No research gap** (K1/K2/K4) |
| Consistency gap (Q-CONS) tied to real code paths? | F5, F8 + ROS 2 Action semantics | HYPOTHESIS H1–H3, testable |
| Author-stated limitation / published open problem? | none in P1/P2/P5/P7 (LIMITATION_MATRIX) | none |
| Known general solution? | Chubby sequencer + lock-delay (2006), Action cancel, fail-closed, auth | yes, per ingredient |
| XR essential? | failures are in the bridge/backend, independent of client type | no (K3) — to be confirmed |

**Decision:** GO for *minimal refutation experiments only* (PHASE 6), whose purpose is to test H4/H5,
i.e. whether existing primitives suffice. **NO-GO for framework development**: no evidence yet of a
gap that standard mechanisms cannot close. Final verdict in PHASE 7.

---

## PHASE 7 — Final verdict (2026-09-29)

# IMPLEMENTATION_GAP_ONLY

Scope: HORUS `horus_ros2@eca75cbf`, Nav2 loopback plant, mock HorusLink clients, one robot. Evidence:
`../audit/HORUS_CODE_AUDIT.md`, `../results/PHASE6_RESULTS.md` (120 formal trials).

### Answers

1. **Security problem reproduced in a real implementation?** Consistency failures, yes
   (EXPERIMENT_CONFIRMED): lease end without stop (15/15), new holder unable to stop the robot after a
   handoff while HORUS reports `goal_cancelled` (30/30), stale admission (15/15), catalog override (5/5).
   Adversarial exploitation of an *authenticated* principal: not applicable — no authentication exists
   (acknowledged by the maintainers as future work).
2. **Is XR essential?** No. Every failure is located in the bridge lease manager and the backend Nav2
   adapter; the clients in the experiment were not XR devices and the failures do not depend on any XR
   state. XR only supplies plausible triggers (headset removal, focus loss), which were not tested
   because the Unity client is closed-source (NOT_VERIFIED).
3. **Different from published attacks / generic authorization?** No material difference. The pattern is
   the stale lock-holder request problem (Burrows, OSDI 2006 §2.4) applied to ROS 2 actions; the fragments
   (no per-operator identity behind a bridge, no goal ownership, static SROS2 permissions) are already
   documented (P3, P4, P5).
4. **Solved by correctly applying existing methods?** Yes, in every tested case: B1 = generic fail-closed
   admission + existing HORUS cancel path on lease end + goal-UUID correlation (ROS 2 Action primitive) +
   host binding passed all targeted goals (PG1–PG5, PG2 after handoff, 0/25 cross-epoch interference).
5. **Responsible boundary / stage.** Bridge admission (`control_lease_manager.cpp:135-148`, 184-285, lease
   erase sites without cancel) and backend result handling (`nav2_action_adapter.cpp:241`). Not a ROS 2,
   Nav2 or SROS2 defect.
6. **Simple configuration / fail-closed / Action cancel enough?** Yes: a ~160-line test-only patch using
   only those mechanisms. The remaining theoretical gap (cross-epoch race, H5) was not observed and, if it
   exists, has a textbook remedy (Chubby sequencer / generation number on commands, lock-delay).
7. **New methodology needed?** No evidence supports it.
8. **Contribution type supported by evidence?** At most an implementation-level case study / bug report
   (lease-end policy undefined; single-handle adapter bug; fail-open protected topics; self-asserted host).
   Not an attack paper (no authenticated boundary to break), not a defense paper (existing mechanisms
   suffice), and only a thin evaluation paper (one framework, overlaps archived August-2026 results).

### Why not the other verdicts

- Not **REPRODUCED_RESEARCH_GAP**: failures were reproduced, but the gap is closed by existing methods.
- Not **OPEN_RESEARCH_HYPOTHESIS**: the only open item (H5) is untested beyond 25 trials, has a known
  remedy, and would not change the verdict even if observed.
- Not **NO_METHOD_GAP** alone: there *is* a concrete implementation gap in HORUS worth reporting; the
  method-level answer is nonetheless "no gap".

### Decision

No framework is developed. The research item is closed with this verdict. Motivating example, NABC and
main-experiment plan are **not** written because the gate condition (a confirmed method gap) is not met.

Possible non-research follow-ups (not performed; require the user's decision): a private,
responsible report to the HORUS maintainers describing F1/F3/F5/F8 and the B1 fixes; testing the real
Unity client lifecycle if its source or a test build becomes available.
