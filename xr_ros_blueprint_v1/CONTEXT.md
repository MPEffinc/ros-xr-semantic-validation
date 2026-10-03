# XR→ROS 연구 context

기준일: 2026-10-02. 이 문서는 연구 배경, 확인된 결과, 현재 판단과 미해결 질문을 정리한 참고 자료다. 이번 회차의 실행 범위·순서·완료 조건은 사용자가 별도로 전달하는 프롬프트에서 정한다. 문서에 남은 다음 후보나 전체 계획은 그 자체로 실행 지시가 되지 않는다.

## 1. 연구 목표와 기여 방향

XR 입력부터 ROS 물리 실행, 로봇 피드백과 사용자 승인까지 전체 경로에서 보호 조건이 어떻게 보존되는지 조사한다. 입력 유효성, 상태 전환, 시간·공간, 장치·소유권, 실행, 피드백·승인, privacy·availability가 범위에 포함된다.

교수님은 matrix 자체의 기여 가능성을 인정했다. 연구실의 시스템/프레임워크 기여 성향도 고려하여 다음 두 경로를 열어 두었다.

- 기존 방법에 필요한 정보·신뢰·시간·집행 전제가 실제 배치에서 충족되지 않는 경우: 그 전제를 확보하는 시스템/방법 후보.
- 개별 기존 방법으로 해결되는 사례들에서도 공통 구조가 반복적인 수정과 통합 비용을 줄이는 경우: 비교 평가를 통한 시스템 기여 후보.

검사들을 묶거나 기존 envelope/gate를 다시 만드는 것만으로 기여가 확정되지는 않는다. 강한 개별 수정과 관련 프레임워크 대비 보호·비용 이득은 아직 검증할 질문이다. 공백 발견이나 프레임워크 제작을 미리 결론으로 두지 않았다.

## 2. 연구 지도와 자료 위치

GitHub 저장소의 Markdown과 DB가 진행 상황의 기준이다. 사용자는 시트를 보고·이해 목적으로 사용하며, 시트 접근은 해당 회차에서 명시적으로 요청한 경우에 한정한다.

| 자료 | 담긴 내용 |
|---|---|
| README.md | 쉽게 읽는 전체 방향 |
| STATUS.md | 완료·미착수·보류·제약의 현재 상태 |
| CONTEXT.md | 연구 배경, 결정, 기존 결과와 주장 범위 |
| BLUEPRINT.md | 전체 흐름, 위협 모델, 분류, 중장기 탐색 계획 |
| data/blueprint.json | 사례·문헌·한계·matrix의 수정 기준 DB |
| data/csv/ | JSON에서 생성한 검토 뷰 |
| ../semantic_evidence_framework/ | 기존 audit/docs/results |
| ../archive/ | 종료된 연구와 보존 기록 |

감사 반영 후 현재 지도는 사례 40개, 방어 유형 14개, 비교 항목 99개, 한계 48건, 출처 49건, 계승 문헌 seed 94건이다. 99개는 실행 완료 횟수가 아니다. KNOWN_METHOD는 해당 범위의 기존 방법 존재이며 모든 배치의 해결을 뜻하지 않는다. CANDIDATE는 검증 질문, UNKNOWN은 근거 부족이다. 저자 limitation과 미추출 항목만으로 현재 공백을 확정하지 않는다. 현재 확정 method gap은 0건이다.

DB의 검증과 CSV 재생성 도구는 scripts/refresh_views.py다. 실제 새 근거는 출처 commit/판본/원문 위치 및 확인 수준과 연결된다.

## 3. 연구 이력과 보존 경계

이전 작업 위치는 /home/cclab/ros_xr_evidence, 연구 브랜치는 research/xr-ros-evidence-framework다. 기존 실험 기준점은 eff464c9b1011a7646ec80e18f4e771028b89cc5이고, Blueprint/DB의 최초 저장 checkpoint는 e772310323e7de9d09af5b515377691564155aa4다. 현재 HEAD는 Git 이력으로 확인되는 값이며 기준점과 동일하다고 가정하지 않는다.

기존 /home/cclab/ros_xr checkout, N1 연구, 다른 작업의 컨테이너는 별도 작업이다. 종료된 authority_continuity와 xr_demo_integrity는 이미 archive로 정리됐다. 새 연구 자료는 xr_ros_blueprint_v1에 있다. 기존 protocol/raw/result는 보존되며, 사후 정정은 별도 문서와 변경 근거로 추적된다.

