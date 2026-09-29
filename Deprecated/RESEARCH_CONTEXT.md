# Research Context

## 1. 파일 목적

이 파일은 새로운 Codex 세션에서 현재 연구의 배경, 가설, 진행 상황과 다음 작업을 빠르게 복원하기 위한 문서다.

### 사용 원칙

* 새로운 세션을 시작할 때 먼저 읽는다.
* 단순 명령마다 반복해서 읽을 필요는 없다.
* 연구 방향이 불분명하거나 중요한 설계 결정을 내리기 전에 다시 확인한다.
* 의미 있는 실험 결과, 연구 방향 변경, Phase 완료가 있을 때만 갱신한다.
* 확인된 사실과 아직 검증되지 않은 가설을 반드시 구분한다.
* 사용자가 요청하지 않은 연구 범위로 임의 확장하지 않는다.
* 파일과 디렉터리 구조를 불필요하게 복잡하게 만들지 않는다.

---

# 2. 연구 목표

XR에서 발생한 로봇 제어 명령이 ROS 2로 전달되는 과정에서 다음 권한 정보가 소실되는지 조사한다.

* XR User
* XR Application
* XR Client
* OpenXR Session
* Runtime State
* Control Role
* Robot Scope

최종적으로 확인하려는 핵심 문제는 다음과 같다.

> XR Runtime에서 결정된 User/App/Session의 권한이 XR–ROS Bridge를 통과한 뒤에도 ROS의 실제 Robot Execution Authority까지 보존되는가?

현재 연구 Item은 다음과 같은 **Cross-Domain Authorization 문제**를 대상으로 한다.

* Principal Collapse
* Origin Confusion
* Privilege Laundering
* Session Authority Mismatch
* Session Resurrection

2026-08-27 decisive validation 이후 현재 Status는 **WEAK / CASE-STUDY ONLY**다.

통합 XR2Act Main Item은 현재 증거로 진행하지 않는다. Fixed HORUS Nav2 adapter의 post-handoff ownership race만 강한 framework case로 유지하고, COMPAS는 custom-integration hazard, authenticated scope bypass는 미확인으로 분리한다.

---

# 3. ROS 기본 배경

## ROS

ROS는 `Robot Operating System`의 약자지만 일반적인 운영체제는 아니다.

Linux 위에서 동작하며 로봇의 센서, 경로계획, 판단, 모터제어 등의 기능을 여러 프로그램으로 나눠 서로 통신하게 하는 로봇용 미들웨어 및 개발 프레임워크다.

## 핵심 구성

### Node

하나의 기능을 담당하는 프로그램이다.

예:

* Camera Node
* Navigation Node
* Motor Controller
* Robot Arm Controller
* XR–ROS Bridge

### Topic

Node 사이에서 데이터를 지속적으로 주고받는 Publish/Subscribe 방식이다.

예:

* `/camera`
* `/joint_states`
* `/cmd_vel`

### Service

요청 한 번에 응답 한 번을 반환하는 방식이다.

짧은 설정 변경이나 상태 조회 등에 사용한다.

### Action

시간이 오래 걸리는 작업에 사용한다.

```text
Goal
→ Feedback
→ Result 또는 Cancel
```

예:

* 목적지까지 이동
* Robot Arm Trajectory 수행
* 물체 집기

---

## ROS 2 / DDS / SROS2

ROS 2는 일반적으로 DDS 계열 미들웨어를 사용한다.

SROS2는 DDS Security를 기반으로 다음 기능을 제공한다.

* Authentication
* Encryption
* Access Control
* Topic/Service/Action Permission

SROS2는 주로 ROS Node, DDS Participant 또는 Enclave가 어떤 ROS Resource를 읽거나 쓸 수 있는지 검사한다.

## Enclave

SROS2에서 Security Identity와 Permission을 묶는 단위다.

하나의 DDS Participant 또는 같은 ROS 2 Context를 공유하는 여러 Node는 동일한 Security Identity와 통합된 Permission을 사용할 수 있다.

이러한 구조에서는 여러 기능 또는 여러 upstream client의 권한이 하나의 ROS Identity로 합쳐질 가능성이 있다.

이 구조가 현재 연구의 기술적 출발점이다.

---

# 4. XR–ROS 시스템 구조

XR을 이용한 Robot Teleoperation은 다음과 같은 구조를 사용할 수 있다.

```text
XR Controller
→ XR Application
→ XR–ROS Interface / Bridge
→ ROS 2
→ Planner / Controller
→ Robot
```

공개된 Quest2ROS와 Quest2ROS2 같은 framework는 Quest Controller의 다음 정보를 ROS 또는 ROS 2로 전달한다.

* Pose
* Velocity
* Button Input
* Hand/Controller State

따라서 다음 경로 자체는 실제 존재하는 구조다.

```text
XR
→ Bridge
→ ROS
→ Robot
```

다만 현재 연구실의 기존 WiVRn/Monado 환경이 교수님이 제안한 Shared Bridge 공격 구조와 바로 일치하는지는 확인되지 않았다.

현재 단계에서는 WiVRn을 연구 환경에서 제외하고, 독립적인 ROS 2 + SROS2 환경부터 구축한다.

---

# 5. 교수님 최초 연구 아이디어

## XR–ROS 2 Origin Confusion / Privilege Laundering

교수님이 제안한 기본 가설은 다음과 같다.

XR에서는 서로 다른 권한을 가진 여러 사용자 또는 Client가 존재할 수 있다.

```text
Operator ─┐
Viewer   ─┼→ Shared ROS Bridge → ROS 2 → Robot
Client C ─┘
```

하지만 ROS 2에서 실제 Publisher가 모두 다음과 같이 보일 수 있다.

```text
Publisher = Trusted Bridge
```

이 경우 서로 다른 XR Principal의 차이가 ROS에서 사라질 수 있다.

---

## Principal Collapse

