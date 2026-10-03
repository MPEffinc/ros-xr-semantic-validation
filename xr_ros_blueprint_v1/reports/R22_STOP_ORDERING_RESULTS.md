# R22 — Stop ordering at the controller boundary: results (R18; 12/12 valid, 2026-10-04)

| | |
|---|---|
| Protocol | R18, frozen e91af93; executed from a `git archive` snapshot, hash-verified per trial |
| Raw data | `experiments/M3_ordering/raw/` (ignored, 48 MB, 354 files incl. pre-flight); sha256 in `results/ORD_RAW_SHA256.txt`; measures in `results/ord_trials.json` |
| Level | real UR5e app path, Gazebo, I3 runtime deactivation; conditional check of a **writer/ordering premise** (small n) |
| Validity | 12/12 valid on the first attempt; no masking; status-4 present in 2 CUR trials (as in R12, not masking) |

## Results (3 trials per cell)

| Condition | Measure | CUR (pause + repeated direct hold) | MUX (exclusive writer through `topic_tools mux`) |
|---|---|---|---|
| NORMAL | P_stop | 3/3 (travel after onset+0.1 s ≤ 0.19 mm) | 3/3 (≤ 0.10 mm) |
| NORMAL | Servo multi-point trajectories on the controller after the first hold | 0/3 | 0/3 |
| LATE | P_stop | 3/3 (≤ 0.04 mm) | 3/3 (≤ 0.26 mm) |
| LATE | injected pre-stop trajectory **reached the controller topic** | **3/3** (at +151–152 ms) | **0/3** |
| LATE | **last trajectory the controller received** in the window | **the injected 14–15-point trajectory (3/3)**, i.e. the hold was replaced | a 1-point hold (+105–106 ms) (3/3) |
| LATE | EE travel after the injection | 0.0 mm (3/3) | 0.0–0.08 mm |
| all | pause ack after onset | 10–93 ms | 29–102 ms; mux select ack 5–11 ms |

**Other observations:**

- The "Servo trajectory after the first hold" count of 1 in the CUR LATE trials is the injected trajectory itself. No
  natural Servo output followed the first hold in any of the 12 trials.
- The Servo pause race (R18 §1) was not observed in this sample. The code path still allows it.

## Reading (per the fixed rule)

- **CUR depends on a writer/ordering premise that does not hold structurally.**
  - A delayed pre-stop trajectory on the controller topic **displaced the hold in 3/3 trials**. The controller's
    final command was a multi-point motion trajectory, not a hold, and none of the CUR re-holds (all ≤ +0.1 s)
    covered it.
  - The pass in P_stop came only from the **content** of that trajectory: it was built just before the stop, so its
    target was within the stopped pose. **The physical effect was 0 mm here.** A late message with a farther target
    (larger latency, faster motion) would move the arm. That is not measured, so it is stated as a structural risk,
    not as an observed harm.
- **MUX removes the premise for writers that go through the boundary.**
  - With the mux as the only writer, the late trajectory on the Servo input never reached the controller (0/3).
    The hold was the last command in 3/3, and normal stopping was unchanged.
  - Cost:
    - one existing node (`topic_tools mux`);
    - one Servo output remap;
    - one service call at stop (select ack 5–11 ms).
- **Not covered:**
  - a process that publishes directly on the controller topic (a permission premise, e.g. SROS2 access control; not
    tested);
  - the action interface;
  - re-arm (switching the mux back);
  - queue depth or DDS behaviour beyond this sample. The ack was **not** assumed to drain queues.
- **Classification.** The stop ordering at the final boundary is an **implementation premise solved by an existing
  pattern** (exclusive writer / mux). It is not a method gap.
