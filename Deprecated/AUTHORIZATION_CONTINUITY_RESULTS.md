# End-to-End Authorization Continuity Feasibility and Novelty Report

## A. Executive Summary

이번 작업은 XR에서 발생한 권한 부여가 Bridge → ROS → Planner/Action Server → Robot Execution까지 갈 때 다음 세 속성을 유지하는지 공개 framework의 고정 source와 격리 runtime으로 검증했다.

1. **Identity** — 누가 허용했는가.
2. **Lifetime / Revocation** — 그 권한은 언제까지 유효하며, 회수 시 이미 시작된 action도 영향을 받는가.
3. **Exact Action Binding** — 사용자가 승인한 robot/goal/trajectory와 실제 전달·실행되는 대상이 같은가.

가장 중요한 결과는 다음과 같다.

- **HORUS 정상 baseline은 동작했다.** A가 lease를 가진 동안 A command는 ALLOW, B command는 BLOCK이었고, A release 뒤 B가 acquire하여 ALLOW됐다. 이는 lease arbitration 자체가 정상임을 확인한 기준선이다. **CONFIRMED BY RUNTIME**.
- **HORUS lease 회수는 이미 수락된 Nav2 goal로 전파되지 않았다.** explicit release, TTL expiry, client disconnect 세 경우에 각각 시작된 goal이 제한된 관찰창 동안 계속 active였고 dummy action server가 받은 cancel request는 0이었다. **CONFIRMED BY RUNTIME + SOURCE CODE**.
- **HORUS의 `app_id`, `role`, `session_id`는 인증된 principal이 아니었다.** 임의 문자열이 수용됐고 실제 lease ownership은 bridge가 부여한 HorusLink logical connection에 묶였다. 보호 catalog도 client가 주장한 `host` role로 clear할 수 있었다. **CONFIRMED BY RUNTIME + SOURCE CODE**.
- **COMPAS XR의 approval과 execution handoff 사이에는 exact trajectory proof가 없다.** 서로 다른 T_A/T_B가 같은 element-derived `trajectory_id`를 가졌고, `SendTrajectory`에는 승인 digest/version/approver/epoch가 없었다. T_A 승인 뒤 T_B가 official message/transport subscriber까지 도달했으며 자동 content 비교나 reject는 없었다. **CONFIRMED BY RUNTIME + SOURCE CODE**.
- **그러나 COMPAS XR의 실제 robot execution은 확인하지 않았다.** 공개 fixed revision에는 official MQTT handoff 이후의 완성된 ROS/MoveIt/RTDE executor가 없고 이 단계가 사용자 integration에 맡겨져 있다. 따라서 결과는 “framework-level binding guarantee가 없는 integration hazard”이지 물리 로봇 취약점 증명이 아니다.
- **두 framework를 하나의 확정된 공격으로 일반화할 수는 없지만 공통 연구 invariant는 남는다.** 외부 권한은 authenticated origin, live revocation epoch, canonical exact action에 묶여 최종 집행점까지 도달해야 한다. 현재는 HORUS 한 곳에서 actual action-lifetime consequence가 강하게 확인됐고, COMPAS는 handoff 단계까지만 확인됐다.

최종 판정은 **CONDITIONAL GO**다.

추천 Main Item은 일반적인 “Authorization Continuity”가 아니라 다음처럼 범위를 좁힌다.

> **Revocable Exact-Action Authorization for Shared XR–ROS Bridges**  
> 부제 후보: **Origin-Bound Robot Action Authorization across XR–ROS Trust Boundaries**

일반적인 “Authorization Continuity” 및 causal authority lineage 개념은 2026년 공개 preprint들과 직접적인 명칭·개념 충돌이 있으므로 first claim을 하면 안 된다.

## B. 기존 연구와 이번 작업의 연결

기존 Quest2ROS2/SROS2 단계에서는 다음을 실제로 확인했다.

- SROS2 Enforce에서 low-privilege ROS node의 direct publish는 BLOCK됐다.
- 같은 logical command를 trusted bridge가 publish하면 bridge enclave 권한으로 ALLOW됐다.
- 두 external client는 ROS graph에서 개별 principal로 나타나지 않고 bridge-side publisher 하나와 같은 endpoint GID로 축약됐다.
- Quest2ROS2 ROS–TCP endpoint의 publisher는 client disconnect 뒤에도 남았고, reconnect client가 재등록 없이 재사용할 수 있었다.
- 하지만 Quest2ROS2에는 authenticated Viewer/Operator role 자체가 없었으므로 “낮은 권한 사용자가 높은 권한 bridge를 세탁했다”는 강한 claim은 성립하지 않았다.

이번 작업은 그 약한 identity-collapse 사례를 두 방향으로 확장했다.

- **HORUS는 lifetime 방향의 강한 사례**다. 실제 multi-operator lease가 존재하고 정상 경쟁 차단도 동작했지만, lease 종료와 이미 수락된 action goal의 lifecycle은 연결되지 않았다.
- **COMPAS XR은 exact-action 방향의 조건부 사례**다. multi-user preview/approval workflow가 있지만 승인 증거와 exact trajectory가 execution handoff에 cryptographically 또는 semantically 묶이지 않았다. 다만 실제 executor는 custom integration 영역이다.

따라서 기존 결과와 새 결과는 다음처럼 연결된다.

```text
Quest2ROS2: 누가 보냈는가가 bridge ROS principal로 축약됨
HORUS:      권한이 끝난 시점과 이미 수락된 action의 수명이 분리됨
COMPAS XR:  승인한 trajectory와 execution handoff trajectory의 정확한 동일성이 보장되지 않음
```

이 세 가지는 Identity, Lifetime, Exact Action Binding이라는 분석 축을 구성하지만, 아직 “모든 XR–ROS framework에 존재하는 하나의 취약점”을 입증하지는 않는다.

