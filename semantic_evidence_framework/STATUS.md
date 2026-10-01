# STATUS — semantic_evidence_framework

Last update: 2026-10-01 (KST). Branch `research/xr-ros-evidence-framework`. Worktree `/home/cclab/ros_xr_evidence`.
Last verified pushed checkpoint: **CP3 OpenVR audit** = `5d4eb59438d1eedb374c0244d7d4651832a60e87` (local == origin).

## Checkpoints

| CP | Scope | State | Evidence |
|---|---|---|---|
| CP1 | Archive the closed workspaces + preservation verification | DONE (pushed `f7c01df`) | `../archive/2026-10-01_closed_research/ARCHIVE_MANIFEST.md` |
| CP2 | Workspace, research context, status | DONE (pushed `5bb076d`) | `docs/`, `hypotheses/CANDIDATES.md`, `audit/AUDIT_METHOD.md` |
| CP3 | Code audit: OpenVR UR5e | DONE (pushed `5d4eb59`) | `audit/A1_OPENVR_UR5E.md` |
| CP4 | Code audit: Quest2ROS2 | DONE (this commit) | `audit/A2_QUEST2ROS2.md` |
| CP5 | Code audit: PickNik, Spes, Docker_Teleop, OpenArmX | TODO | — |
| CP6 | Taxonomy + defense matrix draft | TODO | — |
| CP7 | Minimal reproduction + normal controls | TODO (design only after the audits) | — |
| CP8 | Existing-defense comparison | TODO | — |
| CP9 | Minimal framework + evaluation | CONDITIONAL (brief §8 criteria) | — |

## Completed scope and grounds

- **Reorganization.** The closed `authority_continuity/` and `xr_demo_integrity/` workspaces moved to
  `archive/2026-10-01_closed_research/`.
  - Blobs, local-only data and sidecar outcomes are identical before and after.
  - The 4 smoke-sidecar failures were present before the move.
- **Branch boundaries.** `Deprecated/` was not moved. Cross-flow and N1 remain on the N1 branch and are
  referenced only.
- **Environment.**
  - Jazzy and Humble images with MoveIt Servo and Gazebo exist.
  - The host has Monado 21 and the OpenXR loader 1.0.20, but no headset and no robot.
  - Three containers from other work are running and add concurrent load (`docs/00_ENVIRONMENT.md`).

- **OpenVR UR5e audit** (SOURCE_CONFIRMED unless noted):
  - Grip release publishes nothing, so Servo tracks the last target for up to `incoming_command_timeout` = 0.5 s.
  - ALVR forwards button *edges* only. Under the OpenXR inactive-action rule (`changedSinceLastSync=false`),
    a release during focus loss can never be forwarded. The driver also ignores buttons while the pose is
    invalid. → H-A1 (cached deadman): HYPOTHESIS, since the SteamVR and Quest runtime hops are NOT_VERIFIED.
  - Tracked vs. valid is lost in ALVR (`Running_OK` constant).
  - An ALVR recenter applies a new transform at receipt and ignores `changeTime`. The app subtracts the
    pre-change offset → H-B1 (recenter jump): HYPOTHESIS.
  - The S5 #10 absolute re-reference is not re-proposed.

- **Quest2ROS2 audit** (ROS side SOURCE_CONFIRMED; the Quest app `com.Tiguin.Q2R` is closed, so NOT_VERIFIED):
  - The messages carry no focus, tracking, origin or sequence evidence.
  - Permission is a latched toggle, enabled at start.
  - There is no silence timeout. The anchor and filter survive gaps (PRIOR_INTERNAL runtime).
  - The input stamp and frame are replaced.
  - The final controller is not in the repo.

## Not verified / limits

- Real runtime or headset transitions are NOT_VERIFIED: no Quest, no SteamVR.
- Whether Monado can run headless with a simulated device on this host is NOT_VERIFIED.

## Next

1. Integrate the secondary audits (PickNik, Spes, Docker_Teleop, OpenArmX), which are running in parallel and are verified before commit.
2. Draft the taxonomy and defense matrix.

## Blockers

None for the code audits. Experiments are limited to synthetic inputs and simulation.
