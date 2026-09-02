# Handoff: XR2Act Decisive Validation

## 1. Executive Summary

- 목적: `XR2Act: Authority Refinement and Handoff Integrity for XR-to-Robot Action Pipelines`를 메이저 보안학회 Main Item으로 계속 밀 수 있는지 공격 성공을 전제하지 않고 판정했다.
- Track A — COMPAS: 인증이 필요한 local MQTT에서 정상 `T_A`와 A1–A4 변형을 official `compas_eve`/`SendTrajectory` subscriber까지 전달했다. 모든 `T_B` 변형이 framework handoff에 도달했지만 공개 official/maintainer-linked executor는 찾지 못해 robot/simulation input은 `UNCONFIRMED`다.
- Track B — HORUS: actual HorusLink → fixed HORUS backend/Nav2 adapter → actual Nav2 → `nav2_loopback_sim`에서 80/80 trial을 완료했다. A의 늦은 result publication 이후 B의 정상 HORUS cancel은 0/63 성공이었고, 실패한 동일 B Goal UUID의 direct Nav2 cancel은 67/67 성공했다.
- Track C — authenticated scope bypass: 서로 다른 검증 credential, credential-bound Robot/Action scope, shared downstream ROS authority를 동시에 제공하는 공개 XR–ROS 후보를 확보하지 못했다. 인위적 ACL 누락 환경을 만들지 않았고 공격도 수행하지 않았다.
- Track D — negative controls: COMPAS test-only exact-binding oracle은 정상 `T_A`만 허용하고 A1–A4 `T_B`를 거부했다. HORUS direct exact-UUID cancel은 독립 10/10과 공식 경로 실패 후 rescue 67/67에서 성공했다.
- 최종 판정: **WEAK / CASE-STUDY ONLY**. 확인된 새 결정적 결과는 HORUS fixed Nav2 adapter의 post-handoff ownership race 하나이며, 세 Track을 하나의 실증된 XR2Act failure class로 묶을 증거는 없다.
- Blocker: COMPAS의 inspectable final executor와 실제 authenticated multi-principal shared-bridge threat boundary가 없다. 실제 Quest와 physical robot은 이번 범위가 아니며 사용하지 않았다.

## 2. Feedback Applied

- 기존 `CONDITIONAL GO`를 유지하기 위해 결과를 끼워 맞추지 않고, “두 개 이상의 독립 failure class가 unauthorized actuation으로 연결되는가”를 새 기준으로 적용했다.
- HORUS의 release 후 autonomous continuation은 이미 확인된 결과로 두고, stock Nav2가 B Goal로 A를 preempt한다는 반증을 반영해 대표 공격에서 하향했다. 이번에는 오직 B가 정당한 새 holder가 된 뒤 B의 유효 cancel이 방해되는지를 검증했다.
- COMPAS는 approval과 execution 사이 exact binding gap이 가장 직접적인 두 번째 failure class 후보라서 먼저 검증했다. 그러나 official handoff 이후 robot executor가 custom integration임을 다시 확인해 실제 `T_B` 실행으로 과장하지 않았다.
- generic bridge identity collapse만으로 authenticated privilege laundering을 주장하지 않도록 실제 credential/scope 조건을 Track C에 추가했다.
- 취약한 대상만 고르는 오류를 막기 위해 exact digest/robot/epoch/approver oracle과 exact Goal UUID cancel을 동일 harness의 safe controls로 추가했다.

## 3. Environment and Fixed Revisions

실험일은 2026-08-27(KST)이다. Docker image `ros-xr-horus-nav2-jazzy:local`을 재사용했고, runtime container는 `--network none`, framework source는 read-only mount, evidence만 writable mount로 실행했다. Public broker, host network, privileged container, Quest, 실제 로봇은 사용하지 않았다.

| Component | Revision | Commit date | License | Modification |
|---|---|---|---|---|
| `RICE-unige/horus_ros2` | `eca75cbf559f09ff793d8993338b2f1ffed1adfd` | 2026-07-26 | Apache-2.0 | fixed checkout clean, 수정 없음 |
| `RICE-unige/horus` | `819cdfdc74f1a0c2bd73946dc14897a533f68b61` | 2026-08-07 | Apache-2.0 | fixed checkout clean, 수정 없음 |
| `RICE-unige/horus_sdk` | `f4f00dab41910676519d545515531ec243414044` | 2026-07-26 | Apache-2.0 | fixed checkout clean, 수정 없음 |
| `compas-dev/compas_xr` | `b86e6fbbacdc8e84183fc08c846176a1c79304ca` | 2026-03-27 | MIT | fixed checkout clean, 수정 없음 |
| `compas-dev/compas_xr_unity_assembly` | `f1516ca568b101447507aebc28a594bdc358df3e` | 2024-11-01 | MIT | fixed checkout clean, 수정 없음 |
| ROS 2 / Nav2 | Jazzy / Debian `navigation2 1.3.12` | image package snapshot | mixed upstream | actual action server, loopback plant |