여러 XR 권한 주체가 하나의 Bridge Identity로 합쳐지는 현상이다.

```text
XR Client A ─┐
XR Client B ─┼→ Bridge Identity
XR Client C ─┘
```

## Origin Confusion

ROS에서는 명령을 전달한 Bridge는 알 수 있지만 실제 명령을 생성한 다음 정보는 모를 수 있다.

* User
* XR App
* Client
* Session
* Runtime State
* Control Role

## Privilege Laundering

권한이 없는 XR Client가 권한이 높은 Bridge를 이용해 원래 허용되지 않은 Robot Command를 실행하는 문제다.

예:

```text
Viewer
- Robot State Read: 허용
- Robot Control: 금지

Trusted Bridge
- /cmd_vel Publish: 허용
```

공격 후보:

```text
Viewer
→ Trusted Bridge
→ /cmd_vel
→ Robot
```

SROS2가 실제 Viewer가 아니라 Bridge의 Permission만 검사하면 명령이 허용될 가능성이 있다.

---

# 6. 핵심 Motivating Example

## 실험 A: Direct ROS Access

Low-Privilege ROS Principal이 직접 Robot Control Topic에 접근한다.

```text
Low-Privilege ROS Principal
→ /cmd_vel
→ SROS2
→ BLOCK
```

## 실험 B: Bridge-Mediated Access

동일한 Logical Command를 Low-Privilege External Client가 Trusted Bridge를 통해 전달한다.

```text
Low-Privilege XR/External Client
→ Trusted Bridge
→ /cmd_vel
→ SROS2
→ ALLOW?
```

두 번째 실험이 성공하면 다음을 보여줄 수 있다.

> SROS2가 실패한 것이 아니라, SROS2가 권한을 검사하기 전에 실제 upstream principal이 Bridge Identity로 변환되었다.

이 대조 실험이 첫 번째 GO/NO-GO 기준이다.

---

# 7. 추가 공격 가설

## 7.1 Session Authority Mismatch

XR에서 제어 권한이 종료된 시점과 ROS에서 Robot Control Authority가 종료되는 시점이 다를 수 있다.

```text
XR Session
→ Focus Loss / Logout / Session 종료
→ XR Control Authority 종료

하지만

Bridge SROS2 Identity
→ Robot Control Permission 유지?
```

핵심 질문:

> XR에서 제어권이 종료된 뒤에도 ROS Bridge 또는 기존 Action이 계속 Robot을 제어할 수 있는가?

---

## 7.2 Session Resurrection

다음 사건 이후 과거 Command, Queue 또는 Action Goal이 다시 사용되는지 확인한다.

* TCP Disconnect
* Reconnect
* OpenXR Focus Loss
* OpenXR Session 종료
* Logout
* Role Revocation
* Application 종료

확인할 항목:

* 종료 후 수용된 Command 수
* 종료 후 Robot 이동시간 또는 이동거리
* 진행 중 Action 지속 여부
* 이전 Session의 Sequence 또는 Command 재사용 여부

---

## 7.3 Cross-Robot Retargeting

사용자는 `robot1`만 제어할 수 있지만 Shared Bridge가 `robot1`과 `robot2` 모두의 권한을 가진 경우를 가정한다.

```text
User Permission
- robot1: 허용
- robot2: 금지

Bridge Permission
- robot1: 허용
- robot2: 허용
```

Client가 Topic 또는 Namespace를 다음과 같이 변경했을 때 Robot 2 명령이 실행되는지 확인한다.

```text
/robot1/cmd_vel
→ /robot2/cmd_vel
```

이 공격은 별도 핵심 Contribution보다는 Privilege Laundering의 변형으로 다룬다.

---

# 8. 선행연구 검토 결과

## SROS2

ROS 2의 Authentication, Encryption, Access Control을 제공한다.

주요 보호 대상은 ROS/DDS Participant, Node, Enclave와 ROS Resource 사이의 권한이다.

### 현재 연구와의 차이

SROS2 자체를 공격하는 것이 아니다.

SROS2가 권한을 검사할 때 이미 upstream XR Principal 정보가 Bridge Identity로 축약될 가능성을 연구한다.

---

## ROSAuth

Remote non-ROS Client를 인증하기 위한 MAC, Timestamp, Expiration 기반 구조가 이미 제안됐다.

### 의미

다음 자체는 Novelty가 아니다.

* Remote Client Token
* JWT
* MAC
* Timestamp
* Expiration
* Replay Protection

---

## Application-Level Security for ROS

별도의 Authorization 구조를 이용해 허가된 ROS Application 또는 Node만 참여하도록 제한하는 연구가 존재한다.

### 의미

다음 자체도 Novelty가 아니다.

* Authorization Server
* Whitelist
* Application Authentication
* Application-Level Encryption

---

## Policy-Based Access Control

Application 또는 Node별로 Topic/Service Resource Permission을 관리하고 Runtime Permission Revocation을 수행하는 연구가 존재한다.

### 의미

다음 정도만으로는 Contribution이 부족하다.

```text
App A
→ /cmd_vel 허용

App B
→ /cmd_vel 금지
```

---

## Attribute-Based Access Control for Multi-Robot Systems

User Attribute와 Robot Attribute를 이용한 ABAC, Multi-Robot Control, User Conflict 처리 연구가 존재한다.

### 의미

다음 자체를 Novelty로 주장하기 어렵다.

* User별 Robot Permission
* Robot별 Topic ACL
* Attribute 기반 접근제어
* 다중 사용자 Robot Control 중재

---

## Quest2ROS / Quest2ROS2

Quest Controller 데이터를 ROS 또는 ROS 2에 전달해 실제 Robot Teleoperation에 사용하는 framework다.

### 의미

다음 경로가 실제 존재함을 보여준다.

```text
XR Client
→ Network Bridge
→ ROS / ROS 2
→ Robot
```

