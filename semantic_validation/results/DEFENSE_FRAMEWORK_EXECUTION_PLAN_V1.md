# XR→ROS 방어 프레임워크 연구 실행 계획 v1 (2026-09-22)

> **STATUS: PLAN_FROZEN / EXECUTION_NOT_STARTED.** 이 문서는 기존 연구의 결과를 소급 수정하는 문서가 아니라, 이후 실험의 사전 등록 계획이다. 단계별 완료 증거 없이 DONE으로 표시하지 않는다. 변경이 필요하면 원본 계획을 덮어쓰지 않고 `DEFENSE_PLAN_CHANGELOG.md`에 변경 이유·영향·승인 여부를 기록하고 새 버전을 만든다.

## 0. 최종 목적과 검증할 주장

목적: 실제 XR 입력의 상태와 최종 로봇 제어 수용 사이의 관계가 어긋나는 **구체적인 실행 조건**을 재현하고, 기존 XR-side gate / ROSMonitoring / controller-side check와 동등한 정보를 제공한 공정한 비교에서 새 방어 방법의 독립적 이득을 입증할 수 있을 때에만 방어 프레임워크를 설계한다. 최종 논문 형태는 방어 프레임워크 논문을 목표로 한다. 다만 새로운 방법의 필요성·novelty는 현재 **미확인**이다.

핵심 질문: (Q1) 입력 상태 변화가 실제 원본 downstream 제어 수용/목표/시뮬레이션에 영향을 주는가? (Q2) 기존 방법으로 어느 조건까지 해결되는가? (Q3) 남는 문제가 있다면 어느 *정확한* 입력-상태 관계/계층에서 발생하는가? (Q4) 제안 방법이 다른 독립 구현에서도 재현 가능하며 실시간 비용은 허용 가능한가?

증거 수준을 결코 합치지 않는다: 정적 소스 분석 / synthetic input을 투입한 원본 경로 실행 / 실제 Quest에서 수집한 source-native 상태 / ROS·Pi 수신 / **원본** 제어 소비자 수용 / Gazebo 제어 결과 / 물리적 로봇 동작. 기존 18개는 비무작위 비교 집합이지 ecosystem 보급률의 통계 표본이 아니다. `VALID`, `TRACKED`, Unity `isTracked`, WebXR `emulatedPosition`, Quest system `ORIENTATION`은 동의어가 아니다. 문제로 확인된 상태 정보 누락만으로 위험·운동·취약성을 단정하지 않는다. 자동 복구나 추정 위치 사용은 task policy에 따라 적법할 수 있다.

## 1. 사실상 확정된 선행 결과 (반복 구축 금지)

- PickNik: 실제 Quest `isTracked=false, trackingState=0` 동안 수정하지 않은 ROSPublishers에서 Odometry/TF가 발행됨. 각 유효 구간에서 distinct transform 1. **원본 robot-control consumer 및 motion 미확인.** `semantic_validation/results/PICKNIK_QUEST_FEASIBILITY_20260917.md`.
- Spes: 실제 Quest WebXR `emulatedPosition=true` 상태가 나타난 동일 실행에서 원본 server→upstream ROS→Pi 관측 성립. Pi의 추가 기록 4,100개 원인 미확정, 엄밀한 1:1 수신 주장 불가. Pi는 observation sink일 뿐 controller가 아님. `semantic_validation/results/SPES_QUEST_NATIVE_ROS_FEASIBILITY_20260917.md`.
- Quest2ROS2: 실제 Quest→외부 bridge의 제한된 CDR 호환 패치→원본 RightArmController→target까지 연결했지만 원본 XR tracking 상태는 black box. 실제 tracking-loss attribution 불가. CLIK 최종 소비자 없음. 별도 synthetic ROS sweep에서 원본 source time/frame 무시 및 재생성 확인. `semantic_validation/results/QUEST2ROS2_QUEST_FEASIBILITY_20260917.md`, `QUEST2ROS2_ROS_RUNTIME.md`.
- Docker_Teleop: **Gazebo와 원본 MoveIt Servo 경로가 이미 준비/실행됨.** 기존 synthetic TCP→원본 receiver→mapper→servo→Gazebo에서 D1 Hand-E 이동 약 0.134070 m, D2 `isTracked=false`와 D3 timeout에서는 안정화 후 정지. D4·D5는 재기준점 설정으로 정지했으므로 'stale source가 움직임을 유발했다'는 증거가 아님. 실제 Quest의 system ORIENTATION 전환과 내부 pose-validity는 동등하지 않음. `semantic_validation/results/DOCKER_TELEOP_DOWNSTREAM_RUNTIME.md`, `results/runs/docker_teleop_e2e_20260914/JOINT_STATE_EXTRACTION.md`.
- OpenVR UR5e: **원본 ROS→MoveIt Servo→Gazebo 경로 이미 실행됨.** fake OpenVR 입력 W1 `Running_OK`과 W2 `Running_OutOfRange`(둘 다 `bPoseIsValid=true`)에서 시뮬레이션 관절 이동 관측. 실제 Quest/OpenVR 추적 전환 결과가 아님. `semantic_validation/results/OPENVR_UR5E_DOWNSTREAM_RUNTIME.md`.
- `RESEARCH_DECISION.md`, `QUESTLESS_COMPLETION_MATRIX.md`, `TESTBED_CONTEXT.md` 등 오래된 단계 상태를 2026-09-17의 Quest 결과보다 우선하지 않는다. 기존 실행 경로와 로그를 먼저 재사용한다.