## C. Environment / Revisions

### C.1 Host and isolation

- Host: Ubuntu 24.04, x86_64, Python 3.12, Git 2.43.
- Docker: client/server 29.1.3.
- Test image: `ros-xr-horus-jazzy:local`.
- Final image ID: `sha256:77e3a03de6660509f56a5b029916840c5e39399504be48f8c30035bdd960afed`.
- HORUS container: ROS 2 Jazzy, `ROS_DOMAIN_ID=91`, localhost-only DDS discovery.
- COMPAS dependency lock: `compas==2.15.0`, `compas_eve==2.1.1`, `compas_timber==0.7.0`, `paho-mqtt==2.1.0`.
- Both runtime containers used `--network none`; bridge and MQTT listeners bound to `127.0.0.1` only.
- No host port, public MQTT broker, host network, privileged mode, Quest, or physical robot was used.
- Existing Humble/SROS2 environment and results were preserved. HORUS/COMPAS tests did not enable SROS2 and therefore do not independently prove an SROS2-mediated result.

The Docker base tag and apt indexes are externally floating; the final image ID above is the exact runtime anchor for this run. Rebuilding later re-resolves those packages, while the framework commits and COMPAS Python dependencies are pinned by the runner/Dockerfile.

### C.2 Fixed framework revisions

