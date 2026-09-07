# Spes production source map

Pinned source: `SpesRobotics/teleop@c5d808155a87b584d6147a5943d4b87c34c92db0`.
This is an E1 connected source map, not a new native-hardware result.

| Chain stage | Pinned source | Connected behavior and semantic transform |
| --- | --- | --- |
| Native XR API | `teleop/index.html:264-278,283-388` | `XRFrame.getPose(inputSource.targetRaySpace, referenceSpace)` supplies transform; `getViewerPose` is selected when the controller pose is null. Right tracked-pointer detection uses `inputSource.handedness`. |
| First native decision | `teleop/index.html:334-355` | Controller transform or viewer fallback is selected before packet construction. Raw tracking status is not serialized. |
| Serialization | `teleop/index.html:355-380` | position/orientation, `move`, gripper, scale, buttons, device/message are in `state`; source ID, source time, sequence and tracking state are absent. |
| Transport/server | `teleop/index.html:241-250`; `teleop/__init__.py:220-278` | WSS sends JSON. `Teleop.__update` gates on `move`, applies transform conversion/jump protection, then notifies callbacks. |
| ROS boundary | `teleop/ros2/__main__.py:76-148` | optional adapter publishes `PoseStamped target_frame` and `/tf`; it is not run because current host lacks `ros2`/`rclpy`. |
| Downstream | `teleop/__init__.py:204-218` | original server callback observes accepted target; no physical robot interface is launched. |

Prior Quest evidence is bounded at actual Quest → Spes production server callback, below E5
because that run did not include actual ROS publication/reception.
