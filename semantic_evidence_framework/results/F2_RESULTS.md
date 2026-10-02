# F2 results — matched comparison (27 runs, 2026-10-02)

| | |
|---|---|
| Protocol | `experiments/F2_matched_comparison/PROTOCOL_F2.md`, frozen at commit `f3292ee` |
| Raw data | `results/raw/F2/formal` (ignored). sha256 of each file in `results/F2_RAW_SHA256.txt` (360 files). Runner log: `results/F2_runner.log`. |
| Execution | 27/27 runs, rc 0. Host load average 0.4–2.3. |
| Analysis | frozen `analyze_f2.py` → `f2_summary.json` (sha256 `df238171…199a`) |
| Labels | EXPERIMENT_CONFIRMED for the **stand-in app** on unmodified Monado main `045931d`. **Not a real-app result.** |

Every non-B0 arm uses the same command freshness rule F (≤ 200 ms) and evidence freshness rule E
(≤ 50 ms).

## 1. Normal operation (N1)

**0 / 1,878 false blocks in every arm.** The normal-operation criterion is met.

## 2. Dangerous passes, non-boundary (passes / should-block)

Two scoring definitions:

- **S_life:** blocked if the input was inactive at any point between generation and arrival.
- **S_end:** blocked only if it was inactive at generation or at arrival.

| Case | Def. | B0 | FRESH | ARR | GEN_ARR | INTERVAL | ORD | ARR_ORD | GEN_ARR_ORD | INTERVAL_ORD |
|---|---|---|---|---|---|---|---|---|---|---|
| M1 mid-only (150 ms flight, 60 ms gaps) | S_end | 36/36 | 36/36 | 18/36 | **0/36** | **0/36** | 36/36 | 18/36 | 0/36 | 0/36 |
| M1 mid-only (150 ms flight, 60 ms gaps) | S_life | 75/75 | 75/75 | 57/75 | 39/75 | **0/75** | 75/75 | 57/75 | 39/75 | **0/75** |
| M2 duplicates at +100 ms | both | 1807/1807 | 1807 | 1807 | 1807 | 1796 | **0** | **0** | **0** | **0** |
| M3 reverse arrival (active) | both | 939/939 | 939 | 939 | 939 | 939 | **0** | **0** | **0** | **0** |
| M5a evidence +30 ms | both | 71/71 | 71 | **6** | **6** | **6** | 71 | 6 | 6 | 6 |
| M5b evidence +80 ms | both | 72/72 | 72 | 0 | 0 | 0 | 72 | 0 | 0 | 0 |
| M6b outage covering windows | both | 30/30 | 30 | 0 | 0 | 0 | 30 | 0 | 0 | 0 |

**False blocks outside N1:**

| Case | Arm | False blocks | Notes |
|---|---|---|---|
| M5a | evidence arms | 6 / 1,767 | the same 30 ms lag in the other direction |
| M5b | **every evidence arm** | **1,770 / 1,770** | fail-closed: evidence that is 80 ms late always violates E (50 ms) |
| M6a | ARR | 74 | outage only |
| M6a | GEN_ARR | 77 | outage only |
| M6a | INTERVAL | 80 | outage only |
| M6b | ARR, GEN_ARR | 21 | outage only |
| M6b | INTERVAL | 27 | outage only |

**Boundary-inclusive view for M1.** 141 commands lie within 20 ms of an edge. Under S_life,
INTERVAL passes 0/111 of the should-block commands among them, GEN_ARR passes 50/111 and ARR passes
75/111.

## 3. Short windows (M4; all commands are near an edge, so each window is reported separately)

| Window | Collector saw it | Commands overlapping | B0 | ARR | GEN_ARR | INTERVAL |
|---|---|---|---|---|---|---|
| 5 ms | 17 / 18 | 18 | 18 | 18 | 18 | **1** |
| 10 ms | 18 / 18 | 18 | 18 | 0 | 0 | 0 |
| 20 ms | 18 / 18 | 22 | 22 | 4 | 0 | 0 |
| 40 ms | 18 / 18 | 40 | 40 | 4 | 0 | 0 |

The collector runs every 5 ms.

- **5 ms windows:** only the interval check sees them, and it misses one (collector visibility
  17/18).
- **10 ms and longer:** endpoint checks on generation and arrival are enough. Arrival-only misses a
  few.

## 4. Attribution: which check is responsible for what

| Effect | Responsible check (matched conditions) | Evidence |
|---|---|---|
| Stale commands (> 200 ms) | **F**, command freshness. No F2 case was designed to test it. | F1 decomposition: K2, K3b replays, K3c |
| Generated while inactive, arriving after | **GEN_ARR** (endpoint state at generation) | M1 S_end: ARR 18/36 → GEN_ARR 0/36 |
| Inactive only between generation and arrival (mid-only) | **INTERVAL only** | M1 S_life: GEN_ARR 39/75 → INTERVAL 0/75. M4 5 ms windows: GEN_ARR 18/18 → INTERVAL 1/18. |
| Duplicates within 200 ms | **ORD only** (a stamp-order check) | M2: every state arm passes about 1,800 duplicates; INTERVAL blocks the 11 that straddle a window |
| Reverse arrival inside an active period | **ORD only** | M3: 939 → 0 |
| Late evidence (+30 ms) | none. This is a lag artefact for all evidence arms: 6 dangerous passes and 6 false blocks. | M5a |
| Evidence later than E (+80 ms) | fail-closed in every evidence arm: 100 % false blocks, 0 dangerous | M5b |
| Evidence outage | fail-closed: 0 dangerous; false blocks during the outage | M6a/M6b |

**Decision latency:** INTERVAL p95 is 5.5 µs and every other arm is ≤ 3.6 µs. This is negligible
next to evidence propagation (about 11 ms).

## 5. What the matched comparison shows

1. **The interval check adds something only for mid-only interruptions.** These are commands that
   were applicable when generated and when they arrived, but whose permission lapsed in between. It
   also covers windows shorter than the endpoint sampling. Whether such commands *should* be blocked
   is a policy choice: S_life versus S_end.
   - Under **S_end**, GEN_ARR is enough, and INTERVAL adds nothing measurable here.
   - Under **S_life** (the P1 resume policy), INTERVAL is needed.
2. **Duplicates and reverse arrival are not state problems.** No state check, interval included,
   handles them. A stamp-order check does, but only if stamps are monotonic and meaningful.
   `F2_TIMESTAMP_REVIEW.md` shows that no audited real app provides such stamps unmodified.
3. **Evidence latency bounds every state arm.** The boundary band must cover at least the evidence
   delay plus one poll period: M5a shows passes 30 ms after a transition. Evidence older than the
   freshness rule turns every arm into a full block.
4. **Every arm except ARR needs a generation stamp.** Without app changes, only the stamp-free
   receive-time variant of ARR is available (see the timestamp review).