## 2. 연구 범위, 핵심 대상, 독립성

주 실험 경로: (A) **Docker_Teleop 원본 생산용 제어 체인→Gazebo**로 기존 제어 수용/움직임과 방어 비교; (B) **OpenVR UR5e 원본 생산용 체인→Gazebo**로 독립 구조에 대한 방어 비교. 두 체인의 XR 원본 상태는 synthetic/fake일 때 그 수준을 명시한다.

실제 Quest 관찰의 anchor: **PickNik / Spes**의 기존 local raw trace. 이 두 시스템의 원본 로봇 제어 소비자는 현재 준비됐다는 근거가 없다. 원본 downstream을 확보하지 못하면 'PickNik/Spes에서 실제 로봇 영향'을 주장하지 않고, 별도 연구용 adapter로 Gazebo를 연결할 경우 `RESEARCH_ADAPTER_CONSEQUENCE`로 구별한다. Quest2ROS2는 source-time/reconnect와 원본 RightArmController 목표 발행의 별도 검증에 사용하며, 미포함 CLIK controller를 임의 stub으로 대체해 원본 actuator 동작이라고 부르지 않는다.

Pi(`rosxr`) `semantic_robot_sink`는 **수신 기록만** 한다. Pi에 원본 controller를 실제로 설치·실행할 수 있음을 확인하기 전에는 제어 반응 근거로 쓰지 않는다. 무거운 Gazebo/MoveIt은 기존 검증된 desktop Docker에서 실행하는 것이 우선이다. 물리 로봇·driver·CAN·모터는 이 계획에서 사용하지 않는다. Quest는 P0~P5 중 새로운 증거가 기존 trace로 구별 불가능할 때에만 별도 승인받아 사용한다.

## 3. 고정 단계와 완료 게이트