## 4. 기존 실험과 주장 범위

- S1–S5: 필요한 정보가 전달될 때 기존 검사로 해결된 사례. 신규 주장으로 반복하지 않는다.
- P1/P1b: 합성 OpenVR→Gazebo. 메시지 중단 뒤 27.9–42.4 mm 잔여 이동(최신 감사 정정), JTC 현재 관절 위치 hold에서 약 1 mm. 명령 차단과 실제 정지는 다르다. deadman·recenter는 증거 전달/기존 앱 수정으로 해결한 범위가 있다.
- P2: 오래된 Ubuntu Monado build의 READY 고착은 알려진 upstream 수정 문제였다. 최신 main의 일반적 사양 위반으로 주장하지 않는다.
- F1: 대역 앱 27회. 독립 runtime 상태 경로 feasibility는 보였지만 timestamp 전제와 비교군 freshness 교란이 있었다. 고정 protocol/raw/result는 그대로 보존하고 사후 해석은 별도 문서에 둔다.
- F2: 대역 앱 27회, 동일 freshness로 비교. interval 검사의 필요성은 중간 중단도 금지하는 정책을 선택할 때에만 추가된다. 상태 검사와 중복·역순 검사 효과는 구분한다. 5 ms 전환과 증거 지연에서 누출이 있었으므로 경계를 제외해 성공을 주장하지 않는다.
- F3: 원본 OpenVR UR5e 앱 1개 + 수정 xrizer + Monado/Servo/Gazebo, 6회. runtime 비활성 구간에 앱이 스스로 명령을 멈춰 수신 gate의 추가 차단 0건. 재개 시 목표가 35 mm 점프했으나 물리적 결과는 특이점 정지에 가렸다. 앱은 무수정이어도 배포 구성요소는 3가지 수정됐고 주기도 50→20 Hz로 변했다.
- M39 pilot(R04; 해석 보강 R05, 시계 분리 R07): 같은 실제 앱 경로, 45회, masked 0. 원본 재개 점프가 물리 실행됨(I1 47.9 mm/11.5°, 300 ms에 EE 20–23 mm; N1 절대 재기준 40 mm; 움직이는 중 정지 잔여 10–14 mm). 가장 강한 개별 수정 B1이 전체 계약 충족. 앱 무수정 ROS-side C1은 부분 계약 충족, 새 누름 재허가 0/9.
- 실제 앱에서 `명령 stamp = 입력 sample 시각`은 무수정 상태로 확인되지 않았다. 수신 시점 상태 보호와 sample-to-command 출처 보장은 다르다. runtime token만으로 앱의 명령 계산이 올바르다고 증명되지 않는다.
- 손상 앱 방어는 미완성이다. IPC 제어 권한, 비위조 client 연결, 증거 신뢰, 모든 실행 경로의 매개, 명령 유래를 함께 확인해야 하며 인증 패치 하나로 완료되지 않는다.
- 실제 headset·Quest runtime·물리 로봇, 닫힌 frontend의 내부 읽기는 확인 범위 밖이다. 실제 앱, 대역 앱, 합성 입력, 시뮬레이션, 물리 로봇을 별도 표시한다.


## 5. 현재 판단과 미해결 질문

기존 실험은 전체 문제 중 runtime 입력 활성 증거와 stop/resume 일부를 깊게 검증했다. 특정 독립 수신 gate의 확대 보류는 나머지 사례의 연구 종료를 뜻하지 않는다.

| 축 | 주요 사례 | 남은 질문 |
|---|---|---|
| 중단·정지·재개 | M2/M3/M4/M5/M6/M39 | 개별 stop/re-arm/re-anchor 해법의 결합에 공통 구조의 이득이 있는가 |
| 시간·출처·우회 | M12/M17/M18/M19/M20/M40 | 실제 sample/command 연결, 증거의 신뢰, 짧은 전환, 집행 우회가 어떻게 제한되는가 |
| 화면·승인과 실행 | M22/M23/M25/M26 | 목표 지정형의 장면·선택·명령 관계를 기존 version 검사와 독립 관측이 어디까지 보호하는가 |
| 공간·장치·다중 입력 | M7/M8/M9/M10/M28/M29/M38 | recenter/calibration/drift/위조·장치 전환의 근거와 기존 해법 범위가 무엇인가 |
| 통신·privacy·availability | M15/M16/M30/M31/M32/M35/M36 | 최신 patch/방어 적용 후 남는 teleop 비용·보장·가용성 문제가 무엇인가 |

