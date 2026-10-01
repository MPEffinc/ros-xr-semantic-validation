# 00 — Repository and environment inventory (2026-10-01, KST)

## Instructions that apply

- No `AGENTS.md` or `CLAUDE.md` at the repository root, in `$HOME`, or in any tracked research
  directory. The only `AGENTS.md` files are inside the ignored upstream checkout
  `Deprecated/semantic_validation/targets/isaac_teleop/`, and they apply to that upstream project only.
- Repository rules come from the existing manifests and are inherited here:
  - never edit archived evidence or hash sidecars;
  - pin upstream checkouts by URL and SHA, and keep them untracked;
  - keep raw data local, and commit summaries plus hashes;
  - keep credentials out of git (root `.gitignore`).
- User standing preferences (agent memory):
  - replies in Korean;
  - an audit matrix and design report before freezing any formal campaign;
  - minimum sufficient trials;
  - no concurrent CPU load during timing-sensitive runs.

## Repository

| Item | Value |
|---|---|
| Remote | `git@github.com:MPEffinc/ros-xr-semantic-validation.git` (public) |
| Primary checkout | `/home/cclab/ros_xr`, on `research/n1-predictive-execution-mismatch` @ `6ea081ec3`, clean, no stash |
| This work | separate worktree `/home/cclab/ros_xr_evidence`, branch `research/xr-ros-evidence-framework` |
| Branch base | `main` = `25423a71c19f1ef74a0a8154d095336d6fe0559a` (the branch was created at main and was identical when work began) |
| Other branches (not modified) | `main`, `research/crossflow-gap-validation`, `research/n1-predictive-execution-mismatch` |
| Tags | `archive/pre-authority-continuity-20260929` |

Why a separate worktree: the primary checkout is on the N1 branch and holds N1 and cross-flow ignored
data (`experiments/*/results/raw`, `ws/`). On this branch that data would appear as untracked files.
The tree was not mixed with uncommitted work.

## Local-only assets and how to reuse them

| Asset | Location | Reuse |
|---|---|---|
| 19 S-track upstream target checkouts (OpenVR UR5e, Quest2ROS2, PickNik, Spes, Docker_Teleop, OpenArmX, …) | `/home/cclab/ros_xr/Deprecated/semantic_validation/targets/` (ignored) | read-only; pins in `Deprecated/ARCHIVE_VERIFICATION/nested_upstream_checkouts.txt` and `../references/UPSTREAM_PINS.md` |
| HORUS and COMPAS XR frameworks | `/home/cclab/ros_xr/Deprecated/frameworks/` | read-only |
| Quest 3 raw hardware JSONL (~307 MB), APKs | `/home/cclab/ros_xr/Deprecated/semantic_validation/logs/quest_hw/`, `Deprecated/local_artifacts/` | PRIOR_INTERNAL only |
| authority_continuity / xr_demo_integrity upstreams and raw data | worktree `archive/2026-10-01_closed_research/*/` (verified copy) and the original copy in the primary checkout | read-only |
| N1 / cross-flow raw data | `/home/cclab/ros_xr/experiments/*/results/raw/` | PRIOR_INTERNAL only |

The worktree has **no** copy of `Deprecated/`'s ignored data. Nothing in this workspace writes into
`Deprecated/`. Reads use the absolute primary-checkout path.

## Running processes belonging to other work (not touched)

| Container | Image | Up since | Note |
|---|---|---|---|
| `openvr_sim` | `openvr-jazzy-sim:local` | ~2026-09-14 | bind-mounts pre-2026-09-29 paths (`/home/cclab/ros_xr/semantic_validation/...`); the mounts follow the moved inodes |
| `docker_teleop_sim` | `docker-teleop-humble:local` | ~2026-09-14 | runs `ign gazebo` (~50 % of one core continuously), MoveIt Servo, receiver/mapper/bridge |
| `ros_env-ros-1` | `ros-xr-humble:local` | ~4 weeks | `net=host` |

**Consequences for experiments:**

- The host is not idle; the 1-minute load average is about 1.5.
- Any timing-sensitive run must either record this load or ask the owner before stopping it.
- `ros_env-ros-1` uses host networking, so DDS isolation must be explicit: use `ROS_DOMAIN_ID`, or
  `--network none` for our own containers.

## Software and hardware

| Item | Observed |
|---|---|
| Host OS | Ubuntu 24.04.3 LTS, 20 CPU, 31 GiB RAM |
| ROS on host | none (`/opt/ros` absent) |
| Docker | via `sg docker`, Bash sandbox disabled |
| ROS images | `ros:jazzy-ros-base`, `ros:humble-ros-base`, `openvr-jazzy-sim:local` (Jazzy, MoveIt Servo 2.12.4, ros_gz_sim 1.0.24, gz_ros2_control 1.2.20), `docker-teleop-humble:local` (Humble, MoveIt Servo 2.5.9, Gazebo Sim 6.18 / Fortress, ur_description 2.13.0), `s4b-rosmonitoring-{humble,jazzy}:20260922`, `ros-xr-horus-nav2-jazzy:local`, `xr-udp-jazzy*`, `vr-hand-bridge-humble:local`, `isaac-teleop-jazzy:local`, `openvr-jazzy-runtime:local` |
| XR runtime on host | Monado 21.0.0 (`monado-service`, `monado-cli`), OpenXR loader 1.0.20 (`libopenxr-loader1`). SteamVR is not installed. No headset. Whether Monado can run headless with a simulated device here: NOT_VERIFIED. |
| GPU | GTX 1050 Ti, 4 GiB. Isaac Sim / CloudXR are not usable. |
| Headset / robot | `adb devices` is empty: no Quest. No physical robot. |

**Hardware-dependent claims** cover real runtime focus/session transitions, real tracking loss and real
human behaviour. They are out of reach and are labelled NOT_VERIFIED wherever they arise.
