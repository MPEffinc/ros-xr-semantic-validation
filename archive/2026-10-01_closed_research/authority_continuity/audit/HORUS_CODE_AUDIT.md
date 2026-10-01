# HORUS Code Audit (read-only)

Audit date: 2026-09-29. Auditor: Claude Code for Hyojoong Ju.

## Pinned revisions

| Repository | Commit | Commit date | How obtained | Modified? |
|---|---|---|---|---|
| `RICE-unige/horus_ros2` | `eca75cbf559f09ff793d8993338b2f1ffed1adfd` | 2026-07-26T17:58:10+02:00 | fresh `git clone` into ignored `authority_continuity/references/upstream/horus_ros2`, `git checkout <sha>`; equals upstream `HEAD` on 2026-09-29 | no |
| `RICE-unige/horus_sdk` | `f4f00dab41910676519d545515531ec243414044` | 2026-07-26 | archived clean checkout `Deprecated/frameworks/horus_sdk` (== upstream HEAD 2026-09-29) | no |
| `RICE-unige/horus` | `819cdfdc74f1a0c2bd73946dc14897a533f68b61` | 2026-08-07 | archived clean checkout; this is the *research release channel* (docs, website, APK releases), **not** the Unity source | no |
| `RICE-unige/horus_connector` | `55933a98bb7ddf84bafcf93f1273847928e1a04e` | 2026-07-26 | fresh clone; Zenoh/WebRTC transport, contains no lease client code | no |

The HORUS MR (Unity/Quest) application source is **not public**; only APKs are released
(`v0.0.1-beta`, `v0.2.0` 2026-02-23, `v0.3.0` 2026-03-28, via `gh api repos/RICE-unige/horus/releases`).
Everything the XR client does with leases (when it acquires, whether it stops teleop or sends
cancel on lease loss, how it chooses `role`) is therefore **NOT_VERIFIED** from source.

All paths below are relative to `horus_ros2@eca75cbf`.

## A. Admission decision: `authorize_command_publish`

`horus_unity_bridge/src/control_lease_manager.cpp:125-163`

| Line(s) | Behavior | Label |
|---|---|---|
| 135-138 | Topic not in `protected_topic_to_robot_` → `return true` (allow) | SOURCE_CONFIRMED |
| 145-148 | Topic protected but **no lease for that robot** → `return true` (allow) | SOURCE_CONFIRMED |
| 150-153 | Lease holder's `client_fd` == caller → allow | SOURCE_CONFIRMED |
| 155-162 | Otherwise deny `robot_control_leased` (rate-limited denied event) | SOURCE_CONFIRMED |

Call site: `horus_unity_bridge/src/message_router.cpp:391-449` `MessageRouter::route_horuslink_data_frame`.
Internal lease/catalog topics are diverted at 404-414; every other data frame passes the check at
417-435 before `TopicManager::publish_horuslink_message` (437).

`MessageRouter::route_horuslink_service_request` (`message_router.cpp:451-483`) has **no lease
check**: ROS service calls routed through the bridge are not arbitrated. SOURCE_CONFIRMED.
Whether any robot-motion-relevant service exists in a HORUS deployment: NOT_VERIFIED.

Interpretation (HYPOTHESIS, not a vulnerability claim): the lease is a *cooperative arbitration*
mechanism that only restricts protected topics **while some client holds a lease**; it is
fail-open by construction. The README describes it as "bridge-authoritative per-robot control
lease arbitration and command-topic enforcement" (`README.md:28`) and lists it as "In progress"
with "tune TTL policies" and "extend regression coverage for repeated join/rejoin contention" as
next steps (`README.md:292`). No security goal is stated anywhere in the repository
(`grep -i 'trusted|secure|encrypt|auth'` over READMEs/docs: no security statement). AUTHOR/DOC
wording is not evidence of a security guarantee.

## B. Who defines the protected-topic list

`handle_catalog_message_locked`, `control_lease_manager.cpp:184-285`

- Input: `std_msgs/String` JSON on `/horus/multi_operator/control_topic_catalog` sent by any
  HorusLink client (`message_router.cpp:404-414`).
- `client_fd` is explicitly ignored (`(void)client_fd;`, line 188).
- Authority test is the **self-asserted** JSON field `role ∈ {"host","single"}` (194-197);
  other roles are silently ignored.
- Ops: `clear` wipes all protected topics (205-209); `snapshot` replaces all (247-249);
  `upsert` replaces one robot's topics (271-280); `remove` deletes one robot's topics (260-268).