중장기 Blueprint는 지도 감사 → 사례 검증 → 반복 문제의 시스템 평가라는 방향이다. 최초 조사 후보로 stop/resume 결합이 제안됐으나 pilot 대상, 비교군, trial 수, 실행 예산과 진행 여부는 회차별 프롬프트와 새 조사 결과로 결정된다. 실제 이질적 경로 확보와 강한 비교군 대비 통합 이득이 시스템 평가의 주요 조건이다.

## 5a. 2026-10-03 근거 감사에서 확인한 사실

- 기존 실험의 물리 결과 중 재개 점프 이후 구간 세 개는 MoveIt Servo의 HALT_FOR_SINGULARITY에 가려졌다(P1 C2, P1b C2M, F3). 같은 시작 자세와 +x 이동이다(U46). P1의 회전 기준도 자세 미정착으로 교란됐다.
- JTC 4.42.1의 `cmd_timeout`은 마지막 point 이후에만 동작한다. hold는 측정 상태를 유지한다. 빈 trajectory는 거부한다(L37).
- Servo 2.12.4의 pause와 timeout은 Servo 출력만 멈춘다(L40). 실제 정지에는 controller hold가 필요했다(P1b).
- Safe-ROS는 topic 수준의 0 속도 override 뒤 정지 신호가 사라지면 자동으로 재개한다. 저자는 지연·actuator 불확실성을 범위 밖으로 명시했다(U18, U19, U44).
- clutch/indexing 재기준화는 원격조작의 확립된 관행이다(L41, 검색 발췌 수준).
- 보호 조건이 수치 정책으로 정해진 사례는 40개 중 4개다.

## 5b. 2026-10-03 상세 검토의 사실과 미해결 질문

- 재개 정책은 구현마다 다르다.
  - 자동 재개: OpenArmX, Docker reset 경로, OpenVR의 pose 무효 경로
  - edge 조건 재개: OpenVR release 경로, Quest2ROS2, Spes
  - 재기준점: 현재 tf EE(Quest2ROS2), 마지막 명령(Spes), 새 raw pose(OpenArmX), 절대 상수(OpenVR)
- ROS 2 Lifespan QoS는 발행→수신 시간을 잰다. 다시 발행된 묵은 값을 판정하지 못한다(L42).
- 미해결 질문:
  - 개별 수정들(hold, unpause, 앱 재기준화) 사이의 순서
  - 앱 밖에서 '새 누름'을 관측할 수 있는가(버튼이 wire에 실리는 구현에 한정)
  - hold 뒤 정착 오차
  - 작업별 재개 정책 선언
  - 공통 전환 구성요소의 통합 비용 이득(재기준화에는 앱별 명령 의미 adapter가 필요)

## 5c. 2026-10-03 설계 결정

- 첫 실험 후보로 M39(범위 한정)를 추천했습니다. 비교 결과는 `cases/C02`에 있습니다.
  - M12는 같은 환경에서 시험할 수 있지만, 기존 수정으로 해결될 가능성이 높아 두 번째 후보로 둡니다.
  - M22는 목표 지정형 앱이 없어 BLOCKED_ENV입니다.
- 보호 정책 P_rearm(새 누름)은 정책 선택입니다. 자동 재개를 쓰는 구현도 있으므로 결과를 두 정책으로 함께 보고합니다.
- 앱 밖 구성요소(C1)는 현재 경로의 버튼 edge를 관측할 수 없습니다. 원인은 정보 한계이지만, P_rearm을 요구하는 계약에서 새 누름 없이 재개하면 그 조건은 불충족입니다. 부분 계약과 전체 계약의 결과를 별도 보고합니다.
- 미해결: 앱의 고정 절대 engage 자세가 특이점 근처라면 교란 없는 시작 자세를 찾을 수 있는지는 pre-flight로만 판정할 수 있습니다.

## 5d. R01 방법 검토에서 남은 조건

