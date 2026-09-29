# Raspberry Pi Testbed Status

Session: 2026-09-02. This document records infrastructure/preflight state only.
It is not a semantic-validation finding and must not be cited as evidence in
[EVIDENCE_LEDGER.md](EVIDENCE_LEDGER.md) or [RESEARCH_DECISION.md](RESEARCH_DECISION.md).

Git baseline: repository initialized, branch `main`, baseline commit
`2f40905d728dc83334c3d5940f1ddf337aea4cc5` ("chore: establish ROS-XR research
baseline"), pushed to private GitHub repo
`https://github.com/MPEffinc/ros-xr-semantic-validation`. Local/remote SHA
confirmed identical.

## Hardware

- Desktop: MSI MS-7D42 tower, x86_64.
- Meta Quest 3: not connected/used this session.
- Raspberry Pi 4 Model B: hostname `worker1`, aarch64.

## Desktop

| Item | Value |
| --- | --- |
| hostname | `cclab` |
| OS | Ubuntu 24.04.3 LTS (noble), kernel `7.0.0-30-generic` |
| Architecture | x86_64 |
| Ethernet (research LAN) | `enp4s0`, `10.80.79.38/24`, gateway `10.80.79.254` |
| Wi-Fi | `wlx588694f02e61`, `192.168.0.3/24`, SSID `CCLAB 5G`, gateway `192.168.0.1` |
| USB gadget link to Pi | `usb0`, `10.55.0.1/24`, NetworkManager profile `pi-usb` |
| Tailscale | `tailscale0`, `100.65.175.20/32` |
| `enp3s0f0`/`enp3s0f1` | present, no carrier, unused |
| ROS 2 (host) | not installed (`ros2` not found, no `ROS_*`/`RMW_*` env) |
| ROS 2 (containerized) | `ros_env/compose.yaml` + `Dockerfile` exist (ROS 2 Humble target), previously built per `RESEARCH_CONTEXT.md` progress log (2026-08-25) |
| Docker client | `29.1.3`, present |
| Docker daemon access | **BLOCKED_ENV** — `permission denied` on `/var/run/docker.sock`. Socket is `root:docker` mode `0660`; user `cclab`'s groups are `cclab,adm,cdrom,sudo,dip,plugdev,users,lpadmin` — **no `docker` group membership**. Standard fix is `sudo usermod -aG docker cclab` + re-login; **not performed automatically** (requires sudo). |

## Raspberry Pi (`worker1`, via USB path `10.55.0.2`)

| Item | Value |
| --- | --- |
| hostname | `worker1` |
| Machine ID | `3b7f2979540047dbb479e4f9e6425423` |
| OS | Ubuntu 20.04.5 LTS (focal), kernel `5.4.0-1080-raspi` |
| Architecture | aarch64 / arm64 |
| RAM | 7.6 GiB total |
| Storage | `/dev/mmcblk0p2` ext4, 30G total, 3.8G used, 25G available (14%) |
| `eth0` | **DOWN, NO-CARRIER** — administratively up but no physical link detected |
| `wlan0` | DOWN, NO-CARRIER (radio present, not associated) |
| `usb0` | UP, `10.55.0.2/24` — currently the **only working network path** |
| SSH | enabled, active; key-based auth already working (see below) |
| ROS 2 | not installed |
| Docker | `docker.io 20.10.12` installed; daemon access **BLOCKED_ENV** — same group-membership issue as Desktop (`cclab` not in `docker` group) |
| Existing workspace/data | none found (`find / -iname "*ros_xr*" -o -iname "*semantic*"` empty); home directory has only default dotfiles |

## SSH access

- Working path: `ssh worker1-usb` (alias in `~/.ssh/config`, `HostName 10.55.0.2`, key `~/.ssh/id_ed25519_worker1`) — **key-based, non-interactive, PASS**.
- `worker1.local` (mDNS) resolves on the Desktop's research LAN (`enp4s0`, `10.80.79.0/24`) to **`10.80.79.124`**.
  **This is NOT the target Raspberry Pi.** Its SSH host key (`ssh-ed25519 AAAAC3...EjuY0Mo...`, banner `OpenSSH_8.9p1 Ubuntu-3ubuntu0.16`, consistent with Ubuntu 22.04) does not match the real Pi's host key (`ssh-ed25519 AAAAC3...LKvXsd8...`, banner `OpenSSH_8.2p1 Ubuntu-4ubuntu0.5`, consistent with Ubuntu 20.04, confirmed live via the USB path). This is most likely an unrelated device on the shared LAN with a colliding mDNS name.
  One non-interactive key-only connection attempt was made against `10.80.79.124` for host-key comparison; it was cleanly rejected (`Permission denied (publickey,password)`), no password was sent or requested.
- **Do not treat `worker1.local` / `10.80.79.124` as the Pi** until this is resolved. The real Pi's `eth0` currently has no carrier at all, so it cannot be reachable over the research LAN right now regardless of hostname.

## Decision (2026-09-02, standardization)

- Pi's current Ubuntu 20.04.5 will **not** be used as the final testbed OS.
  Target: **Ubuntu Server 22.04 LTS ARM64 + ROS 2 Humble**. Reimage plan
  written to [`RPI_REIMAGE_PLAN.md`](RPI_REIMAGE_PLAN.md); not performed
  automatically (physical SD-card reflash, user-performed).
- Post-reimage hostname will be **`rosxr`** (not `worker1`), to avoid any
  further confusion with the unrelated `worker1.local` device already found
  colliding on the research LAN.
- The working USB gadget path (`10.55.0.1` ↔ `10.55.0.2`, key-based SSH PASS)
  is kept as the permanent **management/fallback path**, independent of
  whatever happens on the Ethernet data plane.
- The ROS 2/DDS data plane will use a **dedicated Ethernet link**, not the
  shared research LAN.

## Ethernet NIC inventory (Desktop) — read-only diagnostics

Desktop has **three** physical Ethernet controllers, not one:

| Interface | Controller | Carrier | Currently used for |
| --- | --- | --- | --- |
| `enp4s0` | Realtek RTL8125 2.5GbE (`04:00.0`) | up (1) | Research LAN — confirmed via active default route (`8.8.8.8 via 10.80.79.254 dev enp4s0`) and NetworkManager connection `Wired connection 3` |
| `enp3s0f0` | Intel 82576 Gigabit, port 0 (`03:00.0`) | **down (0), NO-CARRIER** | unused — free |
| `enp3s0f1` | Intel 82576 Gigabit, port 1 (`03:00.1`) | **down (0), NO-CARRIER** | unused — free |

**Consequence:** a dedicated Desktop↔Pi Ethernet link does **not** require a
new USB-Gigabit-Ethernet adapter. One of the two free onboard Intel ports
(`enp3s0f0` or `enp3s0f1`) can be cabled directly to the Pi's `eth0` once it
is reimaged, keeping `enp4s0` untouched on the research LAN. No change was
made to `enp4s0`'s configuration.

The Pi's own `eth0` NO-CARRIER (previous finding) is unaffected by this — it
is still a Pi-side physical-link problem (or simply "nothing plugged into
this specific spare port yet") to resolve when the dedicated cable is run.

## Current Physical Topology (verified working, 2026-09-02)

```text
Desktop (cclab, Ubuntu 24.04, x86_64)
  enp4s0     10.80.79.38/24   -- research LAN (untouched; also has an unrelated
                                  host answering to mDNS "worker1" -> 10.80.79.124,
                                  NOT this Pi)
  wlx58...   192.168.0.3/24   -- "CCLAB 5G" Wi-Fi
  enp3s0f1   10.10.10.1/24    -- dedicated Ethernet, NM connection "pi-dedicated-eth",
      |                          no gateway. enp3s0f0 remains free/unused.
      | ROS 2/DDS -- VERIFIED PASS both directions (demo_nodes_cpp talker/listener)
      v
  eth0       10.10.10.2/24  -- Raspberry Pi 4 "rosxr", Ubuntu 22.04.5 arm64,
                                ROS 2 Humble (native apt)
  usb0 (Desktop 10.55.0.1) <--USB gadget--> usb0 (Pi, if re-enabled) -- management
                                              fallback path, not verified after reimage

Quest 3: not connected this session.
```

## Target Topology

```text
Meta Quest 3
   | Wi-Fi
   v
Linux Desktop
   XR application / XR-to-ROS interface / ROS 2 (Docker, network_mode: host)
   |
   | dedicated Ethernet / DDS  -- VERIFIED  (enp3s0f1 -> Pi eth0, 10.10.10.0/24)
   v
Raspberry Pi 4 (rosxr)
   Ubuntu 22.04 / ROS 2 Humble (native apt) -- VERIFIED
   |
   semantic_robot_sink / dummy robot controller  -- NOT YET BUILT
   X
   no physical robot/actuator

Desktop usb0 (10.55.0.1) <--USB gadget--> Pi usb0 (10.55.0.2)
   management/fallback SSH path — not re-verified since reimage (g_ether config
   is not part of the stock Ubuntu image; separate task if needed)
```

## Completed this session

- Restored research context from `semantic_validation/results/` canonical docs and root `RESEARCH_CONTEXT.md`; confirmed current decision **GO — NOT STRONG GO** and the strongest evidence boundaries per stack (see [TESTBED_CONTEXT.md](../../TESTBED_CONTEXT.md) for the condensed summary).
- Desktop read-only inventory (OS, network, ROS, Docker).
- Passive Raspberry Pi discovery over the existing USB gadget link; confirmed working key-based SSH (`worker1-usb`).
- Full read-only Pi inventory over that SSH path (OS, arch, storage, RAM, network interfaces, ROS/Docker state, home directory contents).
- Detected and diagnosed an mDNS hostname collision (`worker1.local` resolves to an unrelated device on the research LAN); did not attempt further contact with that host beyond one clean key-auth rejection.
- Confirmed no destructive action was taken: no OS reinstall, no `sudo`, no Docker socket/group change, no network reconfiguration, no robot/actuator connection.

## Blocked (needs user action/decision)

1. **Pi reimage is a physical action.** Plan is written ([`RPI_REIMAGE_PLAN.md`](RPI_REIMAGE_PLAN.md)); the actual SD-card flash must be done by the user with Raspberry Pi Imager (or equivalent), not automated here.
2. **Dedicated Ethernet cabling is a physical action.** Run a cable from the Pi's `eth0` to the Desktop's `enp3s0f0` or `enp3s0f1` (both free, confirmed no-carrier, not the research LAN). No new hardware is needed — this was previously assumed to require a new adapter; it does not.
3. **Docker daemon access on the Desktop.** Socket is `root:docker` owned; `cclab` is not in the `docker` group. Needed only if the Desktop's `ros_env` (Humble) container will be used for the ROS 2 host role — re-confirmed as needed for this testbed, since Ubuntu 24.04 has no native Humble apt package. Fix is `sudo usermod -aG docker cclab` + re-login — requires sudo, not run automatically. (Pi-side Docker group is **no longer relevant** — Pi will be reimaged, see decision above.)
4. **No dedicated-Ethernet ROS 2/DDS test has been run** — blocked by #1 and #2 (no Pi target OS, no cable run yet) and #3 (no ROS 2 available on the Desktop yet).
5. ~~Git repository is not actually initialized; GitHub CLI is not installed.~~ **RESOLVED.** `gh` was installed and authenticated (account `MPEffinc`) by the user; git repository initialized (branch `main`), 520 files / ~25MB staged after `.gitignore` exclusions (verified: no file >90MB, no `.pem`/`.key`/`.env`/credential-shaped file staged), baseline commit `2f40905` created and pushed to the new private GitHub repo `MPEffinc/ros-xr-semantic-validation`. Local and remote SHA confirmed identical.
6. **Desktop Docker group membership still not fixed.** `id` still shows no `docker` group for `cclab`; `docker info` still returns permission denied. Needed before the Desktop's `ros_env` Humble container can run. Fix (`sudo usermod -aG docker cclab` + re-login) remains a user action.
7. ~~Pi has not been reimaged yet~~ **DONE.** Card flashed with Ubuntu 22.04.5 arm64, cloud-init set for hostname `rosxr` / user `cclab` / static `eth0=10.10.10.2/24`. Full detail: [`RPI_REIMAGE_RESULT.md`](RPI_REIMAGE_RESULT.md).
8. ~~Dedicated Ethernet still shows NO-CARRIER~~ **DONE — with a correction.** The user cabled the Pi to **`enp3s0f1`**, not `enp3s0f0` as originally planned (both were free/equivalent; `enp3s0f1` is now the live dedicated interface, `enp3s0f0` remains free/unused). Desktop side configured as NetworkManager connection `pi-dedicated-eth` (renamed from an auto-created DHCP profile), static `10.10.10.1/24`, no gateway. Carrier confirmed up, ping and ARP/neighbor MAC (`e4:5f:01:c4:0d:94`) cross-verified against the Pi's known `eth0` MAC — same physical device.
9. ~~ROS 2 not installed on Pi~~ **DONE.** Native apt install of `ros-humble-ros-base` + `rclpy`/`rclcpp`/`geometry-msgs`/`nav-msgs`/`std-msgs`/`tf2`/`tf2-msgs`/`tf2-ros`/`rosbag2`/`demo-nodes-cpp`/`demo-nodes-py`/`python3-colcon-common-extensions`/`python3-rosdep`, sourced from `~/.bashrc`. Official `packages.ros.org` apt repo + GPG key only, no third-party install script.
   - **Bootstrap blocker and how it was resolved:** the dedicated link intentionally has no gateway, so the Pi had no path to `packages.ros.org` for `apt install`. With explicit user approval, a **temporary** NAT was set up on the Desktop (`iptables -t nat -A POSTROUTING -s 10.10.10.0/24 -o enp4s0 -j MASQUERADE` + two `FORWARD` accept rules, `pkexec`-authenticated) and a temporary default route + DNS override were added on the Pi (the route/DNS commands were run by the user directly, since the assistant's own attempt was blocked by the auto-mode safety classifier). All of this was **removed again** immediately after the install completed — the dedicated link is back to its steady-state no-gateway configuration. See commands below for the exact add/remove pairs.
10. ~~Desktop `ros_env` Docker Humble not usable~~ **DONE.** `cclab` added to the `docker` group (`pkexec usermod -aG docker cclab`; applied in-session via `sg docker`, no logout needed for the assistant's own use — **a full logout/login is still recommended for the user's own normal terminal sessions** to pick up the new group membership there). `ros_env/compose.yaml` updated: `network_mode: host` and `ROS_LOCALHOST_ONLY: "0"` added (was `"1"`, single-host-only) so the container's DDS traffic reaches the dedicated Ethernet interface directly instead of being trapped behind Docker's bridge/NAT. `ROS_DOMAIN_ID` pinned to `"0"` explicitly (matches the Pi's default). Image `ros-xr-humble:local` builds and runs.
11. **Cross-host ROS 2/DDS baseline: PASS, both directions.** `ros2 run demo_nodes_cpp talker`/`listener`, plain default QoS, `ROS_DOMAIN_ID=0`, `RMW_IMPLEMENTATION=rmw_fastrtps_cpp` on both ends (Desktop container: host network; Pi: native).
    - Desktop talker → Pi listener: 9/9 `Hello World` messages received, in order, arrival ~0.4–0.7 ms after publish.
    - Pi talker → Desktop listener: 9/9 messages received, in order, similar latency.
    - This is `ACTUAL_ROS_RUNTIME` evidence for infrastructure purposes (DDS discovery + pub/sub transport across the dedicated Ethernet) — **not** a semantic-validation finding; no XR data was involved in this test.
12. **`semantic_robot_sink` dummy endpoint: built and verified on the Pi.** Source lives in-repo at `semantic_validation/testbed/pi_ws/src/semantic_robot_endpoint/` (ament_python package), deployed to `~/ros2_ws/src/` on the Pi and built with `colcon build --symlink-install`. Subscribes to a generic `PoseStamped` target-pose topic (`/robot_target_pose`, param-configurable), the two PickNik controller-odometry topics (`/left_controller_odom`, `/right_controller_odom`), and `/tf`; logs every reception to JSONL under `~/semantic_robot_endpoint_logs/` with receive wall/monotonic time, topic, message type, header stamp, frame/child-frame id, position, orientation (or the full transform list for `/tf`), a per-topic receive counter, and an explicit `accept_decision`. **It performs no actuator control and no semantic validation or gating** — `accept_decision` is hardcoded to `ACCEPTED_NO_SEMANTIC_GATING` precisely so its output is never mistaken for a semantic finding. One-shot smoke test from the Desktop container (`ros2 topic pub --once`) confirmed correct field extraction for all three message types over the dedicated Ethernet link.

## Commands (reproducible)

```bash
# Working SSH path to the Pi (USB gadget)
ssh worker1-usb   # alias in ~/.ssh/config -> cclab@10.55.0.2, key ~/.ssh/id_ed25519_worker1

# Desktop inventory
hostnamectl; uname -a; ip -br addr; ip route; nmcli device status
which ros2; docker info

# Pi inventory (over worker1-usb)
ssh worker1-usb 'hostnamectl; uname -a; ip -br addr; free -h; df -h /; lsblk -f'

# Host-key comparison that revealed the mDNS collision
ssh-keyscan -t ed25519 10.55.0.2
ssh-keyscan -t ed25519 worker1.local

# SSH to the reimaged Pi over the dedicated Ethernet link
ssh rosxr   # alias -> cclab@10.10.10.2, key ~/.ssh/id_ed25519_worker1

# Temporary internet path for one-time `apt install` on the Pi (added, used, then
# fully removed again — the dedicated link has no gateway in steady state):
#   Desktop (pkexec, one dialog):
iptables -t nat -A POSTROUTING -s 10.10.10.0/24 -o enp4s0 -j MASQUERADE
iptables -A FORWARD -i enp3s0f1 -o enp4s0 -j ACCEPT
iptables -A FORWARD -i enp4s0 -o enp3s0f1 -m state --state RELATED,ESTABLISHED -j ACCEPT
#   Pi:
sudo ip route add default via 10.10.10.1
sudo resolvectl dns eth0 8.8.8.8 1.1.1.1
#   ...apt install ros-humble-ros-base ... (Acquire::ForceIPv4=true — the Pi has
#   no IPv6 route through this NAT)...
#   Cleanup, Pi:
sudo ip route del default via 10.10.10.1
sudo resolvectl revert eth0
#   Cleanup, Desktop (pkexec):
iptables -t nat -D POSTROUTING -s 10.10.10.0/24 -o enp4s0 -j MASQUERADE
iptables -D FORWARD -i enp3s0f1 -o enp4s0 -j ACCEPT
iptables -D FORWARD -i enp4s0 -o enp3s0f1 -m state --state RELATED,ESTABLISHED -j ACCEPT

# Cross-host ROS 2/DDS baseline (verified PASS both directions)
#   Pi:
ros2 run demo_nodes_cpp listener
#   Desktop:
docker compose -f ros_env/compose.yaml exec -T ros bash -c \
  'source /opt/ros/humble/setup.bash; ros2 run demo_nodes_cpp talker'
#   ...and the reverse direction (talker on Pi, listener on Desktop container).

# Deploy + build + run semantic_robot_sink on the Pi
scp -r semantic_validation/testbed/pi_ws/src/semantic_robot_endpoint rosxr:~/ros2_ws/src/
ssh rosxr 'source /opt/ros/humble/setup.bash && cd ~/ros2_ws && colcon build --symlink-install --packages-select semantic_robot_endpoint'
ssh rosxr 'source /opt/ros/humble/setup.bash && source ~/ros2_ws/install/setup.bash && ros2 run semantic_robot_endpoint semantic_robot_sink'

# Smoke-test publish from the Desktop container, any of the three types, e.g.:
docker compose -f ros_env/compose.yaml exec -T ros bash -c \
  "source /opt/ros/humble/setup.bash; ros2 topic pub --once /robot_target_pose geometry_msgs/msg/PoseStamped \
   '{header: {frame_id: base_link}, pose: {position: {x: 1.0, y: 2.0, z: 0.5}, orientation: {w: 1.0}}}'"
```

## Research Relevance

This testbed's only purpose is to give Spes, PickNik, and Quest2ROS2 a common,
physically-real robot-side ROS 2 endpoint so that an actual XR hardware
transition can be correlated against actual downstream ROS reception on a
device separate from the Desktop — the missing link identified in
[RESEARCH_DECISION.md](RESEARCH_DECISION.md) as required for a second
independent runtime/hardware confirmation (currently only Spes has
`ACTUAL_XR_HARDWARE -> ACTUAL_SPES_SERVER_CALLBACK`; PickNik's
`SOURCE_DATAFLOW_CONFIRMED` decisive experiment specifically calls for a
Quest-to-dummy-ROS-observer run, see [PICKNIK_HW_READY.md](PICKNIK_HW_READY.md)
and [MANUAL_REQUIRED.md](MANUAL_REQUIRED.md)). The Raspberry Pi is not a
physical robot and no finding from this testbed should be reported as
`ACTUAL_ROBOT` evidence.
