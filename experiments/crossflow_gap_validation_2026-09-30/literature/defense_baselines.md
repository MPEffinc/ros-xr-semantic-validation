# Defense baselines and related work (literature)

Cutoff 2026-09-30. Evidence levels: **A** full paper body read, **B** abstract/publisher metadata,
**C** README/implementation docs, **D** our inference (never presented as an author claim).
The per-paper entries below were extracted by a research-assistant agent from pages it fetched; load-bearing
quotes used in `../docs/05_existing_defenses.md` (Tang et al. ARES 2025 §7.2 "478 times bandwidth overhead" /
"not practical"; NetShaper minimum interval T = 10 ms; Minos flow-mixing results) were re-checked against
this text before use. Paywalled items (Tang et al. IFIP SEC 2025 body, CoSe 2026 journal) are level B only.

Cutoff: 2026-09-30. Evidence levels: A = full paper body read; B = abstract/publisher metadata; C = README/implementation docs.
Research question under test (attempting to REFUTE): even with strong per-flow traffic-analysis defenses on XR media, XR pose/input, ROS command, ROS feedback, does cross-flow XR<->ROS temporal correlation leak additional task information?

## Group 1-2: Robot encrypted-traffic fingerprinting (Tang et al.)

### P1. On the Feasibility of Fingerprinting Collaborative Robot Network Traffic
- Authors: Cheng Tang, Diogo Barradas, Urs Hengartner, Yue Hu (U. Waterloo). arXiv v1 Dec 2023 (titled "...Collaborative Robot Traffic"), v3 Mar 2025; published ARES 2025 (Best Research Paper award, per UWaterloo news). Springer chapter 10.1007/978-3-032-00624-0_5.
- URL: https://arxiv.org/html/2312.06802v3 (also v1); https://uwaterloo.ca/news/robots-are-prone-privacy-leaks-despite-encryption
- Evidence: A (arXiv HTML body read, v1 and v3, via fetch summaries + verbatim quote requests)
- Problem: can a passive observer infer high-level robot actions from TLS-encrypted command/feedback traffic of a collaborative robot?
- Threat model: passive eavesdropper on the network path between controller workstation and robot (e.g. "wiretapping the Internet connections"); cannot break TLS or compromise endpoints; owns identical robot model for profiling; closed world.
- System: Kinova Gen3 arm, Kinova API v2.3.0 (not ROS; ROS only mentioned as related), script-based high-level control (NOT teleoperation), Ethernet, tcpdump on controller.
- Method: signal-processing features (convolution/correlation against per-command traffic sub-patterns, e.g. Cartesian move, gripper position/speed) + summary stats -> XGBoost. Baselines: WF attacks (k-NN, CUMUL, k-FP, Tik-Tok, RF).
- Evaluation: 4 actions (pick-and-place, pour water, turn on switch, press key), 50 samples each (200). Proposed attack 97% accuracy; WF baselines 26.5-71.5% (v1: k-NN 29.5%, CUMUL 71.5%, k-FP 69.5%).
- Defenses: (1) padding to multiples of x*100 B -> ~40% accuracy at 1000 B with ~700% bandwidth overhead (as summarised); (2) "latency-aware traffic modulation" (fixed packet size + dummy packets at fixed rate, segmented so as not to exceed permissible latency, e.g. 1 ms for 1 kHz control). Sec 7.2 verbatim: "When sending packets at a 0.01s rate, the defense reduces our attack's accuracy to 31% but incurs a staggering 478 times bandwidth overhead." Conclusion: "Unfortunately, this trade-off is not practical in realistic settings, indicating a pressing need for the development of more sophisticated low-delay defense strategies".
- Multi-flow: single command/feedback channel only; no video/sensor flows, no cross-flow correlation.
- Limitations/future work (Sec 8): "Our evaluation matches that of a closed-world attack ..."; "We assumed a stable and high-performance network connection that was free from interference..."; "We aim to explore more systematic methods for evaluating information leakage in robot traffic..."; v1 Sec 8 also lists teleoperation as future work.
- Code: no code URL in paper (none seen).
- Relevance: K1 (HIGH), K6 (explicit latency-constrained constant-rate defense for robot control, found impractical).

### P2. Uncovering Robot Joint-Level Controller Actions from Encrypted Network Traffic
- Authors: Cheng Tang, Diogo Barradas, Urs Hengartner, Yue Hu. IFIP SEC 2025 (40th IFIP Int. Conf. ICT Systems Security and Privacy Protection, Maribor, May 2025), Springer pp. 121-135 (per UW lab page). Journal extension: "Uncovering Robot Joint-Level Controller Actions from Encrypted Network Traffic: Empirical Attacks and Information-Theoretic Bounds", Computers & Security 2026, doi:10.1016/j.cose.2026.105018 (listed on Barradas publications page; full text 403, not read). UW lab page also lists a related ARES 2025 item "Evaluating Privacy Implications of Robot Arms: Fingerprinting Joint-Level Controllers" (not read).
- URLs: https://link.springer.com/chapter/10.1007/978-3-031-92882-6_9 (paywalled redirect); dataset https://zenodo.org/records/15007304 ; https://cs.uwaterloo.ca/~dbarrada/publications/
- Evidence: B (abstract via search snippets + Zenodo metadata + publication lists; body NOT read)
- Problem/threat model: teleoperation of a robot arm over encrypted network communication; eavesdropper analysing packet timing, size, direction.
- System: Sawyer collaborative arm (Zenodo "sawyer_ros.zip" -> ROS-based setup), teleoperated from smartphone IMU through three joint-level modalities: position, velocity, torque; four distinct actions.
- Result (abstract): "an adversary can accurately identify the actions performed by the robot" with state-of-the-art traffic analysis; prototypes a defense and analyses performance/privacy trade-offs across control modalities. No per-modality numbers seen by me.
- Code/data: data at Zenodo DOI 10.5281/zenodo.15007304 (CC-BY 4.0, 7.4 GB); no code URL seen.
- Multi-flow: not stated in what I read (single teleop command stream implied).
- Relevance: K1 HIGH (teleoperation + ROS-based robot), K6 partially.

