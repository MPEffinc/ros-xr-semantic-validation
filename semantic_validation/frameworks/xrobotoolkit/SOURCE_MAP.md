# XRoboToolkit source map

The repository's native PicoXR semantics are opaque behind the external `PXREARobotSDK` service.
It nevertheless contains a source-auditable wire and downstream path:

| Stage | Source | Observed behavior |
| --- | --- | --- |
| Service callback | `ros2/picoxr/src/publisher.cpp` | `PXREADeviceStateJson` parses external JSON. |
| Custom message | `ros2/xr_msgs/msg/{Custom,Head,Controller}.msg` | `timestamp_ns`, head/controller pose and integer `status` are represented. |
| Publisher treatment | `publisher.cpp` | source timestamp and supplied head status copy through; controller status is set to constant `3` when present, so it is not preserved from the service. |
| Control example | `examples/arx_ros2/src/main_v1.cpp`, `xr_to_arx.cpp` | subscribes `/xr_pose`, transforms poses, and publishes ARX `PosCmd` periodically. |
| Status use | `xr_to_arx.cpp` | control conversion/activation uses trigger and pose, not head/controller `status` or timestamp freshness. |

This establishes no claim about what a PicoXR status value means.