R02_METHOD_REVIEW_R01.md의 검토는 문서 분석이며 새 실행 결과가 아니다. B1에 올바른 hold/re-anchor/unpause 순서와 필요한 runtime 관측을 제공한 가장 강한 기존 수정이 비교 기준이다. C1에는 정책 충족 범위와 입력 정보 차이가 명시된다. 조건 또는 arm이 유발한 특이점·충돌 개입과 증거 공백은 실행 결과에 남는다. 정상 재허가 후 움직임 회복 조건이 없으면 영구 차단이 성공처럼 보일 수 있다. 중립적 pre-flight, SE(3) re-basing 의미와 clock 대응은 아직 확인할 사항이다.

## 5e. 2026-10-03 M39 pilot의 사실과 판단

- 경로 사실(code·관측):
  - Servo는 sim time을 쓰고 앱은 wall stamp를 써서, 이 경로에서는 incoming_command_timeout이 동작하지 않는다. Servo는 마지막 목표를 계속 추종한다.
  - xrizer raw pose는 Monado grip pose에서 offset된 값이라, 손을 회전하면 앱의 위치 목표도 움직인다.
  - 앱의 고정 engage 자세에 대한 모든 IK branch에서 forearm–wrist_2가 근접해 Servo 충돌 감속(status 4)이 나타난다. Pre-flight에서 서로 다른 구간의 추종 지연 차이는 최대 0.33 mm로 관측됐다. 동일 동작의 감속 유무를 짝지어 비교한 인과 추정은 아니므로, 모든 정식 trial에서 감속의 영향이 0.33 mm 이하라고 보장하지 않는다.
- B1 감지 관측(probe):
  - IO 비활성화가 한 tick 이상이면 그다음 tick부터 pose-invalid와 grip false로 보인다.
  - 30 ms 비활성화는 앱이 보지 못한다.
  - 비활성 중의 해제와 누름도 앱에 보이지 않는다.
  - 따라서 무효 tick의 grip을 읽는 단순 edge 검출은 새 누름을 잘못 인정한다.
- 판단:
  - 이 실제 경로의 stop/resume 결합(M39)은 기존 개별 수정(valid-tick fresh press, 측정 EE 재기준화, controller hold, 순서 있는 unpause와 runtime 증거)을 올바르게 결합하면 해결된다(B1).
  - 공통 ROS-side 구성요소는 앱을 수정하지 않고 정지·재기준화·정상 회복을 달성했다. 새 누름 재허가는 버튼이 wire에 없어서 불가능했다. 이는 정보 한계이며 전체 계약 기준으로는 불충족이다.
  - 재기준화에는 앱별 명령 의미 adapter가 필요했다. 위치는 base_link 가산, 회전은 R_anchor·R_rel이다. 잘못된 합성 순서는 host 검사에서 7.99 mm 또는 2.28°의 오차를 냈다.
- 미해결 질문:
  - 버튼이 wire에 실리는 두 번째 실제 경로에서도 같은 구성요소가 전체 계약을 충족하는가? adapter 비용은 per-app 수정보다 작은가?
  - 실제 headset 전환(focus·menu·tracking loss)도 한 tick 안에 pose-invalid로 전달되는가?
  - 다른 자세·속도·하중과 드문 race에서는 어떤가? 3회 반복으로는 알 수 없다.

## 5f. 2026-10-03 M39 해석 보강과 두 번째 경로 확인의 사실

- **R05 사후 분석.** M39의 B1 전체 계약·C1 부분 계약 판정은, freeze 전에 바꾼 추종 기준(원본 앱의 명령 증분)에서 성립한다.
  - 원래 기준(feeder 손 pose)으로는 원본 앱의 정상 운전도 실패한다. 이 기준은 xrizer raw pose offset을 재고 있었다.
  - 최종 기준은 앱 자신의 mapping과의 일관성을 확인할 뿐, 조작자 의도나 좌표계의 정확성을 독립적으로 검증하지 않는다.
  - L3 임계값과 정착 시각 변경은 판정을 바꾸지 않았다.
  - status 4는 감속 크기를 담지 않고, pause 중에는 발행되지 않는다. 판정 구간의 노출은 arm마다 다르다. "hard stop에 가려지지 않음"과 "감속 영향 제거"는 다르다.
- **R07 B0_clock.** 앱을 upstream launch 값인 `use_sim_time:=true`로 실행하면 앱과 Servo의 시계가 일치하고 Servo timeout도 동작한다.
  - 그래도 움직이는 중 중단의 잔여 이동(10–13 mm)은 그대로다. 마지막 JTC 목표가 이미 EE보다 앞서 있기 때문이다.
  - 따라서 이 잔여 이동은 배포 시계 문제가 아니라 controller 수준(M3)의 문제다. 시계 불일치가 만드는 것은 "Servo가 마지막 목표를 끝없이 추종함"이다.