### P3. Can You Still See Me?: Reconstructing Robot Operations Over End-to-End Encrypted Channels
- Authors: Ryan Shah, Chuadhry Mujeeb Ahmed, Shishir Nagaraja (U. Strathclyde). arXiv 2205.08426 (v2 Sep 2022); comment: poster at WiSec'22.
- URL: https://arxiv.org/html/2205.08426v2
- Evidence: A (HTML body read via fetch)
- Threat model: passive eavesdropper on controller-robot channel, TLS 1.2; insider/outsider.
- System: uFactory uARM Swift Pro, master-slave teleoperation over TCP sockets (no ROS), Mininet emulation, ~150k samples.
- Method: DNN on packet timing/length/TLS record length/RTT features to classify individual movements, then reconstruct workflows.
- Evaluation: ~60% baseline movement accuracy; near-perfect with >=50 ms link delay; workflow reconstruction 84-97%; with Tor as countermeasure individual-movement accuracy drops ~20% and workflow reconstruction to ~45-51%.
- Defenses discussed (not evaluated): constant-rate padding (flagged unsuitable for time-critical), IAT padding, GLUE-style background traffic.
- Multi-flow: explicitly single flow; authors state "imaging, system information and sensor data do not directly contribute to movement inference."
- Limitations/future work (Sec 5.3): "Other vectors which could contribute to the classification of robot movements, such as the ability to fingerprint sensor information"; ROS pub/sub and multi-robot as extensions.
- Code: none provided.
- Relevance: K1 HIGH (teleoperation), K3 explicitly left open for robots.

## Group 3: ROS / ROS 2 / other robot encrypted-traffic side channels

### P4. On the (In)Security of Secure ROS2
- Authors: Gelei Deng, Guowen Xu, Yuan Zhou, Tianwei Zhang, Yang Liu (NTU). ACM CCS 2022.
- URL: https://tianweiz07.github.io/Papers/22-ccs-2.pdf ; https://dl.acm.org/doi/pdf/10.1145/3548606.3560681
- Evidence: A (PDF text extracted and read around relevant passages)
- Problem: formal analysis of SROS2 / DDS-Security; 4 vulnerabilities (V1-V4) in Foxy/Galactic/Eloquent.
- Traffic side channel (Sec 4, scope note, verbatim): "we do not consider implicit information leakage via side channels. During our manual analysis, we indeed find one such network side channel in ROS2: when a message is published to a topic, the ROS2 DDS identifies the receiver participants, and sends the message to each one separately. Since the message is the same, the network packets to each participant have the same source IP address, similar packet lengths, and very close timestamps. This allows an adversary to infer sensitive information about other nodes and topics by analyzing the network traffic, even it is encrypted by SROS2." Future work: "How to formally discover such kinds of vulnerabilities is orthogonal to this work, yet an important direction to explore".
- V3 (default rtps_protection_kind = SIGN, CVE-2019-19625): insider adversarial robot lists nodes/topics and infers other robots' tasks (patrolling, guidance, delivery) in RMF clinic world (Sec 6).
- Defense: an encryption scheme (Sec 7) so that traffic between nodes "do[es] not necessarily mean that they are exchanging valid information" -> hides communication topology; not a timing/volume shaper; no latency numbers for side channel seen.
- Relevance: K1 (MEDIUM; topology/task inference, notes a timing side channel qualitatively). Notably the stated side channel is itself a *cross-flow timing correlation* (same message fanned out to several participants -> near-simultaneous packets) inside ROS 2, but unevaluated.
- Code: not checked/seen.

### P5. Detecting Drones Status via Encrypted Traffic Analysis
- Authors: Savio Sciancalepore, Omar Adel Ibrahim, Gabriele Oligeri, Roberto Di Pietro (HBKU). ACM WiseML 2019. DOI 10.1145/3324921.3328791
- URL: https://cri-lab.net/wp-content/uploads/2019/05/Sciancalepore_WiseML2019_website.pdf
- Evidence: A (PDF text read)
- Threat model: passive radio eavesdropper of layer-2 encrypted drone<->RC link (ArduCopter), MAC randomisation assumed; drone operator assumed NOT to apply rate/size evasion.
- Result: flying vs resting status; 200 samples (~3.71 s) -> TP 0.93 / FP 0.07; 400 samples (~7.42 s) -> TP 0.97 / FP 0.04.
- Limitation (Sec 3 adversarial model): "the application of evasion strategies requires further feasibility studies".
- Relevance: K1 (LOW-MEDIUM, coarse robot state from control link).

## Group 4: XR/VR traffic analysis

### P6. I Know What You Did Last Summer: Identifying VR User Activity Through VR Network Traffic
- Authors: Sheikh Samit Muhaimin, Spyridon Mastorakis (U. Notre Dame). arXiv 2501.15313v2 (May 2025); page header "EuroSys '25, March 30-April 3, 2025, Rotterdam" (likely a EuroSys-colocated/poster venue; exact track not verified).
- URL: https://arxiv.org/pdf/2501.15313
- Evidence: A (PDF text extracted and read: abstract, threat model, method, conclusion)
- Threat model (Sec 2.1): attacker on same network as victim capturing headset packets; traffic "encrypted on an end-to-end basis"; one app at a time.
- System: Meta Quest Pro, 25 multi-user VR apps (Rec Room, Horizon Worlds, Gorilla Tag, ...); activities: walking, talking, throwing, flying, button pressing, etc.
- Method: Wireshark; features = average packet length and delta time per second; off-the-shelf ML (random forest best).
- Evaluation (abstract): app ID 92.4%, user activity 91%; <10 min of traffic per app gives >90% app ID and >88% activity ID.
- Defenses: none evaluated (none seen in text).
- Multi-flow: aggregates all headset packets per second; no per-flow or cross-flow analysis.
- Code: none seen.
- Relevance: K2 HIGH (standalone headset traffic -> activity).

### P7. Movement- and Traffic-based User Identification in Commercial Virtual Reality Applications: Threats and Opportunities
- Authors: Sara Baldoni, Salim Benhamadi, Federico Chiariotti, Michele Zorzi, Federica Battisti. IEEE VR 2025. arXiv 2501.16326.
- URL: https://arxiv.org/html/2501.16326v1
- Evidence: A (HTML body read via fetch summary)
- System: public Questset dataset, 60 participants, Meta Quest 2 over wired Quest Link (PC renders and streams to headset); traffic = packet size/timestamp/direction headset<->PC; 4 games (Beat Saber, Cooking Simulator, Medal of Honor, Forklift Simulator).
- Threat model: sniffer on wired/wireless medium (passive), for user *identification*.
- Results: traffic-only 76-82% (Beat Saber 62.8%); movement-only 80-99.7%; combined up to 99.7%; adding traffic to movement improves Medal of Honor "by about 12%, which increases to 18% when considering normalized height".
- Limitation (Sec 5): "The first natural extension of this work concerns the dataset: each game included 30 users and a single session, making identification easier."
- Code: https://github.com/signetlabdei/vr_user_id
- Relevance: K2 (MEDIUM; streaming XR traffic leaks identity), weak K3 (fusion of modalities, but movement data is not network-observable).

