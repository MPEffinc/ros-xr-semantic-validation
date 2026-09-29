# ros-xr-semantic-validation

This repository was reorganized on 2026-09-29.

| Location | What it is |
|---|---|
| [`xr_demo_integrity/`](xr_demo_integrity/README.md) | **Closed** research workspace (2026-09-30): *Integrity of XR-Teleoperation Demonstrations for Robot Learning* — NO_REAL_THREAT_BOUNDARY (data-quality issues only; [final report](xr_demo_integrity/results/FINAL_REPORT.md)). |
| [`authority_continuity/`](authority_continuity/README.md) | **Closed** research workspace: *Security Consistency Across Dynamic XR-ROS Control Authority and Robot Execution* (closed 2026-09-29: IMPLEMENTATION_GAP_ONLY). |
| [`Deprecated/`](Deprecated/ARCHIVE_MANIFEST.md) | **Closed** XR-ROS semantic-validation research, preserved unchanged, with old→new path mapping and preservation checks. |

Pre-reorganization snapshot: tag `archive/pre-authority-continuity-20260929` (commit `e7799a7`).

## Relationship between the two

- The archived S1–S5 semantic-validation study concluded **NO_METHOD_GAP for the tested conditions**
  (`Deprecated/semantic_validation/results/S5_EVIDENCE_AUDIT.md`). S6/S7 were never run.
- The new workspace is not an extension of that methodology.
- However, archived August-2026 reports (`Deprecated/AUTHORIZATION_CONTINUITY_RESULTS.md`,
  `Deprecated/XR2ACT_DECISIVE_RESULTS.md`, …) already examined HORUS lease/authority behaviour on the
  same upstream commit and ended as **WEAK / CASE-STUDY ONLY**. That overlap is disclosed and treated
  as prior internal evidence, not as new results.
- Archived data is background evidence and a reusable testbed only.
- Archived documents cite paths relative to the old root; prefix them with `Deprecated/`.
