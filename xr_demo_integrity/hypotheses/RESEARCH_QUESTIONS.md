# Research Questions — status after PHASE 3

| RQ | Question | Answer from PHASE 1–3 evidence | Evidence class |
|---|---|---|---|
| RQ1 | Can a limited-authority component produce learning data whose meaning differs from the actual demonstration? | **No boundary found that allows it.** The only real limited writer on XR paths (the XR input provider, TB1) changes the robot's behaviour and the record together; recorders and processors are in-process; other separations are unauthenticated (full authority) or whole-dataset writers. One ROS 2 candidate (TF granularity) needs a hypothetical SROS2 deployment and is not XR-related. | SOURCE_CONFIRMED (paths), DERIVED_HYPOTHESIS (TB8′) |
| RQ2 | Does such data pass normal and existing validation? | Not applicable for limited writers (no such data). For FULL_WRITE edits the literature already reports evasion of replay, jerk, loss and dynamics checks (SilentDrift 2601.14323) — prior art, not re-tested. Existing tools check only schema, counts and self-consistency of declared timestamps. | SOURCE_CONFIRMED (tools), prior art (papers) |
| RQ3 | Effect on robot behaviour after learning? | NOT_RUN (gate not met). Prior art demonstrates it for dataset-level poisoning. | — |
| RQ4 | Does the same thing occur with non-XR input? | Yes, everything found is input-agnostic: the recorders store post-retargeting commands and robot state; the same code paths serve leader-arm (LeRobot `so101_leader`, Isaac Lab joint teleop), gamepad/spacemouse, and policy-generated commands (tidybot `remote_policy_diffusion.py`). The XR-specific items (tracking validity, clutch, anchor frame) appear only as DATA_QUALITY (D3, D4) and are the same signals already covered by the closed S5 study (validity, freshness, re-arm). | SOURCE_CONFIRMED |
| RQ5 | If existing methods fail, what information or check is missing? | Nothing beyond standard metadata was identified: validity/clutch/pause flags, measured per-stream timestamps, the post-clip sent action, raw input logs (IsaacTeleop MCAP already records raw tracker data), config/version capture, and content hashes/manifests. All are ordinary engineering additions (DATA_QUALITY / IMPLEMENTATION). | DERIVED_HYPOTHESIS (no experiment) |

## Hypotheses carried forward

| ID | Hypothesis | Status |
|---|---|---|
| H1 | XR tracking/retargeting is necessary for a demonstration-integrity violation | **Rejected at source level**: no XR-specific boundary; XR items are data-quality signals already covered by S5 methods |
| H2 | ROS command/state/recorder separation creates a limited writer that can alter recorded meaning | Open only under hypothetical SROS2 + TF (TB8′); upstream deployment is UNAUTH; not pursued (THREAT_MODEL §4) |
| H3 | A poisoned seed demonstration is amplified by Isaac Lab Mimic generation without provenance links | Plausible from code: the source demo is selected in memory (`isaaclab_mimic/datagen/data_generator.py:433-475`), but the generator returns only `initial_state` and `success` (`:999-1002`) and exports recorder fields, although its docstring still lists `src_demo_inds` (`:657-658`) — so no source-demo link reaches the file; it is a data-provider attack amplified by design, not a boundary violation; **NOT_VERIFIED** — Isaac Sim cannot run on this host (INCONCLUSIVE_RESOURCE_LIMITATION for this sub-item) |
