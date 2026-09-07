# Testbed Context

Quick-restore file for new Claude/Codex sessions. For full detail see
`semantic_validation/results/` (canonical) and `semantic_validation/results/RPI_TESTBED_STATUS.md`.

## Core research question

Does safety-relevant XR semantic context (tracking validity, actively-tracked
vs inferred/emulated state, source identity, source timestamp/freshness,
reference-frame provenance, session/transport generation, invalidation/re-arm
condition) survive the XR application -> transport/bridge -> ROS ->
downstream control boundary, or get equivalently re-validated before action —
or is it silently dropped and treated as still-actionable?

## Current decision

**GO — NOT STRONG GO** (`semantic_validation/results/RESEARCH_DECISION.md`).
Spes has a real actual-hardware-to-server finding; a second independent
stack's actual runtime/hardware confirmation is still missing.

## Strongest evidence per stack

| Stack | Level | Boundary |
| --- | --- | --- |
| Spes `c5d8081` | `ACTUAL_XR_HARDWARE -> ACTUAL_SPES_SERVER_CALLBACK` | Actual Quest 3 emulated-tracking interval; production packet/callback continues 5/5; no-user-rearm recovery 5/5 |
| PickNik `bbaef07` | `SOURCE_DATAFLOW_CONFIRMED` | Tracking state wired to controller Transform, dropped at Odometry/TF publisher boundary; wall-clock re-stamp |
| Quest2ROS2 `07aaf65` | `CONFIRMED_RUNTIME_SYNTHETIC_SOURCE` | Unchanged callback consumes stale/future stamps, re-stamps/re-frames; actual ROS transport `BLOCKED_ENV` |
| NVIDIA | `MACHINE_CHECKED_STATIC` + current-main `RUNTIME_SYNTHETIC` | `VALID` gated, `TRACKED` bits not checked (partial positive control) |

Decisive next experiment (per `RESEARCH_DECISION.md` / `MANUAL_REQUIRED.md`):
**PickNik actual Quest -> dummy ROS observer** (occlude controller, watch
whether Odometry/TF keeps progressing). Requires Unity 6000.1.6f1-compatible
editor + ADB-connected Quest + ROS 2 Python env — none present yet.

## Target testbed architecture

```text
Meta Quest 3
   | Wi-Fi
   v
Linux Desktop
   XR application / XR-to-ROS interface / ROS 2
   |
   | dedicated Ethernet / DDS   (Desktop enp3s0f0 or enp3s0f1 -> Pi eth0)
   v
Raspberry Pi 4 (rosxr, Ubuntu 22.04 ARM64, ROS 2 Humble native apt)
   |
   semantic_robot_sink / dummy robot controller
   X no physical robot/actuator

Desktop usb0 (10.55.0.1) <--USB gadget--> Pi usb0 (10.55.0.2)
   management/fallback SSH path only — separate from the ROS/DDS data plane
```

Purpose: give Spes/PickNik/Quest2ROS2 a common, physically-separate robot-side
ROS endpoint so an actual XR hardware transition can be correlated against
actual downstream ROS reception — not just a server callback on the same box.

**Standardization decision (2026-09-02, approved):** current Pi OS (Ubuntu
20.04.5) will be reimaged to Ubuntu 22.04 ARM64, hostname changed to `rosxr`
(avoids the `worker1.local` mDNS collision below), ROS 2 Humble via native
apt on the Pi. Dedicated Ethernet: Desktop `enp3s0f0` = `10.10.10.1/24` <->
Pi `eth0` = `10.10.10.2/24`, no gateway either side. USB gadget
(`10.55.0.1`/`10.55.0.2`) kept as the permanent management/recovery SSH path.
`enp4s0` research LAN is never touched. Plan:
`semantic_validation/results/RPI_REIMAGE_PLAN.md`. Not performed
automatically — physical SD-card reflash and cabling are user actions.
**Reimage flashed and verified booted 2026-09-02** (see
`semantic_validation/results/RPI_REIMAGE_RESULT.md` and
`RPI_TESTBED_STATUS.md`): official Ubuntu 22.04.5 arm64, hostname `rosxr`,
user `cclab` key-only SSH (`ssh rosxr`, alias in `~/.ssh/config`). Dedicated
Ethernet is live on **`enp3s0f1`** (not `f0` as originally planned — both
were equivalent free ports; the user cabled `f1`), Desktop
`10.10.10.1/24` ↔ Pi `10.10.10.2/24`, no gateway. ROS 2 Humble installed
natively on the Pi and via the Desktop's `ros_env` Docker container
(`network_mode: host` now, was bridge-only). **Cross-host ROS 2/DDS
talker/listener verified PASS in both directions** — this is
infrastructure evidence, not a semantic-validation finding.

