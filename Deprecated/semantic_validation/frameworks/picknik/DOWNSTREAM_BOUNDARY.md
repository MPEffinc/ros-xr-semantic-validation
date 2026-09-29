# PickNik downstream boundary

| Boundary | Status | Claim limit |
| --- | --- | --- |
| Unity ROS-TCP → `ros_tcp_endpoint` | source mapped; runtime blocked | no actual ROS publication yet |
| Odometry/TF → Pi observer | observer exists | future result can establish only `PI_RECEIVED` |
| MoveIt Pro clutch Objective | external component | `NATIVE_CONSUMER_UNAVAILABLE` here |
| actuator pre-write | not prepared | no actuator/robot action permitted |

The robot-free sideband/Pi design in `results/PICKNIK_HW_READY.md` remains unchanged.