Track C에서 ROSAuth/rosbridge를 후보로 source review했지만 runtime component를 추가하지 않았다. 따라서 현재 branch를 fixed experimental dependency로 표현하지 않는다.

## 4. Track A — COMPAS Approval-to-Execution

### Official Executor Search

고정된 `compas_xr`, Unity Assembly, official GHX 두 개, packaged `Cx_SendTrajectory`, documentation이 직접 설명하는 CAD/Grasshopper 경계를 조사했다. 공식 component는 full `SendTrajectory`를 callback으로 받지만 downstream output은 `element_id`와 `robot_name`뿐이며 trajectory content를 controller input으로 노출하지 않는다. GHX도 RRC/RTDE/UR Script를 project-specific placeholder로 둔다.

공식 문서는 all-user approval 뒤 initial requester가 `SendTrajectory`를 보내 robot execution을 요청한다고 설명하지만, 동시에 COMPAS XR가 complete planning routine을 제공하지 않고 CAD 쪽 planning/execution에 추가 user input이 필요하다고 명시한다. [COMPAS XR User Guide](https://compas.dev/compas_xr/latest/userguide.html), [official repository](https://github.com/compas-dev/compas_xr).

판정은 `PASS_CASE_C`: **public official or representative executable executor NOT FOUND**, final robot execution은 custom integration이다. 임의 dummy executor는 만들지 않았다.

### Normal T_A Baseline

- Threat actor/transport: broker credential `xr2act-primary`를 가진 legitimate project participant. Loopback Mosquitto는 anonymous access를 거부했다. 비밀번호는 evidence에 기록하지 않았다.
- Honest review model: A/B/C를 나타내는 세 approval header 뒤 `SendTrajectory(T_A)`를 보냈다. 세 device header는 framework message identity일 뿐 서로 다른 broker-authenticated principals로 검증되지는 않았다.
- `T_A` digest: `1563aeda683f8e866cee45e7cd76ecb356943952ab2707faf79e16d62918d73e`.
- ID/robot: `trajectory_id_assembly-step-7`, `ur10e-local-probe`.
- Observed: `T_A`가 official `compas_eve` parser/subscriber에 도달했다.
- Final executor/actuator input: inert audit sink까지만 확인. Robot/simulation input은 `UNCONFIRMED`.

### T_A→T_B Substitution

- `T_B` digest: `9dcd92a730b50a858150872346c2eb6a5352b4eb1555c34bdee7bcbe79eb933d`; `T_A`와 다르다.
- A1 Mutable `CurrentTrajectory`: Unity approval button과 execute button이 각각 호출 시점의 mutable `CurrentTrajectory`와 `ActiveRobotName`을 다시 읽는다. 이는 `CONFIRMED BY SOURCE`; Unity binary attack runtime은 수행하지 않았다.
- A2 Same ID / Different Content: `T_A`와 `T_B`는 같은 element-derived trajectory ID였고 `T_B`가 official transport/subscriber에 도달했다. `CONFIRMED BY RUNTIME` at handoff.
- `SendTrajectory`에는 approval digest, content version, approver set, approval proof, authorization epoch가 없었다.
- Final classification: `Accept but No Robot Command` + `Custom Integration Dependent`, 즉 **C — Framework Integration Hazard**.

### Cross-Robot / Stale Approval

- A3 Cross-Robot: 승인 robot `ur10e-local-probe` 대신 `ur3-cross-robot-probe`를 넣은 동일-ID message가 official subscriber에 도달했다. Framework reject 없음; robot command 없음.
- A4 Stale Approval: consensus marker 뒤 old response identity와 다른 `T_B`를 보냈고 official subscriber가 수용했다. Send schema에는 검증할 approval epoch가 없다.
- 두 결과 모두 handoff acceptance는 `CONFIRMED BY RUNTIME`, downstream controller acceptance는 `UNCONFIRMED`다.

### Final Classification

Track A는 **C — Framework Integration Hazard**, `SECONDARY EVIDENCE ONLY`다. Framework-level exact-binding guarantee가 public handoff에 없다는 것은 source/runtime으로 확인됐지만, official/representative executor가 `T_B`를 robot 또는 simulation input으로 수용했다는 강한 성공 조건은 충족하지 못했다.

### Evidence

- [COMPAS E2E log](/home/cclab/ros_xr/evidence/compas_e2e_execution.log)
- [Executor audit probe](/home/cclab/ros_xr/authorization_env/compas_executor_probe.py)
- [Runtime probe](/home/cclab/ros_xr/authorization_env/compas_runtime_probe.py)
- [Unity approval/execute source](/home/cclab/ros_xr/frameworks/compas_xr_unity_assembly/Assets/Scripts/UIFunctionalities.cs:1123)
- [Unity approval counter source](/home/cclab/ros_xr/frameworks/compas_xr_unity_assembly/Assets/Scripts/MqttTrajectoryManager.cs:444)
- [SendTrajectory schema](/home/cclab/ros_xr/frameworks/compas_xr/src/compas_xr/mqtt/messages.py:459)
- [Official handoff component](/home/cclab/ros_xr/frameworks/compas_xr/src/compas_xr/ghpython/components/Cx_SendTrajectory/code.py:19)

## 5. Track B — HORUS Post-Handoff Integrity

### Normal Handoff

경로는 Mock XR lifecycle → actual HorusLink TCP → actual `horus_unity_bridge` → actual HORUS backend/`Nav2ActionAdapter` → actual Nav2 `NavigateToPose` → `nav2_loopback_sim`이다. Probe는 ActionServer를 만들지 않았다.

각 80 trial에서 A lease/`G_A` 뒤 A release, B lease acquire, distinct `G_B` acceptance를 재구성했다. A/B UUID는 각각 80개가 모두 unique하고 두 집합의 overlap은 0이었다. B는 80/80에서 정당한 새 lease holder가 되었고 stock Nav2가 `G_A`를 `ABORTED`로 preempt한 뒤 `G_B`를 실행했다.

### Late-Result / Goal Ownership Race

Fixed adapter는 robot별 `active_goal_handle` 하나만 보유한다. `G_B` response callback이 그 handle을 설정한 후에도, `G_A`의 늦은 result callback은 어느 Goal의 callback인지 대조하지 않고 같은 handle을 reset한 뒤 `goal_failed`를 publish한다.

| Timing mode | Official B cancel | Interference | Exact UUID rescue |
|---|---:|---:|---:|
| B accept + 0 ms | 2/10 | 8/10 | 8/8 |
| B accept + 5 ms | 1/10 | 9/10 | 9/9 |
| A result publication + 0 ms | 0/10 | 10/10 | 10/10 |
| A result + 10 ms | 0/10 | 10/10 | 10/10 |
| A result + 50 ms | 0/10 | 10/10 | 10/10 |
| A result + 100 ms | 0/10 | 10/10 | 10/10 |
| A result + 500 ms | 0/10 | 10/10 | 10/10 |

전체 공식 cancel 70회 중 A result status publication 전에 전송된 것은 7회였고 3회 성공했다. Publication 이후 전송된 63회는 0/63 성공이었다. 실패한 67회 모두 같은 `G_B` UUID의 direct Nav2 cancel service가 `goals_canceling`에 정확한 UUID를 반환하고 `CANCELED` terminal을 만들었다.

Adapter private handle은 runtime에서 직접 introspect하지 않았다. 대신 source에서 reset-before-status ordering을 확인하고, runtime에서 HORUS cancel topic 도착, B terminal 부재, 같은 UUID direct cancel 성공을 함께 기록했다. 그러므로 “handle이 비었다”는 결론은 source + runtime 결합이며 메모리 내부를 직접 측정했다는 주장은 하지 않는다.

### B Cancel / Safe Hold

현재 공개 path에서 확인된 가장 가까운 정식 safe control은 HORUS `goal_cancel`이다. 존재하지 않는 Pause/Safe-Hold API는 만들지 않았다.

- 공식 경로 실패 후 exact rescue를 보내기 전 0.75초 관찰창의 simulated odometry path는 0.095100–0.378623 m, 중앙값 0.177091 m였다.
- Exact cancel request → B `CANCELED`는 4.848–43.669 ms, 중앙값 27.520 ms였다.
- Exact cancel → 0.5초 zero-motion hold를 포함한 measured stop detection은 551.931–690.239 ms, 중앙값 630.687 ms였다.
- 각 trial의 final B state가 `CANCELED`인 이유는 실패한 official path 뒤 test oracle이 구조했기 때문이다. Official cancel이 성공했다고 오독하면 안 된다.

이는 B가 현재 owner이고 유효한 공식 cancel을 보냈는데 A의 stale result lifecycle 때문에 B Goal 관리가 실패한 **A — Security Property Violation, CONFIRMED BY RUNTIME**이다. 다만 결과는 loopback simulation이며 physical robot stop/거리 증거가 아니다.

### Stale Session/Epoch

이번 decisive run은 stale session 문자열 재사용을 새 공격으로 만들지 않았다. 기존 F6에서는 B 소유 중 old connection command가 차단됐고, B release 뒤 old logical session ID가 다시 acquire할 수 있었다. `session_id`가 cryptographic epoch/capability라는 보장이 없으므로 이는 **B — Policy Ambiguity / UNCONFIRMED security exploit**로 유지한다.

### Final Classification

Track B는 fixed HORUS Nav2 adapter의 **post-handoff Goal ownership integrity failure**로 확인됐다. 공격/오류 결과는 특정 timing에서 반복되고, direct Nav2 exact-UUID path는 정상이다. 동시에 원인은 한 adapter의 single-handle/result-correlation 오류로 좁혀지며, 작은 local patch로 해결될 가능성이 높다. 따라서 강한 framework case study이지 독립적으로 XR2Act 통합 Main Item을 성립시키지는 않는다.

### Evidence

- [HORUS post-handoff JSONL](/home/cclab/ros_xr/evidence/horus_post_handoff.log)
- [HORUS post-handoff probe](/home/cclab/ros_xr/authorization_env/xr2act_horus_probe.py)
- [Fixed adapter single handle](/home/cclab/ros_xr/frameworks/horus_ros2/horus_backend/include/horus_backend/nav2_action_adapter.hpp:47)
- [Fixed adapter result reset](/home/cclab/ros_xr/frameworks/horus_ros2/horus_backend/src/nav2_action_adapter.cpp:211)
- [Prior actual Nav2 baseline](/home/cclab/ros_xr/evidence/xr_nav2_feasibility_summary.md)

## 6. Track C — Authenticated Scope Bypass

### Selected Real Framework/Auth Layer

실행 조건을 만족하는 후보를 선택하지 못했다. Quest2ROS2/ROS-TCP는 shared ROS authority는 있지만 client authentication/scope가 없고, HORUS identity fields는 self-asserted이며, COMPAS는 authenticated per-user Robot/Action scope와 shared ROS principal을 제공하지 않는다.

ROSAuth + rosbridge도 검토했다. ROSAuth는 remote client connection authentication 도구지만 current rosbridge ROS 2 code의 topic/service/action globs는 server-level parameters이며 credential별 Robot/Action scope로 연결되지 않는다. 또한 rosbridge ROS 2 changelog는 ROSAuth integration이 제거됐다고 기록한다. [ROSAuth repository](https://github.com/GT-RAIL/rosauth), [rosbridge current server parameters](https://github.com/RobotWebTools/rosbridge_suite/blob/ros2/rosbridge_server/scripts/rosbridge_websocket.py), [rosbridge changelog](https://docs.ros.org/en/ros2_packages/kilted/api/rosbridge_server/__CHANGELOG.html).

### A/B Credentials and Scope

검증된 서로 다른 A/B credentials와 다음과 같은 명시적 상반 scope를 제공하는 공개 후보가 없었다.

- A: Robot 1 allow, Robot 2 deny
- B: Robot 2 allow, Robot 1 deny
- Shared bridge: Robot 1/2 downstream authority

이름만 Viewer/Operator로 붙이거나 custom gateway에 일부러 ACL을 빼지 않았다.

### Direct Baseline

기존 SROS2 runtime에서 low direct ROS principal은 `/cmd_vel`에서 BLOCK되고 trusted bridge는 ALLOW였다. 이것은 downstream principal collapse baseline이지, upstream A/B가 실제로 인증되고 서로 다른 scope를 받았다는 baseline은 아니다.

### Shared-Bridge Test

수행하지 않았다. 최소 threat boundary가 없으므로 성공하도록 만든 synthetic runtime은 testbed artifact가 된다. 따라서 credential, assigned scope, forbidden destination, bridge-side decision, actuator receive를 채울 실제 test record도 없다.

### Final Classification

`UNCONFIRMED_REAL_THREAT_BOUNDARY_UNAVAILABLE`, **F — No Vulnerability Claim**. 이는 안전하다는 증명도 공격 성공도 아니다. 정확한 blocker는 “distinct verified credentials + credential-bound Robot/Action scopes + one shared downstream ROS authority”를 동시에 제공하는 공개 후보 부재다.

### Evidence

- [Bridge scope candidate audit](/home/cclab/ros_xr/evidence/bridge_scope_bypass.log)
- [Scope audit script](/home/cclab/ros_xr/authorization_env/xr2act_scope_audit.py)
- [Prior Quest2ROS2 identity evidence](/home/cclab/ros_xr/evidence/quest2ros2_identity.txt)
- [Prior SROS2/bridge results](/home/cclab/ros_xr/AUTHORIZATION_CONTINUITY_RESULTS.md)

## 7. Track D — Negative Control

두 개의 안전 대조를 사용했다.

1. COMPAS test-only reference executor predicate는 canonical trajectory digest, robot identity, approval epoch, exact approver set을 최종 경계에서 비교했다. 정상 `T_A`는 ALLOW, same-ID `T_B`, cross-robot `T_B`, stale-epoch `T_B`는 모두 REJECT였다. 이는 official COMPAS 기능이나 새 defense contribution이 아니다.
2. ROS 2 Action의 exact `G_B` UUID cancel을 사용했다. 독립 `A-result+100 ms` control 10/10이 성공했고, HORUS official path가 실패한 67/67도 같은 B UUID를 정확히 cancel했다. ROS 2 Action design 자체가 goal ID와 timestamp에 따른 cancel을 정의한다. [Official ROS 2 Actions design](https://design.ros2.org/articles/actions.html).

동일 harness가 정상 `T_A`와 잘못된 `T_B`, 손상된 adapter path와 정상 exact-UUID path를 구분했으므로 test oracle은 PASS다. 상세 결과는 [negative control log](/home/cclab/ros_xr/evidence/negative_control.log)에 있다.

## 8. Confirmed / Unconfirmed / Rejected

### CONFIRMED ATTACKS

- **HORUS post-handoff ownership interference — CONFIRMED BY RUNTIME / Security Property Violation.** B가 valid lease와 accepted `G_B`를 보유했지만 A의 late result 뒤 official cancel이 0/63 성공했다. 같은 B UUID direct cancel은 실패 사례 67/67에서 성공했다.
- 실제 consequence는 simulation motion continuation이다. Failed official cancel 뒤 rescue까지 0.095100–0.378623 m의 loopback odometry path가 관측됐다.

### CONFIRMED SAFE BEHAVIOR

- Actual Nav2 normal handoff/preemption과 distinct Goal UUID 생성.
- Direct exact B UUID cancel 77/77: 독립 10회 + official failure rescue 67회.
- Test-only exact COMPAS binding은 정상 A 허용, 세 종류 B 거부.
- Track C에서 threat boundary가 없을 때 synthetic role/ACL attack을 만들지 않은 실험 설계.

### UNCONFIRMED

- COMPAS `T_B`의 MoveIt/RRC/RTDE/UR Script/physical executor input.
- Actual authenticated A/B scope bypass.
- Actual Quest/OpenXR focus/session event와 HORUS lease/action의 연결.
- Physical robot의 제동거리, collision, hardware safe stop.
- HORUS stale logical session ID가 authentication/epoch bypass를 만드는지 여부.

### REJECTED OR DOWNGRADED

- COMPAS official complete executor가 공개되어 있다는 가설: fixed source/artifact에서 찾지 못함.
- COMPAS handoff acceptance를 actual robot execution으로 부르는 주장: 기각.
- Quest2ROS2 identity collapse를 authenticated privilege laundering이라고 부르는 주장: 인증 boundary 부재로 기각.
- Dummy ActionServer의 A/B simultaneous-active 결과를 stock Nav2에 일반화: actual Nav2 preemption으로 기각.
- 세 framework가 하나의 universal XR2Act vulnerability를 보인다는 주장: 증거 부족으로 기각.

## 9. Semantic Refinement and Handoff Analysis

`Grant → Delegation → Semantic Refinement → Goal Creation → In-flight Ownership → Handoff/Revocation → Physical Result`는 좋은 분석 틀이지만, 이번 결과에서 하나의 **실증된 공통 invariant**로 완성되지는 않는다.

- COMPAS: `T_A` grant와 `T_B` handoff 사이 digest/robot/epoch binding 부재는 semantic substitution 후보다. A2는 같은 ID의 다른 joint content, A3는 다른 robot, A4는 stale transaction이므로 단순 byte mismatch보다 scope 확대에 가깝다. 그러나 Goal creation 이후가 custom executor라 chain이 끊긴다.
- HORUS: semantic content refinement보다 accepted Goal의 owner/lifecycle correlation이 핵심이다. B로 ownership이 넘어간 뒤 A result가 B handle을 지우므로 Handoff/Revocation 구간의 명백한 failure다.
- Scope: authenticated principal과 explicit resource scope가 없으므로 Grant/Delegation 자체를 구성하지 못했다.
- Track D: digest/robot/epoch/approver와 Goal UUID가 각 경계에서 binding되면 harness가 정상/비정상을 구분함을 보였다.

따라서 공통 언어는 설명 도구로 남지만, 서로 다른 구현 결함을 하나의 causal bug class로 통합하면 안 된다.

## 10. Existing Work Collision

| Prior work / mechanism | 이미 제공하는 것 | 이번 결과에 남는 residual |
|---|---|---|
| [End-to-End Authorization, OSDI 2000](https://www.usenix.org/conference/osdi-2000/end-end-authorization) | administrative/network/abstraction/protocol boundary를 가로지르는 authority justification | “경계에서 권한이 사라진다”는 일반 원리는 신규가 아니다. Fixed XR–ROS framework의 action-lifecycle 측정만 남는다. |
| [WAVE, USENIX Security 2019](https://www.usenix.org/conference/usenixsecurity19/presentation/andersen) | cryptographic transitive delegation과 permission proof | Delegation/capability 자체를 최초 제안할 수 없다. 이번에는 그런 system을 구현하지 않았다. |
| [UCONABC](https://doi.org/10.1145/984334.984339) | ongoing authorization, immediate revocation, mutable attributes | 지속적 권한 회수 개념은 신규가 아니다. HORUS adapter가 accepted action에서 이를 보존하지 못한 runtime 사례가 residual이다. |
| [SROS2 enclaves](https://design.ros2.org/articles/ros2_security_enclaves.html) / [access-control policies](https://design.ros2.org/articles/ros2_access_control_policies.html) | DDS participant/enclave identity와 ROS resource access control | Shared process가 한 identity/permission union을 갖는 구조를 명시한다. External user/action lineage 복원은 자동 제공하지 않지만 이는 SROS2 취약점이 아니다. |
| [ROSAuth](https://web.cs.wpi.edu/~cshue/research/tepra14.pdf) | remote non-native client의 connection authentication | Anonymous access는 줄이지만 current shared ROS 2 bridge에서 credential-bound per-resource scope와 approved-action/Goal lifetime binding을 입증하지 않는다. |
| [Procedurally Provisioned Access Control for Robotic Systems](https://arxiv.org/abs/1810.08125) / [PBAC for ROS](https://yaoguopku.github.io/papers/Zong-CCR-19.pdf) | ROS policy provisioning, policy/token 기반 request authorization·revocation | Access control와 revocation 자체는 신규가 아니다. Accepted Goal의 late-result ownership race 측정은 별도 implementation residual이다. |
| [ROS 2 Actions design](https://design.ros2.org/articles/actions.html) | Goal UUID, status, exact/temporal/all-goal cancel semantics | “Goal을 UUID로 cancel”은 기존 기능이다. HORUS가 B UUID handle을 잃는 runtime finding만 새 case evidence다. |
| HORUS fixed source | lease arbitration, Nav2 adapter, cancel path | 본 결과는 바로 이 구현의 single-handle late-result correlation failure이며 광범위한 theory가 아니다. |
| [COMPAS XR workflow](https://compas.dev/compas_xr/latest/userguide.html) | multi-user preview/review/approval/SendTrajectory | XR approval 자체는 신규가 아니다. Public handoff의 immutable exact-binding 부재는 integration hazard지만 final executor 부재로 제한된다. |
| [TAT, USENIX Security 2026](https://www.usenix.org/conference/usenixsecurity26/presentation/yao-chengtao) | intended trajectory와 actual arm motion의 trajectory-integrity attestation | Physical trajectory integrity는 이미 더 강하게 다뤄진다. XR human grant/epoch lineage는 개념상 다르지만 이번에는 physical attestation을 구현하지 않았다. |
| [Relay and Betray, USENIX Security 2026](https://www.usenix.org/conference/usenixsecurity26/presentation/ali) | multi-user MR client-side authority와 shared-state 공격의 체계적 실증 | XR client trust 일반 novelty는 약하다. XR-to-ROS accepted Action ownership이라는 좁은 residual만 구분된다. |

단일 Goal-handle generation check 또는 UUID-keyed registry로 HORUS race가 해결될 가능성이 높다. 따라서 현재 evidence는 “TLS/ACL 하나로 모든 Track이 해결되지 않는다”는 통합 contribution보다 “특정 adapter lifecycle correlation 오류”에 더 가깝다.

## 11. Main Research Item Decision

# WEAK / CASE-STUDY ONLY

1. HORUS에서 강한 post-handoff B cancel interference가 actual stack과 actual Nav2로 반복 확인됐다.
2. 그러나 확인된 결정적 failure class는 하나뿐이며 fixed `Nav2ActionAdapter`의 local single-handle race로 좁혀진다.
3. COMPAS A1–A4는 official handoff까지는 성립하지만 actual executor/robot input이 없어 Integration Hazard를 넘지 못했다.
4. Track C는 실제 authenticated scope boundary를 만들 수 없어 attack test 자체를 정직하게 생략했다.
5. Negative controls는 모두 PASS해 harness는 구분력을 가졌지만, 그 자체가 새 defense contribution은 아니다.
6. End-to-End Authorization, WAVE, UCON, ROS access control, Goal UUID/cancel, trajectory attestation과 개념 충돌이 크다.
7. 두 개 이상의 독립 unauthorized actuation failure와 공통 invariant라는 STRONG/CONDITIONAL GO 기준을 충족하지 못했다.
8. 물리 로봇·Quest 결과가 없으므로 XR device 또는 physical safety claim도 할 수 없다.

## 12. What We Can Claim

- “Fixed HORUS ROS 2 revision `eca75cbf...`의 tested Nav2 adapter에서 A의 preempted Goal result가 B의 active handle을 reset한 뒤, B의 valid HORUS cancel은 result publication 이후 63/63에서 B Goal을 cancel하지 못했다.”
- “동일 B Goal UUID에 대한 direct ROS 2 Action cancel은 official failure 67/67과 독립 control 10/10에서 성공했다.”
- “Failed official cancel 이후 exact rescue까지 loopback simulation에서 추가 odometry path가 관측됐다.”
- “Fixed COMPAS XR public handoff에는 approved digest/version/approver set/epoch binding이 없고 A1–A4 변형이 official subscriber까지 도달했지만 final robot execution은 custom integration dependent다.”
- “조사한 공개 후보에서는 authenticated per-principal Robot/Action scope와 shared ROS authority를 동시에 갖춘 runnable Track C boundary를 확보하지 못했다.”

## 13. What We Must Not Claim

- HORUS 전체 또는 모든 XR–ROS framework에 같은 취약점이 있다.
- COMPAS XR 또는 실제 robot이 `T_B`를 실행했다.
- Quest2ROS2에서 authenticated privilege laundering이 확인됐다.
- SROS2, ROS 2 Actions, Nav2, MQTT, OpenXR 자체의 취약점이다.
- Loopback 이동거리나 stop latency가 physical robot 제동거리다.
- End-to-End Authorization, ongoing revocation, capability, Goal UUID, trajectory integrity를 최초 제안했다.
- XR2Act 통합 framework 또는 완성된 defense가 구현·검증됐다.

## 14. Main Item Recommendation

현재 타당한 선택은 **HORUS post-handoff case study**다. XR2Act 통합 Main Item은 중단/보류하고, 확인된 late-result/Goal ownership race를 좁은 framework finding으로 정리한다. COMPAS는 “왜 통합 Item이 아직 성립하지 않는가”를 보여주는 secondary integration-hazard evidence로만 유지한다. Shared-bridge origin/scope study는 실제 authenticated candidate를 확보할 때 별도 재개한다.

## 15. Next Recommended Work

1. **HORUS minimal fix/regression** — Goal UUID 또는 generation별 handle/result correlation을 최소 patch로 구현하고 같은 8-mode × 10-trial matrix, pending goal, multi-robot selectivity를 반복한다. 모두 해결되면 local bug case로 확정되고 Main Item 가능성은 더 낮아진다. race가 다른 adapter/경로에도 남으면 case-study 범위가 넓어진다.
2. **Maintainer-linked COMPAS executor 확보** — 실제 사용된 GH/MoveIt/RRC/RTDE artifact나 maintainer 확인을 받아 `T_A` approval과 final input digest를 비교한다. `T_B`가 independent check 없이 수용되면 두 번째 failure class가 생겨 `CONDITIONAL GO`를 재검토할 수 있고, exact binding이면 Track A를 제거한다.
3. **Real authenticated shared bridge 후보 확보** — 서로 다른 certificates/tokens와 explicit Robot/Action deny scope를 제공하는 maintained implementation을 먼저 찾는다. 실제 후보가 있을 때만 Track C를 실행한다. ACL이 정상 차단하면 scope-bypass 방향은 종료한다.
4. **Actual Quest lifecycle trace** — matching HORUS multi-operator build가 확보되면 focus/pause/session stop → heartbeat/release → Goal/cancel timestamp를 연결한다. Mock mapping과 같으면 XR relevance가 강화되고, 안전한 cancel이면 XR claim을 하향한다.
5. **Physical validation은 마지막** — software fix와 두 번째 failure class가 살아남은 뒤에만 controlled robot/safety setup에서 stop consequence를 평가한다. 현재 loopback 수치를 물리 claim으로 확장하지 않는다.

## 16. 사용자 이해용 쉬운 설명

1. **이번에 무엇을 확인했는가?** 사람 A의 예전 로봇 명령 결과가 늦게 돌아오면, 이미 제어권을 받은 사람 B의 현재 명령 handle을 HORUS가 잃어버려 B의 취소가 먹지 않는 현상을 실제 HORUS/Nav2에서 반복 확인했다.
2. **COMPAS에서는 실제 `T_B` 실행까지 됐는가?** 아니다. 다른 내용 `T_B`가 공식 메시지 수신 지점까지는 갔지만, 공개 코드의 그 다음 로봇 실행부가 사용자별 custom integration이라 실제 실행은 확인하지 못했다.
3. **HORUS에서 B의 제어가 실제로 방해받았는가?** 그렇다. A 결과가 나온 뒤 B 공식 취소는 63번 모두 실패했다. 같은 B UUID를 Nav2에 직접 취소하면 실패 사례 67번 모두 정상 취소됐다.
4. **실제 인증된 A/B 사이 scope bypass가 있었는가?** 없었다. 정확히는 실험할 수 있는 실제 공개 후보가 없어서 확인하지 못했다. 인증 없는 client에 임의 role을 붙이는 가짜 공격은 만들지 않았다.
5. **안전한 시스템에서는 같은 공격이 막혔는가?** Test-only COMPAS exact-binding oracle은 잘못된 trajectory/robot/epoch를 막았고, Nav2 exact UUID cancel도 정상 동작했다.
6. **세 결과를 하나의 연구로 묶어도 되는가?** 현재는 아니다. COMPAS chain은 executor 전에 끊기고, scope Track은 threat boundary가 없으며, HORUS만 실제 failure가 남았다.
7. **메이저 학회 Main Item으로 진행할 수 있는가?** 현재 증거로는 어렵다. `WEAK / CASE-STUDY ONLY`다. 두 번째 독립 framework의 actual execution failure가 필요하다.
8. **다음에 사용자가 무엇을 해야 하는가?** 우선 HORUS UUID/generation fix가 이 문제를 완전히 끝내는지 확인하고, 동시에 실제 COMPAS executor artifact를 maintainer에게 확보해야 한다. 둘 중 어느 것도 확장되지 않으면 통합 XR2Act Item을 폐기하고 HORUS case study만 남기는 것이 타당하다.

## 17. Files and Evidence Links

- [XR2Act Results](/home/cclab/ros_xr/XR2ACT_DECISIVE_RESULTS.md)
- [Decisive Summary](/home/cclab/ros_xr/evidence/xr2act_decisive_summary.md)
- [COMPAS E2E Log](/home/cclab/ros_xr/evidence/compas_e2e_execution.log)
- [HORUS Post-Handoff Log](/home/cclab/ros_xr/evidence/horus_post_handoff.log)
- [Bridge Scope Log](/home/cclab/ros_xr/evidence/bridge_scope_bypass.log)
- [Negative Control Log](/home/cclab/ros_xr/evidence/negative_control.log)
- [Reproduction Runner](/home/cclab/ros_xr/authorization_env/run_xr2act_decisive.sh)
- [HORUS Probe](/home/cclab/ros_xr/authorization_env/xr2act_horus_probe.py)
- [COMPAS Runtime Probe](/home/cclab/ros_xr/authorization_env/compas_runtime_probe.py)
- [Scope Audit](/home/cclab/ros_xr/authorization_env/xr2act_scope_audit.py)
- [Research Context](/home/cclab/ros_xr/RESEARCH_CONTEXT.md)

Evidence SHA-256는 [decisive summary](/home/cclab/ros_xr/evidence/xr2act_decisive_summary.md)에 기록했다. Canonical HORUS run ID는 `xr2act-horus-20260827T044120Z`이며 80/80 trial complete, errors 0, cleanup clean이다.
