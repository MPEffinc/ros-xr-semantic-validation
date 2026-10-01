# Threat Model

Derived only from boundaries that exist in the audited code (`../systems/TRUST_BOUNDARIES.md`). Default
exclusions (from the brief): no root, no control of the whole ROS graph, no simultaneous control of all
sensors, no free edit of the whole dataset, no edit of training/evaluation code or results.

## 1. Intended data meaning (fixed before any attacker is considered)

| Path | `action` means | `observation.state` / `states` means | Time base |
|---|---|---|---|
| P1 LeRobot | joint target decided at step *t* before bus clipping (example) / teleop-processed action (`lerobot-record`) | measured joints read just before step *t* | synthetic `frame_index/fps` |
| P2 Isaac Lab | environment action (EE pose + gripper) before scale/clip | simulator state after the step | step index |
| P4 tidybot_ros | commanded EE/base/gripper target (same message the controller consumes) | latest TF poses + finger joint, latest images | 10 Hz recorder wall timer; HDF5 index only |

A mismatch between command and later state is **expected** (controller lag, clipping, IK error, gravity).
A commanded-action label is the documented definition, not an anomaly. These are not treated as attacks.

## 2. Candidate attackers vs. what exists

| Candidate from the brief | Exists in audited code? | Minimum real authority | Classification |
|---|---|---|---|
| Limited component supplying XR input / tracking | **yes** (TB1: XR client → CloudXR; TB1b WebXR replay; TB7 phone SocketIO) | operator-level XR input on the paired client | its dataset influence equals its robot influence → produces a *genuine* demonstration of chosen behaviour (= published "data provider" poisoning). TB7 additionally has no authentication (UNAUTH) |
| Component influencing part of retargeting | only in-process (TB3) | full process authority | NONE — not a limited boundary |
| Component publishing only specific ROS messages | ROS 2 graph exists (P4) but **no SROS2** → any participant has full graph authority (UNAUTH, TB8); ROS 1 for P3 (TB9) | any DDS participant / ROS 1 node | UNAUTH (generic, prior internal evidence). A per-topic LIMITED writer exists only in a hypothetical SROS2 deployment (TB8′) |
| Component changing some recorder fields | no — recorders are single processes (P1, P2, P3) or a single node (P4) | — | none found |
| Limited write access to stored data | only whole-file / whole-repo writers (disk, Hub, HDF5 tools) | FULL_WRITE | excluded by default; equals the published poisoning threat model |

## 3. Problem classes observed (source level)

| Class | Observed | Examples (SOURCE_CONFIRMED, see SOURCE_AUDIT) |
|---|---|---|
| A. DATA QUALITY | **yes** | D1 LeRobot label is pre-clip / pre-robot-processor (`record.py:160`, `lerobot_record.py:359-367`); D2 synthetic timestamps, cross-stream skew not stored (`dataset_writer.py:224`); D3 hold frames unflagged (LeRobot), paused steps dropped without marker (Isaac Lab `record_demos.py:719-722`); D4 `GRIP_IS_VALID` not consulted (LeRobot example); D5 stale camera frames recorded as current (tidybot, LeRobot ≤500 ms); D6 XRoboToolkit `qpos_des` read without lock; D7 Isaac Lab merge keeps first file's `env_args` only |
| B. INTEGRITY VIOLATION across a real limited boundary | **none found** | only candidate: TF broadcaster under hypothetical SROS2 (TB8′), DERIVED_HYPOTHESIS |
| C. LEARNING IMPACT | not tested | prior art shows impact for FULL_WRITE edits (SilentDrift, DropVLA, !Imperio, State Backdoor, 2609.26868) |
| D. SECURITY / SAFETY IMPACT | not tested | — |

A-class findings are not escalated to security claims.

## 4. The single LIMITED candidate (TB8′) and why it is not pursued experimentally

- **Mechanism (hypothesis):** a node granted `/tf` publish permission for its own frames could broadcast
  transforms for `world→base` or `arm_base_link→bracelet_link`, which the tidybot recorder samples as
  observations (`synchronized_recorder.cpp:562-590`); ROS 2 / DDS permissions are per topic, not per frame.
- **Why it does not satisfy the phase gate:**
  1. the limited boundary exists only if we deploy SROS2 ourselves; upstream neither ships nor documents it
     (brief rule: do not invent an authority boundary);
  2. it involves no XR data and is identical for any teleop source (RQ4 → not XR-specific);
  3. it is a known granularity property of topic-level access control, and the recorder can close it with an
     existing check — recompute the recorded poses from `/joint_states` (which the TF writer does not
     control) or record joint states directly;
  4. so even a positive result would be IMPLEMENTATION_GAP_ONLY / NO_METHOD_GAP and would not support an
     XR-demonstration-integrity method.
- It is recorded as an OPEN, untested ROS 2 observation, not as a finding.
