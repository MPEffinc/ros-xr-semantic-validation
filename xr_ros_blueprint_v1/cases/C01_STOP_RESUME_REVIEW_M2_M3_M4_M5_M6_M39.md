# C01 — Interruption, stop and resume: M2 / M3 / M4 / M5 / M6 / M39 (review, 2026-10-03)

## Basis

- **Internal documents** at `../semantic_evidence_framework/`:
  - audits A1–A6;
  - results P1, P1b, F1, F2, F3 and R0;
  - the timestamp review `results/F2_TIMESTAMP_REVIEW.md`.
- **Pinned code:**
  - MoveIt Servo 2.12.4 (L40);
  - JTC 4.42.1 (L37);
  - target apps at their audit commits.
- **Literature:**
  - Safe-ROS (L21; U18, U19, U44);
  - clutch / indexing prior art (L41, search excerpt only).
- **No new experiment** was run.

Evidence labels: SOURCE (read in code), RUN (executed in an earlier internal experiment),
AUTHOR (paper or README statement), INFER (our reasoning).

## 1. What the controller does after the messages stop

| Path | Messages stop because | What the consumer does | Measured or read |
|---|---|---|---|
| OpenVR UR5e → Servo 2.12.4 → JTC (P1 testbed) | grip released, or the pose becomes invalid | Servo keeps tracking `latest_pose_` until `now − stamp ≥ incoming_command_timeout` (0.5 s), then calls `smoothHalt` (L40 `servo_node.cpp` L297–316). JTC keeps executing points already sent. `cmd_timeout` would only act **after** the last point (L37). | RUN: P1/P1b residual of 27.9–42.4 mm; Servo pause or a 0.1 s timeout did not reduce it; an explicit JTC hold at the measured state left 1.0 mm (P1b, 3/3). |
| Docker_Teleop → Servo 2.5.9 (twist) | stale (0.25 s) or release | The bridge publishes **fresh zero twists at 60 Hz**, so Servo's own timeout never trips and Servo holds the last positions with zero velocity (A5 §A7, `servo_calcs.cpp` L410–450) | SOURCE; PRIOR_INTERNAL D3/D5 |
| Quest2ROS2 → closed Cartesian controller | toggle disabled or silence | No command is published. The consumer is closed, so whether it holds the last target is NOT_VERIFIED (A2). | SOURCE (mapper), NOT_VERIFIED (consumer) |
| Spes → ros2 consumers | `move=false` | `ros2` republishes the *held* target every callback; `ros2_ik` stops sending trajectories (A4) | SOURCE |
| OpenArmX → ForwardCommandController | stream > 0.3 s stale or release | Identity delta, then the FCC holds the last command (whether the FCC holds or times out: NOT_VERIFIED). **A button motion (go_home / hands_up) keeps running after a disconnect.** (A6 §A7) | SOURCE |
| PickNik → MoveIt Pro | — | closed host (A3) | NOT_VERIFIED |
| Safe-ROS (reference architecture) | safety condition | Zero-velocity override at a topic interceptor; forwarding resumes automatically when stop signals cease (U44) | AUTHOR |

**Finding (RUN + SOURCE).** On position-controlled arms, "no more messages" and "Servo stopped
publishing" do not stop the arm. It catches up to the last commanded points. Only an action at the
controller does: a hold or cancel. JTC's `set_hold_position` holds the **measured** state (L37,
L1840–1849), which matches P1b.

## 2. How resume handles permission, buttons, offset and reference

