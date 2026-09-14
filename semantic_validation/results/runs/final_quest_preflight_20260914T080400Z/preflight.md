# Final Quest preflight

- Run: `final_quest_preflight_20260914T080400Z`
- Overall: **`BLOCKED_DEPENDENCY`**
- Quest used: `false`
- Physical driver used: `false`

| Check | Status | Detail |
| --- | --- | --- |
| `outputs.writable` | `PASS` | result output directory is writable |
| `repo_pin.spes` | `PASS` | pinned checkout is present and clean |
| `repo_pin.picknik` | `PASS` | pinned checkout is present and clean |
| `repo_pin.docker_teleop` | `PASS` | pinned checkout is present and clean |
| `repo_pin.openvr_ur5e` | `PASS` | pinned checkout is present and clean |
| `repo_pin.quest2ros2` | `PASS` | pinned checkout is present and clean |
| `repo_pin.openarmx` | `PASS` | pinned checkout is present and clean |
| `docker.daemon` | `PASS` | Docker daemon is usable |
| `docker.image.humble_testbed` | `PASS` | image available: ros-xr-humble:local |
| `docker.image.docker_teleop` | `PASS` | image available: docker-teleop-humble:local |
| `docker.image.jazzy_base` | `PASS` | image available: ros:jazzy-ros-base |
| `docker.humble_compose` | `PASS` | Humble compose configuration validates |
| `ros_env.humble` | `PASS` | isolated ROS 2 humble probe passed |
| `ros_env.jazzy` | `PASS` | isolated ROS 2 jazzy probe passed |
| `pi.semantic_robot_sink` | `PASS` | Pi online; installed observation-only sink executable and log directory found |
| `pi.sink_source` | `PASS` | in-repo sink source is present |
| `orchestration.required_files` | `PASS` | required launch/logger/collect/stop files are present |
| `safety.launch_selection` | `PASS` | preflight selected no runtime launch and executed no physical driver |
| `unity.editor_6000.1.6f1` | `PASS` | Unity editor is installed |
| `unity.android_modules` | `PASS` | AndroidPlayer, SDK, NDK, and OpenJDK are installed |
| `unity.license` | `BLOCKED_USER_ACTION` | Unity editor requires operator license entitlement/login |
| `app.picknik_apk` | `BLOCKED_USER_ACTION` | PickNik validation APK must be built after Unity license activation |
| `app.spes_web_frontend` | `PASS` | Spes native WebXR frontend and side-band instrumentation sources are present |
| `hardware.quest_connection` | `BLOCKED_HARDWARE_NOT_CONNECTED` | Quest is intentionally not connected |
| `app.docker_teleop.editor_6000.2.10f1` | `BLOCKED_USER_ACTION` | install the project-pinned Unity 6000.2.10f1 editor |
| `app.docker_teleop.command_line_build` | `PASS` | repository CommandLineQuestBuild.BuildQuestApk entry point is present |
| `app.docker_teleop.apk` | `PASS` | Docker_Teleop APK exists |
| `app.quest2ros2.frontend_source` | `BLOCKED_DEPENDENCY` | pinned repository has no Quest frontend source; external black-box app is required |
| `app.quest2ros2.install_procedure` | `PASS` | README documents the external Quest2ROS distribution/configuration path |
| `app.quest2ros2.artifact` | `BLOCKED_USER_ACTION` | operator must obtain/install the external Quest2ROS app before the hardware session |
| `app.openvr_ur5e.alvr` | `BLOCKED_DEPENDENCY` | install the external ALVR runtime |
| `app.openvr_ur5e.steamvr` | `BLOCKED_DEPENDENCY` | install/configure the external SteamVR/OpenVR runtime |
| `app.reachy.source` | `PASS` | Reachy Unity project and enabled application scene are present |
| `app.reachy.editor_6000.3.9f1` | `BLOCKED_USER_ACTION` | install the project-pinned Unity 6000.3.9f1 editor |
| `app.reachy.apk` | `BLOCKED_USER_ACTION` | build or obtain the documented Reachy APK after satisfying editor/license/package requirements |
| `app.spes.wheel` | `PASS` | built Spes wheel contains the native WebXR assets |
| `app.spes.native_web_assets` | `PASS` | pinned Spes source contains both native WebXR assets |

`BLOCKED_HARDWARE_NOT_CONNECTED` is expected during this Quest-free run. `PI_RECEIVED` remains observation-only and does not establish native consumer or actuator acceptance.
