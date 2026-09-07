# PickNik production source map

Pinned source: `PickNikRobotics/meta_quest_teleoperation@bbaef0762fdb0b429b8ea12a4ca65040748b41dd`.
This is E1 `SOURCE_DATAFLOW_CONFIRMED`; Unity, Quest and ROS runtime are absent.

| Chain stage | Pinned source | Connected behavior and semantic transform |
| --- | --- | --- |
| Native XR/source binding | Input asset and serialized rig checked by `harness/picknik_deep_validation.py` | left/right position, rotation, `trackingState`, and `isTracked` actions bind to XR controller input; Quest 3/OpenXR feature is enabled. |
| First native state use | serialized controller Transform-driver linkage checked by the validator | tracking state reaches the Transform-driving layer; Unity behavior itself is not executed. |
| Serialization | `UnityProject/Assets/ROSPublishers.cs:318-340,381-417` | `Update` reads each controller Transform; Odometry/TF serializes only position/orientation. |
| Time/transport | `ROSPublishers.cs:166-186,367-416` | reconnect registration waits two seconds; header stamp is `DateTime.UtcNow`, not source sample time. |
| ROS boundary | `ROSPublishers.cs:129-164,404-416` | ROS-TCP registers and emits left/right Odometry and `/tf`. |
| Downstream | upstream README delegates clutch/control to MoveIt Pro | original consumer is external and unexecuted. |

The validator checks serialized scene/action links, not just tokens, but it remains runtime-free.
