# Status

| Phase | Status | Commit | Remote verified | Notes |
|---|---|---|---|---|
| 0 Workspace init | DONE | (this commit) | — | base `a619e23d2` == origin/main, clean |
| 1 Literature | TODO | | | |
| 2 System audit | TODO | | | |
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