- **R08 두 번째 경로.** 감사한 세 후보는 모두 Quest가 필요하거나(Docker_Teleop, Quest2ROS2, PickNik), Linux에서 실행되지 않거나(Unity OpenXR 1.14.3), consumer가 비공개 또는 부재다(PickNik MoveIt Pro, Quest2ROS2 Cartesian controller). 환경 차단이며 공백의 증거가 아니다.
- **wire 버튼과 새 누름.** wire에 버튼이 있다는 것만으로 새 누름이 보장되지는 않는다.
  - Docker_Teleop: stale neutral이 `teleop_enable=false`를 만든다. `source` 필드로만 구분할 수 있다.
  - Quest2ROS2: 버튼 level을 toggle edge로 쓴다.
  - PickNik: 비활성 전환에서 false→true와 press event가 함께 생길 수 있다(미검증).
  - Quest에서는 libmonado 같은 독립 runtime 증거도 없다.
- **미해결 질문.**
  - Quest 확보 시, Docker_Teleop에서 stale을 구분하는 버튼 adapter를 쓴 공통 구성요소가 앱 수정 없이 전체 계약을 충족하는가? 그 비용은 per-app 수정보다 작은가?
  - 현 경로에서 status 4 감속량은 얼마인가? `decelerate_to_hold_position`은 잔여 이동에 어떤 효과가 있는가?


## 5g. 2026-10-03 R05–R08 검토 후 판단

- GitHub의 R05, R07, R08을 검토했다. 이는 ChatGPT의 문서 검토이며 새로운 실행 결과가 아니다.
- 시계 일치로 Servo timeout은 회복됐지만, 이미 발행된 JTC 목표를 따라잡는 잔여 이동은 남았다. 해당 경로·자세·속도에서 controller 수준 정지의 필요성을 뒷받침하며 새로운 method gap을 확정하지 않는다.
- R04의 추종 성공은 원본 앱 mapping 보존이라는 기준에서 성립한다. 사용자 의도·좌표계 정확성에 대한 독립 검증은 아니다. status 4의 크기와 물리 결과에 대한 영향도 아직 분리되지 않았다.
- 두 번째 실제 경로는 환경 차단으로 대기다. Quest를 확보해도 wire 버튼만으로 full contract나 독립 runtime 근거가 확보된다고 가정하지 않는다. 현재 구성을 넘어서 Quest의 모든 관측 방법이 불가능하다고 입증한 것은 아니다.
- 후속 판단은 현 경로의 감속·정지 집행 범위를 명확히 한 뒤 M12(묵은 값에 새 stamp)를 검증하고, 그 결과를 다른 시간·공간 사례와 연결하는 것이다. 기존 방법으로 해결된 결과와 미검증 한계도 matrix에 누적한다.
- 사용자는 부재 중 승인된 여러 단계를 연속 진행할 수 있도록 요청했다. 실행 범위·조건부 분기·예산은 별도 프롬프트에서 정하며, 본 문서는 그 프롬프트를 대신하지 않는다.

## 5h. 2026-10-03 감속·정지·M12 실행의 사실과 판단

- **충돌 감속.** 이 경로의 status 4 감속은 작다. 적용 scale은 최소 0.8945였다. 노출은 arm마다 다르다(B0가 절대 재기준으로 시작 자세에 돌아올 때 가장 크다). 로그만 추가한 Servo build로 직접 기록한 값이며, 이동·지연에 대한 인과 효과는 추정하지 않았다. pause 중에는 collision monitor가 멈추고 이전 scale이 유지된다.
- **정지.**
  - 시계를 맞춰도 Servo timeout만으로는 이미 발행된 목표를 따라잡는 이동이 남는다(10–12 mm, 절반 속도에서 5–6 mm).
  - 기존 측정 상태 hold와 측정 속도 기반 감속 정지(JTC 수식, a=3.0)는 두 속도에서 R03 정지 기준을 충족했다. 중단 증거와 측정 상태가 필요했다. 실제 구현은 pause 요청 뒤 확인 응답 전에 첫 hold를 보내고, 응답 시와 +0.1 s에 재전송했다. 따라서 첫 hold 이전에 pause가 완료되었다는 순서 보장은 아니다.
  - JTC 고유 감속은 action 경로 전용이다. topic 명령은 정지를 덮어쓴다.
