# Key Papers and Primary Sources

Access date for all sources: 2026-09-29. Verification levels:
`FULL TEXT VERIFIED` (entire cited version read) · `FULL TEXT (PREPRINT)` (preprint read, version of
record not) · `ABSTRACT+METADATA` · `SOURCE_CONFIRMED` (design doc / code read at a pinned revision) ·
`NOT_VERIFIED`. Quotes marked ✔ were re-checked by the lead author of this file directly in the PDF
(`pdftotext`); other quotes come from the literature pass and carry their stated level. URLs, versions
and locations: `SOURCE_LEDGER.md`.

Distinguish throughout: **AUTHOR_CLAIM** (what a paper says) vs. **SOURCE_CONFIRMED** (what code does)
vs. **HYPOTHESIS** (ours).

---

## P1. HORUS (arXiv:2506.02622) — FULL TEXT VERIFIED (v1, v2)

- *HORUS: A Mixed Reality Interface for Managing Teams of Mobile Robots.* O. S. Adekoya, A. Sgorbissa,
  C. T. Recchiuto (Univ. Genoa). v1 2025-06-03 ("submitted to IROS 2025"), v2 2026-06-05 ("submitted to
  UR 2026"); text of v1/v2 identical apart from the stamp. No published venue/DOI found.
- Not the same paper as the one cited in `horus_ros2/README.md` ("HORUS: Architecture and Performance
  Characterization…", accepted I-RIM 3D 2026, Springer SPAR) — that paper's full text is NOT_VERIFIED.
- Problem: one operator supervising/tasking/teleoperating a team of mobile robots from a Quest 3 MR
  "Ground Station" mini-map.
- Implementation described: **ROS 1** (multimaster_fkie, one master per robot), Unity TCP Connector →
  a "HORUS Bridge node" extending Unity TCP Endpoint; Tailscale VPN for remote links.
- Security/threat model: none. Only network text: Tailscale "makes it straightforward to establish
  secure links" (Sec. III-A, p.3). No leases, ownership, heartbeat, disconnect or in-flight goal handling.
- Actual contribution: MR multi-robot supervision UI + 20-participant user study.
- Publication-time vs. current code: paper = ROS 1 stack; `horus_ros2` (ROS 2) first commit 2025-12-15,
  i.e. after v1.

## P2. Multi-operator HORUS (arXiv:2606.07013) — FULL TEXT VERIFIED (v1)

- *A Multi-Operator Mixed-Reality Interface for Multi-Robot Control and Coordination: Co-Located and
  Private Workspace Collaboration.* Same authors. v1 2026-06-05, "Submitted to RO-MAN 2026" (the
  `horus` README states "accepted to IEEE RO-MAN 2026"; acceptance not independently verified).
- Problem: multiple cooperative operators; co-located shared vs. private MR workspaces; prevent
  conflicting commands on the same robot.
- Lease mechanism, Sec. III-E "Conflict-Safe Parallelism Through Per-Robot Leases", PDF p.4 ✔:
  > "HORUS addresses this through per-robot control leases. Leases are enforced at the robot level
  > rather than at the whole-workspace level …"
  > "If a holder is no longer active, HORUS treats the lease as stale and permits reacquisition."
  > "The policy is simple: all participants have equal priority; the first active claimant holds the
  > robot; and inactive holders can be displaced through reacquisition. Before starting teleoperation
  > or tasking, the runtime checks whether the current operator is allowed to act. If another operator
  > actively holds the lease, the action is blocked; if the lease is stale, HORUS reacquires the robot
  > before proceeding."
- AUTHOR_CLAIM (Sec. V-A, p.5): "the lease arbitration mechanism remained robust in both modes,
  effectively preventing simultaneous, conflicting interactions with the same robot." Evaluated with
  36 benign participants, 3 simulated Nova Carter robots (Isaac Sim, ROS 2 Jazzy, Wi-Fi 7 LAN); no
  fault-injection or adversarial test.
- Not stated in the paper: enforcement location, TTL values, disconnect behavior, fate of goals/teleop
  already sent when a lease ends or moves, e-stop behavior, authentication.
- Security/threat model: none; operators are cooperative peers.
- Code at submission vs. now: lease logic in `horus_ros2` unchanged except formatting between
  `f7c8e12` (2026-03-12, last commit before submission) and `eca75cbf` (HEAD) — literature-pass
  `git diff -w` finding; the lead audit confirmed the lease file history (`d012fe1` 2026-02-26 add,
  `d0bb1e4` 2026-03-01, `933f68b` 2026-03-04 inactive preemption, `aa2dfa3` 2026-06-29 formatting).

## P3. ROS 2 Security Enclaves (+ DDS-Security, Access Control Policies) — SOURCE_CONFIRMED

- `ros2/design` @ `93a415bf`; articles 180/181/182 last touched by `12f61b14` (2021-10-01).
  Authors: R. White, M. Arguedas (182); R. White, K. Fazzari (181); K. Fazzari (180).
- Principal authenticated = DDS DomainParticipant ↔ ROS context/enclave, not node, not human:
  182 L62-63 "a ``Participant`` can only utilise a single security identity"; 182 L257-258 "all nodes
  in a context share the same security identity and access control credentials"; 180 L40
  "Authentication: Verify the identity of a given domain participant."
- Revocation / runtime permission change: not described (grep `revoc|crl|expir` = 0 hits in 180–182);
  181 L326-327 "staticky provisioned permissions". Default mode permissive (180 L186-187).
- Implication (HYPOTHESIS, used in `EXISTING_DEFENSES.md`): SROS2 can authenticate/authorize the
  HORUS bridge process; it cannot distinguish operators multiplexed through that one participant.

## P4. ROS 2 Actions design — SOURCE_CONFIRMED (+ rcl/rclcpp Jazzy code)

- `articles/actions.md` (Biggs, Perron, Loretz; last touched `2c1ff50a`).
- Client generates goal UUID (L98-100); server decides how to handle multiple clients (L64); cancel
  transitions only if the server accepts (L205-206; codes `OK`/`REJECTED`/`INVALID_GOAL_ID` L247);
  cancel carries only goal ID + timestamp (L243) — no goal ownership; client disconnect not discussed.
- rcl @ `22c0b957`, rclcpp @ `2209942e` (jazzy): goal handle stores no requester identity
  (`goal_handle.c` L25-33); cancel selection by UUID/timestamp only (`action_server.c` L791–);
  `~Client()` invalidates locally, sends no cancel (`client.hpp` L658-669, re-checked). ⇒ no automatic
  cancel on client death; any client may cancel any goal it can name.

## P5. Xia, Gao, Shi — Multi-tenant ROS 2 security (ICRA 2025) — FULL TEXT VERIFIED (author PDF)

- *Investigating Security Threats in Multi-Tenant ROS 2 Systems*, ICRA 2025 pp. 16441-16448,
  DOI 10.1109/ICRA55743.2025.11127490.
- Threat model: attacker is one tenant controlling ≥1 node (Sec. III-B). Attack/measurement paper:
  context-privilege escape, weakly bound enclaves (`ROS_SECURITY_ENCLAVE_OVERRIDE`), topic-name
  collision with no per-message origin authentication, inter-topic hijacking, ROS1-bridge escalation.
- Relevant AUTHOR_CLAIM on revocation (Sec. IV-A-2, author-PDF p.3): enclave expiry "is set when the
  enclave is created, and there is no way to update it after distribution" and updating SROS 2 files
  "requires restarting nodes".
- No actions, no human-operator identity, no in-flight revocation. No public artifact found.

## P6. ROSec (IEEE T-ASE 22, 2025) — ABSTRACT+METADATA only

- *ROSec: Intra-Process Isolation for ROS Composition With Memory Protection Keys*, J. Seo, M. Kayondo,
  J. Kang, K. Lee, D. Kwon, Y. Paek; vol. 22, pp. 10546-10559; DOI 10.1109/TASE.2024.3525050.
- MPK-based memory isolation between composed nodes (6.4% overhead, per abstract). Not access control;
  not relevant to authority transfer beyond "composition shares a security identity". Limitations
  NOT_VERIFIED (closed access).

## P7. Salimi et al. — Conflict resolution + ABAC for multi-robot (JSA 168, 2025) — FULL TEXT (PREPRINT)

- *A customizable conflict resolution and attribute-based access control framework for multi-robot
  systems*, S. Salimi, F. Keramat, J. Peña Queralta, T. Westerlund; J. Systems Architecture 168,
  art. 103528 (Nov 2025); DOI 10.1016/j.sysarc.2025.103528. VoR not accessible (403); arXiv
  2308.16482v1 read (VoR has 40 vs. 38 references ⇒ revised).
- Hyperledger Fabric chaincode `acquire/release/authorize`; "exclusive" mode = voluntary lock on a
  topic (`/cmd_vel`); every message is a Fabric transaction (~300 ms). States access "can be revoked at
  any time" (Sec. III-1, p.4) but presents no revocation mechanism or in-flight handling; topics only,
  no actions. No confirmed public artifact.

## P8. MoveIt Servo — SOURCE_CONFIRMED (`moveit/moveit2` @ `a2117df2`)

- `incoming_command_timeout` default 0.1 s (`servo_parameters.yaml` L102-107, re-checked); staleness
  from sender `header.stamp`; on timeout `smoothHalt` then stop publishing (`servo_node.cpp`
  L241-331, L418-447; `servo.cpp` L664-689).
- No sender identity; last message wins (`servo_node.cpp` L211-227); `~/pause_servo`,
  `~/switch_command_type` unauthenticated beyond DDS.
- Collision/singularity halts (`collision_monitor.cpp` L138-166; `common.cpp` L370-374).

## P9. HORUS ROS 2 implementation — SOURCE_CONFIRMED (`RICE-unige/horus_ros2` @ `eca75cbf`)

See `../audit/HORUS_CODE_AUDIT.md`. Summary: bridge-side lease is fail-open (no lease ⇒ allow),
catalog authority self-asserted, no client authentication, lease end neither cancels nor stops,
single-handle Nav2 adapter.

## Supporting sources used for sufficiency analysis (not key papers)

| Source | Level | Use |
|---|---|---|
| Nav2 jazzy @ `645abd95` `simple_action_server.hpp` | SOURCE_CONFIRMED (re-checked L363-383) | new goal preempts; old goal **ABORTED**; any client's cancel accepted |
| ros2_controllers master `2520ae5b` / jazzy `1bc19b63` | SOURCE_CONFIRMED | diff_drive `cmd_vel_timeout` 0.5 s brake; JTC `cmd_timeout` 0.0 (off); forward_command_controller no timeout |
| Zong, Guo, Chen, PBAC for robotic apps, SOSE 2019, DOI 10.1109/SOSE.2019.00062 | FULL TEXT VERIFIED | ROS 1 runtime token revocation: "prevent further accesses to the requested services immediately" (p.372) — future requests only |
| Mayoral-Vilches, White, Caiazza, Arguedas, SROS2, IROS 2022, DOI 10.1109/IROS47612.2022.9982129 | ABSTRACT+METADATA | SROS2 tooling |
| Toris, Shue, Chernova, rosauth, TePRA 2014, DOI 10.1109/TePRA.2014.6869141 | ABSTRACT+METADATA | connection-time auth for non-native (bridge) clients |
| Dieber et al., IROS 2016, DOI 10.1109/IROS.2016.7759659 | ABSTRACT+METADATA | per-topic application-level authorization (ROS 1) |
| Deng et al., CCS 2022, DOI 10.1145/3548606.3560681 | ABSTRACT+METADATA | SROS2 flaws incl. (per Xia et al.) expired-enclave reuse |
| Desai et al., SOTER, DSN 2019, DOI 10.1109/DSN.2019.00027 | ABSTRACT+METADATA | runtime assurance switches *controllers*, not operators |
| Yao, Zhao, Cheng, Chen, TAT, USENIX Security 2026 | FULL TEXT VERIFIED (lit pass) | trajectory attestation of one arm vs. intended task |
| Zhang & Zhang, arXiv:2607.23586 (2026) | ABSTRACT only | "authorization continuity" for self-evolving LLM agents — name collision |
| Gallo, arXiv:2607.08906 (2026) | ABSTRACT only | Proof-of-Continuity: causal, non-expansive authority propagation — concept collision |
| sros2 `SROS2_Linux.md` @ `e92087a` (2026-09-25) | read | CRL documented, linked before node start; runtime reload not described |
