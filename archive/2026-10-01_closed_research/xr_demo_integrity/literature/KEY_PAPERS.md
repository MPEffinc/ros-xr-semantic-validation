# Key Papers

Literature cut-off: **2026-09-30**. Scope: XR teleoperation → demonstration collection → dataset → policy
learning → autonomous execution, with emphasis on work that may *already solve* the candidate problem.

## How this file was produced (provenance of the text)

- Full texts of the listed arXiv items were downloaded (arXiv HTML → text, bibliography in HTML) into the
  local, git-ignored `references/papers/` scratch area on 2026-09-30. Per-paper extraction (Part A, Part B)
  was drafted by research-assistant agents working only from those texts / fetched pages, and every entry
  carries its own read level (`FULL` = body read, `ABSTRACT` = abstract or landing page only).
- Spot checks done by hand before commit (grep in the local texts): State Backdoor §VIII signature sentence
  (`2601.04266` text line 1413 — it concerns *model* provenance/watermark, not dataset signing); 2609.26868
  use of "teleoperation demonstrations" (§II/§III, text lines 120, 187); SoK Limitation 4 and OP7 provenance
  sentences (text lines 1122, 1139, 1179); arXiv API existence/titles of all 17 arXiv IDs cited below.
- Evidence labels: statements about what a paper says are `SOURCE_CONFIRMED` (paper text) or
  `AUTHOR_STATED_LIMITATION`; any interpretation by us is marked `DERIVED_HYPOTHESIS`.

## Synthesis (our reading; DERIVED_HYPOTHESIS unless marked)

