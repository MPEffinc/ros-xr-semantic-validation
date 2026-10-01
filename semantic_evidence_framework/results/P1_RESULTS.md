# P1 results — OpenVR path pilot (54 Gazebo trials, 2026-10-01)

| Item | Value |
|---|---|
| Protocol | `experiments/P1_openvr_evidence/PROTOCOL.md`, frozen at commit `d254e42` before the scheduled runs. Input hashes: `FREEZE_SHA256.txt`. |
| Raw data | `results/raw/P1/formal_20261001/` (ignored, 65 MB). Per-file sha256 in `results/P1_RAW_SHA256.txt` (828 files, smokes included). Runner log: `results/P1_runner.log`. |
| Execution | 54/54 trials reached the barrier, with 0 setup retries. Image `openvr-jazzy-sim:local` (Servo 2.12.4), `--network none`. |
| Load | Host load average during the trials was 4.9–15.5. This includes our own Gazebo; the background from other work was about 1.5. The host has 20 CPUs. |
| Frozen analysis | `analysis/analyze.py` → `analysis/p1_summary.json` |
| Post-hoc diagnostics | `analysis/posthoc_diagnostics.py` → `analysis/p1_posthoc.json`. Written **after** the frozen analysis. It explains outcomes; it does not replace them. |
| Labels | Results below are **EXPERIMENT_CONFIRMED for the ROS-side consumption of a synthetic source**. They are not a real runtime or headset transition. |

## 1. Frozen outcomes (as computed, 3 repetitions per cell)

| Case | B0 | Defenses |
|---|---|---|
| C0 normal | PASS 3/3 (progress 0.198 m) | — |
| C1 release | VIOLATION 3/3 (35.5 mm) | D_TO VIOLATION 3/3 (40.4 mm); PAUSE VIOLATION 3/3 (33.0 mm) |
| C2 deact + cached grip | PASS 3/3 (0 mm) | REARM_V PASS 3/3; REARM_C PASS 3/3 |
| C3 tracking glitch (control) | PASS 3/3 (0.157 m) | REARM_V **FALSE_BLOCK 3/3** (0.009 m); REARM_C PASS 3/3 (0.157 m) |
| C4L recenter 30 cm/30° | VIOLATION 3/3 (180 mm) | JUMP, EPOCH_G, EPOCH_A: VIOLATION 3/3 each, on the angle criterion only (0 mm displacement) |
| C4S recenter 3 cm | VIOLATION 3/3 (15 mm) | JUMP VIOLATION 3/3 (15 mm); EPOCH_G and EPOCH_A: VIOLATION 3/3 each, on the angle criterion only (0 mm) |
| C5 fast legit (host-only) | — | JUMP **FALSE_BLOCK** (disarmed at 6.02 s); other gates armed |

No cell had disagreeing repetitions, so the expansion rule (extend to 5) was not triggered.

## 2. Confounds found after the run (setup defects, documented and not repaired)