- Default protected fields when `protected_topics` absent: `teleop_command_topic`,
  `teleop_raw_input_topic`, `teleop_head_pose_topic`, `go_to_goal_topic`, `go_to_cancel_topic`,
  `waypoint_path_topic` (232-239).
- The lease table is **not** consulted when the catalog changes; removing a robot's protected
  topics while it is leased silently makes its topics unarbitrated.

All SOURCE_CONFIRMED. Robot registration itself happens elsewhere: ROS service
`horus/register_robot` on `horus_backend` (`horus_backend/src/backend_node.cpp:174-178`, callback
313-400), i.e. any ROS-graph participant; the XR host client then derives the catalog (Unity side:
NOT_VERIFIED).

## C. Identity carried by a lease

`apply_acquire_request_locked`, `control_lease_manager.cpp:341-421`; struct in
`include/horus_unity_bridge/control_lease_manager.hpp:59-73`.

- The only identity the bridge enforces is `holder_client_fd`, which is the HorusLink
  `connection_id` — a monotonically increasing integer (`horuslink_connection_manager.cpp:536-540`),
  **not** a socket fd, so no fd-reuse aliasing. SOURCE_CONFIRMED.
- `app_id`, `role`, `session_id`, `panel_open`, `teleop_active`, `task_active`, `task_kind` are
  copied from client JSON (296-305) and never verified. SOURCE_CONFIRMED.
- Transport admission: `read_initial_hello` accepts a client if `role == UnityClient`, lane
  matches and `session_id != 0` (`horuslink_connection_manager.cpp:478-484`). No credential, token,
  or TLS in the HorusLink path; bridge binds `tcp_ip` default `0.0.0.0`, port 10000
  (`unity_bridge_node.cpp:83-85`). SOURCE_CONFIRMED.
- `horus_unity_bridge/config/bridge_config.yaml:28-30`: `# Security (for future implementation)`,
  `enable_authentication: false`, `enable_encryption: false`. No C++ source reads these keys
  (`grep -rn enable_authentication --include=*.cpp` → none): authentication is an acknowledged,
  deferred feature. SOURCE_CONFIRMED.
- The paper (P2, Sec. III-E p.4) says "Before starting teleoperation or tasking, the runtime checks
  whether the current operator is allowed to act" — i.e. an additional **client-side** check in the
  (closed-source) Unity runtime. AUTHOR_CLAIM; implementation NOT_VERIFIED.
- Realtime and bulk sockets are paired by the client-chosen `session_id`
  (`horuslink_connection_manager.cpp:400-450`). SOURCE_CONFIRMED; security relevance NOT_VERIFIED.

## D. Lease lifecycle

| Event | Code | Effect on lease | Effect on already-published / accepted work | Label |
|---|---|---|---|---|
| acquire, free robot | 356-376 | new lease, `lease_version++` | — | SOURCE_CONFIRMED |
| acquire by holder | 378-395 | refresh | — | SOURCE_CONFIRMED |
| acquire by other, holder "active" (`panel_open‖teleop_active‖task_active`, 612-615) | 397-402 | denied | — | SOURCE_CONFIRMED |
| acquire by other, holder self-reports inactive | 404-420 | **immediate reassignment** (`lease_reassigned_inactive`) | none | SOURCE_CONFIRMED |
| heartbeat, no lease exists | 436-442 | **creates** a lease (implicit acquire) | — | SOURCE_CONFIRMED |
| heartbeat by non-holder | 446-451 | denied | — | SOURCE_CONFIRMED |
| release by holder | 469-496 | lease erased | none — no cancel, no stop published | SOURCE_CONFIRMED |
| TTL expiry (`multi_operator.control_lease_ttl_ms`, default 3000, min 500; 52-54; timer 500 ms 65-67; also lazily at 113/133) | 566-583 | lease erased | none | SOURCE_CONFIRMED |
| client disconnect | `unity_bridge_node.cpp:323-336` → `message_router.cpp:578-598` → 165-182 | holder's leases erased | none; shared ROS publishers kept while other owners remain (`topic_manager.cpp:733-758`) | SOURCE_CONFIRMED |

Consequences read directly from the code (SOURCE_CONFIRMED as logic; runtime effect see §G):

1. After release/expiry/disconnect the robot is **unleased**, so by A.145-148 *every* client —
   including the previous holder — may again publish on the protected topics. Lease end does not
   revoke command admission; it removes arbitration.
