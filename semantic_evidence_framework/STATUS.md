# STATUS — semantic_evidence_framework

Last update: 2026-10-01 (KST). Branch `research/xr-ros-evidence-framework`. Worktree `/home/cclab/ros_xr_evidence`.
Last verified pushed checkpoint: **P1b freeze** = `358dd89e697770f4c6893f383908c5ccf7567827` (local == origin).

## Checkpoints

| CP | Scope | State | Evidence |
|---|---|---|---|
| CP1 | Archive the closed workspaces + preservation verification | DONE (pushed `f7c01df`) | `../archive/2026-10-01_closed_research/ARCHIVE_MANIFEST.md` |
| CP2 | Workspace, research context, status | DONE (pushed `5bb076d`) | `docs/`, `hypotheses/CANDIDATES.md`, `audit/AUDIT_METHOD.md` |
| CP3 | Code audit: OpenVR UR5e | DONE (pushed `5d4eb59`) | `audit/A1_OPENVR_UR5E.md` |
| CP4 | Code audit: Quest2ROS2 | DONE (pushed `f40cf6f`) | `audit/A2_QUEST2ROS2.md` |
| CP5 | Code audit: PickNik, Spes, Docker_Teleop, OpenArmX, plus PickNik real-Quest reanalysis | DONE (pushed `1f9574b`) | `audit/A3`–`A6`, `results/R0_PICKNIK_HW_REANALYSIS.md` |
| CP6 | Taxonomy + defense matrix draft | DONE v0 (pushed `1ddf5ec`) | `docs/03_TAXONOMY_AND_MATRIX.md`, `literature/COMPARATORS.md`, `literature/OPENXR_ITEMS.md` |
| CP7 | Minimal reproduction + normal controls | P1 DONE (`533cf59`); P1b DONE (freeze `358dd89`, results this commit) | `results/P1_RESULTS.md` |
| CP8 | Existing-defense comparison | DONE for the OpenVR path (P1 `533cf59` + P1b this commit) | `results/P1_RESULTS.md` §3–4 |
| CP9 | Minimal framework + evaluation | **NOT BUILT**: §8 conditions 1–2 met at source level, 3 not shown; go/kill criteria defined | `docs/05_FRAMEWORK_DECISION.md` |

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

- **Secondary audits** (delegated, lead spot-checked; SOURCE_CONFIRMED at cited lines):
  - **PickNik.** No valid/tracked/focus field reaches ROS. `runInBackground` is on. One mutable message
    object is reused for both controllers while ROS-TCP-Connector 0.7.0 serializes asynchronously. The
    host side (MoveIt Pro) is NOT_VERIFIED.
  - **Spes (WebXR).** `emulatedPosition` is never read. A null controller pose silently falls back to the
    head pose. There is a 5 cm/35° one-sample jump guard. The clutch re-anchors on the last command.
  - **Docker_Teleop.** `isTracked` = controller *connected*. Every hop has 0.25 s receive-time freshness.
    The bridge streams fresh zero twists, so Servo's own timeout never trips. Re-anchoring on engage,
    regain and reset exists.
  - **OpenArmX.** The binding is the ASCII L/R label only. The `rate` value is fanned out to both hands.
    A TRANSIENT_LOCAL IK override bypasses the grip deadman. A cached grip resumes after the stream
    returns (with re-anchor).
- **R0 reanalysis** of the PRIOR_INTERNAL real-Quest PickNik capture (new analysis, prior data):
  - 54 % of `/left_controller_odom` messages carry `right_controller_odom`; `/tf` carries the left frame
    24 / 29,672 times.
  - During 5 Unity-reported focus-loss intervals (`is_tracked=false`), ROS still received a 60 Hz,
    fresh-stamped, frozen pose. Nothing on the wire marks it.

- **P1 pilot**: 54 Gazebo trials, synthetic OpenVR source, ROS-side consumption only.
  - **Release.** 35–45 mm of residual motion in every arm. Servo pause or timeout does not reduce it:
    it is downstream (controller and plant).
  - **Cached deadman.** The app emits a 10 cm target jump under the stale grip.
    - Re-arm on `bPoseIsValid` blocks it, but false-blocks 3/3 tracking glitches.
    - Re-arm on action activity passes both cases → METADATA.
  - **Recenter.** B0 moves 180/15 mm. The Spes jump guard misses the 3 cm change.
    - The epoch gate stops the arm, and the operator must re-press.
    - The 15-line app retrofit keeps continuity.
  - **Confounds.** The orientation had not settled, so the angle criterion is invalid. A Servo
    singularity e-stop masked C2 physically.

- **P1b** (18 trials):
  - A controller-level hold stops the release motion: 1 mm vs 33–35 mm for B0 and Servo pause.
  - The stale-permission commands reached Servo again (225/trial). The physical move was refused by
    the Servo singularity hard stop, which is configuration-dependent and not credited.
- **Framework decision:** not built. A ROS-side model cannot remove the source-side evidence-delivery
  edits. The next gate is an independent runtime-side evidence path (P2).

## Not verified / limits

- Real runtime or headset transitions are NOT_VERIFIED: no Quest, no SteamVR.
- Whether Monado can run headless with a simulated device on this host is NOT_VERIFIED.

## Next

1. Pilot P1 on the OpenVR path: release, cached deadman vs tracking glitch, recenter. ROS-side consumption only, with equal-evidence defense comparison.

## Blockers

None for the code audits. Experiments are limited to synthetic inputs and simulation.
