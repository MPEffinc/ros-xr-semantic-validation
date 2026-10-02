# F2 — matched comparison of state, interval and order checks (frozen 2026-10-02, before measured runs)

## 0. Scope

- **Mechanism study with the stand-in app** (`sa_client` + injector). It does **not** count as a
  real-app result.
- **Runtime:** unmodified Monado main `045931d` (image `f1-monado-main:045931d`), headless, `remote`
  driver. One container, one uid.
- **Security scope:** S1 only (`../F1_independent_evidence/SECURITY_SCOPE.md`).
- **Confound removed:** F1 applied command freshness unequally across arms (`results/F2_CLAIM_CLEANUP.md`).
  In F2 every non-B0 arm uses identical freshness rules.
- F1 files are not changed.

## 1. Truth

Runtime-applied inactive windows are `[ret(off), call(on)]` from `mnd_sched`. This is one persistent
libmonado connection that toggles IO at absolute CLOCK_REALTIME times. In the setup probe
(`results/raw/F2/probe_short`, excluded) a call took about 0.03 ms, and the applied durations of
5/10/20/40 ms matched the targets within 0.1 ms.

- The edge times are the call times.
- **Boundary:** t_gen or t_arr within 20 ms of an edge. Boundary commands are reported separately.

## 2. Arms (same command stream; same F and E rules for all non-B0 arms)

| Rule | Definition |
|---|---|
| F (command freshness) | t_arr − t_gen ≤ 200 ms and t_gen ≤ t_arr + 5 ms |
| E (evidence freshness) | a state lookup at time t uses the latest *visible* evidence sample at or before t, and requires it to be ≤ 50 ms older than t |
| δ | 10 ms (the interval starts at t_gen − δ) |

| Arm | Rule |
|---|---|
| B0 | admit all |
| FRESH | F |
| ARR | F ∧ E: active at t_arr |
| GEN_ARR | ARR ∧ E: active at t_gen |
| INTERVAL | ARR ∧ every evidence sample in [t_gen − δ, t_arr] active, with no gap > 50 ms |
| ORD | F ∧ t_gen > last admitted t_gen of this arm. This is a stamp-order check that rejects duplicates and reverse arrivals, and needs no sequence field. |
| ARR_ORD, GEN_ARR_ORD, INTERVAL_ORD | the corresponding arm ∧ the ORD rule (per-arm state) |

## 3. Cases

- **Run layout:** 16 s per run. One command every 20 ms in [1.5, 14) s. Grip held throughout.
- **Exact tables:** `harness/cases.py`.

| Case | Inactive windows | Delivery | Purpose |
|---|---|---|---|
| N1 normal | none | 10 ms + U[0, 8] ms | normal-operation criterion |
| M1 mid-only | 60 ms at 3, 5, 7, 9, 11, 13 s | 150 ms for all commands | generated and arriving active, inactive only in between |
| M2 short replay | 40 ms at 4, 8, 12 s | every command delivered at 10 ms **and** again at 110 ms | duplicates within 200 ms, some across a window |
| M3 reverse order | none | 60 ms for even seq, 0 ms for odd seq | older commands arrive after newer ones inside an active period |
| M4 short windows | 24 windows of 5/10/20/40 ms (cycled, every 0.5 s from 2.0 s) | 10 ms | windows at or below the polling scale (collector 5 ms, app about 10 ms) |
| M5a / M5b evidence delay | 200 ms at 4, 8, 12 s | 10 ms | gate sees evidence 30 / 80 ms late |
| M6a evidence outage | none | 10 ms | collector SIGSTOP during [5.0, 5.3) and [9.0, 9.3) |
| M6b outage over a window | [5.10, 5.20) and [9.05, 9.25) | 10 ms | collector SIGSTOP as in M6a, covering the windows |

**Runs:** 9 cases × 3 runs = **27** (seed 20261003, rep-major, shuffled). About 13 minutes. A setup
smoke of N1, excluded, already passed: 626/626 admitted by every arm.

## 4. Scoring (`analyze_f2.py`, frozen)

Each command gets categories:

- `stale`: age > 200 ms;
- `dup`: not the first arrival of its seq;
- `ooo`: its seq is lower than one already arrived;
- `end_inactive`: t_gen or t_arr is inside a window;
- `mid_only`: a window overlaps (t_gen, t_arr) while both endpoints are active.

Two definitions of "should block" are reported side by side:

- **S_endpoint** = stale ∨ dup ∨ ooo ∨ end_inactive. A command may run if it was applicable when it
  was generated and when it arrived.
- **S_lifetime** = S_endpoint ∨ mid_only. No command may survive an interruption. This matches the
  P1 resume policy.

Metrics:

- dangerous passes and false blocks per arm, under each definition;
- per-category pass counts, which attribute each block to F, endpoint state, interval or order;
- M4 per window duration: collector visibility and passes of overlapping commands;
- M6 false blocks during the outage (the fail-closed cost);
- decision latency.

## 5. Criteria (fixed in advance)

1. **Normal operation (N1).** Each evidence arm must have false blocks ≤ 0.5 % of should-admit. If
   not, the arm is reported as failing the normal criterion.
2. **Interval effect.** It is attributed to the interval check only where INTERVAL blocks a
   `mid_only` command that GEN_ARR passes. If `mid_only` commands are blocked by F alone, they are
   **not** credited to INTERVAL.
3. **Order effect.** `dup`/`ooo` blocks are attributed to ORD only where the state arms pass them.
4. **M4.** A window shorter than the collector period can be missed. Misses are reported as a
   detection limit, not as an arm failure. The window durations at which each arm reaches 0 passes
   are reported.
5. **No retuning after outcomes.** Thresholds stay as frozen.
