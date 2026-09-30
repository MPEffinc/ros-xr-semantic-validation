# 02 — Simulation Setup and Frozen Protocol

Frozen before any formal trial. Smoke runs (`results/raw/smoke/`, git-ignored) were used only to make the
mechanisms work. No predictor error was computed during smoke testing.

## 1. Stack (UPSTREAM)

| Component | Source | Notes |
|---|---|---|
| UR5 description, controllers, MoveIt config | `openvr_ur5e_jazzy@170dad582d624f536359a3192a7f829669c2b031` (`Deprecated/semantic_validation/targets/`), mounted **read-only**; built into git-ignored `ws/` | `ur5_description`, `ur5_controller`, `ur5_moveit_config` |
| Gazebo (gz) + ros2_control JTC + MoveIt Servo (Jazzy) | image `openvr-jazzy-sim:local` (Dockerfile `Deprecated/semantic_validation/harness/openvr_ur5e_downstream/Dockerfile`) | container `n1sim`, `--network none`, `ROS_DOMAIN_ID=61` |
| Servo config | pinned `ur_servo.yaml`: 50 Hz, collision check on (scene threshold 0.02 m), singularity and joint-limit scaling, smoothing off | condition E swaps in `use_smoothing: true` (Butterworth plugin) through a copied launch file `scripts/ur5_servo_variant.launch.py`; the baseline is restored with the same copy and no overrides |
| Bring-up | `scripts/bringup.sh` (copied logic of the archived `run_trial.sh`; pinned launch files unmodified); Servo switched to TWIST | — |

Two known quirks, which are recorded rather than fixed:
- Two `robot_state_publisher` nodes (Gazebo launch + Servo launch) share one name.
- Gazebo runs below real time. Servo integrates on its own wall-time period, so the pipeline uses the
  **wall clock** for operator ticks and log stamps. Sim stamps are logged separately. With sim time, execution
  ran ≈ 1.33× the command (smoke `xscen.jsonl`); with wall time, the final displacement equals the integrated
  command (smoke `xscen_wall.jsonl`).

## 2. Added nodes (SYNTHETIC operator, real pipeline) — `scripts/n1_pipeline.py`

Chain: operator → delay (A) → shared-autonomy blend (F) → CBF safety filter (C) → `/servo_node/delta_twist_cmds`.
Servo then adds collision scaling (D) and smoothing (E, if enabled).

- **Operator.** 50 Hz scripted EE twist in `base_link`: +x 0.08 m/s for 0–3 s, hold 3–4 s,
  −x 0.08 m/s for 4–9 s, hold 9–10 s. A per-trial constant bias ~N(0, 4 mm/s) per axis is added while moving
  (seeded).
- **Home.** `[1.57, -1.2, 1.6, -1.97, -1.57, 0]`, EE (-0.110, -0.338, 0.604). Chosen because the nominal
  scenario produces **no** Servo warning (smoke: status 0 throughout). Other homes triggered Servo
  self-collision or singularity scaling in the nominal case.
- **Reset.** Servo paused (response checked), JTC trajectory to home republished every 1 s with stamp 0, until
  max joint error < 0.002 rad (30 s timeout). The residual is logged as `reset_residual_rad`.
- **A delay.** FIFO between the operator and the robot side, 150 ms.
- **F shared autonomy.** For 4–9 s, u = 0.6·u_op + 0.4·clip(g − p, ±0.1). Here p is the current EE position
  (FK of the latest `/joint_states`) and g = home + (−0.03, 0, 0): the policy wants to stop earlier than the
  operator.
- **C safety filter.** First-order CBF on x, v_x ≤ 2.0·(x_max − x), with x_max = home_x + 0.15.
- **D obstacle.** A 0.20 × 0.06 × 0.30 m box at home + (0.40, 0, 0), published as a PlanningScene diff on
  `/monitored_planning_scene` and removed after the trial.
- **Logging.** JSONL with every stage's twist, `/joint_states`, Servo's `JointTrajectory` output (the final
  executable command), `/servo_node/status` (the intervention reason), plus filter/SA activity and state age.

FK (`scripts/ur5_fk.py`) matches TF `base_link→wrist_3_link` to 2.5e-13 m (20 samples,
`scripts/fk_validate.py`).

Mechanism smoke checks (not results):
- C limited max +x to 0.153 m.
- F stopped the −x motion at −0.087 m.
- D produced Servo code 4 (decelerate for collision) from ≈ 2.4 s. Servo's scaling also slowed the motion
  *away* from the box (upstream behaviour).
- E Butterworth smoothing roughly halved the effective speed.

## 3. Frozen experiment matrix

