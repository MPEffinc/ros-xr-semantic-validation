# 00 — Asset Inventory

Checked 2026-09-30, read-only, from repository root `/home/cclab/ros_xr` (branch
`research/crossflow-gap-validation` off `main@25423a71`). Nothing listed here was re-run for this
inventory. "Real" means produced with a physical Meta Quest 3; everything else is synthetic.

## 0. Findings that constrain this study

1. **No packet captures exist anywhere in the repository** (`*.pcap`, `*.pcapng`, `*.cap` — none). No
   tcpdump/tshark/scapy scripts, no LTTng / ros2_tracing use, no traffic or ML classifier code, no plotting
   scripts. The only `tc netem` code is in a never-run third-party checkout
   (`authority_continuity/references/upstream/horus_connector/scripts/run_distributed_benchmark.py`).
2. **A real Quest 3 was used over Wi-Fi** (Aug 30–31 and Sep 17, 2026). Its recordings are
   application-level (JSONL receive times, rosbag2, adb logcat), **not packet-level**, and none is task-labelled.
3. **Lab topology separates XR and ROS links**: Quest → Wi-Fi "CCLAB 5G" → desktop `wlx588694f02e61`
   (192.168.0.3); desktop → dedicated Ethernet `enp3s0f1` (10.10.10.1) → Raspberry Pi 4 (10.10.10.2,
   Humble) for DDS (`Deprecated/TESTBED_CONTEXT.md`, `…/results/RPI_TESTBED_STATUS.md`).
4. **Host constraints (checked live)**: GTX 1050 Ti (driver 580.173.02); `tcpdump` present but needs sudo
   (password required); `tshark` absent; host Python without numpy/pandas/sklearn/scapy; Docker only via
   `sg docker -c` with sandbox disabled; `adb devices` empty today (no Quest attached).
5. **CloudXR runtime cannot run here**: NVIDIA lists supported server GPUs as L40/L40S, RTX Pro Blackwell,
   RTX 5000/6000, GeForce RTX 5090/5080/4090 (docs.nvidia.com/cloudxr-sdk/latest/requirement/runtime_req.html,
   fetched 2026-09-30); Pascal is not listed.

## 1. Real-headset data

| Path | Content | Transport on the wire | Use here? | Caveats |
|---|---|---|---|---|
| `Deprecated/semantic_validation/logs/quest_hw/spes_quest_hw_2026083*/` (local-only, sha256 in `Deprecated/ARCHIVE_VERIFICATION/local_only_raw_sha256.txt`) | `server.jsonl` per-message server receive/complete monotonic ns + pose (canonical `…20260831T001349Z`: 90,583 updates) | WebXR over **HTTPS/WSS (TLS)**, Wi-Fi | Possible as a *timing* reference for a real XR input stream | no packet sizes; no task labels; server-side timestamps only |
| `Deprecated/semantic_validation/results/runs/hw_docker_native_20260917T071824Z/` | rosbag2 (155,837 msgs, 652 s), logcat | app TCP **plaintext** inside `adb reverse` | limited | Gazebo; not encrypted |
| `…/hw_picknik_native_20260917T074600Z/` | ROS observer JSONL (~60 Hz), Unity side-band | ROS-TCP **plaintext** :10000 over Wi-Fi | limited | plaintext; staged APK |
| `…/hw_quest2ros2_*_20260917T08*/` | rosbag2 (`cdr_093000Z`: 5,098 pose + 5,098 input + 2,153 target msgs) | ROS-TCP **plaintext** :10000 over Wi-Fi | limited | bags other than `cdr_093000Z` lack metadata |
| `…/hw_spes_native_20260917T081300Z/` | side-band, native ROS observer (5,197 msgs), `pi_sink.jsonl` (9,297 records over wired DDS) | WebXR TLS → DDS (Ethernet) → Pi | the only real XR→ROS→Pi chain | Pi clock unsynced; summary flag contradicts doc |
| `Deprecated/local_artifacts/quest_apps/{docker_teleop,picknik}/*.apk` | Quest apps | — | only with a headset | local-only |

## 2. XR–ROS stacks (source / images)

