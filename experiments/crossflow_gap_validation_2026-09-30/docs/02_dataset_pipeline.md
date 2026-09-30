# 02 — Dataset Pipeline (Stage 2)

## 1. Outcome

**A real, task-labelled, synchronized XR + ROS traffic dataset cannot be collected in this environment,
and no existing dataset provides one.** The capture/preprocess/manifest pipeline was built and validated on
real ROS 2 DDS traffic (pipeline test only). No dataset for Stages 3–6 exists.

Reasons (all checked):

| Requirement | Status | Evidence |
|---|---|---|
| XR media + input traffic of the Gate-1 system (S1, CloudXR) | impossible here | CloudXR server GPUs: L40/L40S, RTX Pro Blackwell, RTX 5000/6000, RTX 5090/5080/4090 (NVIDIA runtime requirements page, fetched 2026-09-30); host GPU GTX 1050 Ti |
| a physical headset + human operator performing labelled tasks | not available autonomously | `adb devices` empty on 2026-09-30; a Quest 3 exists in the lab (used 2026-08-30/31, 09-17) but needs an operator |
| the only real encrypted XR→ROS chain in the lab (S2, Spes WebXR → DDS → Pi) | fails Gate 1 as deployed and has **no XR media flow** | `01_topology_and_threat_model.md` §1–3 |
| existing real recordings | application-level receive times, not packets; no task labels | `00_asset_inventory.md` §1 |
| public datasets | single-domain only: robot traffic (Tang et al., Zenodo 10.5281/zenodo.15007304, 7.4 GB) and VR traffic (Questset, Quest 2 over Quest Link) | `../literature/defense_baselines.md` (P2, P7) |

Pairing an independent robot dataset with an independent VR dataset would *fabricate* the very cross-flow
relation under test, so it is not done. Synthetic traffic is not used to decide anything (README rule).

## 2. Pipeline built (for any future real session)

| Script | Function | Validated |
|---|---|---|
| `scripts/Dockerfile.capture`, `scripts/capture_flows.sh` | tcpdump sidecar joins a container's network namespace (`--net container:<id>`, NET_RAW) — no host root needed; pcap written outside Git (`results/raw/`, git-ignored) | yes |
| `scripts/preprocess_pcap.py` | dependency-free libpcap parser → per-packet CSV (ts, wire length, 5-tuple flow key, direction); EN10MB / SLL / SLL2 | yes |
| `scripts/make_manifest.py` | appends trial/task/session/operator/raw path/size/sha256/capture point/network condition/provenance to `manifests/dataset_manifest.csv` | yes |

**Pipeline test** (`manifests/dataset_manifest.csv`, row `pipeline_test_001`, provenance `PIPELINE_TEST`):
two `ros:humble-ros-base` containers on a Docker bridge, `ros2 topic pub -r 10 /chatter` → `ros2 topic echo`;
8 s sidecar capture on the listener: 104 packets captured, 92 IPv4 parsed; the data flow
`udp 172.18.0.2:7411 → 172.18.0.3` carried 70 packets, all 170 bytes (constant content → constant size);
SPDP multicast to 239.255.0.1:7400 separated as its own flow. sha256 of the pcap:
`2435badfad51a5ce59ad558e0f40c9af03c1afc87e12004cc2962103561ca684`. This confirms only that capture,
flow separation and hashing work. It is not task data.

## 3. Protocol a real session would have to follow (not executed)

- **System/topology:** S1 cannot run; the feasible real option is S2 re-deployed so that the ROS link
  shares the Wi-Fi/switch with the headset (e.g. Pi DDS moved onto the Wi-Fi), since the deployed S2 fails
  Gate 1. S2 has no media flow, so hypothesis flows A (XR media) cannot be tested at all.
- **Tasks:** idle, reach, grasp, move-left/right, rotate, pick-and-place; one application run for all tasks
  (no restarts, same ports) so labels are not exposed by session structure.
- **Per trial:** pcap at the shared observer point, operator marker file, task label, session ID, operator ID,
  network condition, trial ID; clock sync by chrony on both hosts plus an in-band marker packet.
- **Splits:** session-separated and operator-separated test sets; no execution sequence in both train and test.

## 4. Consequence for later stages

Stages 3, 4 and 6 need real paired traffic and are **NOT_RUN** for lack of data. Stage 5 (existing
defenses) is done from literature and analysis, which — as Stage 5 shows — is sufficient to decide whether a
methodology gap can exist at all.
