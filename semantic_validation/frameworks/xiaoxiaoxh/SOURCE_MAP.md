# xiaoxiaoxh source map

| Stage | Connected source path | Observed behavior |
| --- | --- | --- |
| Unity source | `Unity/Assets/Scripts/HandDataCollector.cs:1-235` | `OVRInput` reads controller buttons/triggers and configured controller `Transform`s are copied each fixed update. `OVRSkeleton` fields exist but are not used in the observed send path. |
| Native semantic decision | `HandDataCollector.cs:120-223` | `message.valid` is set true unconditionally after controller collection. No `isTracked`, validity, confidence, source identity provenance, or source timestamp gate is consumed on this path. |
| Serialization/transport | `HandDataCollector.cs:44-71,121-149` | JSON holds Unity `Time.time`, `valid`, left/right poses, commands and buttons; it posts to `http://<ip>:<port>/unity`. |
| Server/control path | `real_world/teleoperation/teleop_server.py` | `/unity` buffers the message; `process_cmd` maps pose/commands and makes robot-server HTTP requests. |
| ROS boundary | `teleop.py` starts `BimanualRobotPublisher`, but that ROS publisher is parallel infrastructure; it is not evidence that Unity data reaches ROS before robot control. |
| Consumer risk | `teleop.py` constructs `BimanualFlexivServer`; `TeleopServer.send_command` addresses robot endpoints. Neither was launched. |

The connected source chain is auditable, but no runtime or robot inference is allowed.
