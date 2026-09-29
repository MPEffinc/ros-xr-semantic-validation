# Existing Defenses and Their Sufficiency

Each defense is evaluated at its documented, intended configuration (no deliberately weakened control),
then in combination. PG = protection goals in `../hypotheses/THREAT_MODEL.md`.

| Defense | What it guarantees (source) | PG it can cover | What it cannot cover alone |
|---|---|---|---|
| D-L HORUS lease + bridge authorization (`horus_ros2@eca75cbf`) | Blocks protected-topic publishes from non-holders **while a lease exists** (audit §A) | PG1 (partially) | PG2 (handle bug), PG3 (no cancel), PG4 (fail-open), PG5 (self-asserted host) |
| D-R Robot-side final authority check | **Does not exist** in HORUS (audit §E). Nav2/JTC accept any client's goals and cancels (N1, C1) | — | — |
| D-A ROS 2 Action cancel (P4, rcl/rclcpp jazzy) | Terminates a named goal (UUID) if the server accepts; Nav2 and JTC always accept (N1, C1) | PG2, PG3-stop if **someone calls it** | not invoked on lease end; no ownership, no auto-cancel on client death |
| D-S MoveIt Servo `incoming_command_timeout` 0.1 s; diff_drive `cmd_vel_timeout` 0.5 s; JTC `cmd_timeout` (default off) | Halts streaming motion when fresh commands stop arriving (header-stamp based) | PG3-stop for **streaming** teleop, once admission stops | nothing for Nav2 goals; useless while the bridge still admits a stale stream (PG4 violated) |
| D-SROS2 enclaves / DDS-Security (P3) | Authenticates the bridge process and restricts which participants may publish/subscribe/call | Blocks X6 (direct ROS bypass) | All operators share the bridge's single participant ⇒ no operator distinction, no epoch; permissions static (P3, P5) |
| D-ABAC (P7, Salimi et al.) | Per-message attribute check + exclusive acquire/release lock | PG1, PG4 (future messages) | in-flight work on revocation untreated (preprint) |
| D-Auth connection-time auth (rosauth R3; HORUS "future implementation") | Only credentialed clients connect | removes X5 | not consistency |
| D-Seq Chubby sequencer / lock-delay (Burrows 2006 §2.4) | Recipient rejects requests carrying a stale lock generation | PG6, PG3-cont | requires the recipient (backend) to check it |
| D-RTA Runtime assurance (SOTER, R6) | Switches to a certified safe controller on safety-envelope violation | physical safety | not authority; switches controllers not operators (abstract) |

## Combination analysis (argument, to be tested in PHASE 6)

Baseline **B1 — existing primitives, correctly combined**, implemented as a *test-only* patch
(`../experiments/baselines/b1_existing_primitives.patch`, applied to a copy inside the container, never to
upstream):

- (a) generic **fail-closed** admission: protected topic without a lease ⇒ deny (covers PG4, and makes
  D-S effective for streams);
- (b) lease end ⇒ invoke HORUS's **own** cancel path for that robot (D-A through the existing
  `goal_cancel` topic) (PG3-stop);
- (c) Nav2 adapter correlates results by **goal UUID** before clearing the active handle (D-A primitive)
  (PG2);
- (d) catalog authority bound to the **first host connection** until it disconnects; others ignored (PG5
  stand-in for D-Auth).

Not included in B1 and why:
- SROS2: all tested commands originate from the same bridge participant, so enabling it changes no
  outcome of cases C1–C7 (information-equivalent). It would only block X6, which the cases do not use.
  Recorded as NOT_RUN with this reason, not as "ineffective".
- Servo/controller timeouts: the loopback plant has no Servo/diff_drive controller; streaming effect is
  measured at admission (C7). Controller behavior is SOURCE_CONFIRMED (P8, C1) only.
- D-Seq (epoch tag on goals): held back deliberately — it is the remedy for H5; tested only if C5F shows
  cross-epoch interference.

If B1 satisfies PG1–PG5 and PG6 either holds or is closed by D-Seq, every failure of stock HORUS is
repaired by standard mechanisms ⇒ no method gap.