다만 기존 framework의 핵심 목적은 Teleoperation과 Robot Learning Data Collection이며 Cross-Domain Authorization은 주된 연구 대상이 아니다.

---

# 9. 수정된 Research Gap

교수님 원안을 그대로 사용하면 기존 인증 및 접근제어 연구와 겹칠 수 있다.

따라서 연구 문제를 단순 User Authorization이 아니라 다음과 같이 좁힌다.

> XR Runtime에서 변하는 User/App/Session Authority가 Bridge를 통과해 ROS의 실제 Robot Execution Authority까지 의미적으로 보존되는가?

구조:

```text
XR User
+ XR App
+ XR Session
+ Runtime State
+ Robot Scope
        ↓
XR–ROS Bridge
        ↓
ROS Authorization
        ↓
Robot Execution
```

핵심은 **Cross-Domain Authorization Binding**이다.

---

# 10. 현재 연구 질문

## RQ1. Architecture

공개 XR–ROS Bridge에서 다음 identity 중 무엇이 ROS까지 전달되고 무엇이 소실되는가?

* Client
* User
* App
* Session
* Robot
* Control Role

## RQ2. Privilege Laundering

SROS2가 활성화된 상태에서도 Low-Privilege External Client가 Trusted Bridge의 ROS Permission을 이용할 수 있는가?

## RQ3. Session Authority

XR Focus Loss, Logout, Disconnect 또는 Session 종료 이후에도 Robot Command나 Action이 수용되는가?

## RQ4. Existing Defense

다음 기존 방법만으로 문제가 완전히 해결되는가?

* Bridge-local ACL
* PBAC
* ABAC
* Per-client Bridge
* Per-client SROS2 Enclave
* ROSAuth/JWT/mTLS

## RQ5. New Defense

기존 방법으로 충분히 해결되지 않는다면 XR Runtime Authority를 Robot Actuator 실행 시점까지 결합하는 별도 Reference Monitor가 필요한가?

---

# 11. 연구 Phase

## Phase 0. ROS 2 환경 구축

목표:

* ROS 2 Humble 환경 구축
* SROS2 설치 및 기본 동작 확인
* Topic Publish/Subscribe 확인
* 이후 실험을 위한 Workspace 준비

현재 단계에서는 다음을 하지 않는다.

* XR 연동
* WiVRn 연동
* Quest 연동
* Quest2ROS2 설치
* ROS-TCP 공격 실험
* ORBIT 구현
* eBPF 구현

---

## Phase 1. Bridge Architecture 분석

후보:

* Quest2ROS2의 ROS-TCP 구조
* Unity ROS-TCP-Endpoint
* rosbridge_suite

확인할 항목:

* 여러 Client Connection을 받을 수 있는가?
* Connection별 Client Identity가 존재하는가?
* 인증된 User/App Identity를 저장하는가?
* Client별 Publisher를 사용하는가?
* 여러 Client가 동일 ROS Publisher를 공유하는가?
* Client가 Topic/Service/Action Destination을 선택할 수 있는가?
* ROS에서는 어떤 Node/Enclave Identity로 보이는가?
* Disconnect 시 Publisher, Queue, Action Goal이 정리되는가?

---

## Phase 2. 최소 SROS2 PoC

실제 Robot 대신 Dummy Controller 또는 Simulation을 사용한다.

```text
Low-Privilege ROS Node
→ /cmd_vel
→ BLOCK
```

```text
Low-Privilege External Client
→ Trusted Bridge
→ /cmd_vel
→ ALLOW?
```

이 결과로 첫 번째 연구 가설을 판단한다.

---

## Phase 3. Multi-Client / Session 실험

* Operator와 Viewer 권한 분리
* Viewer의 Unauthorized Command
* Disconnect 이후 Command
* Reconnect 이후 이전 Session Command
* Action Goal 지속 여부
* Cross-Robot Retargeting

---

## Phase 4. 기존 방어 비교

다음 Baseline을 비교한다.

1. SROS2 Only
2. Client Authentication + SROS2
3. Bridge-local ACL/PBAC/ABAC
4. Per-client Bridge Process
5. Per-client SROS2 Enclave
6. 제안 방어 구조

기존 방법이 모든 공격을 낮은 비용으로 해결한다면 새로운 방어 시스템의 필요성이 약해진다.

---

## Phase 5. 방어 시스템 설계

다음 세 조건이 모두 확인된 뒤에만 진행한다.

1. 실제 Principal Collapse 또는 Session Authority Mismatch 존재
2. Robot Command 실행으로 이어지는 Physical Impact 존재
3. 기존 ACL/ABAC/Per-client Enclave만으로 완전히 해결되지 않음

작업명 후보:

> ORBIT: Origin-Bound Authorization for XR-to-ROS 2 Control

예상 구조:

```text
XR Runtime / Origin Authority
→ Session-Bound Capability
→ XR–ROS Bridge
→ ORBIT Guard
→ Robot Controller
```

Bridge에는 실제 Robot Actuator 권한을 직접 주지 않고 Guard만 최종 권한을 갖도록 한다.

---

## Phase 6. eBPF/LSM 적용 여부 판단

eBPF 자체를 Novelty로 주장하지 않는다.

eBPF/LSM은 다음 문제가 실제 확인될 때만 사용한다.

* Bridge가 Guard를 우회해 Controller에 직접 접근
* User-space 정책 집행 우회
* 특정 DDS/Socket/IPC 경로의 Kernel-Level 차단 필요
* 저오버헤드 Audit 필요

가능한 역할:

```text
Origin 생성
→ OpenXR / Authorization Layer

Authorization 판단
→ ORBIT Guard

Bypass Prevention / Audit
→ eBPF / LSM
```

---

# 12. GO / NO-GO 기준

## GO

다음이 확인되면 연구 Item을 계속 진행한다.

