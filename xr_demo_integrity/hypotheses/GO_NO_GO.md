# GO / NO-GO

## Gate after PHASE 3 (2026-09-30)

| Gate question | Evidence | Result |
|---|---|---|
| Is there a real, connected XR → (ROS) → recorder → dataset path in public code? | SYSTEM_INVENTORY §2: yes for P1 LeRobot and P2 Isaac Lab (no ROS), P4 tidybot_ros (phone WebXR + ROS 2). Isaac ROS Teleop has no recorder. | met (with the ROS caveat) |
| Is there a real component with *limited* write authority that can change the recorded meaning beyond its entitlement? | TRUST_BOUNDARIES §1–3, THREAT_MODEL §2: XR input provider changes robot and record together; processors/recorders are in-process; other separations are UNAUTH or FULL_WRITE; the only LIMITED candidate needs a SROS2 deployment upstream does not document and is not XR-related | **not met** |
| Is XR necessary for any observed issue? | RESEARCH_QUESTIONS RQ4, H1: no; XR-specific items are data-quality signals already covered by S5 methods | **no** |
| Is ROS necessary? | NVIDIA XR→dataset paths use no ROS; in P4 ROS only adds a generic unauthenticated graph | **no** |
| Does anything survive prior art? | LIMITATION_MATRIX: demonstration poisoning (C1) HIGH collision; curation, timestamp checks, provenance exist for benign/generic cases | nothing XR/ROS-specific found |

**Decision.** NO-GO for PHASE 4–7 formal experiments and for any framework. The brief's rule for this
point applies: "이 단계에서 실제 공격 경계가 없으면 NO_REAL_THREAT_BOUNDARY 또는 DATA_QUALITY_ONLY로
판정한다; 신규 공격을 억지로 만들지 않는다."

- PHASE 4 (testbed) — NOT_RUN: gate not met. Additionally P2 cannot run on this host (Isaac Sim needs an RTX GPU; GTX 1050 Ti present) and P1 needs SO-101 hardware and a headset.
- PHASE 5 (protocol) — NOT_FROZEN: no formal campaign is justified (`../experiments/PROTOCOL.md`).
- PHASE 6 (refutation experiments) — NOT_RUN.
- PHASE 7 (learning impact) — NOT_RUN (its own precondition, a residual after B2, cannot arise).

Final verdict: PHASE 8 section below.
