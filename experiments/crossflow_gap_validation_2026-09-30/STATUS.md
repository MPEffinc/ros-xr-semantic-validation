# Status

| Stage | Status | Commit | Main result | Next |
|---|---|---|---|---|
| 0 Asset inventory | DONE | `c3a6b5568c362382762f27c4e3586383efcf052d` | no pcaps/classifiers in repo; real Quest data is app-level only; XR (Wi-Fi) and ROS (dedicated Ethernet) on separate links in lab; CloudXR not runnable (GPU) | Stage 1 |
| 1 Topology / observer | DONE | `1e74ff10cdfabec6f9ae9fe2d34dde573bad9996` | GATE 1 CONDITIONAL PASS: single observer sees XR+ROS only when robot shares switch/AP/Wi-Fi with headset; fails in lab testbed (separate links) | Stage 2 |
| 2 Dataset pipeline | DONE (no dataset) | (this commit) | pipeline built + validated on real DDS (PIPELINE_TEST); real task-labelled XR+ROS capture impossible here (CloudXR GPU, no headset/operator); no public paired dataset | Stage 3–4 NOT_RUN; Stage 5 |