* 실제 Bridge에서 XR/External Client Identity가 ROS Identity로 축약됨
* Direct ROS Command는 SROS2가 차단
* 동일 Command를 Bridge로 전달하면 허용
* Session 종료 또는 권한 회수 후 Stale Authority 존재
* 기존 ACL/ABAC/Per-client Enclave로 완전히 해결되지 않음
* 실제 Robot 또는 Simulation에서 Physical Impact 확인 가능

## NO-GO 또는 방향 수정

다음 결과가 나오면 현재 Item을 재검토한다.

* 공격이 인증되지 않은 Open Port에만 의존
* 단순 Topic Allowlist로 완전히 해결
* Client별 Enclave가 낮은 비용으로 모든 문제 해결
* 실제 Bridge가 Client Identity를 이미 종단 간 보존
* Session 종료 시 모든 Command/Action이 즉시 안전하게 중단
* 현재 공격 구조가 공개 framework가 아닌 인위적 설정에서만 가능
* Physical Impact 없이 단순 Message Injection만 확인

---

# 13. 현재 환경 결정

## 현재

* ROS 2 Humble + SROS2 bridge baseline
* ROS 2 Jazzy + actual HORUS backend/Nav2 adapter feasibility
* Docker 기반 격리 환경
* Actual Nav2 + `nav2_loopback_sim` simulated robot

## 현재 제외

* WiVRn
* Monado
* Quest 3
* OpenXR Application
* XR Runtime State 연동

기존 XR 환경은 폐기한 것이 아니라, ROS 2와 Bridge 구조가 확인된 이후 필요한 경우 다시 연결한다.

현재는 다음을 가정하지 않는다.

* Linux + Monado + Quest 3 + ROS 2가 이미 통합되어 있음
* 기존 WiVRn 환경에 Shared ROS Bridge가 존재함
* 현재 연구실 환경에서 즉시 공격 재현 가능
* eBPF가 반드시 필요함

---

# 14. 다음 작업

ROS 2/SROS2, generic rosbridge, Quest2ROS2, HORUS, COMPAS XR의 fixed-revision checkpoint와 XR2Act decisive validation까지 완료됐다.

다음 연구 작업은 우선순위대로 다음이다.

1. HORUS `Nav2ActionAdapter`에 Goal UUID/generation별 result correlation을 적용하는 최소 fix를 만들고 동일 8-mode × 10-trial regression, pending goal, multi-robot selectivity를 검증한다.
2. Maintainer-linked COMPAS XR Grasshopper/CAD → ROS/MoveIt/RRC/RTDE executor artifact를 확보해 승인 `T_A`와 final executor input을 비교한다.
3. 실제 서로 다른 credential과 Robot/Action scope를 제공하는 maintained shared bridge가 발견될 때만 authenticated Track C를 재개한다.
4. Matching HORUS multi-operator Quest/OpenXR build를 확보한 뒤 focus/pause/session stop과 lease/release/action cancel timestamp를 연결한다.
5. 두 번째 독립 failure class가 살아남기 전에는 physical robot, ORBIT, eBPF/LSM 또는 full XR2Act defense를 시작하지 않는다.

핵심 kill/pivot 조건:

```text
Goal UUID/generation local fix가 HORUS race를 완전히 해결하고,
대표 COMPAS integration이 승인 content/version과 execution을 검증하며,
실제 authenticated shared-bridge scope 후보를 확보하지 못한다면
통합 XR2Act Main Item은 폐기하고 HORUS Nav2 case study만 유지한다.
```

---

# 15. 현재 진행 상황

## 완료

* ROS 기본 개념 정리
* 교수님 최초 아이디어 구조화
* Principal Collapse / Origin Confusion / Privilege Laundering 개념 정리
* 관련 ROS Security 및 XR–ROS Teleoperation 선행연구 예비 검토
* 단순 인증/ACL/ABAC만으로는 Novelty가 부족하다는 점 확인
* Research Gap을 Cross-Domain Authorization Binding으로 수정
* 초기 연구 Status를 CONDITIONAL GO로 결정했으며 이후 decisive validation에서 하향
* WiVRn을 현재 ROS 환경 구축 단계에서 제외
* Phase 0 ROS 2 Humble + SROS2 환경 구축 및 Pub/Sub 검증
* SROS2 Enforce 기준 실험과 rosbridge 최소 Feasibility PoC
* Quest2ROS2와 maintained `ros_tcp_communication` fixed revision 정적 분석
* `quest2ros`, `ros_tcp_endpoint`, `q2r2_bringup`, `origin_test` Humble build/import
* 실제 ROS–TCP framing emulator, SROS2 대조, multi-client와 publisher lifecycle 검증
* HORUS ROS 2 `main@eca75cbf`와 관련 공개 repository fixed revision 확보 및 Jazzy 4-package build
* HORUS 정상 lease arbitration, no-lease, self-asserted identity metadata, protected catalog control-plane runtime 검증
* HORUS real backend/Nav2 adapter와 dummy action server를 이용한 release/expiry/disconnect 중 accepted-goal lifecycle 검증
* COMPAS XR `main@b86e6fb`와 Unity Assembly `main@f1516ca` protocol/state/execution-handoff 추적
* COMPAS official message/transport와 loopback MQTT를 이용한 T_A approval → T_B handoff 및 identity/duplicate-message 검증
* 기존 연구 collision 확인과 Authorization Continuity 후보의 범위 축소
* HORUS explicit cancel, release, TTL expiry, disconnect를 각 5회·10초 checkpoint로 반복한 결정적 장시간 실험
* HORUS lease handoff 뒤 A/B distinct Nav2 Goal의 동시 active 상태를 5/5 runtime으로 확인
* Test-only robot-wide cancel hook의 nominal coverage와 wrong-latest-goal cancel selectivity 실패를 각각 5회 검증
* COMPAS XR official GHX/component 실행 경계를 재감사해 final controller가 custom integration인 Case C로 확정
* OpenXR-style mock → actual HorusLink/HORUS → actual Nav2 `NavigateToPose` → `nav2_loopback_sim` end-to-end F0–F6를 각 5회 검증
* Actual Nav2 explicit cancel 5/5, release/disconnect 뒤 5초 Goal 지속, TTL 뒤 자연 완료까지 이동, handoff preemption 5/5 확인
* XR2Act COMPAS authenticated loopback에서 normal `T_A` 및 A1–A4 `T_B` official handoff 검증; public final executor 부재로 robot input은 미확인
* Actual HORUS/HorusLink/Nav2 post-handoff timing 8개 mode × 10회, 총 80/80 완료
* A late-result publication 이후 B official cancel 0/63, 전체 official cancel 3/70, 실패 후 same-UUID direct cancel 67/67 성공
* 독립 exact-UUID cancel negative control 10/10 및 COMPAS exact digest/robot/epoch/approver reference control PASS
* Authenticated per-principal Robot/Action scope와 shared ROS authority를 동시에 갖춘 real Track C 후보 부재 확인; synthetic attack 미수행
* Existing-work claim collision 재검토 후 통합 Item을 `WEAK / CASE-STUDY ONLY`로 하향

