# Limitation Matrix

Two views: (1) what the authors themselves say is missing (`AUTHOR_STATED_LIMITATION`, exact wording in the
per-paper sections below and in KEY_PAPERS.md), and (2) which candidate claims of this study already collide
with prior art.

## 1. Author-stated limitations relevant to demonstration integrity

| Paper | Stage attacked / studied | Attacker's assumed access | Relevant author-stated limitation or open problem | Touches XR? ROS? teleop collection path? |
|---|---|---|---|---|
| BadVLA 2505.16640 (NeurIPS 2025) | training (clean-label, objective-decoupled) | training pipeline / model supply chain | §6: targeted backdoors "beyond the scope"; App. C: need "detection, verification, and behavior-level auditing" | no / no / no |
| State Backdoor 2601.04266 | dataset (state + opposite-action labels, 10 %) | black-box data poisoning (§IV) | §VIII: detection/certification frameworks; signatures for **model** provenance (watermark); §IX defenses future work | no / no / real SO-101 data but no collection-path attacker |
| 2609.26868 industrial | dataset (physical trigger + action-segment edits) | dataset of teleop demos | §V: defense misses in-task and multimodal triggers; suggests "cross-modal consistency checks" | no / no / teleop demos used, attacker after collection |
| RoboCurate 2602.18742 | synthetic data quality (sim replay + video-action classifier) | none (benign) | no limitations section; simulator not named; sim-to-real gap (§5) | no / no / no |
| SoK 2606.16788 | survey | — | Lim. 4 / C4: missing "provenance records … runtime traces"; OP7: end-to-end evidence mechanism "remains an open problem" | no / no / no |
| Survey 2608.16843 | survey | — | §5.6: "state provenance, sensor-to-state consistency, temporal consistency"; §10.2 provenance first-class; §10.3 cross-modal checks | no / no / no |
| XRoboToolkit 2508.00097 | teleop + data collection framework | — | §V: PICO-specific body model, retargeting assumptions, MuJoCo only; no data-integrity mechanism | yes / partly (ROS 1 in code, see SOURCE_AUDIT) / yes |
| Isaac Lab 2511.04831 | sim framework incl. teleop + Mimic | — | §7: evaluation overhead; no statement on demo integrity/provenance | via IsaacTeleop / no / yes (HDF5) |
| XRoboToolKit-T 2609.16437 | tactile teleop | — | only "extend to industrial scenarios" | yes / not stated / yes |

## 2. Prior-art collision for the candidate claims

| Claim | Strongest prior art (this search) | Collision level | What remains open (to my knowledge, uncertain) |
|---|---|---|---|
| C1 partial modification of recorded demos (actions/obs/timestamps) implants backdoor / degrades policy | SilentDrift 2601.14323 (smooth delta-pose action edits, 2% poison, evades replay/jerk/loss checks); DropVLA 2510.10932 (action relabel, 0.31%); !Imperio smolVLA 2607.04146 (LeRobot action replacement, 0.3–1%); BC poisoning 2511.20992 (obs); world-model 2606.09499 (teleop-provider video perturbation) | HIGH for actions & observations | Timestamp-only / temporal-shift manipulation as attack vector not found; XR-pipeline-level (tracking stream/retargeting/calibration) injection point not found; ROS-bag-level edits not found |
| C2 detect poisoned/corrupt demos via attribution/quality | CUPID 2506.19121, DemInf 2502.08623, Demo-SCORE 2503.03707, DataMIL 2505.09603, Lee et al. 2603.09056; DMDR 2510.14467 (LOF on Gaussian noise); RDA blind test (crude corruption) | MEDIUM: methods exist, none evaluated against adversarial/backdoor demos | Evaluating curation methods vs. SilentDrift/DropVLA-style poisoning appears unaddressed; trigger-gated harm likely invisible to rollout-based influence (inference) |
| C3 obs–action consistency checks | DemInf MI(S;A) score (benign); Mind the Gap 2602.08776 (command–execution mismatch as feature); UMI kinematic feasibility filter; VR-DAgger online hand–EE keypoint error gate | LOW–MEDIUM | No post-hoc adversarial obs↔action (e.g., action vs observed proprio/vision motion) integrity verifier found |
| C4 timestamp alignment checks in dataset tooling | LeRobot tolerance_s/check_delta_timestamps + video PTS tolerance; RDA monotonicity/gap/jitter/sensor-sync; demosift video-span check; UMI latency measurement | MEDIUM (benign sanity checks exist) | All checks test self-consistency of declared timestamps; consistent forged timestamps pass (RDA concedes monotone duplicates evade) |
| C5 provenance via hashing/signing | Black Block Recorder (RA-L 2019, rosbag2 signed hash-chain + ledger); VAMP 2105.10051 (generic ML); DropVLA proposes "provenance tracking"; MCAP/rosbag2 CRC only; LeRobot Hub git revision only | MEDIUM (ROS-level signed logging exists, dated) | Signing does not address a malicious recorder/insider; no robot-learning dataset (LeRobot/RLDS) signing scheme found; binding signed raw ROS logs to derived training datasets not found |
| C6 XR-specific tracking/retargeting errors in recorded demos | VR-DAgger 2605.27114 (15 cm keypoint gate, Quest/ROS); Bunny-VisionPro (self-occlusion jerk); ARCap (AR feasibility feedback); Open-TeleVision (SE(3) filter, no filtering) | LOW–MEDIUM (acknowledged, benign, online) | Systematic characterisation of XR tracking/retargeting/calibration error in stored datasets, and distinguishing benign XR error from adversarial edits, not found |

Additional collision observed in source code (not literature), see `systems/SOURCE_AUDIT.md`:
- Command-vs-state separation is *already implemented* in Isaac Lab's recorder (`actions`,
  `processed_actions`, `states`), and state-replay comparison already exists (`replay_demos.py --validate_states`).

## 3. What no checked source addresses (candidate openings, DERIVED_HYPOTHESIS — to be tested in PHASE 2–3)

| Opening | Why it might matter | What would make it void |
|---|---|---|
| O1 An attacker with *limited* authority inside the collection path (XR input provider, one ROS publisher, recorder field) | All published attacks assume dataset write access | No real limited boundary exists in the public collection paths (then NO_REAL_THREAT_BOUNDARY) |
| O2 Temporal / timestamp manipulation as an integrity attack | Only benign self-consistency checks exist (C4) | Datasets store synthetic timestamps anyway (then nothing to manipulate beyond generic data editing) |
| O3 Distinguishing benign XR error from tampering | Natural base rate of discontinuities is high (RDA: 99/100 DROID episodes) | It reduces to generic anomaly detection with no XR-specific signal |
| O4 Binding raw collection logs (MCAP/rosbag2) to the derived training dataset | Signing exists for logs, not for derived datasets | Standard content-addressing / hash manifests already solve it (then NO_METHOD_GAP) |
