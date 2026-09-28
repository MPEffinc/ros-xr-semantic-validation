# XRROS-S4B-D6Q1-1.0.0 — prospective Docker D6 invalidation/recovery setup qualification and design report

This campaign instantiates, and does not change, XRROS-S4-1.0.0 D6 (research protocol SHA-256 `3a40337121f8d687dc68036ff2ffc85a1bc6eda275a700ba7d9e8119cd322969`). The registered D6 case is: "Valid→invalid for 1 s→valid held teleop for .8 s→release .2 s→press at current reference→+.15 X; both registered recovery policies, no jump caused solely by lost/reacquired reference". The capture is 10 s. Thresholds are the originals, with F250.

D1–D5 results are unchanged and not pooled. D5 is a scoped 50-trial study, and D4-L is a scoped 200/450 study.

## Fixture (`inputs/d6_fixture.py`)

20 Hz, 200 slots, one connection, generation 1, and a fresh stamp for every sample.

| Slots | Phase | Teleop | Tracked | Position |
| --- | --- | --- | --- | --- |
| 36–55 | Active (moving) | true | true | x=.35 |
| 56–75 | **Invalid** (1 s) | true | **false** | x=.35 |
| 76–91 | Valid, held grip (0.8 s) | true | true | x=.35 |
| 92–95 | Release (0.2 s) | false | true | x=.35 |
| 96 | Press at the current reference | true | true | x=.35 |
| 112–131 | Subsequent movement | true | true | x=.50 |

## Implementation (declared delta vs the D5Q2 inputs; see `preflight/d5q2_to_d6q1_input_delta.txt`)

- **Shared code:** D6 uses the D5 recovery state machine, the I_FULL receiver-connection observation, the stop/resume adapter mode, and the 10 s / 500-tick capture. The D5-only branches now accept `CASE_ID` values D5 and D6.
- **Sender:** `d5_sender.py` selects the fixture module by case. It closes, reconnects or replays only when the fixture defines those events, which D6 does not. It emits `isTracked` from the fixture.
- **Probe:** `d1_probe.py` also checks the tracked state against the fixture.
- **Invalidation:** invalid tracking with teleop held is an invalidation fault (`INVALID_TRACKING`) in the shared state machine.
- **Transport:** a reconnect is legal only after at least 1.5 s with no bytes. The only case is B1 R_EXPLICIT, which correctly withholds 1.8 s (slots 56–91). Each reconnect must be matched by the original receiver's own idle-drop log line.
- **Setup analyzer:** `analysis/d6_setup_audit.py` runs the frozen D5 `inspect()` and `pair()` with the D6 fixture and transport rules.

## Host preflight

- **`analysis/test_d6.py`, 6/6 PASS.**
  - The timelines show R_EXPLICIT rejecting all 20 invalid and all 16 held-grip samples and re-arming exactly on the edge sample 96. R_AUTO re-arms at 86, 500 ms after the first valid sample 76.
  - The real TCP loopback reproduces the original 1.5 s idle drop:
    - B0 sends everything on one connection.
    - B1 I_FULL withholds slots 56–91 (R_EXPLICIT, one logged reconnect) and 56–85/86 (R_AUTO).
    - B1 I_NATIVE withholds only the invalid slots 56–75 and has no recovery.
    - Every sent sample is received once.
  - Attempt 1 failed a single assertion: R_AUTO re-armed on slot 87 instead of 86, because the 500 ms dwell boundary falls exactly on a sample and real-time jitter deferred it. That output is retained in `preflight/test_d6_attempt1.*`. The test now accepts 86 or 87.
- **D5 regression in this root:**
  - `test_d5_rearm`: 16/16.
  - `test_d5_sender`: first run 4/5, with the same dwell-boundary jitter at 83 vs 84, which D5 formal also showed. The first output is retained, the boundary tolerance was added, and the rerun passed 5/5.
- **Official monitor/oracle path:** the D5Q2 genuine component result is reused. The property code path is identical apart from the case check, and the invalid-tracking predicate is the same `validity()` function.

## Design report (minimum-sufficient scaling)

- **Candidate matrix:** 10 arms × 2 recovery policies × 5 repetitions = 100.
- **Essential:**
  - I_FULL B1, B2-native, B2-composed and B3 × R_EXPLICIT and R_AUTO, 8 per repetition: the invalidation stop, no motion from invalid samples, held-grip prevention, the dwell, the fresh reference, the subsequent movement, and attribution.
  - B0 and the shim, 2 per repetition, which are policy-independent.
- **Redundant for formal repetition:**
  - B0 and the shim across policies (byte-identical).
  - I_NATIVE × both policies. The native interface carries tracked and teleop, so D2 already showed native invalid-tracking stops. It does not carry the freshness or generation that the registered recovery rule requires, so no native re-arm machine runs. I_NATIVE is run once in setup to document the consequence (a held-grip restart) and is NOT_RUN in the formal campaign.
- **Evidence split:** host tests cover all timings and edge cases. Gazebo is used for the real stop/resume control path, jump-free re-reference and the subsequent movement.
- **Proposed formal campaign:** 50 trials, 10 per repetition × 5, about 1 h, sequential with no concurrent load.
- **Claims:**
  - Supported: I_FULL D6 behavior under both policies, B2-native versus B2-composed, and the original's consequence.
  - Unsupported: formal native repetitions, other invalid durations, actual Quest tracking loss, and physical robots.

## Setup schedule and gate

`qualification_schedule.csv` lists 14 cells: B0/shim, I_FULL × 2 policies (8), and I_NATIVE (4). All must move. At most two retries are allowed, and only before the barrier. The B0/shim pair must be within 5 ms and 0.02 rad. Every cell must be MEASUREMENT_QUALIFIED under `analysis/d6_setup_audit.py`. This is not a policy score.
