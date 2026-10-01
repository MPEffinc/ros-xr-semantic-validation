# PHASE 6 Results — Authority-Transition Cases vs. Existing Baselines

Status of every statement here: EXPERIMENT_CONFIRMED in this workspace, in the setup of
`../experiments/PROTOCOL.md` (software loopback plant, not a physical robot, not a real Quest/Unity
client). Criteria were frozen in commit `421a050` before the formal runs.

## Runs

| Run | Trials | Started / finished (UTC) | Repo HEAD at run | Errors |
|---|---|---|---|---|
| `ac6_formal_main` | 8 cases × 5 × 2 baselines = 80 | 2026-09-29T12:49:02Z / 13:00:31Z | `421a050` (clean) | 0 |
| `ac6_formal_c5f20` | C5F × 20 × 2 = 40 | 2026-09-29T13:00:31Z / 13:06:47Z | `421a050` (clean) | 0 |

- HORUS `horus_ros2@eca75cbf` (unmodified for B0; B1 = test-only patch sha256 `238b22d8…5b36`).
- Image `ros-xr-horus-nav2-jazzy:local` id `sha256:ff6138bc9bdb…dc86`; `docker run --network none`.
- Commands: `sg docker -c "AC_TRIALS=5 scripts/run_phase6.sh ac6_formal_main"`;
  `sg docker -c "AC_TRIALS=20 AC_CASES=C5F_handoff_back_to_back scripts/run_phase6.sh ac6_formal_c5f20"`;
  `python3 experiments/harness/analyze.py results/phase6_verdicts.json results/PHASE6_VERDICT_TABLE.md <both trials.jsonl>`.
- Input hashes per run: `raw/<run>/inputs.sha256`; all raw files (git-ignored, local):
  `PHASE6_RAW_SHA256.txt`; per-trial measurements and verdicts: `phase6_verdicts.json`.
- Smoke runs (`smoke_*`, harness debugging) are hashed but **not counted**.

## Verdicts (pre-registered criteria; counts of trials)

| Case | Goal | B0 stock HORUS | B1 existing primitives |
|---|---|---|---|
| C1 normal control | PG1 exclusivity | PASS 5 | PASS 5 |
| C1 | PG2 holder stop | PASS 5 | PASS 5 |
| C2 release while executing | PG3-stop | **FAIL 5** | PASS 5 |
| C2 | PG3-cont | PASS 5 | FAIL 5 (by design: B1 = must-stop) |
| C2 | PG4 stale admission | **FAIL 5** | PASS 5 |
| C3 TTL expiry while executing | PG3-stop | **FAIL 5** | PASS 5 |
| C3 | PG3-cont | PASS 5 | FAIL 5 (by design) |
| C3 | PG4 | **FAIL 5** | PASS 5 |
| C4 disconnect / reconnect | PG3-stop | **FAIL 5** | PASS 5 |
| C4 | PG3-cont | PASS 5 | FAIL 5 (by design) |
| C4 | PG2 after reconnect | PASS 5 | N/A 5 (goal already stopped) |
| C5 handoff | PG2 new holder stop | **FAIL 5** | PASS 5 |
| C5 | PG6 cross-epoch | PASS 5 | PASS 5 |
| C5F handoff back-to-back | PG2 | **FAIL 25** | PASS 25 |
| C5F | PG6 | PASS 25 | PASS 25 |
| C6 catalog change during lease | PG1 | PASS 5 | PASS 5 |
| C6 | PG5 catalog integrity | **FAIL 5** | PASS 5 |
| C7 stale teleop stream | PG4 | **FAIL 5** | PASS 5 |

No UNKNOWN, no NOT_RUN among the registered cases. SROS2 and controller timeouts: NOT_RUN (reasons in
`../audit/EXISTING_DEFENSES.md`).

## Supporting measurements (median [min, max])

- Lease end observed after the triggering action: release 0.0006 s, disconnect 0.0007 s, TTL 1.517 s
  [1.337, 1.531] (TTL 1200 ms + 500 ms sweep).
- B0, C2–C4: 0 cancel messages on ROS after lease end (15/15); Nav2 controller still commanding motion
  2.5 s later (15/15); goal `EXECUTING` 3 s later (15/15).
- B1, C2–C4: exactly 1 cancel per trial; goal terminated 0.031 s [0.003, 0.038] (release), 0.022 s
  [0.005, 0.027] (TTL), 0.032 s [0.004, 0.040] (disconnect) after lease end; no motion 2.5 s later.
- B0, C5/C5F (30 trials): A's goal ended `ABORTED` by Nav2 preemption; B's HORUS cancel then produced the
  HORUS status `goal_cancelled` **while B's goal kept executing** (30/30) and the plant kept moving
  (30/30). This matches source F8 (single `active_goal_handle` cleared by A's late ABORTED result).
- B1, C5/C5F (30 trials): B's cancel terminated B's goal in 0.005–0.006 s median; no misleading status.
- C7: B0 admitted 36/36 stale Twist messages per trial after release (5/5); B1 admitted 0 (5/5).
- C6: B0 admitted B's goal after B's self-asserted `host` catalog `remove` while A held the lease (5/5),
  Nav2 executed it; B1 ignored the catalog change (5/5).
- H5 (cross-epoch race of B1's lease-end cancel against B's back-to-back goal): **not observed in 25
  trials**. This is non-observation, not proof of absence.

## Mapping to hypotheses

| Hypothesis | Result |
|---|---|
| H1 stock violates PG3-stop on release/TTL/disconnect | EXPERIMENT_CONFIRMED (15/15) |
| H2 stock violates PG2 after handoff | EXPERIMENT_CONFIRMED (30/30) |
| H3 stock violates PG4 and PG5 | EXPERIMENT_CONFIRMED (C2/C3/C7 15/15; C6 5/5) |
| H4 existing primitives, combined, satisfy PG1–PG5 (must-stop policy) | EXPERIMENT_CONFIRMED (all B1 targeted goals PASS) |
| H5 residual cross-epoch race in B1 | NOT observed (0/25); UNKNOWN beyond this sample |

Stock HORUS **passes** PG3-cont (continue-after-release) in all 15 trials; so continuation alone is only a
violation under a must-stop policy. Under the may-continue policy the stock failure that remains is PG2
(the next holder cannot stop the continuing robot through HORUS, and HORUS reports `goal_cancelled`).

## Relation to archived results (PRIOR_INTERNAL)

The archived August-2026 track reported the same qualitative behavior at the same commit (release/TTL/
disconnect without cancel; post-handoff official cancel failure; client-asserted catalog). These results
are independent re-measurements with a new harness and fixed pre-registered criteria; their novelty
contribution is the **B1 sufficiency test**, which the archive did not run in this form.

## Limits

Software loopback Nav2 plant; mock HorusLink clients (real Unity client closed-source, its own
client-side checks not exercised); one robot; one adapter (Nav2); 5 trials per case (25 for C5F).
