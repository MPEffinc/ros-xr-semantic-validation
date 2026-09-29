# Status

| Phase | Status | Commit | Remote verified | Notes |
|---|---|---|---|---|
| 0 Workspace init | DONE | `970e9261aebee33259c0b31b11f9c56d508a7aac` | yes | base `a619e23d2` == origin/main, clean |
| 1 Literature | DONE | `ee281ee3a82a067b7a404a93b78bb770af17aae6` | yes | all 10 listed items resolve; demo-poisoning prior art HIGH (SilentDrift, DropVLA, !Imperio, State Backdoor, 2609.26868); all assume dataset write access; no collection-path attacker in literature |
| 2 System audit | DONE | (this commit) | — | NVIDIA XR→dataset paths (LeRobot, Isaac Lab) use no ROS; Isaac ROS Teleop has no recorder; only tidybot_ros joins XR(phone)+ROS 2+dataset; XR boundaries: dataset influence = robot influence; other boundaries UNAUTH or FULL_WRITE; one LIMITED ROS candidate (TF granularity, hypothetical SROS2) |
| 3 Threat model | TODO | | | |
| 4 Testbed | TODO | | | |
| 5 Protocol freeze | TODO | | | |
| 6 Refutation experiments | TODO | | | |
| 7 Learning impact | TODO | | | conditional on PHASE 6 |
| 8 Verdict | TODO | | | |

## Environment observed 2026-09-30

- Host: Ubuntu 24.04.3 LTS, 20 CPU, 31 GiB RAM, GPU NVIDIA GeForce GTX 1050 Ti (4 GiB), no ROS on host.
- Docker available through the `docker` group (`sg docker`); existing local images include
  `ros:jazzy-ros-base`, `ros:humble-ros-base`, `isaac-teleop-jazzy:local` (from the closed S-track).
- `adb devices`: no Quest attached.
- Host Python 3.12.3 without numpy (experiments run in containers or a venv).
