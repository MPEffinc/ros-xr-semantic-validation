# Upstream pins

Checkouts are read-only. They are reused from the primary checkout
(`/home/cclab/ros_xr/Deprecated/semantic_validation/targets/`) unless noted. New clones go to
`references/upstream/`, which is ignored. Each was verified clean (`git status --porcelain` empty) when first used.

| Target | URL | Commit | Local path | Audit role |
|---|---|---|---|---|
| OpenVR UR5e (Jazzy) | https://github.com/mrutyunjaykalyani/teleoperation-of-a-UR5e-robot-in-Gazebo-using-Meta-Quest-3-via-ROS2-bridge-jazzy-.git | `170dad582d624f536359a3192a7f829669c2b031` | `targets/openvr_ur5e_jazzy` | primary audit 1 |
| Quest2ROS2 | https://github.com/Taokt/Quest2ROS2.git | `07aaf65149c9e29103f1fc61deb466cef8a55cef` | `targets/quest2ros2` | primary audit 2 |
| PickNik meta_quest_teleoperation | https://github.com/PickNikRobotics/meta_quest_teleoperation.git | `bbaef0762fdb0b429b8ea12a4ca65040748b41dd` | `targets/meta_quest_teleoperation` | secondary |
| Spes teleop | https://github.com/SpesRobotics/teleop.git | `c5d808155a87b584d6147a5943d4b87c34c92db0` | `targets/spes_teleop` | secondary |
| Docker_Teleop | https://github.com/Noah727/Docker_Teleop.git | `64cbdde88bc52c6a80d37f994752e50f95ba537e` | `targets/docker_teleop` | secondary |
| OpenArmX teleop VR | https://github.com/openarmx/openarmx_teleop_vr.git | `a3da7411b3d6ecaa7f94df859e07fb642aec859b` | `targets/openarmx_teleop_vr` | secondary |

Each pin is checked against the remote HEAD when its audit runs, and both values are recorded in the audit file.
