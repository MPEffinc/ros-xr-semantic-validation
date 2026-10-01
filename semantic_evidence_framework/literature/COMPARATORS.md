# Comparison systems: what each one provides (initial ledger, 2026-10-01)

Labels:

- **AUTHOR_CLAIM**: what the source states.
- **PRIOR_INTERNAL**: our own S4/S5 measurement of a pinned version.
- **NOT_VERIFIED**: not checked here.

No row below claims that a system "fails". A blank capability only means the system does not claim it.

| System | What it is (source) | Evidence it can consume | Where it enforces | Label / notes |
|---|---|---|---|---|
| ROSMonitoring | RML/oracle-based runtime monitors placed on ROS topics. Instrumented nodes can filter messages. Ferrando et al., RV 2020; https://github.com/autonomy-and-verification-uol/ROSMonitoring | any field present on a monitored topic | an in-path monitor node (filter) or offline log | AUTHOR_CLAIM. PRIOR_INTERNAL (S5, image `s4b-rosmonitoring-*:20260922`, *that* version and configuration only): an oracle fault left the monitor fail-open, and generated `MultiThreadedExecutor` stalls appeared on Jazzy. **Not generalised.** |
| ROSMonitoring 2.0 | adds service monitoring and ordered-topic propagation through buffering. Ghaffari Saadat, Ferrando, Dennis, Fisher, FMAS 2024; https://arxiv.org/abs/2411.14367 | as above, plus order across topics | as above. On ROS 2 only service monitoring is available, not reordering (AUTHOR_CLAIM). | AUTHOR_CLAIM; not evaluated here |
| RCL / Vanda | ROS Contract Language: FOL assume–guarantee contracts per node. Vanda synthesises RML monitors and ROSMonitoring configs. https://arxiv.org/abs/2208.05507 ; https://github.com/autonomy-and-verification/ros-contract-language | contract variables bound to topic fields | through ROSMonitoring | AUTHOR_CLAIM |
| FRET / Ogma / Copilot | structured natural-language requirements (FRET) → Copilot stream monitors → hard real-time C99; Ogma generates ROS 2 monitor packages. Perez et al., FMAS 2022, https://arxiv.org/abs/2209.14030 ; https://github.com/nasa/ogma ; https://github.com/Copilot-Language/copilot | streams mapped from topics | a ROS 2 monitor node that reports violations (handling is user-defined) | AUTHOR_CLAIM |
| RTron | risk analysis of ROS function interactions over 3,100 packages; enforces policies through coordination nodes. Xu, Zhang, Bao, arXiv 2103.12365 (2021) | interactions among robot-app functions | coordination nodes | AUTHOR_CLAIM. Its target is interactions between apps, not XR evidence. |
| FlowTags | middleboxes export tags carrying causal context so that downstream SDN policies stay enforceable after packet modification. Fayazbakhsh et al., NSDI 2014; https://www.usenix.org/conference/nsdi14/technical-sessions/presentation/fayazbakhsh | tags that upstream modifiers attach | switches and downstream middleboxes | AUTHOR_CLAIM. This is the closest *structural* analogue to "the middleware drops causal evidence; restore it through tags". It is prior art for the tagging idea itself. |
| SROS2 | DDS-Security for ROS 2: authentication, encryption and access control per topic | identity and permissions | DDS participant | Protection goal is the communication boundary. Tracking validity is out of its scope, not a gap. |
| tf2 | time-indexed transform buffer. `lookupTransform(target, source, time)` returns the transform at a stamp, or raises on extrapolation. | frame graph plus stamps | the consumer that calls it | Interval-correct lookup is available. Whether a consumer uses `Time(0)` (latest) is an implementation choice. SOURCE_CONFIRMED: Servo 2.12.4 uses `Time(0)` for command frames (`servo.cpp` L565). |
| Timeout / watchdog | e.g. Servo `incoming_command_timeout`; S5 common 250 ms heartbeat | receive or stamp time | consumer | SOURCE_CONFIRMED (Servo 2.12.4 / 2.5.9); PRIOR_INTERNAL (S5) |
| MoveIt Servo built-ins | collision and singularity scaling, joint limits, `~/pause_servo`, halt on stale command | robot state, command stamp | final consumer | SOURCE_CONFIRMED (2.12.4) |
| RTA (Simplex; SOTER on ROS) | switch to a certified fallback near envelope violation. Shivakumar et al., https://arxiv.org/abs/2008.09707 | plant state | arbitration node | AUTHOR_CLAIM. It targets plant-safety envelopes, not input-evidence validity. |
| XRobotAssist | embedded XR↔industrial-robot middleware: MQTT + ØMQ, Redis cache, ROS 2 robot side, ArUco spatial sync, HRI safeguards. Szilágyi, Hajdu, Széll, Galambos, JMMP 10(2):46, 2026; doi:10.3390/jmmp10020046 | robot data and XR streams; marker-based alignment | edge middleware | AUTHOR_CLAIM, from the abstract only. The full text was not retrieved (MDPI returned 403). Whether it handles tracking validity, focus or re-anchor epochs is NOT_VERIFIED. |

## How these bound the contribution

The following are all prior art:

- tagging or forwarding causal context (FlowTags);
- contract-to-monitor generation (RCL/Vanda, FRET/Ogma/Copilot);
- in-path monitors (ROSMonitoring);
- coordination or enforcement nodes (RTron);
- fallback arbitration (RTA).

A result of this study can only be one of two things:

- an evidence-model finding: *which* XR evidence must be carried, linked to *which* transition, and
  enforced *where*, measured across implementations;
- a measured improvement in modification count, latency or false blocks over per-implementation
  retrofits.
