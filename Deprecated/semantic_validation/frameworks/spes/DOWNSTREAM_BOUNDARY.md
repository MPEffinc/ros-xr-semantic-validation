# Spes downstream boundary

| Boundary | Observable | Claim limit |
| --- | --- | --- |
| `Teleop.__update` → callback | callback/target update | original server software handoff, not ROS or robot control |
| `teleop.ros2` → `target_frame` and `/tf` | source-visible optional publisher | requires ROS 2; no current actual ROS run |
| Original robot consumer / driver | none | `NATIVE_CONSUMER_UNAVAILABLE` in this session |
| Pi sink | not connected | future use establishes only `PI_RECEIVED` |

No physical driver, actuator, or robot is authorized by this package.
