# Architecture (as implemented at `horus_ros2@eca75cbf`)

Source-derived; line references in `HORUS_CODE_AUDIT.md`.

```text
 XR client A (Quest, HORUS APK, closed source)      XR client B
      │ HorusLink TCP 10000 (realtime) + 10001 (bulk), no auth, no TLS
      ▼                                                ▼
 ┌────────────────────── horus_unity_bridge (one ROS node) ───────────────────────┐
 │ HorusLinkConnectionManager: connection_id = next_connection_id_++              │
 │ MessageRouter.route_horuslink_data_frame                                       │
 │   ├─ internal topics → ControlLeaseManager                                    │
 │   │     control_lease_request {acquire|heartbeat|release, app_id, role, ...}   │
 │   │     control_topic_catalog {role:host|single, op:snapshot|upsert|remove|clear}│
 │   │     → publishes control_lease_state (transient-local)                      │
 │   ├─ authorize_command_publish(connection_id, topic)                           │
 │   │     unprotected → allow │ no lease → allow │ holder → allow │ else deny      │
 │   └─ TopicManager: one shared generic publisher per topic                      │
 │ MessageRouter.route_horuslink_service_request → ServiceManager (no lease check)│
 └────────────────────────────────────────────────────────────────────────────────┘
      │ ROS 2 topics, publisher identity = horus_unity_bridge node / its enclave
      ▼
 ┌──────── horus_backend ────────┐        ┌──── robot-side consumers ──────────────┐
 │ horus/register_robot (srv)    │        │ teleop_command_topic → e.g. cmd_vel /   │
 │ Nav2ActionAdapter per robot:  │        │   MoveIt Servo / ros2_control           │
 │  goal_pose  → async_send_goal │──────▶ │ NavigateToPose action server (Nav2)     │
 │  goal_cancel → cancel(active) │        │   goal UUID, accept/cancel/result       │
 │  single active_goal_handle    │        │ controllers (timeouts, if configured)   │
 └───────────────────────────────┘        └────────────────────────────────────────┘
```

## State held at each layer

| Layer | Authority/state object | Keyed by | Carried downstream? |
|---|---|---|---|
| XR app | operator, workspace mode, UI panel/teleop/task flags | app-internal (NOT_VERIFIED) | flags self-reported in lease JSON |
| Bridge | `RobotControlLease{holder_client_fd, app_id, role, session_id, flags, lease_version}` | robot name | **no** |
| Bridge | `protected_topic_to_robot_` | topic | no |
| ROS topic | message | topic | publisher GID = bridge |
| Backend | `active_goal_handle` (one per robot) | robot id | goal UUID to Nav2 only |
| Nav2 / action server | goal handles, states | goal UUID | — |
| Controller | last command, timeout timers | controller | — |

The three states named in the candidate question — XR authority state, bridge admission state,
ROS accepted/executing state — are held in three different places with **no shared key**
(no lease version or operator identity on commands or goals). SOURCE_CONFIRMED.
