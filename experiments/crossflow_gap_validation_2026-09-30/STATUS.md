# Status

| Stage | Status | Commit | Main result | Next |
|---|---|---|---|---|
| 0 Asset inventory | DONE | `c3a6b5568c362382762f27c4e3586383efcf052d` | no pcaps/classifiers in repo; real Quest data is app-level only; XR (Wi-Fi) and ROS (dedicated Ethernet) on separate links in lab; CloudXR not runnable (GPU) | Stage 1 |
| 1 Topology / observer | DONE | `1e74ff10cdfabec6f9ae9fe2d34dde573bad9996` | GATE 1 CONDITIONAL PASS: single observer sees XR+ROS only when robot shares switch/AP/Wi-Fi with headset; fails in lab testbed (separate links) | Stage 2 |
| 2 Dataset pipeline | DONE (no dataset) | `f4d9de6333e15058da00cd3bcce72b3736134ca0` | pipeline built + validated on real DDS (PIPELINE_TEST); real task-labelled XR+ROS capture impossible here (CloudXR GPU, no headset/operator); no public paired dataset | Stage 3–4 NOT_RUN; Stage 5 |
| 3 Unprotected leakage | NOT_RUN | `3551865e3f75edb696a2459937d2fb024c6c702d` | no real paired data; GATE 2 undecided | Stage 4 |
| 4 Cross-flow ablation | NOT_RUN | `c039a0cca3ec14d19f29e8a87eb0fc584759f843` | depends on Stage 3 data | Stage 5 |
| 5 Existing defenses | DONE (analysis + 1 real-stack probe) | (this commit) | regularising per-flow constant-rate makes the joint trace task-independent by construction; ROS teleop flows measured already constant-size/60 Hz (≈8 % padding cost); media cost is a known bandwidth trade-off; joint shapers exist (NetShaper, Minos) | Stage 6 |
