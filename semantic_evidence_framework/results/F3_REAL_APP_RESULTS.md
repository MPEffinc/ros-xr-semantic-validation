# F3 results — one real XR→ROS app, end to end, receive-time state (6 trials, 2026-10-02)

| | |
|---|---|
| Protocol | `experiments/F3_real_app_receive_time/PROTOCOL_F3.md`, frozen at commit `9e9e303` |
| Raw data | `results/raw/F3/` (ignored); per-file sha256 in `results/F3_RAW_SHA256.txt` (132 files); `results/F3_runner.log` |
| Execution | 6/6 trials, rc 0. Host load average 3.8–12.4, including our own Gazebo. |
| Frozen analysis | `analyze_f3.py` → `f3_summary.json` (sha256 `e8427252…`) |
| Post-hoc diagnostics | `posthoc_f3.py` → `f3_posthoc.jsonl` (sha256 `2751ae33…`), written after the frozen analysis |

## What ran

The unmodified **OpenVR UR5e** app (`quest_teleop.py` @ 170dad5) ran through xrizer @ 0989a7f.

- **xrizer is a modified deployment component.** Three changes:
  - (1) a Vulkan extension filter;
  - (2) a background frame pump that also updates `display_time`;
  - (3) legacy input on the temporary session.
- **The rest is unmodified:** Monado main 045931d, MoveIt Servo 2.12.4 in Gazebo.
- **No GPU environment change was needed** (lavapipe).
- **This is a real teleoperation app.** It is not a generic OpenXR test app. It was not modified.
- **Input came from Monado's `remote` driver**, not a headset.

**Effects of the deployment change on the app:**

- The app's 50 Hz timer now runs at about **20 Hz**: 20.1 Hz pre-window in every trial. The pump
  blocks in `xrWaitFrame` on the null compositor's frame period.
- Poses are now located at the predicted display time instead of the init time. The command stamp
  minus the gate receive time has a median of −0.44 ms.

## Results (frozen measures, 3 trials per arm)

| Measure | B0 (app → Servo) | GATED (receive-time state) |
|---|---|---|
| App commands per trial | 260–261 | 260 |
| Gate false blocks before the window | — | **0 / 109–110** (normal criterion met) |
| App commands inside the runtime-applied deactivation (8.0–9.5 s, ±20 ms excluded) | **0** | **0** |
| Commands reaching Servo inside the window | 0 | **0** (gate claim met) |
| Commands reaching Servo in the ±20 ms boundary band | 1 per trial | 1 per trial |

## Interpretation

1. **The real chain is connected and the gate behaves as claimed.** An unmodified app's commands
   passed through a receive-time-state gate and on into the consumer. The evidence came from the
   runtime, out of the app process; FOCUSED, IO and input-block flags were all observable for this
   compositor-backed client. Normal operation saw no false blocks. Nothing reached Servo while the
   runtime reported input inactive.
2. **On this stack the gate had nothing to block.** The runtime's deactivation invalidates the poses
   that xrizer returns, so the app itself stops publishing. In-window app commands were 0 in both
   arms. Only boundary-band commands remain, about 1 per trial in both arms. **The gate's measured
   added protection here is zero.** It would matter only for paths where commands keep flowing
   during an interruption, such as the PickNik frozen stream (R0) or the cached deadman under ALVR
   (K6). Neither of those paths is runnable here.
3. **Resume after the interruption is not covered by receive-time state** (post-hoc, command level).
   - At reactivation the app resumed **without a fresh press**, because the held grip reads true
     again with no edge. It kept its pre-interruption offset, so the command target **jumped 35.0 mm**
     in every trial of both arms. That equals 0.5 × the 70 mm hand motion during the window. The gate
     admitted it, since input was active at receive time.
   - This is the S5 #10 / P1 resume class. Blocking it needs a resume rule (a fresh press after an
     interruption), and the gate cannot see button edges from libmonado's client flags.
4. **The physical effect of the jump is masked.** The arm followed normally before the window
   (74.6–74.8 mm of progress between 4.0 and 7.5 s). After the resume jump, Servo's singularity hard
   stop held it for the rest of every trial (about 350 HALT_FOR_SINGULARITY statuses). This is the
   same configuration-dependent confound as in P1/P1b. **The frozen "EE jump after resume" measure,
   about 0.01 mm, is therefore not interpretable.**

## Second app

None is available on this host. IsaacTeleop needs NVX1 extensions, and the other five audited
frontends are Android/Unity/WebXR builds (`APP_COMPATIBILITY.md`). The expansion step was not
reached.
