# R20 — M12 through the real Docker_Teleop receiver: results (R16; 36/36 valid, 2026-10-04)

| | |
|---|---|
| Protocol | R16, frozen 1648c57; executed from a `git archive` snapshot with per-trial hash and upstream-HEAD checks |
| Raw data | `experiments/M12_receiver/raw/` (ignored, 16 MB, 342 files); sha256 in `results/R_RAW_SHA256.txt`; measures in `results/r_trials.json` |
| Level | **backend/component**: real receiver code @64cbdde (B0 unmodified; B1 = the original + a 21-line edit); synthetic packet producer; no Quest frontend; not a second XR path |

## Results (3 trials per cell; message counts summed; "admitted" = passed as motion)

| Condition | Class | B0 (original receiver + stamp-age check) | B1 (typed provenance + gate), primary | B1 fail-open (logged) |
|---|---|---|---|---|
| N_MOVE | fresh | 2481/2481 | 2481/2481 | 2481/2481 |
| N_STILL | fresh | 2481/2481 | 2481/2481 | 2481/2481 |
| CACHE_GAP (0.2 s silence) | stale_gap (cache republished with fresh stamps) | **21/21 admitted** | **0/21** (`rx_age`) | 0/21 |
| NEUTRAL_GAP (1.0 s silence) | stale_gap / neutral | **27/27** / neutral passed by the stamp check (138; carries `teleop_enable = false`) | **0/27** / 139 → `neutral_stop` (stop only) | 0/27 |
| RECONNECT_DUP | stale_gap / neutral / stale_dup | **27/27 / 11 / 36/36** | **0/27 / 11 → stop / 0/36** (`seq_regress_or_duplicate`) | 0 / — / 0 |
| MISSING_DUP (no seq/session/timestamp 5–8 s) | stale_dup | **36/36** | **0/35** (fail-closed `provenance_missing`) | **35/35 admitted** |
| MISSING_DUP | fresh during the missing window | 2445/2445 | 1909/2419: **506 blocked** (fail-closed) | 2415/2419 |

**Fresh false blocks of B1 outside the designed missing window: 13/14 591.**

- **12** occurred at t ≈ −1.17 s, before the scripted run: a backlog of 4 receiver messages delivered together when
  the gate's subscription matched (receipt age 103–164 ms), in 3 trials.
- **1** occurred at the end of the duplicate window (RECONNECT_DUP r2, 7.209 s): the receiver still published the
  duplicate packet's state while the time-matched ground truth had moved to the next send. This is a
  ground-truth matching edge, reported as counted.

## Reading

- **The original receiver output cannot be checked for source freshness.**
  - Its only time is the 60 Hz publish stamp. The packet timestamp is read nowhere, and the packet receipt time and
    count are internal only.
  - A generic stamp-age check passed every cache republish (48), duplicate (72) and neutral message. This is
    **"not checkable"** (the information is absent from the output), not "checked but failed".
- **The strongest direct fix works within its assumptions.** It has three parts: keep the packet receipt time and
  count plus the producer's sequence/session in a typed message together with the payload, and check them.
  - Every stale cache republish and duplicate was blocked; reconnect with a new session was handled; the false-block
    cost was small (13 / 14 591, explained above).
  - The neutral state is passed only as a stop, never as motion. That policy was declared before running.
- **Fix cost:**

  | Component | Change |
  |---|---|
  | producer | +2 fields (the real Unity sender would need this change) |
  | receiver | +21 lines (edit script), plus a new 3-file message package |
  | gate | a new node; consumers move to the typed topic |
  | everything | **upstream code untouched** in the repository (no license) |

- **What it cannot preserve:**
  - **The sensing time.** Only receipt, plus the producer clock `timestamp`, which is not comparable to the receiver
    clock without a mapping and is not used.
  - **Duplicate detection without a producer sequence.**
    - With provenance missing, the fail-closed policy blocks fresh motion (506 messages in 3 s).
    - A fail-open policy admits all duplicates (35/35).
    - Missing provenance therefore forces a trade-off that the receipt time alone cannot resolve.

## Classification for the matrix (backend/component level)

- **Cache republish and duplicate on the receiver hop:** a known fix (provenance preservation plus sequence checks)
  is sufficient **when the producer supplies a sequence**.
- **Unmodified real receiver:** the needed information is not on the wire. This is **a known root fix that is not
  deployed**, not a method gap.
- **Unresolved:**
  - the real Unity frontend (no sequence; no Quest);
  - the downstream mapper and bridge (not run);
  - the sensing time;
  - S2.
