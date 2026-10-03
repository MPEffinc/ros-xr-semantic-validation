# R19 — M12 source stall: receive watchdog results (R15; 36/36 valid, 2026-10-04)

| | |
|---|---|
| Protocol | R15, frozen 290de4d; executed from a `git archive` snapshot of 290de4d, hash-verified before every trial |
| Raw data | `experiments/M12_watchdog/raw/` (ignored); sha256 in `results/WD_RAW_SHA256.txt`; measures in `results/wd_trials.json` |
| Validity | 36/36 valid on the first attempt; no Servo masking statuses |
| Level | command level. Real app (A2 copy), synthetic periodic source, Monado remote driver (S1/S2 = **patched runtime variant**, labelled) |

## Results (3 trials per cell)

| Condition | S0 (R13 A2, original runtime) | S1 (driver receive watchdog 100 ms + A2) | S2 (receipt evidence at the gate + A2) |
|---|---|---|---|
| N_MOVE: fresh admitted | 811/811 | 810/810 | 811/811 |
| N_STILL (periodic identical packets): fresh admitted | 810/810 | 809/809 | 809/809 |
| STALL15: stale_source admitted | **84/84** | **0** (the app generated 0 messages in the stall) | **0/84** (blocked: `source_rx_age`) |
| STALL5: stale_source admitted | **294/294** | **0** (0 generated) | **0/294** |
| Last admitted command after stall start | 1.46 s / 4.96 s (to the end of the stall) | 0.059–0.067 s | 0.060–0.066 s |
| First admitted command after stall end (recovery) | 0.010–0.014 s | 0.010–0.058 s | 0.010–0.015 s |
| Resume target jump (last admitted before vs first after) | 47.9 mm / 67.9 mm | 47.9 / 67.9 mm | 47.9 / 67.9 mm |
| Fresh false blocks (all conditions) | 0 | 0 | 0 |

## Reading

- **The standard root fix works for the stated contract.** A receive watchdog for a periodic source (10 ms period,
  100 ms timeout), placed either in the driver (S1) or as a receipt-age check at the gate (S2):
  - stopped every source-stale command on this path within one watchdog period (≈ 60–67 ms after the last packet);
  - recovered within one app tick after packets resumed;
  - produced no false stop for a still hand that keeps sending identical packets.
- **The two placements differ in where the decision lives:**

  | | S1 (driver) | S2 (gate) |
  |---|---|---|
  | Effect | the runtime reports the controller as untracked, so the original app logic stops generating commands | commands keep flowing and are rejected |
  | Information used | — | the latest receipt time of a separate stream |
  | Link to a specific pose | — | **none**: on this path the pairing is implied only by temporal ordering, not proven |

- **Still unresolved:**
  - **The resume jump** (47.9 / 67.9 mm) is unchanged. The app keeps its offset across the pose-invalid interval,
    and the watchdog does not re-arm or re-anchor (M5/M39 territory, R04).
  - **Physical sensing freshness.** The watchdog measures packet receipt. A source that keeps sending packets with
    stale content (a frozen sensor, a replaying driver) is not detected by either placement.
  - **Event-driven sources** are not covered by this policy.
  - **Real headsets**, which have their own runtimes and their own tracking-loss semantics.
  - **S2-class threats** (a compromised driver or gate) are out of scope.
- **Classification.** M12 source stall is **solved by a known root fix for periodic synthetic sources on this path**
  (a deployment change in the runtime driver or a gate with driver evidence). It is not a method gap. The
  information was available at the driver and only needed to be kept.