## 현재 Phase

```text
Phase 1–3 기존 Bridge/SROS2/Quest2ROS2 checkpoint 완료
HORUS Nav2 revocation 장시간·반복·handoff·minimal-fix checkpoint 완료
Mock XR → actual HORUS → actual Nav2 loopback consequence checkpoint 완료
COMPAS public executor boundary는 Case C로 확정
XR2Act decisive validation 완료: HORUS post-handoff race confirmed, COMPAS secondary, Track C unavailable
통합 Main Item은 WEAK / CASE-STUDY ONLY
```

## 다음 Phase

```text
HORUS Goal UUID/generation-aware 최소 fix와 동일 timing regression
maintainer-linked COMPAS final executor 확보
실제 authenticated scope-bound shared bridge가 발견될 때만 Track C 재개
```

## 확인된 사실

* SROS2 Enforce mode에서 `/authorized`의 `/cmd_vel` publish는 허용되고 `/low`는 deny rule로 차단됐다.
* Low direct와 동일한 `Twist` 값을 External Client가 rosbridge로 보내면 `/trusted_bridge` 권한으로 전달됐다.
* 두 WebSocket Client는 ROS graph에서 개별 node가 아니며 하나의 `/rosbridge_websocket` publisher와 `/trusted_bridge` enclave로 관찰됐다.
* SROS2는 Bridge 이전의 External Client가 아니라 실제 ROS/DDS principal인 Bridge identity를 기준으로 정책을 집행했다.
* Quest2ROS2 `main@07aaf651`과 ros_tcp_communication `main@5c5f089`의 ROS-side package 4개가 source patch 없이 Humble container에서 build/import됐다.
* Quest2ROS2가 선언한 Topic `/q2r_right_hand_twist`의 ROS-side 경로에서 `/low` direct `0.440`은 차단되고 같은 값이 TCP Endpoint를 거치면 `/trusted_quest_bridge` 권한으로 전달됐다.
* A가 등록한 server-global publisher를 별도 TCP Client B가 재등록 없이 사용했으며, A/B 명령은 publisher 1개와 동일 GID로 관찰됐다.
* 모든 TCP Client 종료 후에도 publisher/GID가 남았고 reconnect Client가 재등록 없이 이를 재사용했다.
* 같은 Topic 재등록은 publisher를 교체해 GID를 바꿨으며, Endpoint 종료 후에야 publisher가 제거됐다.
* 두 target repository에는 Client authentication, Viewer/Operator role 또는 Client별 ROS principal mapping이 없다.
* HORUS 정상 lease에서 A command는 ALLOW, A lease 중 B command는 BLOCK, A release 뒤 B acquire/publish는 ALLOW였다.
* HORUS protected topic은 active lease가 없을 때 command를 ALLOW했고, `app_id`, `role`, `session_id`는 client assertion으로 수용됐다.
* HORUS catalog handler는 client가 주장한 `host` role의 clear를 수용했고, clear 전 BLOCK된 B command가 clear 뒤 ALLOW됐다.
* HORUS backend/Nav2 adapter가 수락한 goal은 explicit release, 1200 ms TTL expiry, client disconnect 뒤 각각 1.0 s, 0.7 s, 1.0 s 관찰창 동안 active였고 action server cancel request는 0이었다.
* 2026-08-26 decisive follow-up에서 HORUS 공식 cancel은 5/5 동일 Goal UUID를 cancel해 `CANCELED`로 종료됐다.
* Unmodified HORUS release/TTL expiry/disconnect는 각각 5/5에서 cancel 0이었고, accepted Goal은 모든 0.5/1/3/5/10초 checkpoint에서 `EXECUTING`이었다.
* HORUS handoff는 5/5에서 B lease와 distinct B Goal을 수락했으며 A/B Goal이 10초 동안 동시에 active였다. 이는 multi-goal dummy server의 software 결과이며 physical collision 증거가 아니다.
* Test-only robot-wide/latest-handle cancel hook은 nominal R1–R4를 5/5 정리했지만, selectivity challenge에서는 5/5 unrelated latest Goal을 잘못 cancel하고 lease-owned A Goal을 남겼다.
* Fixed HORUS public backend의 official Action adapter는 Nav2 `NavigateToPose` 하나뿐이어서 second Action runtime은 수행하지 않았다.
* HORUS 두 client command는 ROS graph에서 `/horus_unity_bridge` publisher endpoint 하나로 관찰됐다. 이번 HORUS run 자체에는 SROS2를 적용하지 않았다.
* COMPAS XR `trajectory_id`는 `element_id` 기반이며 서로 다른 T_A/T_B content가 같은 ID를 가졌다.
* COMPAS XR `SendTrajectory`에는 approval digest, content version, approver set 또는 authorization epoch가 없다.
* T_A approval 뒤 T_B는 official message/`compas_eve` transport를 사용하는 inert handoff subscriber까지 자동 equality/digest reject 없이 도달했다.
* 공개 COMPAS XR fixed repository에는 완성된 ROS/MoveIt/RTDE robot executor가 없고 최종 execution은 custom integration 경계다.
* Official COMPAS GHX/component 재감사에서도 downstream output은 element/robot뿐이고 robot control은 RRC/RTDE/UR Script placeholder였다. Executor 판정은 Case C다.
* Canonical run `xr-nav2-20260826T125755Z`에서 OpenXR-style mock F0–F6 총 35/35 trial이 measurement complete 및 cleanup clean으로 끝났다.
* Actual HORUS `Nav2ActionAdapter`와 actual Nav2 `NavigateToPose`를 사용했고, robot plant만 `nav2_loopback_sim`으로 대체해 `/odom` polyline 이동거리를 측정했다.
* F0 explicit cancel은 5/5 `CANCELED`였고 cancel 뒤 추가 이동 중앙값은 0.079426 m, 0.5초 정지 hold를 포함한 stop latency 중앙값은 738.931 ms였다.
* F2 lease release와 F3 disconnect는 lease 제거 후 cancel topic/Nav2 `CANCELING`/terminal/stop이 5/5 없었고, 5초 추가 이동 중앙값은 각각 2.363350 m와 2.359485 m였다.
* F4 TTL expiry도 cancel 0/5였으며 Goal은 5/5 자연 `SUCCEEDED`할 때까지 expiry 후 중앙값 1.757236 m 이동했다.
* F5에서는 stock Nav2가 5/5 B Goal로 A를 preempt해 A `ABORTED`, B `EXECUTING`이 됐다. Dummy server의 A/B 동시 active는 일반화되지 않지만 B 도착 전 F2–F4 revocation gap은 actual Nav2에서도 유지된다.
* F5 측정 뒤 supporting cleanup check에서 B의 ordinary HORUS cancel은 0/5였고 direct Action cancel-all만 B UUID를 5/5 정리했다. Fixed adapter의 single `active_goal_handle`가 A의 late result에서 reset되는 source 구조와 일치하며 production fix 증거는 아니다.
* F6에서는 Goal command에 session/lease epoch field가 없었고, B 소유 중 old client command는 차단됐지만 B release 뒤 old logical session ID 재획득과 Goal 수락이 5/5 가능했다. 이는 cryptographic replay나 authentication bypass 증거가 아니다.
* Canonical run `xr2act-horus-20260827T044120Z`는 actual HorusLink/HORUS/Nav2와 loopback plant에서 80/80 trial, error 0으로 완료됐다.
* 모든 trial에서 A/B Goal UUID는 unique했고 B가 새 lease와 Goal을 획득했다.
* A result publication 뒤의 B official HORUS cancel은 0/63 성공이었다. Accept 직후 race까지 포함하면 official cancel은 3/70 성공, post-handoff interference는 67/70이었다.
* Official path 실패 67회에서 동일 B UUID의 direct Nav2 cancel은 67/67 `CANCELED`를 만들었다. 독립 direct control도 10/10 성공했다.
* Official failure 후 exact rescue 전 0.75초 동안 loopback odometry path는 0.095100–0.378623 m, 중앙값 0.177091 m였다. 이는 physical distance가 아니다.
* Fixed adapter source는 robot별 `active_goal_handle` 하나를 두고 각 result callback에서 Goal identity 비교 없이 reset한다.
* COMPAS local broker는 credential authentication을 요구했고 normal `T_A`, same-ID `T_B`, cross-robot `T_B`, stale-approval `T_B`가 official subscriber에 도달했다. Final robot/executor input은 여전히 미확인이다.
* Test-only COMPAS exact-binding oracle은 normal A만 허용하고 same-ID/cross-robot/stale-epoch B를 모두 거부했다.
* 실제 credential-bound A/B Robot/Action scope를 가진 public shared XR–ROS bridge candidate는 확인하지 못했다. Track C attack은 수행하지 않았다.

