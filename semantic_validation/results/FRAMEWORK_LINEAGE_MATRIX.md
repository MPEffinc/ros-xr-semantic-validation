# Framework Lineage and Architecture-Family Matrix

Purpose: prevent repository count from being mistaken for architectural generality. A fork, a
shared vendor SDK, a shared Unity example, or a shared transport library does **not** produce an
independent stack. This matrix records the lineage evidence actually found in source.

## Lineage fields per framework

| Framework | XR SDK / API | ROS integration | Transport | Downstream controller | Shared-code origin evidence |
| --- | --- | --- | --- | --- | --- |
| Spes | WebXR (browser) | research adapter only (not native) | HTTPS/WSS | Spes server callback; ROS added by this project | none found; self-contained web app |
| PickNik | Unity XR/OpenXR + XRI | Unity ROS-TCP Connector | TCP (ROS-TCP) | MoveIt Pro (external) | **Unity Robotics Hub** dependency |
| Quest2ROS2 | external Quest app (opaque) | external `ros_tcp_communication` | TCP (ROS-TCP) | external CLIK Cartesian controller | frontend is the public `quest2ros` app; ROS-TCP family |
| Docker_Teleop | Unity 6000.2.10f1, OpenXR 1.15.1 + Meta XR SDK 72.0.0 | **bespoke TCP JSON receiver** (primary) + vendored ROS-TCP-Endpoint (secondary channel) | raw TCP, newline JSON, port 5026→5005 | MoveIt Servo → Gazebo | vendors Unity `ROS-TCP-Endpoint` verbatim (`server.py:1` Unity copyright); credits in `docs/System_Setup.md:324-328`. **No Quest2ROS evidence** (grep: zero hits) |
| OpenVR UR5e | **OpenVR/SteamVR via pyopenvr** (ALVR to Quest 3) | direct rclpy publisher | in-process (no network transport) | MoveIt Servo → Gazebo | assembled from MoveIt Setup Assistant output, third-party `ur5_description`, and the stock MoveIt "hello_moveit" tutorial (mismatched maintainer identities; leftover `yourusername` clone URL) |
| OpenArmX | PICO/OpenXR app (external APK repo) | custom C++ bridge | **ASCII over UDP**, port 5100 | closed `openarmx_arm_driver` IK core → `forward_position_controller` → CAN | no fork evidence; original Chinese-language codebase |
| VR-hand-bridge | **Godot 4.6 OpenXR** | rclpy WebSocket server | WebSocket JSON, port 8765 | none (rviz/printer) | Godot OpenXR Vendors plugin (external binaries, git-ignored) |
| Nakama | claimed Unity | claimed Unity ROS-TCP Connector | claimed ROS-TCP | claimed Franka Cartesian impedance | **code absent**; README credits `frankaemika/franka_ros2`, `sp-sophia-labs/franka_ros2`, Unity ROS-TCP-Connector; actual code in third-party fork `JuanR5/VR_Teleop_Interface` |
| xiaoxiaoxh | Unity Meta (OVRInput/Transform) | HTTP `/unity` + rclpy | HTTP | direct Flexiv robot server | none found |
| Reachy | Unity Meta Movement | **none (non-ROS)** | direct WebSocket to daemon | Reachy daemon `/api/move/ws/set_target` | none found |
| NU-MECH | Unity Oculus Interaction (`IHand`) | C++ UDP parser → rclpy | UDP text | Qt visualiser only | Oculus Interaction SDK |
| Legged | Unity XR (`XRHand`) | Unity ROS-TCP Connector | TCP (ROS-TCP) | unconfirmed | **Unity Robotics Hub** dependency |
| Homebrew | Unity XR | rosbridge WebSocket | WebSocket | none included | rosbridge-suite |
| XRoboToolkit | **PicoXR Robot SDK/service** (vendor) | custom `xr_msgs/Custom` | vendor service JSON | ARX example (external) | vendor SDK |
| LTS0429 | opaque APK | ROS 2 node | UDP | unconfirmed | unknown |
| AgileX | opaque APK | ROS 2 + ADB | ADB/host | host IK | unknown |
| xArm Quest | **Quest2ROS app** | ROS 1 | ROS-TCP | direct xArm service | **shared Quest2ROS lineage** — explicitly excluded from independent counting |
| NVIDIA IsaacTeleop | native OpenXR / CloudXR | `isaac_ros_teleop` | DeviceIO tensors | retargeter → ROS EE messages | vendor stack |

## Architecture families

A family is defined by the combination of **XR acquisition API** and **XR→ROS boundary
mechanism**, because those two jointly determine which semantics can exist and where they can be
lost. Membership is asserted only where source lineage was inspected.

| Family | Members | Independent implementations within family |
| --- | --- | --- |
| **F1 WebXR / WSS** | Spes | 1 |
| **F2 Unity XR-or-Meta + Unity ROS-TCP** | PickNik, Legged, (Quest2ROS2 via external app), xArm Quest | PickNik and Legged share the Unity Robotics Hub connector; xArm shares the Quest2ROS frontend. **Count as 1 family, ~2 independent implementations (PickNik, Legged)** |
| **F3 Unity Meta + bespoke TCP JSON** | Docker_Teleop | 1 |
| **F4 Unity Meta + UDP text** | NU-MECH | 1 |
| **F5 Unity Meta + HTTP** | xiaoxiaoxh | 1 |
| **F6 Unity Meta + direct WebSocket, non-ROS** | Reachy | 1 |
| **F7 Unity XR + rosbridge WebSocket** | Homebrew | 1 |
| **F8 OpenVR / SteamVR + direct rclpy** | OpenVR UR5e | 1 |
| **F9 Godot OpenXR + WebSocket** | VR-hand-bridge | 1 |
| **F10 PICO/OpenXR + ASCII UDP** | OpenArmX | 1 |
| **F11 Vendor PicoXR service + custom ROS msg** | XRoboToolkit | 1 |
| **F12 Native OpenXR/CloudXR vendor stack** | NVIDIA IsaacTeleop | 1 |
| **F13 Opaque APK + UDP/ADB** | LTS0429, AgileX | unknown internals; not countable |
| **(unresolved)** | Nakama | source not available at pinned identity |

## What may and may not be claimed

- **Source-architecture breadth is genuinely wide**: at least 12 distinguishable families were
  identified with inspected source, spanning four different XR acquisition APIs (WebXR, Unity
  XR/Meta, OpenVR, Godot OpenXR) plus two vendor stacks (PicoXR, NVIDIA), and six distinct
  XR→ROS boundary mechanisms (WSS, Unity ROS-TCP, bespoke TCP JSON, UDP text, HTTP, rosbridge
  WebSocket) plus a non-ROS direct WebSocket case.
- **Runtime breadth is far narrower.** Actual runtime evidence exists for exactly two families:
  F1 (Spes, post-gate replay to ROS/DDS/Pi) and F2-adjacent (Quest2ROS2's host-side controller,
  actual ROS 2 transport and Pi reception). Everything else is E1 source evidence.
- **Do not count** xArm Quest as independent of Quest2ROS2 (shared frontend), and do not count
  PickNik and Legged as two independent transport designs (shared Unity ROS-TCP connector) —
  they are independent *applications* over a shared boundary library.
- **Do not count** Nakama at all until its source identity is resolved.
