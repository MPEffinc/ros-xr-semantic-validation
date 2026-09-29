# HRI-EU/reachy-vr-quest source map

Classification: **Group A — independent principal source-audited direct-robot architecture**,
E1 only.  It is not a ROS stack and therefore expands the comparison family rather than the ROS
population.  No daemon, robot, Unity editor, APK, Quest, or WebSocket connection was started.

| Chain step | Pinned source evidence | Semantics / transformation |
| --- | --- | --- |
| Native XR source | `Assets/Scripts/Runtime/Tracking/MetaBodySkeletonProvider.cs:4, 87-108, 145-154` | Meta Movement `RetargetingBodyDataSource.IsPoseValid()` is delayed by `validBodyTrackingDelay` into `_poseStable` |
| Native decision | `ReachyHeadCommandPublisher.cs:89-103, 136-145` | payload build requires an active, ready skeleton provider and required transforms; failure returns false before send |
| Control representation | `ReachyHeadCommandBuilder.cs`, `ReachyDaemonTargetAdapter.cs:15-47` | head matrix, antennas, body yaw; yaw becomes radians for daemon schema |
| Transport | `Transport/ReachyDaemonTargetWebSocketClient.cs:137-148, 244-350` | asynchronous direct WebSocket queue to `/api/move/ws/set_target` |
| Real downstream boundary | `Assets/Config/ReachyTeleopConfig.asset:15-22`, scene runtime linkage | Reachy daemon target endpoint; it is potentially robot-facing |

An inert WebSocket server may be used only after its protocol acceptance semantics are documented
and its endpoint cannot forward to a daemon.  Until then the target remains `SOURCE_ONLY`, not
runtime-ready.  The project requests Unity `6000.3.9f1`, distinct from PickNik's `6000.1.6f1`.