| 단계 | 목적 및 실행 | 완료 판정 (모두 필수) | 기본 상태 |
| --- | --- | --- | --- |
| P0 | 읽기 전용 상태 점검: HEAD/origin, local raw 존재·SHA-256, 로그 포맷·동기화, Docker/Pi/기존 원본 consumer의 실제 존재, 선행 문서 stale 여부 확인. 계획 내 원본 소스·로그와 갭 목록 고정. | `P0_INVENTORY.md`, 데이터별 source/hardware/consumer 구분, 원시 로그 manifest 및 해시, 실행 가능/불가와 이유, 위험/변경 없음 확인; commit/push 및 remote SHA 확인 | NOT_STARTED |
| P1 | **기존 결과 재분석만**: PickNik/Spes actual trace의 상태 전환과 ROS output 시간 결합, Docker/OpenVR Gazebo bag의 메시지→servo→joint 결과를 재계산, Quest2ROS2 stale synthetic 확인. 전후 간격·clock domain·제외 구간 확인. | `P1_TRACE_AUDIT.md`, 재현 명령, 입력 해시·결과 수치·출처 표, 유효 구간/비동기·불명 결과 분류, 표본 주장의 상한; commit/push/remote 확인 | NOT_STARTED |
| P2 | 기존 **Docker와 OpenVR Gazebo** 경로 재현: 원본 source 수정 없이 기존 실행 명령으로 기초 상태/ROS/Servo/관절 상태 확인. 오작동 조건은 비교 가능한 실제 입력 경계에서 고정하고, static pose를 움직임으로 과장하지 않는다. | `P2_CONTROL_BASELINE.md`, 정확한 이미지/컨트롤러/토픽/경로와 start-stop 명령, healthy baseline 및 상태 변화 case 로그, counterfactual pair, control stage별 수용·출력·관절 변화, no-Quest/synthetic 명시; commit/push/remote 확인 | NOT_STARTED |
| P3 | 비교 실험의 사전 등록: task-specific 허용 정책(추정 입력 허용 여부, freshness 예산, timeout, 복구/재arm), threat/failure model, 각 구현의 신뢰 가능한 원본 상태 공급 지점, 각 case의 차이 변수 하나씩 및 판정 기준 고정. | `P3_BASELINE_PROTOCOL.md`, 적어도 tracking, old source sample, delayed delivery, disconnect/reconnect, recovery를 **서로 다른 조건**으로 규정. source time vs ROS receive time·clock sync 구분. 동등한 state/sequence metadata 제공 방침, fail-open/closed·정상 조작 영향까지 사전 명시; commit/push/remote 확인 | NOT_STARTED |
| P4 | 기존 방어 방법 **실제 구현·비교**: ① 원본 무방어 ② XR-side source-state gate(Quest 대신 동일 source API semantics를 재현한 harness; native claim 금지) ③ ROSMonitoring(기존 버전/실제 기능 명시, 원본 상태 supplied) ④ controller-side direct check. 같은 입력·policy·환경에서 개별/결합 방식 비교. | `P4_EXISTING_DEFENSES.md`와 재현 가능한 코드·raw execution logs, 정상/비정상 수용, false positive/negative, 감지·차단·안정화 시점, ROS output/Servo/joint 결과. ROSMonitoring 실행 불가면 이유 명시, '실패'라고 쓰지 않음. baseline이 문제를 모두 해결하면 그 결과 그대로 기록; commit/push/remote 확인 | NOT_STARTED |
| P5 | P4에서 남는 조건의 **독립 구현 검증**: 다른 XR acquisition/ROS boundary의 Docker↔OpenVR 조합 및 PickNik/Spes 원본 trace에서 실제와 synthetic을 분리해 재검증. 필요 시 연구용 adapter 효과와 원본 controller 결과를 분리. 18개 positive/negative 사례 중 해당 조건과 무관한 사례는 강제로 포함하지 않는다. | `P5_CROSS_STACK_DECISION.md`: 공통 문제가 무엇인지, 어떤 실험에서 확인되고 어디서는 반례/UNKNOWN인지, 기존 방법의 정확한 부족 조건과 신뢰 가정. 독립 novelty가 없으면 **NO_METHOD_GAP** 명시; commit/push/remote 확인 | NOT_STARTED |
| P6 | **조건부**: P5에서 기능적 또는 실용적 갭 확인된 경우에만 방어 방법 설계·구현. ROSMonitoring 2.0, source-side gate, direct checks, ROS tracing, Simplex 등과 실제 기술적 차이 재검토. eBPF는 원본 상태 누락을 복원할 수 없으며 별도 실측 이점이 있을 때만 채택. | `P6_METHOD_DECISION.md`, mechanism/placement/trust/coverage/limitations 및 baseline 대비 차이, 각 입력 케이스 결과. 갭 미발견 시 프레임워크 개발을 계속하지 않고 명시적 연구 방향 재심사; commit/push/remote 확인 | NOT_STARTED |
| P7 | 조건부 최종 프레임워크 평가: 여러 독립 경로에서 방어 정확도, 정상 조작 보존, median/p95/p99 지연·jitter·CPU/memory·failure mode, 적용 변경량·이식성. 동일 기능/입력/컨트롤러 설정으로 baseline 비교. | `P7_EVALUATION.md`, 코드·raw logs·재현 절차·비교표, 범위에 맞는 논문 claim. 마찬가지로 commit/push/remote 확인 | NOT_STARTED |