## 아직 확인되지 않은 가설

* Quest2ROS2 target tree에 실제 Quest/Unity app source가 없어 app의 registration, device identity, authentication과 session metadata는 확인되지 않았다.
* B의 무등록 global registry 사용은 Endpoint가 허용하는 protocol probe이며 실제 Quest app reconnect 절차와 동일하다고 확인하지 않았다.
* Twist는 framework-native Topic이지만 current arm controller는 Pose와 Inputs를 사용하므로 robot actuation과 physical impact는 확인되지 않았다.
* Authenticated Viewer/Operator privilege laundering, Focus Loss, full Session Resurrection, 기존 방어 우회 및 최종 novelty는 확인되지 않았다.
* 실제 HORUS Quest/OpenXR focus loss가 lease와 accepted action에 미치는 영향은 확인되지 않았다.
* HORUS의 bounded test 결과가 실제 robot의 physical stop 부재를 의미하는지는 확인되지 않았다.
* Nav2 외 second Action/framework의 revocation behavior는 확인되지 않았다.
* 실제 Quest/OpenXR runtime의 focus/pause/STOPPING event가 이번 mock의 P2 release/disconnect 정책과 동일하게 연결되는지는 확인되지 않았다.
* Loopback odometry가 실제 physical robot의 제동거리, 충돌 위험 또는 safety-controller 동작을 예측하는지는 확인되지 않았다.
* Owner/lease epoch/Goal UUID를 결합한 production-oriented fix의 pending-goal race, late-result isolation, multi-robot correctness는 확인되지 않았다.
* COMPAS XR 대표 custom executor에서 T_B가 검증 없이 실제 실행되는지는 확인되지 않았다.
* COMPAS Unity binary의 duplicate vote, reconnect, timeout, mobile focus behavior는 확인되지 않았다.
* 두 independent framework의 end-to-end physical authorization failure와 전체 novelty는 확인되지 않았다.
* HORUS post-handoff race가 Nav2 이외 adapter, 다른 framework 또는 actual Quest lifecycle에서도 재현되는지는 확인되지 않았다.
* Real authenticated multi-principal shared bridge에서 cross-principal scope bypass가 가능한지는 확인되지 않았다.