1. **Demonstration poisoning is established prior art.** Small edits to recorded demonstrations implant
   backdoors in IL/VLA policies: action relabelling (DropVLA 2510.10932, 0.31 % of episodes; !Imperio
   2607.04146 on LeRobot/smolVLA), smooth action drift that the authors say passes human replay, jerk and
   loss-curve checks (SilentDrift 2601.14323, 2 %), state-space triggers with opposite-action labels on a real
   SO-101 (State Backdoor 2601.04266, 10 %), physical-trigger + action-segment edits on *teleoperation*
   demonstrations (2609.26868), observation poisoning of BC (2511.20992), and a teleop-provider attack via
   world models (2606.09499). BadVLA (NeurIPS 2025) keeps labels clean and attacks training. **A claim "a
   component that can edit part of a demonstration can backdoor the policy" is therefore not new**
   (SOURCE_CONFIRMED for each paper's own claims).
2. **All of these attackers act on a finished dataset or on training**, i.e. they assume dataset write access
   (data provider / hub uploader). None places the attacker inside the XR tracking → retargeting → recorder
   path, and none uses XR- or ROS-specific mechanisms (SOURCE_CONFIRMED by reading their threat models; see
   Part A §b and Part B §1).
3. **Existing detection/curation** (CUPID, DemInf, Demo-SCORE, DataMIL, Lee et al., DMDR, RDA, demosift,
   robomimic/robosuite playback, Isaac Lab `replay_demos`, RoboCurate's action-verification by sim replay) is
   evaluated on benign quality defects; none is evaluated against the published poisoning attacks above.
   RoboCurate is the closest *action-vs-video* consistency check, but targets synthetic data errors.
4. **Provenance** is raised only as an open problem (SoK Limitation 4 / OP7; 2608.16843 §5.6, §10.2–10.3).
   ROS-level signed logging exists (Black Block Recorder, RA-L 2019, abstract only), MCAP/rosbag2 have CRC32
   only, LeRobot relies on the Hub git revision (SOURCE_CONFIRMED in source, see `systems/SOURCE_AUDIT.md`).
5. **XR teleop systems** (XRoboToolkit, Open-TeleVision, Bunny-VisionPro, ARCap, VR-DAgger, DexCap,
   AnyTeleop) acknowledge benign tracking/retargeting errors and handle some online (VR-DAgger 15 cm gate);
   none characterises such errors in stored datasets or distinguishes them from tampering.
6. **The two literatures are disconnected** (CITATION_GRAPH.md): no security paper in the set cites an XR
   teleop framework or Isaac Lab, and no teleop paper cites a security paper.

Consequence for this study: the only candidate contribution not already covered would have to come from
the *collection path itself* (an attacker with limited authority inside XR→retargeting→ROS→recorder), which
PHASE 2 must show actually exists before anything is claimed.

---

# Part A — Listed items (verified one by one)

## Verification table

| arXiv id | Title | Authors (first 3 + et al.) | v1 date | Latest version (date) | Venue / status (arXiv comment / journal-ref, or verified elsewhere) | Read level |
|---|---|---|---|---|---|---|
| 2505.16640 | BadVLA: Towards Backdoor Attacks on Vision-Language-Action Models via Objective-Decoupled Optimization | Xueyang Zhou, Guiyao Tie, Guowen Zhang, et al. (6 authors) | 2025-05-22 | v1 (2025-05-22) | arXiv comment: "19 pages, 12 figures, 6 tables" (no venue). VERIFIED NeurIPS 2025 main-conference poster: neurips.cc/virtual/2025/poster/115803; OpenReview id rEhVHla9zp; camera-ready PDF on proceedings.neurips.cc (local copy `badvla_neurips.pdf`, footer "39th Conference on Neural Information Processing Systems (NeurIPS 2025)") | FULL (arXiv v1 + NeurIPS camera-ready) |
| 2601.04266 | State Backdoor: Towards Stealthy Real-world Poisoning Attack on Vision-Language-Action Model in State Space | Ji Guo, Wenbo Jiang, Yansong Lin, et al. (9 authors) | 2026-01-07 | v2 (2026-06-08) | no comment / journal-ref in arXiv metadata | FULL |
| 2609.26868 | Backdoors in Learning-Based Industrial Robotic Arm Manipulation: An Empirical Security Study | Zijian Zhang, Zhen Zeng, Zhongshu Gu, et al. (4 authors) | 2026-09-22 | v1 (2026-09-22) | arXiv comment: "Accepted at the IROS 2026 Workshop on Industrial Applications of Robot Learning" | FULL |
| 2602.18742 | RoboCurate: Harnessing Diversity with Action-Verified Neural Trajectory for Robot Learning | Seungku Kim, Suhyeok Jang, Byungjun Yoon, et al. (6 authors) | 2026-02-21 | v1 (2026-02-21) | arXiv comment: "20 pages; 6 figures; Project page ..." (no venue) | FULL |
| 2606.16788 | SoK: Security and Privacy of Foundation-Model-Powered Robots | Xueluan Gong, Chen Chen, Jinxin Liu, et al. (5 authors) | 2026-06-15 | v1 (2026-06-15) | arXiv comment: "21 pages, 2 figures" (no venue) | FULL |
| 2608.16843 | Security of Foundation-Model-Powered Embodied Agents: Attack Surfaces, Attacks, Defenses, and Evaluation | Jiawei Liu, Jiacheng Guo, Tian Zhang, et al. (7 authors) | 2026-08-17 | v1 (2026-08-17) | no comment / journal-ref | FULL |
| 2508.00097 | XRoboToolkit: A Cross-Platform Framework for Robot Teleoperation | Zhigen Zhao, Liuchuan Yu, Ke Jing, et al. (4 authors) | 2025-07-31 | v2 (2025-11-05) | arXiv comment: "accepted at The 2026 IEEE/SICE International Symposium on System Integration" | FULL |
| 2511.04831 | Isaac Lab: A GPU-Accelerated Simulation Framework for Multi-Modal Robot Learning | NVIDIA: Mayank Mittal, Pascal Roth, et al. (~105 named authors) | 2025-11-06 | v1 (2025-11-06) | arXiv comment: code/docs link only (no venue) | FULL |
| 2609.16437 | XRoboToolKit-T: Teleoperation with High Stability and Precision with Tactile Sensing for Contact-rich Manipulation | Xiwen Dengxiong, Xueting Wang, Ke Jing, et al. (5 authors) | 2026-09-14 | v1 (2026-09-14) | no comment / journal-ref | FULL (arXiv HTML v1 fetched 2026-09-30) |

---

## 1. 2505.16640 — BadVLA (NeurIPS 2025)

Read: arXiv v1 (HTML text) plus NeurIPS camera-ready (`badvla_neurips.txt`). Section numbers are the same in both for §1–6. Appendix numbering differs: arXiv v1 App. B = Implementation Details, C = Trajectory Visualization. NeurIPS adds B "Supplementary Experiments" (B.1–B.4), C "Discussion", D "Trajectory Visualization".

**a. Contribution.** The paper calls itself "the first dedicated backdoor attack framework for VLA models" (§1). It uses "objective-decoupled two-phase optimization". Stage I (§3.1) injects a trigger into the perception module through a reference-aligned loss (restrict + trigger-separation). Stage II (§3.2) freezes perception and fine-tunes the backbone and action head "exclusively on clean data". The attack is **untargeted**: §6 says "the first untargeted backdoor attack framework".

**b. Threat model (§2.2 "Threat Model").**
- Knowledge: "a white-box attacker who has full access to the model architecture and pre-trained parameters."
- Capability: "The adversary can intervene only during the model training stage. Specifically, the attacker can (i) inject crafted training samples containing imperceptible triggers, (ii) modify loss functions, or (iii) manipulate optimization strategies". The attacker "cannot alter the model's architecture or influence deployment". Motivation: Training-as-a-Service (TaaS).
- What is modified: the **visual observation** (additive trigger δ with ‖δ‖²<ε, §2.3). BadVLA itself does **not** poison action labels: Stage II uses clean labels. The *Data-Poisoned* baseline (BadNet-style) pairs a visual trigger with "a random 7D action label" (§4.1).
- Poisoning rate: none stated (it is a training-procedure attack, not a rate-based one). Trigger sizes studied are 1%, 5% and 10% of image area (§4.3).
- Triggers: pixel block, red mug, red stick (§4.2). NeurIPS App. C: "ℓ2 distances as low as 1.3".

**c. Data & models.** Four OpenVLA variants, each trained on one LIBERO suite (Spatial, Object, Goal, Long/10), plus SpatialVLA on SimplerEnv (§4.1, App. B). LoRA ranks 4 and 8. Hardware: 8×A800.

**d. Pipeline stage.** Model training / fine-tuning (outsourced TaaS). There is no collection-time or recording-time intervention.

**e. Defenses evaluated.**
- §4.5 input perturbation: JPEG compression and Gaussian noise. ASR stays high ("97.4 on Libero_10 under q=20%, and 94.7 under ε=0.08"), described as "conventional image preprocessing defenses are ineffective".
- §4.5 re-fine-tuning: ASR stays high, e.g. "ASR = 98.2 on Libero_object even after fine-tuning from Libero_10".
- NeurIPS App. B.1 adds Fine-Pruning and zero-shot Image Purification. The authors say class-consistency defenses ("Neural Cleansing, Activation Clustering") "are not directly applicable". Fine-pruning at ratio 0.8 leaves ASR at about 94–95%. High purification drops Goal SR to 10.0% while ASR stays at 75.2%.
- NeurIPS App. B.2 physical perturbations (lighting, occlusion, perspective): ASR "typically 89–100%".

**f. Evaluation scope.** Simulation only: LIBERO and SimplerEnv (google_robot tasks appear in Table 2). No real-robot experiment was found in either version. NeurIPS App. B.2 "simulated common disturbances".

**g. Author-stated limitations / future work.**
- §6 "Limitation.": "does not explore the potential severity or downstream misuse of the injected backdoors. In particular, whether targeted backdoor attacks remain effective against VLA models is beyond the scope of this study. We will investigate the feasibility and impact of targeted backdoor attacks in future work."
- §6: "We hope this work motivates further research into robust training, verification, and defense mechanisms".
- NeurIPS App. C "Discussion": "can be extended to targeted scenarios"; and "emphasizing the urgent need for dedicated detection, verification, and behavior-level auditing mechanisms before deploying VLA models".
- Version discrepancy: the arXiv v1 §6 says "experiments on state-of-the-art VLA models such as RT-2 and OpenVLA", but NeurIPS §6 says "such as OpenVLA and SpatialVLA". RT-2 was not evaluated in the experiments.

**h. Follow-ups citing it (seen).** Within the listed set: State Backdoor [15] (as a baseline), SoK [35] and Survey [18]. Titles that came up in a web search for BadVLA, but whose citation of BadVLA was NOT verified: TrustVLA (arXiv 2607.12571), ATAAT (2605.08612), "Towards Backdoor-Based Ownership Verification for VLA Models" (2605.09005).

**i. Unverified.** The NeurIPS author list on neurips.cc spells "Hecheng Wang" while arXiv spells "Hechang Wang". Not checked on OpenReview: review and decision text.

**Flags.** Teleop demos: no (uses the existing LIBERO dataset; the paper never discusses how the demos were collected). XR: no. ROS: no. Action-label vs observation mismatch: only in the Data-Poisoned baseline (visual trigger + random action label); BadVLA keeps labels clean. Dataset provenance/hash/signing: not discussed. Replay verification: no. Time sync: no.

**Citation edges (bibliography).**
- arXiv v1 → Open X-Embodiment: "[6] Open X-Embodiment Collaboration, Abby O'Neill, ... " ; NeurIPS: "[31] Open X-Embodiment Collaboration et al. Open X-Embodiment: Robotic Learning Datasets and RT-X Models. https://arxiv.org/abs/2310.08864. 2023."
- → TrojanRobot: "Trojanrobot: Physical-world backdoor attacks against vlm-based robotic manipulation. arXiv preprint arXiv:2411.11683, 2024b." (NeurIPS [11])
- → LIBERO: "Libero: Benchmarking knowledge transfer for lifelong robot learning. Advances in Neural Information Processing Systems, 36:44776–44791, 2023." (NeurIPS [20])
- No bibliography hits for Isaac Lab, XRoboToolkit, LeRobot, robomimic, DROID, ALOHA, GELLO, Open-TeleVision, Bunny-VisionPro, AnyTeleop or BadRobot.

---

## 2. 2601.04266 — State Backdoor (arXiv v2, 2026-06-08)

**a. Contribution.** The paper claims to be the first to use "the robot arm's initial state as the trigger" (Abstract; §V). It introduces a Preference-guided Genetic Algorithm (PGA; §V-B/V-C) that searches for a minimal state shift using a surrogate model, and an "Opposite Action Trajectory" poisoned label, where a_fail = negated normal actions (§V-D, Eq. 12). It also proposes reusing the attack for dataset watermarking (§VII).

**b. Threat model (§IV "Threat Model").**
- "black-box data poisoning setting ..., where the attacker has access only to the training dataset but no knowledge of the victim model"; "the attacker cannot manipulate the training pipeline or alter the model architecture"; the attacker uses a surrogate model.
- Inference: "the attacker can only perturb the initial state of victim robot arm". This is justified by an adversary who "acts as a maintenance technician" (§IV, "Why the Manipulability of the Initial State is Realistic").
- Poisoning stage: "data poisoning during this fine-tuning stage using real-world data"; it is "also applicable when datasets are published online and a VLA model is trained from scratch" (§IV).
- **Fields modified.** Fig. 1 caption: "selecting a subset of samples, injecting a specific triggered state, and altering their corresponding action labels to attacker-defined targets." So the **proprioceptive state** field and the **action labels** are both poisoned. The paper does not say that images/video are re-recorded for poisoned samples; Fig. 3 says triggered states are used "to synthesize poisoned training samples".
- Poisoning rate: "We train each model for 200K steps with a poisoning rate of 10%" (§VI-A). Rates are swept in §VI-D, where the authors call 10% "optimal".
- Goal: untargeted task failure (§IV "Effectiveness").

**c. Data & models.** Five real-world tasks (Pick-and-Place, Drawer Opening, Button Pressing, Peg Insertion, Tennis Pushing). "Each dataset contains 100 samples collected in real-world settings. Each sample consists of a 30-second MP4 video ..., a natural language instruction ..., and a sequence of 6-DOF robotic arm states recorded at each timestep" (§VI-A). Models: ACT, DP, SmolVLA, π0, OpenVLA. Also LIBERO simulation (Table IV). Hardware: SO-101 arm, cited as LeRobot [20]. Baselines: BadVLA and TrojanRobot (§VI-A).

**d. Pipeline stage.** Dataset poisoning before fine-tuning or training, plus a physical initial-state setting at deployment. §III ("Training pipeline") notes that demonstration datasets are "collected from teleoperation or reinforcement learning". This is the only mention of teleop; the attack does not target the teleop channel.

**e. Defenses evaluated (§VI-E "Robustness Evaluation").**
- Fine-pruning (0–10%): "State Backdoor consistently achieves an ASR above 90% across all pruning levels".
- Image compression (quality 100%→50%): "ASR remains high at 86%, while the model's SR drops significantly".
- Semantic Shield: "almost no impact on the attack performance" (Table VIII).
- The authors note: "Since no existing defense approaches are specifically designed for VLAs, we adapt traditional backdoor defense methods".

**f. Evaluation scope.** Real robot (SO-101, 6-DoF, 100 trials per task, §VI-B) and LIBERO simulation. An RTX 4090 is used.

**g. Author-stated limitations / discussion / future work (§VIII "Discussion", §IX).**
- §VIII "Future work.": "extending the State Backdoor paradigm to broader embodied intelligence domains"; "explore more systematic detection and certification frameworks to verify whether a deployed VLA model contains malicious or watermark-like state behaviors"; and "combining the state-space watermark with cryptographic signatures to achieve secure and verifiable model provenance tracking."
- §VIII "Societal impact.": the attack "raise[s] ethical and societal concerns if misused in safety-critical applications".
- §IX: "The design of effective defense mechanisms against backdoor attacks in VLA models remains an important direction for future research."
- §VII-B (watermark): "extensive fine-tuning can partially overwrite the state-conditioned associations".
- §II-B critique of prior work: existing VLA backdoors "rely solely on synthetic poisoned data and operate in white-box settings with access to training pipelines".
- No explicit "Limitations" heading was found.

**h. Follow-ups citing it (seen).** SoK 2606.16788 [38] and Survey 2608.16843 [32].

**i. Unverified / our observations (not author-stated).**
- The paper does not describe how the 100-sample datasets were collected (teleop device not named), or whether video frames of poisoned episodes match the altered initial state.
- A possible image-vs-state inconsistency in poisoned samples is OUR inference. The authors do not discuss it.
- The watermarking section's text mentions a "keyed joint/pose configuration".

**Flags.** Teleop demos: only a generic mention (§III). XR: no. ROS: no. Action-label vs observation mismatch: YES by design (state trigger + opposite-action labels). Dataset provenance/hash/sign: the dataset watermark (§VII) serves ownership verification, and cryptographic signatures appear only as future work (§VIII). Replay verification: no. Time sync: no.

**Citation edges.**
- → BadVLA: "[15] X. Zhou, G. Tie, G. Zhang, H. Wang, P. Zhou, and L. Sun (2025) BadVLA: towards backdoor attacks on vision-language-action models via objective-decoupled optimization. arXiv preprint arXiv:2505.16640."
- → TrojanRobot: "[14] X. Wang, H. Pan, H. Zhang, ... (2025) TrojanRobot: physical-world backdoor attacks against vlm-based robotic manipulation. arXiv preprint arXiv:2411.11683."
- → BadRobot: "[11] H. Zhang, C. Zhu, X. Wang, Z. Zhou, S. Hu, and L. Y. Zhang (2024) Badrobot: jailbreaking llm-based embodied ai in the physical world. arXiv preprint arXiv:2407.20242."
- → LeRobot: "[20] R. Cadene, S. Alibert, A. Soare, ... (2024) LeRobot: state-of-the-art machine learning for real-world robotics in pytorch. Note: https://github.com/huggingface/lerobot"
- → ALOHA/ACT: "[17] T. Z. Zhao, V. Kumar, S. Levine, and C. Finn (2023) Learning fine-grained bimanual manipulation with low-cost hardware. arXiv preprint arXiv:2304.13705."
- → LIBERO [36].
- No bibliography hits for Isaac Lab, XRoboToolkit, robomimic, DROID, Open X-Embodiment, GELLO, Open-TeleVision, Bunny-VisionPro or AnyTeleop.

---

## 3. 2609.26868 — Backdoors in Learning-Based Industrial Robotic Arm Manipulation (IROS 2026 workshop)

The first-page footnote reads: "Presented at the IEEE/RSJ International Conference on Intelligent Robots and Systems (IROS 2026) Workshop on Industrial Applications for Robot Learning, 2026, Pittsburgh". The paper is short (six sections) and describes itself as "a preliminary empirical security study" (Abstract, §VI).

**a. Contribution.** The paper studies physical-trigger backdoors on real FANUC LR Mate 200iD and xArm 6 arms. It proposes an online defense ("task-aware spatial filtering and online observation sanitization", §III), compares it to offline fine-tuning, and measures throughput overhead on an RTX 4090 and a Jetson AGX Orin.

**b. Threat model / attacker capability (§I, §III).** The threat comes via the "AI model supply chain, where training datasets, demonstrations, or pretrained models may originate from third parties"; "an adversary can poison third-party demonstration datasets" (§I). The paper has no formal threat-model section.
- **What is modified** (§III "Physically Triggered Backdoor Attack"): "For each clean demonstration, we select a semantically meaningful action primitive, inject a physically realizable trigger into an off-task workspace region, and modify the corresponding action segment to induce a predefined failure. We preserve the original task context and the remaining trajectory while ensuring that the modified motion remains physically executable."
- In short, both the **visual observation** (physical trigger object in the camera view) and a **segment of the action labels** are modified.
- Poisoning rate: "We set the poisoning ratio to 0.1, which means 5 episodes are modified" (§IV-B).
- The attack is targeted-semantic, e.g. dropping a screw or solder wire (Figs. 1–2).
- The attacker has no training-pipeline access: "isolates the attack to the demonstration data" (§III).

**c. Data & models.** Two tasks: Color Sorting and Machinery Boxing ("Collecting" in the §IV-A list). Demonstrations: "We evaluate attack efficacy and stealthiness across two representative manipulation tasks using teleoperation demonstrations" (§IV-A). The teleop device is not specified. Victim: "a visuomotor policy [5]", where [5] is Zhao et al. 2023 (ACT/ALOHA). Dataset size is not stated directly; 0.1 = 5 episodes implies about 50, but that is our arithmetic.

**d. Pipeline stage.** Demonstration-dataset poisoning (training-time). The defense runs at inference, sanitizing the input.

**e. Defenses and results.**
- Table III (Color Sorting, 5 rollouts): Fine-tuning at 2%/4%/8% gives N_ap 4/5, 4/5, 3/5 and N_dp 0/5 at every level. Online Sanitization gives N_ap 1/5 and N_dp 5/5.
- Table IV throughput (cycles in 10 min, unshielded/shielded): RTX 4090 31/32; Jetson AGX Orin 32/29.
- §I and §II-B argue that state-space safety filters (CBF, HJ reachability, MPS) and latent-space monitors miss "semantically incorrect but physically valid behavior".
- Attack results (Table II, out of 10): FANUC N_cp 8 and 10, N_ap 9 and 9; xArm N_cp 10 and 9, N_ap 10 and 8.

**f. Evaluation scope.** Real robots only (FANUC LR Mate 200iD, xArm 6). Small trial counts: 10 rollouts for attacks, 5 for defense.

**g. Author-stated limitations (§V "Discussion").**
- "Adaptive Attacks and In-Task Triggers.": "This defense assumes that physical triggers reside in the off-task background ... An adaptive adversary could instead place triggers on task-relevant objects or manipulator links, bypassing static task-mask filtering." Proposed remedy: "A stronger defense should therefore model trigger visibility in 3D: depth estimation and point-cloud consistency".
- "Multimodal and Language-Conditioned Triggers.": "This defense currently targets physical visual triggers and does not cover backdoors activated through other modalities." Suggested extension: "cross-modal consistency checks".
- §II-A: training "without explicit semantic verification of training trajectories, leaving the training pipeline vulnerable to backdoor injection."

**h. Follow-ups citing it.** None seen (v1 is dated 2026-09-22).

**i. Unverified.** The teleop interface, dataset size, camera setup beyond "top-view camera image" (§IV-B), and exact policy architecture per arm ("heterogeneous policy architectures", §I) are not detailed.

**Flags.** Teleop demos: YES (explicitly "teleoperation demonstrations"). XR: no. ROS: not mentioned. Action-label vs observation mismatch: the poison is consistent in the sense that a trigger in the image is paired with a modified action segment. The label change is edited, not physically executed during collection, which the authors call "modify the corresponding action segment". Dataset provenance/hash/sign: no, but the paper does name the untrusted third-party dataset supply chain. Replay verification: no, though the edits keep motion "physically executable". Time sync: no.

**Citation edges.** → ALOHA/ACT: "[5] T. Z. Zhao, V. Kumar, S. Levine, and C. Finn (2023) Learning fine-grained bimanual manipulation with low-cost hardware. In Proceedings of Robotics: Science and Systems (RSS)". No other listed-paper or keyword hits: no BadVLA, State Backdoor, TrojanRobot, LeRobot or others.

---

## 4. 2602.18742 — RoboCurate (data-quality paper, not a security paper)

The text carries "Keywords: Machine Learning, ICML" from the template. That is NOT evidence of acceptance: the arXiv metadata has no venue.

**a. Contribution.**
- A synthetic ("neural trajectory") data framework that "evaluates and filters the quality of annotated actions by comparing them with simulation replay" (Abstract).
- §3.2 "Action-level Filtering of Neural Trajectory": IDM-predicted actions are replayed "in simulator and renders the corresponding rollout video w_sim(a_IDM), whose robot motion is consistent with a_IDM. This converts the action verification problem into a motion-consistency comparison between two videos".
- An attentive probe on a frozen V-JEPA2 encoder classifies whether each pair is motion-consistent. A sample is kept only if p exceeds threshold c.
- The probe is trained on real demos, with positives = (real clip, sim replay of real action) and negatives = "Temporally shifted negatives" and "Cross-episode negatives" (§3.2, Fig. 3).
- Additional pieces: I2I editing and action-preserving V2V transfer (§3.1), and Best-of-N sampling using the probe as a critic (§3.3).

**b. Threat model.** NONE. This is a benign data-quality framework. Its error model is "physically implausible video motion or IDM prediction errors can make the predicted action inconsistent with the video" (§3.2).

**c. Data & models.**
- Pre-training data: Fourier ActionNet ("30K teleoperated episodes", of which a 3K subset is used; GR1-T1, 44-dim; §4.1 "Datasets").
- Fine-tune/eval: GR-1 Tabletop and DexMimicGen (simulation).
- Real robot: ALLEX humanoid (48-dim), with "48 teleoperated demonstrations" for the ID task (§4.2).
- Policy: GR00T N1.5. Video models: Cosmos-Predict2-14B, FLUX.2-dev, Cosmos-Transfer2.5-2B. IDM: DiT + SigLIP-2. VLM judges: Gemini 3 Pro and Gemini 2.5 Flash (App. B).

**d. Pipeline stage.** Dataset curation (synthetic-data generation and filtering) before training.

**e. "Defenses" (filters) and results.**
- Table 4 compares filtering against video-only plausibility judges (DreamGenBench, VideoCon-Physics). The authors conclude "verifying action quality is crucial for policy learning, whereas relying solely on VLM-based video-level plausibility assessments is insufficient" (§4.3).
- Table 6 ablation: a cosine-similarity baseline "yields limited gains", and "human labels provide little benefit and can even underperform the naive baseline, likely due to noisy judgments on subtle action mismatches" (§4.3).
- Headline gains (Abstract): +70.1% (GR-1 Tabletop, 300 demos), +16.1% (DexMimicGen), +179.9% (ALLEX real).

**f. Evaluation scope.** Simulation benchmarks plus a real ALLEX humanoid (24 trials across 3 tasks, Table 3).

**g. Author-stated limitations / discussion.**
- There is no Limitations section.
- §6 Conclusion: "We hope RoboCurate encourages principled quality evaluation for synthetic robot data".
- Impact Statement: "Careful consideration is required to ensure that synthetic robot data and resulting policies align with social values."
- §5 (about simulation generally): "sim-to-real gap, inaccurate physical modeling, and difficulties in handling articulated objects, deformable materials, or complex tool interactions".
- §2 notes that "D_syn has zero-padded proprioceptive states, since IDMs do not predict state information."
- The simulator used for replay is NOT named anywhere in the text (checked by grep).

**h. Follow-ups citing it.** None seen.

**i. Unverified.** The simulator identity and the value of threshold c (not in Table 7). Whether the replay verifier would detect *adversarial* (rather than accidental) action–video mismatch was not studied, and any such claim is extrapolation.

**Flags.**
- Teleop demos: YES as source data (ActionNet "teleoperated episodes"; ALLEX "teleoperated demonstrations").
- XR: no. ROS: no.
- Action-label vs observation mismatch: YES, the central topic, but for benign/generative errors. This is the closest prior art to action-vs-video consistency checking. It replays actions in simulation and compares motion to video.
- Dataset provenance/hash/sign: no.
- Replay verification: YES (simulator replay + learned consistency probe).
- Time sync: temporally shifted clips are used as *negatives* (§3.2), i.e. the probe is trained to reject temporal misalignment between video and replayed action. This is relevant to time-sync attacks, but the authors frame it only as supervision design.

**Citation edges.**
- → DROID: "Khazatsky et al. (2024) ... Droid: a large-scale in-the-wild robot manipulation dataset. arXiv preprint arXiv:2403.12945."
- → Open X-Embodiment: "O'Neill et al. (2024) ... Open x-embodiment: robotic learning datasets and rt-x models ... ICRA 2024".
- No hits for Isaac Lab, XRoboToolkit, LeRobot, robomimic, ALOHA, GELLO, Open-TeleVision, Bunny, AnyTeleop, BadVLA, TrojanRobot or BadRobot. It cites MimicGen/DexMimicGen (Mandlekar et al., 2023; Jiang et al., 2025) but not robomimic.

---

## 5. 2606.16788 — SoK: Security and Privacy of FM-Powered Robots

**a. Contribution.**
- The F-E-S-G "progressive ... structural boundary framework" (§II-B) has four layers: Foundation model (F), Embodied system (E), Supporting ecosystem (S) and Governance impact (G).
- It builds a multi-level taxonomy (§II-C) and codes each paper by target, stage, mechanism, system access and effect (§II-D).
- Corpus (§II-E): "starts from 290 candidate papers, retains 118 papers after full-text screening, and produces a final coded corpus of 96 papers". "The corpus was last updated in June 2026."
- Layer-assignment rule (§II-B): a work goes in the layer "where the risk or mitigation is primarily introduced". Example given: "BadVLA-style poisoning [35] is classified as F because it backdoors the VLA checkpoint, while a trojanized SROS2 package [36] is classified as S".

**b. Threat model.** This is a survey with no single threat model.
- Relevant categorization, §III-A "Model Compromise": "In data poisoning, the adversary poisons the data sources used to train, adapt, or condition the model, such as few-shot instruction-code examples [37], VLA fine-tuning demonstrations [40], state-action training samples [38], or action-trajectory data [39]". Here [38] = State Backdoor, [39] = SilentDrift, [40] = GoBA.
- Malicious fine-tuning is separated from data poisoning: "[42, 35, 41, 43]", with BadVLA [35] as the example.
- The authors' assessment (§III-A): "they typically require restrictive white-box access and control over the training pipeline."

**c. Data & models covered.** LLM/VLM/VLA-powered robots. World foundation models are excluded from the main systematization (§II-E) and treated as an open problem (OP4).

**d. Pipeline stages.** The "Stage" coding attribute uses values such as Development and Deployment (Table II). Table II codes State Backdoor [38], SilentDrift [39], GoBA [40], BadVLA [35] and INFUSE [41] all as "VLA | Policy Module | Model Compromise | Development | White-box | High | High".
- **Discrepancy:** the SoK codes State Backdoor as White-box, but State Backdoor's own §IV says "black-box data poisoning setting".

**e. Defenses systematized.**
- F layer (§III-C): "Model Hardening" (data-centric hardening [59] = "Task robustness via re-labelling vision-action robot data"; adversarial training; model merging; interpretable architecture) and "Execution Guardrail" (SAFE-Dict).
- E layer (§IV-C): runtime guardrails and middleware hardening (ROS 2 communication LTL analysis, Yang et al. [98]).
- S layer (§V-C): supply-chain verification (LLM semantic checker, Xie et al. [104]), multi-robot resilience, and runtime MITM detection.
- The SoK itself names no dataset-level integrity defense (hash, signing, replay check) for demonstrations. This is based on grep: "teleop" gets 0 hits.

**f. Evaluation scope.** Literature only.

**g. Author-stated limitations / gaps / future work.**
- Limitation 1 (§III-C) "Semantic-to-physical Validation Gap".
- Limitation 2 (§IV-C) "Reactive and Layer-local Mitigation": guardrails "intervene only after sensing, grounding, or reasoning has already shaped intermediate decisions".
- Limitation 3 (§V-C) "Limited Understanding of Compositional Risks".
- Limitation 4 (§VI-A) "Governance Lag and Weak Accountability Evidence": "Auditing and incident response further depend on provenance records, update histories, runtime traces, and deployment logs, which may be incomplete, inaccessible, or privacy-sensitive."
- §VII-A (C2): "existing mitigation strategies are often deployed locally at the layer where the harm is observed, suppressing downstream symptoms without eliminating the upstream vulnerability."
- §VII-A (C4) "Insufficient Technical Evidence for Accountability": "current FM-powered robots often lack unified provenance records, model-update histories, runtime traces, and privacy-preserving audit interfaces."
- §VII-B: (E1) "Lack of Shared Benchmarks"; (E2) metrics; (E3) utility cost; (E4) "Limited Sim-to-Real Validation".
- §VII-C:
  - (OP3) "requires temporal verification frameworks that can monitor intent consistency and behavioral invariants over time".
  - (OP4) WFMs "may introduce new risk pathways, including synthetic-data poisoning, manipulation of world-state or simulator inputs".
  - (OP6) "asymmetric monitoring".
  - (OP7) "combining techniques such as cryptographic commitments for provenance, trusted-execution attestation for integrity, and zero-knowledge proofs for selective disclosure. ... How to integrate them into a coherent, end-to-end evidence mechanism for FM-powered robots remains an open problem."
- App. C "Scope and Validity Considerations": "the corpus is structured and representative rather than an exhaustive bibliometric census"; "Security work is more mature than privacy work".

**h. Follow-ups citing it.** None seen.

**i. Unverified.** Appendix B screening statistics were not re-checked line by line. Table rows beyond Table II's F-layer attack rows were not transcribed.

**Flags.**
- Teleop demos: no ("teleop" 0 hits). "VLA fine-tuning demonstrations" appear only as a poisoning target.
- XR: no.
- ROS: YES, at the middleware and supply-chain level: SROS2 flaws [83], DDS security [84], ROS 2 metadata leakage [87], ROS 1 exposed masters [107], trojaned SROS2 package [36], ROS2 LoRA supply-chain backdoor [104]. None of these concern recorded demonstration data.
- Action-label vs observation mismatch: not discussed as such.
- Dataset provenance/hash/sign: only as governance/accountability gaps (C4, Limitation 4, OP7).
- Replay verification: no.
- Time sync: no. Temporal verification is mentioned only for runtime behaviour (OP3).

**Citation edges.**
- → BadVLA: "[35] X. Zhou, G. Tie, G. Zhang, H. Wang, P. Zhou, and L. Sun (2025) Badvla: towards backdoor attacks on vision-language-action models via objective-decoupled optimization. arXiv preprint arXiv:2505.16640." (cited in Table II, §II-B, §III-A)
- → State Backdoor: "[38] J. Guo, W. Jiang, Y. Lin, Y. Liu, R. Zhang, G. Lu, A. Chen, X. Han, H. Li, and D. Niyato (2026) State backdoor: towards stealthy real-world poisoning attack on vision-language-action model in state space. arXiv preprint arXiv:2601.04266." (Table II, §III-A)
- → TrojanRobot: "[9] X. Wang, H. Pan, ... (2025) TrojanRobot: backdoor attacks against llm-based embodied robots in the physical world. arXiv preprint arXiv:2411.11683." (Title differs from the version cited by BadVLA/State Backdoor.)
- → BadRobot: "[11] H. Zhang, C. Zhu, X. Wang, ... (2024) Badrobot: jailbreaking embodied llms in the physical world. arXiv preprint arXiv:2407.20242."
- Also cited but not in the keyword list: SilentDrift [39] (arXiv:2601.14323), GoBA [40] (arXiv:2510.09269), INFUSE [41] (arXiv:2602.00500).
- No hits for the industrial-backdoor paper, RoboCurate, Isaac Lab, XRoboToolkit, LeRobot, robomimic, DROID, OXE, ALOHA, GELLO, Open-TeleVision, Bunny, AnyTeleop or LIBERO in the bibliography. LIBERO appears only in the body: "LIBERO-derived settings [77, 49]", §VII-B.

---

## 6. 2608.16843 — Security of FM-Powered Embodied Agents: Attack Surfaces, Attacks, Defenses, and Evaluation (survey)

**a. Contribution.** A "trust-boundary-centric survey" that uses a "first-compromised-trust-boundary principle" and "separate[s] attack surface from attack mechanism" (Abstract).
- Structure: five layers and twelve attack surfaces, AS01–AS12 (§4).
- Corpus: "58 attack records and 61 defense records collected through August 15, 2026" (Abstract, §2.2).
- Five RQs (§1.4).
- The 2606.16788 SoK is reference [1] and was used as a "major seed source" (§2.2).

**b. Threat model.** §3.3 "Adversary capabilities and access models": black-box, gray-box and white-box ("can access model weights, gradients, training data, or internal representations"), plus "A system-level adversary may additionally reach ROS topics, network links, credentials, cloud APIs, or inter-robot messages".
- Coding rule (§2.3): "For backdoors, malicious capability implanted during training is coded as AS01 even if deployment-time triggers are linguistic or visual."
- AS01 (§5.1) covers "training data, fine-tuning examples, LoRA/Adapters, checkpoints, third-party perception/policy models".
- AS06 (§5.6) covers "joint state" and proprioception. State Backdoor is the example: "explicitly studies stealthy poisoning in VLA state space[32]".

**c. Data & models.** LLM/VLM/VLA/world-model agents. Inclusion tiers are A–Core, B–Adjacent and C–System Extension (§2.1).

**d. Pipeline stages.** Development/supply chain (AS01) through execution (AS12). "Lifecycle stage: distinguish development-time threats involving training, fine-tuning, and model distribution from deployment-time ..." (§2.4).

**e. Defenses systematized (§7).**
- §7.1 model hardening. Backdoor-specific defenses listed: "TrustVLA uses causal footprints, trigger localization, and inpainting at inference time[108]; Bera detects abnormal attention ...[121]; and VLAGuard/APFT together with SARF ...[109, 110]".
- §7.2 advocates "provenance-aware privilege control: source identity, authority, integrity, freshness".
- §7.3 "World-state integrity, cross-modal consistency, and verifiable facts": "object relations, pose, occupancy, affordances, joint states, and feedback should carry provenance and support cross-modal and temporal consistency checks".
- §5.1 on AS01: "clean-task performance does not establish trustworthiness ... Stronger guarantees require data provenance, weight/adapter integrity, model-differential analysis, trigger search, and persistence testing under downstream fine-tuning."
- §5.10 (AS10): "Only 6 of 58 attack records and 2 of 61 defense records cover AS10". Proposed direction: "message signing, device identity, cloud-model authentication, endpoint attestation, state provenance".

**f. Evaluation scope.** Literature only.
- §9.4 recommends a three-level protocol: simulator → digital-to-physical sensing → real closed-loop robot.
- §9.5: "logs should be preserved at model, planning, action, and physical layers."

**g. Author-stated limitations / future work.**
- §2.5 "Methodological limitations": "Three limitations are unavoidable". They are (1) preprint status may change, (2) "multi-label coding necessarily involves judgment", and (3) "paper counts measure research attention rather than real-world attack probability".
- §2.2: "'near-exhaustive' should not be interpreted as a literal guarantee"; the corpus is "a dynamic snapshot".
- §8.6: "Only 4 of 58 attack records cover AS06 directly"; "the literature more often uses state to make safety decisions than studies how that state can itself be compromised."
- §5.6: "Future work should examine state provenance, sensor-to-state consistency, temporal consistency, feedback spoofing".
- §10.2 "Provenance and delegated authority should become first-class objects": "attach source, identity, authorization level, timestamp, integrity evidence, and permitted influence scope to each information item."
- §10.3: "building sensor-to-state provenance and cross-modal consistency checks".
- §10.8: "Certified robustness must move from single frames to trajectories".
- §11.4: "Paper count is not risk magnitude".
- Abstract: "open challenges in state provenance, compositional defenses, long-horizon attack propagation, physical realizability, Byzantine multi-robot behavior, and unified closed-loop evaluation."

**h. Follow-ups citing it (seen).** Survey 2608.16843 cites it as [1] ("major seed source", §2.2).

**i. Unverified / discrepancies found.**
- Appendix A Table 5 codes BadVLA as "AS01;AS05;AS09 | VLA | Simulation + real robot". Neither the arXiv v1 nor the NeurIPS text of BadVLA reports a real-robot experiment; all are LIBERO/SimplerEnv simulation (see §1). The survey's validation coding for BadVLA therefore looks incorrect.
- State Backdoor is coded "AS01;AS06;AS09 | Simulation + real robot", which is consistent with its paper.
- Some reference entries have no URL, e.g. "[22] Clean-Action Backdoor ... paper/preprint, 2025."

**Flags.**
- Teleop demos: no ("teleop" 0 hits). "Demonstrations" appear only as in-context demonstrations (AS03).
- XR: no.
- ROS: YES (AS10, RIPA ROS2 prompt injection, Secure ROS2 insecurity).
- Action-label vs observation mismatch: not discussed for datasets. Cross-modal and temporal consistency is proposed only for runtime *state* (§7.3, §10.3).
- Dataset provenance/hash/sign: only "data provenance" as a named requirement (§5.1) and message signing for middleware (§5.10). No mechanism is surveyed.
- Replay verification: no.
- Time sync: "timestamp" and "freshness" appear as provenance attributes (§7.2, §10.2).

**Citation edges.** Bibliography entries use the format "Title. venue, year. URL".
- → SoK 2606.16788: "[1] X. Gong, C. Chen, J. Liu, Q. Wang, and K.-Y. Lam. SoK: Security and Privacy of Foundation-Model-Powered Robots. arXiv:2606.16788, 2026."
- → BadVLA: "[18] BadVLA: Towards Backdoor Attacks on Vision-Language-Action Models via Objective-Decoupled Optimization. arXiv, 2025. https://arxiv.org/abs/2505.16640"
- → State Backdoor: "[32] State Backdoor: Towards Stealthy Real-world Poisoning Attack on Vision-Language-Action Model in State Space. arXiv, 2026. https://arxiv.org/abs/2601.04266"
- → TrojanRobot: "[13] TrojanRobot / Robot Collapse: Supply-Chain Backdoor Attacks Against VLM-based Robotic Manipulation. arXiv, 2025. https://arxiv.org/abs/2411.11683"
- → BadRobot: "[9] BadRobot: Jailbreaking Embodied LLMs in the Physical World. ICLR 2025 / arXiv, 2024."
- Also cited (not in the keyword list): DropVLA [21] (2510.10932), Clean-Action Backdoor [22], AttackVLA [23] (2511.12149), SilentDrift [33], INFUSE [62], TrustVLA [108].
- No hits for 2609.26868 (it postdates the corpus cutoff), RoboCurate, Isaac Lab, XRoboToolkit, LeRobot, robomimic, DROID, OXE, ALOHA, GELLO, Open-TeleVision, Bunny, AnyTeleop or LIBERO.

---

## 7. 2508.00097 — XRoboToolkit (arXiv v2; accepted at IEEE/SICE SII 2026)

**a. Contribution.** A "cross-platform framework for extended reality-based robot teleoperation built on the OpenXR standard" (Abstract).
- Components: Unity Client on the headset, PC Service (C++), PC Service Pybind, Robot Vision, and IK/dexterous retargeting (§II-A, Fig. 1).
- Supported devices: "PICO 4 Ultra and Meta Quest 3" (§I).
- Robots: UR5, ARX R5, Galaxea R1-Lite, Shadow hands. Simulation: MuJoCo (§I).
- Motivating gap: "Another significant limitation is the lack of standardized data formats between XR devices and robot controllers" (§I).

**b. Threat model.** None. The paper contains no security, authentication or encryption content (grep found 0 hits for security/authenticat/encrypt/TLS).

**c/d. Data collection & recording formats (the relevant facts).**
- §II-B "Data Streaming", "XR Data Formats": the PC Service "employs an asynchronous, callback-driven architecture". Poses are "formatted as seven floating-point numbers separated by commas: 3D position vector [x,y,z] followed by quaternion [qx,qy,qz,qw]". Coordinates are OpenXR right-handed; "The origin is established at the user's head position when the application launches."
- "All real-time tracking data are transmitted within a single JSON object at 90 Hz." Table I fields:
  - Head: pose, status ("Tracking confidence (0: unreliable, 1: reliable)"), handMode.
  - Controller: pose, axisX/Y, axisClick, grip, trigger, buttons; menuButton = "Menu (L), Screenshot/Record (R)".
  - Hand: isActive, scale, 26 HandJointLocations.
  - Whole-Body: 24 joints.
  - Motion Tracker: p, va, wva, sn ("Unique serial number of tracker").
- "While transmitted with the JSON object at 90 Hz, hand tracking data updates at 60 Hz due to camera limitations" (§II-B). This is a rate mismatch inside the stream.
- §II-C1: control is relative. "end-effector tracking activates when the user holds the grip button ... the robot's end-effector tracks controller displacement relative to its state when grip was first pressed."
- §II-D "XR Unity Application": "The Data Collection panel enables timestamped recording of both pose and visual data streams on the headset. Note that robot state data is recorded separately through the teleoperation module." Headset-side recording and robot-side recording are therefore **separate streams**.
- §IV-B "Data Collection for VLA Fine-tuning": "100 demonstrations of a bimanual carpet folding task using the ARX R5 dual-arm system equipped with RealSense D405i wrist cameras and a D435i overhead camera ... recorded at 50 FPS, with every frame containing 14-dimensional robot joint states, 14-dimensional position control commands, and 424×240 RGB images from all three cameras." Used for LoRA fine-tuning of π0, with "a 100% success rate during 30 minutes of continuous operation".
- Not in the paper; from the repo README (`XR-Robotics_XRoboToolkit-Teleop-Sample-Python.README.md`, local copy):
  - Logs are `.pkl` files named `teleop_log_YYYYMMDD_HHMMSS_<session_id>.pkl`.
  - The README claims "Timestamp synchronization across all data streams". It says the B button starts/stops logging and a right-joystick click discards the session.
  - There is a conversion example to LeRobot format.
  - "the controller communicates with the robot hardware via ROS" (Galaxea R1-Lite).
  - The README is software documentation, not peer-reviewed, and the timestamp-sync claim was not verified in code here.

**e. Evaluation.**
- §IV-A video latency, measured with an LED panel. XRoboToolkit ZED Mini→PICO 4 Ultra: 82.00 ms. ZED Mini→Quest 3: 94.5 ms versus Open-TeleVision's 121.50 ms ("27 ms (22%) latency reduction"). PICO→PICO: 100.50 ms, STD 3.12.
- The paper's own condition list is miscounted: "Three conditions were evaluated: 1) ... 3) ... and 3)" lists four conditions.

**f. Scope.** Real robots (ARX R5 dual-arm, UR5 dual, Galaxea R1-Lite) plus MuJoCo and MeshCat visualization.

**g. Author-stated limitations / future work (§V "Conclusions").**
- "Current whole-body tracking relies on PICO's 24-joint model due to the absence of standardized whole-body definitions in OpenXR, potentially creating compatibility issues with other XR brands".
- "while whole-body tracking data is provided, it has not been validated through retargeting to humanoid robots".
- "the hand retargeting framework assumes each joint is individually controllable and therefore cannot accurately retarget to robot hands with mechanical constraints that couple joint movements, such as the INSPIRE Hands".
- "The framework currently supports only MuJoCo simulation".
- Future work: "improving hand retargeting algorithms for underactuated systems, expanding simulation support through platforms such as Roboverse ..., and developing humanoid teleoperation capabilities"; "contribute to OpenXR standardization efforts".
- **Data-quality statements.** "current approaches suffer from limited scalability, complex setup procedures, and suboptimal data quality" (Abstract, about prior systems). Vision-based teleop "often suffer[s] from unstable tracking performance and higher latency, degrading operator performance and data quality" (§I). §IV-B notes "occasional regrasping and repositioning behaviors" in demonstrations. The paper has no data-integrity or data-validation mechanism beyond downstream policy success.

**h. Follow-ups citing it (seen).** XRoboToolKit-T (2609.16437) cites it as [2] and is "built upon PICO's XRoboToolkit [2]" (see §9).

**i. Unverified.** README claims (timestamp sync, pkl schema) and the v1→v2 diff (not compared).

**Flags.**
- Teleop demos: YES. XR: YES (OpenXR, PICO, Quest). ROS: only in the README (R1-Lite via ROS). The paper has no ROS mention (grep "ROS" 0 hits in body).
- Action-label vs observation mismatch: the recorded "position control commands" (actions) and "robot joint states" come from the teleop module. Headset pose/vision is recorded separately. The paper does not discuss consistency between them.
- Dataset provenance/hash/sign: none.
- Replay verification: none.
- Time sync: headset recording is "timestamped". The paper does not describe clock synchronization between headset and robot PC. Mixed rates: 90 Hz JSON / 60 Hz hand / 50 FPS recording / 60 Hz stereo video.

**Citation edges.**
- → ALOHA: "[11] T. Zhao, V. Kumar, S. Levine, and C. Finn (2023) Learning fine-grained bimanual manipulation with low-cost hardware. Robot. Sci. Syst."
- → AnyTeleop: "[12] Y. Qin, W. Yang, B. Huang, K. Van Wyk, H. Su, X. Wang, Y. Chao, and D. Fox (2023) AnyTeleop: a general vision-based dexterous robot arm-hand teleoperation system. In Robot. Sci. Syst."
- → Open-TeleVision: "[14] X. Cheng, J. Li, S. Yang, G. Yang, and X. Wang (2024) Open-television: teleoperation with immersive active visual feedback. In Proc. Conf. Robot Learn."
- Other teleop refs (not in the keyword list): OPEN TEACH [10], Oculus Reader [15], Seo et al. 2023 [16].
- No hits for Isaac Lab, LeRobot, robomimic, DROID, OXE, GELLO, Bunny-VisionPro or the security papers.

---

## 8. 2511.04831 — Isaac Lab (NVIDIA; framework paper)

**a. Contribution.** "the natural successor to Isaac Gym". It "integrates actuator models, multi-frequency sensor simulation, data collection pipelines, and domain randomization tools" (Abstract). It is built on Isaac Sim with PhysX and RTX (§8), and a Newton engine integration is upcoming (§7.1).

**b. Threat model.** None. Grep for security/integrity/provenance found no security content.

**c/d. Data collection & recording formats (the relevant facts).**
- §3.5 "Teleoperation Support": teleop is used for "direct user control, controller and policy evaluation, and demonstrations for robot learning".
- §3.5.1: keyboard (delta pose) and spacemouse. "The use of a spacemouse can enable higher quality human demonstrations for data collection for imitation learning tasks".
- §3.5.2 "Extended Reality (XR) Device Teleoperation":
  - Uses "an Apple Vision Pro (AVP) headset. The user's hand joints detected by the AVP are mapped to the end-effector pose, which is then used in inverse kinematics (IK)", with a waist task and a null-space task.
  - "In contrast to prior XR teleoperation systems that directly stream stereoscopic video from the robot's perspective to the operator's display (Zhang et al., 2025b; Cheng et al., 2024), Isaac Lab uses NVIDIA CloudXR framework". CloudXR "incorporates re-projection algorithms to mitigate the perceptual effects of residual streaming delays" and supports AR overlays.
- §5.4 "Imitation Learning":
  - "Isaac Lab supports IL through integration with the widely used RoboMimic framework ... Demonstration data can be collected through human teleoperation or synthetically generated using Isaac Lab Mimic".
  - **"All demonstrations are stored in the standardized HDF5 format based on the RoboMimic schema."**
  - There is "a dedicated conversion utility allowing users to transform existing HDF5 datasets into the LeRobot format ..., which utilizes columnar Parquet for time-series data and MP4 encoding for efficient visual data handling".
- §3.7.1: the manager-based workflow includes managers "for observations, actions, rewards, terminations, commands, curricula, events, and recording".
- §5.5 "Synthetic Data Generation" (Isaac Lab Mimic): "segments a human demonstration into object-centric subtasks, applies rigid transformations to each segment, and recombines them into new demonstrations". It "can generate an effectively unbounded number of synthetic demonstrations from as little as a single human demonstration". SkillGen (§5.5.2) "reduces manual data collection while improving dataset consistency and validity".
- §3.3 "Sensors": "flexible sensor update frequencies ... This avoids the typical unrealistic assumption of synchronized sensing and control, and better approximates real-world conditions where sensors operate at different rates and experience communication delays."
- §2.3 (TiledCamera): supports "camera poses in multiple conventions, such as those used in ROS". This is the only ROS mention found.

**e. Evaluation.** Throughput benchmarks (§4) and application showcase (§6). No data-integrity evaluation.

**f. Scope.** Simulation framework. Sim-to-real results are cited from applications (§6, §7.2.2).

**g. Author-stated limitations / future work (§7 "Future Work and Discussion").**
- Newton integration "addresses key limitations of existing engines in complex robotic scenarios".
- "future releases will enhance rendering capabilities"; "we aim to build a standardized platform for policy evaluation and benchmarking".
- §7.2.1 Arena: current end-to-end evaluation "often requires significant manual effort. This leads to fragmented setups with high overhead, limited scalability, and a steep entry barrier". Arena "will be open-sourced on GitHub soon".
- §7.2.2: extend to "the full set of NIST benchmark tasks". §7.2.3: expand the dexterous suite to humanoids.
- **Data-quality statements.** Only the spacemouse remark (§3.5.1) and the SkillGen "consistency and validity" claim (§5.5.2). There is no stated limitation about demonstration integrity, provenance or validation of HDF5 datasets.

**h. Follow-ups (seen in this set).** XRoboToolKit-T cites it as [16]. Wider citers were not assessed.

**i. Unverified.** The HDF5 schema details, and the recorder-manager contents (field names, timestamps), are not specified in the paper and would need repo docs. The local `il_teleop_imitation.txt` / `il_augmented_imitation.txt` docs exist in `lit/` but were not part of this paper read.

**Flags.** Teleop demos: YES (keyboard, spacemouse, AVP XR). XR: YES (AVP + CloudXR). ROS: only the camera pose convention. Action-label vs observation mismatch: not discussed. Mimic-generated demos are transformed and stitched trajectories, so labels are synthetic by construction. Dataset provenance/hash/sign: none. Replay verification: not described in the paper. Time sync: multi-rate sensors are simulated on purpose; recording sync is not described.

**Citation edges.**
- → robomimic: "[59] A. Mandlekar, D. Xu, J. Wong, S. Nasiriany, C. Wang, R. Kulkarni, L. Fei-Fei, S. Savarese, Y. Zhu, and R. Martin-Martin (2022) What matters in learning from offline human demonstrations for robot manipulation. In Conference on Robot Learning (CoRL)".
- → LeRobot: "[11] R. Cadene, S. Alibert, A. Soare, ... (2024) LeRobot: state-of-the-art machine learning for real-world robotics in pytorch. Note: https://github.com/huggingface/lerobot. Cited by: §5.4."
- → Open-TeleVision: "[18] X. Cheng, J. Li, S. Yang, G. Yang, and X. Wang (2024) Open-television: teleoperation with immersive active visual feedback. arXiv preprint arXiv:2407.01512. Cited by: §3.5.2."
- → Orbit (predecessor): "[63] M. Mittal, C. Yu, Q. Yu, ... (2023) Orbit: a unified simulation framework for interactive robot learning environments. IEEE RA-L 8 (6), pp. 3740–3747."
- → Isaac Gym: "Isaac gym: high performance gpu based physics simulation for robot learning. In Proceedings of the Neural Information Processing Systems Track on Datasets and Benchmarks".
- The "Zhang et al., 2025b" cited in §3.5.2 resolves to "Unleashing humanoid reaching potential via real-world-ready skill space. arXiv:2505.10918".
- No hits for XRoboToolkit, DROID, OXE, ALOHA, GELLO, Bunny-VisionPro, AnyTeleop or any security paper.

---

## 9. 2609.16437 — XRoboToolKit-T (tactile extension of XRoboToolkit)

Read: full text fetched on 2026-09-30 from arxiv.org/html/2609.16437v1 and converted with `h2t.py` to `lit/2609.16437.txt` (it was not in the pre-downloaded set). arXiv subjects: cs.RO; cs.HC.

**a. Contribution.** "XRoboToolkit-Tactile (XRoboToolkit-T or XRT-T), a tactile-informed teleoperation system ... built upon PICO's XRoboToolkit [2] and consists of two new modules: 1) a contact force stabilizer and 2) a Vision-Language-Action (VLA) model-based action refiner" (§I). Affiliations: RIT, TikTok Pico Lab and HKUST-GZ.

**b. Threat model.** None (no security content).

**c/d. Data collection & recording formats.**
- §III-A "Tactile Perception": a "generic sensor reading module" with a "hardware-agnostic interface that abstracts vendor-specific communication protocols and converts raw measurements into a unified tactile data format compatible with the robot feedback stream. Incoming signals are synchronized with robot kinematics and timestamped to maintain temporal consistency across perception channels."
- Table I "Robotic Haptic Feedback Data Formats":
  - Tactile: Normal Force (grid x×y), Shear Force, Force Direction, Contact State (0/1).
  - End-Effector: Type, Active Dof, Pose (p, q quaternion), Velocity, Torque, End Effector Status.
  - Robotic Joints: Mode, Joint Position/Velocity/Effort, Chassis movement, Position.
- §III-C: "The robot data feedback stream module extends the XRoboToolkit PC Service to support real-time bidirectional communication ... asynchronous publish–subscribe pipeline ... the PC Service manages network transport, synchronization, and event dispatch to registered callbacks."
- §III-B: 26-joint PICO 4 Ultra hand tracking, and "controller input with a transmission frequency of up to 90 Hz".
- **Control law (§IV-B, Eq. 3):** U_ee^{t+1} = U_ee^t + I^f·δ_teleop^t + I^s(t)·δ_refine^t.
  - Stabilizer at "approximately 20 Hz". It can "temporarily disable teleoperation by setting I^f = 0" (§IV-A).
  - VLA refiner at "approximately 7 Hz", taking "a tactile image ... as its visual observation" (§IV-A).
- **Our observation, not author-stated:** the executed and recorded robot motion is a fusion of operator input, a stabilizer gain and autonomous VLA corrections. A "demonstration" collected this way is therefore not purely human-authored. The paper does not say whether δ_teleop, I^f and δ_refine are logged separately.
- App.: "Pico4U XR headset, which communicated with the control computer via WiFi to stream operator motion commands".

**e. Evaluation.**
- Table II, successful manipulations in 15 min: Twist2 128; XRT-T+gripper 138; XRT-T+dexterous hand 132.
- Table III, control frequency: XRT+hand tracking 20.2 Hz; XRT-T+hand tracking 48.6 Hz; XRT-T+controller 96.4 Hz.
- Table IV ablation, manipulations/min: XRT 8.5; +refiner 9.0; +stabilizer 8.8; both 9.6.
- Fig. 6 is a qualitative syringe comparison.
- No policy is trained on the collected data. "Data collection efficiency" is measured as throughput only.
- The text's labels don't match the table: Table III lists "XRT-T + controller" (96.4 Hz), but the text says "When tactile sensing is enabled, the control frequency further increases to 96.4 Hz".

**f. Scope.** Real robots: dual UR5e with Robotiq grippers (two 6×5 piezoresistive arrays each), Realhand L6 hands (five 12×6 arrays each), and Inspire RH56DFX (no tactile).

**g. Author-stated limitations / future work.**
- The only future-work statement (§VI) is: "In future work, we plan to extend the system to more complex industrial manipulation scenarios."
- There is no limitations section.
- Data-quality framing: "Collecting high-quality robot data for contact-rich manipulation tasks is essential"; "existing data collection solutions often lack the capability to obtain stable and high-frequency tactile feedback" (Abstract). "because human input is inherently imperfect, even small, unintentional hand movements by the operator can lead to excessive force application and task failure" (§I).

**h. Follow-ups.** None seen (v1 2026-09-14).

**i. Unverified.**
- The refiner's VLA architecture and training data are not specified (grep found only π0/OpenVLA in related work).
- The on-disk recording format (file type) is not specified. Neither is the synchronization mechanism behind "synchronized ... and timestamped".

**Flags.**
- Teleop demos: YES. XR: YES (PICO 4 Ultra over WiFi). ROS: not mentioned.
- Action-label vs observation mismatch: potentially YES by design (fused operator + VLA action), but the authors do not discuss it.
- Dataset provenance/hash/sign: none. Replay verification: none.
- Time sync: claimed ("timestamped to maintain temporal consistency") but not specified. Multi-rate loops: 90 Hz controller, 20 Hz stabilizer, 7 Hz refiner.

**Citation edges.**
- → XRoboToolkit: "[2] Z. Zhao, L. Yu, K. Jing, and N. Yang (2025) Xrobotoolkit: a cross-platform framework for robot teleoperation. arXiv preprint arXiv:2508.00097."
- → Isaac Lab: "[16] M. Mittal, P. Roth, J. Tigue, A. Richard, O. Zhang, P. Du, G. State, et al. (2025) Isaac lab: a gpu-accelerated simulation framework for multi-modal robot learning. arXiv preprint arXiv:2511.04831."
- → ALOHA: "[12] T. Zhao, V. Kumar, S. Levine, and C. Finn (2023) Learning fine-grained bimanual manipulation with low-cost hardware. Robotics: Science and Systems XIX."
- → Open-TeleVision: "[14] X. Cheng, J. Li, S. Yang, G. Yang, and X. Wang (2024) Open-television: teleoperation with immersive active visual feedback. In Conference on Robot Learning (CoRL)".
- → AnyTeleop: "[10] Y. Qin, W. Yang, B. Huang, ... (2023) AnyTeleop: a general vision-based dexterous robot arm-hand teleoperation system. In Robotics: Science and Systems (RSS)".
- Others (not in the keyword list): Twist2 [3] (arXiv:2511.02832) as baseline, and SONIC [4].
- No hits for LeRobot, robomimic, DROID, OXE, GELLO, Bunny-VisionPro or any security paper.

---


---

# Part B — Broader search (areas 1–8)

## Area 1 — Poisoning/backdoors of IL / DP / VLA via demonstrations

### 1.1 Dataset Poisoning Attacks on Behavioral Cloning Policies — FULL
- Kalra et al.; arXiv 2511.20992 (v2 dated 2026-07-28); venue not stated on page. https://arxiv.org/html/2511.20992
- Contribution: claims first study of dataset poisoning of BC policies (no reward); visual triggers (patches/Gaussian noise) injected into obs of state–action pairs for a target action; action labels unchanged; low budgets (~2.31% overall corruption).
- Threat model: dataset contributor edits observations only. Policy: small CNN BC (no DP/ACT/VLA).
- Stage: training data (observation modality). Detection/repair: none evaluated.
- Limitations (Limitations/Conclusion): "Future work should see if these trends hold across other environments and other imitation learning algorithms"; attacks "limited to the visual observation space (the adversary has no direct action manipulation ability)."
- XR/ROS: none.

### 1.2 DropVLA: An Action-Level Backdoor Attack on Vision–Language–Action Models — FULL
- Xu, Li, Zhao, Zheng, Ma, Jiang; arXiv 2510.10932 (v5 2026-09-10). https://arxiv.org/html/2510.10932v5
- Contribution: action-level backdoor forcing a reusable primitive (open_gripper) at trigger onset via "window-consistent relabeling" of action labels in chunked fine-tuning; 0.31% episode poisoning -> ~99% ASR, ~99% clean retention on LIBERO/OpenVLA-7B; physical π0-fast on Franka 20%/200 trials.
- Threat model: fine-tuning data supplier; modifies action labels + inserts visual/text trigger. No timestamp modification.
- Detection: none evaluated; Discussion suggests runtime gating, trigger-surface audits, "adaptation-time data hygiene including provenance tracking" (proposed only).
- Limitations: "Our study focuses on a single target action and evaluates within the LIBERO benchmark family using OpenVLA-7B." Also notes trigger location drift as camera–robot pose changes.
- XR/ROS: none.

### 1.3 SilentDrift: Exploiting Action Chunking for Stealthy Backdoor Attacks on VLA Models — FULL
- Bingxin Xu, Yuzhang Shang, Binghui Wang, Emilio Ferrara; arXiv 2601.14323; Findings of ACL 2026. https://arxiv.org/html/2601.14323
- Contribution: black-box data-provider attack perturbing delta-pose action labels at approach-phase keyframes with Smootherstep (C2-continuous) drift -> "near-miss" failures; 2% poisoning (one episode per task); 93.2% ASR / 95.3% clean SR on VLA-Adapter, π0 (LIBERO).
- Directly relevant to C1 (partial action modification) AND claims evasion of: human replay verification, jerk/kinematic-based detection, loss-curve analysis, dynamics-based anomaly filters. Defense proposed: Adaptive Chunk Truncation (deployment-time).
- Limitations: page's limitations section is dual-use statement: "The primary limitation of this work lies in the inherent dual-use nature of backdoor attack research..."
- XR/ROS/timestamps: none.

### 1.4 !Imperio, smolVLA: The Implications of Data Poisoning on Open Source Robotics — FULL
- Stefan Bühler, Mark Schutera; arXiv 2607.04146 (2026-07-05). https://arxiv.org/html/2607.04146v1
- Contribution: trigger-word DoS backdoor on smolVLA via LeRobot/HF community datasets; replaces all joint actions of poisoned episodes with fixed configuration, prepends trigger to prompt; 1–3 poisoned episodes in 320 (0.3–1%). Frames the LeRobot/HF sharing ecosystem as lacking "mandatory integrity verification".
- Detection: none; Future work lists "dataset auditing and anomaly detection on training trajectories as practical mitigations".
- Limitations: "it focuses on a single task, model, and robot platform, which allows for controlled evaluation but limits generalisability."
- XR/ROS/signing: none.

### 1.5 Targeting World Models to Compromise Robot Learning Pipelines — FULL
- Rathbun, Agha, Mahmud, Amato, Oprea, Bagdasarian; arXiv 2606.09499 (2026-06-08). https://arxiv.org/html/2606.09499v1
- Contribution: "malicious robot teleoperation data provider" adds imperceptible LAB-space perturbations to demo video frames; activates only after world-model (Cosmos) synthesis -> dangerous synthetic trajectories for VLA BC / PPO. Cosmos guardrail failed to detect.
- Limitations (Sec. 7): "the effectiveness of our Visual Prompt and Transition Hijacking attacks remain unverified in more realistic robot learning pipelines with text and action conditioned world models."
- XR/ROS: teleop named as vector; no XR/ROS.

### Other seen (not detailed): TrojanRobot 2411.11683 (module-level/LVLM backdoor, not demo poisoning; ABSTRACT via search); GoBA 2510.09269 (physical object trigger in training data; search snippet only); VLA Safety survey 2604.23775 (search only).

## Area 2 — Detecting/curating bad demonstrations (attribution & quality)

### 2.1 CUPID: Curating Data your Robot Loves with Influence Functions — FULL
- Agia, Sinha, Yang, Antonova, Pavone, Nishimura, Itkina, Bohg; arXiv 2506.19121 (2025; CoRL 2025 per project materials — venue not verified on page). https://arxiv.org/html/2506.19121
- Contribution: influence of each demo on expected policy return estimated from m evaluation rollouts (25–100); filters harmful demos / selects new ones; <33% curated data -> SOTA diffusion policy on RoboMimic.
- Evaluated harm types: mixed-quality demos, spurious correlations (e.g. background color), brittle strategies. NOT evaluated: adversarial poisoning, corrupted/noisy actions, backdoors.
- Limitations (Sec. 9): "Future work should further investigate how properties of the data dictate the extent to which curation can improve policy performance"; "Estimating performance influences over the full demonstration dataset incurs a computational cost comparable to that of policy training".
- Note for C2: requires rollouts where the harm manifests; a trigger-gated backdoor does not manifest in clean rollouts (my inference, not claimed by authors).
- XR/ROS: none.

### 2.2 DemInf — Robot Data Curation with Mutual Information Estimators — FULL
- Hejna et al. (Google DeepMind / Stanford); arXiv 2502.08623 (v3 Apr 2025). https://arxiv.org/html/2502.08623
- Contribution: per-demo quality score from KSG k-NN mutual information I(S;A) between VAE-embedded states and action chunks; rollout-free.
- Evaluated on: RoboMimic multi-operator tiers; Franka with 50% intentionally poor demos (drops, inefficient paths, jerky motion); RoboCrowd novices. NOT evaluated: deliberately corrupted or misaligned obs–action pairs.
- Limitations: "DemInf considers the aggregate mutual information between states and actions within the dataset...largely ignores the fact that these quantities are linked in the sequential setting via the environment dynamics."; "DemInf assumes that all provided demonstrations are successful at completing the desired task."
- Relevance C2/C3: MI between obs and action is the closest learned "obs–action consistency" score, but not framed adversarially.

### 2.3 Demo-SCORE — Curating Demonstrations using Online Experience — FULL
- Annie S. Chen, Alec M. Lessing, Yuejiang Liu, Chelsea Finn; arXiv 2503.03707 (v2 Jul 2025); RSS 2025 (roboticsconference.org listing seen in search). https://arxiv.org/html/2503.03707v2
- Contribution: classifier trained on policy rollouts (success vs fail) scores and filters original demos; +15–35% abs SR.
- Evaluated: heterogeneous strategies, camera-occluding approaches, multi-operator mixes. Not adversarial.
- Limitations: "Demo-SCORE relies on the assumption that the policy rollouts are representative of the original demonstration distribution..."

### 2.4 DataMIL: Selecting Data for Robot Imitation Learning with Datamodels — ABSTRACT (search snippets/landing)
- Dass, Khaddaj, Engstrom, Madry, Ilyas, Martín-Martín; arXiv 2505.09603; ICLR 2026. https://arxiv.org/abs/2505.09603
- Contribution: datamodels (regression / metagradient) scoring each sample by influence on validation loss; selects data from Open X-Embodiment. Not adversarial.

### 2.5 Quality over Quantity: Demonstration Curation via Influence Functions for Data-Centric Robot Learning — ABSTRACT
- Haeone Lee, Taywon Min, Junsu Kim, Sinjae Kang, Fangchen Liu, Lerrel Pinto, Kimin Lee; arXiv 2603.09056; ICRA 2026. https://arxiv.org/abs/2603.09056
- Contribution: influence on validation-demo loss; motivated by "human errors, operational constraints, and teleoperator variability". Not adversarial.

### 2.6 (Defense, runtime) When Attention Betrays: Erasing Backdoor Attacks in Robotic Policies by Reconstructing Visual Tokens (Bera) — FULL
- Li et al.; arXiv 2602.03153 (Feb 2026). https://arxiv.org/html/2602.03153
- Test-time: Mahalanobis anomaly on visual tokens + attention cues + MAE reconstruction; visual-trigger backdoors only; residual ASR 10–13% on real robots. Does NOT address action-only or timestamp poisoning.
- Limitation quote: "semantically integrated triggers are more challenging to detect."

Other seen: 2609.26868 (skipped per brief) proposes task-aware spatial filtering; "Your Robot Was Trained on a Lie: Collision Mesh Poisoning" 2609.18122 (search title only, not read).

## Area 3 — Robustness to noisy / misaligned action labels, obs–action misalignment

### 3.1 Restoring Noisy Demonstration for Imitation Learning with Diffusion Models (DMDR) — FULL
- Shang-Fu Chen, Co Yong, Shao-Hua Sun; arXiv 2510.14467 (2025-10-16); venue not stated. https://arxiv.org/html/2510.14467
- Noise model: states and actions independently corrupted w.p. p with zero-mean Gaussian ("states and actions ... usually captured by different sensors"). Not adversarial.
- Method: autoencoder + Local Outlier Factor filtering, then conditional diffusion restoration of noisy s/a. Eval: FetchPick/Push, HandRotate, Walker.
- Limitations: "density-based anomaly detectors, such as LOF, are restricted in their performance on an edge case when the noise distribution is uniform."
- Relevance: closest filter+repair for corrupted demos; random noise, would likely not catch smooth targeted edits (cf. SilentDrift C2-continuous) — my inference.

### 3.2 Mind the Gap: Rethinking I/O Design for Contact-Rich Visuomotor Policy Learning — FULL
- Xu et al.; arXiv 2602.08776 (v2 Sep 2026). https://arxiv.org/html/2602.08776
- Studies leader-command vs follower-execution mismatch (latency, gains, backlash, friction) in teleop data (ARX leader/follower, 60 Hz); EC2C conditions on both command and execution histories; latency-adaptive inpainting.
- Limitations (Sec. 5): "The learned mismatch semantics are tied to the teleoperation device, low-level controller, and embodiment."
- Relevance: command–execution mismatch is intrinsic signal; treats it as useful feature, not integrity check. No XR/ROS.

### 3.3 Robust Imitation Learning from Noisy Demonstrations (RIL-Co) — ABSTRACT
- Voot Tangkaratt et al.; AISTATS 2021 (PMLR v130) — pre-2023, background only. https://arxiv.org/abs/2010.10181
- Symmetric-loss classification + co-pseudo-labeling; no noise-distribution assumptions.

(Also seen, not read: "Imitation Learning from a Single Temporally Misaligned Video" 2502.05397 — about human-video temporal misalignment, not obs–action desync in robot logs.)

## Area 4 — Dataset provenance / integrity / validation tooling

### 4.1 LeRobot library (source) — FULL (source code read, commit e0d50211, 2026-09-29) + paper FULL
- Paper: "LeRobot: An Open-Source Library for End-to-End Robot Learning", Cadène et al., arXiv 2602.22818 (2026-02-26). https://arxiv.org/html/2602.22818 . Paper does not discuss dataset validation, timestamp sync, quality checks or security. Limitations (Limitations section) are robot/algorithm coverage and inference optimization.
- Code (https://github.com/huggingface/lerobot): `validate_frame` / `validate_episode_buffer` (src/lerobot/datasets/feature_utils.py) check feature presence, dtype/shape, episode index, non-empty — schema only. `check_delta_timestamps` checks that requested delta timestamps are multiples of 1/fps within `tolerance_s` (default 1e-4). Video decoders (video_utils.py) raise "One or several query timestamps unexpectedly violate the tolerance" when a decoded frame's timestamp is farther than tolerance_s from query. No content hashing/signing of episodes found by grep (hashlib only used for language augmentation seeding); Hub `revision` pins git revision.
- Integrity implication: timestamp checks verify internal consistency of *declared* timestamps vs fps/video PTS; they do not verify timestamps against an independent clock nor obs–action semantic consistency.

### 4.2 RDA — Robot Data Audit (open-source tool, MIT) — FULL (README + blog + audit issue)
- Author GitHub "liesliy"; https://github.com/liesliy/rda ; PyPI robot-data-audit; v0.9.x in Sep 2026. Posts audits to DROID (#82, 2026-09-15), ALOHA, LIBERO, LeRobot repos.
- Checks: timestamp monotonicity, frame-interval consistency, schema; temporal gaps, sensor sync, idle structure; velocity spikes, motion discontinuities; statistical outliers. No obs–action consistency, hashing/provenance or tamper claims. README: "diagnostic, not predictive".
- Blind test blog ("I Poisoned 50 Episodes of LeRobot's PushT Dataset. The Audit Tool caught 40 with zero false..."; dev.to/liesliy): 5 defect classes x10 (empty, NaN state, timestamp reversal, frozen, duplicate frames); precision 1.0 on 156 clean, strict recall 0.8. Authors concede midstream duplicates with monotone timestamps "would likely evade detection"; dataset "unusually easy" so multi-stream sync not exercised. "Poisoned" = crude corruption, NOT adversarial/backdoor. https://dev.to/liesliy/i-poisoned-50-episodes-of-lerobots-pusht-dataset-the-audit-tool-caught-40-with-zero-false-963
- DROID audit: "1,428 action discontinuity spikes detected across 99 out of 100 episodes (99%)" in lerobot/droid_100 — shows natural discontinuity base rate is high (hampers naive spike detectors).

### 4.3 demosift (open-source CLI) — FULL (README)
- https://github.com/christophe17/demosift . Level-0 deterministic checks: format/metadata, robot/camera/fps/codec, state/action dims, episode counts, video span matches episode length within one frame; MAD-outlier episode lengths. Explicitly cannot yet detect timestamp gaps inside episodes, frozen frames, action ranges, video content. No security claims.

### 4.4 DROID: A Large-Scale In-The-Wild Robot Manipulation Dataset — ABSTRACT (+ search snippets on QC)
- Khazatsky et al., RSS 2024, arXiv 2403.12945. Quality control seen in search results only (not verified on primary page): ~16k of ~92k episodes labeled unsuccessful; later post-hoc camera calibration (CtRNet-X/DUSt3R) filtering extrinsics outliers (~1.7%) (Medium blog by Z. Irshad). Mark as UNVERIFIED detail.

### 4.5 Preventing Machine Learning Poisoning Attacks Using Authentication and Provenance (VAMP) — ABSTRACT
- Jack W. Stokes, Paul England, Kevin Kane (Microsoft); arXiv 2105.10051 (2021; pre-2023 background). Cryptographic authentication + provenance manifests over data/labels/software/model (SHA-2). Generic ML, not robotics; abstract does not treat a malicious authorized signer (i.e., signing does not stop an insider who records then edits before signing).

### 4.6 Replicable Simulation-Based Robot Validation through Provenance — ABSTRACT
- Ortega, Wiest, Pasch, Hochgeschwender; arXiv 2605.29973; IEEE ERAS 2026. W3C-PROV/FAIR-style provenance for sim-based robot test datasets; no hashing/signing mentioned in abstract; not about demonstrations.

(Seen, not read: Sentry 2510.00554 "Authenticating ML Artifacts on the Fly"; 2503.22573 "Framework for Cryptographic Verifiability of End-to-End AI Pipelines"; OpenSSF model-signing (models, not datasets).)

## Area 5 — Cross-modal consistency & timestamp synchronization

### 5.1 Universal Manipulation Interface (UMI) — FULL (PDF text)
- Cheng Chi, Zhenjia Xu, Chuer Pan, Eric Cousineau, Benjamin Burchfiel, Siyuan Feng, Russ Tedrake, Shuran Song; arXiv 2402.10329; RSS 2024 (roboticsproceedings.org/rss20/p045 in search results). https://arxiv.org/abs/2402.10329
- Contribution relevant here: physically measured per-stream latency (camera via QR-code timestamp display, App. A1; proprioception; gripper/arm execution latency e.g. 120 ms/100 ms), inference-time observation alignment to the highest-latency stream and action latency compensation (PD1). "Kinematic-based data filtering" (HD6): SLAM-recovered EE poses filtered for embodiment kinematic/dynamic feasibility.
- Limitations (Sec. VIII): "we rely on data filtering to ensure the kinematic feasibility of the resulting policy"; "our SLAM-based action recovery system inherits visual SLAM's requirement for sufficient texture".
- Relevance C3/C4/C6: engineering-grade timing calibration & feasibility filtering, benign (not adversarial); tracking source is SLAM not XR.

### 5.2 LeRobot timestamp tolerance checks — see 4.1 (declared-timestamp vs fps/video-PTS consistency, default 1e-4 s).
### 5.3 RDA sensor-sync / timestamp monotonicity / gap checks — see 4.2 (benign-defect detection; multi-stream sync not exercised in their blind test).
### 5.4 Mind the Gap (2602.08776) — see 3.2 (command vs execution mismatch).

(Attempted: Correll-lab Medium post claiming "sub-frame misalignment between state and action quickly degraded policy performance" — HTTP 403, NOT read; quote seen only in search summary, do not cite.)

## Area 6 — Replay verification of demonstrations

### 6.1 robomimic playback_dataset.py — FULL (source read, master branch, 2026-09-30)
- https://github.com/ARISE-Initiative/robomimic/blob/master/robomimic/scripts/playback_dataset.py
- With `--use-actions`, replays recorded actions and compares each step's sim state to the recorded next state: `if not np.all(np.equal(states[i + 1], state_playback)): ... print("warning: playback diverged by {} at step {}")`. Only a printed warning; no threshold, no rejection, no sim-to-real analogue. Sim-only (MuJoCo states).
### 6.2 robosuite "Human Demonstrations" docs — FULL
- https://robosuite.ai/docs/algorithms/demonstrations.html : "action playback trajectories are quite similar even if not completely identical to the original collected state trajectories, they do tend to drift over time"; "action playback is NOT guaranteed (in fact, very unlikely) to work across platforms or even across different machines". Recommends state replay. No integrity checks.
- Implication: benign replay divergence is expected, so a replay-divergence detector needs a tolerance model — a gap an attacker can hide inside (inference).
### 6.3 MimicGen (Mandlekar et al., CoRL 2023, PMLR v229) — ABSTRACT + source grep
- https://proceedings.mlr.press/v229/mandlekar23a/mandlekar23a.pdf ; generate_dataset.py tracks num_success/num_failures/num_problematic; generated trajectories kept only on task success (success filtering). Filters generated data, does not verify seed human demos' integrity.
### 6.4 Learning to Stack: Cube-Stacking Imitation Learning from Virtual Reality Demonstrations — FULL
- Gryffin Reizian, Jordan Dowdy, Jean Chagas Vaz; arXiv 2609.19040 (2026-07-20); IEEE NAECON 2026. https://arxiv.org/html/2609.19040
- XR: HTC Vive Pro 2 + Manus gloves via OpenXR; Pink IK to 5-DoF arm (sim). "each trajectory is then replayed to verify reproducibility and converted from inverse-kinematics pose actions into joint-space position sequences." No reported failure rates / rejection criteria.
- Limitations (Sec. V): "synthetic trajectory generation still depends on seed-demonstration quality and replay consistency."
- Relevance: XR-collected demo + replay check exists, but as a benign reproducibility step. No ROS.
(Isaac Lab replay tooling skipped per brief.)

## Area 7 — XR teleop retargeting/calibration errors in collected data

### 7.1 Open-TeleVision: Teleoperation with Immersive Active Visual Feedback — FULL
- Xuxin Cheng, Jialong Li, Shiqi Yang, Ge Yang, Xiaolong Wang; arXiv 2407.01512 (2024; CoRL 2024 per common knowledge — venue not verified on page). https://arxiv.org/html/2407.01512
- Does NOT document tracking/retargeting/latency/recording errors or demo filtering; only "input end-effector poses are smoothed using an SE(3) group filter".
- Limitations (Sec. 5): "A system that enables the relabeling of expert data could be very helpful for increasing success rate, which is also missing from our system now." No ROS (Vuer web server).
### 7.2 Bunny-VisionPro: Real-Time Bimanual Dexterous Teleoperation for Imitation Learning — FULL
- Runyu Ding, Yuzhe Qin, et al.; arXiv 2407.03162 (2024). https://arxiv.org/html/2407.03162
- Limitation: "Vision Pro's hand tracking is inaccurate when fingers are self-occluded, causing jerky control commands." No retargeting-error metrics, no demo rejection criteria (50/30 demos collected). No ROS.
### 7.3 DexCap: Scalable and Portable Mocap Data Collection System for Dexterous Manipulation — FULL
- Chen Wang et al.; arXiv 2403.07788 (2024; RSS 2024 — not verified on page). https://arxiv.org/html/2403.07788v1
- Mocap (EMF gloves + SLAM), not XR. Notes frame-rate drop "may affect SLAM tracking accuracy, potentially leading to jumping tracking results"; manual point-cloud alignment UI; optional human-in-the-loop correction. No systematic filtering. No ROS.
### 7.4 AnyTeleop — ABSTRACT
- Qin, Yang, Huang, Van Wyk, Su, Wang, Chao, Fox; RSS 2023; arXiv 2307.04577. Abstract silent on errors/filtering.
### 7.5 ARCap: Collecting High-quality Human Demonstrations for Robot Learning with Augmented Reality Feedback — FULL
- Sirui Chen, Chen Wang, Kaden Nguyen, Li Fei-Fei, C. Karen Liu; arXiv 2410.08464 (2024). https://arxiv.org/html/2410.08464
- Collection-time AR feedback against kinematic infeasibility (joint speed limits), collisions, camera FOV; user may "delete the demonstration with severe constraint violations". No post-hoc validation. No ROS.
### 7.6 VR-DAgger: Immersive VR for Dexterous Data Collection and Uncertainty-Guided On-Policy Correction — FULL
- René Zurbrügg, Tifanny Portela, Arjun Bhardwaj, et al. (ETH RSL); arXiv 2605.27114 (v2 2026-05-28). https://arxiv.org/html/2605.27114
- Strongest XR-specific data-quality mechanism found: "we continuously monitor the alignment between the tracked human hand and the robot end-effector pose used for retargeting... we pause recording when the mean keypoint error exceeds a threshold τ (15 cm in all experiments)." Logs time-aligned obs/actions with timestamps. Meta Quest + OpenXR/Unity; ROS 1/UDP data plane, optional ROS 2.
- Limitations: "Our evaluation is currently limited to simulation and a single dexterous hand embodiment."
- Relevance C6: benign online gating of retargeting error at recording time; no post-hoc/adversarial verification.
(ACE, HATO not fetched due to budget; XRoboToolkit skipped per brief.)

## Area 8 — Security of ROS 2 recording (rosbag2 / MCAP)

### 8.1 MCAP specification — FULL. https://mcap.dev/spec
- Only CRC32 (chunk, data section, summary, attachment); value 0 disables/means unavailable. No cryptographic signature/authentication in the format. CRC is recomputable by any editor -> not tamper-evident.
### 8.2 rosbag2 source — FULL (grep, commit 7aac3bd0, 2026-09-28). https://github.com/ros2/rosbag2
- No SHA/HMAC/signature/OpenSSL use (only "function signature" hits). MCAP plugin exposes noChunkCRC/noAttachmentCRC/enableDataCRC/noSummaryCRC; presets "fastwrite" (noSummaryCRC) and "zstd_fast" (noChunkCRC) disable CRCs.
### 8.3 Black Block Recorder: Immutable Black Box Logging for Robots via Blockchain — ABSTRACT (search-result abstract text only; PDF not retrievable)
- Ruffin White, Gianluca Caiazza, Agostino Cortesi, Young Im Cho, Henrik I. Christensen; IEEE RA-L, Oct 2019 (pre-2023 but direct prior art). https://ieeexplore.ieee.org/document/8764004/
- rosbag2 plugin; DSA signatures + HMAC; 2D hash-chain making bag DB append-only; checkpoints to permissioned ledger. Threat: "unsupervised physical system access or postmortem collusion could result in the truncation or alteration of prior records". => post-recording tamper evidence; does not address an insider/compromised source writing false data at record time (my reading of abstract).
### 8.4 Event-driven Fabric Blockchain – ROS 2 Interface: Towards Secure and Auditable Teleoperation of Mobile Robots — ABSTRACT
- Lei Fu, Salma Salimi, Jorge Peña Queralta, Tomi Westerlund; arXiv 2304.00781 (2023). Hyperledger Fabric bridge for auditable teleop commands; latencies in hundreds of ms. Not demonstration datasets / not learning.

