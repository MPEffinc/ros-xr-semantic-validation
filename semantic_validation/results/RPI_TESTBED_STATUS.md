# Raspberry Pi Testbed Status

Session: 2026-09-02. This document records infrastructure/preflight state only.
It is not a semantic-validation finding and must not be cited as evidence in
[EVIDENCE_LEDGER.md](EVIDENCE_LEDGER.md) or [RESEARCH_DECISION.md](RESEARCH_DECISION.md).

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
- Post-reimage hostname will be **`rosxr-pi`** (not `worker1`), to avoid any
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

## Current Physical Topology

```text
Desktop (cclab, Ubuntu 24.04, x86_64)
  enp4s0  10.80.79.38/24  -- research LAN (also has an unrelated host
                              answering to mDNS name "worker1" -> 10.80.79.124,
                              NOT this Pi)
  wlx58...  192.168.0.3/24 -- "CCLAB 5G" Wi-Fi
  usb0    10.55.0.1/24  ---- USB gadget ---- usb0  10.55.0.2/24
                                                     |
                                          Raspberry Pi 4 (worker1,
                                          Ubuntu 20.04.5, aarch64)
                                          eth0   DOWN / NO-CARRIER
                                          wlan0  DOWN / NO-CARRIER

Quest 3: not connected this session.
```

Only the USB gadget link (`usb0` 10.55.0.1 <-> 10.55.0.2`) is currently functional
between Desktop and Pi. The dedicated-Ethernet path called for in the target
architecture is not physically established on the Pi side.

## Target Topology

```text
Meta Quest 3
   | Wi-Fi
   v
Linux Desktop
   XR application / XR-to-ROS interface / ROS 2
   |
   | dedicated Ethernet / DDS      (enp3s0f0 or enp3s0f1 -> Pi eth0)
   v
Raspberry Pi 4 (rosxr-pi)
   Ubuntu 22.04 / ROS 2 Humble
   |
   semantic_robot_sink / dummy robot controller
   X
   no physical robot/actuator

Desktop usb0 (10.55.0.1) <--USB gadget--> Pi usb0 (10.55.0.2)
   management/fallback SSH path only, not part of the ROS/DDS data plane
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
5. **Git repository is not actually initialized; GitHub CLI is not installed.** `.git/` is an empty directory (no `HEAD`/`objects`/`config`). `gh` is not installed (`gh: command not found`), so `gh auth status` cannot even run yet. `.gitignore` has been drafted and written (excludes vendored upstream clones under `frameworks/` and `semantic_validation/targets/`, the oversized raw `semantic_validation/logs/quest_hw/` captures — one file is 115MB, over GitHub's 100MB hard limit — build caches, and any credential-shaped files). Estimated trackable size after these exclusions: **~23MB** (from a 715MB working tree). `git init`, the first commit, `gh` installation/login, and GitHub repo creation all still need your explicit go-ahead before proceeding.

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