- **M12.**
  - 이 경로에서 발행·수신 stamp가 새롭다는 사실은 입력이 새롭다는 근거가 되지 않는다.
  - 앱이 획득 시각·순서·유효성을 명령과 함께 보존하는 기존 provenance 방식은 지연·캐시 재발행·비활성 재사용을 구분했다. 비용은 앱 6줄, gate, 모든 재발행자가 보존해야 하는 필드다. 신뢰는 앱에 의존한다.
  - runtime 상태만으로는 비활성 재사용만 구분된다.
  - 원천 정지는 정당한 정지 상태와 구분할 정보가 경로에 없다. Monado remote 드라이버와 OpenVR API 모두 sample 시각을 제공하지 않는다. method gap이 아니라 이 배치의 정보 가용성 한계다.
- **M7/M8/M9.**
  - M7: 이 경로에서는 frame이 같아 발생하지 않는다. stamped tf 조회는 M12의 stamp 의미 한계를 그대로 물려받는다.
  - M8(공유 메시지 객체)·M9(head pose 대체): 기존 root fix가 대상 구현과 upstream에 적용되지 않은 구현 공백이다.
- **미해결 질문.**
  - 실제 headset runtime은 원천 손실 시 sample 시각이나 tracking 손실 신호를 노출하는가?
  - 실제 재발행자(예: Docker_Teleop receiver 재stamp)를 거쳐도 provenance 필드가 보존되는가?
  - 다른 자세·가속 한계·실제 로봇에서도 정지 결과가 유지되는가?
  - 장치·source 식별을 provenance에 포함하면 M8/M9를 함께 막을 수 있는가?

## 5i. 2026-10-03 R12/R13 검토 후 판단

검토 문서는 `reports/R14_REVIEW_R12_R13.md`다. 새로운 실행 결과가 아니다.

- M3는 해당 경로·두 속도에서 기존 controller 정지 방법으로 해결됐다. native action 감속과 외부 topic 수식 구현은 구분한다.
- M12의 해결 판정은 전송 지연·bridge 캐시·비활성 재사용과 정상 앱 가정에 한정한다. 앱 read 시각·read sequence는 실제 source sample 시각·update sequence가 아니다. 원천 정지와 손상 앱의 자기보고는 해결되지 않았다.
- 정보가 gate에 없다는 결과는 정보 확보 연구를 배제하지 않는다. remote driver 수신 시각 watchdog이라는 기존 root fix를 먼저 비교해야 한다. 이는 패킷 수신 신선도이며 물리 sensing 신선도를 보장하지 않는다.
- B1 I3 재실행에서 실제 정지 속도 기준 실패가 1건 있었다. 이전 성공 데이터는 보존하되 failure-free 보장으로 확대하지 않는다.
- pause 확인 전에 hold가 발행됐고 뒤늦은 trajectory가 이를 덮을 수 있다. 현재 통과 결과에는 writer·queue 전제가 남는다.
- 다음 검증 축은 source 증거 확보, 실제 재발행 코드의 provenance 보존, M7의 동적 frame 시간 정합성이다. 구체적인 실행 범위는 별도 프롬프트에서 정한다.

## 5j. 2026-10-04 정보 확보·전달·집행 전제 검증의 사실과 판단

