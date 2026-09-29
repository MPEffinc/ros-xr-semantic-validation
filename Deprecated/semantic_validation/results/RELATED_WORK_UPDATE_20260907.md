# Related-work update — 2026-09-07

This update separates papers that evaluate teleoperation performance from the present question:
whether loss/source/time/session semantics remain distinguishable, or are equivalently
revalidated/gated, across a concrete XR-to-control chain.

| Work | Identity and tested scope | Method / useful overlap | Limit relative to this RQ |
| --- | --- | --- | --- |
| RoboFuzz | Kim et al., *RoboFuzz: Fuzzing Robotic Systems over ROS for Finding Correctness Bugs*, 2022, [PDF](https://gts3.org/assets/papers/2022/kim:robofuzz.pdf) | ROS graph input fuzzing for correctness bugs | Does not give a native XR validity/source-time contract or compare XR implementations |
| Caldas et al. | Ricardo Caldas et al., *Runtime Verification and Field-based Testing for ROS-based Robotic Systems*, IEEE TSE 2024, [DOI](https://doi.org/10.1109/TSE.2024.3444697), [preprint](https://arxiv.org/abs/2404.11498) | literature/repository study plus questionnaires produces field-test and RV guidance | motivates explicit observables and deployment evidence, but is not XR-input semantic conformance |
| TeleXR | Ziliang Zhang, Cong Liu, Hyoseung Kim, *Understanding and Mitigating Network Latency Effect on Teleoperated-Robot with Extended Reality*, 2025, [arXiv:2506.01135](https://arxiv.org/abs/2506.01135) | evaluates latency mitigation and reconstruction for XR teleoperation | network delay/loss is not proof that raw tracking invalidation/source identity is preserved or revalidated downstream |
| XRoboToolkit | Zhigen Zhao, Liuchuan Yu, Ke Jing, Ning Yang, *XRoboToolkit: A Cross-Platform Framework for Robot Teleoperation*, 2025/2026, [arXiv:2508.00097](https://arxiv.org/abs/2508.00097) | OpenXR modular toolkit, multiple modalities/platforms and task demonstrations | this checkout's native vendor source remains opaque; toolkit coverage does not establish cross-implementation semantic behavior |
| Quest2ROS2 | Jialong Li, Zhenguo Wang, Tianci Wang, Maj Stenmark, Volker Krueger, *Quest2ROS2: A ROS 2 Framework for Bi-manual VR Teleoperation*, HRI 2026, [arXiv:2601.18289](https://arxiv.org/abs/2601.18289) | relative-motion control, pause/reset, RViz and gripper workflow | close architectural baseline, but paper-level features do not resolve exact loss/recovery behavior at a native XR transition |

## Novelty and threat boundary

The plausible contribution is **not** a claim that any stack is unsafe.  It is a repeatable,
cross-architecture method that binds native raw transitions to their source decision, serialized
representation, transport/bridge, ROS observation, and—where safely available—an inert substitute
at the native consumer boundary.  This overlaps ROS testing and XR teleoperation studies, so the
study must retain their limitations: only actual Quest traces can answer RQ3; post-gate synthetic
injection is `BOUNDARY_LIMITED_REPLAY`; and a Pi receiver is transport observation only.