**`semantic_robot_sink` dummy endpoint built and verified**
(`semantic_validation/testbed/pi_ws/src/semantic_robot_endpoint/`, deployed
and colcon-built on the Pi): subscribes to `/robot_target_pose`
(PoseStamped), `/left_controller_odom` + `/right_controller_odom`
(Odometry, matching PickNik's topic names), and `/tf`; logs every reception
to JSONL with wall/monotonic time, header stamp, frame ids, pose, and a
per-topic counter. No actuator, no semantic gating —
`accept_decision` is hardcoded `ACCEPTED_NO_SEMANTIC_GATING`. Smoke-tested
end-to-end from the Desktop container over the dedicated link for all three
message types.

## Current topology (as of 2026-09-02)

- Desktop `cclab`: Ubuntu 24.04.3, x86_64. Three physical Ethernet NICs:
  `enp4s0` (Realtek RTL8125 2.5GbE) 10.80.79.38/24 — research LAN, active
  default route, **in use, do not repurpose**; `enp3s0f0` and `enp3s0f1`
  (Intel 82576 Gigabit dual-port) — both currently DOWN/NO-CARRIER, **free**,
  earmarked for the dedicated Pi Ethernet link (no new adapter needed). Also
  `wlx588694f02e61` 192.168.0.3/24 (Wi-Fi "CCLAB 5G"), `usb0` 10.55.0.1/24
  (USB-gadget link to the Pi, NM profile `pi-usb`), `tailscale0`
  100.65.175.20.
- Raspberry Pi `worker1`: Ubuntu 20.04.5 (focal), aarch64, 7.6GiB RAM, 30GB
  storage (25G free). `usb0` 10.55.0.2/24 is the only working link right now.
  `eth0` and `wlan0` are both DOWN/NO-CARRIER — the intended dedicated
  Ethernet link is **not physically established**.
- SSH: `ssh worker1-usb` (config alias -> `10.55.0.2`, key
  `~/.ssh/id_ed25519_worker1`) works non-interactively today.
- **`worker1.local` (mDNS on the research LAN, resolves to 10.80.79.124) is a
  DIFFERENT device, not this Pi** — SSH host key mismatch confirmed
  (OpenSSH 8.9p1/Ubuntu 22.04-style banner vs the real Pi's OpenSSH
  8.2p1/Ubuntu 20.04-style banner over the USB path). Do not SSH into it or
  treat it as the robot-side computer.

## ROS versions

- Compatibility target: Ubuntu 22.04 ARM64 + ROS 2 Humble on the Pi.
- Desktop: no host ROS 2; `ros_env/compose.yaml` + `Dockerfile` provide a
  Humble container, previously built, but Docker daemon access is currently
  denied (see blockers).
- Pi: no ROS 2 installed yet; OS is 20.04, not the 22.04 target.

## Completed setup

- Passive Pi discovery + read-only inventory over the working USB path.
- Desktop OS/network/ROS/Docker inventory.
- mDNS collision on the research LAN identified and avoided.
- `semantic_validation/results/RPI_TESTBED_STATUS.md` written with full detail.

## Blocked / needs your action (still open)

1. Pi reimage (Ubuntu 22.04 ARM64, hostname `rosxr`) — physical
   SD-card-flash action, not yet done (Pi still answers as `worker1`/20.04.5
   over USB). See `RPI_REIMAGE_PLAN.md`.
2. Dedicated Ethernet cable from Pi `eth0` to Desktop `enp3s0f0` — physical
   cabling action, not yet done (`enp3s0f0` still NO-CARRIER).
3. Desktop `cclab` is still not in the `docker` group (socket is
   `root:docker`, `docker info` still permission-denied) — needed to run the
   Desktop's `ros_env` Humble container. Fix: `sudo usermod -aG docker cclab`
   + re-login; not done automatically.

## Resolved this session

- Git repository initialized, `.gitignore` applied, baseline commit
  `2f40905d728dc83334c3d5940f1ddf337aea4cc5` pushed to the new private
  GitHub repo `https://github.com/MPEffinc/ros-xr-semantic-validation`
  (branch `main`, local/remote SHA confirmed identical). `gh` CLI is
  installed and authenticated as `MPEffinc`.

## Key file paths

**Start here (2026-09-07 framework audit):**

- `semantic_validation/results/FRAMEWORK_RESEARCH_UTILITY_AUDIT.md` — main audit, four-axis model, claim-utility matrix, selection-bias check
- `semantic_validation/results/FRAMEWORK_POPULATION_MATRIX.md` — 18 identities × four axes × I1–I5 disposition
- `semantic_validation/results/FRAMEWORK_LINEAGE_MATRIX.md` — architecture families and shared-lineage guard
- `semantic_validation/results/FRAMEWORK_TESTBED_ADAPTATION_PLAN.md` — what to run next, with a safety register of launch files that must never be run
- `semantic_validation/results/RESEARCH_ITEM_REASSESSMENT.md` — paper shape and decision
- `semantic_validation/frameworks/<name>/RESEARCH_UTILITY.md` — per-framework reports
- `semantic_validation/methodology/` — V2 evidence levels, event model, selection policy

**Latest runtime results (both robot-free, E2, no Quest):**

- `semantic_validation/results/QUEST2ROS2_ROS_RUNTIME.md` — actual ROS 2 transport with the pinned production node
- `semantic_validation/results/QUEST2ROS2_SIMULATIONINPUT_PI.md` — in-repo simulator → production node → DDS → Pi, 619/619

**Prior canonical:**

- `semantic_validation/results/EVIDENCE_LEDGER.md` — canonical findings ledger
- `semantic_validation/results/RESEARCH_DECISION.md` — GO/NOT-STRONG-GO rubric
- `semantic_validation/results/MANUAL_REQUIRED.md` — exact remaining manual/hardware steps
- `semantic_validation/results/PICKNIK_HW_READY.md` — prepared PickNik hardware harness
- `semantic_validation/results/RPI_TESTBED_STATUS.md` — full Pi/Desktop testbed detail
- `semantic_validation/results/RPI_REIMAGE_PLAN.md` — Pi reimage target/procedure
- `.gitignore` — applied in the baseline commit

Git: initialized, branch `main`, baseline commit
`2f40905d728dc83334c3d5940f1ddf337aea4cc5`, pushed to
`https://github.com/MPEffinc/ros-xr-semantic-validation` (private).
Local/remote SHA confirmed identical.
