# ros-xr-semantic-validation

This repository was reorganized on 2026-09-29 and again on 2026-10-01
(closed workspaces moved under `archive/`; see the manifests).

| Location | What it is |
|---|---|
| [`archive/2026-10-01_closed_research/`](archive/2026-10-01_closed_research/ARCHIVE_MANIFEST.md) | Closed workspaces moved on 2026-10-01 (old→new map, preservation checks): |
| ↳ [`authority_continuity/`](archive/2026-10-01_closed_research/authority_continuity/README.md) | **Closed** 2026-09-29: *Security Consistency Across Dynamic XR-ROS Control Authority and Robot Execution* — IMPLEMENTATION_GAP_ONLY. |
| ↳ [`xr_demo_integrity/`](archive/2026-10-01_closed_research/xr_demo_integrity/README.md) | **Closed** 2026-09-30: *Integrity of XR-Teleoperation Demonstrations for Robot Learning* — NO_REAL_THREAT_BOUNDARY ([final report](archive/2026-10-01_closed_research/xr_demo_integrity/results/FINAL_REPORT.md)). |
| [`Deprecated/`](Deprecated/ARCHIVE_MANIFEST.md) | **Closed** XR-ROS semantic-validation research (S1–S5) and August-2026 reports, preserved unchanged since 2026-09-29. |

Closed items on another branch (not merged here; see the 2026-10-01 manifest §4):
`research/n1-predictive-execution-mismatch` @ `6ea081ec3` holds `experiments/crossflow_gap_validation_2026-09-30/`
(KILL) and `experiments/n1_predictive_execution_mismatch/` (IMPLEMENTATION_GAP_ONLY → KILL).

Pre-reorganization snapshot: tag `archive/pre-authority-continuity-20260929` (commit `e7799a7`).

## Relationship between the studies

- The archived S1–S5 semantic-validation study concluded **NO_METHOD_GAP for the tested conditions**
  (`Deprecated/semantic_validation/results/S5_EVIDENCE_AUDIT.md`). S6/S7 were never run.
- Archived August-2026 reports (`Deprecated/AUTHORIZATION_CONTINUITY_RESULTS.md`,
  `Deprecated/XR2ACT_DECISIVE_RESULTS.md`, …) examined HORUS lease/authority behaviour and ended as
  **WEAK / CASE-STUDY ONLY**; authority_continuity revisited it and closed as IMPLEMENTATION_GAP_ONLY.
- All archived results are PRIOR_INTERNAL background evidence and reusable testbeds, not new results.
- Archived documents cite paths relative to their own old root. For the 2026-09-29 archive, prefix
  `Deprecated/`. For the 2026-10-01 archive, see its manifest §6.
