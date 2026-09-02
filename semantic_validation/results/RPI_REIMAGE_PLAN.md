# Raspberry Pi Reimage Plan

This is a plan only. No reimage has been performed automatically — the SD
card/OS reinstall is a physical/user action per project rules (no OS
reinstall without the user doing it directly).

## Why

Current Pi (`worker1`) runs Ubuntu 20.04.5 LTS (focal), which does not match
the research compatibility target (Ubuntu 22.04 LTS ARM64 + ROS 2 Humble,
matching Quest2ROS2's own target and the rest of the harness). No research
data exists on the current SD card (confirmed empty home directory, no
`ros_xr`/`semantic` workspace found) — see
[RPI_TESTBED_STATUS.md](RPI_TESTBED_STATUS.md).

## Target configuration

| Item | Value |
| --- | --- |
| Hardware | Raspberry Pi 4 Model B |
| OS image | Ubuntu Server 22.04 LTS, 64-bit ARM (arm64) |
| Hostname | `rosxr-pi` (changed from `worker1` — avoids the mDNS collision with an unrelated `worker1.local` device already observed on the research LAN) |
| User | `cclab` |
| SSH | enabled at first boot (via Raspberry Pi Imager's OS customization, or cloud-init `user-data`) |
| Wired networking | enabled, DHCP by default (static assignment decided later, see Networking below) |
| Wi-Fi | optional, not required for the testbed |
| ROS 2 | Humble — installed **after** first boot verification, not part of the image itself |

## Recommended imaging method

Raspberry Pi Imager (`rpi-imager`) supports Ubuntu Server 22.04 LTS (arm64)
directly and has a built-in "Edit Settings" step that can pre-configure:

- hostname (`rosxr-pi`)
- username/password or SSH public key for `cclab`
- enable SSH (public-key only recommended — reuse the existing
  `~/.ssh/id_ed25519_worker1.pub` or generate a fresh key for the reimaged
  host, user's choice)
- locale/timezone

This avoids a manual first-boot login entirely and lets SSH work immediately
on first boot over whichever network path comes up (see Networking below).

## Networking after reimage

- **USB gadget path (management fallback):** if the current `g_ether`/USB
  gadget configuration is baked into the base image or re-applied after
  imaging, `usb0` should come back at `10.55.0.2/24` reachable from the
  Desktop's `10.55.0.1`. If it does not persist automatically, this is a
  manual USB-gadget re-setup step separate from ROS/DDS networking (out of
  scope for this plan — SSH over a directly-connected wired port is the
  simpler first path).
- **Dedicated Ethernet (ROS/DDS data plane):** connect the Pi's `eth0` port
  directly to one of the Desktop's two currently **unused** onboard Ethernet
  ports — `enp3s0f0` or `enp3s0f1` (Intel 82576 Gigabit, confirmed
  `DOWN`/`NO-CARRIER`, not part of the research LAN). This avoids the shared
  research LAN entirely (where the `worker1.local` mDNS collision was found)
  and needs no new USB-Ethernet adapter, since a second onboard NIC port is
  already free. Static IPs for this link (proposed, not yet applied):
  `10.10.10.1/24` on the Desktop side, `10.10.10.2/24` on the Pi side, no
  default gateway on either end of this link.

## Minimal post-reimage verification (for the user to run)

After first boot, from the Desktop:

```bash
# If SSH key was pre-provisioned during imaging:
ssh cclab@rosxr-pi.local 'hostname; lsb_release -a; uname -m; uptime'

# Or via a directly-known IP if mDNS is not yet resolved:
ssh cclab@<pi-ip> 'hostname; lsb_release -a; uname -m; uptime'
```

Expected output:

```text
rosxr-pi
Ubuntu 22.04.x LTS
aarch64
```

Then confirm storage and network baseline:

```bash
ssh cclab@rosxr-pi.local 'df -h /; ip -br addr; ip -br link'
```

## ROS 2 Humble install (after verification, not part of imaging)

Two options, to decide once the OS is confirmed:

1. **Native apt install** (`ros-humble-ros-base` per the official
   `packages.ros.org` apt repo for Jammy arm64) — matches "robot-side SBC"
   realism most closely.
2. **Docker container**, reusing the same `ros_env/Dockerfile` approach as
   the Desktop, if native install has any arm64-specific friction — keeps
   Desktop and Pi ROS environments consistent.

Neither is performed by this plan; both require the OS to be confirmed
working first, and the native option needs no `sudo`-restricted step beyond
what the user already controls on their own freshly-imaged Pi.

## Explicitly out of scope for this reimage

- No physical robot, actuator, motor driver, or gripper is connected at any
  point.
- No Docker group/permission change is planned on the Pi — irrelevant once
  reimaged, and not needed for a native ROS 2 install.
- No firewall/security policy changes.
- No Wi-Fi credential provisioning (optional, user's discretion only if
  ever needed as a fallback path).