1. **Orientation was not settled.** At every event the EE was still rotating at 15–17 °/s
   (`ee_rot_rate_deg_s_before_event`). It was converging toward the app's absolute engage orientation,
   `robot_home_rot` (S5 #10 class), and it stalls about 27° short near 7.7 s. The smoke check had only
   verified *position* settling.
   - **The frozen 2° rotation criterion is therefore uninterpretable** in C2, C4L and C4S.
   - Every "VIOLATION on the angle criterion only" above is this confound.
   - The position criterion is unaffected: the position had settled by 2.3 s.
2. **Servo emergency stops for singularity.** These occurred (262–282 per trial) in every trial where
   commands kept streaming while the hand was still near this pose: C2/B0, C4/B0, C4/EPOCH_A and
   C4S/JUMP. They are absent where the gate paused Servo.
   - In **C2/B0**, the 10 cm target jump commanded after resume was **not executed**. The reason was
     Servo's singularity hard stop in this configuration, not any permission logic. C2's physical-level
     B0 PASS is therefore an incidental protection and not evidence that the candidate is absent.
   - In C4L/B0 the arm still moved 180 mm.
3. **C1 oracle strictness.** 5 mm within 0.1 s after release is below what this plant can do at
   0.2 m/s commanded speed (see §3). The frozen verdict stands. The interpretation is in §3.

## 3. What the data show (command level and physical level kept separate)

### Release (C1): a filtered message is not an executing goal stopped, and that is not a physical stop

From `p1_posthoc.json`, r1; r2 and r3 are similar:

| Arm | Last Servo input | Servo output after release | EE x at 6.5 / 6.6 / 6.8 / 7.0 / 7.5 s | Last target x |
|---|---|---|---|---|
| B0 | 6.485 s | continues (holding the target, 300 msgs) | 0.635 / 0.662 / 0.690 / 0.696 / 0.697 | 0.697 |
| D_TO (0.1 s) | 6.488 s | continues | 0.644 / 0.657 / 0.688 / 0.696 / 0.697 | 0.697 |
| PAUSE | 6.487 s | **0 after 6.49 s** | 0.652 / 0.664 / 0.689 / 0.692 / 0.692 | 0.697 |

- In every arm the arm keeps moving 35–45 mm for about 0.5 s after release, toward the last commanded
  target. **Pausing Servo stops Servo's output immediately, but not the motion.** The remaining motion
  is in the trajectory controller and plant: points already sent, plus tracking lag of about 0.2 s at
  0.2 m/s.
- The candidate "motion continues until Servo's 0.5 s timeout" is **not the dominant mechanism**.
  D_TO did not reduce the residual.
- **Conventional remedy not tested here:** a stop at the controller (JTC hold at the current state, or
  a controller switch). It is the next measurement (P1b).

### Cached deadman vs tracking glitch (C2/C3): the cause evidence decides, not the checker

| | C2 cached grip (must block) | C3 glitch (must continue) |
|---|---|---|
| App output after resume | **10.0 cm target jump** under the stale permission, in all 9 C2 trials | continues |
| B0 (forwarded to Servo) | 225 commands forwarded (physical motion prevented only by the singularity stop, §2) | 320, motion 0.157 m |
| REARM_V (I_ALVR: `bPoseIsValid` only) | 0 forwarded ✔ | 0 forwarded → **false block** 3/3 |
| REARM_C (I_FULL: + action activity) | 0 forwarded ✔ | 320 forwarded ✔ (0.157 m) |

- **ROS-side consumption of a stale deadman reproduced at the command level** (EXPERIMENT_CONFIRMED,
  synthetic source). Given a stale *pressed* grip, the unmodified app resumes with the pre-interruption
  offset. Its target jumps by the hand displacement during the interruption.
- **With only the evidence ALVR delivers**, the conventional re-arm rule (S5-style) cannot satisfy both
  C2 and C3. It must choose between residual permission (no re-arm) and a false block on every
  tracking glitch (re-arm).
- **With action activity delivered**, the same conventional rule satisfies both. The limitation is
  **METADATA (evidence delivery), not a checker or method limit.**

### Recenter (C4L/C4S): an epoch is needed; a threshold guard is not enough

| Arm | Command jump C4L (pos/rot) | C4L EE displacement | Command jump C4S | C4S EE displacement | Teleop after the event |
|---|---|---|---|---|---|
| B0 | 0.180 m / 30° forwarded | **180 mm** | 0.015 m forwarded | **15 mm** | continues (displaced) |
| JUMP (Spes thresholds, I_ALVR) | blocked | 0 mm | **not detected**, forwarded | **15 mm** | C4L: stopped, needs a re-press |
| EPOCH_G (I_FULL epoch, gate) | blocked (1 command leaked in 1/3 trials; poll race) | 0 mm | blocked | 0 mm | stopped, needs a re-press |
| EPOCH_A (I_FULL epoch, 15-line app retrofit) | **0 / 0** (continuous) | 0 mm | 0 | 0 mm | **continues without a re-press** |

- The recenter mixes intervals in the unmodified app: it applies the pre-change offset to post-change
  raw poses. The jump reaches the consumer and moves the arm. EXPERIMENT_CONFIRMED (synthetic source,
  ROS side).
- The heuristic guard (Spes thresholds) catches large changes but misses small ones (C4S). It also
  false-blocks legitimate fast motion above about 2.5 m/s (C5, host-only).
- **With the epoch delivered**, both conventional placements work.
  - A generic gate keeps the arm safe at the cost of an operator re-press. It also has a small
    poll-race leak, the S5 PLACEMENT class.
  - The app retrofit keeps continuity but needs implementation-specific knowledge of the app's
    offset/scale semantics.

## 4. Classification for the matrix (P1-scoped)

| Item | Result | Class |
|---|---|---|
| M3 release | The residual motion comes from the downstream pipeline. Servo-level filtering, pausing or a shorter timeout does not stop it. A controller-level stop is untested. | INTEGRATION (stop placement), open until P1b |
| M4 cached deadman | Command-level reproduction. Solved by a conventional re-arm **if** action activity is delivered; with ALVR-level evidence: false blocks or residual permission. | **METADATA** |
| M6 recenter | B0 moves 180 / 15 mm. The jump guard misses small changes and false-blocks fast motion. An epoch makes both a gate and an app retrofit work. | **METADATA** (+ app retrofit is implementation-specific) |

**No method gap was found.** Every failure is closed by an existing mechanism once the relevant evidence
is delivered. The recurring cost is delivering the evidence, which `docs/04_RETROFIT_SITES.md` places
at a different code site in every implementation.

## 5. Not run, or not shown

- Real ALVR, SteamVR or Quest behaviour. The stale grip in C2 was *assumed*; the Monado check of the
  premise is P2 (draft).
- Physical-level C2 motion: masked by the Servo singularity stop.
- Controller-level stop (P1b).
- Rotation outcomes: confounded.
- Physical robot.
- Repetitions beyond 3.
