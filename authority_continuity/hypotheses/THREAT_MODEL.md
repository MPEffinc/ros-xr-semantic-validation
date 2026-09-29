# Threat Model

Grounded only in identities and paths that exist in `horus_ros2@eca75cbf` (see
`../audit/HORUS_CODE_AUDIT.md`, `../audit/TRUST_BOUNDARIES.md`). RESEARCH_PLAN K4 applies: no actor is
given an identity, credential or path the implementation does not have.

## System assets

A1 robot motion (Nav2 goals, streaming teleop) · A2 the exclusivity of control while an operator holds a
lease · A3 the current holder's ability to stop the robot · A4 the protected-interface catalog.

## Actors that actually exist

| Actor | What the implementation lets it do (SOURCE_CONFIRMED) | Adversarial? |
|---|---|---|
| X1 Current lease holder (connection C_h) | publish on protected topics of its robot; heartbeat; release; publish goal / cancel via backend | benign by assumption (cooperative operator) |
| X2 Other connected operator | publish on unprotected topics; on protected topics only when **no** lease exists; acquire when holder inactive (self-reported flags); send catalog with self-asserted `role:"host"` | benign or buggy in HORUS's intended use |
| X3 Previous holder after release / TTL expiry | same as X2; its client UI may still be streaming or send stale goals | typically benign-but-stale |
| X4 Reconnected session | new `connection_id`; no continuity with the old lease; same as X2 until it re-acquires | benign |
| X5 Any network peer reaching TCP 10000/10001 | **identical to X2** — HorusLink has no authentication (`enable_authentication: false`, "for future implementation") | could be adversarial |
| X6 Any ROS-graph participant | publish directly on `/<robot>/goal_pose`, `/goal_cancel`, cancel any Nav2 goal; call `horus/register_robot` | outside HORUS; SROS2 can restrict |

Not existing, therefore **not modeled**: an *authenticated* XR operator with a verifiable identity and
role; per-operator credentials; a robot-side authority check; a lease token carried by commands.
Consequently an "authenticated insider abuses authority" attack cannot be instantiated: any such attack
is already available to X5 without authentication. That is the generic, maintainer-acknowledged
"unauthenticated bridge" problem (same class as rosbridge/ROS-TCP-Endpoint deployments) and is **not a
research gap** (RESEARCH_PLAN K1/K2).

## Two distinct questions the candidate hypothesis mixes

- **Q-SEC (adversarial):** Can a non-holder obtain robot motion against the lease? In the implemented
  system: yes, trivially (X5 + catalog `clear`, service routes, direct ROS), because there is no
  authentication. Answer is known; remedy is standard authentication + SROS2 + fail-closed defaults.
- **Q-CONS (consistency among cooperative operators, safety-relevant):** When authority moves
  (release, expiry, reassignment, disconnect), do bridge admission and ROS execution follow the policy
  the lease is supposed to implement? This is the only form of the candidate question that is
  meaningful in HORUS's own trust model (P2: "all participants have equal priority").

## Protection goals (fixed before PHASE 6)

Continuation of accepted work after a lease ends is **not** by itself a violation (RESEARCH_PLAN K5).
We therefore state two alternative policies and test against each.

| ID | Goal | Applies under |
|---|---|---|
| PG1 | Exclusivity: while X1 holds a lease, protected-interface commands from any other connection do not reach ROS. | both policies |
| PG2 | Stop authority: the **current** holder's HORUS cancel terminates the robot's current Nav2 goal (bound 3 s). | both policies |
| PG3-stop | Under a *must-stop* policy, a goal accepted under a lease is terminated within 1 s after that lease ends (release / TTL / disconnect / reassignment). | must-stop deployments |
| PG3-cont | Under a *may-continue* policy, the continuing goal must remain stoppable by the next holder (⇒ PG2) and must not be cancelled on behalf of a *different* lease. | may-continue deployments |
| PG4 | No stale admission: a connection without a lease cannot get new protected commands into ROS. | only if the lease is meant to be mandatory (P2 says the runtime checks before acting; the bridge does not) |
| PG5 | Catalog integrity: while a robot is leased, a non-holder connection cannot remove its protected interfaces. | both policies |
| PG6 | No cross-epoch interference: a lease-end action for lease *k* never terminates work started under lease *k+1*. | both policies |

HORUS documentation defines neither PG3-stop nor PG3-cont; which one HORUS intends is NOT_VERIFIED.
