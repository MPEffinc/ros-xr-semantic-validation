# Source Ledger

All accessed 2026-09-29. "Where" = location of the evidence used. Local copies of PDFs are kept only
in the session scratchpad (not committed; `*.pdf` under `references/papers/` is git-ignored).

| ID | Source | URL | Version / revision | Level | Where evidence was taken |
|---|---|---|---|---|---|
| P1 | Adekoya, Sgorbissa, Recchiuto, HORUS | https://arxiv.org/abs/2506.02622 · https://arxiv.org/pdf/2506.02622v2 | v1 2025-06-03; v2 2026-06-05 | FULL TEXT VERIFIED | Sec. III-A p.3; Sec. V p.7 (future-work quote re-checked ✔) |
| P2 | Adekoya, Sgorbissa, Recchiuto, Multi-operator MR interface | https://arxiv.org/abs/2606.07013 · https://arxiv.org/pdf/2606.07013v1 | v1 2026-06-05 | FULL TEXT VERIFIED | Sec. III-E p.4 (re-checked ✔); Sec. IV p.4; Sec. V-A pp.5-6; Sec. VI p.8; ref [9] |
| P2b | Adekoya et al., HORUS: Architecture and Performance Characterization… (I-RIM 3D 2026) | `RICE-unige/horus` @ `819cdfdc` `papers/irim-2026/index.html`; `README.md:122` | web abstract only | NOT_VERIFIED (full text) | abstract mentions "bridge-enforced per-robot control leases" |
| P3 | ROS 2 design: Security Enclaves; DDS-Security; Access Control Policies | https://design.ros2.org/articles/ros2_security_enclaves.html · …/ros2_dds_security.html · …/ros2_access_control_policies.html | `ros2/design` gh-pages `93a415bf`; files last changed `12f61b14` (2021-10-01) | SOURCE_CONFIRMED | 182 L32-35, L45, L62-63, L114, L257-266; 180 L40, L56-57, L74, L122, L186-196; 181 L120-121, L326-331 |
| P4 | ROS 2 design: Actions | https://design.ros2.org/articles/actions.html | `articles/actions.md` last changed `2c1ff50a` | SOURCE_CONFIRMED | L58, L64, L98-100, L176-192, L205-206, L232, L240-256 |
| P4c | rcl / rclcpp (jazzy) | https://github.com/ros2/rcl · https://github.com/ros2/rclcpp | rcl `22c0b957`; rclcpp `2209942e` | SOURCE_CONFIRMED | `goal_handle.c` L25-33; `action_server.c` L791-, L850-855; `server.cpp` L512-523, L607-672; `server.hpp` L56-61, L439-450; `server_goal_handle.hpp` L244-252; `client.hpp` L658-669 (re-checked ✔) |
| P5 | Xia, Gao, Shi, Investigating Security Threats in Multi-Tenant ROS 2 Systems, ICRA 2025 | https://www.weisongshi.org/papers/xia25-ICRA.pdf · https://doi.org/10.1109/ICRA55743.2025.11127490 | author PDF (8 pp.) | FULL TEXT VERIFIED (author PDF; proceedings page mapping unchecked) | Sec. III-B p.2; Sec. IV-A-2 p.3; Sec. VI pp.5-6 |
| P6 | Seo et al., ROSec, IEEE T-ASE 22:10546-10559 | https://doi.org/10.1109/TASE.2024.3525050 (→ Xplore 10836890) | VoR (closed) | ABSTRACT+METADATA | Crossref metadata; abstract |
| P7 | Salimi, Keramat, Peña Queralta, Westerlund, JSA 168:103528 | https://doi.org/10.1016/j.sysarc.2025.103528 · preprint https://arxiv.org/abs/2308.16482 | VoR not accessible (403); preprint v1 2023-08-31 | FULL TEXT (PREPRINT) | preprint Sec. III-1 p.4; Alg. 1, Listing 1 p.5; Sec. IV p.7; Sec. V pp.7-8 |
| P8 | MoveIt 2 / moveit_servo | https://github.com/moveit/moveit2 | `a2117df217dc3620b6f1a5d2d150a20e40aa7c7c` | SOURCE_CONFIRMED | `servo_parameters.yaml` L102-107 (re-checked ✔); `servo_node.cpp` L114-155, L195-331, L369-447; `servo.cpp` L496-542, L664-689; `collision_monitor.cpp` L138-172; `common.cpp` L282-374 |
| P8t | MoveIt 2 tutorials, realtime servo | https://moveit.picknik.ai/main/doc/examples/realtime_servo/realtime_servo_tutorial.html | `moveit2_tutorials` main `e1b3727d` | SOURCE_CONFIRMED | `.rst` L40-41, L225-253 |
| P9 | RICE-unige/horus_ros2 | https://github.com/RICE-unige/horus_ros2 | `eca75cbf559f09ff793d8993338b2f1ffed1adfd` (2026-07-26) | SOURCE_CONFIRMED | see `../audit/HORUS_CODE_AUDIT.md` |
| P9b | RICE-unige/horus_sdk | https://github.com/RICE-unige/horus_sdk | `f4f00dab41910676519d545515531ec243414044` | SOURCE_CONFIRMED (grep) | no lease logic |
| P9c | RICE-unige/horus (release channel) | https://github.com/RICE-unige/horus | `819cdfdc74f1a0c2bd73946dc14897a533f68b61`; releases v0.0.1-beta, v0.2.0, v0.3.0 (APK only) | read | README L16-35, L84-91, L120-140 |
| P9d | RICE-unige/horus_connector | https://github.com/RICE-unige/horus_connector | `55933a98bb7ddf84bafcf93f1273847928e1a04e` | read | README; no lease client |
| N1 | Nav2 (jazzy) | https://github.com/ros-navigation/navigation2 | `645abd95f2be02a13ca539b29c2ddc065db34f89` | SOURCE_CONFIRMED | `simple_action_server.hpp` L146-215, L363-383 (re-checked ✔), L452-468; `bt_action_server_impl.hpp` L303-318; `navigate_to_pose.cpp` L196-224 |
| C1 | ros2_controllers | https://github.com/ros-controls/ros2_controllers | master `2520ae5b`; jazzy `1bc19b63` | SOURCE_CONFIRMED | diff_drive yaml L109-113, cpp L123-137, L440-464; JTC yaml L157-163, cpp L375-392, L1551-1613; forward_command_controller (no timeout) |
| R1 | Zong, Guo, Chen, Policy-based Access Control for Robotic Applications, SOSE 2019 | https://yaoguopku.github.io/papers/Zong-CCR-19.pdf · DOI 10.1109/SOSE.2019.00062 | author PDF | FULL TEXT VERIFIED | Sec. IV-D-3 p.372; p.373 |
| R2 | Mayoral-Vilches, White, Caiazza, Arguedas, SROS2, IROS 2022 | https://arxiv.org/abs/2208.02615 · DOI 10.1109/IROS47612.2022.9982129 | — | ABSTRACT+METADATA | — |
| R3 | Toris, Shue, Chernova, TePRA 2014 | https://doi.org/10.1109/TePRA.2014.6869141 | — | METADATA | — |
| R4 | Dieber et al., IROS 2016 | https://doi.org/10.1109/IROS.2016.7759659 | — | METADATA | — |
| R5 | Deng et al., On the (In)Security of Secure ROS2, CCS 2022 | https://doi.org/10.1145/3548606.3560681 | — | ABSTRACT | — |
| R6 | Desai et al., SOTER, DSN 2019 | https://doi.org/10.1109/DSN.2019.00027 | — | ABSTRACT | — |
| R7 | Yao, Zhao, Cheng, Chen, TAT, USENIX Security 2026 | https://www.usenix.org/system/files/usenixsecurity26-yao-chengtao.pdf | proceedings | FULL TEXT VERIFIED (lit pass) | Sec. 9 pp.3451-3452 |
| R8 | ros2/sros2 SROS2_Linux.md | https://github.com/ros2/sros2/blob/master/SROS2_Linux.md | `e92087a` (2026-09-25) | read | "Certificate Revocation Lists" section |
| R9 | Zhang & Zhang, arXiv:2607.23586 | https://arxiv.org/abs/2607.23586 | v1 2026-07-26 | ABSTRACT only | — |
| R10 | Gallo, arXiv:2607.08906 | https://arxiv.org/abs/2607.08906 | v1 2026-07-09 | ABSTRACT only | — |
| R11 | Baek et al., arXiv:2602.23694 | https://arxiv.org/abs/2602.23694 | v3 2026-05-31 | FULL TEXT (refs + citing sentence) | ref [23] |
| S1 | Semantic Scholar citations API | https://api.semanticscholar.org/graph/v1/paper/arXiv:2506.02622/citations · …/arXiv:2606.07013/citations · …/DOI:10.1109/icra55743.2025.11127490/citations | — | queried | P1: 2 results; P2: 0; P5: 7 |
| S2 | OpenAlex | https://api.openalex.org (W4415133925, W7163904033, W4413926271, W4406258620, W4413008806) | — | queried | cited_by lists |
| S3 | Google Scholar | — | — | NOT_VERIFIED (HTTP 403) | — |
| I1 | Archived internal reports (PRIOR_INTERNAL) | `../../Deprecated/AUTHORIZATION_CONTINUITY_RESULTS.md`, `…/XR2ACT_DECISIVE_RESULTS.md`, `…/RESEARCH_CONTEXT.md` | commit `e7799a7` | internal | §G collision table; §794-819 runtime results |

Search queries used for follow-up discovery (WebSearch + arXiv/S2/OpenAlex APIs): "multi-operator mixed
reality robot control lease security"; "control authority handover teleoperation security ROS 2";
"shared control authority revocation robot in-flight command stale goal after takeover"; "teleoperation
takeover authority transfer safety multi-operator arbitration"; "ROS 2 action goal preemption
authorization revoked lease robot security"; "\"control lease\" OR \"command lease\" robot teleoperation
multi-user security"; "authority revocation in-flight robot command stale authorization lease expiry ROS
navigation goal security"; DDS/SROS2 dynamic permissions / revocation without restart. Result: no verified
2019–2026 publication on revoking authority over already-accepted ROS 2 action goals or on multi-operator
XR lease-to-execution consistency. Absence of evidence under these searches, not proof of absence.