**P0부터 순차 실행하고 한 번에 한 단계만 실행한다.** P3 정책/실험 기준은 P4 입력 결과를 본 뒤 사후 조정하지 않는다. P1/P2 결과에서 실험 불가능·일관성 결여가 드러나면 이유를 기록하고 **BLOCKED / NEEDS_PLAN_REVISION**으로 보고한다. 최초 Quest 재실행은 최우선이 아니다.

## 4. 단계별 저장·검증 프로토콜

- 고정 문서: 이 파일. 추적 파일: `semantic_validation/results/DEFENSE_EXECUTION_STATUS.md` (Codex가 P0에서 작성). 변경 결정: `DEFENSE_PLAN_CHANGELOG.md`. 각 단계 보고서: 위 표의 고정 이름. 상태는 `NOT_STARTED / RUNNING / DONE / BLOCKED / INVALIDATED`.
- 모든 실험 단위에서 `stage, trial, framework, upstream revision, input provenance, injection point, original-or-research-adapter, capture time, receive time, consumer action, simulated result, evidence level, exclusion reasons`를 명시. 실제 계측 불가 필드는 UNKNOWN; 임의 값을 채우지 않는다.
- 종료 시: 새로 생성된 raw 로그 경로·SHA-256 manifest, 원본 source/실행 명령, stdout/stderr, 환경·컨테이너/토픽/ROS_DOMAIN_ID/clock contract, 결과 표·해석·미해결 문제, 재실행 명령을 보고서에 기록한다. **기존 raw evidence는 덮어쓰지 않는다.** 이미 추적되지 않는 큰 raw/bag/APK는 임의 Git 추가·삭제 없이 로컬 보존하고 커밋된 해시 manifest로 검증 가능하게 한다. commit 가능한 소형 결과만 명시적 `git add <path>`로 staging.
- 원본 vendor/upstream, 네트워크 설정(특히 lab `enp4s0`), Docker socket permission, 물리 robot/driver/CAN 관련 파일을 임의 수정하지 않는다. `git add .`, `git clean`, `git reset --hard`, 무차별 `git stash`, force-push 금지. 새로운 source mutation이 꼭 필요하면 원본과 분리한 overlay/adapter를 사용하고 차이를 기록한다.
- 각 단계 Codex 수행 → 사용자에게 stage, result(DONE/BLOCKED), 변경 파일, 핵심 관측, 해시, **local HEAD와 origin/main SHA가 같은지** 및 commit URL 공유 → ChatGPT가 GitHub 원격의 commit과 문서·소형 로그를 실제로 조회하여 PASS/REVISE 판단. ChatGPT가 raw 파일을 원격에서 읽지 못한 경우 '로컬 raw 직접 검증 안 됨'을 명시한다. ChatGPT 확인 전 다음 단계 실행 금지.
- GitHub에 plan이 먼저 커밋되므로 P0 시작 전에 Codex는 remote main과 로컬 tracked 변경/미추적 raw 상태를 읽기 전용으로 점검하고 **안전하게 fast-forward 가능한 경우에만** 최신 plan을 동기화한다. 충돌/미확인 변경 시 중단하고 보고한다.

## 5. 첫 수행: P0 only

P0는 환경/기존 데이터 인벤토리, 충돌 없는 Git 동기화, 고정 계획 읽기 및 추적 문서 생성까지만 수행한다. Quest, Gazebo, ROSMonitoring, source patch, 네트워크 변경 등 실제 runtime을 시작하지 않는다. 이미 설치/실행/수집된 것을 먼저 확인한 뒤 다음 단계를 시작한다. 현 시점에서 **P0 완료나 원격 raw evidence 검증은 아직 수행되지 않았다.**
