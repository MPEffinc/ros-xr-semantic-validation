# Research Plan

## 1. Goal and stopping rule

Trace the real flow *XR teleoperation → demonstration collection → dataset → policy learning →
autonomous execution* in public implementations, and decide whether a limited-authority component
can change the meaning of recorded demonstrations in a way that (a) passes existing data-quality and
integrity checks and (b) changes learned robot behaviour. The work stops, with the corresponding
verdict, at the first phase whose gate is not met:

| After | Gate | Verdict if not met |
|---|---|---|
| PHASE 1 | A demonstration-integrity question not already solved in published work | NO_METHOD_GAP / prior-art collision noted |
| PHASE 2 | A real, connected XR→(ROS)→recorder→dataset path in public code | NOT_VERIFIED path; scoped claim only |
| PHASE 3 | A component with a real, *limited* write boundary into that path | NO_REAL_THREAT_BOUNDARY or DATA_QUALITY_ONLY |
| PHASE 6 | A change that survives B2 (strong existing validation) | NO_METHOD_GAP |
| PHASE 7 | Changed behaviour of a trained policy | integrity claim only (no attack-success claim) |

No new framework is built in this workspace.

## 2. Overlap with closed studies (extracted from the actual reports)

| Closed study finding | Relevance here | Treatment |
|---|---|---|
| S5: validity (`isTracked`, `bPoseIsValid`), freshness, silence, generation/re-arm, binding identity and monitor fail-closed are all met by existing configurable baselines (NO_METHOD_GAP). IsaacTeleop controller tracker keeps OpenXR `VALID` but not `TRACKED` bits (NVIDIA_VS_SPES_ANALYSIS). | Tracking-loss / stale / invalid XR samples entering a recorded dataset are the *same* signals, now observed at recording time instead of at command time. | Not re-claimed. If a demonstration-integrity case reduces to "an invalid/stale XR sample was recorded", it is covered by S5 methods (PRIOR_INTERNAL) and classed DATA_QUALITY or NO_METHOD_GAP. |
| S5 #10: OpenVR application re-anchor defect (APPLICATION class). | Could appear as action-label discontinuity in recorded data. | Background only. |
| XR2Act / Authorization Continuity: bridge principals collapse (Quest2ROS2, rosbridge, HORUS); no client authentication; unauthenticated TCP endpoints. | "Any client can publish to the bridge" is *not* a limited-authority boundary — it is absence of authentication, already reported. | Not used as the attacker model; an unauthenticated injector is recorded as a known generic issue. |
| Authority Continuity: IMPLEMENTATION_GAP_ONLY; stale-holder problem solved by fail-closed admission, cancel, goal UUID, sequencer. | Episode boundaries / pause / reset in recorders are also lifecycle events. | If a recorder lifecycle issue appears, check sequencer/epoch remedies first. |
| RESEARCH_CONTEXT §16: "Demonstration Poisoning" was explicitly excluded from the first research scope. | This workspace is the first time it is investigated. | No prior internal results exist for it; nothing reused as new evidence. |

## 3. Phases

1. Literature (KEY_PAPERS, CITATION_GRAPH, LIMITATION_MATRIX, SOURCE_LEDGER).
2. Source audit of Isaac ROS Teleop, IsaacTeleop, Isaac Lab (teleop + mimic/recorder), XRoboToolkit,
   and any further ROS 2 demonstration recorder found; all pinned by SHA.
3. Threat model restricted to boundaries that exist in the audited code.
4. Minimal testbed (only if 2–3 pass).
5. Frozen protocol (B0/B1/B2).
6. Minimal refutation experiments.
7. Learning impact (only if 6 leaves a residual).
8. Verdict and FINAL_REPORT.

## 4. Known resource constraints (recorded before any result)

- GPU is a GTX 1050 Ti with 4 GiB. Isaac Sim / Isaac Lab officially require an RTX-class GPU; running
  the Isaac Lab recorder inside Isaac Sim is expected to be infeasible here (to be confirmed in PHASE 4,
  not assumed).
- No Quest headset is attached (`adb devices` empty). Real-XR-hardware evidence is expected to be
  NOT_VERIFIED; replay or synthetic XR input would be a separate evidence grade.