| Path | Re-arm required? | Button state at resume | Offset / reference at resume | Source |
|---|---|---|---|---|
| OpenVR UR5e app | Only after a grip *release*. After an invalid-pose interval with grip held (or cached), the app **continues without a fresh press**. | ALVR edge-only forwarding can leave grip "pressed" (K6 on Monado confirmed the edge rule). On xrizer the legacy grip reads true again with no edge (F3). | An invalid-pose interval keeps the **old offset**, so F3 saw a 35 mm target jump. A real re-engage re-anchors to the **absolute** pose (0.4, 0, 0.3) + home rotation (S5 #10). | A1; F3; P1 |
| Quest2ROS2 | Toggle edge re-enables streaming, and the stream **starts enabled** | toggle level kept across gaps | Re-anchored on enable, from tf EE + Quest sample. Silence keeps anchor and filter (PRIOR runtime: target jumps by the hand displacement). | A2 |
| Docker_Teleop | No fresh press after a **reset**: the 8 s latch auto-releases and motion resumes if grip is held (A5 L747–749, L932–935) | grip level each frame | Re-anchors on engage, clutch release, tracking regain, mode change and reset | A5 |
| OpenArmX | **No fresh press**: a grip cached high when the stream returns re-engages by itself (py L425–435) | cached grip | Re-captures the reference, so there is no jump | A6 |
| Spes | `move=false` → `move=true` re-anchors | move level | Re-anchor base = the **last commanded** target, not the measured robot pose (`__init__.py` L263) | A4 |
| Safe-ROS | automatic | — | not applicable (mobile base, velocity) | U44 |

**Finding (SOURCE).** Across six implementations the resume policy differs:

| Behaviour | Implementations |
|---|---|
| automatic resume | OpenArmX, the Docker reset path, the OpenVR invalid-pose path, Safe-ROS |
| edge-gated resume | OpenVR release path, Quest2ROS2, Spes |
| reference used | current tf EE (Quest2ROS2), last command (Spes), fresh raw pose (OpenArmX), absolute constant (OpenVR) |

No implementation states which of these it intends.

## 3. Strongest existing individual fix per sub-problem

| Sub-problem | Strongest known fix | Where it must live | Status |
|---|---|---|---|
| M3 stop (residual motion) | controller hold/cancel at the measured state, issued with Servo pause so Servo cannot overwrite it; JTC `decelerate_to_hold_position` for a smooth stop | ROS controller side | RUN: 1.0 mm (P1b), one pose and one speed |
| M4 permission lapse | (a) release-on-inactive at the source (ALVR fix, one site), or (b) cause-aware re-arm with action-activity evidence | app/middleware (a) or gate with evidence (b) | RUN: command level (P1); physical outcome masked |
| M5 stale reference | re-anchor to the **measured current EE** on every (re-)engage, plus a **fresh press** after any interruption. This is classic clutch/indexing practice (L41); alignment-gated resume is a further option. | app/mapper (button and offset live there) | **not executed** in any internal experiment |
| M6 recenter | an epoch with continuity-preserving re-offset (app, 15 lines) or epoch gate + re-arm | app (continuity) or gate (stop) | RUN: position level (P1) |
| M2 frozen stream while unfocused | deliver activity or tracked state and gate on it (S5 class); or a receive-time state gate from runtime evidence | app/wire, or runtime-side collector | RUN: S5 synthetic; F1/F2 stand-in; **F3 real app: the app stopped by itself, gate added 0** |
| Pending/queued targets on resume | flush queues; Servo `pauseServo(false)` already resets smoothing and the rolling window (L40 L159–178) | consumer | SOURCE |

## 4. Questions left after every individual fix is applied (INFER; to be tested, not gaps)

1. **Ordering between fixes.** The hold, the gate or Servo unpause, and the app re-anchor are separate
   components. If Servo is unpaused or the gate re-admits before the app re-anchors, one command
   aimed at the old target can pass. P1 already saw one leaked command at an epoch boundary
   (U29).
2. **Who can observe a "fresh press".** Button edges exist only inside the app or on the app's wire.
   libmonado exposes no input values (F1). OpenVR UR5e publishes no button topic. Quest2ROS2, PickNik
   and Docker do publish buttons. A ROS-side component can therefore enforce fresh-press resume only
   where the button travels on the wire.
3. **Reference after a hold.** Holding at the measured state, then re-anchoring to tf EE, could
   still give a jump if the hold settles (gravity, controller error) between the two. This is
   unmeasured.
4. **Policy choice per task.** Automatic resume (Safe-ROS, OpenArmX) and fresh-press resume are
   both in use. S_end and S_life (F2) are both defensible. The protected condition must be declared
   per task before anything is called a violation.
5. **Integration cost (the only plausible system benefit).** Today each fix sits in a different
   place: the app offset, the gate, the controller, the Servo service. The places differ per
   implementation (`docs/04_RETROFIT_SITES.md`).

   A common transition component *could* provide: interruption → controller hold → suppression
   until re-arm → **re-basing of absolute pose targets onto the current EE** → release. That would
   need no app change for pose-target apps. It *cannot* supply fresh-press evidence where buttons
   are not on the wire, and re-basing needs per-app knowledge of the command semantics (an
   adapter).

## 5. Why the F3 gate added 0 blocks, and what not to repeat

- On the F3 path the runtime deactivation invalidates xrizer poses, so the **app itself** stops
  publishing. A receive-time state gate is redundant there.
- The hazards actually observed on that path were:
  - (a) the catch-up residual (M3);
  - (b) the resume jump (M5): 35 mm in the command target, physically masked.

  A receive gate addresses neither.
- **Confound to avoid (U46).**
  - Every masked outcome (P1 C2, P1b C2M, F3) came from the same start pose plus +x motion near the
    extension singularity. The orientation was still converging to the app's absolute `robot_home_rot`.
  - A new design must pre-qualify the start pose and motion path: Servo status NO_WARNING
    throughout, and orientation settled.
  - It must declare trials **invalid** if HALT_FOR_SINGULARITY, HALT_FOR_COLLISION or
    DECELERATE_FOR_SINGULARITY appears in the evaluation window.

## 6. Case status after this review

| Case | Judgment kept | What would change it |
|---|---|---|
| M3 | KNOWN_METHOD (controller hold) | a second pose/speed range, or a real robot |
| M4 | KNOWN_METHOD at the command level | a physical result without the confound; the real ALVR chain |
| M5 | KNOWN_METHOD by design; **never executed** | executing re-anchor-to-measured-EE + fresh press on a real app |
| M6 | KNOWN_METHOD at the position level | real recenter; rotation outcome |
| M2 | CANDIDATE | a runnable app that keeps streaming while unfocused (none on this host) |
| M39 | CANDIDATE (umbrella) | combined-contract comparison: per-app fixes vs a common transition component, same conditions |