- **원천 정지.** Monado remote driver는 수신 시각 없이 최신 값을 tracked로 보고한다. driver에 수신 시각을 보존하고 주기 watchdog을 적용하면 정지를 60–67 ms 안에 차단하고, 정지한 손을 오차단하지 않는다. 정보는 driver에 있었고 보존만 하면 됐다. method gap이 아니다. 패킷 수신은 sensing이 아니므로, 오래된 내용을 계속 보내는 source와 실제 headset의 손실 의미는 열린 질문이다. gate 쪽 수신 증거는 pose와 시간 순서로만 짝지어진다.
- **실제 재발행자.** Docker_Teleop receiver는 packet timestamp를 읽지 않고, 수신 시각·횟수를 내부에서만 쓰며, 매 publish마다 새 stamp를 찍는다. 출력만으로는 검사가 불가능하다(검사 실패와는 다르다). typed schema로 payload와 provenance를 한 메시지에 담으면 해결된다. 다만 producer sequence가 없으면 fail-closed와 fail-open 중 하나를 택해야 한다. 실제 Unity frontend는 sequence를 보내지 않는다. neutral은 새 관측이 아니므로 정지로만 허용한다.
- **M7.** 올바른 변환 시각은 작업 의미에 따라 다르다. world target 유지라면 표현 시각, 현재 frame 추종이라면 latest다. 표현 시각은 transport stamp와 별도로 보존해야 재발행자의 재stamp를 견딘다. 남은 위험은 의미 선언과 시각 보존이며, 방법 부재가 아니다. 허용된 지연에서의 효과는 기본 stamp 나이 때문에 측정되지 않았다.
- **정지 순서.** Servo pause 확인은 이후 출력이 없음을 보장하지 않는다. JTC는 topic trajectory마다 hold를 대체한다. 직접 hold 방식은 늦게 도착한 메시지가 마지막 명령이 될 수 있는 구조다. 이번에는 내용이 정지 자세 근처라 피해가 없었다. 최종 경계의 단일 writer(mux)는 경계를 지나는 writer에 대해 이 전제를 제거한다. 직접 publish 권한, action 경로, 재허가 전환은 별도 전제다.
- **기여 판단.** 이번 회차의 네 결과는 모두 기존 방법(watchdog, provenance 보존, 시각별 tf, 단일 writer)이 각 전제를 충족할 때 해결된다는 것이다. method 기여의 근거는 늘지 않았다. 시스템 기여 쪽에서는 해결책이 hop마다 다른 정보를 보존·검사해야 한다는 반복 비용이 확인됐다(driver patch, receiver schema, 표현 시각 필드, writer 경계). 다만 공통 구성요소가 이 비용을 줄이는지는 두 번째 실제 경로 없이 입증되지 않았다.
- **남은 UNKNOWN.** 실제 headset의 sample 시각·손실 신호, provenance 위조(S2), 오래된 내용을 계속 보내는 source, 실제 Unity sender의 sequence, mapper/bridge hop, 허용된 지연에서의 M7, 먼 목표의 late message, controller topic 직접 publish 권한.

## 6. 근거 해석의 공통 기준

- SDK 제공 가능성, 앱의 실제 읽기, wire 전달, ROS 소비는 각각 다른 확인 단계다. 검색에서 못 찾은 경우는 부재 증명과 구분된다.
- 공식 문서, 저자 주장, code, 기존 trace 재분석, 대역 실험, 실제 앱 실행, 물리 로봇 결과, 우리 추론은 다른 근거 수준이다.
- 비교에는 동일 정책·freshness·정보·권한·부하·초기 조건과 상태 전환 경계가 중요하다. 새로운 정보 경로를 추가한 경우 그 신뢰와 비용도 비교에 포함된다.
- 메시지 차단, controller의 목표 중단, 실제 정지는 서로 다른 결과다. 특이점·충돌 정지가 결과를 가리면 의도한 방어 효과로 인정되지 않는다.
- 공격자 권한과 단순 고장은 구분되며, SROS2 등 인증 방어의 보호 목표 밖 의미 조건은 인증 실패로 평가되지 않는다.
- 기존 방법으로 해결된 사례에도 저자 가정·한계·후속 해결 상태와 미검증 배치가 남는다. 환경 차단은 공백 부재의 증거가 아니다.

## 7. context와 실행 지시의 관리

사용자는 ChatGPT의 회차별 지시 → Claude Code 수행 및 기술 보고 → ChatGPT의 보고·GitHub 근거 검토 → ChatGPT의 쉬운 설명 → 다음 판단·이유 설명·별도 Claude Code 프롬프트 제공 순서로 연구를 진행한다. Claude Code는 기술 보고를 담당하고, 사용자에게 쉽게 설명하며 다음 회차를 판단하고 지시하는 역할은 ChatGPT가 맡는다. 저장소에는 사실·근거·결정·질문·현재 상태가 누적된다. 한 회차의 명령문, 승인된 실행 범위와 완료 조건은 별도 사용자 프롬프트에 있다.

STATUS의 다음 후보는 추천/backlog이며 실행 명령으로 해석되지 않는다. 새 결과가 나오면 현재 상태와 context를 Git으로 갱신하고, 완료한 작업의 범위와 checkpoint는 이력으로 추적된다. 과거 독립 gate에 대한 보류 판단이나 실행 계획은 새로운 결과 없이 자동으로 확대되지 않는다.
