# P1b results — controller-level stop and the cached-deadman consequence (18 Gazebo trials)

- **Protocol:** `experiments/P1b_stop_and_resume/PROTOCOL.md`, frozen at commit `358dd89` before the
  scheduled runs.
- **Raw data:** `results/raw/P1b/formal_20261001/`, ignored. Per-file sha256 is in
  `results/P1b_RAW_SHA256.txt`, and the runner log is `results/P1b_runner.log`.
- **Execution:** 18/18 trials reached the barrier with 0 setup retries. Host load was about 7–9.
- **Analysis:** frozen `analysis/analyze.py` → `analysis/p1b_summary.json`.
- **Label:** EXPERIMENT_CONFIRMED for ROS-side consumption of a synthetic OpenVR source, in Gazebo.

| Cell | Outcome (3 reps) | Max EE displacement after the event | Notes |
|---|---|---|---|
| C1 release / B0 | VIOLATION 3/3 | 32.8 mm (32.3–35.2) | same as P1 |
| C1 release / PAUSE (Servo-level) | VIOLATION 3/3 | 35.3 mm (29.4–42.4) | Servo output stops, but motion continues |
| C1 release / **HOLD** (controller-level) | **PASS 3/3** | **1.0 mm** | 2 holds sent per trial |
| C2M cached grip, moving hand / B0 | PASS 3/3 (physical) | 0 mm | **225–226 stale-permission commands reached Servo**; 263 Servo singularity emergency stops per trial |
| C2M / REARM_V | PASS 3/3 | 0 mm | 0 commands forwarded |
| C2M / REARM_C | PASS 3/3 | 0 mm | 0 commands forwarded |

## Interpretation (per the pre-registered rules)

1. **Release (M3) is closed by an existing controller-level stop.**
   - Filtering at the Servo boundary (PAUSE) or shortening its timeout (D_TO in P1) leaves 30–45 mm of
     motion.
   - A one-point hold at the measured joint state, sent to the trajectory controller, leaves 1 mm.
   - This is an INTEGRATION/PLACEMENT result: the stop must act where execution happens. It is not a
     method gap.
   - It also measures the brief's distinction directly: a filtered message, a stopped executing goal
     and a physical stop are three different things.
2. **Cached deadman (M4).**
   - The stale-permission commands reach the consumer (command-level reproduction, now 6/6 across P1
     and P1b B0).
   - In this pose, the 10 cm resume jump is refused by MoveIt Servo's singularity hard stop
     (`hard_stop_singularity_threshold`), even with the hand moving.
   - That block is incidental and depends on configuration: P1 C4L/B0 executed an 18 cm jump. It is
     not a permission defense and is not credited as one.
   - The physical consequence of the stale deadman therefore remains **NOT_VERIFIED in this
     configuration**. The evidence-regime result (P1 C2/C3) is unaffected, because it is decided at
     the command level.

## Not run

- Other start poses or configurations that would avoid the singularity region in C2M.
- A hold policy for C4 (recenter) and C2. HOLD was only tested for release.
