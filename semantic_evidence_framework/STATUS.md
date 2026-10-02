# STATUS — semantic_evidence_framework

Last update: 2026-10-02 (KST). **Claim scope was corrected on 2026-10-02; see `docs/06_CLAIM_SCOPE_CORRECTION.md`.** Branch `research/xr-ros-evidence-framework`. Worktree `/home/cclab/ros_xr_evidence`.
Last verified pushed checkpoint: **F2 protocol freeze** = `f3292ee54d94e901f46f2cc27e33657ba79789a2` (local == origin).

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
- **Framework decision:** not built (decision as of 2026-10-01; the 2026-10-02 feasibility study is in progress). A ROS-side model cannot remove the source-side evidence-delivery
  edits. The next gate is an independent runtime-side evidence path (P2).

- **P2 (Monado)**: BLOCKED_ENV for the main question, because the headless session never reaches
  FOCUSED.
  - Observed on this runtime build: while not focused, `xrSyncActions` returns `NOT_FOCUSED`, yet
    actions report `isActive=1` with live state. Source: action update ignores focus.
  - Consequence: the conformance of the evidence source itself is a trust condition.

- **2026-10-02 feasibility study F1** (independent evidence path, no app modification):
  - **Claim scope corrected** (`docs/06`).
  - **P2 cause:** the old Monado build. Current main works headless.
  - **Real apps: 0 of 2 functional on this host.**
    - OpenVR UR5e + xrizer runs, but the session never focuses, so it emits 0 commands.
    - IsaacTeleop needs NVX1 extensions.
  - **Stand-in mechanism (27 runs).** The runtime-side libmonado IO evidence plus the consumer
    interval gate blocked every late, replayed, reordered and cross-client command (0 dangerous passes
    outside a ±20 ms band), with 0 false blocks outside the evidence outage. An app-published state
    stream gives the same result, so for an honest app the guarantee is not a differentiator; the
    difference is 0 app edits.
  - **No S2 defense:** libmonado control is unauthenticated.
  - **H-A1 premise confirmed on Monado:** a release inside the inactive window is never forwarded
    under the edge-only rule.
  - **Expansion on hold** (`docs/05` update).

- **F1 claim cleanup (post-hoc, `results/F2_CLAIM_CLEANUP.md`):**
  - Runtime-state collection without app changes is shown. Checking the generation interval without
    app changes is **not** shown.
  - Freshness alone explains the K2/K3b-replay/K3c blocks.
  - With equal freshness, arrival state matches the interval check except 6 K3a commands.
  - Boundary-inclusive totals: C_INTERVAL passed 11 should-block commands, all within 20 ms of a
    transition.

- **F2 matched comparison** (27 runs, stand-in app, equal freshness for all arms):
  - N1: 0 false blocks for every arm.
  - The interval check adds protection only for mid-only interruptions (M1 S_life: GEN_ARR 39/75 →
    INTERVAL 0/75) and for 5 ms windows.
  - Generation + arrival state handles the "generated while inactive" case.
  - Duplicates and reverse arrivals are caught only by the stamp-order check.
  - With 30 ms evidence delay, every state arm lets 6 commands through. With evidence older than
    E, every arm fails closed.

## Not verified / limits

- Real runtime or headset transitions are NOT_VERIFIED: no Quest, no SteamVR.
- P2 READY state: **cause = the installed Monado build** (e26a272c, 2023-03), which predates upstream `d7514687` (headless → FOCUSED on begin, 2023-12). The client and the configuration are not the cause. The `isActive=1` observation is specific to that build (`results/P2_CAUSE_ANALYSIS.md`).

## Next

1. Get one real XR→ROS app running functionally on Monado. Options:
   - an immersive OpenXR app with a frame loop;
   - the OpenVR UR5e app on a frame-pumping xrizer (a component change, reported separately).

   Then repeat F1 with no app change.
2. Use a GPU path for compositor-backed clients, to observe focus/tracking evidence at the service. This needs nvidia-container-toolkit (a host change that requires approval) or a native host setup.
3. Runtime variant with authenticated libmonado control calls, reported separately, before any S2 claim.

## Blockers

- No headset and no SteamVR. Real Quest/ALVR/SteamVR hops stay NOT_VERIFIED.
- Closed frontends (Quest2ROS2 APK, OpenArmX APK) and a closed host (PickNik / MoveIt Pro) bound the audit scope.
- Host load from other work's containers (about 1.5) is recorded, not removed.
- No NVIDIA container runtime: the host GPU cannot be used in containers (F1 bring-up). lavapipe lacks the fd-sync extensions that xrizer requests.
