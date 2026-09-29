# Source Ledger

Checked 2026-09-30. `FULL` = body text read; `ABSTRACT` = abstract / landing / search snippet only;
`CODE` = source read at a pinned SHA. arXiv metadata from the arXiv API (`export.arxiv.org/api/query`).
Local copies of fetched texts: `references/papers/` (git-ignored); SHA-256 of the text files:
`references/papers_sha256.txt`.

## A. Items listed in the brief

| # | Item as given | Resolves? | Actual identity | Version / date | Status / venue | Read |
|---|---|---|---|---|---|---|
| 1 | NVIDIA Isaac ROS Teleop, github.com/NVIDIA-ISAAC-ROS/isaac_ros_teleop | yes | ROS 2 wrapper (`teleop_ros2_node` from IsaacTeleop + `pose_reset_node`) | `main@e80602863a0c4c94360a22b02248164c2dad6fa4` (2026-09-21); IsaacTeleop gitlink `de761a036a0e7188409c0741de861fe691c7b739` (release/1.4.x) | software, no paper found | CODE |
| 2 | NVIDIA Isaac Teleop, github.com/NVIDIA/IsaacTeleop | yes | XR device I/O, retargeting, CloudXR, MCAP record/replay; Python package `isaaccapture` (alias `isaacteleop`) | `main@47f33af3cc50d01bc3d60f51d17ef0a480fa0969` (2026-09-29) | software, no paper found | CODE |
| 3 | Isaac Lab docs, isaac-sim.github.io/IsaacLab | yes | + paper arXiv 2511.04831 "Isaac Lab: A GPU-Accelerated Simulation Framework for Multi-Modal Robot Learning" (NVIDIA, Mittal, Roth, et al.) | code `main@5eef1d70f3c7f3af1e1c99eae85192b61cda52ac` (2026-09-29); paper v1 2025-11-06 | arXiv preprint | CODE + FULL |
| 4 | XRoboToolkit, github.com/XR-Robotics/XRoboToolkit-Teleop-Sample-Python | yes | + paper arXiv 2508.00097 "XRoboToolkit: A Cross-Platform Framework for Robot Teleoperation" (Zhao, Yu, Jing, Yang) | code `main@79e5cb8a56e3455515ce1b476e993c764ec58739` (2025-12-31); paper v2 2025-11-05 | accepted, IEEE/SICE SII 2026 (arXiv comment) | CODE + FULL |
| 5 | BadVLA, NeurIPS 2025 | yes | arXiv 2505.16640 "BadVLA: Towards Backdoor Attacks on Vision-Language-Action Models via Objective-Decoupled Optimization" (Zhou, Tie, Zhang, et al.) | v1 2025-05-22 | NeurIPS 2025 poster (neurips.cc/virtual/2025/poster/115803; OpenReview rEhVHla9zp) | FULL (arXiv v1 + camera-ready) |
| 6 | State Backdoor, arxiv.org/abs/2601.04266 | yes, title matches | "State Backdoor: Towards Stealthy Real-world Poisoning Attack on Vision-Language-Action Model in State Space" (Guo, Jiang, Lin, et al.) | v1 2026-01-07, v2 2026-06-08 | arXiv preprint | FULL |
| 7 | arxiv.org/abs/2609.26868 | yes, title matches | "Backdoors in Learning-Based Industrial Robotic Arm Manipulation: An Empirical Security Study" (Zhang, Zeng, Gu, Pisharody) | v1 2026-09-22 | IROS 2026 Workshop on Industrial Applications of Robot Learning (arXiv comment) | FULL |
| 8 | RoboCurate, arxiv.org/abs/2602.18742 | yes, title matches | "RoboCurate: Harnessing Diversity with Action-Verified Neural Trajectory for Robot Learning" (Kim, Jang, Yoon, et al.) | v1 2026-02-21 | arXiv preprint | FULL |
| 9 | SoK, arxiv.org/abs/2606.16788 | yes, title matches | "SoK: Security and Privacy of Foundation-Model-Powered Robots" (Gong, Chen, Liu, et al.) | v1 2026-06-15 | arXiv preprint | FULL |
| 10 | arxiv.org/abs/2608.16843 | yes; full title longer | "Security of Foundation-Model-Powered Embodied Agents: Attack Surfaces, Attacks, Defenses, and Evaluation" (Liu, Guo, Zhang, et al.) | v1 2026-08-17 | arXiv preprint | FULL |

