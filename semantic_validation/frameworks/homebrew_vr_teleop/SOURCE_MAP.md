# homebrewroboticsclub/vr-teleop source map

Classification: **Group B — positive/design control**, E1 source-dataflow confirmed.
The pinned Unity project requests `2022.3.62f2`.  No Unity editor, Quest, robot, or original
robot-control consumer was run.

| Chain step | Pinned source evidence | Semantics / transformation |
| --- | --- | --- |
| Native input | `Assets/Scripts/QuestRosPoseAndJointsPublisher.cs:397-408` | Unity XR `InputDevice` controller `isTracked`; hand `XRNodeState.TryGetPosition/Rotation` |
| Decision | `:402-414`, `:607-625` | controller presence plus hand fallback after `handsGraceSeconds`; no raw state is serialized |
| Representation | `:415-437`, `:439-549` | head and relative hand/controller poses become `geometry_msgs/PoseArray`; joints become `JointState` |
| Time | `:724-739` | estimated ROS Unix timestamp enters message header; source-time provenance is not separately encoded |
| Transport | `:743-750` and `RosbridgeImageSubscriber.TryPublish` | custom rosbridge JSON over WebSocketSharp |
| ROS boundary | configured `/quest/poses`, `/quest/joints` | no included original robot-control subscriber was found |

Scene/config linkage remains a Unity-editor verification item.  The design is useful precisely
because it makes a source-side validity/fallback decision; it must not be equated to OpenXR,
WebXR, or Meta raw tracking semantics.