2. A holder whose heartbeats stopped but whose data frames still arrive regains admission after
   expiry, and its next heartbeat recreates the lease (436-442).
3. The lease has a `lease_version` but no command carries it; published commands are not tagged
   with holder, version or session.

## E. Bridge → ROS → execution path (identity propagation)

- `TopicManager::register_publisher` (`topic_manager.cpp:146-191`): one generic publisher per topic
  shared by all clients (owner refcount at 155-158). ROS subscribers see a single publisher, the
  `horus_unity_bridge` node. Operator identity is **not** forwarded to ROS. SOURCE_CONFIRMED.
- Nav2 path (`horus_backend/src/nav2_action_adapter.cpp`):
  - subscribes `/<robot>/goal_pose` and `/<robot>/goal_cancel` (80-101); any ROS publisher on those
    topics is obeyed; no lease/identity check in the backend. SOURCE_CONFIRMED.
  - `handle_goal` (106-151): `async_send_goal` with no reference to the sender; future stored.
  - `goal_response_callback` (185-200): `active_goal_handle = goal_handle` (overwrites; single slot).
  - `handle_cancel` (153-183): cancels only `active_goal_handle`; if empty publishes
    `goal_cancelled` although nothing was cancelled (181).
  - `result_callback` (211-245): on **any** goal's result resets `active_goal_handle` (241) without
    comparing goal IDs.
  - SOURCE_CONFIRMED. HYPOTHESIS H-E1: after A's goal is preempted by B's goal, A's late result
    clears B's handle, so a later HORUS cancel does not reach B's goal and a misleading
    `goal_cancelled` status is published. (Archived PRIOR_INTERNAL runtime at this commit reported
    exactly this pattern; see §G.)
- Teleop streaming topics (`teleop_command_topic` etc.) go straight to robot-side ROS consumers;
  HORUS has no timeout/zero-command logic on lease end in the bridge (no code path found).
  Robot-side command timeouts are outside HORUS (see `EXISTING_DEFENSES.md`).
- No robot-side independent authorization check exists in HORUS code. SOURCE_CONFIRMED (absence,
  within these four repositories).

## F. Tests

`horus_unity_bridge_test/` contains no lease tests (`grep -ril lease` → none). SOURCE_CONFIRMED.

## G. Relation to archived runtime results (PRIOR_INTERNAL, same commit)

The archived August-2026 track ran this exact revision in Docker (`ros-xr-horus-nav2-jazzy:local`,
still present locally) and reported (`Deprecated/RESEARCH_CONTEXT.md:794-819`,
`Deprecated/XR2ACT_DECISIVE_RESULTS.md`): no-lease ALLOW; client-asserted `role:"host"` catalog
clear accepted; release/TTL/disconnect produced 0 cancels while the accepted Nav2 goal stayed
`EXECUTING` for 10 s; post-handoff official cancel 0/63 after A's late result, while direct
exact-UUID cancel succeeded 67/67. These are **not** results of this workspace; PHASE 6 decides
whether any of them is re-run here, and only as a baseline for defense sufficiency.

## H. Findings summary

| ID | Finding | Label |
|---|---|---|
| F1 | Protected topics are admitted when no lease exists (fail-open) | SOURCE_CONFIRMED |
| F2 | Unprotected topics and all routed ROS services bypass lease checks | SOURCE_CONFIRMED |
| F3 | Catalog authority = self-asserted `role` field; `clear`/`remove` possible for any client | SOURCE_CONFIRMED |
| F4 | Lease identity = bridge connection id; `app_id/role/session_id` unauthenticated; HorusLink has no client authentication (maintainers mark it "for future implementation") | SOURCE_CONFIRMED |
| F5 | Lease end (release/TTL/disconnect) neither cancels accepted goals nor stops streaming consumers | SOURCE_CONFIRMED (logic) |
| F6 | Inactive-holder reassignment relies on holder's self-reported activity flags | SOURCE_CONFIRMED |
| F7 | Operator identity / lease version not propagated past the bridge; backend obeys any ROS publisher | SOURCE_CONFIRMED |
| F8 | Nav2 adapter single `active_goal_handle` reset by any result; cancel may miss the current goal | SOURCE_CONFIRMED (code); runtime consequence HYPOTHESIS here, PRIOR_INTERNAL archived |
| F9 | Unity client lease behavior (acquire timing, stop-on-loss, role selection) | NOT_VERIFIED (source not public) |
| F10 | Security meaning of F1–F7 | HYPOTHESIS — evaluated in `hypotheses/THREAT_MODEL.md` |