### P8. Remote Keylogging Attacks in Multi-user VR Applications
- Authors: Zihao Su, Kunlin Cai, Reuben Beeler, Lukas Dresel, Allan Garcia, Ilya Grishchenko, Yuan Tian, Christopher Kruegel, Giovanni Vigna. USENIX Security 2024. arXiv 2405.14036.
- URL: https://arxiv.org/abs/2405.14036
- Evidence: B (abstract)
- Threat model: attacker is a co-participant in same virtual room; extracts avatar motion data delivered to its own client (not an on-path encrypted-traffic observer).
- Result: 97.62% keystrokes inferred in user study (Rec Room); defenses adopted by industry.
- Relevance: K2 (pose/input stream content leaks keystrokes) - shows XR pose/input stream is task-sensitive, but it is a content-access attack, not metadata.

### P9 (out of scope, noted). VReaves: Eavesdropping on Virtual Reality App Identity and Activity via Electromagnetic Side Channels
- Wei Sun, Minghong Fang, Mengyuan Li; arXiv 2506.17570 (2025). URL https://arxiv.org/html/2506.17570v1. Evidence A. EM (not network) side channel; Quest 3 / Vive XR Elite; 99% app and activity recognition at 1-2 m. No code. Relevance: non-network; shows XR activity leaks via other channels too.

## Group 5: Website-fingerprinting (WF) defenses

