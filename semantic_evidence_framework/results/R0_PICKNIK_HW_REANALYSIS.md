# R0 — Reanalysis of the 2026-09-17 PickNik real-Quest capture

**Label.** The data is **PRIOR_INTERNAL**: a capture from the closed S-track, with a real Quest 3 and the
PickNik Unity app, a ROS-TCP-Endpoint and an observer, and no robot. The analysis is **new**: it was
written 2026-10-01 and is read-only. It is not counted as a new experiment of this study, and it says
nothing about a physical robot or the closed MoveIt Pro host.

| Item | Value |
|---|---|
| Input | `Deprecated/semantic_validation/results/runs/hw_picknik_native_20260917T074600Z/ros_observer.jsonl` sha256 `7e1fdcfd05cd8a85145b33ac9ca1b1b57e852d8852f7383910e0f7bdb171c43c`; `sideband_final.jsonl` sha256 `313eaa39ebd4c07df4e3791e943d7bf2fc983971d34ea0de55c0b74bc91de062`. Both are tracked in git and unchanged. |
| Script | `experiments/R0_picknik_hw_reanalysis/reanalyze.py` sha256 `e558162c4d485bac7ecf08e41252143565d66c9af7368d1d29a1e738885f7eb4` |
| Output | `experiments/R0_picknik_hw_reanalysis/reanalysis_output.json` sha256 `a4ec8b1a7935bdc316f338e2f03ec6967e004a532ae5520d1c7b6056a61acead`. The output is identical when run on both checkouts. |
| Command | `python3 experiments/R0_picknik_hw_reanalysis/reanalyze.py <repo>/Deprecated/semantic_validation/results/runs/hw_picknik_native_20260917T074600Z` |
| Observation boundary (from the run) | `safety=ROS-TCP Endpoint + observer only; no robot, driver, actuator, MoveIt, or Pi consumer` |

## Q1 — left/right binding on the wire

| Measure | Value |
|---|---|
| `/left_controller_odom` messages | 14,836 |
| … with `child_frame_id = right_controller_odom` | **8,005 (54 %)** |
| … with the same header stamp **and** bit-identical position as a `/right_controller_odom` message | **5,713** |
| `/right_controller_odom` messages with a wrong child frame | 0 / 14,836 |
| `/tf` transforms with child `left_controller_odom` / `right_controller_odom` | **24** / 29,648 |

**Interpretation.**

- The left topic carried the right controller's frame name and pose for most messages. `/tf`
  almost never carried the left frame.
- This matches the code path in audit A3, which is SOURCE_CONFIRMED:
  - `ROSPublishers.cs` reuses one mutable `Odometry`/`TFMessage` instance for both controllers
    (L76–90, L386–416).
  - Its comments assume synchronous serialization.
  - ROS-TCP-Connector v0.7.0 (`c27f00c6`) only queues the reference in `Publish()`
    (`RosTopicState.cs` L211–216, `TopicMessageSender.cs` L47–62). It serializes later on the sender
    thread (L109–117), after the right controller's values have overwritten the shared object.
- The right controller is published second, so it wins.

**Classification.** IMPLEMENTATION (frontend), with a consequence on **input ↔ arm binding**. The
conventional fix is to allocate per publish, or use separate message instances per controller, which
changes a few lines.

**What a ROS-side checker could see.** The corruption is detectable only for the child-frame field
(`child_frame_id ≠ topic`). A pose swap with a correct frame would be invisible: the stamps and values
are plausible.

**Not verified.**

- How the closed MoveIt Pro objective consumes `/left_controller_odom` vs `/tf`.
- Whether the left arm would actually have followed the right hand.

## Q2 — what ROS receives while the app is not focused

There were 8 unfocused intervals reported by Unity (`application_focus`). The 5 intervals that fall
inside the ROS capture show the same pattern:

| Interval (Quest clock) | Duration | Left msgs / rate | Right msgs / rate | Distinct right positions | Unity `is_tracked` (both) |
|---|---|---|---|---|---|
| …267035–274083 | 7.0 s | 427 / 60.6 Hz | 427 / 60.6 Hz | 1 | false |
| …386660–393806 | 7.1 s | 432 / 60.5 Hz | 432 / 60.5 Hz | 1 | false |
| …425304–426973 | 1.7 s | 84 | 84 | 1 | false |
| …433913–444400 | 10.5 s | 633 | 633 | 1 | false |
| …476873–485641 | 8.8 s | 529 | 529 | 1 | false |

On the left topic there are 3–4 distinct positions: frozen left and frozen right values, mixed by the
Q1 contamination.

**Interpretation.**

- During focus loss the app reported `application_focused=false` and `is_tracked=false` in Unity. The
  ROS side nevertheless received an **uninterrupted 60 Hz stream of a frozen pose with fresh publish-time
  stamps**.
- No field or gap distinguishes this from an operator holding still. A freshness check, a silence
  watchdog or a stamp-age check passes it by construction.
- This is the real-device counterpart of the evidence-delivery loss recorded in audits A1 (ALVR), A2
  (Quest2ROS2: fields absent) and A3 (PickNik: fields absent, `runInBackground: 1`).

**Classification.** METADATA. The evidence exists at the source and is dropped at the app→wire
boundary.

- The conventional remedy has S5 precedent and is PRIOR_INTERNAL, NO_METHOD_GAP: transport
  `is_tracked`/`focused`, then gate on them.
- A ROS-side "frozen-pose" heuristic would false-block a stationary operator.

**Limits.**

- One session with one operator. The focus-loss causes (menu, headset removal) were not annotated.
- The pose freezing is consistent with the earlier internal note (PICKNIK_QUESTLESS_CONVERGENCE
  §5.1–5.2). That note is not counted again here.