| Stack | Path | Wire transport | Runnable here | Use here? |
|---|---|---|---|---|
| Isaac ROS Teleop + CloudXR | `xr_demo_integrity/references/upstream/{isaac_ros_teleop@e8060286, IsaacTeleop@47f33af3}` | CloudXR.js: UDP 47998 media, TCP 49100 signalling, TCP 48322 TLS proxy; ROS 2 DDS to robot | **No** (GPU, headset) | topology analysis (Stage 1) |
| Spes WebXR teleop | `Deprecated/semantic_validation/targets/spes_teleop` (`c5d8081`), harness `…/harness/spes_hardware_server.py`, `spes_native_hardware_day.py` | HTTPS/WSS TLS :4443; DDS to Pi | yes with a Quest (was used) | only real encrypted XR→ROS chain available |
| Quest2ROS2 | `…/targets/quest2ros2` (`07aaf65`) + `Deprecated/ros_env/ros2_ws/src/ros_tcp_endpoint` (`54c1a64`) | ROS-TCP **plaintext** (`server.py:52,95-100`) | yes with Quest app | second stack for Stage 1 |
| PickNik Meta Quest teleop | `…/targets/meta_quest_teleoperation` (`bbaef07`) | ROS-TCP plaintext | APK present | no |
| Docker_Teleop | `…/targets/docker_teleop` (`64cbdde`), image `docker-teleop-humble:local` | JSON TCP plaintext | image yes | no |
| HORUS | `Deprecated/frameworks/horus*`, `authority_continuity/references/upstream/horus_ros2@eca75cb` | TCP 10000/10001, no TLS | mock client only | no |
| horus_connector | `authority_continuity/references/upstream/horus_connector` (`55933a9`) | Zenoh tcp/tls/quic + WebRTC DTLS-SRTP | never run; multi-host | candidate for encrypted media+control, not runnable as-is |
| UDP/WebSocket bridges (NU-MECH, OpenArmX, LTS0429, vr_hand_bridge) | `…/targets/*`, images `xr-udp-jazzy*`, `vr-hand-bridge-humble` | plaintext UDP / WS | synthetic only | no |

## 3. Images and simulators (built locally)

| Image | Content | As-is | Use here? |
|---|---|---|---|
| `ros-xr-humble:local` (`Deprecated/ros_env/Dockerfile`) | Humble + rosbridge + **sros2** + fastapi/websockets; host network | yes | yes: DDS / SROS2 traffic generation and capture in-container |
| `openvr-jazzy-sim:local` | MoveIt Servo + Gazebo + ros2_control (xvfb, CPU) | yes | possible robot-side plant |
| `docker-teleop-humble:local` | Docker_Teleop + MoveIt Servo + Gazebo | yes | possible |
| `ros-xr-horus-nav2-jazzy:local` | Nav2 + loopback plant | yes | no |
| `ros:humble-ros-base`, `ros:jazzy-ros-base`, `python:3.12-slim` | bases | yes | yes (analysis env) |
| `isaac-teleop-jazzy:local`, `xr-udp-jazzy*`, `vr-hand-bridge-humble` | no Dockerfile in repo | yes | no |

## 4. Harness code

| Path | Purpose | Use here? | Caveat |
|---|---|---|---|
| `Deprecated/semantic_validation/harness/spes_*` | real-Quest WebXR server with per-message timing; hardware-day orchestration Quest→Spes→DDS→Pi | only if a real capture session is run | scripts reference pre-archive paths (need `Deprecated/` prefix — copy, don't edit) |
| `…/testbed/pi_ws/src/semantic_robot_endpoint/semantic_robot_sink.py` | Pi-side sink with receive timestamps | same | deployed on the Pi |
| `…/harness/*_runtime.py`, `*_trials.py` | synthetic wire injectors | no (synthetic) | loopback / `--network none` |
| `Deprecated/ros_env/security/policy.xml`, `run_feasibility.sh` | SROS2 Enforce keystore | yes as encryption baseline reference | loopback |

## 5. What does not exist and would have to be built

pcap capture points on real links, a task-labelled trial protocol, feature extraction, classifiers
(RF/XGBoost, 1D-CNN), shuffling/shift ablations, defense implementations (padding, constant-rate, FRONT,
NetShaper-style DP shaping), plotting. Real XR traffic additionally needs a physical Quest and a human
operator; CloudXR traffic needs an RTX 4090-class server.