| Framework | Repository | Branch | Exact commit | Commit date | Version note |
|---|---|---|---|---|---|
| HORUS ROS 2 | [RICE-unige/horus_ros2](https://github.com/RICE-unige/horus_ros2) | `main` | `eca75cbf559f09ff793d8993338b2f1ffed1adfd` | 2026-07-26 17:58:10 +0200 | package 0.1.0 |
| HORUS app artifacts/docs | [RICE-unige/horus](https://github.com/RICE-unige/horus) | `main` | `819cdfdc74f1a0c2bd73946dc14897a533f68b61` | 2026-08-07 12:51:12 +0200 | public APK/docs tree |
| HORUS SDK | [RICE-unige/horus_sdk](https://github.com/RICE-unige/horus_sdk) | `main` | `f4f00dab41910676519d545515531ec243414044` | 2026-07-26 17:58:04 +0200 | protocol/docs support |
| COMPAS XR | [compas-dev/compas_xr](https://github.com/compas-dev/compas_xr) | `main` | `b86e6fbbacdc8e84183fc08c846176a1c79304ca` | 2026-03-27 11:45:46 -0400 | package reports 1.0.0; `v1.0.0-82-gb86e6fb` |
| COMPAS XR Unity Assembly | [compas-dev/compas_xr_unity_assembly](https://github.com/compas-dev/compas_xr_unity_assembly) | `main` | `f1516ca568b101447507aebc28a594bdc358df3e` | 2024-11-01 15:54:11 +0100 | README says Unity 2023.3.10f1; ProjectSettings says 2023.2.10f1 |

### C.3 Test configurations

HORUS:

- The unmodified fixed HORUS ROS 2 tree was copied read-only into a temporary colcon workspace and all four packages built on Jazzy.
- Real `horus_unity_bridge_node` and `horus_backend_node`/Nav2 adapter were run.
- A local HorusLink-compatible two-lane client emulator supplied A/B traffic because a matching current public Unity source client was unavailable.
- A dummy ROS `NavigateToPose` action server accepted long-running goals and counted cancellation requests; it did not control hardware.
- Lease TTL was shortened to 1200 ms only to make expiry reproducible.

COMPAS XR:

- The fixed official Python message classes and official `compas_eve` MQTT transport were loaded from the checked-out source.
- A local Mosquitto broker listened on `127.0.0.1:1883`, `persistence=false`, with anonymous access intentionally enabled inside a `--network none` container.
- The receiving side was an inert audit subscriber using the official message/transport path. No robot executor was connected.
- Duplicate-vote assertions used official MQTT messages plus a source-faithful model of the inspected Unity state increments; this was not a Unity binary runtime.

## D. HORUS Results

### D.1 HORUS-A1 — Normal lease baseline

- **Purpose:** establish that lease arbitration works before interpreting adversarial/lifecycle cases.
- **Expected:** A acquires Robot1 lease and publishes; B is denied while A owns it; A release permits B acquire and publish.
- **Observed:** A `0.11` ALLOW, B `0.22` BLOCK during A lease, A release, B acquire, B `0.22` ALLOW. B could also acquire after A disconnect. ROS topic endpoint inspection showed one publisher node `/horus_unity_bridge` with one GID, not A/B ROS nodes.
- **Evidence:** [HORUS runtime log](/home/cclab/ros_xr/evidence/authorization_continuity_horus_runtime.log), `normal_lease`, `bridge_publisher_identity`.
- **Interpretation:** lease arbitration baseline is valid. Client commands collapse to a bridge-side ROS publisher, but lease ownership itself remains separated by HorusLink logical connection.
- **Classification:** **CONFIRMED BY RUNTIME**.

### D.2 HORUS-A2 — Protected command with no active lease

- **Purpose:** determine whether a catalog-protected command requires an active lease.
- **Expected:** outcome intentionally open; compare source and runtime.
- **Observed:** with the topic protected but no lease entry, Client B's `0.31` command reached the dummy robot.
- **Evidence:** runtime field `no_lease_on_protected_topic: ALLOW`; source returns true when no lease exists in [control_lease_manager.cpp](/home/cclab/ros_xr/frameworks/horus_ros2/horus_unity_bridge/src/control_lease_manager.cpp:125).
- **Interpretation:** current lease is an exclusive collision lock, not a mandatory “must possess a lease” authorization check. This may match HORUS's arbitration design intent and is not by itself labeled a vulnerability.
- **Classification:** **CONFIRMED BY RUNTIME + CONFIRMED BY SOURCE CODE**.

### D.3 HORUS-A3 — Identity, role, and session trust

- **Purpose:** identify the actual server-side principal behind `app_id`, `role`, `session_id`, and lease ownership.
- **Expected:** authenticated values should be derived or verified server-side if they are authorization principals.
- **Observed:** the client supplied `self-asserted-app`, `self-asserted-admin`, and `fake-session`; the bridge accepted/reflected them. The observed authorization key was HorusLink connection ownership. A second client still could not use A's lease merely by choosing metadata.
- **Evidence:** runtime `identity_metadata`; parsing and lease storage in [control_lease_manager.cpp](/home/cclab/ros_xr/frameworks/horus_ros2/horus_unity_bridge/src/control_lease_manager.cpp:287); socket lane pairing relies on a client-provided nonzero session token before the bridge assigns its logical connection ID in [horuslink_connection_manager.cpp](/home/cclab/ros_xr/frameworks/horus_ros2/horus_unity_bridge/src/horuslink_connection_manager.cpp:370).
- **Interpretation:** the strings are untrusted metadata in the tested path; the meaningful lease identity is an unauthenticated transport connection. This is stronger than pure ROS principal collapse but still not authenticated Viewer/Operator privilege laundering.
- **Classification:** **CONFIRMED BY RUNTIME + CONFIRMED BY SOURCE CODE**.

### D.4 HORUS-A4 — Protected catalog control-plane

- **Purpose:** determine who can define, clear, or change protected topics.
- **Expected:** an authoritative catalog source should be authenticated or derived from a trusted channel.
- **Observed:** B was BLOCKed by A's active lease. B then sent a catalog message claiming `role=host`, `op=clear`; the catalog was cleared and the same B command `0.44` was ALLOWed.
- **Evidence:** runtime `catalog_control_plane`; handler explicitly discards `client_fd`, accepts JSON role `host`/`single`, and performs clear/update in [control_lease_manager.cpp](/home/cclab/ros_xr/frameworks/horus_ros2/horus_unity_bridge/src/control_lease_manager.cpp:184).
- **Interpretation:** the tested control-plane authority comes from a self-asserted role. This is a concrete local trust gap, but it should not become the Main Item because it is implementation-specific and could be fixed independently.
- **Classification:** **CONFIRMED BY RUNTIME + CONFIRMED BY SOURCE CODE**.

### D.5 HORUS-A5 — Lease revocation versus in-flight Nav2 action

- **Purpose:** test whether ending the authority that started an action also terminates the accepted action.
- **Expected:** determine actual policy; if continuity is enforced, release/expiry/disconnect should cause an action cancel or an equivalent downstream stop.
- **Observed:** three goals were accepted through the real HORUS backend/Nav2 adapter. After explicit release, TTL expiry, and client disconnect, the corresponding goal remained active during 1.0 s, 0.7 s, and 1.0 s observation windows. The action server observed zero cancel requests and all three goals remained active at observation end. B could acquire after disconnect, showing lease cleanup itself completed.
- **Evidence:** runtime `ongoing_action_lifecycle`; the adapter sends goals in [nav2_action_adapter.cpp](/home/cclab/ros_xr/frameworks/horus_ros2/horus_backend/src/nav2_action_adapter.cpp:64), while only an explicit cancel topic invokes asynchronous cancellation around [nav2_action_adapter.cpp](/home/cclab/ros_xr/frameworks/horus_ros2/horus_backend/src/nav2_action_adapter.cpp:153). Disconnect cleanup releases lease/resources but has no goal cancellation lineage in [message_router.cpp](/home/cclab/ros_xr/frameworks/horus_ros2/horus_unity_bridge/src/message_router.cpp:578).
- **Interpretation:** in this runtime, lease lifetime governs admission of future commands but is not propagated to already accepted goal lifetime. The observation proves “no cancel was requested within the measured windows,” not that a real robot can never stop through another safety layer.
- **Classification:** **CONFIRMED BY RUNTIME + CONFIRMED BY SOURCE CODE**.

### D.6 HORUS-A6 — OpenXR focus lifecycle

- **Purpose:** trace whether OpenXR focus/session loss stops heartbeat/teleop, releases lease, and cancels an action.
- **Expected:** inspect current Unity source, then run hardware only if available and justified.
- **Observed:** the public `horus` revision contains app artifacts/documentation rather than the matching current multi-operator Unity implementation. No reliable current OpenXR focus callback → lease/heartbeat → action cancellation path was found. Focus is not a field in the tested HorusLink authorization path; available state is self-reported application metadata.
- **Evidence:** [fixed HORUS app tree](/home/cclab/ros_xr/frameworks/horus); bridge configuration marks authentication/encryption false and future work in [bridge_config.yaml](/home/cclab/ros_xr/frameworks/horus_ros2/horus_unity_bridge/config/bridge_config.yaml:28).
- **Interpretation:** actual Quest focus-loss consequence remains a hardware/current-app-source experiment. No claim about focus loss is established here.
- **Classification:** **UNCONFIRMED HYPOTHESIS**.

### D.7 Additional source boundary

- The HorusLink topic publish route performs the lease check immediately before the shared bridge publishes to ROS in [message_router.cpp](/home/cclab/ros_xr/frameworks/horus_ros2/horus_unity_bridge/src/message_router.cpp:391).
- The service-request route does not call the same lease check in [message_router.cpp](/home/cclab/ros_xr/frameworks/horus_ros2/horus_unity_bridge/src/message_router.cpp:451). This is **CONFIRMED BY SOURCE CODE**, but was not exercised at runtime and is not treated as a confirmed bypass.
- No SROS2 policy is part of the inspected HORUS repositories/configuration. Shared ROS publisher identity is structurally and graphically observed, but an SROS2-combined HORUS run remains future work.

## E. COMPAS XR Results

### E.1 COMPAS-B1 — Exact trajectory schema and ID semantics

- **Purpose:** determine whether approval and send messages name an immutable exact trajectory.
- **Expected:** a content/version identifier or comparison should distinguish T_A from T_B.
- **Observed:** T_A digest was `1563aeda...d73e`; T_B digest was `9dcd92a7...933d`. Both used `trajectory_id_assembly-step-7` because the ID is constructed only from `element_id`. `SendTrajectory` fields were header, element, robot, trajectory ID, and trajectory; no approval proof, digest, version, approver set, request binding, or epoch was present.
- **Evidence:** runtime `schema_binding`; schemas in [messages.py](/home/cclab/ros_xr/frameworks/compas_xr/src/compas_xr/mqtt/messages.py:314) and [messages.py](/home/cclab/ros_xr/frameworks/compas_xr/src/compas_xr/mqtt/messages.py:459); C# equivalent in [MQTTDataCompasXR.cs](/home/cclab/ros_xr/frameworks/compas_xr_unity_assembly/Assets/Scripts/MQTTDataCompasXR.cs:586).
- **Interpretation:** `trajectory_id` identifies an assembly step, not exact trajectory content/version. The wire schema does not carry verifiable approval-to-send binding.
- **Classification:** **CONFIRMED BY RUNTIME + CONFIRMED BY SOURCE CODE**.

### E.2 COMPAS-B2 — Official execution path versus custom integration

- **Purpose:** locate the actual official robot execution boundary.
- **Expected:** distinguish a framework executor from a user-provided controller graph.
- **Observed:** official `Cx_SendTrajectory` subscribes to MQTT and exposes `element_id`/`robot_name`; it contains no ROS action/controller call. The public GHX example leaves robot control to an integration such as RRC, RTDE, or UR Script. The Unity tree visualizes trajectories and opens rosbridge but contains no fixed robot goal/publish executor path. Official documentation states that a complete planning routine is not supplied and CAD integration is required.
- **Evidence:** [Cx_SendTrajectory component](/home/cclab/ros_xr/frameworks/compas_xr/src/compas_xr/ghpython/components/Cx_SendTrajectory/code.py:19), [Unity execution button](/home/cclab/ros_xr/frameworks/compas_xr_unity_assembly/Assets/Scripts/UIFunctionalities.cs:1169), and [COMPAS XR user guide](https://compas.dev/compas_xr/latest/userguide.html).
- **Interpretation:** the official boundary verified here is an execution **handoff**, not physical execution. Whether a particular deployment validates approval before moving a robot depends on custom integration.
- **Classification:** **CONFIRMED BY SOURCE CODE**; official robot consequence **UNCONFIRMED**.

### E.3 COMPAS-B3 — T_A approval to T_B execution-handoff substitution

- **Purpose:** test whether the framework rejects a different trajectory after approval.
- **Expected:** normal T_A should reach the sink; substituted T_B should either be rejected, accepted, or left to custom integration.
- **Observed:** normal T_A reached the inert official message/transport subscriber. After an approval message carrying T_A, `SendTrajectory` carrying T_B but the same element-derived ID also reached the subscriber. No automatic equality/digest check rejected T_B.
- **Evidence:** [COMPAS runtime log](/home/cclab/ros_xr/evidence/authorization_continuity_compas_runtime.log), `approval_to_execution_substitution` and `received_handoffs`.
- **Interpretation:** result category is **C — framework handoff does not decide; custom integration is responsible**. It is valid evidence of missing framework-level exact-action binding, not evidence that an official or physical robot executed T_B.
- **Classification:** handoff **CONFIRMED BY RUNTIME**; downstream execution **UNCONFIRMED HYPOTHESIS**.

### E.4 COMPAS-B4 — Approval identity and duplicate vote

- **Purpose:** determine whether one authenticated device can contribute at most one vote to a current transaction.
- **Expected:** duplicate approvals/counter replies from one device should be deduplicated and tied to the active trajectory/epoch.
- **Observed:** two identical logical-device approval messages and two counter replies produced `ApprovalCount +2` and `UserCount +2` in the source-faithful Unity state model. The handler increments counters per message without a distinct-device set or exact current-trajectory comparison. Separately, official Python `Header.parse` did not preserve the encoded fields: sequence/response/device/timestamp shifted because of positional construction.
- **Evidence:** runtime `duplicate_vote_source_logic_model` and `python_header_round_trip`; Unity handlers in [MqttTrajectoryManager.cs](/home/cclab/ros_xr/frameworks/compas_xr_unity_assembly/Assets/Scripts/MqttTrajectoryManager.cs:444) and [MqttTrajectoryManager.cs](/home/cclab/ros_xr/frameworks/compas_xr_unity_assembly/Assets/Scripts/MqttTrajectoryManager.cs:573); Python parse in [messages.py](/home/cclab/ros_xr/frameworks/compas_xr/src/compas_xr/mqtt/messages.py:108).
- **Interpretation:** identity continuity is not enforced by the inspected application state logic. The duplicate count is not a Unity binary runtime result, and the Python parser defect is implementation-specific; neither should be the Main Item.
- **Classification:** official wire/Python parse **CONFIRMED BY RUNTIME**; Unity counter behavior **CONFIRMED BY SOURCE CODE + SOURCE-FAITHFUL MODEL**.

### E.5 COMPAS-B5 — Producer disconnect/reconnect and direct handoff

- **Purpose:** determine whether a replacement producer must present prior approval proof.
- **Expected:** if approval continuity is enforced at handoff, a new producer without proof should fail.
- **Observed:** after the original producer disconnected, a new MQTT client labeled `forged-device` sent T_B and the inert subscriber received it. `SendTrajectory` has no prior approval field to verify.
- **Evidence:** runtime `producer_disconnect_reconnect`; schema source above.
- **Interpretation:** this demonstrates framework-level binding absence under the deliberately anonymous local broker. It does **not** demonstrate the security configuration of an official deployment or claim that TLS/ACL cannot restrict publish access.
- **Classification:** **CONFIRMED BY RUNTIME** with deployment limitation.

### E.6 State, timeout, focus, and reconnect static findings

- `PrimaryUser`, `UserCount`, `ApprovalCount`, current trajectory, timeout token, and dirty flag are process-local mutable state.
- Counter and approval messages are not deduplicated by authenticated device, transaction epoch, or exact trajectory content.
- `SendTrajectory` is published before the status-2 consensus message in the inspected execution button path.
- Connection loss logs a warning/restart instruction. Generic mobile focus handling is not bound to authorization state; the base focus reconnect code is under a UWP/HoloLens guard.
- These are **CONFIRMED BY SOURCE CODE**. Actual Android/iOS/HoloLens focus-loss runtime and broker-session behavior remain **UNCONFIRMED HYPOTHESES**.

## F. Confirmed / Unconfirmed / Rejected

### F.1 CONFIRMED

- **Runtime:** HORUS normal lease arbitration works for two HorusLink clients.
- **Runtime + source:** a protected HORUS command is allowed when no active lease exists.
- **Runtime + source:** HORUS identity strings are client assertions; lease ownership is connection-based.
- **Runtime + source:** a client asserting `host` can clear the tested protected-topic catalog.
- **Runtime + source:** explicit release, TTL expiry, and disconnect did not issue a cancel for already accepted Nav2 goals within the measured windows; all three remained active at observation end.
- **Runtime:** two HORUS clients appeared behind one bridge ROS publisher endpoint.
- **Runtime + source:** COMPAS XR T_A/T_B can have different content and the same element-derived trajectory ID.
- **Runtime + source:** `SendTrajectory` lacks approval proof/content digest/version/approver epoch.
- **Runtime:** T_B reached the inert official message/transport handoff after T_A approval without automatic content rejection.
- **Source:** public COMPAS XR execution ends at a customizable handoff; no complete official robot executor is present in the fixed repositories.
- **Runtime + source model:** duplicate messages are not deduplicated in the inspected count logic.
- **Runtime:** fixed Python `Header.parse` corrupts the encoded identity field mapping.

### F.2 REASONABLE INFERENCE

- A HORUS deployment that maps the shared bridge publisher into one trusted SROS2 enclave will be authorized at that bridge principal unless it adds a separate per-client enforcement layer. This follows from the observed ROS graph plus the already verified SROS2 model, but was not rerun with HORUS.
- A COMPAS integration that directly executes each `SendTrajectory` payload without an independent approval/content/version comparison would make T_B eligible for execution. This follows from the official handoff schema/runtime, but no representative executor was run.
- Identity collapse, lease/action lifetime separation, and approval/action substitution are different manifestations of external authorization semantics not being carried as one final-enforcement object. This is a cross-framework analytical inference, not a proven universal root cause.

### F.3 UNCONFIRMED

- Actual Quest/OpenXR focus loss causing or failing to cause HORUS lease release and action cancellation.
- HORUS behavior with the matching current production Unity client rather than the faithful local emulator.
- Physical robot stop/cancellation semantics after HORUS lease revocation.
- Whether a deployed COMPAS XR broker uses TLS, ACLs, client certificates, or topic-level authorization.
- T_B reaching MoveIt/RTDE/controller execution in a representative official case-study integration.
- Actual Unity binary duplicate vote, reconnect, timeout, and mobile focus behavior.
- A universal authorization-continuity failure across XR–ROS systems.
- Final novelty after exhaustive peer-reviewed literature review and artifact comparison.

### F.4 REJECTED OR DOWNGRADED

- **“Quest2ROS2 proves authenticated privilege laundering.”** Rejected: no authenticated upstream role boundary exists in the inspected framework.
- **“HORUS `app_id`/`role`/`session_id` are authenticated identities.”** Rejected for the tested current source/runtime.
- **“HORUS requires a lease for every protected command.”** Rejected for current implementation; no-lease state allows a command.
- **“COMPAS trajectory ID uniquely names trajectory content.”** Rejected; it is element-derived.
- **“COMPAS XR itself contains a complete robot executor that accepted T_B.”** Rejected for the fixed public repositories.
- **“The result is an SROS2 vulnerability/bypass.”** Rejected: SROS2 correctly authorizes the ROS/DDS bridge principal it sees.
- **“Missing MQTT authentication is the main novelty.”** Downgraded as a known deployment/network-control issue.
- **“Authorization Continuity is a new name/general concept.”** Rejected due to direct 2026 prior-art terminology and causal-lineage collision.
- **“A cancel request proves physical stop.”** Rejected as an evaluation shortcut; controller/robot stop must be measured independently.

## G. Existing Work Collision

| Existing work | Collision with this item | Residual distinction / consequence |
|---|---|---|
| [Authorization Continuity for evolving AI agents (2026 preprint)](https://arxiv.org/abs/2607.23586) | Direct collision with the term and general question “is this still the agent I authorized?” | Do not claim the name or generic concept first. Narrow to XR–ROS shared bridges, robot action epochs, and exact accepted action consequences. |
| [Proof-of-Continuity (2026 preprint)](https://arxiv.org/abs/2607.08906) | Causal authority lineage and non-expansive authority propagation overlap the abstract model. | Contribution must be a concrete XR–ROS threat model, framework measurements, and final robot-action enforcement/cancellation semantics, not generic lineage theory. |
| [SROS2 enclaves](https://design.ros2.org/articles/ros2_security_enclaves.html), [DDS security](https://design.ros2.org/articles/ros2_dds_security.html), [access-control policy](https://design.ros2.org/articles/ros2_access_control_policies.html) | Provides participant/enclave authentication, encryption/signing, and resource ACLs. | It authorizes the bridge's ROS/DDS principal; it does not automatically reconstruct external human/app/session identity or bind an earlier approval to one exact downstream action. This is a trust-boundary problem, not an SROS2 flaw. |
| [ROSAuth](https://web.cs.wpi.edu/~cshue/research/tepra14.pdf) | Connection token/MAC, nonce, and expiration overlap upstream client authentication. | Removes anonymous/self-asserted access but does not by itself establish exact robot-action content binding and already-running goal cancellation. |
| [Application-level security for ROS](https://bernharddieber.com/publication/dieber2016applicationlevelsecurity/dieber2016applicationlevelsecurity.pdf) | Prior per-message publisher identity/signature/encryption kills any “first per-message ROS provenance/integrity” claim. | A residual question is semantic authorization of one human-reviewed action and revocable action lineage, not generic message integrity. |
| [PBAC for ROS](https://yaoguopku.github.io/papers/Zong-CCR-19.pdf) | Expiring identity/access tokens and runtime revocation cover future request authorization. | Runtime revocation itself is not novel. The candidate must test accepted/in-flight robot action cancellation and exact approved payload/goal binding. |
| [Fabric-enabled ABAC for ROS 2 multi-robot systems](https://www.sciencedirect.com/science/article/pii/S1383762125002000) | X.509 attributes, bridge authorization, per-message ledger assets, and task tuples cover identity-preserving bridge authorization and exclusive resource acquisition. | Kills “first bridge auth/user-to-robot task binding.” Residual scope must include XR runtime authority epoch, canonical exact action, and bounded downstream cancellation/stop. |
| [HORUS initial paper](https://arxiv.org/abs/2506.02622) and [multi-operator HORUS paper](https://arxiv.org/abs/2606.07013) | HORUS already provides multi-user collision arbitration/control leases. | Current result is not “first multi-user lease”; it is the measured separation between lease end and accepted Nav2 goal lifetime plus unauthenticated control metadata. |
| [COMPAS XR user guide](https://compas.dev/compas_xr/latest/userguide.html) and workflow | Preview/review/approval/execution workflow is existing functionality. | Do not claim first XR trajectory approval. The precise residual is absent immutable approval evidence at a customizable execution handoff. |
| [Dual-mode VR robot programming, Robotica 2024](https://doi.org/10.1017/S0263574724000663) | Prior preview/approve execution and continuous-consent/deadman behavior collide with generic XR consent novelty. | Candidate must compare exact binding and authority epoch propagation, not merely add an approve button or deadman trigger. |
| [Digital-twin trajectory command manipulation](https://arxiv.org/pdf/2211.09507) | Prior trajectory substitution/manipulation threat model. | Do not claim first trajectory manipulation; focus on mismatch between authenticated XR approval object and accepted robot action under shared bridge semantics. |
| [PAtt](https://www.usenix.org/system/files/raid2019-ghaeini.pdf) and [TAT, USENIX Security 2026](https://www.usenix.org/conference/usenixsecurity26/presentation/yao-chengtao) | Robot/trajectory integrity and attestation are established. | TAT compares actual robot motion against intended task/path; this work would need to define and carry a human/XR-approved canonical action and live revocation epoch. Confirm exact distinctions again before a novelty claim. |
| [ROS 2 Actions design](https://design.ros2.org/articles/actions.html) | Goal UUIDs and cancellation primitives already exist. | Novelty cannot be “actions can be canceled.” The question is whether upstream authority is linked to the exact accepted goal and whether revoke triggers bounded safe termination; cancel acceptance is not physical stop. |

Conclusion of collision check: the broad terminology and many individual mechanisms are known. A defensible paper cannot be built around missing TLS, principal collapse alone, lease cleanup alone, preview/approval alone, message signatures alone, or trajectory integrity alone.

## H. Cross-Framework Synthesis

### H.1 Property matrix

| Framework/path | Identity | Lifetime / Revocation | Exact Action Binding | Evidence strength |
|---|---|---|---|---|
| Quest2ROS2 + SROS2 baseline | External A/B collapse to one trusted endpoint ROS identity; no authenticated app role found | Publisher survives client loss and can be reused; full action/session authority not tested | Not tested for an approved action | Strong runtime for ROS identity/lifecycle; weak authorization premise |
| HORUS current fixed main | Lease separated by logical connection; `app_id`/`role`/`session_id` self-asserted; shared ROS publisher | Lease release/expiry/disconnect works for future ownership, but accepted goals received no cancel in measured windows | Lease check gates topic publish, not a persistent lease-to-goal lineage | Strong runtime/source, including actual ROS action consequence |
| COMPAS XR current fixed main | Payload `device_id` is not bound to broker connection/authenticated principal; vote dedupe absent in source logic | Approval state/timers are local mutable state; no execution proof carries an epoch | Element-derived ID; approval and send each carry mutable trajectory; no approval digest/proof at handoff | Strong schema/handoff evidence; downstream robot consequence unverified |

### H.2 Does one common model actually hold?

The proposed flow is:

```text
XR Authorization
→ authenticated Identity
→ live Lifetime / Revocation epoch
→ canonical Exact Action Binding
→ ROS / Robot final enforcement
```

It holds as a useful **security invariant and measurement framework**, not yet as a proven universal vulnerability:

- HORUS supplies the strongest Lifetime counterexample: ending a lease did not cancel the action already accepted under it.
- COMPAS XR supplies an Exact Action Binding counterexample at the messaging handoff: the approved object is not verifiably bound to the sent object.
- Quest2ROS2 supplies an Identity/trust-boundary baseline: ROS sees the bridge principal, not external clients.
- These failures are not the same implementation bug and do not share one immediate patch. Their common root is that external authorization semantics are not first-class, end-to-end data at the final action enforcement point.

The synthesis must therefore remain conditional. It becomes a strong unified item only if a representative COMPAS integration executes or would accept T_B without an independent equality/version check, and a real HORUS Quest/session transition reproduces authority-to-action lifetime separation. If either framework's production integration already restores those properties, it becomes a case study or is removed.

## I. GO / NO-GO

# CONDITIONAL GO

Reasons:

1. HORUS provides one strong, reproducible framework result with an actual ROS Action consequence: three authority termination paths did not generate action cancellation within explicit observation windows.
2. COMPAS XR independently exposes an exact-action binding gap in official schemas and handoff, but its physical/official execution semantics are custom and therefore incomplete.
3. Quest2ROS2 supplies consistent bridge identity-collapse evidence, but lacks an authenticated upstream role and cannot independently support privilege-laundering novelty.
4. The residual problem is more than missing TLS or a one-line ACL: final enforcement needs authenticated origin, revocation epoch, exact action identity, and accepted-goal lineage together.
5. Broad “Authorization Continuity,” bridge auth, revocation, per-message provenance, XR approval, and trajectory integrity each collide with existing work; only a carefully narrowed integration/evaluation contribution remains plausible.
6. No physical robot, current Quest focus lifecycle, or representative COMPAS executor was tested. Those missing links prevent STRONG GO.

Kill/pivot rule: if a representative COMPAS executor binds approval to a content/version digest and current HORUS Quest lifecycle reliably cancels or safely stops the exact in-flight goal on authority loss, abandon the unified Main Item. Retain only isolated implementation findings if independently worthwhile.

## J. 현재 우리가 실제로 주장할 수 있는 문장

### J.1 What we CAN claim

- “At fixed revision `eca75cb...`, the tested HORUS lease mechanism correctly arbitrated concurrent clients, while explicit release, TTL expiry, and disconnect did not issue cancellation for already accepted Nav2 goals within 0.7–1.0 second observation windows.”
- “In the tested HORUS path, lease ownership was associated with a logical transport connection, whereas `app_id`, `role`, and `session_id` were client-provided metadata rather than authenticated principals.”
- “At fixed COMPAS XR revisions, `trajectory_id` was derived from `element_id`, and `SendTrajectory` carried no verifiable approval digest, version, approver set, or authorization epoch.”
- “A trajectory different from the approved trajectory but sharing the same element-derived ID reached an inert official message/transport handoff without framework-level content rejection.”
- “The public COMPAS XR repositories delegate the final robot-control integration; therefore exact enforcement behavior is integration-dependent.”
- “Across the measured systems, external authorization semantics were not represented as one end-to-end binding among authenticated origin, live authority epoch, and exact accepted robot action.”
- “These results motivate, but do not yet establish, a general XR–ROS security mechanism and evaluation methodology.”

### J.2 What we MUST NOT claim

- SROS2 is vulnerable, bypassed, or incorrectly implemented.
- All XR–ROS frameworks collapse identity or fail authorization continuity.
- A completed authenticated privilege-laundering attack exists in Quest2ROS2 or HORUS.
- A physical robot or official COMPAS executor executed T_B.
- Actual Quest/OpenXR focus loss has been exploited or even reproduced.
- A HORUS release can never lead to stopping through any downstream safety layer; only no action cancel was seen in the bounded test.
- An accepted ROS action cancellation is equivalent to physical robot stop.
- The Python header parser defect or catalog-clear behavior alone establishes a general research contribution.
- This is the first authorization-continuity, provenance, bridge-authentication, revocation, XR-approval, or trajectory-integrity work.
- Existing PBAC/ABAC/TAT/SROS2 mechanisms cannot address parts of the problem.

## K. 다음 작업

### K.1 Priority 1 — Current HORUS Quest/OpenXR lifecycle run

- **What:** obtain the matching current multi-operator Unity source/build, run on Quest, and timestamp focus loss/session stop/app pause against heartbeat, lease release, action cancel, and simulated/robot stop.
- **Why:** it connects a real XR authority event to the strongest existing action-lifetime finding.
- **Decision:** real focus loss with bounded lease cleanup but no exact-goal cancel/stop strengthens GO; reliable goal cancellation/safe stop rejects the focus/lifetime claim and may downgrade HORUS to a catalog/authentication case study.

### K.2 Priority 2 — Representative COMPAS XR execution integration

- **What:** reproduce one official paper/example-style Grasshopper/CAD → controller integration with an inert or simulated robot, instrument T_A approval and T_B delivered/executed content, and record any custom equality/version check.
- **Why:** current evidence stops at handoff; this is the missing second-framework consequence.
- **Decision:** T_B accepted by the representative integration without independent binding moves toward STRONG GO; a robust content/version check rejects the COMPAS substitution hypothesis and may remove Track B.

### K.3 Priority 3 — Narrow novelty and claim chart

- **What:** build a claim-by-claim table against Authorization Continuity/Proof-of-Continuity, PBAC, Fabric-ROS2 ABAC, application-level security, Robotica consent work, PAtt, and TAT; verify peer-reviewed status and artifacts.
- **Why:** broad terminology and several mechanisms already collide.
- **Decision:** a residual invariant containing authenticated XR origin + live epoch + canonical exact action + bounded accepted-goal termination supports GO; if an existing system already provides and evaluates that full chain, pivot or NO-GO.

### K.4 Priority 4 — HORUS plus SROS2 identity baseline

- **What:** place the real HORUS bridge in a trusted SROS2 enclave and repeat low direct BLOCK versus HorusLink-mediated ALLOW while recording ROS publisher GID and external connection identity.
- **Why:** connects the new strong framework to the existing SROS2 baseline without calling it a bypass.
- **Decision:** shared bridge principal with connection-local lease state strengthens the trust-boundary model; per-client ROS/DDS identity or end-to-end policy preservation weakens identity-collapse generalization.

### K.5 Priority 5 — Complete HORUS admission-path coverage

- **What:** locally test the source-observed service path, action cancel path, direct ROS-side publishers, and publisher/resource lifecycle under lease change.
- **Why:** determines whether the invariant is limited to one Nav2 adapter/topic path or spans framework admission paths.
- **Decision:** multiple paths lacking lease/action lineage strengthen the systemic claim; one isolated adapter defect narrows it to a patch-level case.

### K.6 Priority 6 — Defense only after the above gates

- **What:** only if both tracks survive, specify a minimal authenticated origin + authority epoch + canonical action digest/goal-ID token at the final enforcement point and measure cancellation/stop latency; do not start ORBIT/eBPF yet.
- **Why:** a defense before confirming the second consequence risks solving an artificial problem.
- **Decision:** inability to enforce without breaking normal multi-user/robot workflows is a pivot signal; a small one-line framework fix downgrades the paper scope to case study unless the general enforcement/evaluation problem remains.

## L. 사용자 이해용 쉬운 설명

1. 우리가 연구하려는 것은 “XR에서 허락한 로봇 동작이 끝까지 같은 사람, 같은 유효시간, 같은 동작으로 유지되는가?”이다.  
2. 단순히 bridge에 비밀번호가 없는지를 찾는 연구가 아니다.  
3. HORUS에서는 두 사람이 동시에 조종하지 못하게 하는 lease가 정상 동작했다.  
4. A가 lease를 가지면 A 명령은 통과하고 B 명령은 막혔다.  
5. 그러나 A가 이미 긴 Nav2 동작을 시작한 뒤 lease를 반납하거나 잃어도 그 동작의 cancel 요청은 나오지 않았다.  
6. 즉 “새 명령 권한 종료”와 “이미 시작된 로봇 동작 종료”가 분리돼 있었다.  
7. HORUS의 app/role/session 문자열도 서버가 인증한 신원이 아니라 client가 보낸 값이었다.  
8. COMPAS XR에서는 사람이 본 T_A와 다른 T_B가 같은 step 기반 ID를 가질 수 있었다.  
9. 승인 메시지와 실행 메시지 사이에 T_A임을 증명하는 hash/version/승인 증거가 없었다.  
10. 그래서 T_A 승인 뒤 T_B가 MQTT 실행 handoff까지 도달했다.  
11. 다만 공개 COMPAS XR에는 완성된 로봇 executor가 없어서 T_B가 실제 로봇을 움직였다고 말할 수 없다.  
12. 지금 결과는 하나의 강한 HORUS 사례와 하나의 조건부 COMPAS 사례다.  
13. 따라서 논문 Main Item 가능성은 있지만 아직 확정은 아니며 판정은 CONDITIONAL GO다.  
14. 다음에는 실제 HORUS Quest focus-loss 실험과 대표 COMPAS robot integration을 먼저 해야 한다.  
15. 두 실험에서도 같은 문제가 남으면 방어 설계를 시작하고, 이미 안전하게 연결돼 있으면 과감히 범위를 줄이거나 중단해야 한다.

## M. Files / Evidence Links

### Primary report and context

- [AUTHORIZATION_CONTINUITY_RESULTS.md](/home/cclab/ros_xr/AUTHORIZATION_CONTINUITY_RESULTS.md)
- [RESEARCH_CONTEXT.md](/home/cclab/ros_xr/RESEARCH_CONTEXT.md)
- [Evidence summary](/home/cclab/ros_xr/evidence/authorization_continuity_summary.md)

### Runtime evidence

- [HORUS runtime evidence](/home/cclab/ros_xr/evidence/authorization_continuity_horus_runtime.log)
- [COMPAS XR runtime evidence](/home/cclab/ros_xr/evidence/authorization_continuity_compas_runtime.log)
- [Existing Quest2ROS2 runtime evidence](/home/cclab/ros_xr/evidence/quest2ros2_runtime.log)
- [Existing Quest2ROS2 identity evidence](/home/cclab/ros_xr/evidence/quest2ros2_identity.txt)

### Reproduction

- [Combined authorization-continuity runner](/home/cclab/ros_xr/authorization_env/run_authorization_continuity.sh)
- [Authorization test Dockerfile](/home/cclab/ros_xr/authorization_env/Dockerfile)
- [HORUS container runner](/home/cclab/ros_xr/authorization_env/run_horus_runtime_in_container.sh)
- [HORUS runtime probe](/home/cclab/ros_xr/authorization_env/horus_runtime_probe.py)
- [COMPAS container runner](/home/cclab/ros_xr/authorization_env/run_compas_runtime_in_container.sh)
- [COMPAS runtime probe](/home/cclab/ros_xr/authorization_env/compas_runtime_probe.py)

### Fixed source trees

- [HORUS ROS 2 source](/home/cclab/ros_xr/frameworks/horus_ros2)
- [HORUS app artifacts/docs](/home/cclab/ros_xr/frameworks/horus)
- [HORUS SDK source](/home/cclab/ros_xr/frameworks/horus_sdk)
- [COMPAS XR source](/home/cclab/ros_xr/frameworks/compas_xr)
- [COMPAS XR Unity source](/home/cclab/ros_xr/frameworks/compas_xr_unity_assembly)

Raw logs are intentionally not duplicated in this report. The retained evidence logs contain timestamp, fixed revision, command/test ID, expected scope, structured observations, and final verdict.