No listed link was wrong. Found while verifying: XRoboToolKit-T, arXiv 2609.16437 (v1 2026-09-14), FULL;
NVIDIA Isaac Sim paper arXiv 2606.03551 (metadata only, not used).

## B. Broader search (existence verified via arXiv API unless noted)

| Area | Source | Id / URL | Status | Read |
|---|---|---|---|---|
| Poisoning | Dataset Poisoning Attacks on Behavioral Cloning Policies | 2511.20992 | EAI SmartSP 2025 | FULL |
| Poisoning | DropVLA: An Action-Level Backdoor Attack on VLA Models | 2510.10932 (v5) | IROS 2026 | FULL |
| Poisoning | SilentDrift: Exploiting Action Chunking for Stealthy Backdoor Attacks on VLA Models | 2601.14323 (v2) | Findings of ACL 2026 | FULL |
| Poisoning | !Imperio, smolVLA: The Implications of Data Poisoning on Open Source Robotics | 2607.04146 | KI 2026 | FULL |
| Poisoning | Targeting World Models to Compromise Robot Learning Pipelines | 2606.09499 | CoRL preprint | FULL |
| Poisoning | TrojanRobot 2411.11683; GoBA 2510.09269; VLA safety survey 2604.23775 | — | — | search snippet only (not used) |
| Curation | CUPID 2506.19121; DemInf 2502.08623; Demo-SCORE 2503.03707 | — | CoRL 2025 (not verified); —; RSS 2025 | FULL |
| Curation | DataMIL 2505.09603; Lee et al. "Quality over Quantity" 2603.09056 | — | ICLR 2026; ICRA 2026 | ABSTRACT |
| Runtime defense | "When Attention Betrays" (Bera) 2602.03153 | — | preprint | FULL |
| Noisy demos | DMDR 2510.14467; Mind the Gap 2602.08776 (v2, CoRL); RIL-Co 2010.10181 | — | — | FULL; FULL; ABSTRACT |
| Tooling | LeRobot paper 2602.22818 + code `lerobot@e0d50211ef236143ae867228662b7dfaba554f02` | github.com/huggingface/lerobot | — | FULL + CODE |
| Tooling | RDA (Robot Data Audit) | github.com/liesliy/rda | tool | FULL (README/blog) |
| Tooling | demosift | github.com/christophe17/demosift | tool | FULL (README) |
| Dataset | DROID 2403.12945 | — | RSS 2024 | ABSTRACT |
| Provenance | VAMP 2105.10051; Replicable sim-based validation 2605.29973 | — | 2021; ERAS 2026 | ABSTRACT |
| Sync | UMI 2402.10329 | — | RSS 2024 | FULL |
| Replay | robomimic `playback_dataset.py` (master, 2026-09-30); robosuite demonstrations doc; MimicGen (PMLR v229) | — | — | CODE/FULL; FULL; ABSTRACT + code grep |
| XR teleop | Learning to Stack from VR demos 2609.19040 (NAECON 2026); Open-TeleVision 2407.01512; Bunny-VisionPro 2407.03162; DexCap 2403.07788; ARCap 2410.08464; VR-DAgger 2605.27114 | — | — | FULL |
| XR teleop | AnyTeleop 2307.04577 | — | RSS 2023 | ABSTRACT |
| ROS logging | MCAP spec (mcap.dev/spec); rosbag2 source `7aac3bd0` (2026-09-28) | — | — | FULL / CODE grep |
| ROS logging | Black Block Recorder (White et al., IEEE RA-L 2019) ieeexplore 8764004 | — | RA-L 2019 | ABSTRACT (PDF not retrievable) |
| ROS logging | Fabric blockchain–ROS 2 teleop 2304.00781 | — | 2023 | ABSTRACT |
| Phone XR + ROS 2 | Phone2Act 2605.01948 | — | preprint | code only (see SYSTEM_INVENTORY) |

## C. Code repositories surveyed for ROS 2 demonstration recorders (HEAD on 2026-09-30)

Recorded in `systems/SYSTEM_INVENTORY.md` §3 with SHAs.

## D. Not verified

- Venues marked "not verified" above; DROID quality-control details; Black Block Recorder full text.
- Forward citations (who cites each paper).
