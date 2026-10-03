# R18 — Stop ordering at the controller boundary (protocol; small conditional check; frozen before formal runs)

## 1. Code and trace facts (before running)

**MoveIt Servo 2.12.4 (`servo_node.cpp`).** The pause flag can lag the ack by one trajectory.

- `pauseServo()` (L147–178) takes `lock_` and sets `servo_paused_`.
- The servo loop checks `servo_paused_` **without** the lock (L348–353), then takes `lock_` (L356) and computes and
  publishes a trajectory.
- So an iteration that passed the check before the pause can block on the lock and **publish one more trajectory after
  the pause callback returns**, at or after the acknowledgement. The ack does not mean "no further Servo output".
- Messages already handed to DDS can still be delivered after the ack.

**JTC 4.42.1 (`topic_callback` L1385–1398).** Every valid topic trajectory replaces the current one, including a
hold (`rt_is_holding_ = false`). Any writer on `/ur5_arm_controller/joint_trajectory` can override a stop.

**R12 traces (HOLD arm).**

- The first hold went out **before** the pause ack (ack at +58…+119 ms).
- In one of the HOLD trials, one Servo trajectory reached the controller after the first hold, and the re-holds
  covered it.

That is the sampled normal case only. It is not a writer or queue guarantee.

## 2. Arms (same evidence, trigger latch, clock, app and Servo configuration)

| Arm | Controller-boundary design |
|---|---|
| CUR | R10/R12 HOLD: `pause_servo(true)` + hold published **directly** on the controller topic (at once, at the pause ack, +0.1 s) |
| MUX | **existing multiplexer as the exclusive writer**: `topic_tools mux` (ros-jazzy-topic-tools 1.3.4, image `m3-ordering-mux:v1`) is the only writer to the controller topic. Its inputs are `/m3/servo_out` (Servo output **remapped**, `harness/servo_launch_remap.py`) and `/m3/hold_in`. On trigger: `select(/m3/hold_in)` + `pause_servo(true)`; holds are published on `/m3/hold_in` (at once, at the select ack, +0.1 s). |

**Premise of MUX.** Every legitimate writer goes through the mux. A process with permission to publish directly on
the controller topic **bypasses** it. That is a separate permission premise, not tested and not defended here (no
claim against malicious publishers).

## 3. Conditions

| ID | Construction |
|---|---|
| NORMAL | R10 I3 (runtime deactivation mid-motion at 6.0 s) |
| LATE | I3 plus a **late pre-stop trajectory**: the last Servo trajectory published before 6.0 s is re-published unchanged once at onset + 150 ms on the path Servo uses (CUR: the controller topic; MUX: `/m3/servo_out`). This models a delayed in-flight pre-stop message (`harness/late_injector.py`). |

2 arms × 2 × 3 = **12 formal trials** (`schedule_ord.csv`).

## 4. Measures

- R03 P_stop (S1 ≤ 5 mm after onset + 0.1 s; S2 ≤ 0.01 rad/s after onset + 0.3 s);
- EE travel after onset and after the injection;
- **whether the injected trajectory reached the controller topic** (observer on the controller topic, matched by
  stamp);
- Servo multi-point trajectories on the controller topic after the first hold;
- the last trajectory the controller received in the window;
- pause and select ack times.

Validity: R03 rules.

## 5. Reading (fixed)

- If CUR lets the late trajectory reach the controller and move the arm while MUX does not, then the current pass
  depends on a writer/queue assumption, and **exclusive writing at the final boundary (an existing pattern)**
  removes it **for writers that go through the boundary**.
- If neither moves, the late message is not harmful in this configuration; report why.
- **Out of scope:** no action-path conversion and no general stop framework.
