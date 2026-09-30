# 01 — Topology and Observer Model (Stage 1)

Question: *can one realistic passive network observer see XR traffic and ROS traffic at the same time?*

Sources are marked: **S** = source/docs read at a pinned revision, **L** = lab facts from repository
records, **D** = our inference.

## 1. Systems examined

### S1 — Isaac ROS Teleop + CloudXR (primary candidate; documented topology, not runnable here)

Data path (S unless marked):

```
Quest/PICO browser (CloudXR.js) or Vision Pro
  │  Wi-Fi 5/6 GHz ("client or server may be wireless, but not both"; server wired)
  ▼
AP ──(wired LAN)──► workstation: CloudXR runtime + WSS proxy + IsaacTeleop retargeting
                       │  teleop_ros2_node (60 Hz fixed loop) → ROS 2 DDS
                       ▼
                    robot / robot computer (controller, cameras)
                       └─ optional camera "split mode": robot NVENC → RTP/UDP 5000+ → workstation ("wired networks only")
```

Evidence: CloudXR network setup (docs.nvidia.com/cloudxr-sdk/latest/requirement/network_setup.html, fetched
2026-09-30): web clients use TCP 49100 signalling, **UDP 47998 media**, TCP 48322 TLS proxy; server wired,
client on 5/6 GHz; 100 Mbps minimum, 200 Mbps recommended; 20–30 ms pose-to-frame target. IsaacTeleop
`docs/source/getting_started/quick_start.rst:185-218` (ports), `docs/source/references/cloudxr.rst:100-140`
(`--usb-local`: all XR traffic over USB), `docs/source/references/camera_streaming.rst:380-392` (split mode),
isaac_ros_teleop `launch/isaac_ros_teleop.launch.py:78-82` (`rate_hz` 60).

| Flow | Source → destination | Protocol / port | Encrypted on the wire | Rate / bandwidth | Latency sensitivity |
|---|---|---|---|---|---|
| F1 XR media (video down) | workstation → headset | UDP 47998 (CloudXR) | CloudXR stream encryption: NOT_VERIFIED (only the TLS signalling path is documented) | ~100–200 Mbps, frame-paced | 20–30 ms pose-to-frame |
| F2 XR pose/input (up) | headset → workstation | CloudXR media channel (same UDP port; separable by direction/size — D) | as F1 | display-rate periodic (D) | same |
| F3 signalling | headset ↔ workstation | TCP 49100 / 48322 TLS | TLS on 48322 | low | session setup |
| F4 ROS command | workstation → robot | DDS/RTPS UDP (7400+ range) | plaintext unless SROS2 is deployed | fixed 60 Hz loop, fixed-size messages for fixed joint sets (NamedPoseArray, JointState: S) | control loop |
| F5 ROS feedback (state) | robot → workstation | DDS/RTPS UDP | as F4 | robot-driver rate (not in repo) | control loop |
| F6 robot camera (split mode) | robot → workstation | RTP/UDP 5000+ | not documented as encrypted | per-camera fps | teleop view |

### S2 — Lab testbed: Spes WebXR → ROS 2 → Raspberry Pi (real Quest used 2026-08-30/31, 09-17)

```
Quest 3 (192.168.0.178, Quest Browser WebXR)
  │  Wi-Fi "CCLAB 5G", HTTPS/WSS TLS :4443
  ▼
desktop wlx588694f02e61 192.168.0.3 — Spes server + upstream ROS 2 node
  │  dedicated Ethernet enp3s0f1 10.10.10.1 ↔ 10.10.10.2, DDS
  ▼
Raspberry Pi 4 (Humble) semantic_robot_sink (no robot)
```

(L: `Deprecated/TESTBED_CONTEXT.md`, `Deprecated/semantic_validation/results/SPES_QUEST_NATIVE_ROS_FEASIBILITY_20260917.md`.)
There is no media flow to the headset (WebXR renders locally), so only F2 and F4 exist.
**XR (Wi-Fi) and ROS (dedicated wire) never share a link.**

### S3 — Quest2ROS2 (second stack, as required by the gate rule)

Quest app → **plaintext** ROS-TCP (`ros_tcp_endpoint@54c1a64` `server.py:52, 95-100`: raw TCP socket, port
10000, no TLS) over Wi-Fi → endpoint on the desktop → DDS to the robot. Content is readable on the wire, so
traffic analysis is unnecessary against the default deployment. Protecting it requires adding a tunnel
(e.g. WireGuard) — then F2 becomes one encrypted tunnel on Wi-Fi, and F4/F5 stay wherever the robot link is.

## 2. Observer positions and what each sees

| Observer | Realistic authority | S1 flat LAN, robot wired to same switch | S1 robot on the same Wi-Fi (mobile robot) | S1 robot on dedicated link | S2 (lab) |
|---|---|---|---|---|---|
| O1 passive Wi-Fi sniffer (monitor mode, no network credentials) | any nearby radio; sees 802.11 frame sizes, timing, MAC addresses even under WPA2/3 | F1–F3 only | **F1–F5** (both stations on the channel) | F1–F3 only | F2 only |
| O2 compromised / mirrored switch or gateway on the LAN | in-network, privileged but common in threat models | **F1–F5** (AP uplink and robot port cross the switch) | F1–F5 (AP uplink) | F1–F3 only | F2 only (Pi on a direct cable) |
| O3 compromised AP | in-network | F1–F3 (+ robot if wireless) | **F1–F5** | F1–F3 | F2 |
| O4 VPN/tunnel endpoint outside | sees only the tunnel | one aggregate flow | one aggregate flow | — | — |
| O5 workstation host NIC | root on the host | everything **in plaintext** — not a traffic-analysis adversary | same | same | same |
| O6 two colluding observers (Wi-Fi + robot link) | two positions | F1–F5 | — | F1–F6 | F2 + F4 |

**Excluded as unrealistic for this question:** O5 (with host access the adversary reads the data directly);
O6 is a stronger, two-position adversary — the classic end-to-end flow-correlation setting — and is recorded
but not used as the main model.

## 3. Gate 1

| System | Single realistic observer seeing ≥2 heterogeneous XR + ROS flows? |
|---|---|
| S1 flat LAN or robot on the same Wi-Fi | **yes** — O1 (robot on Wi-Fi) or O2/O3 |
| S1 robot on a dedicated link / camera split mode on a separate wire | no (only O5/O6) |
| S1 `--usb-local` | no (XR traffic not on the network) |
| S2 lab testbed | **no** — XR on Wi-Fi, DDS on a dedicated cable |
| S3 Quest2ROS2 default | moot — plaintext; with a tunnel, same as S1 depending on robot link |

**GATE 1: CONDITIONAL PASS.** A single passive observer can see XR and ROS flows together only in
deployments where the robot's ROS link crosses the same switch/AP as the headset, or the robot is on the
same Wi-Fi channel. That topology is plausible (mobile robots on Wi-Fi; one flat lab LAN) and permitted by
CloudXR's rule "server wired, client wireless". It does **not** hold in this lab's own testbed (S2), where
the two traffic classes are on separate links.

Consequences carried forward:
1. Every later result applies only to the shared-segment deployment.
2. In the shared-segment case the adversary also sees *which* device sends what (MAC/IP), so flow
   separation is trivial; "cross-flow" means correlating headset↔workstation flows with workstation↔robot flows.
3. An obvious existing mitigation in the same deployment is topology itself (dedicated robot link, as in S2)
   or a single tunnel from the workstation; both are recorded as existing defenses for Stage 5.

Machine-readable form: `../configs/topology.yaml`; diagram: `../figures/topology.md`.