### D1. Zero-delay Lightweight Defenses against Website Fingerprinting (FRONT, GLUE)
- Authors: Jiajun Gong, Tao Wang (HKUST). USENIX Security 2020.
- URL: https://www.usenix.org/system/files/sec20-gong.pdf
- Evidence: A (PDF text extracted and read: abstract, Tables 1/3/4, availability)
- Threat model: local passive eavesdropper (e.g. ISP) between Tor client and guard; WF on a single client trace (one page load). Defense runs at client and a relay proxy.
- Mechanism: FRONT injects Rayleigh-distributed dummy packets concentrated at the *front* of the trace, randomised per trace; GLUE injects dummy "glue traces" between page loads so traces cannot be segmented.
- Cost/effect (Table 3/4, DS-19, open world): FT-2 = 0% latency, 48.80% data overhead -> DF F1 0.94 -> 0.40, kFP 0.93 -> 0.46; FT-1 33.01% data; WTF-PAD 32.71% data, DF F1 0.70; Tamaraw 78.43% latency, 162.93% data overhead, DF F1 0.11. GLUE: ~22-44% data overhead (abstract), "3%-53%, depending on client behavior".
- Table 1 classifies BuFLO/CS-BuFLO as Very High latency + Very High data; Tamaraw High/High; all three need "Fixed-rate network transfer".
- Multi-flow: defense is per trace/per client connection; relies on the trace having a feature-rich start (page load). Nothing about concurrent flows or inter-flow timing. (My inference: FRONT's front-padding logic does not map onto long-lived continuous teleop streams, and zero-delay obfuscation leaves real-packet timing intact, which is what cross-flow correlation exploits.)
- Code: https://github.com/websitefingerprinting/WebsiteFingerprinting (simulation code, attacks, defenses, datasets).

### D2. RegulaTor: A Straightforward Website Fingerprinting Defense
- Authors: James K Holland, Nicholas Hopper (U. Minnesota). PoPETs 2022(2):344-362, DOI 10.2478/popets-2022-0049.
- URL: https://petsymposium.org/popets/2022/popets-2022-0049.pdf
- Evidence: A (PDF text read: abstract, design motivation, related work, conclusion)
- Mechanism: regularises download sequence into surges with decaying rate; *upload packet sending is modelled as a function of the download sequence* (Sec 3, verbatim: "by modeling upload packet sending as a function of the download packet sequence, the upload traffic leaks no further information about the destination web page").
- Cost/effect (abstract): closed world Tik-Tok 66% (vs comparable defenses) -> 25.4%; 6.6% latency overhead; 79.7% bandwidth overhead (vs 119% for FRONT-2500); open-world precision-tuned Tik-Tok F1 .135 vs .625 for FRONT-2500.
- Related work on traffic splitting (TrafficSliver, Multihoming), verbatim: "TrafficSliver only prevents WF attacks that take place at the guard node, and Multihoming does not protect against local attackers who can see outgoing traffic."
- Limitations (Sec 6): "we did not test it in terms of preventing an attack from identifying a web site based on a series of page loads ... left for future work."
- Multi-flow relevance: the up/down coupling design is the closest WF-defense analogue to *removing inter-direction (command vs feedback) correlation*, but within one Tor connection and for bursty web traffic; not for independent concurrent flows.
- Code: not located in the paper text I grepped (no own-code URL seen).

### D3. Surakav: Generating Realistic Traces for a Strong Website Fingerprinting Defense
- Authors: Jiajun Gong, Wuqi Zhang, Charles Zhang, Tao Wang. IEEE S&P 2022, DOI 10.1109/SP46214.2022.9833722.
- URL: https://cse.hkust.edu.hk/~charlesz/papers/surakav.pdf
- Evidence: A- (PDF text read; the downloaded file reported 6 pages, so possibly partial; abstract + intro + availability read)
- Mechanism: GAN generates realistic sending patterns (burst sequences); client/relay regulate buffered real data to follow sampled pattern (regularisation with realistic templates).
- Cost/effect (abstract, live Tor): TPR reduced by 57% with 55% data and 16% time overhead (42% less data than FRONT); heavyweight setting: TPR 8% with ~50% less data/time overhead than Tamaraw. Also fortifies Walkie-Talkie and TrafficSliver.
- Multi-flow: single Tor circuit/page trace; intro notes multi-tab scenario as related; no concurrent-flow correlation analysis.
- Code: https://github.com/websitefingerprinting/wfd-gan and https://github.com/websitefingerprinting/surakav-imp
- Relevance: K5/K6 via "regulate to generated schedule" idea; time overhead (buffering) is incompatible with ms-level teleop unless the pattern is rate-matched.

### D4. Real-Time Website Fingerprinting Defense via Traffic Cluster Anonymization (Palette)
- Authors: Meng Shen, Kexin Ji, Jinhe Wu, Qi Li, Xiangdong Kong, Ke Xu, Liehuang Zhu. IEEE S&P 2024, DOI 10.1109/SP54263.2024.00247.
- URL: http://www.thucsnet.com/wp-content/papers/meng_sp2024.pdf ; code https://github.com/kxdkxd/Palette
- Evidence: A (PDF text read: abstract, intro, overhead definitions)
- Mechanism: cluster websites with similar traffic, regulate every member to a cluster-uniform "super-matrix" pattern (anonymity set); implemented as Tor Pluggable Transport.
- Effect: reduces SOTA WF accuracy by 73.60% on average live (61.97% on public dataset vs SOTA attack), up to 16.68% more than RegulaTor "with a similar bandwidth and time overhead". Paper uses "moderate overhead" = BOH <100%, TOH <50%.
- Multi-flow: per Tor connection; none.
- Relevance: K5 conceptually (anonymity-set shaping: map a whole task class to one pattern) — would need a *joint* multi-flow super-matrix to cover cross-flow structure.

### D5. BuFLO / CS-BuFLO / Tamaraw (regularisation family; summarised from D1 Table 1 and Table 3)
- Evidence: A for the comparison in FRONT paper (secondary source); original papers (Dyer et al. S&P 2012 BuFLO; Cai et al. CS-BuFLO WPES 2014; Cai et al. Tamaraw CCS 2014) NOT fetched.
- Capability: fixed-rate, fixed-size transmission hides size/timing within a connection; BuFLO/CS-BuFLO "Very High" latency and data overhead, Tamaraw "High"/"High"; Tamaraw measured 78.43% latency, 162.93% data overhead with DF F1 0.11 (FRONT Table 3/4).
- Relevance: K5: if applied to ONE aggregate tunnel, constant-rate removes timing of all inner flows (and hence cross-flow correlation) by construction, but only as long as the rate is never exceeded; if applied per flow, each flow is constant-rate and cross-flow correlation is also removed except for the start/stop (duration) and rate-change events. Cost in teleop: P1 shows 478x bandwidth for latency-bounded constant rate.

## Group 6: DP / provable traffic shaping

### S1. NetShaper: A Differentially Private Network Side-Channel Mitigation System
- Authors: Amir Sabzi, Rut Vora, Swati Goswami, Margo Seltzer, Mathias Lecuyer, Aastha Mehta (UBC). USENIX Security 2024; arXiv 2310.06293.
- URL: https://www.usenix.org/system/files/usenixsecurity24-sabzi.pdf ; project page https://spg.cs.ubc.ca/publication/2024-usenixsec/
- Evidence: A (full PDF text read: design, threat model, evaluation, limitations, conclusion)
- Threat model (Sec 2.3): endpoints inside trusted private networks behind gateway/middlebox; adversary controls public links (ISP), records sizes/timing/direction between gateways, knows NetShaper and its config, can train on arbitrary known streams. Goal = hide *content* of traffic; hiding app identity/type is a non-goal. Verbatim: "NetShaper does not address leaks of one application's sensitive data through the traffic shape of colocated benign applications."
- Mechanism: per-flow buffering queues; every DP shaping interval T a DP (Gaussian) query on queue length gives L~ bytes to send (real + dummy); "Within a tunnel, the Shaper transmits bytes from all active flows into a differentially-private packet sequence" over one QUIC tunnel; neighbouring streams defined over windows W with L1 distance DeltaW; Renyi-DP composition over time. Shapes both directions.
- Multi-flow: explicitly pools multiple flows in one tunnel to "amortize the shaping overheads among multiple flows without compromising the privacy for individual flows" -> an observer sees only the tunnel aggregate. This is a direct instance of K5 (joint shaping). Note: the DP guarantee is per-flow stream-neighbourhood; a joint secret spanning several flows would need group-privacy style accounting (my inference; not analysed in paper).
- Cost: smallest configurable T = 10 ms (Tprep = 6 ms, Tenq = 1 ms profiled); web response latency e.g. T=10ms: 30.47 +/- 3.89 ms, T=50ms: 51.39 ms, T=100ms: 77.49 ms (1.4 KB objects; base network ~0.56 ms); "The latency overhead is dominated by the choice of DP shaping interval"; bandwidth overhead three orders of magnitude lower than constant-rate (CR) for video/web; middlebox reaches ~88% of 10 Gbps line rate; needs 2 extra cores.
- Attack results: unshaped BB classifier 0.61 and TCN 0.99 accuracy on video; drop to ~chance under shaping (Fig 5; exact per-epsilon values not transcribed).
- Cross-direction remark (Sec 5): Pacer "does not shape client traffic. Thus, it leaks the timing and shape of client requests, which could potentially reveal information about the server responses" -> acknowledged request/response (cross-direction) correlation leakage.
- Limitations: Sec 4.2 constant-time crypto and profiling of Tprep/Tenq ("If Prepare's execution exceeds the profiled max values, it violates the theoretical DP guarantees"); Sec 7: "can be extended to mitigate leaks in multi-node systems, but we leave the details to future work."
- Code: https://github.com/ubc-systopia/netshaper
- Relevance: K5 HIGH, K6 (10 ms minimum interval -> incompatible with 1 kHz joint control; potentially compatible with 30-90 Hz XR frames/poses only if added 10+ ms latency accepted).

### S2. Minos: A Lightweight and Dynamic Defense against Traffic Analysis in Programmable Data Planes
- Authors: Zihao Wang, Qing Li, Guorui Xie, Dan Zhao, Kejun Li, Zhuochen Fan, Lianbo Ma, Yong Jiang (Pengcheng Lab / Tsinghua SIGS / Northeastern U.). USENIX ATC 2025.
- URL: https://www.usenix.org/system/files/atc25-wang-zihao.pdf
- Evidence: A (full PDF text read)
- Threat model (Sec 2.1): passive attacker isolating flows by 5-tuple, local (at gateway) or remote (untrusted network); WF and IoT fingerprinting.
- Mechanism (Tofino1 P4 switch): Proxy Module = line-rate header encryption (PRINCE, "encryption round compression") hiding 5-tuple (IPsec-gateway-like tunnel); Schedule Module = dynamic flow scheduling that *interleaves packets from different flows* in round-robin queues to "simulate dummy packets without causing bandwidth and delay overhead"; Traffic Morphing Module = FRONT-like front dummy insertion (window W, probability Omega) + padding, enabled only when fewer than 4 flows share the tunnel.
- Results: flow mixing: attack metrics "converge at n=5. When flow numbers are larger than 5, both metrics are lower than 20%"; Table 5/6: DF accuracy 96.9% -> 7.06% (Minos-500, 0% latency, 6% bandwidth) / 6.67% (Minos-1000, 12% bandwidth); Tamaraw 14.23% latency, 143.82% bandwidth; WTF-PAD 0% / 60%. Multi-flow goodput ~99.2%, 500,000th-packet arrival delay ~2.4%; ~95 Gbps throughput.
- Key caveat for our RQ: flow mixing obfuscates because the *other* flows are unrelated users' flows (anonymity by aggregation). If the mixed flows are the correlated XR and ROS flows of ONE session, the tunnel aggregate is still a (joint) fingerprint; the paper does not evaluate correlated-flow mixing. Author admission (Sec 8): "our simple and intuitive Website Fingerprinting defense cannot reduce the accuracy of Website Fingerprinting attacks to random guess".
- Code: no repository URL found in the paper text.
- Relevance: K5 HIGH (aggregate tunnel + mixing removes per-flow separability, with ~0-12% bandwidth cost), but no latency bound analysis at ms scale for control loops.

## Group 7: Flow-correlation attacks and defenses

### C1. DeepCoFFEA: Improved Flow Correlation Attacks on Tor via Metric Learning and Amplification (incl. the "Decaf" defense)
- Authors: Se Eun Oh, Taiji Yang, Nate Mathews, James K Holland, Mohammad Saidur Rahman, Nicholas Hopper, Matthew Wright. IEEE S&P 2022, DOI 10.1109/SP46214.2022.9833801.
- URL: https://www-users.cse.umn.edu/~hoppernj/deepcoffea.pdf ; code+data https://github.com/traffic-analysis/deepcoffea
- Evidence: A (full PDF text read incl. Sec VI robustness, countermeasures, conclusion)
- Threat model: end-to-end adversary observing client-guard (Tor) flows and exit-server flows; goal = link pairs (correlation, not classification).
- Method: triplet-trained feature-embedding networks (FENs) for each side + "amplification": split flows into short windows (11 windows) and vote, lowering FPR.
- Results: 93% TPR vs at most 13% for prior work when tuned for high precision; 89% vs 13% TPR at 1e-4 FPR vs m-DeepCorr; 85% vs 7.6% at 10k pairs; ~2 orders of magnitude faster.
- **Correlation survives per-flow padding (K4)**: trained on defended traces of obfs4-iat0/iat1, WTF-PAD (27.54% bw overhead) and FRONT (33.26%): "DeepCoFFEA achieved TPRs above 50% for FPR of 10^-5 for all defenses besides FRONT"; DeepCorr collapses (2.7%/2.5%/1.8% TPR at 1e-3) while DeepCoFFEA ">80% of correlated pairs at the same FPR"; FRONT gave "a 15% TPR drop at 10^-3 FPR ... insufficient". Trained only on undefended traces, still ">20% for defended flows with FPR of 10^-5"; "Correlations thus appear to remain between the Tor flow and the exit flow". Authors' claim: "this is the first investigation of the effectiveness of WF defenses against end-to-end flow correlation attacks."
- Decaf defense (Sec VI-E): inject dummy packets at timestamps copied from v of k omega-second windows of a random *peer flow* (omega = 5 s, v/k = 0.5) -> 49.6% bandwidth overhead, "much more effectively than any setting of FRONT"; Decaf-DC comparable to FRONT14 with 4% lower bandwidth. Assumes defender knows approximate attacker window length.
- Future work (Sec VII): "the most important next step is to devise a defense that can be effectively deployed against DNN-based traffic analysis attacks"; also "correlation of VPN or HTTPS proxy services".
- Important nuance for our RQ: this is correlation of the *same* flow at two points (padding only on one side). Our RQ concerns correlation of *different but causally coupled* flows (XR pose -> ROS command -> robot -> ROS feedback -> XR video). The mechanism (window-level timing co-variation survives zero-delay padding) transfers conceptually, but no paper found evaluates causally-coupled heterogeneous flows.

### C2. DeepCorr: Strong Flow Correlation Attacks on Tor Using Deep Learning
- Authors: Milad Nasr, Alireza Bahramali, Amir Houmansadr (UMass). ACM CCS 2018, DOI 10.1145/3243734.3243824; arXiv 1808.07285.
- URL: https://arxiv.org/abs/1808.07285
- Evidence: B (abstract); also secondary results in C1 (DeepCorr collapses to 1.8-2.7% TPR at 1e-3 FPR under obfs4/WTF-PAD/FRONT) and C3.
- Result: ~900 packets per flow -> 96% flow-correlation accuracy vs 4% for RAPTOR in same setting.
- Code/data: DeepCorr dataset distributed via DeepCoFFEA repo notes / Kaggle mirror (https://www.kaggle.com/datasets/ipidkaggle/deepcorr-flow-correlation-of-tor, not opened).

### C3. Defeating DNN-Based Traffic Analysis Systems in Real-Time With Blind Adversarial Perturbations (BLANKET)
- Authors: Milad Nasr, Alireza Bahramali, Amir Houmansadr. USENIX Security 2021.
- URL: https://www.usenix.org/system/files/sec21-nasr.pdf ; code https://github.com/SPIN-UMass/BLANKET
- Evidence: A (PDF text read: abstract, DeepCorr results, limitations)
- Mechanism: input-agnostic ("blind") adversarial perturbations (timing delays, dummy packet insertion, size changes) applied in real time via a Tor pluggable transport; remapping functions enforce network constraints.
- Results vs flow correlation: timing-only perturbation mu=0, sigma=50 ms reduces DeepCorr TP "from 95% to 55%"; combining time and size perturbations "the accuracy of DeepCorr drops from 95% to 59% (with FP = 10^-3) by injecting only 20 packets".
- Limitations (Sec 10): targets DNN-based analysis only; "Non-DNN traffic analysis techniques, in particular flow watermarking techniques ... and volume-based traffic classifiers ... can not be protected by our defense." Also a tailored adversarial-training countermeasure is proposed, i.e. the defense is not robust to an adaptive attacker by construction.
- Relevance: K4/K5 (adversarial per-flow perturbation; tens of ms timing noise -> conflicts with teleop latency; no guarantee against simple cross-correlation statistics).

### C4. Maybenot: A Framework for Traffic Analysis Defenses
- Authors: Tobias Pulls (Karlstad U.), Ethan Witwer (Linkoping U.). arXiv 2304.09510 (v2, 2024; WPES 2023 version per v1 - not verified).
- URL: https://arxiv.org/html/2304.09510v2
- Evidence: A (HTML body read via fetch)
- What: Rust library of probabilistic finite-state machines for padding/blocking; evolved from Tor circuit-padding framework; integrated in Mullvad VPN's DAITA. Can approximate FRONT, RegulaTor, Tamaraw/constant-rate (bypass+replace flags).
- Multi-flow: "There should be one instance of the framework per connection and party/participant ... per circuit ... per connection for TLS, per stream for QUIC". Deployed inside a VPN (DAITA) the instance protects the tunnel, i.e. the aggregate of all inner flows (my reading of "per connection" applied to a WireGuard tunnel).
- Limitations: packet sizes removed ("unclear whether it is even possible to create effective, efficient defenses in settings with variable packet sizes"); simulator "sim2real problem"; blocking cannot be simulated correctly because inter-packet dependencies are unknown.
- Code: https://github.com/maybenot-io/maybenot (MIT/Apache-2.0), crates maybenot, maybenot-simulator, maybenot-ffi.
- Relevance: practical lab tool for implementing per-flow vs per-tunnel constant-rate / FRONT-like machines (K5/K6 testbed).

### C5. The Loopix Anonymity System
- Authors: Ania Piotrowska, Jamie Hayes, Tariq Elahi, Sebastian Meiser, George Danezis. arXiv 1703.00536 (USENIX Security 2017 - venue from general knowledge, not verified on fetched page).
- URL: https://arxiv.org/abs/1703.00536
- Evidence: B (abstract)
- Mechanism: stratified Poisson mixing + loop/drop cover traffic; protects against global passive adversary (breaks timing correlation between flows by design).
- Cost: per-node processing <1.5 ms, but end-to-end delivery "in the order of seconds".
- Relevance: K5 (mixing + cover traffic removes cross-flow correlation) — but seconds-level latency is incompatible with K6 teleoperation.

## Group 8: Multi-flow inference in IoT / conferencing and aggregate defenses

### M1. Keeping the Smart Home Private with Smart(er) IoT Traffic Shaping (STP)
- Authors: Noah Apthorpe, Danny Yuxing Huang, Dillon Reisman, Arvind Narayanan, Nick Feamster. PoPETs 2019 (popets-2019-0040); arXiv 1812.00955.
- URL: https://petsymposium.org/popets/2019/popets-2019-0040.pdf
- Evidence: A (PDF text read: Sec 5 VPN/ILP analysis, STP, future work)
- Threat model: passive ISP/Wi-Fi observer; infers in-home activities from traffic rates of encrypted IoT devices.
- VPN aggregation analysis (Sec 5.2): a VPN "wraps all traffic from an endpoint ... aggregating it into a single" flow, but adversary can still fingerprint devices from VPN traffic rates in cases: single device; "Sparse activity. If there are multiple devices that send traffic at different times, time periods containing traffic from only a single device would still allow activity inference"; plus ML de-multiplexing. "the additional protection is inconsistent and difficult to quantify."
- Independent link padding (constant-rate, Sec 5.3): on their lab gateway "required approximately 40KB/s of overhead traffic ... approximately 104GB of overhead data per month"; latency trade-off with buffering.
- STP: inject cover "fake activity" periods at random; no added latency; adversary confidence vs bandwidth trade-off (inverse-square relation per paper).
- Future work (Sec 8, verbatim): "We are also interested in whether combining metadata from multiple devices could allow an adversary to infer higher-order user behaviors, such as 'hosting a party' or 'late night working.'" -> K3 posed as open (2019).
- Code: https://github.com/NoahApthorpe/iot-inspector (Raspberry Pi config).
- Relevance: K5 (aggregation insufficient if flows are temporally sparse/distinctive — directly analogous to XR+ROS where both flows are active only during teleop), K3 (posed open).

### M2. PingPong: Packet-Level Signatures for Smart Home Device Events
- Authors: Rahmadi Trimananda, Janus Varmarken, Athina Markopoulou, Brian Demsky (UC Irvine). NDSS 2020; arXiv 1907.11797.
- URL: https://arxiv.org/pdf/1907.11797 ; code https://github.com/uci-plrg/pingpong
- Evidence: A (PDF text read around signatures + padding evaluation)
- Method: request/reply packet-pair signatures (lengths+directions); pairs may occur in any of Phone-Device, Device-Cloud, Phone-Cloud communication; a signature can be a set of packet sequences that "appear in different TCP connections" within a signature duration -> multi-connection signature (K3, weak form). >97% average recall.
- Padding evaluation (Sec VII): WAN sniffer, TP-Link plug. VPN-based padding (all packets multiplexed over one tunnel) -> "193,338 positives, or ... more than 1,900 false positives for every event"; per-TLS-connection padding -> "100 detected events, with no FPs" (adversary uses timing/duration filtering). Paper notes timing-based attacks would need a stronger adversary and points to STP for timing.
- Relevance: K5 (single-tunnel multiplexing + padding defeats per-connection signature where per-connection padding fails), K3 (weak).

### M3. Classification of Encrypted IoT Traffic Despite Padding and Shaping
- Authors: Aviv Engelberg, Avishai Wool. arXiv 2110.11188 (Oct 2021); ACM WPES 2022 (DOI 10.1145/3559613.3563191 per search result).
- URL: https://arxiv.org/abs/2110.11188
- Evidence: B (abstract)
- Result: packet-size distribution still fingerprints active IoT devices under padding and shaping; external attacker on aggregated NAT traffic: "at least 96%" recall and precision; distinguishes real activity from cover traffic with "81% accuracy" in 1-s windows.
- Relevance: K4/K5 (aggregate NAT traffic + shaping still leaks which devices are active).

### M4. Peek-a-Boo: I see your smart home activities, even encrypted!
- Authors: Abbas Acar, Hossein Fereidooni, Tigist Abera, Amit Kumar Sikder, Markus Miettinen, Hidayet Aksu, Mauro Conti, Ahmad-Reza Sadeghi, Selcuk Uluagac. ACM WiSec 2020; arXiv 1808.02741.
- URL: https://arxiv.org/abs/1808.02741
- Evidence: B (abstract)
- Result: multi-stage (device type -> state -> user activity) over WiFi/ZigBee/BLE; >90% accuracy; proposes spoofed traffic generation countermeasure (overhead not seen).
- Relevance: K1-analogue (encrypted device traffic -> activities); K3 weakly (multi-device activity inference).

### M5. I Still See You: Why Existing IoT Traffic Reshaping Fails
- Authors: Su Wang, Keyang Yu, Qi Li, Dong Chen. EWSN 2024; arXiv 2406.10358.
- URL: https://arxiv.org/abs/2406.10358
- Evidence: B (abstract page fetched)
- Content (abstract): image-based attack infers user activities despite existing IoT reshaping defenses ("current defending approaches are not sufficient to protect IoT device user privacy"); releases open-source ITEMTK toolkit for benchmarking attacks and defenses (URL not seen).
- Relevance: K4 (reshaping per device fails).

### M6. FlowPrint: Semi-Supervised Mobile-App Fingerprinting on Encrypted Network Traffic
- Authors: Thijs van Ede, Riccardo Bortolameotti, Andrea Continella, Jingjing Ren, Daniel J. Dubois, Martina Lindorfer, David Choffnes, Maarten van Steen, Andreas Peter. NDSS 2020.
- URL: https://www.ndss-symposium.org/wp-content/uploads/2020/02/24412.pdf ; code https://github.com/Thijsvanede/FlowPrint
- Evidence: A (PDF text read: method Sec (correlation graph), evasion discussion)
- Method: cluster flows by destination; model each cluster's activity as binary time series per window; compute normalised **cross-correlation between clusters' activity**, build correlation graph, maximal cliques = app fingerprint. I.e., an explicit *inter-flow temporal correlation* fingerprint over encrypted flows.
- Results (per search abstract/paper): 93.5% precision on previously unseen apps; 72.3% of apps detected within first five minutes.
- Evasion (Sec VI): redirect all traffic through a VPN/proxy; per-app VPN still leaves a single-destination fingerprint; system-wide VPN "would be recognizable as unusual device behavior as our approach would detect all device traffic as originating from a single app".
- Relevance: K3 HIGH as a *technique* (cross-flow temporal co-activity improves identification), K5 (aggregation into one tunnel defeats the inter-flow correlation step but reveals "single app"). Granularity is coarse (window-level co-activity, app identity), not fine-grained task/content inference.

## Group 9: Deterministic / constant-rate teleoperation transport (incidental timing removal)

### T1. A Multiplexing Scheme for Multimodal Teleoperation (Cizmeci et al.) and its precursor "A Visual-Haptic Multiplexing Scheme for Teleoperation Over Constant-Bitrate Communication Links"
- Authors: Burak Cizmeci, Xiao Xu, Rahul Chaudhari, Christoph Bachhuber, Nicolas Alt, Eckehard Steinbach (TUM). ACM TOMM 2017 (DOI 10.1145/3063594); Cizmeci Dr.-Ing. dissertation TUM 2017 (same title); precursor EuroHaptics 2014 (Springer 10.1007/978-3-662-44196-1_17).
- URL (read): http://mediatum.ub.tum.de/doc/1352277/document.pdf (dissertation, open-access link returned by Semantic Scholar API for the TOMM DOI)
- Evidence: A for dissertation (text read: abstract, Sec 3.3, Table 5.5); B for EuroHaptics/TOMM versions (metadata only).
- Mechanism: application-layer multiplexer for haptic + video + audio over a constant-bitrate (CBR) link; "uniformly divides the available transmission rate TR into 1 ms discrete resource buckets and controls the size of the transmitted video packets as a function of the irregular haptic transmission events"; preemptive-resume scheduling with haptic priority; video encoder with accurate rate control (flat bitstream); transmission-rate estimator adapts to capacity changes.
- Results (Table 5.5): CBR 1/2/3 Mbps: force delay mean 10.14/6.47/3.81 ms; video delay ~31-34 ms mean (35 ms constraint), low jitter.
- Security: none — designed for QoS, not privacy. But it is effectively a *joint* (cross-modal) constant-rate channel: haptic events displace video bytes inside a fixed-rate stream, so on the wire the aggregate rate is constant. Caveats (my inference): packet sizes/boundaries per bucket may still be visible unless padded; rate adaptation events (TR estimator, congestion drops) leak coarse state; not evaluated against traffic analysis.
- Relevance: K6 HIGH-ish as an engineering precedent (latency-bounded multiplexing of teleop control + video at ms granularity with known delay cost), K5 (joint CBR multiplexing), but zero security evaluation.

### T2. Time-Sensitive Networking for robotics
- Authors: Carlos San Vicente Gutierrez, Lander Usategui San Juan, Irati Zamalloa Ugarte, Victor Mayoral Vilches (Erle/Acutronic Robotics). arXiv 1804.07643 (2018).
- URL: https://arxiv.org/abs/1804.07643
- Evidence: B (abstract page; plus search snippet stating sub-microsecond sync, ROS 2 message timestamping <100 us, ms-level latencies — snippet not independently verified)
- Content: argues TSN (IEEE 802.1 time-aware shaping etc.) will be de-facto real-time comms for robots; experimental evaluation of a shaping mechanism in a robotic app.
- Relevance: K6 (time-triggered schedules make periodic control traffic timing deterministic, i.e. sender-timing independent of content for scheduled streams) — no privacy analysis; TSN is L2/LAN, not the WAN path a remote XR operator uses. No paper found that analyses TSN/TAS schedules as a traffic-analysis defense.

## Group 10: Additional cross-channel correlation precedents

### X1. Practical Traffic Analysis Attacks on Secure Messaging Applications
- Authors: Alireza Bahramali, Ramin Soltani, Amir Houmansadr, Dennis Goeckel, Don Towsley. NDSS 2020; arXiv 2005.00508.
- URL: https://arxiv.org/abs/2005.00508
- Evidence: B (abstract)
- Content: encrypted IM traffic (Telegram, Signal, WhatsApp) leaks channel membership/admin identity by correlating event timing/size across users' encrypted flows; countermeasures: cover traffic, open-source IMProxy client-side tool (URL not seen in abstract).
- Relevance: K4 (event-level correlation between *different* parties' flows carrying causally linked messages — structurally closest analogue to XR-input -> ROS-command causality), K5 (cover traffic).

### X2. Game of Drones - Detecting Streamed POI from Encrypted FPV Channel
- Authors: Ben Nassi, Raz Ben-Netanel, Adi Shamir, Yuval Elovici. arXiv 1801.03074 (2018).
- URL: https://arxiv.org/abs/1801.03074
- Evidence: B (abstract)
- Content: induces a physical stimulus (e.g. flickering) at a target and correlates it with the bitrate of the drone's encrypted FPV video stream to detect whether the target is being filmed (DJI Mavic).
- Relevance: K4-analogue — *cross-channel* correlation between a known physical/motion event and encrypted video bitrate; in XR teleop the robot's motion (visible in robot-camera video -> XR media flow) is exactly such a stimulus correlated with the ROS command flow.

### X3. Beauty and the Burst: Remote Identification of Encrypted Video Streams
- Authors: Roei Schuster, Vitaly Shmatikov, Eran Tromer. USENIX Security 2017.
- URL: https://www.usenix.org/conference/usenixsecurity17/technical-sessions/presentation/schuster
- Evidence: B (abstract page)
- Content: MPEG-DASH segment bursts leak which video is streamed despite encryption; also via web adversary (JS on nearby device). The BB classifier is re-used as the attack in NetShaper (S1).
- Relevance: supports that the XR *media* flow alone leaks content dynamics (scene motion -> VBR bitrate).

---

# Prior-art collision table (K1-K6)

Legend: collision = how much of the claim is already established in prior art. Evidence levels in brackets.

| Claim | Strongest prior art | Collision | What remains open (honest, uncertain) |
|---|---|---|---|
| K1 encrypted robot/ROS traffic leaks robot actions/tasks | Tang et al. ARES 2025 [A] (97% action ID, Kinova, TLS); Tang et al. IFIP SEC 2025 + CoSe 2026 journal [B] (Sawyer/ROS teleop via IMU, joint-level position/velocity/torque); Shah et al. WiSec'22 poster [A] (teleop workflows 84-97%); Deng et al. CCS'22 [A] (SROS2 side channel noted, task inference via misconfig) | HIGH | ROS 2/DDS-Security (SROS2) *traffic-analysis* over a WAN path is not empirically evaluated (Deng et al. only note it qualitatively); XR-driven (6-DoF pose -> IK -> joint command) teleop not studied; open-world task sets. |
| K2 encrypted XR traffic leaks user activity/input | Muhaimin & Mastorakis 2025 [A] (Quest Pro, 25 apps, 92.4% app / 91% activity); Baldoni et al. IEEE VR 2025 [A] (Quest Link streaming traffic identifies users 76-82% alone); Su et al. USENIX Sec 2024 [B] (keystrokes from avatar motion, content-level) | HIGH (activity), MEDIUM (fine-grained input from metadata only) | Fine-grained input (pose trajectories, gestures) from *encrypted* pose/input flow metadata alone in streaming XR (ALVR/CloudXR/WebRTC) not shown in anything I read; XR used as a robot-teleop front end not studied. |
| K3 combining multiple flows of one session improves inference over single flows | FlowPrint NDSS 2020 [A] (cross-correlation of per-destination flow activity -> app fingerprint); PingPong NDSS 2020 [A] (signatures spanning several TCP connections); Baldoni et al. 2025 [A] (traffic + movement fusion +12-18%); Apthorpe PoPETs 2019 [A] (poses multi-device combination as future work) | MEDIUM | No work found that fuses *heterogeneous, causally coupled* flows (human input -> robot command -> robot feedback -> rendered video) or quantifies the *incremental* information of the cross-flow lag structure over the union of single-flow features. That incremental-gain measurement is the unoccupied part. |
| K4 correlation between flows survives per-flow padding/shaping | DeepCoFFEA S&P 2022 [A] (TPR >50% at 1e-5 FPR under obfs4/WTF-PAD; FRONT only -15% TPR at 1e-3; "Correlations thus appear to remain"); BLANKET USENIX 2021 [A] (needs tens of ms timing noise to hurt DeepCorr); Engelberg & Wool 2021 [B] (IoT fingerprinting despite padding+shaping); NetShaper [A] notes Pacer's unshaped client requests "could potentially reveal information about the server responses" | MEDIUM-HIGH | Existing results concern the *same* flow observed at two points, or request/response of one connection. Whether correlation between *different* flows survives when EACH flow is shaped by a strong regularising defense (constant-rate/Tamaraw/NetShaper per flow) is untested; for truly constant-rate per-flow shaping the residual channel is only start/stop, rate switches and queueing-induced delay, i.e. the leak could be small — this is the most likely refutation route. Zero-delay defenses (FRONT/WTF-PAD) almost certainly leave it (timing of real packets untouched). |
| K5 joint/aggregate shaping (single constant-rate tunnel, mixing) removes cross-flow correlation, with known cost | NetShaper USENIX 2024 [A] (all flows in one DP-shaped QUIC tunnel; T >= 10 ms; code public); Minos ATC 2025 [A] (flow interleaving in P4 tunnel; <20% attack acc. with >=5 flows; 0-12% bw); PingPong [A] (VPN-multiplexed padding -> >1,900 FPs/event vs 0 FPs per-connection); Apthorpe [A] (VPN aggregation "inconsistent", constant-rate ILP ~104 GB/month); Loopix [B] (mixing, seconds latency); Tang ARES 2025 [A] (latency-aware constant-rate, 478x bw); Cizmeci TUM [A] (joint CBR teleop multiplexing, QoS only) | HIGH for "aggregation/constant-rate removes it" in principle; MEDIUM for cost in teleop regime | Minos/Apthorpe show aggregation only helps when the tunnel contains *unrelated or overlapping* traffic; if XR and ROS flows of one session are the only content, the aggregate is itself a joint fingerprint. NetShaper's DP guarantee is per-flow-neighbourhood; accounting for a secret expressed jointly across flows is not analysed. Cost of joint shaping at XR+teleop rates (1 kHz control, 72-120 Hz video) not measured. |
| K6 latency-constrained (real-time) shaping for teleoperation | Tang et al. ARES 2025 [A] "latency-aware traffic modulation" (31% acc. at 478x bandwidth; "not practical"; call for "low-delay defense strategies"); Tang et al. IFIP SEC 2025 [B] (defense across joint-level modalities); Cizmeci et al. TOMM 2017 / thesis [A] (1 ms buckets CBR multiplex, force delay 3.8-10 ms, video ~33 ms, no security); NetShaper [A] (minimum 10 ms interval) | MEDIUM-HIGH | No defense found that is simultaneously (a) latency-bounded at <=1-10 ms, (b) multi-flow/joint across XR and ROS, (c) evaluated against a correlation attacker. Low-delay joint shaping remains explicitly open per Tang et al. |

Direct XR+ROS cross-flow prior art: NONE found (searched robot/ROS traffic analysis, VR traffic analysis, cross-flow/multi-flow correlation; cutoff 2026-09-30). Closest: Tang et al. (robot teleop, single command stream, smartphone IMU instead of XR), Shah et al. (explicitly excluded sensor/imaging flows), Deng et al. (qualitative ROS 2 fan-out timing side channel).

Refutation assessment for the RQ (my judgement, uncertain): the RQ's precondition "each flow individually protected with STRONG defenses" is decisive. If "strong" = regularising constant-rate per flow (BuFLO/Tamaraw-like or NetShaper per flow with fixed T), per-flow timing becomes (nearly) content-independent and the cross-flow correlation channel largely collapses to session-level on/off and rate-change coincidences -> the RQ is likely refutable or reduces to a small residual. If "strong" = SOTA lightweight zero-delay defenses (FRONT, WTF-PAD, RegulaTor-class, BLANKET), DeepCoFFEA-type evidence makes surviving cross-flow correlation very plausible, but then the novelty collides with K4 (MEDIUM-HIGH). The novelty that survives: quantifying the *incremental* leakage of causally-coupled heterogeneous flows under latency-feasible per-flow defenses for teleoperation, and a latency-bounded joint defense.

Public code usable in a lab testbed: NetShaper https://github.com/ubc-systopia/netshaper ; Maybenot (FRONT/RegulaTor/Tamaraw-like machines, DAITA) https://github.com/maybenot-io/maybenot ; FRONT/GLUE + WF attacks https://github.com/websitefingerprinting/WebsiteFingerprinting ; Surakav https://github.com/websitefingerprinting/surakav-imp (+ wfd-gan) ; Palette https://github.com/kxdkxd/Palette ; BLANKET https://github.com/SPIN-UMass/BLANKET ; DeepCoFFEA attack+data https://github.com/traffic-analysis/deepcoffea ; FlowPrint https://github.com/Thijsvanede/FlowPrint ; PingPong https://github.com/uci-plrg/pingpong ; VR user-id analysis https://github.com/signetlabdei/vr_user_id ; Tang Sawyer traces (data only) https://zenodo.org/records/15007304 . No code seen for: Minos, RegulaTor (own repo not found in paper), Tang defenses, Shah et al., Muhaimin & Mastorakis.

Not read / gaps in this study: original BuFLO/CS-BuFLO/Tamaraw papers; TrafficSliver (CCS 2020) original; Tang IFIP SEC 2025 body and CoSe 2026 journal body (paywalled, 403); ESPRESSO / sliding-subset-sum Tor correlation (NDSS 2024) not analysed; cloud-gaming input inference literature not found.
