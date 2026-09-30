# Decision — KILL

**Item:** cross-flow temporal-correlation leakage between XR media/input and ROS command/feedback flows
after strong per-flow traffic-analysis defenses. Decided 2026-09-30.

KILL is a successful refutation, not a failure. The decision does **not** rest on attacker experiments,
because none could be run on real data (no CloudXR-capable GPU, no headset/operator, no paired public
dataset). It rests on the topology audit, the construction argument, one real-stack measurement and prior art.
Not measured: how much *unprotected* combined-flow leakage exceeds single-flow leakage. The decision holds
whatever that value is, because the kill comes from the defended regime.

## Kill conditions (brief §9) — which hold

| Kill condition | Holds? | Evidence |
|---|---|---|
| realistic observer cannot see both traffic classes | **partly** — only in shared-segment deployments; not in the lab testbed (separate links) | `docs/01` Gate 1 CONDITIONAL PASS |
| no additional gain from combined observation | not tested | `docs/03` NOT_RUN |
| cross-flow correlation is not the cause | not tested | `docs/04` NOT_RUN |
| **existing defenses make it disappear** | **yes** — a regularising per-flow constant-rate/constant-size defense makes the joint trace task-independent for any attacker (up to session boundaries, which session-level padding removes) | `docs/05` §2 |
| **solved by existing scheduler/shaper combination** | **yes** — NetShaper (single DP tunnel), Minos (mixing) handle the multi-flow case | `docs/05` §1, `literature/defense_baselines.md` |
| XR/ROS only play a testbed role | **yes** — the coupling (operator input → command → feedback → rendered view) exists in any teleoperation loop; prior teleop traffic work uses a smartphone IMU instead of XR (Tang et al.); ROS contributes periodic fixed-size flows, measured as the *easiest* to regularise | `docs/05` §3, `results/stage5_ros_size_probe.txt` |
| **remaining work is parameter tuning without a new algorithm/system** | **yes** — what remains is the latency/bandwidth tuning of known padding/shaping for the media flow, i.e. the excluded "단순 latency-aware traffic padding"; Tang et al. already name it open | `docs/05` §4 |

## KEEP conditions (brief §9) — status

| # | Condition | Status |
|---|---|---|
| 1 | realistic observer in a real system | conditional only |
| 2 | joint observation adds task leakage | untested |
| 3 | the cross-flow relation itself is the cause | untested |
| 4 | leakage survives strong per-flow defenses | **no** — impossible under the regularising defense by construction |
| 5 | not easily removed by existing multi-flow shaping | **no** — NetShaper/Minos exist |
| 6 | a new constraint/algorithm/mechanism is needed | no evidence |
| 7 | removing XR or ROS changes the problem structure | no — any teleop input/command/feedback loop has the same coupling |

## Verdict

**KILL.** The only surviving sub-question is the cost of making a VBR XR media flow (100–200 Mbps,
20–30 ms pose-to-frame budget) constant-rate. That is a per-flow bandwidth/latency trade-off, not a
cross-flow methodology gap, and it falls in the excluded category. Work proceeds to the new gap search:
`docs/08_new_gap_search.md`.

Honest limits:
- The kill would be *re-opened* only by evidence that no regularising defense is deployable for the XR
  media flow within its latency budget, **and** that every cheaper defense leaves cross-flow leakage that
  joint shapers cannot remove at teleop latency. Neither was shown here or in the literature read.
- Items not verified: CloudXR stream encryption and CBR options; real XR task leakage; attacker results
  under any defense.
