# Problem Definition

## Candidate problem (as posed)

Multiple XR operators control one ROS robot through a shared bridge. Authority changes (release,
expiry, reassignment, reconnection). Are (i) XR authority state, (ii) bridge admission state and
(iii) ROS-accepted / executing state consistent?

## What the evidence so far reduces it to

1. In HORUS the three states live in three places with no shared key
   (`../audit/ARCHITECTURE.md`): the bridge lease (`connection_id`, `lease_version`), the backend's
   single `active_goal_handle`, and Nav2's goal UUIDs. Nothing on a command or goal names the lease
   epoch under which it was admitted. SOURCE_CONFIRMED.
2. Adversarial variants reduce to "no authentication" (THREAT_MODEL Q-SEC) — known, acknowledged.
3. The remaining question is Q-CONS: after an authority change, is accepted work stopped or kept
   according to a stated policy, and does the next holder retain stop authority (PG2–PG6)?

## Structural identity with a known problem

Q-CONS is an instance of the *stale lock-holder request* problem of distributed locking:

> "a process holding a lock L may issue a request R, but then fail. Another process may acquire L and
> perform some action before R arrives at its destination. If R later arrives, it may be acted on
> without the protection of L" — Burrows, *The Chubby Lock Service for Loosely-Coupled Distributed
> Systems*, OSDI 2006, §2.4, PDF p.4 (FULL TEXT checked ✔,
> https://www.usenix.org/legacy/event/osdi06/tech/full_papers/burrows/burrows.pdf).

Chubby's remedy is the **sequencer** (lock name, mode, *lock generation number*) passed with each
protected request and checked by the recipient, plus a *lock-delay* after holder failure (same §2.4).
Mapped to ROS: lease = lock, `lease_version` = generation number, Nav2 goal / teleop command = protected
request, backend/controller = recipient server. The robot-specific additions are (a) requests that are
*long-running* after acceptance (ROS 2 actions), so terminating them on epoch change needs the Action
cancel primitive (P4), and (b) streaming commands whose safe termination is a controller timeout (P8,
ros2_control). Each ingredient pre-exists.

## Hypotheses to test (PHASE 6)

- H1 (stock HORUS): PG3-stop is violated for release, TTL and disconnect (no cancel is issued).
- H2 (stock HORUS): PG2 is violated after a handoff because the adapter's single handle is cleared by the
  previous goal's ABORTED result (Nav2 preemption aborts the old goal, N1).
- H3 (stock HORUS): PG4 and PG5 are violated (fail-open admission; self-asserted catalog authority).
- H4 (existing primitives, correctly combined = B1): PG1–PG5 hold.
- H5 (B1): PG6 may be violated when the next holder's goal and the lease-end cancel race on different
  topics; closing it needs epoch tagging (Chubby-style sequencer) — also an existing pattern.

If H4 holds and H5 is either false or fixed by a sequencer, the verdict ceiling is
**IMPLEMENTATION_GAP_ONLY** (RESEARCH_PLAN K1/K2).
