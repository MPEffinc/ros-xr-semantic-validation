# New-gap literature matrix

Cutoff 2026-09-30. Compiled from three parallel literature passes (ROS 2 systems; XR security /
teleoperation / HRI; embodied AI / runtime assurance / teleop security). Each entry carries its own evidence
level: **A** full text read, **B** abstract/metadata, **C** README/docs, **D** inference.

Provenance caveats (recorded before use):
- arXiv IDs cited in `../docs/08_new_gap_search.md` were checked to exist with matching titles via the arXiv
  API on 2026-09-30 (17 IDs).
- Part 2 quotes from PDFs were taken from `pdftotext` output after one WebFetch summary was found to
  fabricate content; entries resting on a summary only are marked there.
- Part 3 quotes come from WebFetch extraction (model-summarised), **not verbatim copy**; treat them as
  paraphrase-level until re-checked against the source.
- ACM pages returning 403 (Deng et al. CCS'22, Wang et al. AsiaCCS'24, RoboRebound EuroSys'25) are level B.

---

# Part 1 — ROS 2 security, real-time, monitoring, tracing, middleware, isolation, forensics

Cutoff 2026-09-30. Evidence: A = full body read (arXiv/NDSS PDF -> pdftotext, grepped sections quoted), B = abstract / publisher metadata (Semantic Scholar API or project page), C = README/docs, D = my inference (labelled "D:").
Fields abbreviated: Prob / Threat / Sys / Method / Eval / Assump / Limit (quote, section) / Future / Follow-up / Generic-solvable? / XR-ess? ROS-ess? / Gap / Ev.

---
## Category 1 — ROS 2 security (SROS2 / DDS Security / access control / attacks / fuzzing)

### 1.1 Deng, Xu, Zhou, Zhang, Liu. "On the (In)Security of Secure ROS2." ACM CCS 2022. DOI 10.1145/3548606.3560681
- Prob: whether SROS2 actually delivers its security goals. Sys: ROS2 + DDS Security plugins, multi-robot testbeds (Open Robotics / AWS RoboMaker workloads).
- Method: formal model of ROS2 comm workflow in a concurrent modeling language + model checking -> 4 SROS2 vulnerabilities; defense via private broadcast encryption. Eval: simulation + physical multi-robot; project page: "100 repetitions of each attack".
- Threat: adversary able to obtain unauthorized permissions / steal info despite SROS2 (abstract: "totally invalidate the security protection offered by SROS2").
- Outcome: mitigation (certificate revocation) merged into ROS2 rolling (project page sites.google.com/view/secure-sros2).
- Limit/Future: not accessible (ACM PDF 403). Follow-up: 48 citations (S2), incl. multi-tenant ROS 2 (ICRA'25), DDS discovery DoS (DATE'26), supply-chain SROS2 (MILCOM'25), Zero-trust fleets (2026).
- Generic-solvable? Revocation/PKI hygiene = generic. XR-ess: no. ROS-ess: yes (SROS2 semantics).
- Gap (D): identity-level authN/Z only; nothing about *what* an authorized participant (e.g., an XR operator app) is allowed to cause physically.
- Ev: B (S2 abstract + project page).

### 1.2 Wang, Li, Guan. "A Formal Analysis of Data Distribution Service Security." AsiaCCS 2024. DOI 10.1145/3634737.3656288
- Method: ProVerif model of DDS Security goals/flow; found permission-file impersonation, DoS, degradation, privacy-leakage attacks; mitigations proposed. Threat: Dolev-Yao-style network attacker (D: inferred from ProVerif use).
- Follow-up: 6 cites; "Data Distribution and Redistribution – formal & practical analysis of DDS Security" (ACM SAC 2025, DOI 10.1145/3672608.3707869, not read).
- Generic-solvable: protocol fixes. XR-ess no; ROS-ess partially (DDS, not ROS-specific).
- Ev: B.

### 1.3 Mayoral-Vilches, White, Caiazza, Arguedas. "SROS2: Usable Cyber Security Tools for ROS 2." IROS 2022, arXiv 2208.02615
- Prob: usability of securing ROS 2 graphs; DevSecOps methodology; case: Nav2 + SLAM Toolbox on TurtleBot3.
- Limit (§ policy generation): "the observation window is only instantaneous and can easily miss asynchronous resource access events" (services/actions ephemeral).
- Limit (§ Discussion/Conclusion): "lack of granularity of security configurations ... difficult to configure encryption and authentication options separately"; "lifecycle management of security artifacts, including updating certificates and keys".
- Future: "more advanced monitoring and introspection capabilities, the extension of SROS2 to other communication middlewares (beyond DDS)".
- Follow-up: LiSA4ROS2 static policy extraction (IROS 2024, B: "precisely analyze 66% of existing repositories").
- Generic-solvable: policy mining/static analysis (yes, being done). XR-ess no. ROS-ess yes. Gap (D): policies are topic-level allow/deny; no notion of temporal or physical-effect-conditioned permissions.
- Ev: A.

### 1.4 Sakib et al. "Supply Chain Exploitation of Secure ROS 2 Systems ... Keystore Exfiltration." MILCOM 2025, arXiv 2511.00140
- Prob: SROS2 root of trust = keystore; trojanized sros2 Debian package exfiltrates keystore via DNS. Sys: Quanser QCar2, ROS 2 Humble, SROS2, RealSense stop-sign routine.
- Threat (§II-A): "The attacker has no physical or root access ... operates upstream in the software supply chain".
- Key finding (§II-A): "Because SROS 2 trust is identity-based, a node launched with stolen credentials is accepted ... ROS 2 permits multiple publishers per topic, so an attacker can race or override /qcar2/user_command".
- Eval: forced braking, sustained acceleration, turning loops; phantom/suppressed stop signs.
- Mitigation (§IV): supply-chain hardening + "semantic checks within subscriber nodes ensures received messages fall within physically plausible ranges."
- Future (§V): "lightweight intrusion detection and provenance verification mechanisms to detect malicious package artifacts before deployment."
- Generic-solvable: yes (reproducible builds, signing, SLSA; range checks). XR-ess no. ROS-ess partial. Gap (D): multiple authenticated publishers on command topic — which one the human intended is not captured (NB: authority handoff is excluded direction).
- Ev: A.

### 1.5 Pandya, Kumar, Pillai, Ganapathy. "Decentralized Information-Flow Control for ROS2" (Picaros). NDSS 2024
- Prob (§I): SROS2 lacks downstream control — "when ObjectDetector consumes a message tagged with the topic Image, it is free to publish this image ... under a different topic name." -> data exfiltration.
- Method: DIFC cast as decentralized multi-authority ABE (Lewko-Waters, BN-254); trusted declassifiers; modifies rclcpp. Assump: SROS2 present by default.
- Eval (§V): "raw cost of encryption and decryption is on the order of a few milliseconds, and increases linearly with the number of tags"; 10 Hz pipelines vs SROS2 baseline.
- Limit: "Picaros currently only supports rclcpp. We plan to add support for Python applications by modifying rclpy in future work."
- Generic-solvable: DIFC is generic OS/distributed-systems idea; novelty = decentralization. XR-ess no (D: XR clients that re-publish camera/point clouds are natural downstream consumers). ROS-ess yes.
- Gap (D): labels on data confidentiality only; no label/flow control for *influence* (integrity: which data may drive actuation) — DIFC integrity side unexplored for ROS 2.
- Ev: A.

### 1.6 Xia, Gao, Shi. "Investigating Security Threats in Multi-Tenant ROS 2 Systems." ICRA 2025 (PDF weisongshi.org)
- Threat (§III-B): "the attacker is one tenant and controls one or more nodes"; Docker OS-level isolation, namespaces & domain IDs enabled; goals = info leakage, privilege escalation.
- Findings (§I): nodes "can exploit hidden methods, such as internal APIs, to escape the privilege inheritance mechanism"; bypass namespace/domain-ID isolation; "break SROS 2 due to the weak bond between nodes and security enclaves"; ROS1-bridge lets attackers "invalidate the security mechanisms of the connected ROS 2 system". Five vulnerabilities (§VIII).
- Measurement: "45 of 54 open-source projects ... utilize ROS 2 packages from external developers". Defense: static topic-collision checker (92.6% TP, ~2.97% FP).
- Limit: no explicit limitation section (D). Generic-solvable: partly (capability-based isolation, MAC). XR-ess: no, but D: XR bridges (rosbridge / Unity TCP endpoint / Zenoh bridge) are a *cross-system bridge* analogous to ROS1-bridge — not analyzed. ROS-ess: yes.
- Ev: A.

### 1.7 Shen et al. "Enhancing ROS System Fuzzing through Callback Tracing" (R2D2). ISSTA 2024
- Method: callback-tracing-guided ROS system fuzzing; B (search snippet + PDF): 3.91x/2.56x coverage vs Ros2Fuzz/RoboFuzz, 39 new vulns.
- Limit (§Discussion): benchmark values from runtime statistics — "the dynamic nature of ROS systems can lead to variability that might not be captured within a fixed sample size."
- Also: RoboFuzz (Kim & Kim, ESEC/FSE 2022), ROZZ, "Broken in Transit" type-confusion fuzzing of ROS 2 deserialization (SII 2026, title only), MDPI survey "A Survey of Fuzzing for ROS-Based Robotic Systems" (Appl. Sci. 2026, not read).
- Generic ROS fuzzing + XR = EXCLUDED direction. Ev: A (R2D2 discussion), others title-level.

### 1.8 Gonzales et al. "Practical Zero-Trust for Mission-Critical Robotic Fleets via Hardware Attestation and Packet Timing Watermarking." arXiv 2609.05741 (Sep 2026)
- Method: TPM 2.0 + ELK/Kismet SIEM + non-crypto inter-packet-delay watermark; kurtosis of IPD detects MitM command injection "with complete detection accuracy"; live ROS 2 Wi-Fi testbed, OSI L2–5 exploits.
- Future (§V): "automated, zero-touch deployment pipeline ... adapt the real-time IPD and TPM loops to support heterogeneous fleets ... UAVs".
- Generic: largely generic network security. XR-ess no. Ev: A.

### 1.9 Shahriar et al. "Temporal Misalignment Attacks against Multimodal Perception in Autonomous Driving" (DejaVu). SaTML 2026, arXiv 2507.09095
- Threat: in-vehicle network attacker delaying frames; assumptions listed A1 gPTP secure, A3 "The ROS-based DDS infrastructure is" trusted — both violated. Result: 1-frame LiDAR delay -> car mAP -88.5%; 3-frame camera delay -> MOTA -73%; Autoware e2e sim.
- Limit (§Attack Limitations): "the attack has not been validated on a physical vehicle platform"; "assumes a high level of knowledge about the target system".
- Relevance (D): shows *time integrity* inside ROS/DDS perception pipelines is an attack surface; XR operator displays fuse the same streams. (Timestamp-validity checking of XR inputs is EXCLUDED.)
- Ev: A.

### 1.10 Surve, Shabtai, Elovici. "SoK: Cybersecurity Assessment of Humanoid Ecosystem." EuroS&P 2025, arXiv 2508.17481 — seven-layer model, 39 attacks / 35 defenses, up to HRI layer. Ev: B (abstract read from PDF header).
### 1.11 Gong et al. "SoK: Security and Privacy of Foundation-Model-Powered Robots." arXiv 2606.16788 (Jun 2026) — F-E-S-G boundary framework. Ev: B.
### 1.12 Al-Batati, Koubaa et al. "ROS 2 in a Nutshell: A Survey." ACM CSUR 2026 — four pillars incl. security & safety, multi-robot. Ev: B.

### 1.13 Sabouri. "Cybersecurity of Teleoperated Quadruped Robots: A Systematic Survey ..." arXiv 2602.23404 (Feb 2026) — KEY for XR
- Six-layer taxonomy incl. "VR/AR operator targeting"; TRL gap: comms defenses TRL 7–9 vs perception/operator defenses TRL 3–5.
- Operator-layer (§III): "if an attacker can shape what the operator sees (and when they see it), they can shape what the operator does—even without touching the robot's onboard stack." Attacks: cybersickness induction, HMD side channels, display content injection.
- Gap 5 (§VI-E) "Operator Degradation Detection and Adaptive Autonomy Transfer": cybersickness detection (91.1% F1) "was obtained in seated VR experiments, not during active teleoperation"; transfer must be "graduated", "stability-preserving", "attack-resistant (an adversary should not be able to trigger autonomy transfer as a means of removing the human from the loop ...)", "reversible".
- Gap 6 (§VI-F): security overhead constant "1–3 ms DTLS per-packet processing" even when "the control loop can tolerate no additional latency"; "formal framework linking physical stability margins to communication QoS requirements ... has not been established".
- Gap 7 (§VI-G): "No published framework correlates weak signals across these layers" (perception, operator interface, control).
- Gap 8: fleet-level wormable exploit containment.
- Author limitation (Abstract): "Platform security assessments rely on publicly available information ... attack success rates are derived from cited studies under controlled conditions".
- Generic-solvable: Gap 6 overlaps QoS/priority (EXCLUDED); Gap 7 generic multi-layer IDS partly; Gap 5 is XR-essential.
- Ev: A.

### 1.14 Lee, Kim, Corsaro, Park. "The Three Dimensions of ROS 2 Middleware." arXiv 2607.01304 (Jul 2026) — survey of 94 studies (see also Cat. 5)
- Limit/Gap (§VI-A3 Security Overhead): "Enabling mandatory security plugins, including encryption and authentication, introduces latency and throughput degradation that directly competes with time-critical data exchange"; "Unprotected discovery services and software-level policy evaluation expose the system to replay attacks and identity spoofing"; proposes delegating crypto to "a dedicated hardware-backed execution context".
- Ev: A.

Category-1 synthesis (D): ROS 2 security literature is about *who may publish/subscribe* (identity, PKI, discovery, DIFC for confidentiality). Nothing found binds a command's *authorization to the perceptual state the human operator saw* — the integrity side of information flow from display->decision->command is unaddressed (see open problems).

---
## Category 2 — ROS 2 real-time & executors (callback chains, end-to-end latency)

### 2.1 (SURVEY) Casini, Chen, Li, Reghenzani, Teper. "A Survey of Real-Time Support, Analysis, and Advancements in ROS 2." LITES 11(1), arXiv 2601.10722 v2 (Apr 2026)
- Scope: executor internals, single/multi-threaded executor RTA, reaction time / data age, DDS delay bounds, message filters, micro-ROS, GPU, tracing tools; taxonomies.
- Metrics (§ reaction time & data age): MRT "latency from an external event to the system's corresponding reaction"; MDA "data freshness ... determined backward from the actuation to the cause". Limitation of Teper et al. baseline: "constrained to a single executor, excluding chains that span multiple executors and thus not supporting distributed systems ... does not incorporate OS-level scheduling overheads".
- Synchronizers (§3.3): ApproximateTime "requires prior knowledge of incoming message timing characteristics, and any inaccuracies ... can significantly degrade performance"; LatestTime "does not guarantee bounded time disparity"; Wu et al. found "a critical flaw ... could lead to unbounded latencies".
- Future (§6): "predictable interaction between ROS 2 and hardware accelerators for AI"; "impact of model uncertainty (e.g., uncertain execution time estimates ... or uncertain arrival patterns) on timing metrics"; "technology transfer ... common view of how the new ROS 2 executor should be designed".
- Security: the survey does not treat adversarial timing (D: grep found "security" only in passing).
- Generic-solvable: classical RT theory. XR-ess: no. ROS-ess: yes.
- Gap (D): all chains are machine-only (sensor->...->actuator); none model a chain that exits ROS into a renderer + human and re-enters as a command (human-in-the-loop cause-effect chain); no adversarial arrival patterns.
- Ev: A.

### 2.2 Sobhani, Choi, Kim. "Timing Analysis and Priority-driven Enhancements of ROS 2 Multi-threaded Executors." arXiv 2408.08440 (RTAS 2023 line; rev. Dec 2024)
- RTA for chains on multi-threaded executors incl. mutually-exclusive callback groups; priority-driven enhancement; Jetson AGX Xavier case study. Assump: known WCETs/periods. Ev: B (abstract from PDF).

### 2.3 Related executor/starvation work (title/abstract level)
- Blass/Brandenburg et al. "A ROS 2 Response-Time Analysis Exploiting Starvation Freedom and Execution-Time Variance" RTSS 2021 (mpi-sws PDF; not read in body). EMSOFT'24 best paper "Thread Carefully: Preventing Starvation in the ROS 2 Multi-Threaded Executor" (SIGBED blog; B): multi-threaded executor can starve callbacks; wait-set refresh fix.
- Ishikawa-Aso, Yano, Azumi, Kato. "Middleware-Transparent Callback Enforcement ..." (CallbackIsolatedExecutor) arXiv 2505.06546 (2025): one OS thread per callback; cost 1.4x inter-process / 5x intra-process vs SingleThreaded. Future: "evaluate our approach on real-world systems such as Autoware". Ev: A (short WIP).
- Yano & Azumi. "Multi-Deadline DAG Scheduling Model for Autonomous Driving Systems" arXiv 2505.06780 (2025): existing CE chain models "struggle to accurately represent ... sync callbacks, queue consumption patterns, and feedback loops". Ev: B.
- Zhu et al. "Scheduling Cause-Effect Chains without Timing Anomalies in End-to-End Latency" arXiv 2604.09102 (2026). Ev: B.
- CROS-RT cross-layer priority scheduling (RTAS 2025) — QoS/priority scheduling = EXCLUDED.

### 2.4 Narayanan et al. "PEERNet: An End-to-End Profiling Tool for Real-Time Networked Robotic Systems." arXiv 2409.06078 (2024)
- Profiling of sensors, networks, DL pipelines; image-based teleoperation of Franka; one-way delay in wireless. Related-work finding: "prior work has not integrated [network profiling] into the benchmarking of networked robotics." No stated security threat model. Ev: A (sections II, VI).

Category-2 synthesis (D): RT analysis gives MRT/MDA bounds for machine-only chains under benign timing. Two unexplored combos: (a) adversarially induced timing (starvation / arrival-pattern manipulation) treated as a *security* property of the bound; (b) cause-effect chains that include an off-ROS rendering stage + human decision (data age of what the operator saw when commanding). (b) is XR-essential; (a) alone is generic RT/security.

---
## Category 3 — ROS 2 runtime monitoring / verification / runtime assurance

### 3.1 (SURVEY/SLR+questionnaire) Caldas, Piñera García, Schiopu, Pelliccione, Rodrigues, Berger. "Runtime Verification and Field-based Testing for ROS-based Robotic Systems." IEEE TSE 2024, arXiv 2404.11498 v3
- Method: literature review + mining ROS repos + questionnaire (55 responses) -> 20 guidelines. Table 4 open challenges: lack of formal specs, field test generation, isolation, oracle, security & privacy, distributed monitoring, monitoring states, richer reactions, imprecise traces.
- Author-stated open problems (§6.5): "Decentralization of the monitoring architecture is identified as an area that has not received much attention"; "Most monitoring tools do not support active reactions, like enforcement, recovery, and explanations ... We did not find guidelines related to this aspect."
- (§6.7): "Runtime verification tools rarely support imprecision in their input traces, e.g., imprecise timestamps, traces with incomplete events or inconsistencies in event sources ... Our guidelines do not provide recommendations or solutions".
- (§6.1) DbC for ROS: "we did not find much use of DbC for robotics in industrial settings ... could be an interesting research direction".
- Generic-solvable: partly (decentralized RV exists in general RV literature). XR-ess no. ROS-ess yes (node lifecycle/hidden state). Ev: A.

### 3.2 Ghaffari Saadat, Ferrando, Dennis, Fisher. "ROSMonitoring 2.0: Extending ROS Runtime Verification to Services and Ordered Topics." FMAS 2024 (EPTCS 411), arXiv 2411.14367
- Prob (§1): original ROSMonitoring ordered messages by receipt only — "if a property needs to monitor several topics, then it is unusual for the messages from more than one topic to be received in the order they were published." Adds service interception + publish-order reordering. ROS1, "partially ROS2". Case: fire-fighting UAV.
- Future (§Conclusions): prove deadlock-freedom; threading; "expand the framework to support ROS actions".
- Assump (D): monitor trusts publisher timestamps for publish-order (no adversary).
- Generic-solvable: yes for ordering (vector clocks / HLC). XR-ess no. Ev: A.

### 3.3 AS2FM: "Enabling Statistical Model Checking of ROS 2 Systems for Robust Autonomy." arXiv 2508.18820 (2025) — SCXML extension for ROS 2 + Behavior Trees -> JANI -> off-the-shelf SMC; design-time. Ev: B.

### 3.4 Desai, Ghosh, Seshia, Shankar, Tiwari. "SOTER: A Runtime Assurance Framework for Programming Safe Robotics Systems." DSN 2019, arXiv 1808.07921
- Simplex RTA (advanced controller / safe controller / decision module) on ROS; limitation of prior RTA (§I): apply RTA "to a single untrusted component ... or wrap the large monolithic system into a single instance". Assump: DM monitors plant state periodically, Δ-lookahead. Ev: A (intro).
- Follow-ups: Black-Box Simplex (arXiv 2102.12981), Mission-Level RTA for AD (arXiv 2606.06996, 2026), Synergistic Simplex (arXiv 2605.08190, 2026) — titles only.
- Gap (D): RTA treats the *advanced controller* as untrusted; a human XR operator as the "advanced controller" whose inputs are conditioned on a (possibly stale/manipulated) rendered view is not modelled — DM checks plant state, not the operator's perceptual basis.

### 3.5 Li, Wang, Wang, Stenmark, Krueger. "Quest2ROS2: A ROS 2 Framework for Bi-manual VR Teleoperation." arXiv 2601.18289 (Jan 2026) — XR<->ROS 2 system model
- Sys: Meta Quest -> relative-pose control -> ROS 2 arms; RViz; pause-and-reset.
- Safety (§3.2): tracking degradation "could cause the controller to send random commands and lead to unexpected behavior from the robotic arm"; button-priority conflict -> "system sometimes struggles to prioritize between our custom button functions and the coordinate alignment function".
- Future (§4): finer gripper control; homing; "A more robust controller button priority logic".
- No threat model. (XR input validity = EXCLUDED.) Ev: A.

Category-3 synthesis (D): RV monitors observe ROS topics; monitors assume trace precision and benign sources; "richer reactions" (enforcement/recovery/explanation) are author-stated open. None monitor properties that relate *what an operator was shown* to *what was commanded* (a cross-boundary property spanning XR renderer + ROS).

---
## Category 4 — ROS 2 tracing / observability

### 4.1 Bédard, Lütkebohle, Dagenais. "ros2_tracing: Multipurpose Low-Overhead Framework for Real-Time Tracing of ROS 2." RA-L 2022, arXiv 2201.00393
- LTTng-based instrumentation of rcl/rclcpp/rmw; e2e latency overhead "on average 0.0033 ms" with all instrumentation.
- Limit/Future (§VII): "primarily aimed at offline monitoring and analysis, the instrumentation itself could be leveraged for online monitoring ... LTTng live mode"; other OS backends (QNX); analyze executor determinism.
- No security threat model (D: tracing trusts the traced host). Ev: A.

### 4.2 Bédard, Lajoie, Beltrame, Dagenais. "Message Flow Analysis with Complex Causal Links for Distributed ROS 2 Systems." RAS 2023, arXiv 2204.10208
- One-to-many / many-to-many causal links input->output messages; indirect links via user annotations.
- Assump (§V): "traces collected from multiple computers usually do not have the same clock reference ... The time synchronization method and its precision should of course be taken into consideration".
- Future (§VIII): split transport vs executor wait (needs DDS instrumentation); multi-threaded executors; /tf listener; "extend this work to include ROS 2 services and actions"; critical-path analysis.
- Ev: A.

### 4.3 Recent follow-ups (2025–2026; from S2 citation list of ros2_tracing)
- Ito et al. "BA-TRACE: Boundary-Aware Trace Reconstruction ... Mixed AUTOSAR Adaptive and ROS 2" arXiv 2609.19699 (Sep 2026): reconstructs e2e graph across DDS–SOME/IP boundary via bridge instrumentation. Author caveat (Abstract): "The reconstructed topology is used as evidence of traceability, not as proof of behavioral correctness or safety." Future (§Conclusion): broader scenarios, placements, "automated scenario generation and search-based testing ... across the DDS–SOME/IP boundary". Ev: A. (D: the structural analogue for XR<->ROS boundary exists; cross-boundary trace-ID provenance/log aggregation are EXCLUDED, so this is a prior-art blocker, not a gap.)
- Yu, Lee, Choi, Park. "ros2probe: Non-intrusive, Kernel-selective Observability for ROS 2 Middleware" arXiv 2606.10746 (Jun 2026): defines "observer's probe effect" — a DDS observer "inflates the discovery plane, adds deserialization cost ... near saturation displaces the subscriber's own messages". In-kernel filter. Future: "leave support for non-DDS transports such as Zenoh to future work." Ev: A (abstract+grep). (Observer isolation / eBPF = EXCLUDED; relevant as blocker: an XR visualizer subscribing to ROS is exactly such an observer.)
- Others (title-level, B): "Data Age Analyzer: Non-Intrusive Data Age Tracing for Real-Time ROS 2 Pipelines" (RTCSA 2026 poster); "LeCal: Latency-Aware Curation and Alignment for LeRobot Teleoperation Datasets" (ICCA 2026); DRAPP containerized ROS latency tool (ASP-DAC 2026); CART AUTOSAR+ROS 2 tracing (RSP 2025).

### 4.4 Yano & Azumi. "Toward the Right Analytical Model and System Software for Autonomous Driving Systems: Open Problems and Research Directions." arXiv 2607.04129 (Jul 2026) — open-problem paper (bridges Cat. 2/4)
- (TP2) "How can one analysis reason jointly about E2E latency, response time, freshness, timing disparity, and miss probability? ... an analytical model that treats the full set jointly remains open."
- (TP5) "Binding schedulability to safety across the MRM mode change: What does a timing violation mean for safety ... a model that co-derives all three remains open."
- (PP2) "the ROS 2 publish/subscribe API does not force the message sending of a task to occur at its end ... the model holds only by programmer discipline".
- (PP3) criticality ordering puts "logging or a human-machine interface at the lowest".
- D: PP3's assumption (HMI = lowest criticality) is violated in teleoperation/XR where the HMI is inside the control loop; no analysis found that assigns criticality to an HMI path that carries commands. Ev: A.

Category-4 synthesis (D): tracing is mature and already crosses middleware boundaries (BA-TRACE). Tracing is diagnostic, not assurance ("not proof of ... safety"). Gap-relevant residue: turning timing observations into a *safety-meaningful* judgment (TP5) when the chain includes a human.

---
## Category 5 — ROS 2 middleware (DDS, Zenoh, rmw)

### 5.1 (SURVEY) Lee, Kim, Corsaro, Park. "The Three Dimensions of ROS 2 Middleware." arXiv 2607.01304 (Jul 2026)
- Framework: Space (location transparency) / Time (predictability) / State (continuity); 94 studies; conflicts Space–Time (serialization, fragmentation ~1400-B, intra/inter-host redundancy; multicast "entirely unusable in practice" in swarms of 20+), Time–State (lock contention 5 ms -> 122 ms, liveliness control overhead, retransmission congestion), Space–State (node anonymity, path-blind forwarding, router SPOF).
- Structural gaps (§VI-A): QoS semantic loss ("logical QoS configurations are not propagated into OS kernel scheduling or network-level priority mechanisms"); evaluation inadequacy ("Wireless evaluations underrepresented"); security overhead (quotes in 1.14).
- Roadmap (§VI-B): cross-layer co-design; adaptive middleware; decoupled state architecture.
- Conclusion: "Fully satisfying Space, Time, and State simultaneously ... remains structurally constrained".
- Human/teleop: not discussed (per full read of available text). Ev: A.

### 5.2 Zhang, Yu, Ha, Peña Queralta, Westerlund. "Comparison of Middlewares in Edge-to-Edge and Edge-to-Cloud Communication for Distributed ROS 2 Systems." arXiv 2309.07496 v4 (Nov 2024; J. Intell. Robot. Syst.)
- CycloneDDS best on Ethernet; Zenoh better on Wi-Fi/4G; real robot drift smallest with Zenoh. Security table (§5): mean latency 77.35 ms with SROS2 vs 72.11 ms without (their setup). Ev: A (sections).

### 5.3 Lee, Kim, Chae, Park. "Optimizing ROS 2 Communication for Wireless Robotic Systems." arXiv 2508.11366 (Aug 2025)
- Finds IP fragmentation, retransmission timing, buffer bursts for large payloads over lossy Wi-Fi; XML QoS tuning fix.
- Limit (§Conclusion): "focuses on optimizing periodic communication ... many real-world robotic systems rely on event-driven or aperiodic transmissions ... important direction for future work"; "assumes a one-to-one Pub-Sub communication model".
- (QoS tuning = EXCLUDED direction.) Ev: A.

### 5.4 Choi, Lee, Park. "When Discovery Becomes a Storm: A ROS 2 Discovery Model for Wireless Robotic Networks." arXiv 2608.02242 (Aug 2026)
- First closed-loop analytic model of SPDP/SEDP discovery storms; 1,350 runs / 90 topologies. Future: mesh/cellular networks. No adversary (D: discovery DoS as attack is in DATE'26 "Abusing DDS Discovery", title only). Ev: A (abstract+grep).

### 5.5 Sánchez de la Fuente et al. "AXON: A ROS 2 RMW with Shared-Memory/QUIC Transport and QKD/ML-KEM Key Establishment." arXiv 2609.10024 (Sep 2026)
- Non-DDS RMW; QUIC remote path; hybrid ML-KEM or QKD. Threat (§ threat model): resist passive capture/modification/replay; limitation: "certificates are self-signed and accepted without a CA or pinned fingerprint ... does not authenticate a peer against an active man-in-the-middle ... this is future work." Does not preserve DDS wire interop. Ev: A.
- Related: rmw_zenoh (C: ros2/rmw_zenoh repo, not fetched), "Enhancing ROS 2 security with standardized post-quantum cryptosystems" (IJIS 2025, title).

Category-5 synthesis (D): middleware research optimizes Space/Time/State for machine flows; security is an overhead term. XR clients are typically *outside* DDS (rosbridge/WebSocket, Unity TCP connector, Zenoh bridge) — the security semantics at that bridge (who the XR device is to SROS2) are not analyzed in any paper found in this category.

---
## Category 6 — Provenance / forensics / black-box recorders / accountability

### 6.1 Winfield, van Maris, Salvini, Jirotka. "An Ethical Black Box for Social Robots: a draft Open Standard." TAROS 2022, arXiv 2205.06564
- EBB = "device, or software module, capable of securely recording operational data (sensor, actuator and control decisions) ... to support the investigation of accidents or near-miss incidents." Record format includes separate EBB clock and robot clock ("botT is needed in case the robot's clock shows a different time to the EBB's clock").
- Limit: explicitly "a first draft for discussion". No adversary model (D). Ev: A (standard annex skimmed).
- Predecessor: Winfield et al. "Robot Accident Investigation: a case study in Responsible Robotics" arXiv 2005.07474 (2020) — lists human-factor causes, e.g., "Operator inattentiveness and forgetfulness may lead them to misjudge a situation". Ev: A (intro).

### 6.2 Fernández-Becerra, González-Santamarta, Guerrero-Higueras, Rodríguez-Lera, Matellán-Olivera. "Enhancing Trust in Autonomous Agents: An Architecture for Accountability and Explainability through Blockchain and LLMs." arXiv 2403.09567 v4 (Jul 2025; IEEE Access)
- ROS/ROS 2 black box: rosbag + hashes of selected messages to blockchain; RAG+LLM explanations of navigation.
- Eval (§VII): "hashing one of every 100 messages resulted in less than 5% message loss, even for high-frequency topics exceeding 300 Hz"; LLM-judge correctness ≥75%; Cronbach's α 0.9792.
- Future (§VII): extend to other domains; ICL/fine-tuning; hybrid KG retrieval; "Incorporating real-time explanation generation".
- Assump (D): integrity of what is recorded, not whether recorded data equals what a remote operator saw. Generic-solvable: tamper-evident logging is generic (e.g., "Accountability of Things" arXiv 2308.05557, ~8 KB/hour/device). XR-ess no. ROS-ess partial. Ev: A.

### 6.3 Janarthanan & Zargari. "Forensic Investigation in Robots." Latin-American J. of Computing 11(2), 2024 (SHURA PDF)
- ROS/ROS 2 forensics: rosbag parsing challenges, security challenges, network/memory forensics. Ev: B (front matter/headings only).

### 6.4 Imrell, Miotto, Mohammadi Kashani, Conti, Giaretta. "RobResilience: ... Resilience Framework for Cyber-Physical Embodied Systems." CPSIoTSec '26, arXiv 2609.17349 (Sep 2026)
- Runtime predicates δ (tolerable disruption), γ (tolerable degradation), μ (mitigation feasibility) over IDS-derived compromised set; Webots PR2 + ROS2; 8 attack scenarios.
- Threat model (§4): "No human operator is involved."
- Limit (§Limitations): κ set to 0 -> "assuming 100% accuracy is unrealistic". Future (§Future Work): "We inject attacks symbolically rather than as real ROS2 exploits, bypass the IDS entirely by setting κ = 0, and model mitigations as deterministic."
- Gap (D): resilience decision (tolerable vs catastrophic) excludes the human operator both as a disruption source and as a mitigation option. Ev: A.

Category-6 synthesis (D): recorders secure *what the robot logged*; none capture/attest *what a remote/XR operator was presented* at decision time, so post-incident one cannot establish whether an operator command was reasonable given the displayed state (accountability of the human decision). NB: trace-ID provenance and XR–ROS log aggregation are EXCLUDED; the distinct residue is *evidentiary attestation of operator-perceived state*, not ID propagation.

---
## Category 7 — Network / middleware isolation (containers, hypervisors, micro-ROS, partitions)

### 7.1 Yen, Huang, et al. "Jiao: Bridging Isolation and Customization in Mixed Criticality Robotics." arXiv 2605.03641 (May 2026)
- Jailhouse static-partitioning; hard-RT servo cell + soft-RT perception + "operator applications on shared hardware while maintaining strict isolation"; partition boundary treated "as a safety interface"; cell "checks commanded values against predefined envelopes"; "Recovery requires explicit operator acknowledgment to prevent automatic resumption after transient faults."
- Limit (§V): "evaluation focuses on timing isolation under a single workload class (1 kHz EtherCAT manipulator control) ... Quantifying black-channel fault detection via systematic fault injection remains important future work."
- XR-ess no; ROS-ess partial (ROS-style parameter service across cells). Gap (D): envelope checks at partition boundary are static; an operator/XR application partition issuing commands is treated as untrusted-but-benign best-effort. Ev: A.

### 7.2 CSAR: "Containerized System Architecture for Robotics." arXiv 2606.30293 v2 (Jul 2026) — LXC/LXD system containers + ROS 2/DDS + three-layer edge; multi-user orchestration. Security discussed only as LXC features (D). Ev: B/A (abstract+grep).

### 7.3 Runtime Verification Containers for Publish/Subscribe Networks. arXiv 2408.06380 (2024) — RV monitors deployed as containers alongside pub/sub participants (Zenoh-focused, SDV case). Ev: B.

### 7.4 ROSGuard: "A Bandwidth Regulation Mechanism for ROS2-based Applications." arXiv 2506.04640 (2025) — multicore memory-bandwidth regulation at ROS2 level (timing interference). Ev: B.

### 7.5 SERA: "Secure Micro XRCE-DDS Establishment With Remote Attestation" (IEEE, 2025/26; ieeexplore 11357921) — title and search-engine snippet only (page not retrievable): remote attestation in XRCE-DDS handshake; claims 380–795 ms handshake overhead on NUCLEO-L552ZE-Q. Ev: below B (unverified snippet) — do not cite numbers without re-checking.

### 7.6 Multi-tenant Docker isolation broken at ROS layer — see 1.6 (Xia et al., ICRA 2025): containers give OS isolation but "apps can only communicate with each other via the topic mechanism", and namespaces/domain IDs/SROS2 enclaves are bypassable.

Category-7 synthesis (D): isolation work protects *timing and memory* of critical partitions and assumes HMI/operator apps are low-criticality best-effort (cf. Yano & Azumi PP3). For XR teleoperation the operator partition originates commands, so "freedom from interference" is insufficient: the question is which effects a low-criticality partition may *cause* in a high-criticality one (integrity flow), not only whether it can delay it.

---
## Category 8 — Robot cybersecurity SoKs / general surveys

### 8.1 Gong, Chen, Liu, Wang, Lam. "SoK: Security and Privacy of Foundation-Model-Powered Robots." arXiv 2606.16788 (Jun 2026)
- F-E-S-G boundary framework; 96 papers; coded by target / lifecycle / mechanism / access / effect.
- Limitation 1 (§3): "Semantic-to-physical Validation Gap ... evaluations typically focus on model-level outcomes ... rather than examining grounded planning, action generation, or physical execution."
- Limitation 2 (§4): E-layer guardrails "intervene only after sensing, grounding, or reasoning has already shaped intermediate decisions ... physical actions may be irreversible".
- Limitation 3 (§5): "components that are individually trustworthy but introduce new security and privacy risks when integrated into an end-to-end robotic control pipeline ... compositional risk evaluation an important research direction."
- (C4): FM robots "lack unified provenance records, model-update histories, runtime traces".
- Open problems (§7.3): OP1 "how to translate abstract ethical principles, safety requirements, and privacy norms into computable, observable constraints"; OP3 long-horizon "semantic drift ... requires temporal verification frameworks that can monitor intent consistency"; OP6 monitor/policy "circular dependency ... asymmetric monitoring"; OP7 "evidence of what a robot perceived, planned, decided, and executed ... end-to-end evidence mechanism ... remains an open problem."
- Scope: FM-centric; runtime MITM between robot and "its remote operator" appears only as S-layer detection. Prompt-injection+XR = EXCLUDED. Ev: A.

### 8.2 Surve, Shabtai, Elovici. "SoK: Cybersecurity Assessment of Humanoid Ecosystem." EuroS&P 2025 (arXiv 2508.17481 v2)
- Seven-layer model; 39×35 attack–defense matrix with risk-weighted scoring; Pepper, G1 EDU, Digit assessed.
- Operator-UI precedent (§ attacks): Quarta et al. (industrial controller) — unsigned FlexPendant boot image used "to falsify the User Interface (UI), misleading the operator about robot state."
- Defense examples: RIPS-ROS2 per-topic rules on "/teleop/*" with "≈0.8-1.2s reactions" (TIAGo); signed BT-spec monitors aborting illegal transitions "<4ms".
- Conclusion: "critical foundational layers remain dangerously exposed. Cross-layer cascade analysis shows attackers can exploit these gaps". Ev: A (selected sections).

### 8.3 Sabouri 2026 teleoperated quadruped survey — see 1.13 (the only SoK/survey found that treats VR/AR operator targeting as a first-class layer).

### 8.4 Also seen (not read): "Cybersecurity AI: Hacking Consumer Robots in the AI Era" arXiv 2603.08665 (2026); "Offensive Robot Cybersecurity" arXiv 2506.15343 (Mayoral-Vilches, thesis 2025); "Security of Foundation-Model-Powered Embodied Agents ..." arXiv 2608.16843 (2026); "Towards Trustworthy Embodied Intelligence" arXiv 2607.26121 (2026). Titles from S2 citation list only.

Category-8 synthesis (D): SoKs agree that (i) validation stops at model/message level rather than physical effect, (ii) mitigations are layer-local and reactive, (iii) compositional risks at integration seams are open, (iv) accountability evidence of "what was perceived" is missing. Only the quadruped survey places the XR operator in the threat model; there the human is attacked *through* the display.

---
## Category 9 — Multi-robot / fleet security

### 9.1 (SURVEY) Liao, Shi, Zhang, Wang, Sun. "A Survey of Resilient Coordination for Cyber-Physical Systems Against Malicious Attacks." ACM CSUR (arXiv 2402.10505, 2024)
- Node-injection attacks; resilient consensus (MSR family) by physical structure / communication / topology; MRS and smart-grid applications.
- Future (§Conclusion): nonlinear dynamics ("heterogeneity, time delays, and stochasticity should be considered"); multi-dimensional spaces; "interplay between resilient coordination and formal method". Open (§4): "coordination in time-varying graphs still remains an open question."
- Human operator: not in model (D). Generic control-theoretic. Ev: A.

### 9.2 Salimi, Keramat, Westerlund, Peña Queralta. "A Customizable Conflict Resolution and Attribute-Based Access Control Framework for Multi-Robot Systems." arXiv 2308.16482 (2023)
- Hyperledger Fabric ABAC + ROS 2 bridge; user (Operator) and robot attributes; conflict resolution by task priority.
- Future (§VI): ABAC scalability in large MRS; "comparative studies with other access control mechanisms, like SROS2's role-based access control". Ev: A.
- Predecessor: Keramat et al. "Partition-Tolerant and Byzantine-Tolerant Decision-Making ... with IOTA and ROS 2" arXiv 2208.13467 (title).

### 9.3 Gandhi, Cai, Haeberlen, Phan. "RoboRebound: Multi-Robot System Defense with Bounded-Time Interaction." EuroSys 2025, DOI 10.1145/3689031.3696079 — title/authors only (ACM + talk page, no abstract available). FM-SoK 8.1 describes this line as "bounding the time window in which faulty robots can affect others". Ev: B- (secondary description).

### 9.4 Gonzales et al. 2026 zero-trust fleets (1.8); Sabouri 2026 Gap 8 fleet wormable exploit containment (1.13): "Current security architectures treat each robot as an isolated entity, lacking fleet-wide anomaly correlation, coordinated quarantine mechanisms, or cryptographic segmentation".
### 9.5 "Securing Swarms: Cross-Domain Adaptation for ROS2-based CPS Anomaly Detection" MILCOM 2025, arXiv 2508.15865 — domain-adapted IDS (generic ROS IDS = EXCLUDED). Ev: B.

Category-9 synthesis (D): fleet security = Byzantine/consensus + per-robot attestation + IDS. One operator commanding many robots through one XR front-end (1:N supervisory control) is not modelled: a single compromised or misled operator view becomes a fleet-wide common-mode input, which resilient-consensus (which assumes f of n *robots* faulty) does not cover.

---
## FINAL — Open problems explicitly stated by authors that could involve an XR front-end interacting with ROS 2
(Quote = author claim, evidence A unless noted. "Generic coverage" = my assessment (D). Overlap flags vs EXCLUDED list given where relevant.)

OP-1. Operator-degradation detection + attack-resistant autonomy transfer — Sabouri 2026 (arXiv 2602.23404, §VI-E Gap 5)
 Quote: cybersickness detection "was obtained in seated VR experiments, not during active teleoperation"; transfer must be "attack-resistant (an adversary should not be able to trigger autonomy transfer as a means of removing the human from the loop and then exploiting the less-capable autonomous fallback)".
 Generic coverage: PARTIAL — shared-autonomy arbitration and Simplex RTA (SOTER) exist; cybersickness classifiers exist but are adversarially fragile (Kundu et al. cited: 4.65x/5.94x drops). Nothing treats *induced* operator degradation as the trigger an attacker controls. XR-ess yes; ROS-ess moderate. OVERLAP FLAG: close to "authority continuity/lease handoff" (excluded) if framed as handoff; distinct only if framed as adversarial manipulation of the human state that drives the switch.

OP-2. Operator-perception attacks ("shape what the operator sees and when") — Sabouri 2026 §III (operator layer) + Surve et al. SoK (Quarta et al. UI falsification)
 Quote: "if an attacker can shape what the operator sees (and when they see it), they can shape what the operator does—even without touching the robot's onboard stack"; display injection threat "is epistemological rather than computational"; operator-layer defenses at TRL 3–5 (Abstract).
 Generic coverage: PARTIAL — authenticated telemetry (SROS2) protects the ROS link, trusted-UI/secure-overlay work exists outside robotics; neither verifies that the *rendered* XR scene is consistent with ROS ground state. XR-ess yes; ROS-ess yes. OVERLAP FLAG: must not collapse into "safety warning UI" or "XR input validity".

OP-3. Cross-layer weak-signal correlation (perception + operator interface + control) — Sabouri 2026 §VI-G Gap 7
 Quote: "No published framework correlates weak signals across these layers to detect coordinated attacks."
 Generic coverage: PARTIAL — multi-source IDS/SIEM fusion (e.g., Gonzales 2026 ELK/Kismet) is generic. OVERLAP FLAG: high risk of becoming "generic ROS IDS" (excluded) unless the operator-interface layer is the essential signal.

OP-4. Binding timing violations to safety (incl. freshness) — Yano & Azumi 2026 (arXiv 2607.04129, TP2/TP5)
 Quote: TP2 "an analytical model that treats the full set [E2E latency, response time, freshness, timing disparity, miss probability] jointly remains open"; TP5 "What does a timing violation mean for safety ... a model that co-derives all three remains open."
 Context: Casini et al. survey MRT/MDA analyses are machine-only; Teper-style analyses "constrained to a single executor".
 Generic coverage: NO for chains that leave ROS through a renderer and re-enter via a human command (data age of what the operator saw when the command was issued). XR-ess yes; ROS-ess yes. OVERLAP FLAG: avoid "XR timestamp checking" and "QoS/priority scheduling"; the residual is *analysis/semantics* of human-in-loop chain freshness, not enforcement at input.

OP-5. HMI assumed lowest-criticality — Yano & Azumi 2026 PP3 (+ Jiao 2026 partitions)
 Quote: criticality ordering places "logging or a human-machine interface at the lowest"; Jiao: operator applications run as isolated best-effort cells, "Recovery requires explicit operator acknowledgment".
 Generic coverage: PARTIAL — mixed-criticality isolation guarantees freedom from *interference*; not what effects a low-criticality command-originating partition may *cause* (integrity). XR-ess yes (XR HMI originates commands); ROS-ess yes. OVERLAP FLAG: must not become "QoS/priority scheduling" or "XR observer isolation".

OP-6. Compositional risk at integration seams — Gong et al. FM-SoK 2026 (arXiv 2606.16788, Limitation 3) + Xia et al. ICRA'25 (bridges)
 Quotes: "components that are individually trustworthy but introduce new security and privacy risks when integrated into an end-to-end robotic control pipeline ... compositional risk evaluation an important research direction"; Xia: ROS1-bridge lets attackers "invalidate the security mechanisms of the connected ROS 2 system".
 Generic coverage: PARTIAL — bridge hardening (rosbridge optional TLS/auth) is generic; no analysis of XR bridges (rosbridge/WebSocket, Unity TCP endpoint, Zenoh) as an SROS2 trust-boundary seam was found (absence claim limited to this search). XR-ess moderate; ROS-ess yes.

OP-7. Downstream control of data (DIFC) — Pandya et al. NDSS'24
 Quote: "ROS2 does not provide the data owner ... with any primitives that allow it to exert downstream control over how this data is used."
 Generic coverage: MOSTLY — Picaros solves confidentiality for rclcpp ("currently only supports rclcpp"); classical DIFC (integrity labels) conceptually covers influence-flow; unaddressed for non-rclcpp XR clients. XR-ess weak-moderate. Lower priority.

OP-8. Accountability evidence of what was perceived/decided — Gong et al. FM-SoK OP7 + Winfield EBB + Fernández-Becerra 2025
 Quote: "Effective governance ... requires evidence of what a robot perceived, planned, decided, and executed ... How to integrate them into a coherent, end-to-end evidence mechanism ... remains an open problem."
 Generic coverage: PARTIAL — tamper-evident logging/blockchain hashing (Fernández-Becerra: 1/100 hashing, <5% loss at >300 Hz) covers robot-side logs; nothing covers what a remote XR operator was shown. OVERLAP FLAG: HIGH with "trace-ID provenance" and "XR–ROS log aggregation" (excluded) — only a *privacy-preserving attestation of operator-perceived state* angle might be distinct; treat as risky.

OP-9. Richer monitor reactions & imprecise traces — Caldas et al. TSE'24 (§6.5, §6.7)
 Quotes: "Most monitoring tools do not support active reactions, like enforcement, recovery, and explanations"; "Runtime verification tools rarely support imprecision in their input traces, e.g., imprecise timestamps, traces with incomplete events or inconsistencies in event sources".
 Generic coverage: PARTIAL (RV theory has imprecise-trace and enforcement work in general). XR involvement: a monitor for properties spanning XR display state and ROS commands would face exactly these. XR-ess moderate. OVERLAP FLAG: must not be an eBPF monitor.

OP-10. Human excluded from resilience reasoning — Imrell et al. RobResilience 2026 (§4 threat model, §Future Work)
 Quote: "No human operator is involved."; future: "We inject attacks symbolically rather than as real ROS2 exploits, bypass the IDS entirely by setting κ = 0".
 Generic coverage: NO for human-as-mitigation/human-as-disruption in δ/γ/μ predicates. XR-ess moderate (operator via XR as recovery channel). Lower evidence of demand (scope choice, not stated as a gap).

Strongest non-excluded candidates (D): OP-4 (human-in-loop cause-effect freshness semantics), OP-5 (integrity of command-originating low-criticality HMI partitions), OP-2 (render-vs-ground-state consistency of the XR view), OP-6 (XR bridge as SROS2 seam). OP-1/OP-3/OP-8 carry high overlap risk with excluded directions.

Caveats: ACM-hosted papers (Deng CCS'22, Wang AsiaCCS'24, DDS Security+, RoboRebound) could not be read (403); evidence B/B-. SERA (IEEE) numbers are from a search snippet only. "Not found" statements reflect this search session, not exhaustive proof.

---

# Part 2 — XR security/privacy, XR teleoperation, MR-HRI, remote/multimodal teleop


Evidence levels: A = full paper body read; B = abstract/publisher metadata; C = README/docs; D = inference (labelled).
Note on method: WebFetch summaries of PDFs were found to hallucinate at least once (Cheng et al. USENIX'23 summary invented attack names/numbers); for PDFs, text was extracted with pdftotext and quotes taken from the raw text. Items marked A were read from raw text or arxiv HTML.

---
## Category 1 — XR security & privacy SoKs, perceptual manipulation, AR output security

### 1.1 Teymourian et al., "SoK: Come Together – Unifying Security, Information Theory, and Cognition for a Mixed Reality Deception Attack Ontology & Analysis Framework"
- Year/Venue: arXiv 2502.09763, Feb 2025 (SoK).
- Problem: no theoretical framework to describe/analyse MR deception attacks on cognition.
- Threat model: adversary degrades/denies/corrupts/subverts the MR information channel (Borden–Kopp).
- System model: generic MR headset + user; no robot.
- Method: SLR (80 articles), ontology, Shannon-model, decision-making model -> Deception Analysis Framework (DAF).
- Evaluation: theoretical; maps 31 attacks from literature.
- Assumptions: Borden–Kopp / Shannon models fit MR.
- Author-stated limitation (Sec. 9): "It is theoretical in nature and would benefit from further empirical validation."
- Future work: "Controlled experiments involving MR deception attacks are essential for refining the framework".
- Follow-up: used as questionnaire (DAF) in Wang et al. 2026 (1.3).
- Generic solution? n/a (taxonomy). XR essential: yes. Robot essential: no — robots/CPS not mentioned.
- Remaining gap: no ontology category for *deception arising from a benign-but-stale/incorrect rendering of a remote physical agent* (D).
- Evidence: A (arxiv HTML).

### 1.2 Cheng, Tian, Kohno, Roesner, "Exploring User Reactions and Mental Models Towards Perceptual Manipulation Attacks in Mixed Reality"
- Year/Venue: USENIX Security 2023.
- Problem: how users react to PMA (visual, auditory, situational-awareness manipulation).
- Threat model: malicious/buggy MR content shown to user.
- System model: HoloLens-style MR headset, lab tasks (reaction-time, sustained attention, SA scenario); no robot.
- Method: in-person deception study, 21 participants.
- Evaluation: PMA degraded main-task performance; secondary effects (users slower/more cautious later); users rationalised attacks as glitches.
- Author-stated limitation (Sec. 3.6): "we do not aim to make causal or generalizable claims."
- Discussion/future (Sec. 7.2): proposes "Contextual focus mode", "Escape to reality" (all MR outputs "verifiably disabled"), human-centred defenses; "we expect that the impacts in more critical applications and/or with more finely-tuned attacks may be substantially worse."
- Follow-up: many (Wang 2026, Teymourian 2025, Xiu/Gorlatova VIM work).
- Generic solution? "escape to reality" is a kill switch; does not apply when the XR view *is* the only view of a remote robot (teleop has no "reality" to escape to) (D).
- XR essential: yes. Robot essential: no.
- Key observation for our gap: users attribute anomalies to glitches -> in teleop a stale/incorrect twin would likely also be rationalised (D).
- Evidence: A (pdftotext of USENIX PDF).

### 1.3 Wang, Yao, Xiu, Yi, Gorlatova, Li, "Is It Real? Exploiting Virtual-Physical Discrimination Vulnerability in Mixed Reality"
- Year/Venue: arXiv 2606.17783, June 2026.
- Problem: users cannot distinguish virtual from physical objects; exploitable object-level deception.
- Threat model: compromised MR task-assistance app with legitimate permissions; reads world-sensing data, writes arbitrary content (geometry/texture/occlusion).
- System model: Apple Vision Pro, visionOS 26, ARKit/RealityKit.
- Method: expert workshops (12) -> 4-subtype taxonomy (Endogenous Injection, Type-Deceptive Overlay, Attribute-Deceptive Overlay, Exogenous Injection); 26-participant within-subjects study.
- Evaluation: e.g., Phantom Obstacle: 23/26 deviated from path; Disguised Ad: 26/26 grasped virtual clones.
- Assumptions: rendering fidelity high enough to confuse.
- Author-stated limitation (Sec. 6.3): "We focused exclusively on visual confusion, though MR systems increasingly support spatial audio and haptic feedback"; "we did not implement a full exploit chain".
- Future work (Sec. 6.3): "interact with AI-agent-mediated MR workflows where users delegate verification to AI assistants".
- Proposed defenses (Sec. 6.2): provenance enforcement at object layer, per-object write permissions, reality-verification mode, OS-mediated gating of consequential actions, "asynchronous content auditing comparing rendered vs. physical content".
- Generic solution? provenance/permissions (Arya/Erebus-style) cover *malicious app* case; "rendered vs physical auditing" is proposed, not built.
- XR essential: yes. Robot essential: no (no robots).
- Remaining gap: rendered-vs-physical auditing when the "physical" is a remote robot observed only through sensors (D).
- Evidence: A (arxiv HTML).

### 1.4 Xiu & Gorlatova, "Demonstrating Visual Information Manipulation Attacks in Augmented Reality: A Hands-On Miniature City-Based Setup"
- Year/Venue: MobiHoc 2025 demo (Oct 2025), arXiv 2509.02933.
- Problem/threat: VIM attacks alter real-world cues (text labels, road signs, virtual obstacles).
- System: Meta Quest 3, ArUco, miniature city with a remote-controlled car driven by the user.
- Evaluation: pilot, 3 users; 2 failed to notice manipulated building text.
- Future work: "conduct a user study to quantitatively assess how VIM attacks influence user decision-making".
- Related: "Detecting Visual Information Manipulation Attacks in AR: A Multimodal Semantic Reasoning Approach" (arXiv 2507.20356) — detection via VLM reasoning (B, from search listing only).
- Robot essential: partially — the RC car is a teleoperated vehicle proxy but no ROS/robot state. XR essential: yes.
- Remaining gap: attacks/errors on the *robot-state overlay* itself are not addressed (D).
- Evidence: A (arxiv HTML, short demo paper).

### 1.5 Lebeck, Ruth, Kohno, Roesner, "Securing Augmented Reality Output" (Arya)
- Year/Venue: IEEE S&P 2017 (foundational, pre-2024).
- Problem: untrusted AR apps can obscure/distract/overlay real-world objects.
- Threat model: "Arya is trusted, but the AR applications running on Arya are untrusted."
- System model: AR OS with recognizers + output policy module; simulated AR (HoloLens/car windshield).
- Method: condition/mechanism output policies (e.g., don't occlude pedestrians), composable.
- Evaluation: prototype performance.
- Author-stated limitation (Sec. Discussion): "Input noise may confound output policy management (e.g., if a recognizer fails to detect a person)"; composable design "excludes some policy mechanisms, particularly those that move AR objects".
- Future work: noisy input/confidence, constraint-solving policies, non-visual output.
- Follow-up: Erebus (USENIX Sec 2023, access control), Ruth et al. multi-user AR; no 2024-26 direct output-policy follow-up found in search.
- Generic solution relevance to our gap: Arya polices *where/whether* app content is drawn relative to *locally sensed* real objects. It does NOT check whether an overlay's *semantic content* (e.g., a rendered robot pose, predicted trajectory) is correct/fresh relative to a *remote* robot's true state; the robot visualisation app is itself the trusted source (D).
- XR essential: yes. Robot essential: no.
- Evidence: A (pdftotext of author PDF).

### 1.6 Yang et al., "Inception Attacks: Immersive Hijacking in Virtual Reality Systems"
- Year/Venue: arXiv 2403.05721 (2024).
- Threat: malicious VR app traps the user in a fake replica of the system interface; "interaction attacks" alter what users see from others.
- Evaluation: IRB user studies of effectiveness/stealth; proposes multifaceted defense pipeline.
- Robot: none. Relevance: a teleop client could similarly be spoofed, but that is a generic app-integrity/UI-spoof problem (D).
- Evidence: B (arxiv abstract).

### Category 1 take-aways (D)
- All XR-security work treats the *malicious app / adversarial content* case; the platform's legitimate content is assumed correct.
- None of the SoKs mentions robots or teleoperation; the "real world" is always co-located with the user.
- Defences proposed (provenance, output policies, reality-verification, escape-to-reality) assume the user can compare with local physical reality. In remote teleop the XR scene is the operator's *only* access to reality — escape-to-reality does not exist.

### 1.7 Kundu et al., "Securing Virtual Reality Experiences: Unveiling and Tackling Cybersickness Attacks with Explainable AI" (arXiv 2503.13419, 2025)
- Adversarial examples against DL cybersickness detectors (Simulation 2021 / Gameplay datasets). Per Sabouri 2026 survey: "degrade LSTM-based detection accuracy by 4.65x and Transformer-based detection by 5.94x".
- Robot: none. Evidence: B (search abstract + secondary citation in 2.1).

---
## Category 2 — XR teleoperation of robots (incl. teleop security surveys)

### 2.1 Sabouri, "Cybersecurity of Teleoperated Quadruped Robots: A Systematic Survey of Vulnerabilities, Threats, and Open Defense Gaps"
- Year/Venue: arXiv 2602.23404, Feb 2026 (survey).
- Problem: security of VR-teleoperated legged robots across 6 layers (perception; VR/AR-specific; comms; control; localisation; network/ROS 2).
- Threat model: external attacker at any layer; Layer 2 = cybersickness induction, HMD side-channel, display content injection.
- System model: operator HMD <-> radio (WiFi/5G/sat) <-> ROS2/DDS <-> locomotion controller.
- Method: systematic survey + TRL-tiered defense review + consequence-severity table.
- Key text (III-C 3): display content injection "introducing overlays that mimic authentic telemet[ry]"; "altered pose/velocity readings can skew operator control towards destabilizing directives."
- Key observation (Sec. V): attacks on the operator "entail significant human and mission repercussions while inflicting minimal direct harm to the robot".
- Author-stated open problem (VI-E, Gap 5 "Operator Degradation Detection and Adaptive Autonomy Transfer"): cybersickness F1 results "obtained in seated VR experiments, not during active teleoperation"; transfer must be "attack-resistant (an adversary should not be able to trigger autonomy transfer as a means of removing the human from the loop...)".
- Digital twin anomaly detection listed only as TRL 1–3; table notes "No legged robot implementation" and "Real-time sync latency, physics model fidelity" as open issues.
- Generic solution? Display-injection defence reduces to channel integrity (SROS2/DDS Security, TLS) for the *external attacker* case. It does not cover benign divergence (stale/latency, model error) between the displayed state and true/future robot state (D).
- XR essential: yes (Layer 2). ROS essential: yes (ROS2/DDS layer).
- Remaining gap: no work verifies that what the HMD *renders* equals what ROS believes / what the controller will do (D).
- Evidence: A (arxiv HTML text extracted; quotes grep-verified).

### 2.2 Cheng, Ji, et al., "Open-TeleVision: Teleoperation with Immersive Active Visual Feedback"
- Year/Venue: CoRL 2024, arXiv 2407.01512.
- Problem: immersive stereo, active-neck teleop of humanoids for imitation-learning data.
- System model: Vision Pro -> Vuer web server -> Unitree H1 / Fourier GR-1; 60 Hz loop; ZED Mini on actuated neck; also coast-to-coast demo.
- Evaluation: task success (e.g., can sorting 92% pick); stereo reduced completion time ~27% in user study.
- Author-stated limitation (Sec. 5): "there is still a lack of other forms of feedback, such as haptic feedback".
- Future work: "extended to mobile version which utilizes all the DoFs of the robot".
- Security/safety: none discussed.
- Follow-up: many (e.g., "Learning to Look Around" arXiv 2411.00704; TelePreview 2412.13548; Sabouri survey cites it).
- XR essential: yes. Robot essential: yes. ROS: not used (custom web stack) (C/D).
- Gap: no treatment of head-motion vs camera-neck lag, i.e., view shown for a camera pose the robot has not yet reached (D).
- Evidence: A (arxiv HTML via summary; quotes from summary—moderate confidence).

### 2.3 Guo et al., "TelePreview: A User-Friendly Teleoperation System with Virtual Arm Assistance for Enhanced Effectiveness"
- Year/Venue: arXiv 2412.13548v3, Jan 2025.
- Problem: novice teleop errors; show "a virtual robot that represents the outcome of the user's next movement" before execution.
- System model: hand tracking -> IK -> AR-rendered virtual arm aligned via AprilTag + hand-eye calibration.
- Divergence handling: when pedal activates preview, "the physical robot stops while the preview appears" — i.e., preview and execution are temporally separated.
- Evaluation: new-user success e.g. cup stacking 0.5->1.0.
- Author-stated limitation: "a key limitation is the visual ambiguity caused by occlusions between the preview robot and scene objects".
- Future work: depth from RGB-D.
- Gap (D): the preview is the IK *target*; the executed trajectory (controller, planner, joint limits, collisions, dynamics) after commit is not checked to equal what was previewed. "Preview == what robot will do" is assumed, not verified.
- XR essential: yes. Robot essential: yes. Evidence: A (arxiv HTML via summary; quotes from summary).

### 2.4 van Haastregt, Welle, Zhang, Kragic, "Puppeteer Your Robot: Augmented Reality Leader-Follower Teleoperation"
- Year/Venue: IEEE-RAS Humanoids 2024, arXiv 2407.11741.
- Problem: leader-follower teleop without a physical leader arm.
- System model: AR headset virtual leader robot -> IK -> real follower; follower joint positions "relayed back to the AR device" as a transparent ghost.
- Method (existing solution to command-vs-actual divergence): ghost green under threshold; "If the follower diverges too far, if too high joint velocities on the virtual robot are detected, or a communication interruption is noted, the streaming is stopped for safety reasons and the transparent robot turns red"; user realigns with "X".
- Evaluation: pilot n=10, UX questionnaire (perceived safety lowest, mildly).
- Author-stated limitation (Conclusion): "the virtual robot does not display the same amount of inertia as a real physical robot does".
- Future work: bimanual, arbitrary robot models.
- Generic-solution status: covers *command vs reported state* divergence with a threshold + stop. Does NOT cover: (a) the reported state itself being stale/wrong (ghost is only as fresh/true as the joint-state stream); (b) divergence of the *environment* model; (c) future/planned motion. (D)
- XR essential: yes. Robot essential: yes. Evidence: A (pdftotext; quotes verified).

### 2.5 Liu, Yu, Zhao, Ding, Wei, Munawar, Unberath, Kazanzides, "Digital Twin-Driven VR Teleoperation with Multi-View Spatial Perception for Surgical Robots"
- Year/Venue: arXiv 2609.25527, Sept 2026 (JHU, dVRK).
- Problem: replace video with a DT scene in a Quest 3S for surgical teleop.
- System model: three async streams: robot joint state via UDP (~90 Hz) -> Unity; object state via SAM2/3 + FoundationPose (SAM2 ~157 ms/frame) as JSON packets; commands from controllers. Rendering from state packets asynchronously at headset rate.
- Divergence handling (Sec. system): "The system holds the last valid pose during temporary tracking dropouts and alerts the operator via the GUI ... if manual re-initialization is needed."
- Evaluation: 15 participants; VR vs MR baseline path length -86%, jerk -95%; end-to-end teleop loop ~59.7 ms.
- Author-stated limitation (Sec. VI): "the scene-twin update rate currently lags behind the 90 Hz robot-twin rate"; FoundationPose "assumes rigid body geometry".
- Safety/security: none.
- Gap (D, strong): the rendered scene is a *composite of differently-aged state* (robot ~90 Hz, objects at perception rate, dropped objects frozen at last valid pose) presented as one coherent 3D world; there is no per-element freshness/confidence semantics, no check that the composite is physically consistent (e.g., instrument drawn not touching tissue that has actually moved). An attacker (or fault) that freezes/delays only the object stream produces a plausible but false scene.
- XR essential: yes. Robot essential: yes (ROS not stated; UDP/Unity). Evidence: A (arxiv HTML; quotes grep-verified).

### 2.6 Wang, Shen, Lee, "Towards Massive Interaction with Generalist Robotics: A Systematic Review of XR-enabled Remote Human-Robot Interaction Systems"
- Year/Venue: arXiv 2403.11384, 2024 (100 papers, 2013–2023).
- Findings: digital-twin interfaces most common; "system latency effects are not considered in nearly half of the studies (49%)"; "addressing latency is especially important for systems that require the participation of multiple users and robots".
- Security: essentially none discussed (only incidental word use).
- Evidence: A (arxiv HTML; quotes grep-verified).

### 2.7 Kim, Lee, Spinola, Kwon, Moghaddam, "AHEAD: Anticipatory Hand-Driven Teleoperation via Human Intent Prediction"
- Year/Venue: arXiv 2607.15172, July 2026.
- Method: VR digital twin; classifier predicts intended grasp object/slot (76% top-1); robot starts proactively; 0.6 s / 1.4 s lower reaction latency.
- Relevance (D): robot acts on *predicted* intent — so the robot can be doing something the operator has not yet committed to; the XR view must convey which goal the robot has adopted. Mis-prediction visibility not studied in abstract.
- Evidence: B (arxiv abstract).

### 2.8 Richter, Zhang, Zhi, Orosco, Yip, "Augmented Reality Predictive Displays to Help Mitigate the Effects of Delayed Telesurgery"
- Year/Venue: ICRA 2019 (foundational). da Vinci; AR predicted tool motion overlaid on delayed video; 10 participants; "decreased time to complete task while having no effect on error rates when operating under delay".
- Existing-solution role: predictive displays address *latency* (showing where the tool will be under the commanded input, assuming a known kinematic model). They do not address the prediction being wrong because the robot will not follow the command (safety controller override, planner rejection, fault, compromise) (D).
- Evidence: B (arxiv abstract).

### Category 2 take-aways (D)
- XR teleop systems (Open-TeleVision, TelePreview, surgical DT, AHEAD) present three kinds of robot-state visuals: (i) reported current state (ghost), (ii) commanded/previewed target, (iii) predicted/anticipated goal. Existing mechanisms: threshold-stop on (i)-vs-command (Puppeteer), temporal separation (TelePreview), predictive kinematics (Richter). None verifies (ii)/(iii) against what the robot's *downstream* stack (planner, safety controller, ROS 2 controllers) will actually execute, and none gives per-element freshness in composite DT scenes.
- No XR-teleop system paper found (2024–26) with a security threat model; the only security treatment is the 2026 quadruped survey (2.1), which lists display injection and DT anomaly detection as low-TRL.

---
## Category 3 — Mixed-reality HRI (intent visualisation, AR robot programming, XR-DT)

### 3.1 Suzuki, Karim, Xia, Hedayati, Marquardt, "Augmented Reality and Robotics: A Survey and Taxonomy for AR-enhanced Human-Robot Interaction and Robotic Interfaces"
- Year/Venue: CHI 2022 (SoK-style survey, 460 papers).
- Author-stated open problem (Sec. Future Opportunities, "Making AR-HRI Practical and Ubiquitous"): "if the AR system fails in such a safety-critical situation, users might be at risk (e.g., device malfunctions, content misalignment, obscured critical objects with inappropriate content overlap, etc)"; open question "What extent should users rely on AR systems in case the system fails?"
- Security: no adversarial treatment (search of text: only venue names contain "Security").
- Generic solution? Arya-like output policies cover "obscured critical objects"; nothing covers "content misalignment" with the robot's true/future state (D).
- XR essential: yes; robot essential: yes. Evidence: A (pdftotext; quotes verified).

### 3.2 Grubert, Dudley, Ofek, Kristensson, "Extended Reality as a Mediation Layer for Situated Human Control in Human-Robot Teaming"
- Year/Venue: arXiv 2607.25047, July 2026 (position/research-agenda paper).
- Problem: XR interfaces display intent but do not support situated *control*; "robot plans are often technically feasible while remaining questionable in context".
- System model: conceptual; scenarios: bedside nursing, multi-arm supervisory teleop, collaborative assembly.
- Method: four mediation functions, six design dimensions; proposed scenario-based evaluations.
- Author-stated open problem (Sec. 3.3 "Uncertainty, Plan Validity, and Situational Awareness"): "Situated human control depends on the user's ability to understand whether a robot plan remains valid. Plans can become outdated when people move, objects are occluded, sensor readings conflict, the task goal changes..." ; "XR interfaces should therefore communicate both planned action and the reliability of the assumptions behind it"; e.g., "indicate that a planned motion requires renewed approval after the environment changes."
- Future work: studies introducing "stale plans, or hidden uncertainty"; "users may initially attend to uncertainty and authority cues but later ignore them or over-trust the system."
- Security: none (no adversary).
- Generic solution? Uncertainty visualisation literature (cited) covers *display* of confidence; the *mechanism* for detecting that a displayed/approved plan is no longer the one that will execute (plan-approval binding) is not given (D). Note: "authority/handover" facet overlaps EXCLUDED lease/authority direction — avoid.
- XR essential: yes. Robot essential: yes. Evidence: A (arxiv HTML; quotes grep-verified).

### 3.3 Wang, Byeon, Yehia, et al., "XR-DT: Extended Reality-Enhanced Digital Twin for Safe Motion Planning via Human-Aware MPPI"
- Year/Venue: arXiv 2512.05270v2, Mar 2026.
- System model: Quest Pro (pose, gaze, egocentric video) + Clearpath Husky; Unity + ROS; TCP/IP; 10 Hz timestamp-aligned data.
- Method: ATLAS transformer predicts human trajectory from headset signals; chance-constrained HA-MPPI; XR-DT visualises robot inference.
- Evaluation: ADE 0.44 m; "no collisions" in 30 trials/condition; user-rated trust 4.75/5 vs safety 3.54/5.
- Assumption: VR-DT "continuously updated using the robot's LiDAR-derived 3D spatial information, ensuring that virtual representations remain synchronized" — synchronisation assumed, not measured.
- Future work: multi-human/multi-robot, open environments.
- Note (D): here the headset is also a *sensor* feeding the robot planner — the XR view and the planner's human model can diverge in both directions.
- Evidence: A (arxiv HTML via summary; quotes from summary).

### 3.4 Wozniak et al., "Happily Error After: ... Correcting Robot Perception Errors in Virtual Reality" (RO-MAN 2023)
- VR lets users correct Franka perception errors; 56 participants; VR faster learning than screen.
- Relevance: VR as channel to *repair* the robot's world model — implies XR view and robot world model are expected to differ and must be reconciled (D).
- Evidence: B (abstract).

### 3.5 ROS 2 <-> AR headset infrastructure (Magic Leap 2 ROS 2 sensor streaming, Univ. Padua thesis, arXiv-hosted 2609.31396, Sept 2026) — C/B-level; no security, no latency quantification per summary. Low weight.

### Category 3 take-aways (D)
- MR-HRI literature explicitly names "content misalignment" (Suzuki 2022) and "plan validity"/"stale plans" (Grubert 2026) as open, but treats them as HCI visualisation problems with no adversary, no formal consistency check between rendered intent and the executing ROS stack.
- Intent visualisations are rendered from planner output (e.g., MoveIt display trajectory); nothing binds the *visualised* plan to the *executed* plan (e.g., re-plans, controller preemption, safety-rated speed-and-separation override).

---
## Category 4 — HRI / teleop security (deceiving operators, physical–digital mismatch)

### 4.1 Shen, Geng, Zheng, Lu, "Seeing is Not Believing: Breaking the Physical-to-Digital Trust Boundary in Robotics"  ** closest prior work **
- Year/Venue: arXiv 2609.08280, 8 Sept 2026 (UCL/PolyU).
- Problem: attacker decouples robot physical behaviour from telemetry seen by verifiers (humans in RViz, monitors, peers).
- Threat model: user-space code execution via compromised third-party artifact (e.g., Docker image); LD_PRELOAD hook on `rcl_publish()` before SROS 2 protection; no root, no SROS2 key compromise; verifier uncompromised and relies only on telemetry.
- System model: ROS 2 + Franka arm + RViz monitor; attacker runs Isaac Sim as a digital twin to synthesise physically consistent telemetry.
- Method: intercept/modify commands; synthesise joint states with micro-motion, inter-joint coupling, cross-channel consistency; VLM-generated final-state images.
- Evaluation: "the attack achieves a 100% success rate" with and without SROS 2 (success = hijacked robot "while the victim's RViz visualizer continues to display normal task execution"); ~3 ms delay; bypass 87–100% of four detectors (per summary).
- Author-stated limitation (Discussions): live multi-view video spoofing "prohibitively expensive at scale"; model only "forging only the final-state image".
- Key statement: "securing telemetry in transit does not guarantee it reflects physical reality."
- Proposed defense: "a trusted sensing element (e.g., a secure microcontroller or TEE) signs each payload with a monotonic counter at acquisition time".
- Generic solution? Source-signed sensing (attested sensors) addresses the *forgery* case. It does not address divergence introduced *after* authentic measurements (fusion, twin reconstruction, prediction, rendering, reprojection in an XR client) nor benign staleness (D).
- XR essential: NO (RViz monitor, not XR). ROS essential: YES.
- Remaining gap (D): the XR rendering pipeline is a *further* transformation stage (twin, predicted poses, reprojection/ATW, overlays) not covered by sensor signing. Also: live multi-view XR (stereo + twin) is exactly the "multiple viewpoints" case the authors argue is hard to forge — possible cross-view consistency defence idea.
- Evidence: A (arxiv HTML; quotes grep-verified).

### 4.2 Pu, He, Cheng, Chen, Sun, "CORMAND2: A Deception Attack Against Industrial Robots"
- Year/Venue: Engineering 32 (2024).
- Threat: network adversary (ARP spoofing) injects malicious robot code, replays recorded normal movement data to SCADA.
- Evaluation: 7 robots / 6 OEMs; SVM detector detection 2.4% vs FA 2.7%; +1.7 ms.
- Limitation (per summary): requires ≥3 cycles; assumes no sub-cycles.
- XR: no. Robot: yes (non-ROS industrial). Evidence: B (publisher page summary).

### 4.3 Sabouri 2026 quadruped survey (see 2.1) — "Display Content Injection" layer; "altered pose/velocity readings can skew operator control". Evidence: A.

### 4.4 LLM-robot trust surveys (e.g., "Trust in LLM-controlled Robotics", arXiv 2601.02377) — over-trust / interface poisoning; mostly prompt-injection => EXCLUDED direction. Evidence: B (search snippet only). Not used.

### Category 4 take-aways (D)
- Physical–digital mismatch attacks on ROS 2 now exist (4.1) and on industrial SCADA (4.2), with the human viewer as the deceived verifier — but the viewer is RViz/SCADA, never an XR headset; and the proposed fix (sign at source) stops at the telemetry layer.
- No paper found that treats the *XR rendering/prediction layer itself* (twin reconstruction, predicted/preview poses, timewarp) as a place where the operator's belief diverges from robot truth, adversarially or benignly.

---
## Category 5 — SA failures, latency, predictive displays, runtime assurance in (XR) teleop

### 5.1 Zhang, Liu, Kim, "Understanding and Mitigating Network Latency Effect on Teleoperated-Robot with Extended Reality" (TeleXR)
- Year/Venue: arXiv 2506.01135v2, June 2025 (UC Riverside).
- Problem: motion-to-motion (M2M) latency in XR teleop; dependence on network for both control and feedback.
- System model: Northstar Next XR headset + Kinova Gen3; DDS XR->robot, UDP robot->XR point clouds; PCs or Jetson.
- Method: "dual-reconstruction": robot side reconstructs missing/delayed hand poses via online trajectory planning; XR side extrapolates robot end-effector pose with an EKF from local hand pose; contention-aware GPU scheduling; edge-preserving point-cloud scaling.
- Divergence handling (Sec. III): "When the prediction error becomes too large due to unforeseen external factors, the robot pose reconstruction pauses the next iteration to avoid abrupt visual changes."
- Evaluation: network delay dominant; GPU contention +45% render time on embedded; near-100% point-cloud drops under 4G LTE (per summary).
- Author-stated future: "a neural network prediction model ... could be used for highly randomized user motion".
- Safety/security: none.
- Gap (D, strong): BOTH ends synthesise state the other side never sent — the robot executes *reconstructed* commands the user did not issue, and the XR shows *extrapolated* robot poses the robot has not reached. The divergence handler is tuned for visual smoothness, i.e., it hides divergence exactly in the "unforeseen external factors" case (collision, e-stop, safety-controller override) where the operator most needs to see it.
- Generic solution? Puppeteer-style threshold/red ghost partially; none bounds or discloses extrapolation age/error to the operator. XR essential: yes. ROS/DDS essential: yes (DDS).
- Evidence: A (arxiv HTML; quotes grep-verified).

### 5.2 Zhang, Liu, Kim, "Toward a Predictive eXtended Reality Teleoperation System with Duo-Virtual Spaces"
- arXiv 2409.15464, Sept 2024, 3-page. User-side virtual space localises agent/objects locally, "calibrating with periodic ground-truth poses from the agent-side virtual space".
- Gap (D): between calibrations the operator sees a locally simulated robot; divergence bound not given in abstract.
- Evidence: B (abstract).

### 5.3 Khalil & Kwon, "Towards Generative Predictive Display for Vision-Based Teleoperation: A Zero-Shot Benchmark of Off-the-Shelf Video Models"
- Year/Venue: arXiv 2605.09670, May 2026.
- Method: 5 video models (LTX-Video 2B/13B, SVD 1.1, Wan VACE/I2V) predicting 8 future frames from 9 on CARLA driving data.
- Evaluation: no model achieved low error + stability + real-time at 15 FPS; "SVD predictions visibly drift away from the conditioning scene structure".
- Author-stated limitations: "zero-shot, off-the-shelf only"; no "closed-loop or human-in-the-loop study"; "pixel-level MAD is a coarse proxy for predictive utility".
- Future: "a closed-loop teleoperation study", task-aware metrics.
- Gap (D): generative predictive displays can *hallucinate plausible futures*; no check that predicted frames agree with robot's planned/controlled motion. Robot: vehicle in sim (no ROS); XR: no (2D).
- Evidence: A (arxiv HTML via summary; quotes from summary).

### 5.4 Richter et al. ICRA 2019 AR predictive display (see 2.8). Evidence: B.

### 5.5 Hazardous-environment teleoperation review (OAE, "Robotic teleoperation in hazardous environments: a review of feedback architectures, stability, and learning-based adaptation", Open Access, 4 Aug 2026)
- Scope: feedback architectures, stability under delay, learning-based adaptation.
- Author statements (verified in page text): "Predictive displays, digital-twin reconstruction, XR interfaces, and robot-side contact intelligence partially alleviate its limitations"; model-mediated teleop: "unmodelled friction can drive large normal estimation deviations, which would directly corrupt rendered constraint cues under realistic contact"; shared autonomy failure modes: "over-assistance, unexpected intervention, and mode confusion, where operators struggle to predict the system's current level of autonomy"; "miscalibrated confidence can prolong incorrect assistance when feedback is delayed".
- Cites intention-reflected XR predictive display (Zhu et al., ROBOMECH J. 2023) reducing errors in irreversible tasks ">50%".
- Security: no substantive cyber treatment found in grep.
- Evidence: A (full page text grep; authors not extracted).

### 5.6 Hejrati, Mustalahti, Mattila, "Robust Immersive Bilateral Teleoperation of Dissimilar Systems with Enhanced Transparency and Sense of Embodiment" (arXiv 2505.14486, 2025)
- VR headset + pan-tilt camera + 7-DoF haptic exoskeleton -> 6-DoF hydraulic manipulator; UDP, stable up to 150 ms delays; n=10, embodiment 76.4%.
- Multimodal (haptic+video) teleop; divergence between felt (haptic model) and seen (delayed video) not studied as a safety issue (D).
- Evidence: A- (arxiv HTML via summary).

### 5.7 Safety filters / runtime assurance (e.g., Hsu, Hu, Fisac, "The Safety Filter: A Unified View of Safety-Critical Control in Autonomous Systems", Annu. Rev. Control Robot. Auton. Syst. 2024)
- Safety filter = monitor + intervene: may override the candidate control input.
- Relevance (D): when a safety filter / ROS 2 safety controller overrides an operator command, the XR preview/predicted pose (TelePreview, TeleXR EKF, predictive display) shows the *unfiltered* intent — runtime assurance guarantees robot safety but creates a *belief divergence* for the operator (mode confusion per 5.5). Not addressed by RTA literature, which targets the plant, not the operator's display.
- Evidence: B (search snippet / abstract only).

### Category 5 take-aways (D)
- Latency compensation in XR teleop now routinely *synthesises* robot state (EKF extrapolation, local simulation, generative video, preview IK). Validity is judged by visual smoothness or task time, not by bounded disagreement with the robot's actual/executing state.
- Predictive displays assume the robot will do what was commanded; safety filters/controllers/planners that change the command are invisible to the predictor.

### 5.8 Other DT-teleop / DT-runtime-verification items (B-level, abstracts only)
- Betzer et al., "Digital Twin Enabled Runtime Verification for Autonomous Mobile Robots under Uncertainty" (DS-RT 2024, arXiv 2412.09913): cloud DT watchdog via MQTT overrides actuations; speed-mismatch reduced up to 41%. Monitors robot vs spec — not operator's view.
- Yelchuri et al., "RoboTwin" (arXiv 2506.01027, 2025): dual DTs for telesurgery; surgeon operates local twin; patient-side twin "provides a layer of safety for operator-related mishaps"; 25x lower bandwidth.
- Carr et al., "Attacking Digital Twins of Robotic Systems to Compromise Security and Safety" (arXiv 2211.09507, 2022, 4 pp.): ROS DT person-in-the-middle "could eventually lead to a collapse of the cyber-physical system".
- Not retrievable (403): ScienceDirect "A systematic review of XR-based robotic teleoperation" (2026, S266730532600089X); ACM 3694907.3765931 (AR interface overconfidence). Snippet-only, NOT used as evidence.

---
## Synthesis — the "rendered-belief divergence" question

Question: can the operator's XR view (rendered robot state, DT, overlays, preview/predicted poses) diverge from the robot's actual state or from what the robot will do, in a safety/security-relevant way, and does existing work solve it?

Divergence sources found in the literature (all evidence-backed):
1. Latency/extrapolation: XR shows EKF-extrapolated poses; robot executes reconstructed commands (TeleXR 5.1); local simulated agent between calibrations (5.2); generative video futures that drift (5.3).
2. Mixed-freshness composites: robot twin ~90 Hz, object twin at perception rate, dropped objects frozen at "last valid pose" (2.5).
3. Preview-vs-execution: preview is IK target; executed motion unchecked (2.3); predictive displays assume command is followed (2.8, 5.5).
4. Override/mode changes: safety filters / shared autonomy change the command ("unexpected intervention, and mode confusion", 5.5, 5.7).
5. Adversarial telemetry: forged physically-consistent joint states and final-state images fool RViz under SROS 2 (4.1); display content injection (2.1); SCADA replay (4.2).

What existing work covers:
- Command vs *reported* state divergence: threshold + stop + red ghost (Puppeteer 2.4). Covered for that pair.
- Forged telemetry: source-signed sensing (proposed, 4.1); channel integrity (SROS 2). Covered for in-transit forgery only; 4.1 shows SROS 2 insufficient.
- Malicious app overlays: Arya/Erebus/provenance (1.5, 1.3). Covered only for co-located "reality" and untrusted third-party apps.
- Plant safety: RTA/safety filters (5.7). Robot safe, operator belief not addressed.

NOT covered (candidate gap, D):
- An end-to-end guarantee that what the XR client *renders* (including synthesised/predicted/preview content) stays within a declared, operator-visible bound of (a) the robot's authenticated current state and (b) the command stream the ROS 2 stack will actually execute after planners/safety controllers; and a robot-side mechanism so that commands issued against a view that has since become invalid (divergence beyond bound, override active, frozen elements) are not executed as if the operator had seen the truth.
- Security twist: 4.1's attack forges telemetry upstream; the XR pipeline adds more synthesis stages (twin, EKF, reprojection) where an attacker/bug can hide divergence (TeleXR even suppresses "abrupt visual changes" by design). Multi-view XR (stereo camera + DT + point cloud) is exactly the multi-viewpoint consistency 4.1 says is costly to forge -> cross-representation consistency checking inside the XR render path is a plausible, unexplored defence.

Overlap risks with EXCLUDED list (flag for caller):
- "commands issued against an invalid view are rejected" can drift into XR input timestamp/validity checking (EXCLUDED) — must be framed as *output/render-side belief integrity*, bound to robot-side executed state, not as input freshness checks.
- Showing staleness badges alone = "simple safety warning UI" (EXCLUDED); the contribution must be the consistency mechanism/bound, not the badge.
- Sabouri Gap 5 autonomy transfer overlaps authority/lease handoff (EXCLUDED).

---
## Author-stated open problems (XR + robot/ROS) and generic-solution coverage

1. Suzuki et al. CHI 2022 (Future Opportunities): "if the AR system fails in such a safety-critical situation, users might be at risk (e.g., device malfunctions, content misalignment, obscured critical objects...)"; "What extent should users rely on AR systems in case the system fails?" — Coverage: occlusion part by Arya-style output policies; *content misalignment w.r.t. robot state* not covered.
2. Grubert et al. 2026 (Sec. 3.3): "Situated human control depends on the user's ability to understand whether a robot plan remains valid. Plans can become outdated when people move, objects are occluded, sensor readings conflict..."; calls for studies with "stale plans, or hidden uncertainty". — Coverage: uncertainty visualisation (display) only; no mechanism detecting that the shown/approved plan != executing plan. Partial.
3. Liu et al. 2026 surgical VR-DT (Sec. VI): "the scene-twin update rate currently lags behind the 90 Hz robot-twin rate"; design "holds the last valid pose during temporary tracking dropouts". — Coverage: none for composite-consistency; faster perception reduces but doesn't bound it.
4. Shen et al. 2026 (Abstract/Conclusion): "securing telemetry in transit does not guarantee it reflects physical reality"; live multi-view spoofing "prohibitively expensive at scale" (Discussions). — Coverage: source signing (proposed) for forgery; post-measurement XR synthesis stages uncovered.
5. Sabouri 2026 (Table, Tier-3 DT anomaly detection): open issues "Real-time sync latency, physics model fidelity"; "No legged robot implementation". — Coverage: DT anomaly detection exists for industrial CPS (Xu et al. 2021 cited) but not for operator-facing XR twins.
6. Sabouri 2026 (VI-E Gap 5): cybersickness detection results "obtained in seated VR experiments, not during active teleoperation"; autonomy transfer must be "attack-resistant". — Coverage: partial (existing detectors); transfer part overlaps EXCLUDED authority direction.
7. Hazardous-teleop review 2026: shared-autonomy failure modes "over-assistance, unexpected intervention, and mode confusion, where operators struggle to predict the system's current level of autonomy"; "unmodelled friction ... would directly corrupt rendered constraint cues". — Coverage: safety filters make the robot safe but do not reconcile operator's displayed expectation. Not covered.
8. Khalil & Kwon 2026: no "closed-loop or human-in-the-loop study"; "pixel-level MAD is a coarse proxy for predictive utility". — Coverage: none; no safety-aware metric for predictive displays.
9. Cheng et al. USENIX Sec 2023 (Sec. 7.2): impacts "in more critical applications and/or with more finely-tuned attacks may be substantially worse"; recommends "Escape to reality". — Coverage: escape-to-reality is inapplicable to remote teleop (the XR scene is the only reality view) (D).
10. Wang et al. 2026 (Sec. 6.2/6.3): proposes "asynchronous content auditing comparing rendered vs. physical content"; limitation "We focused exclusively on visual confusion". — Coverage: proposed only; not built; not for remote robots.
11. TelePreview 2025: "a key limitation is the visual ambiguity caused by occlusions between the preview robot and scene objects". — Coverage: depth-aware rendering (generic graphics) solves this; low novelty.

---

# Part 3 — Embodied AI / FM robots, runtime assurance, teleop security, shared autonomy, side channels

Cutoff 2026-09-30. Evidence: A=full body read (html), B=abstract/metadata, C=README/docs, D=inference (labelled).
Note: WebFetch returns model-summarised page content; "full body" (A) means the arxiv HTML full text was fetched and queried, quotes are as returned by that extraction.

## Cat 1: FM-powered robot security (jailbreaks, VLA attacks)

### 1.1 Robey et al., "Jailbreaking LLM-Controlled Robots" (RoboPAIR), arXiv 2410.13691 (2024; later ICRA 2025 per common knowledge - D)
- Problem: can LLM-planner robots be jailbroken into harmful physical actions.
- Threat model: white-box (Dolphins), gray-box (Jackal + GPT-4o planner), black-box (Unitree Go2 GPT-3.5, voice).
- System: LLM planner emitting robot API calls; no human approval in loop.
- Method: PAIR adapted with robot system prompt, in-context harmful actions, syntax checker.
- Eval: RoboPAIR 100% ASR on all three; template/in-context baselines 86-97%.
- Assumptions: attacker has prompt/API access; "physical actions execute without intermediate human approval".
- Limitation quote (Sec 6.4): "Filtering-based defenses...may be ineffective given the need to situate malicious prompts within the context of a robot's environment."
- Future work (6.4): need "physical safety filters, which (a) place hard physical constraints on robot actions and (b) take into consideration the robot's context and environment."
- Follow-ups: yes (RoboGuard 2503.07885, many VLA attack papers, survey 2601.02377).
- Generic solution? Partially: CBF/shielding for hard constraints; context-dependent harm is not generically solved.
- XR essential? No. ROS essential? No (Jackal is ROS-based, but not essential - D).
- Gap: human operator/teleop not considered at all ("Not mentioned").
- Evidence: A

### 1.2 Li et al., "Vision-Language-Action Safety: Threats, Challenges, Evaluations, and Mechanisms" (survey), arXiv 2604.23775v2 (Aug 2026)
- Taxonomy: attack timing x defense timing (training vs inference).
- Open problems (Sec 8): 8.1 "Certified robustness for embodied trajectories" / "physically realizable defenses"; 8.2 "Safety-aware training and unified runtime architectures"; 8.3 "Standardized evaluation and sim-to-real transfer"; 8.4 "Continuous learning and fleet-level deployment"; 8.5 regulatory/ethical.
- Human-in-loop items covered: APO (human interventions -> preference supervision), Hi-ORS (human-in-the-loop rejection sampling), SafeVLA online filtering, "Safe-Night VLA" CBF-QP runtime filter.
- XR/AR: none mentioned. Teleoperator-as-attack-surface: not identified in the extraction.
- Relevance: human intervention data used for policy improvement (APO, Hi-ORS) is an attack surface not analysed by the survey (D).
- Evidence: A (survey; extraction-level)

### 1.3 Zhang et al., "BadRobot: Jailbreaking Embodied LLM Agents in the Physical World", arXiv 2407.20242, ICLR 2025
- Problem: voice-interaction jailbreaks of embodied LLM agents (VoxPoser, Code-as-Policies, ProgPrompt).
- Threat: three risk surfaces: (1) cascading LLM jailbreak, (2) "safety misalignment" between linguistic and action outputs (model says "Sorry, I cannot..." in response field while function field encodes harmful motion), (3) conceptual deception (world-model gaps).
- Eval: MSR metric; +215.9% / +193.8% / +213.7% MSR vs vanilla (GPT-4-turbo); real arm 68.57% vs 22.85%.
- Defenses tried: multimodal consistency validation (-22.27% MSR, insufficient); world-model fine-tuning mixed.
- Limitation quote (discussion): "Fine-tuning reliable world models is computationally and data-intensive."; mitigation is a "cat-and-mouse arms race".
- KEY for XR/teleop: Risk 2 is a *stated-vs-executed divergence*: a human supervising via the language/UI channel sees a refusal while the robot executes. BadRobot does not study the human supervisor's perception of this divergence (D).
- Generic solution? Action-level shield/CBF catches physical harm irrespective of text; does not address supervisor deception.
- XR essential? No. ROS essential? No.
- Evidence: A

### 1.4 Ravichandran et al., "Safety Guardrails for LLM-Enabled Robots" (RoboGuard), arXiv 2503.07885 (RA-L accepted)
- Problem: guardrail against jailbroken LLM planners.
- Threat: jailbreaks (non-adaptive and adaptive; white/gray/black box).
- System: Clearpath Jackal, GPT-4o SPINE planner, semantic-graph world model (JSON).
- Method: root-of-trust LLM contextualises rules into LTL; "minimal-violation control synthesis, which maximally follows user preferences while ensuring that the safety specifications are satisfied."
- Eval: unsafe plan execution 92% -> <2.5%.
- Assumptions: root-of-trust LLM "shielded from malicious user input"; accurate world model.
- Limitation quotes (Sec V): "RoboGuard requires an accurate world model. A severely compromised world model would induce safety failures"; "LTL may not be appropriate for some scenarios, such as when system dynamics are critical to safety".
- User notification of plan modification: none mentioned (extraction). No human operator, no teleop.
- Gap (D): guardrail silently rewrites plan -> user intent vs executed plan divergence is unexplained to the human; world model (also what an operator would see in XR) is an attack point.
- XR essential? No. ROS essential? No (likely ROS-based platform, D).
- Evidence: A

### 1.5 Huang et al., "Trust in LLM-controlled Robotics: a Survey of Security Threats, Defenses and Challenges", arXiv 2601.02377 (Dec 2025)
- Open challenges (Sec VIII): A "Environment Context is Critical"; B "preventing 'harmful text' is not sufficient", defenses "siloed across layers"; C "multimodal LLMs expand the overall attack surface"; D "a unified 'one-size-fits-all' defense is infeasible".
- Human-in-loop: only as "escalating to humans" in recovery (Sec V-A). Teleop/shared control: not mentioned. XR: not mentioned. ROS: supply-chain mention only.
- Evidence: A (survey)

### 1.6 Jones et al., "Adversarial Attacks on Robotic Vision Language Action Models", arXiv 2506.03350 (Jun 2025)
- Threat: textual GCG on VLA (OpenVLA) to obtain "control authority"; persistence attacks across rollout steps.
- Eval: LIBERO overall success 77.3-97.5%; persistence up to "28x" steps; real-world 61.2%.
- Limitation quote (Limitations): "our attack may be difficult to employ in practice, due to the white-box nature and relative cost of the GCG algorithm... Extending attack frameworks to black-box scenarios and diffusion-based models will be a critical step".
- Human operator/monitoring: none.
- Relevance (D): "control authority" framing directly competes with a human operator's authority, but paper has no human.
- Evidence: A

### 1.7 Huang et al., "Propagating Unsafe Actions in LLM Controlled Multi-Robot Collaboration via Single Robot Compromise", arXiv 2605.15641 (May 2026)
- Threat: one compromised robot spreads harmful instructions via peer channels; obedience 1.00, infectiousness 0.90, ~3.0 rounds to full compromise, stealthiness 0.81.
- Human: none. Evidence: B

### 1.8 Zhang et al., "Backdoors in Learning-Based Industrial Robotic Arm Manipulation: An Empirical Security Study", arXiv 2609.26868 (Sep 2026)
- Threat: poisoned teleoperated demonstrations (ratio 0.1) with physical triggers; FANUC LR Mate 200iD, xArm 6.
- Defense: online observation sanitization (attack executions 1/5) vs fine-tuning (3-4/5).
- Limitation quote (Sec V): "An adaptive adversary could instead place triggers on task-relevant objects or manipulator links, bypassing static task-mask filtering."; "Foundation VLA models such as pi0 introduce additional trigger channels...".
- Teleop interface: collection method only, no operator/VR analysis.
- NOTE: falls under EXCLUDED "generic training-data integrity"; recorded for completeness only.
- Evidence: A

### 1.9 Banik & Hovakimyan, "Principled Authority Switching for Shared Autonomy in Human-Robot Teams", arXiv 2608.16293 (Aug 2026)
- Problem: control switching in shared autonomy as identical-interest dynamic game, LQ closed form, "stochastic human override", humans retain override.
- Security: none (cooperative/identical interest assumption - an adversarial human or adversarial autonomy is out of scope, D).
- Relevance: arbitration theory assumes benign cooperative players -> open: adversarially robust arbitration. (Borderline with excluded authority handoff; this is arbitration of control, not lease.)
- Evidence: B

## Cat 2: Runtime assurance for learning-enabled robots (Simplex, CBF safety filters, shielding, SafeVLA) and its interaction with human operators

### 2.1 Zhang et al., "SafeVLA: Towards Safety Alignment of VLA via Constrained Learning", arXiv 2503.03480, NeurIPS 2025 Spotlight
- Method: Integrated Safety Approach, CMDP min-max safe RL; Safety-CHORES benchmark (AI2THOR). -83.58% cumulative safety cost, +3.85% success.
- Assumptions: safety as compositional predicates; cost threshold "empirically set to 20% of the converged cost from the FLaRe baseline".
- Limitation quote: "The credit assignment for psi_j remains an area for exploration in future work"; mostly simulation, limited sim-to-real (Sec 5.3).
- No runtime filter, no human operator.
- Generic solution? Training-time only; complementary runtime shield needed.
- Evidence: A

### 2.2 Tayal & Nambi, "ShieldVLA: Feasibility-Aware Safety Alignment for VLA Models", arXiv 2609.13231 (Sep 2026)
- Method: HJ-reachability critic + feasibility-gated policy optimisation + rubric-based VLM cost supervision. -57% cumulative cost vs SafeVLA, +0.13 success.
- Limitation quotes (Sec 6 / App B): claims "empirical rather than formal"; "Sub-8B VLM scorers exhibit mode collapse on tail frames"; "real-robot validation will require re-calibrating the VLM rubric on domain-shifted observations."
- Human/teleop: none. Evidence: A

### 2.3 Nesti et al., "The Use of the Simplex Architecture to Enhance Safety in Deep-Learning-Powered Autonomous Systems", arXiv 2509.21014 (Sep 2025)
- System: Furuta pendulum; AgileX Scout Mini rover (ROS 2); Zynq UltraScale+ with CLARE type-1 hypervisor (Linux rich domain, RTOS safe domain); Simplex switch to backup controller.
- Human: after safety stop the "human operator must acknowledge it before re-enabling" the HP controller (Sec 5.3). No switching-transparency mechanism.
- Limitation quote (Sec 6): "introduction of hypervisor technology requires specific know-how and dedicated configuration tools"; inter-domain latency.
- Gap (D): operator acknowledgement is a trust decision made without evidence of why the switch happened; a remote (XR) operator re-enabling a compromised HP controller is unstudied.
- ROS essential? ROS 2 used, not essential. XR? No. Evidence: A

### 2.4 Oh et al., "Safety with Agency: Human-Centered Safety Filter with Application to AI-Assisted Motorsports", arXiv 2504.11717v3 (2025)
- Method: HCSF with state-action CBF (Q-CBF), smooth minimal intervention on human inputs; learned neural safety value.
- Eval: Assetto Corsa with real wheel/pedals, N=83; HCSF improved safety & satisfaction vs none; beats last-resort filter on agency/comfort.
- Transparency: arrows showing steering/throttle modification (Fig 4), drivers "immediately recognize when and how the system intervenes".
- Assumption: benign human; "no explicit discussion of adversarial or malicious human inputs"; opponents not adversarial.
- Future work quote (Sec VII): "Future work could explore transferring the learned safety filter to real-world racing environments".
- Gap (D): the transparency cue itself is an unauthenticated display of filter behaviour -> if filter or display compromised, operator believes a correction story that differs from execution. Not studied.
- XR? No (monitor sim). ROS? No. Evidence: A

### 2.5 Guler et al., "A Safety-Aware Shared Autonomy Framework with BarrierIK Using CBFs", arXiv 2603.01705, ICRA 2026
- System: 7-DOF arm, HTC Vive controllers, Unity3D VR teleop, 90 Hz; blend operator + autonomy (LERP/SLERP), then CBF-constrained IK post-blend.
- Eval: N=10; ~80% success; reduced violation time; users report "higher perceived safety and trust, lower interference".
- Operator visibility: no explicit visualisation of when/how CBF modifies the blended command (operator sees executed motion only).
- Limitation quotes: "Treating safety as a hard constraint can induce detours..."; "Design choices for the barrier (e.g., class-K functions and shaping) materially influence intervention behavior and were not tuned per-user per-scene."
- Future work: "deploy on physical hardware ... study the impact of class-K choices and adaptive shaping on user acceptance and intervention rates with a more extensive user study."
- Security: none.
- THIS IS THE CLOSEST XR + shared autonomy + runtime assurance paper found: three-way composition (operator VR intent, autonomy blend, CBF) with no visibility of which layer changed the command. Gap (D): attribution of deviation (blend vs filter vs attack) to the VR operator.
- XR essential? Yes (VR teleop is the input modality). ROS? Not stated. Evidence: A

### 2.6 Zhang & Tron, "Learning Personalized Safety Interventions for Haptic Human-Robot Shared Control", arXiv 2607.19534 (Jul 2026)
- Method: operator reviews FPV replay with haptic feedback, edits force magnitudes sparsely; GP interpolation; optimise CBF response gains to match preferences.
- System: AirSim HIL + DJI Tello; "Communication between the drone, host computer, and haptic device is implemented through ROS".
- Eval: no formal user study; 23.1% MSE reduction.
- Future work quote (Sec 6): "A comprehensive user study will evaluate annotation effort, perceived workload, and the usability of the preference-learning procedure."
- Security: none. KEY GAP (D): operator corrections directly tune safety-filter gains -> a malicious or coerced/biased operator (or tampered replay) can weaken the safety filter; no bounds on how much preference-learning may relax safety are discussed in extraction. This is "operator corrections used as training data for the assurance layer itself" - distinct from generic data integrity because it targets the safety envelope parameters.
- XR? FPV replay (not XR). ROS: yes (used). Evidence: A

### 2.7 Collier, Narayan, Admoni, "The Sense of Agency in Assistive Robotics Using Shared Autonomy", arXiv 2501.07462 (Jan 2025)
- Kinova 7-DOF, joystick + blending alpha dial; N=24. "higher goal-directed robot autonomy adversely affects SoA"; only 15.6% trials had perceptually significant assistance changes.
- Proposes "disagreement angle theta_d between executed and user commands could be a proxy metric for one component of SoA".
- Future work: "Future work will augment this study for people with upper mobility limitations".
- Security: none. Gap (D): the perceptual threshold for noticing executed-vs-commanded mismatch defines a stealth budget for an adversary (or faulty assurance layer) to alter execution without operator noticing; unexplored.
- Evidence: A

### 2.8 Pei et al., "FARM: Reading Failure Signals from the Internal Predictive States of a Frozen Robotic World Model", arXiv 2609.11445
- Runtime failure monitor from frozen world-model latents; human-in-loop framed as control switching between autonomy and expert takeover (HG-DAgger). No security.
- Evidence: B (PDF extraction weak; numbers not extracted)

## Cat 3: Teleoperation security (latency, command injection, network, operator-targeted attacks)

### 3.1 Sabouri, "Cybersecurity of Teleoperated Quadruped Robots: A Systematic Survey of Vulnerabilities, Threats, and Open Defense Gaps", arXiv 2602.23404v1 (Feb 2026)
- Scope: 130 publications 2019-2025. Six-layer taxonomy: perception; VR/AR-specific (cybersickness induction, HMD side channels, display content injection); communication; control-signal (FDIA, replay, hijack, delay injection); localisation; network/system (ROS topic flooding, node impersonation, supply chain).
- Quote: "communication delay of 50ms—imperceptible for a wheeled robot—can result in a quadruped missing the crucial swing-to-stance transition when ascending stairs, leading to a tumble fall".
- Quote: "critical maturity gap between field-deployed communication protections (TRL 7–9) and largely experimental perception and operator-layer defenses (TRL 3–5)."
- Quote on e-stop: "depending on the gait phase, terrain, and velocity, it may induce a loss of balance or uncontrolled descent, thereby exacerbating harm instead of mitigating it."
- Notes behavioural (LLM) and cyber barriers may "simultaneously fail when autonomy is influenced by language-model components."
- Eight gaps (Sec VI): 1 gait-phase-aware IDS; 2 real-time FDIA detection; 3 "Stability-Preserving Recovery Control Under Cyber Attack"; 4 perception attack detection for legged dynamics; 5 "Operator Degradation Detection and Adaptive Autonomy Transfer"; 6 locomotion-aware comms; 7 "Cross-Layer Anomaly Correlation for Coordinated Attack Detection"; 8 fleet-level/wormable (UniPwn).
- Adversarially-triggered autonomy handover: not cited (no attack papers on the handover mechanism) -> Gap 5 treats transfer as a defense only; the transfer trigger itself (operator-degradation detector) is an attack surface (D). NB: overlaps excluded "authority handoff" only if framed as lease; framed as attacking the degradation detector/arbitration it is in scope.
- XR essential? Partly (VR/AR layer). ROS essential? Partly (ROS 2/DDS in Layer 6). Evidence: A

### 3.2 Kwon et al., "Perfectly Undetectable False Data Injection Attacks on Encrypted Bilateral Teleoperation System based on Dynamic Symmetry and Malleability", arXiv 2409.13061 (Sep 2024)
- Threat: MITM exploiting ElGamal homomorphic malleability + manipulator dynamic symmetry (Lie group) -> reflection/scaling FDIAs.
- System: 2-DOF leader (Atlanta) / follower (Tokyo), 4-channel bilateral, <10 ms VPN.
- Result: follower altered while "the operator who manipulates the leader device perceives the operation as if it were normal"; with obstacle, force feedback mirrored -> "could lead to dangerous situations if the human operator is not able to detect the attack in time."
- Limitation quote: "identical leader and follower movements were not reproduced across different trials due to the nature of the human-in-the-loop system."
- Future work: "investigations of attack synchronization, communication delays as well as countermeasures to prevent malleability-based attacks."
- Generic solution? Authenticated encryption / MACs defeat malleability (generic crypto) - but encrypted control wants homomorphism; so partial.
- Relevance: canonical example of operator-perceived vs executed divergence; not with learned policies / XR.
- Evidence: A

### 3.3 Kundu et al., "Securing Virtual Reality Experiences: Unveiling and Tackling Cybersickness Attacks with Explainable AI", arXiv 2503.13419 (Mar 2025)
- Threat: imperceptible perturbations fooling DL cybersickness detector so mitigation is not triggered (or triggered wrongly).
- Defense: XAI-guided attack detection; HTC Vive Pro Eye testbed.
- Teleop: not addressed. XR essential: yes. ROS: no. Evidence: B
- Older foundational (not re-read in body, B): Bonaci et al. "To Make a Robot Secure" arXiv 1504.04339 (2015; Raven II MITM/intention modification); Alemzadeh et al. DSN 2016 "Targeted Attacks on Teleoperated Surgical Robots: Dynamic Model-based Detection and Mitigation" (~90% detection).

## Cat 4: Robot safety standards (ISO 10218, ISO/TS 15066 SSM) interplay with teleoperation / learned control

### 4.1 Parma, Tonola, Pedrocchi, Beschi, "Embedding ISO 10218 Safety Compliance in Robots via Control Barrier Functions for Human-Robot Collaboration", arXiv 2606.13203 (Jun 2026)
- Method: SSM embedded as CBF with worst-case stopping forward prediction including human acceleration; SQP (Python/Numba/quadprog). PFL context only.
- System: UR10e, ZED 2 skeleton + Inxpect X-300 radar; ROS 2 (Ubuntu 22.04).
- Assumption: "certified real-time tracking of humans" per IEC TS 61496-4-3:2022; prediction error "absorbed into the minimum admissible distance parameter".
- Eval (15,000 s sim): Method II 789 laps, 0.81 mean scaling vs external SSM baseline 41 laps, 0.15 scaling; 63% lower mean trajectory error than Method I.
- Limitation quotes (Sec VI): "The constant human acceleration assumption is effective, it requires a conservative safety buffer C to absorb prediction errors."; "System performance relies on static SQP cost-function weights...".
- Future work: "Integrating probabilistic models for human motion forecasting could tighten this bound..."
- Absent: teleop, learned policies, adversarial sensing, XR.
- Gap (D): SSM-CBF throttles robot speed silently (scaling factor); a remote teleoperator (possibly XR) commanding a cobot under SSM sees commanded vs scaled motion mismatch; and a spoofed human-tracking input can either freeze (DoS) or unlock full speed. Neither the remote-operator case nor adversarial pose input is addressed.
- ROS essential? used. XR? No. Evidence: A

### 4.2 Ding, Cui, Wang, Wen (Siemens), "Toward Certified Functional Safety for Industrial Humanoid Robots: The Fail-Passive Gap and a Feasibility Study", arXiv 2608.02809 (Aug 2026)
- Fail-passive gap: "removing power from a walking biped produces an uncontrolled fall, which is itself a hazard."
- Learned fallback "yields a probabilistic confidence rather than a certifiable guarantee."
- Limitation quotes (Sec IX): "motion-policy interruption and transition to a balanced standstill are not certified."; "The G1's onboard compute is standard COTS, so the SDA endpoint is not a certified safety runtime and carries no SIL/PL claim."; "Single zone, single scenario (may not generalize)."
- No teleop, no human override, no ROS, no cybersecurity.
- Consistent with Sabouri 2602.23404 e-stop observation. Evidence: A

### 4.3 Prather, "The Geopolitics of Teleoperated Robots" (Substack blog, 24 Oct 2025)
- Claim: standards "neither explicitly deals with remote tele-operation over a network where the operator may be thousands of kilometres away"; lack "explicit annexes that treat the remote operator as a safety function, with shift-length limits, recertification, and scenario-based evaluation."; "all operator interventions are logged as data for machine learning".
- Missing: network-health fallback, operator fatigue, cybersecurity of human-robot links.
- Evidence: C (industry blog, not peer-reviewed)

### 4.4 ISO 10218-1:2025 (per ANSI/A3 blog pages returned by search; standard text not read)
- 2025 revision adds "requirements for cybersecurity to the extent that it applies to industrial robot safety", Class I/II robots, collaborative applications merged (ISO/TS 15066 content). Evidence: C/B (secondary pages only; not verified against standard text).

## Cat 5: Side channels in robotics (acoustic, EM/RF, power, network)
(Network traffic-analysis privacy is an EXCLUDED direction for novelty; listed only to mark coverage.)

### 5.1 Acoustic / RF physical side channels (B, from search + abstract pages; bodies not re-read)
- "Fingerprinting Robot Movements via Acoustic Side Channel", arXiv 2209.10240 (2022): smartphone mics fingerprint robot movements and patterns (e.g., surgical procedures). Evidence: B
- "Reconstructing Robot Operations via Radio-Frequency Side-Channel", arXiv 2209.10179 (2022). Evidence: B
- ASIDS, Computers & Security (2025, S0167404825002755): acoustic side-channel *used defensively* as IDS for industrial arms; 2.36% trajectory reconstruction error, 95.9% detection over >25,000 cycles. Evidence: B
- Network: "Can You Still See Me?: Reconstructing Robot Operations Over End-to-End Encrypted Channels" arXiv 2205.08426; "On the Feasibility of Fingerprinting Collaborative Robot Network Traffic" arXiv 2312.06802; joint-level controller actions from encrypted teleop traffic (Springer 2025 chapter, ~97% per search snippet; page paywalled/unread). Evidence: B
- Gap relevant to this agent (D): no found work uses physical side channels (acoustic/EM) as an *independent ground-truth witness* of what the robot actually executed, compared against what the (XR) operator is shown - ASIDS is the closest (acoustic trajectory reconstruction for IDS) but has no operator/teleop/XR framing.
- XR-side channel: Sabouri 2602.23404 lists "HMD side-channel leakage" (eye-tracking/IMU exposing operator intent) as a layer-2 threat; no dedicated teleop paper found in this pass.

## Cat 6: Cyber-physical attacks on robot perception relevant to what the operator sees

### 6.1 Nagaraja, Bahsi, da Cunha, "From Prompt to Physical Actuation: Holistic Threat Modeling of LLM-Enabled Robotic Systems", arXiv 2604.27267v2 (May 2026)
- Method: DFD + STRIDE-per-interaction, integrating ATT&CK, ATLAS, OWASP LLM Top 10; edge-cloud LLM ground robot; conceptual, no ROS, no empirical eval.
- Human operator: status feedback loop is a "human-in-the-loop safeguard"; tampering "can mask unsafe robot behavior, eliminating the human-in-the-loop safeguard".
- Finding: "no component between the User Interface (P1) and the Autonomous Platform (P6) independently validates whether the LLM-generated plan is safe".
- Limitation quotes (Sec III-A): "training-data poisoning and model supply-chain attacks are outside scope"; "Our analysis is limited to a single autonomous robot".
- Open problem (Sec V): "a unified taxonomy for LLM-enabled cyber-physical systems remains an open research challenge".
- Future work (Sec VI): "empirical validation on a physical robotic platform are natural next steps".
- Relevance: explicitly names feedback-loop tampering that blinds the human supervisor, but only as a threat-model entry, no mechanism/eval. Gap stands (D).
- XR? No. ROS? No. Evidence: A

### 6.2 Sabouri 2602.23404 (see 3.1): layer-1 camera feed attacks: "Fake object insertion", "Obstacle removal", "Video replay", "Temporal desynchronization"; mirror-based LiDAR phantoms; attacks "steering human decision-making toward unsafe or suboptimal actions". Evidence: A (survey)

### 6.3 Vanlyssel, Roman, Anwar, "Silent Subversion: Sensor Spoofing Attacks via Supply Chain Implants in Satellite Systems", arXiv 2603.10388 (Mar 2026)
- Off-domain (NASA NOS3/cFS) but shows operator-console deception: housekeeping "reflect the *intended* operational state rather than the actual hardware state"; COSMOS shows valid-looking telemetry.
- Limitation quote (Sec VI-D): "All experiments were conducted within NASA's NOS3 simulation environment; we did not test on flight hardware..."
- NB: attack relies on MID-only identity -> overlaps EXCLUDED identifier-checking direction. Analogy only. Evidence: A

## Cat 7: Human override vs autonomous policy arbitration; operator corrections as training data (shared control, mixed autonomy)

### 7.1 Xia et al., "Human-assisted Robotic Policy Refinement via Action Preference Optimization" (APO), arXiv 2506.07127 (v Oct 2025)
- Collection: SpaceMouse real-time corrective interventions during deployment. Auto-labelling: "last 10 actions before human intervention" marked undesirable; human actions c_t=2, policy actions c_t=1.
- Eval: e.g., Coffee 44%->60%; real Insert 65%->85% (in-dist), 25%->55% (position disruption).
- Assumption: human corrections trusted; no validation.
- Limitation quote: "the experiments are based solely on autoregressive VLA models. Future work should explore a broader range of VLA frameworks, including regression-based approaches and diffusion policy models".
- Security: none.
- Gap (D): the *timing* of an intervention is itself a label (negative preference on the preceding 10 actions). An attacker who can influence *when* the operator intervenes (e.g., by manipulating what the operator sees, or injecting spurious takeover events) can push negative preference onto arbitrary safe behaviours without touching action data. Differs from generic data poisoning because the channel is the operator's perception->decision loop. Not addressed by existing work found.
- Evidence: A

### 7.2 Xiao et al., "ROVE: Unlocking Human Interventions for Humanoid Manipulation via Reinforcement Learning", arXiv 2606.17011v1 (Jun 2026)
- Interface: "the motion-capture operator observes the robot state through a VR headset and aligns their body and hand pose with the current humanoid and dexterous hand configuration"; command filtering smooths transitions.
- Method: intervention episodes decomposed into autonomous rollout / adaptation / recovery; penalty at t_r ("conservative boundary"); Optimistic Value Estimation; human videos for value.
- Eval: whiteboard 45%->80%, toaster 56.7%->86.7%; beats HG-DAgger, RECAP, Filtered BC.
- Limitation quotes: "human experience is currently used only for value learning, not for direct policy learning"; "ROVE is mainly an offline or iterative offline RL framework. Extending it to online RL would require efficient exploration and stable deployment-time updates".
- Security: none.
- KEY: this is VR-teleop + learned humanoid policy + intervention-derived RL labels - exactly the XR x learning intersection. What the operator sees in VR determines takeover time t_r and therefore reward penalties. No integrity analysis of the VR view or takeover signal.
- XR essential? Yes (VR headset for takeover). ROS? not stated. Evidence: A

### 7.3 Belsare et al., "What Is My Robot Thinking? Design Considerations for Transparent and Trustworthy Shared Autonomy", arXiv 2606.06870v2 (HRI)
- N=25 within-subjects; visual/auditory x sparse/rich feedback of inferred goal on a tablet.
- Findings: "Providing feedback significantly improves intent alignment and reduces corrective inputs"; "revealing the robot's full belief distribution did not consistently improve alignment or trust."
- Future work (Sec VIII): "adaptive transparency strategies..."; "Longitudinal studies are needed..."; "explore modality trade-offs under degraded visual conditions, sensor misalignment, and alternative assistive contexts".
- Security: none; no safety filter; no AR/VR.
- Gap (D): transparency display is trusted; if the displayed belief is spoofed, users reduce corrective inputs ("reduces corrective inputs") -> transparency increases reliance, thus a spoofed transparency channel suppresses human override. Not studied.
- Evidence: A

### 7.4 Kenny et al., "GUIDER: Evaluating Goal-Free Human Intent Inference for Teleoperated Manipulation on Real-Robot Data", arXiv 2608.15446 (Aug 2026)
- System: Franka Panda on Ridgeback, joystick, MoveIt 2 Servo, ROS 2 Humble, PREEMPT-RT; operator "cannot directly see the manipulator" (camera-only view).
- Eval: target within predicted set 20/20; time to confident prediction 3.7 s mean; stability 96.4%; single operator.
- Future work (Sec VI-VII): "Future work will integrate GUIDER's online belief state into closed-loop shared-autonomy behaviors...".
- Security: none. Gap (D): intent inference driven by operator motion + perception; adversarial objects/perception could steer inferred goal -> assistance pulls operator toward attacker goal. Not studied.
- ROS: yes (used). XR: no (monitor). Evidence: A

### 7.5 Earlier pieces noted (B): IntervenGen arXiv 2405.01472 amplifies "a handful of interventional corrections provided by a single human operator" into large synthetic intervention sets (robustness up to 39x with 10 interventions) -> any malicious/erroneous intervention would be amplified (D). HAIM-DRL 2401.03160 (human takeover switch function T). No security analysis in snippets.

### 7.6 ByteDance Seed, "End-to-End Dexterous Arm-Hand VLA Policies via Shared Autonomy: VR Teleoperation Augmented by Autonomous Hand VLA Policy for Efficient Data Collection", arXiv 2511.00139 (Sep 2025)
- Interface: XRoboToolkit, OpenXR, "90fps, <100ms latency"; operator controls 6-DoF arm via VR controllers; DexGrasp-VLA controls 12-DoF hand autonomously.
- Data from this shared autonomy (100 demos) trains end-to-end arm-hand VLA ("temporally synchronized observations and actions from both control sources").
- Eval: DexGrasp-VLA 95.5%; end-to-end 88.7% (91.7 seen / 85.6 unseen); tactile ablation 90% vs 21%.
- Limitation: "an initial proof-of-concept of the full stack, without particular engineering efforts".
- Security: none. ROS: none.
- Gap (D): training data mixes XR-operator actions and autonomous-copilot actions; provenance of which DoF came from human vs copilot determines what is learned; a compromised copilot contaminates "human" demonstrations. (Borderline with excluded generic data integrity / trace provenance - flag.)
- XR essential? Yes. Evidence: A

### 7.7 Zhou, Yang, Weber, Erickson, "SAPS: Shared Autonomy for Policy Steering by Blending Teleoperation with a Pretrained VLA", arXiv 2606.15568 (Jun 2026)
- Arbitration: takeover (hard switch), equal blending, cosine-similarity confidence gamma = sigmoid(k cos theta), k=6; a = alpha a_VLA + (1-alpha) a_expert.
- Interface: gamepad/keyboard (no VR).
- Eval: LIBERO-PRO pi0.5 15.0% -> cosine 97.4% (30.0% intervention); real hardware ~26.7% -> 98.3% (~62.4% intervention).
- Limitation quotes: "SAPS requires a human operator at test time, so performance depends on operator timing, skill, and the teleoperation interface"; "because SAPS uses blending with the policy rather than explicit task progress, intent, uncertainty, contact, or safety estimates, it can fail when the policy is confidently wrong".
- Operator visibility of blended command: not addressed. Security: none.
- KEY Gap (D): agreement-based arbitration grants authority to the policy when it agrees with the human; an adversarially-steered VLA (cf. Jones 2506.03350 persistence attacks) can mimic the operator's direction to accrue alpha, then deviate - "authority farming". Not studied anywhere found. Generic fix? Bounding alpha change rate / safety filter post-blend (BarrierIK-like) partially, but does not address deception.
- Evidence: A

## Cat 8: Attacks on the runtime-assurance layer itself (safety filters / monitors)

### 8.1 Arnstrom & Teixeira, "Data-Driven and Stealthy Deactivation of Safety Filters", arXiv 2412.01346 (Dec 2024); predecessor "Stealthy Deactivation of Safety Filters" arXiv 2403.17861
- Threat: FDIA "injects false sensor measurements to bias state estimates toward the interior of a safety region" so CBF filter accepts unsafe inputs; data-driven version needs only I/O observations. Eval: inverted pendulum. Predecessor proposes a bias detector (per search snippet).
- Human: none. Relevance (D): with a teleoperator, a deactivated filter is invisible - operator believes filter is protecting; combined with "transparency arrows" (2504.11717) showing no intervention, the operator infers their commands are safe.
- Evidence: B (html 404; abstract page only)

### 8.2 Tan et al. (Ames, Tabuada), "Secure Safety Filter: Towards Safe Flight Control under Sensor Attacks", arXiv 2505.06845 (May 2025)
- Threat: arbitrary sensor spoofing, "zero-trust sensor fusion"; up to s attacked sensors.
- Method: Secure State Reconstructor + robust CBF over all plausible states. SITL + Holybro X500 hardware.
- Limitation quotes: feasibility assumption "is challenging to verify in general"; attacks injected between EKF and control, not physical; "future work will test different sensing and attacking configurations".
- Human pilot: not mentioned (fully autonomous).
- Generic solution status: this IS the generic fix for spoofed-state safety filters (s-sparse attack). Does not cover human-in-loop or what the operator's display shows.
- Evidence: A

### 8.3 Yu et al., "ActFovea: Runtime Safeguarding for VLA Policies via Spatiotemporal Visual-Action Consistency", arXiv 2607.29169 (Jul 2026)
- Threat: non-adversarial disturbances (visual overlay, visual delay, frozen replay, action drift); "disturbances introduced after this interface are outside our threat model."
- Eval (LIBERO, pi0): overlay 49.3->90.3%; delay 76.2->86.0%; drift 83.1->90.1%; frozen replay 2,000/2,000 timely safe failure.
- On detection: "bounded safe-failure procedure"; no human handover.
- Limitation quote: "Formal collision-avoidance guarantees lie outside the scope of this mechanism."
- Gap (D): the same visual-delay/frozen-replay disturbances hit a teleoperator's XR stream; ActFovea protects the policy's view, not the human's; and it halts rather than hands to human.
- Evidence: A

## Cat 9: Further surveys (for coverage check)

### 9.1 Kojima et al. (U Tokyo / Japan AISI), "A Comprehensive Survey on Physical Risk Control in the Era of Foundation Model-enabled Robotics", arXiv 2505.12583v2 (May 2025)
- Open problems (Sec 5): "there is much room to study...pre-incident risk mitigation strategies"; "research that assumes physical interaction with humans" underdeveloped; "essential issues of foundation models themselves".
- Human: intervention data to train failure classifiers / RL (4.3.3); "errors can also be addressed through human intervention, such as teleoperation" (4.3.1). No shared control, no AR/VR. Evidence: A (survey)

### 9.2 Yang et al., "Towards Trustworthy Physical AI: From Theory to Practice Across the Life Cycle", arXiv 2607.22877v3 (Sep 2026)
- Sec 6: "Safety must be enforced _online_, within the control period, by a filter or fallback controller rather than post-hoc moderation"; "evidence does not transfer between stages of the life cycle for free"; "continuous assurance, drift monitoring, and explicit re-validation triggers".
- Uses ISO/TS 15066 SSM protective distance formula; conformal scores "trigger human intervention" when confidence drops. No XR, no ROS. Evidence: A (survey)

---------------------------------------------------------------------
## SYNTHESIS

### Does existing work address the specially-requested interaction problems?
| Problem | Closest existing work | Status |
|---|---|---|
| Safety filter modifies commands -> operator view/intent diverges from execution | BarrierIK 2603.01705 (VR, no visualisation of filter), HCSF 2504.11717 (arrows, benign), Collier 2501.07462 (disagreement angle theta_d as SoA proxy), Kwon 2409.13061 (attack invisible to operator) | Usability addressed for benign case; ADVERSARIAL exploitation of the divergence budget and ATTRIBUTION (blend vs filter vs attack) unaddressed (D) |
| Operator corrections used as training data | APO 2506.07127, ROVE 2606.17011 (VR), IntervenGen 2405.01472, ByteDance 2511.00139 (XR), Zhang&Tron 2607.19534 (tunes CBF gains) | All assume trusted corrections; none analyse manipulation of intervention *timing* via operator's view, or erosion of safety-filter parameters via preference edits (D). Generic data poisoning work exists (1.8) but targets demo content, not the intervention signal |
| Shared-autonomy arbitration exploitable by adversaries | SAPS 2606.15568 (cosine-confidence), Banik 2608.16293 (cooperative game), Sense-of-agency 2501.07462 | No security analysis found; agreement-based arbitration invites "authority farming" (D) |
| Runtime-assurance switching invisible/confusing to operator | Simplex 2509.21014 (operator acknowledges re-enable), ActFovea 2607.29169 (halts, no handover), stealthy filter deactivation 2412.01346 | Mode-confusion literature (automotive, B) exists; no robot/XR paper links RTA switch visibility with adversarial manipulation (D) |
| Attacks on assurance layer | 2412.01346 / 2403.17861 (deactivation), 2505.06845 (secure filter) | Generic secure-state-estimation fixes exist for autonomous case; human-in-loop consequence unstudied |

### Author-stated open problems (human teleop/XR + robot/ROS + learning/assurance)
1. SAPS 2606.15568 Limitations: "SAPS requires a human operator at test time, so performance depends on operator timing, skill, and the teleoperation interface" and "it can fail when the policy is confidently wrong". Generic cover: post-blend CBF (BarrierIK) bounds physical harm only; no generic solution for adversarial/over-confident policy capturing arbitration weight.
2. BarrierIK 2603.01705: "Design choices for the barrier (e.g., class-K functions and shaping) materially influence intervention behavior and were not tuned per-user per-scene"; future: "study the impact of class-K choices and adaptive shaping on user acceptance and intervention rates". Generic cover: personalisation (2607.19534) - but that creates a tamperable tuning channel; no bounded-personalisation method found.
3. Zhang & Tron 2607.19534 Sec 6: "A comprehensive user study will evaluate annotation effort, perceived workload, and the usability of the preference-learning procedure." (operator edits tune CBF gains over ROS). Generic cover: none for security of preference-tuned safety parameters.
4. Sabouri 2602.23404 Sec VI Gap 5 "Operator Degradation Detection and Adaptive Autonomy Transfer" + "critical maturity gap between field-deployed communication protections (TRL 7–9) and largely experimental perception and operator-layer defenses (TRL 3–5)". Generic cover: none (operator-layer, VR cybersickness attacks included).
5. Kwon 2409.13061: attack "could lead to dangerous situations if the human operator is not able to detect the attack in time"; future: "countermeasures to prevent malleability-based attacks". Generic cover: authenticated encryption covers the channel; operator-side detection of commanded-vs-executed divergence not covered.
6. Nagaraja 2604.27267: status-feedback tampering "can mask unsafe robot behavior, eliminating the human-in-the-loop safeguard"; "no component between the User Interface (P1) and the Autonomous Platform (P6) independently validates whether the LLM-generated plan is safe". Generic cover: RoboGuard-type guardrail for plan; signed telemetry for transport; semantic truthfulness of what the human sees is uncovered (D).
7. Belsare 2606.06870 Sec VIII: "explore modality trade-offs under degraded visual conditions, sensor misalignment, and alternative assistive contexts"; finding that feedback "reduces corrective inputs". Generic cover: none for adversarial transparency displays.
8. ROVE 2606.17011: "Extending it to online RL would require efficient exploration and stable deployment-time updates" (VR takeover -> RL). Generic cover: safe-RL / constrained updates (SafeVLA-type) partial; integrity of takeover signal uncovered.
9. HCSF 2504.11717 Sec VII: "Future work could explore transferring the learned safety filter to real-world racing environments"; assumes benign human (no adversarial input discussion). Generic cover: none for adversarial/strategic humans gaming a learned filter.
10. RoboPAIR 2410.13691 Sec 6.4: need "physical safety filters, which (a) place hard physical constraints on robot actions and (b) take into consideration the robot's context and environment." Generic cover: largely addressed by RoboGuard 2503.07885 + CBF work for autonomous case (not with human in loop).
(Also C-level: Prather blog: standards lack "explicit annexes that treat the remote operator as a safety function".)

### Candidate gaps (all D = inference; check vs excluded list)
G1 Deviation attribution under layered control: operator(XR) -> arbitration blend -> safety filter -> execution; three legitimate deviation sources plus attack, operator cannot attribute. Stealth budget = perceptual threshold (Collier theta_d). Not "simple warning UI" if framed as verifiable attribution; but risk of overlap with excluded "simple safety warning UI" - must be mechanism, not display.
G2 Arbitration capture ("authority farming") in confidence/agreement-based shared autonomy with VLAs (SAPS-type) by adversarially steered policy (Jones 2506.03350). No existing work.
G3 Intervention-signal manipulation: intervention *timing* labels (APO "last 10 actions", ROVE t_r) steered by manipulating XR operator view -> preference poisoning without touching action data. Borderline with excluded generic training-data integrity; distinct channel.
G4 Safety-envelope erosion through operator preference tuning of CBF gains (2607.19534) - bounded personalisation.
G5 Silent RTA/filter deactivation + transparency cue = false reassurance for operator (2412.01346 x 2504.11717).
