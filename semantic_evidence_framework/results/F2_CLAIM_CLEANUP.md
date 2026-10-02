# Claim cleanup after F1 (2026-10-02, post-hoc; F1 frozen files are unchanged)

Source: `experiments/F2_matched_comparison/f1_posthoc_decomposition.py` →
`f1_posthoc_decomposition.json`, applied to `results/raw/F1/linkage_formal` (F1 raw sha256 in
`results/F1_RAW_SHA256.txt`). This analysis was written **after** the F1 results and is labelled
post-hoc.

## 1. Two claims, kept separate

| Claim | Status |
|---|---|
| **(a) Runtime state can be collected without modifying the app.** The input-activity flags come from monado-service through libmonado, out of the app process. | EXPERIMENT_CONFIRMED on Monado main with a stand-in client. It also holds for a real app's client in principle: the collector saw the unmodified OpenVR app's client in candidate 1 (state READY, never focused). |
| **(b) The command's generation interval can be checked without modifying the app.** | **Not shown.** F1 used the stand-in injector's `header.stamp` as the generation time. Whether a real app's stamp means "sample/generation time" on the evidence clock is a property of that app (see `F2_TIMESTAMP_REVIEW.md`). |

Stand-in results are **not** evidence of real-app applicability or of reduced modification cost for
real apps.

## 2. Totals with boundary commands included (F1, all 3 runs)

| Case | should_block (non-boundary / incl. boundary) | C_INTERVAL passes (non-boundary / incl. boundary) | B0 passes (incl. boundary) |
|---|---|---|---|
| K2 | 348 / 360 | 0 / 0 | 360 |
| K3a | 299 / 318 | 0 / 0 | 318 |
| K3b | 444 / 453 | 0 / **2** | 453 |
| K3c | 150 / 150 | 0 / 0 | 150 |
| K4 | 291 / 300 | 0 / **2** | 300 |
| K5b | 294 / 303 | 0 / **6** | 303 |
| K6 | 291 / 299 | 0 / **1** | 299 |

Including boundary commands, C_INTERVAL let **11** should-block commands through. All of them lie
within 20 ms of a transition. The guarantee "0 dangerous passes" holds **only outside the ±20 ms
band**.

## 3. How much of the blocking is explained by command freshness alone?

Freshness means age ≤ 200 ms and t_gen ≤ t_arr + 5 ms.

| Case | C_INTERVAL blocks explained by freshness alone | should-block commands passed by *freshness + arrival-state* (C_ARRIVAL ∧ fresh) | Main reason for should-block |
|---|---|---|---|
| K2 (late arrival, 2.5 s) | **348 / 348** | 0 | stale (+ generated inactive) |
| K3a (reorder ≤ 150 ms) | 0 / 299 | **6** | generated and/or arrived inactive |
| K3b (replay after loss) | **150 / 444** (the replays) | 0 | the replays are stale; the rest arrived inactive |
| K3c (stale replay) | **150 / 150** | 0 | stale |
| K4, K5b, K6 | 0 | 0 | arrived inactive |

**Corrected reading of F1.**

- The late-arrival and replay blocks attributed to the interval check in F1 (K2, K3b replays, K3c)
  come entirely from the **200 ms command freshness limit**. That limit was applied only to
  C_INTERVAL and D_STREAM, not to C_ARRIVAL or D_DIRECT. F1's comparison was therefore
  **confounded**: the arms had unequal freshness rules.
- With equal freshness, "freshness + arrival state" matches C_INTERVAL everywhere except **6
  commands in K3a**. Those 6 were generated during the inactive window and arrived after it within
  150 ms. A generation-time state check would also catch them, so the data do not separate "interval"
  from "generation + arrival".
- The structural question remains open: does the interval check add anything beyond age, order and
  duplicate checks plus endpoint states? F2 tests it with matched conditions.
