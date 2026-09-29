# Raspberry Pi Reimage Result

Actual observed results of the reimage described in
[RPI_REIMAGE_PLAN.md](RPI_REIMAGE_PLAN.md). This is infrastructure/preflight
record, not a semantic-validation finding.

## Target identification and safety verification

Performed 2026-09-02, on the Desktop (`cclab`, Ubuntu 24.04.3).

| Check | Result |
| --- | --- |
| Device | `/dev/sdb`, exposed by a USB card reader (`usb 2-1.3`, VID/PID `0bda:0306`, "Generic USB3.0-CRW") |
| Model / Size | `SD/MMC/MS/MSPRO`, 29.8G (32.0 GB, 62,521,344 × 512-byte blocks) |
| Transport / removable | `usb`, `RM=1` |
| Root disk comparison | Desktop root is `/dev/nvme0n1` (internal NVMe, `TRAN=nvme`, `RM=0`) — confirmed different device |
| `/boot`, `/boot/efi`, `/home/cclab/ros_xr` disk | all on `/dev/nvme0n1` — confirmed different device |
| Candidate count | exactly one with media present (`/dev/sda` on the same reader was a second, empty slot — 0 bytes, no partitions, not used) |
| **Positive identity match** | `sdb1` (vfat) UUID `5D5B-8026` and `sdb2` (ext4) UUID `a7c221ca-e02d-4446-8229-6c6cbd888234`, label `writable`, matched **exactly** the filesystem UUIDs observed earlier this session over SSH on the live Pi (`worker1`, `mmcblk0p1`/`mmcblk0p2`) — confirming this is the same physical SD card, not a guess |

Safety result: **all conditions met, exactly one candidate, cross-verified by filesystem UUID — proceeded.**

## Image

| Item | Value |
| --- | --- |
| Ubuntu version | 22.04.5 LTS |
| Architecture | arm64 (Raspberry Pi preinstalled server image) |
| Filename | `ubuntu-22.04.5-preinstalled-server-arm64+raspi.img.xz` |
| Source | `https://cdimage.ubuntu.com/releases/22.04/release/` (official, no mirror/third party) |
| SHA256SUMS source | same official directory |
| SHA256 (expected) | `fd7687c5c9422a6c7ba4717c227bf6473fe4e0c954d5a9f664201dcecc63e822` |
| SHA256 (downloaded file, verified) | matched — **SHA256 verification: PASS** |
| Local cache | `/home/cclab/ros_xr/.cache/rpi-image/` (git-ignored, not committed) |

## Flash

- Method: `xzcat <image> | pkexec bash -c 'dd of=/dev/sdb bs=4M status=progress conv=fsync'`, followed by `pkexec sync`.
- **Privilege escalation method:** `pkexec` (PolicyKit), which opened a native graphical authentication dialog on the user's own desktop session (Wayland/GNOME, `polkitd` active). The user entered their password directly into that system dialog — it was never seen, requested, or handled by the assistant, and no password was stored anywhere. Plain non-interactive `sudo` was tried first and failed cleanly (`sudo: a password is required`, no partial write) before this method was used.
- Bytes written: 4,683,988,992 (4.7 GB, matches image size). `dd` exit code `0`; `sync` exit code `0`.
- Post-flash `partprobe /dev/sdb` (also via `pkexec`) re-read the partition table.
- Result partitions: `sdb1` vfat `system-boot` (512M, new UUID `9FBA-406B`), `sdb2` ext4 `writable` (3.8G pre-growth, new UUID `f7380f37-4684-4f77-abe0-219400572e43`) — both fresh, distinct from the old card's filesystem UUIDs, confirming the write took effect.

## First-boot configuration (cloud-init)

Mounted `/dev/sdb1` at user level via `udisksctl mount` (**no root needed** — desktop udisks policy permits the logged-in user to mount their own removable media). Read the stock Ubuntu cloud-init defaults first, then edited in place (not arbitrary new files):

- `user-data`: hostname `rosxr`; single user `cclab` (groups matched to the previous Pi's actual group memberships observed over SSH: `adm,sudo,dialout,cdrom,audio,video,plugdev,games,users,input,render,netdev,gpio,i2c,spi`), `lock_passwd: true` (no password ever set), `sudo: ALL=(ALL) NOPASSWD:ALL`, single `ssh_authorized_keys` entry reusing the Desktop's existing `~/.ssh/id_ed25519_worker1.pub` (already the dedicated key for this physical Pi). `ssh_pwauth: false` (unchanged from stock default) — key-only login. The stock default `ubuntu`/`ubuntu` password user block was replaced entirely, so that account is not created.
- `network-config`: `eth0` set to static `10.10.10.2/24`, `dhcp4: false`, no gateway, `optional: true` (boot does not block if the cable isn't connected yet). This matches the approved dedicated-Ethernet plan directly — no separate DHCP/USB-gadget bootstrap step is needed for first SSH access, as long as the Desktop side (`enp3s0f0` → `10.10.10.1/24`) is configured before/around the same time.
- Both files passed a YAML syntax check (`python3 -c "import yaml; yaml.safe_load(...)"`) before unmounting.
- `meta-data` left unchanged (`dsmode: local`, fixed `instance_id: cloud-image` — fine for a never-yet-booted card).
- `config.txt`, `cmdline.txt`, kernel/dtb/firmware files: **untouched**.

`/dev/sdb1` unmounted cleanly afterward (`udisksctl unmount`). `/dev/sdb2` (`writable`) was never mounted or modified by this process — first boot will initialize it as-is from the image.

## Git

This result and the docs it updates
(`TESTBED_CONTEXT.md`, `RPI_TESTBED_STATUS.md`) are left uncommitted, to be
folded into the "Pi/Network baseline" milestone commit once first boot and
network bring-up are verified, per the session's commit policy (no commits
on every small edit).

## Not yet verified

- Actual first boot on Pi hardware (pending physical re-insertion and power-on).
- Whether `hostname: rosxr` and the static `eth0` address actually apply as
  configured (cloud-init `user-data`/`network-config` correctness is a
  strong signal, not a guarantee, until observed on the real device).
- SSH reachability at `10.10.10.2` once the Desktop's `enp3s0f0` is also
  configured to `10.10.10.1/24` and the dedicated cable is connected.
