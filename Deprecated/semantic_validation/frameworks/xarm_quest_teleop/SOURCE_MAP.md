# RuiyuWANG/xarm_quest_teleop source map

Classification: **Group D — excluded from independent principal population**.  This historical
default branch is ROS 1 and consumes Quest2ROS messages, so it does not provide independent native
input lineage.  It also has a direct xArm service boundary; no launcher, service, or robot was run.

| Chain step | Pinned source evidence | Boundary |
| --- | --- | --- |
| XR input boundary | `src/io/quest2.py:1-90` | subscribes to `quest2ros` `PoseStamped`, `Twist`, and input messages; raw Quest state is upstream |
| Synchronization/control | `src/teleop/quest_xarm_teleop_sync.py:86-117`, `:417-512` | ApproximateTimeSynchronizer, deadman gate, reference latch, filter and step limiting |
| Robot boundary | `src/robots/xarm.py:111`, `:523-545` | `/xarm/move_servo_cart` ROS service; direct physical path |

The no-command branch on deadman release is a control gate, but says nothing about raw Quest
tracking validity.  An inert ROS 1 service that exactly matches `xarm_msgs/Move` would be required
before a safe runtime adaptation; this is intentionally not introduced in the current population.
