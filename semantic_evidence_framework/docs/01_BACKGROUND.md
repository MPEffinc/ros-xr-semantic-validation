# 01 — Background, research question, and conclusions carried forward

## Research question

> In XR→ROS teleoperation, how can the evidence needed to judge whether a command is still
> *applicable* be acquired and linked, and how can that condition be enforced up to the actual
> executing consumer, including during state transitions?

**Evidence** means observable or specifiable facts, not abstract user intent:

- whether the input action is active;
- tracking state (valid vs. tracked);
- session and focus state;
- the effective time of a reference-space or origin change;
- the anchor or transform actually used;
- the target arm, robot, or controller a command applies to.

## Planned flow (the taxonomy/defense-matrix contribution is already accepted by the advisor)

1. Classify meaning and transition conditions.
2. Audit how real implementations deliver and consume that information.
3. Measure what existing defenses achieve and what they cost.
4. Test whether the recurring requirements can be served by a common model and enforcement system
   (§8 of the brief). This step is conditional, not presumed.

## Prior conclusions that must hold (all PRIOR_INTERNAL)

| Item | Conclusion | Scope limit | Source |
|---|---|---|---|
| S1–S5 semantic validation | **NO_METHOD_GAP** for the tested conditions | synthetic Docker source and fake OpenVR API only; no real Quest/SteamVR semantics; no physical robot | `Deprecated/semantic_validation/results/S5_EVIDENCE_AUDIT.md` (sha256 `5cfcaed2…878e`) |
| S6/S7 | **not run** | — | same |
| OpenVR resume displacement (S5 req. #10) | **APPLICATION** class: `quest_teleop.py` maps each engage to a fixed absolute target; the conventional fix is to re-anchor to the current EE pose on engage | do **not** re-propose as a new spatial-semantics gap | S5 §2 #10, §4 |
| Official ROSMonitoring fail-open; generated `MultiThreadedExecutor()` stalls on Jazzy | **INTEGRATION / IMPLEMENTATION** for the pinned versions and configuration of 2026-09-22 | not a statement about ROSMonitoring in general or about later versions | S5 §2 #13, #15; images `s4b-rosmonitoring-*:20260922` |
| authority_continuity (HORUS) | **IMPLEMENTATION_GAP_ONLY** | `horus_ros2@eca75cbf`, Nav2 loopback, mock clients | `archive/2026-10-01_closed_research/authority_continuity/hypotheses/GO_NO_GO.md` |
| xr_demo_integrity | **NO_REAL_THREAT_BOUNDARY** | no experiments | `archive/2026-10-01_closed_research/xr_demo_integrity/results/FINAL_REPORT.md` |
| cross-flow leakage | **KILL** | no real paired data | `git show 6ea081ec3:experiments/crossflow_gap_validation_2026-09-30/DECISION.md` |
| N1 predictive/execution mismatch | **IMPLEMENTATION_GAP_ONLY → KILL** | synthetic operator and display, single UR5 Gazebo plant; no HMD and no users | `git show 6ea081ec3:experiments/n1_predictive_execution_mismatch/DECISION.md` |

## What S5 already established, which this study must not re-claim

The following were each shown to be closable with I_FULL information and ordinary mechanisms:

- tracking-validity gating;
- freshness and age at the consumer;
- silence watchdogs;
- reconnection/generation re-arm (R_EXPLICIT / R_AUTO);
- binding-identity checks;
- fail-closed monitor health.

The mechanisms were:

- metadata transport;
- a direct check;
- a watchdog;
- re-arm logic;
- treating `unknown` as a stop.

**What S5 did not cover** is the starting point here:

- *Where the evidence comes from* in real implementations, and whether it exists at all. S5 supplied
  I_FULL synthetically.
- *Transitions* outside its matrix, such as:
  - action deactivation (focus loss) versus tracking loss;
  - reference-space or origin changes and their effective time;
  - interaction-profile changes;
  - multi-arm/device binding.
- *Cost of retrofitting* per implementation. S5 #16 was descriptive only.

## Contribution boundary

- This study does not claim tags, contracts, monitor generation, state machines or enforcement-node
  placement as first contributions. Prior art covers them (ROSMonitoring, RCL/Vanda, FRET/Ogma/Copilot,
  RTron, FlowTags, SROS2, tf2, RTA).
- A contribution exists only if linking the evidence and transition relations through a common
  model is measurably better than per-implementation retrofits, either in modification count or in
  latency/false blocks.
- If a one-line condition fixes a case, that case is recorded as solved in the matrix.
