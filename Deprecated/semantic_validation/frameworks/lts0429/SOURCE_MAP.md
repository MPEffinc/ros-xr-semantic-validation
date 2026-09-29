# LTS0429 source map and limitation

The checkout contains `Teleoperator.apk` but not its XR source. Its public host chain is
source-visible only from the UDP payload onward:

| Chain stage | Pinned source | Observed boundary |
| --- | --- | --- |
| Native XR semantic/source decision | APK only | `SOURCE_PATH_UNCONFIRMED`: input API, tracking state, source time, session semantics, and first gate cannot be audited. |
| UDP representation | `meta_quest_client/src/udp_client.cpp:42-74` | semicolon tokens `LeftHandPos/Rot`, `RightHandPos/Rot`, `HeadsetPos/Rot`; no validity, source time, sequence, or session field. |
| ROS transform/publication | `udp_client.cpp:90-179` | coordinate conversion, host `this->now()` stamp, `PoseStamped` topics and `/tf`. |
| Downstream candidate | README plus vendored `moveit_servo` | pose tracking is a separate launch; no linked original consumer execution was verified. |

The upstream README names Quest 3, ROS 2 Humble and MoveIt, but README statements do not repair
the missing native semantic source. This candidate is not counted as included until that source
or a verified trace contract is available.