## 이번 checkpoint에서 기각 또는 하향된 가설

* Quest2ROS2가 authenticated Viewer/Operator privilege laundering을 이미 증명한다는 가설은 기각했다.
* HORUS의 `app_id`, `role`, `session_id`가 authenticated server-side principal이라는 가설은 현재 source/runtime에서 기각했다.
* HORUS protected topic이 active lease 없이는 항상 BLOCK된다는 가설은 기각했다.
* COMPAS XR `trajectory_id`가 exact trajectory content/version을 고유하게 식별한다는 가설은 기각했다.
* 공개 COMPAS XR 자체가 complete robot executor를 제공하고 T_B physical execution까지 확인됐다는 가설은 기각했다.
* 기존 HORUS 0.7–1.0초 결과가 단순 asynchronous cancel delay라는 가설은 5회·10초 cancel 0 결과로 기각했다.
* Robot-wide/latest-handle cancel 한 줄이 owner-selective production fix라는 가설은 wrong-goal cancel 5/5로 기각했다.
* generic Authorization Continuity, bridge authentication, runtime revocation 또는 trajectory integrity 자체를 최초 기여로 주장하는 방향은 prior-art collision 때문에 하향했다.
* COMPAS A1–A4 official handoff acceptance가 actual unauthorized actuation이라는 가설은 final executor 부재로 하향했다.
* 실제 authenticated scope boundary 없이 identity collapse만으로 privilege laundering을 주장하는 Track C는 기각했다.
* 세 Track이 하나의 검증된 universal XR2Act invariant를 이룬다는 가설은 현재 evidence에서 기각했다.

## 현재 판단

Generic/Quest2ROS2 identity-collapse와 기존 HORUS revocation-gap baseline은 유지된다. 새 decisive result는 fixed HORUS Nav2 adapter의 post-handoff ownership race다. A의 late result 뒤 B official cancel은 0/63 성공했고, 같은 B UUID direct cancel은 failure rescue 67/67에서 성공했다. 이는 actual HORUS/Nav2 software path의 강한 Security Property Violation이지만 loopback simulation이고 한 adapter의 single-handle/result-correlation 오류로 좁혀진다.

COMPAS XR는 A1–A4가 official handoff까지 도달했지만 final controller가 custom이라 Integration Hazard다. 실제 authenticated scope-bound shared bridge 후보도 확보하지 못했다. Negative controls는 안전한 구성을 정확히 구분했지만 새 defense contribution은 아니다.

따라서 전체 연구 Item은 **WEAK / CASE-STUDY ONLY**다. 추천 범위는 **HORUS post-handoff Goal ownership case study**이며 XR2Act 통합 Main Item은 보류한다. Maintainer-linked COMPAS executor에서 두 번째 failure class가 확인되거나 다른 independent Action/framework에서 같은 ownership failure가 재현될 때만 `CONDITIONAL GO`를 다시 검토한다.

---

# 16. 연구 작업 규칙

* 공격이 확인되기 전에 ORBIT를 구현하지 않는다.
* 기존 방어와 비교하기 전에 Novelty를 확정하지 않는다.
* SROS2 자체의 취약점이라고 표현하지 않는다.
* 인증되지 않은 TCP Port 공격을 핵심 Contribution으로 삼지 않는다.
* User/App/Session Origin을 사용자의 실제 물리적 의도 증명으로 과장하지 않는다.
* AI Delegation, FrameShift, SplitSight, Demonstration Poisoning은 첫 연구 범위에서 제외한다.
* 새로운 논문 또는 구현을 확인할 때 현재 Gap과 직접 관련 있는지 먼저 판단한다.
* 논문 인용 전 제목, 저자, 연도, Venue 및 실제 내용을 다시 검증한다.
* 의미 있는 실험 결과는 성공과 실패 모두 기록한다.
* 사용자가 요청하지 않은 구현, 리팩터링, 파일 생성 또는 연구 범위 확장을 하지 않는다.

---

# 17. Progress Log

* 교수님으로부터 XR–ROS 2 Origin Confusion / Privilege Laundering 연구 아이디어 전달받음.
* ROS, ROS 2, SROS2, DDS Participant 및 Enclave 기본 구조 조사.
* ROSAuth, Application-Level Security, PBAC, ABAC, Quest2ROS 계열 Related Work 예비 검토.
* 원안을 단순 User Authorization이 아닌 XR Runtime Authority와 ROS Robot Execution Authority 사이의 Cross-Domain Binding 문제로 수정.
* 현재 연구 Item을 CONDITIONAL GO로 판단.
* 기존 WiVRn 환경은 현재 ROS 환경 구축 작업에서 제외.
* Phase 0 시작 당시 다음 작업은 ROS 2 Humble + SROS2 환경 구축 및 기본 Pub/Sub 검증이었음.
* 완료 날짜: 2026-08-25
  * Docker build 성공 여부: 성공.
  * ROS 2 실행 확인 여부: 성공.
  * SROS2 package 확인 여부: 성공.
  * Publish/Subscribe smoke test 결과: 성공 — Talker/Listener 메시지 수신 확인.
  * Blocker: 없음.
* 2026-08-25 SROS2/Bridge 최소 Feasibility PoC
  * Phase 1 SROS2 기준: Authorized ALLOW / Low-Privilege BLOCK.
  * Phase 2 Bridge Identity: `/rosbridge_websocket`와 `/trusted_bridge`로 축약.
  * Phase 3 핵심 PoC: Direct BLOCK / Bridge-mediated ALLOW.
  * Multi-client 관찰: Client A/B가 publisher 1개와 동일 endpoint GID를 공유.
  * 판단: 최소 Feasibility GO, 전체 연구 Item CONDITIONAL GO.
  * 다음 단계: 실제 XR–ROS Bridge와 client별 authorization baseline 분석.
