# Research Plan

Date: 2026-09-29. Goal: decide, with evidence, whether an independent unresolved research problem
exists. Completing a framework is **not** a goal.

## Phases and gates

| Phase | Work | Output | Gate to continue |
|---|---|---|---|
| 3 | Literature: bibliographic verification, author-stated limitations (with section/page), backward + forward snowballing, follow-up resolution up to 2026-09-29 | `literature/*` | Always proceeds to 4 (code audit is needed regardless) |
| 4 | Read-only audit of `RICE-unige/horus_ros2` at a pinned SHA; trace lease, routing, registration, action paths | `audit/HORUS_CODE_AUDIT.md`, `ARCHITECTURE.md`, `TRUST_BOUNDARIES.md` | Findings labeled SOURCE_CONFIRMED / HYPOTHESIS / NOT_VERIFIED |
| 5 | Threat model grounded only in identities/paths that exist; protection goals; sufficiency of existing defenses **combined** (lease + robot-side check + Action cancel + Servo timeout + SROS2 + ABAC + RTA) | `hypotheses/*`, `audit/EXISTING_DEFENSES.md` | If existing defenses (properly combined) close the problem → record NO-GO, stop; no framework |
| 6 | Minimal refutation experiments, only for cases tied to a confirmed code path and hypothesis | `experiments/*`, `results/*` | Only if gate 5 = GO |
| 7 | Verdict: NO_METHOD_GAP / IMPLEMENTATION_GAP_ONLY / OPEN_RESEARCH_HYPOTHESIS / REPRODUCED_RESEARCH_GAP | `hypotheses/GO_NO_GO.md` | — |

## Kill / downgrade criteria (fixed before looking at new evidence)

- K1. The problem is fully explained by a missing configuration, a generic fail-closed default,
  or not wiring an existing primitive (e.g. calling ROS 2 Action cancel on lease loss)
  → at most **IMPLEMENTATION_GAP_ONLY**.
- K2. Published work up to 2026-09-29 already states and resolves the problem → **NO_METHOD_GAP**.
- K3. XR is incidental (the same issue exists identically for any multi-client teleop bridge)
  → the XR framing is not a contribution; record it.
- K4. The attack requires an identity, credential, or path that does not exist in the
  implementation → the case is discarded, not simulated.
- K5. Continuation of already-accepted work after a lease ends is judged against an explicit
  protection goal (must-complete vs must-stop); continuation alone is not a violation.
- K6. Results that merely re-run archived `PRIOR_INTERNAL` experiments on the same commit do not
  constitute new evidence of novelty.

## Fairness rules

- Baselines are configured as their documentation intends; no deliberately weakened control.
- Baseline and candidate receive identical information.
- Normal system behavior is not scored as attack success.
