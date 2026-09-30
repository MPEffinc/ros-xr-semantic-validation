# Status

| Stage | Status | Commit | Main result | Next |
|---|---|---|---|---|
| 0 Asset inventory | DONE | `c3a6b5568c362382762f27c4e3586383efcf052d` | no pcaps/classifiers in repo; real Quest data is app-level only; XR (Wi-Fi) and ROS (dedicated Ethernet) on separate links in lab; CloudXR not runnable (GPU) | Stage 1 |
| 1 Topology / observer | DONE | `1e74ff10cdfabec6f9ae9fe2d34dde573bad9996` | GATE 1 CONDITIONAL PASS: single observer sees XR+ROS only when robot shares switch/AP/Wi-Fi with headset; fails in lab testbed (separate links) | Stage 2 |
| 2 Dataset pipeline | DONE (no dataset) | `f4d9de6333e15058da00cd3bcce72b3736134ca0` | pipeline built + validated on real DDS (PIPELINE_TEST); real task-labelled XR+ROS capture impossible here (CloudXR GPU, no headset/operator); no public paired dataset | Stage 3–4 NOT_RUN; Stage 5 |
| 3 Unprotected leakage | NOT_RUN | `3551865e3f75edb696a2459937d2fb024c6c702d` | no real paired data; GATE 2 undecided | Stage 4 |
| 4 Cross-flow ablation | NOT_RUN | `c039a0cca3ec14d19f29e8a87eb0fc584759f843` | depends on Stage 3 data | Stage 5 |
| 5 Existing defenses | DONE (analysis + 1 real-stack probe) | `dc2bd93a9341d340ade7d06e4dc40484026b0c1a` | regularising per-flow constant-rate makes the joint trace task-independent by construction; ROS teleop flows measured already constant-size/60 Hz (≈8 % padding cost); media cost is a known bandwidth trade-off; joint shapers exist (NetShaper, Minos) | Stage 6 |
| 6 Residual leakage | NOT_RUN (no data); analytic table | `f10ed1c260f3f7b3312643361374eb523bebd75b` | keep-pattern impossible under regularising defenses; weaker regimes reproduce prior art K4 | Stage 7 |
| 7 Decision | **KILL** | `8174b579054488cbbda96361cb8ac8ea28cb72ed` | regularising per-flow defenses remove cross-flow channel by construction; joint shapers exist; XR/ROS not essential; remainder is excluded latency-aware padding tuning | new gap search (docs/08) |
| 8 New gap search | DONE | (this commit) | 7 candidates; N1 view-to-execution consistency = NEEDS PILOT; N2/N3/N5/N7 WEAK; N4/N6 KILL | N1 kill-first sim pilot (awaiting decision) |