* 2026-08-25 Quest2ROS2 ROS–TCP fixed-revision validation
  * Quest2ROS2 `07aaf651`과 ros_tcp_communication `5c5f089`을 분석·build.
  * Quest2ROS2가 선언한 Twist Topic의 ROS-side 경로에서 Direct Low BLOCK / Trusted Endpoint ALLOW.
  * A/B는 server-global publisher와 동일 GID를 공유했고 ROS Client Node는 생성되지 않음.
  * 모든 Client 종료 뒤 publisher가 남아 무등록 reconnect에 재사용됨.
  * 동일 Topic 재등록 시 publisher GID rotation, Endpoint 종료 시 cleanup 확인.
  * Framework에 authentication/Role이 없어 결과를 unauthenticated trust/principal collapse로 수정.
  * 판단: ROS-side feasibility GO, authenticated privilege laundering NOT ESTABLISHED, 전체 CONDITIONAL GO.
  * 다음 단계: 실제 Quest app source/revision 또는 wire capture로 upstream identity boundary 확인.
* 2026-08-26 HORUS / COMPAS XR Authorization Continuity checkpoint
  * HORUS ROS 2 `eca75cbf`, HORUS `819cdfdc`, HORUS SDK `f4f00dab`을 고정하고 isolated Jazzy build/runtime 검증.
  * 정상 lease arbitration PASS; no-lease command ALLOW; identity metadata와 catalog authority가 client assertion임을 source/runtime으로 확인.
  * real HORUS backend/Nav2 adapter를 통한 accepted goal 3개가 release/expiry/disconnect 뒤 bounded window에서 계속 active, cancel request 0.
  * COMPAS XR `b86e6fbb`, Unity Assembly `f1516ca`를 고정하고 official schema/transport + local broker + inert sink 검증.
  * 서로 다른 T_A/T_B가 같은 element-derived ID를 가졌고 T_A approval 뒤 T_B가 automatic content reject 없이 handoff까지 도달.
  * COMPAS final robot executor는 custom integration이므로 physical execution은 NOT VERIFIED.
  * broad Authorization Continuity/bridge auth/revocation/trajectory integrity prior art collision을 확인해 claim을 좁힘.
  * 판단: HORUS strong runtime + COMPAS conditional handoff, 전체 **CONDITIONAL GO**.
  * 다음 단계: actual HORUS Quest focus lifecycle과 representative COMPAS execution integration.
* 2026-08-26 Decisive XR–ROS Authorization follow-up
  * HORUS explicit cancel과 R1 release/R2 TTL/R3 disconnect를 각 5회, 32초 Goal과 10초 observation으로 실행.
  * Explicit cancel 5/5 성공; R1/R2/R3는 각각 cancel 0/5이고 10초 checkpoint까지 `EXECUTING`.
  * R4 handoff 5/5에서 B Goal 수락, A/B 동시 active, cancel/preemption 0.
  * Test-only cancel hook은 nominal R1–R4를 정리했지만 F1 5/5에서 unrelated latest Goal을 잘못 cancel.
  * Fixed HORUS에는 second official Action adapter가 없어 Nav2-specific limitation으로 기록.
  * COMPAS official executor boundary는 Case C; physical execution은 `UNCONFIRMED`, track은 secondary evidence.
  * 판단: **CONDITIONAL GO** 유지. 다음 단계는 owner/epoch/Goal UUID 최소 prototype, actual Quest focus trace, second Action/framework.
* 2026-08-26 XR Mock → actual HORUS → actual Nav2 feasibility
  * 실제 Quest/OpenXR hardware 대신 deterministic OpenXR-style lifecycle state machine으로 P1/P2 event를 만들었다. 이는 실제 Quest event 증거가 아니다.
  * Canonical run `xr-nav2-20260826T125755Z`에서 F0–F6 각 5회, 총 35/35가 measurement complete 및 cleanup clean이었다.
  * F0 explicit cancel 5/5 성공. F2 release/F3 disconnect 뒤 cancel 없이 5초간 Goal이 `EXECUTING`했고 odom 추가 이동 중앙값은 2.363350 m/2.359485 m였다.
  * F4 TTL은 cancel 없이 5/5 자연 완료했고 expiry 후 중앙값 1.757236 m 이동했다.
  * F5 actual Nav2는 B가 A를 5/5 preempt했다. Dummy의 동시-active 결과는 stock Nav2로 일반화되지 않지만 F2–F4 revocation gap은 유지된다.
  * F6는 epoch capability probe이며 cryptographic replay/authentication bypass를 입증하지 않았다.
  * 판단: **CONDITIONAL GO** 유지. 다음 단계는 actual Quest lifecycle trace, owner/epoch/Goal UUID prototype, second Action/framework다.
* 2026-08-27 XR2Act decisive validation
  * COMPAS authenticated local loopback에서 normal `T_A`와 A1–A4 변형의 official handoff를 확인했지만 public final executor는 찾지 못했다.
  * Actual HorusLink/HORUS/Nav2 timing matrix 80/80을 완료했다. A result publication 이후 B official cancel 0/63, official failure 뒤 same-UUID direct cancel 67/67이었다.
  * Independent direct UUID cancel 10/10과 COMPAS exact-binding test oracle이 PASS했다.
  * 실제 authenticated credential/scope/shared-authority 조건을 갖춘 Track C 후보가 없어 attack을 만들지 않았다.
  * Existing-work collision과 GO 기준을 적용해 통합 연구를 **WEAK / CASE-STUDY ONLY**로 하향했다.
  * 다음 단계: HORUS UUID/generation fix regression과 maintainer-linked COMPAS executor 확보. 둘이 확장되지 않으면 통합 Item 종료.
