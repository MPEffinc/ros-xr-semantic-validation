# S4-B CP21: Docker D4-L post-gate delivery-delay comparison (scoped)

**Result: `D4L_SCOPED_FORMAL_COMPLETE` — 200/200 executed, 200/200 `VALID_FORMAL_TRIAL`.** The configuration is the frozen scoped XRROS-S4B-D4LF1-1.0.0, pushed at `e3f9de769c2b8236db11caf0d7f55858cdef2120` before the first trial. Research policy XRROS-S4-1.0.0 is unchanged.

This covers **200 of the 450 registered D4-L combinations**. The other 250 are listed in `formal_summary.json → registered_not_run`: 120 are inferred by monotonicity, 50 are B1 offline profile inferences, and 80 are native cells that are unobservable by construction. The full registered comparison is **not** claimed complete. The input is synthetic, over the original Docker path to MoveIt Servo and Gazebo. There is no actual Quest or physical robot.

## Execution and validity

Evidence is in `runs/s4b_d4l_formal_20260928T105106Z/`: `raw/` (200 directories, 1.9 GB), `attempts.jsonl`, `commands.jsonl`, the frozen `analysis/d4l_formal_audit.py` → `formal_summary.json`, and `runtime_evidence_manifest.sha256` (15,046 files, verified).

- **Run conduct:** all 200 rows ran once, in order. Every first attempt reached the barrier and exited 0. No retry, rerun or concurrent workload occurred.
- **Controls:** all 25 B0/shim pairs PASS, with maximums of 0.204 ms and 0.0052 rad. All 150 matched schedules PASS.
- **Delivery:** the FIFO queue and the idle-time reconnect rule were satisfied in every trial.

## Results

Source age at receiver receipt was about delay + 0.2–1.2 ms in every trial. The B1 source gate decided at ≤ 0.07 ms of source age in every trial.

| Arm (I_FULL) | Cell (n=5 each) | Frozen result | Mechanism / evidence |
| --- | --- | --- | --- |
| **B1 source gate** | L000, L050, L150 at F250 | 5/5 PASS each | Delay within budget |
| **B1** | L350, L750 at F250 | **5/5 FAIL each**: `OVER_BUDGET_SAMPLE_REACHED_CONSUMER_PLACEMENT_EFFECT_POST_DECISION_DELAY` | Gate-local decisions were all correct (0 false accept or reject). About 350 or 750 ms-old samples still reached nonzero Servo commands (20/trial). The inferred F100 result fails from L150 up, and the inferred F500 result fails only at L750. |
| **B2-composed** | All 7 cells | **35/35 PASS** | Rejections at L150/F100, L350/F250 and L750/F500. Decision 2.9–17.0 ms, request 6.0–19.4 ms, settle ≤ 15.8 ms. Official `currently_false` verdict; common stop adapter. |
| **B3 receiving-side** | 6 cells | **30/30 PASS** | Rejections: decision 2.6–16.8 ms, request 3.9–21.1 ms, settle ≤ 14.1 ms |
| **B3** | L050/F100 | 4 PASS + 1 **UNKNOWN_BOUNDARY_STRADDLE** (r04) | A cached copy at about 100.x ms, inside the registered ±1 ms band, was rejected and caused the stop. The first clearly over-budget decision (101.7 ms) came 98 ms later. This is the prospectively registered rule. |
| **B2-native** | Accept cells | 20/20 PASS | — |
| **B2-native** | L150/F100, L350/F250, L750/F500 | **15/15 FAIL**: `NO_EXPLICIT_NEUTRALIZATION_REQUEST` | Every over-budget event was blocked, and 0 over-budget samples reached the consumer, but no stop was requested |
| I_NATIVE (all four) | L750 | 20/20 UNOBSERVABLE | 20 over-budget samples reached nonzero Servo commands per trial, and the robot moved |
| B0 original | All delays | Control | Moved in 25/25 |

- **False acceptance and false rejection:** across all I_FULL receiving-side arms there was 0 false acceptance and 0 false rejection of fresh input.
- **Consumer level:** 0 over-budget first-callback samples in B2-native, B2-composed and B3.
- **Cached repeats:** later cached-repeat callbacks aged past F are reported, for example 20 in B3 L050/F100 r04. They are not scored, as in D2–D4.
- **Stamp preservation:** the receiver's new ROS header never replaced the source stamp. Every defense stamp matched the recorded stamp, which the analyzer checks and invalidates otherwise.

**Overhead (descriptive).** Paired median deltas against the shim:

| Arm | CPU per ~7–8.5 s capture | First-callback p95 |
| --- | --- | --- |
| B1 | +0.6 s | +0.6 ms |
| B3 | +0.4 s | +0.8 ms |
| B2-native | +2.0 s | +13.7 ms |
| B2-composed | +2.4 s | +15.3 ms |

The p95 delta includes cached-command waiting and is not the exact added gate latency, which remains UNKNOWN.

## Interpretation and boundaries

D4-L isolates the **architectural placement effect** the protocol anticipated. A source-side gate with full source information cannot see delivery delay introduced after its decision. It admitted old samples that reached the consumer; its predicate was correct, but its placement was wrong.

The existing receiving-side configurations closed that gap in every scored cell:

- B3, a direct check before the original mapper;
- B2-composed, the official ROSMonitoring verdict plus ordinary stop integration.

This required only the original source stamp to be carried in the I_FULL envelope. B2-native again detected and blocked, but did not neutralize.

For the tested synthetic Docker conditions, this is consistent with **NO_METHOD_GAP**. An ordinary receiving-side freshness check or composed monitor solves post-decision delay; the B1 failure is a placement limitation, not evidence for a new method.

What these results do not show:

- runtime evidence for the NOT_RUN combinations;
- delays beyond 750 ms or jittered delays;
- delay after the receiving-side check, for example between the mapper and Servo;
- actual Quest clocks, OpenVR or physical robots.

S5 remains INSUFFICIENT_EVIDENCE.