| Condition | A delay | C filter | D obstacle | E smoothing | F SA | Why kept |
|---|---|---|---|---|---|---|
| N0 | – | – | – | – | – | nominal / calibration |
| A | 150 ms | | | | | delay alone |
| C | | ✓ | | | | filter alone |
| D | | | ✓ | | | Servo collision scaling (upstream) |
| E | | | | ✓ | | upstream smoothing |
| F | | | | | ✓ | shared autonomy |
| AC | ✓ | ✓ | | | | delay × filter interaction |
| AD | ✓ | | ✓ | | | delay × Servo intervention |
| CDF | | ✓ | ✓ | | ✓ | several modifiers at different pipeline points |
| ACDF | ✓ | ✓ | ✓ | | ✓ | full combination |

- 5 repetitions (seeds 1–5) per condition, so 50 trials. Order: seed-major over N0–ACDF excluding E, then an
  E block after one Servo swap.
- Estimated 45–60 min. No other CPU load runs during the campaign.
- **B stale state** is a feedback-link property, so it is applied **offline** to every trial. This is exact,
  because it changes only what the predictor may know:
  - B0 fresh (latest state);
  - B1 all robot-side information delayed by 300 ms;
  - B2 feedback outage from 4.0 to 5.0 s trial time.
- Omitted as redundant:
  - E combinations, because smoothing is a single Servo stage whose effect on prediction equals a lag;
  - A+F, because it is covered by ACDF.

## 4. Predictors (evaluated offline, causally, at every 50 Hz operator tick t; horizon h)

"Robot-side info" means state, post-filter twist, Servo output and status. It is available with age τ
(B0: latest message; B1: +300 ms; B2: none during the outage). ts denotes the time of the robot-side info
used.

| Id | Brief name | Prediction p̂(t+h) |
|---|---|---|
| P0 | Baseline | home + Σ u_op·DT up to t + u_op(t)·h (operator input taken as the future robot state; no feedback) |
| PA | Improved A | FK(q(ts)) + ∫ u_op from ts to t + u_op(t)·h |
| PB | Improved B | FK(q(ts)) + w(ts)·(t + h − ts), where w = latest post-filter twist (Servo input) |
| PC | Improved C | FK(q_cmd + dq_cmd·(t + h − t_cmd)) from the latest Servo `JointTrajectory` (final executable command). **Stale stop:** freeze if t − ts > 0.2 s. **Bound:** r = r_nom; if an intervention is flagged (Servo status ≠ 0, or filter/SA active at ts), r = r_nom + 0.10·h |
| PD | Improved D (strongest) | Forward-simulates every *known* modifier from FK(q(ts)): known delay, SA law and CBF law applied to the operator inputs from ts to t + h (u_op held). Servo effects are not modelled (internal) but handled by the PC flag/bound; same stale stop |

- **Horizon.** h = 0.25 s primary (≈ nominal command-to-execution lag seen in smoke); 0.5 s secondary.
- **r_nom calibration.** The 95th percentile of PC's error in N0/B0 (all 5 seeds), computed per h before any
  other condition is analysed. The same r_nom is used for PD.

## 5. Metrics and decision rules (frozen)

**Metrics.**
- e(t) = ‖p̂(t+h) − p(t+h)‖, where p is FK of `/joint_states` interpolated at t + h.
- Per trial: mean, p95 and max e over displayed (non-frozen) ticks; mean e in [onset, onset + 0.5 s] after each
  intervention onset; mean e in the B2 window.
- **Misleading duration:** displayed ticks with e > max(0.02 m, r) (r = 0 for P0–PB), in seconds.
- **Freeze ratio:** frozen ticks / all ticks.
- **Task interruption:** any Servo status 5 (halt), or final |x − x_intended| > 0.05 m, where x_intended is
  the end of the integrated operator command.

**Validity.** A trial is valid if reset_residual < 0.01 rad and the log is complete (≥ 480 operator ticks,
≥ 300 Servo outputs). Invalid trials are reported, not replaced.

**Decision rules.**
- **Q1 YES (→ KILL)** if PC or PD has median misleading duration ≤ 0.1 s per trial in every condition × B
  level, and their max error while displayed is ≤ r + 0.02 m in ≥ 4/5 seeds.
- **Q2 (→ IMPLEMENTATION_GAP_ONLY)** if residual misleading time disappears once a specific piece of available
  information is propagated, as shown by the ablations in docs/05.
- **Q3.** Residual misleading time persists for PD in ≥ 4/5 seeds of some condition after all available
  information is used. Then identify the mechanism. The outcome is METHOD_GAP_CANDIDATE only if the mechanism
  is structural (not missing propagation), and NEEDS_REAL_XR_VALIDATION if it hinges on the operator/display
  loop.
