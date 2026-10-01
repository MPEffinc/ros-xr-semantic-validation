# PHASE 6 Protocol — Minimal Refutation Experiments

Frozen before the first run (this file's git commit precedes any result). Purpose: test H1–H5 of
`../hypotheses/PROBLEM_DEFINITION.md`, i.e. whether stock HORUS fails the protection goals and whether
existing primitives correctly combined (B1) repair them. Not a vulnerability demonstration.

## Setup

- Image `ros-xr-horus-nav2-jazzy:local` (ROS 2 Jazzy + official Nav2 + `nav2_loopback_sim`), reused from
  the archived testbed; `docker run --network none`, sources mounted read-only.
- HORUS `horus_ros2@eca75cbf` built twice inside the container from a read-only copy:
  **B0 stock** (unmodified) and **B1 existing primitives** (`baselines/b1_existing_primitives.patch`,
  test-only; never applied upstream).
- Bridge params: `tcp_ip 127.0.0.1`, ports 11000/11001, `horuslink_keepalive_ms 0`,
  `multi_operator.control_lease_ttl_ms 1200`, WebRTC off. Backend: default Nav2 adapter; robot `robot1`
  registered via `horus/register_robot` with `nav2_action_topic=/navigate_to_pose`,
  `goal_topic=/robot1/goal_pose`, `cancel_topic=/robot1/goal_cancel`.
- Plant: `nav2_bringup tb3_loopback_simulation.launch.py` (headless). Start pose (-2.0, -0.5);
  goal A (1.5, -0.5); goal B (-1.5, 1.0) (archived coordinates).
- Clients: two HorusLink clients (A, B) using the archived protocol client
  (`Deprecated/authorization_env/horus_runtime_probe.py`, imported read-only, sha256 recorded). A sends
  the catalog snapshot (`role:"host"`) at trial start. Clients report `panel_open=true, task_active=true`.
- Between trials: cancel-all via the Nav2 action service (cleanup, not a defense), reset pose, fresh
  connections, ≥1.6 s gap (> TTL).
- Trials: 5 per case per baseline. No other load on the host during runs.

## Cases and pre-registered criteria

`UNKNOWN` if the trial errored, A's goal never reached `EXECUTING`, or a precondition (e.g. B granted
in C5/C5F) failed. `NOT_RUN` if the case was not executed. Otherwise PASS/FAIL per goal:

| Case | Scenario (paper conditions 1–6) | Goal | PASS iff |
|---|---|---|---|
| C1 | normal single-operator control; B tries during A's lease (1, 2) | PG1 | `b_denied` and not `b_goal_reached_ros` |
| | | PG2 | `a_cancel_terminal == CANCELED` within 3 s |
| C2 | A releases while its goal executes (2, 4) | PG3-stop | A's goal terminal (CANCELED/ABORTED) ≤ 1.0 s after lease end observed |
| | | PG3-cont | A's goal still EXECUTING (or SUCCEEDED) 3 s after lease end |
| | | PG4 | A's post-release goal does not reach ROS |
| C3 | A's heartbeats stop, connection stays; lease expires (TTL) (4) | PG3-stop / PG3-cont / PG4 | as C2 (lease end = `lease_expired`) |
| C4 | A disconnects while its goal executes; A reconnects (new connection), re-acquires, cancels (5) | PG3-stop / PG3-cont | as C2 (lease end = `client_disconnected_release`) |
| | | PG2 (reconnect) | if goal still active at reconnect: `a2_cancel_terminal == CANCELED`; else N/A |
| C5 | handoff: A releases, B acquires (after grant), B sends goal (Nav2 preempts A), B cancels via HORUS (3, 4) | PG2 | `b_cancel_terminal == CANCELED` within 3 s |
| | | PG6 | B's goal not terminated before B's own cancel |
| C5F | as C5 but B's acquire+goal are sent back-to-back right after A's release (race probe for H5) | PG2 / PG6 | as C5 |
| C6 | B (non-holder, self-asserted `host`) removes robot1 from the catalog during A's lease, then sends a goal (6) | PG1 | B's goal before the change does not reach ROS |
| | | PG5 | B's goal after the change does not reach ROS |
| C7 | A streams teleop Twist at 20 Hz, releases after 1 s, keeps streaming 2 s (stale stream) | PG4 | 0 Twist messages reach ROS later than 0.2 s after release |

Expected under the hypotheses (not criteria): B0 fails PG3-stop (C2–C4), PG2 (C5), PG4 (C2, C3, C7),
PG5 (C6); B1 passes those; PG3-cont is the complementary policy and B1 is *expected to fail it by
design* (it implements must-stop). C5F decides H5.

## Recorded per trial

Monotonic timeline (lease state events, XR-side actions, messages on `/robot1/goal_pose`,
`/robot1/goal_cancel`, `/robot1/goal_status`, `/robot1/cmd_vel`, `/cmd_vel`, Nav2 goal status
transitions by UUID), derived measurements, error. Raw JSONL and logs in git-ignored
`../results/raw/<run_id>/`; summary, hashes and the verdict table committed under `../results/`.

## Amendments before the formal run (committed before any formal trial)

- A1. Harness shake-down: three smoke runs (`results/raw/smoke_123938`, `smoke_124118`, `smoke_124458`,
  1 trial each) found and fixed three **harness** bugs: (i) cancel `String` was sent with an extra CDR
  header (the bridge re-adds it for generic topics, `topic_manager.cpp:535-537`), so no cancel reached
  ROS; (ii) retained terminal goals from earlier runs in the Nav2 status array were mistaken for new
  goals; (iii) C4 measured before the disconnect event arrived. Smoke trials are **not** counted.
- A2. C5F is additionally run with **20** trials per baseline (separate run), because a narrow
  cross-topic race is unlikely to appear in 5 trials. Non-observation in 20 trials is reported as
  "not observed", not as absence.
- A3. Verdicts are computed only by `harness/analyze.py` as committed with this amendment.
