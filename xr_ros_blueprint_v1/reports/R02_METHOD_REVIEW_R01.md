# R02 — R01 draft protocol 방법 검토

검토 기준은 8f73c9c의 R01, C01, STATUS, CONTEXT와 DB다. 이번 검토는 문서 분석이며 신규 실험은 없다. 구체적인 다음 실행 지시는 별도 사용자 프롬프트로 제공된다.

## 현재 결론

M39의 실제 앱+시뮬레이션 경로에서 기존 개별 수정과 ROS 측 보완을 비교하는 pilot은 진행할 가치가 있다. 새 검사 방법의 필요성이나 시스템 기여는 아직 입증되지 않았다. 이번 단계의 실증 목적은 기존 물리 결과의 교란 제거와 개별 해결들의 결합 검증이다.

DB에서 확인한 현재 규모는 사례 40개, 방어 14개, 비교 99개, 출처 49개, 한계 48개, 연구 계획 8개다. 99개는 실험 횟수가 아니다.

## 1. 비교군 B1의 강도

R01 B1은 앱의 pose-invalid/release와 engaged Bool을 기반으로 동작한다. 이 신호가 실제 runtime 입력 비활성화를 빠짐없이 나타내는지는 아직 전제다. 동일 runtime 관측이 가능한 B1에 이를 제공하는 비용까지 포함한 완전한 기존 수정이 비교 기준이 될 수 있다.

hold, queue 정리, 재기준화, unpause의 올바른 순서와 acknowledgment는 기존 방법에서도 구현 가능하다. 불완전한 B1에서 순서 race가 나타나고 C1에서 나타나지 않는 결과만으로 공통 구조의 필요성을 입증할 수 없다. 최초 구현 실패와 올바른 개별 수정의 결과는 구분되는 기록이다.

## 2. C1의 정보 제한과 판정

C1이 fresh press를 관측하지 못한다는 것은 실패 원인의 설명이다. P_rearm을 요구하는 계약에 대해 재누름 없이 재개했다면 그 조건은 불충족이다. 부분 계약(P_stop/P_resume)과 전체 계약(P_stop/P_resume/P_rearm)은 별도로 평가된다. 충족할 수 없는 조건을 분모에서 빼고 전체 보호 성공으로 합산할 수 없다.

같은 runtime 증거를 사용한다는 말은 같은 입력 정보 전체를 갖는다는 뜻이 아니다. 각 비교군의 버튼·활성 상태·pose·EE·command 관측표와 정책 범위가 필요하다. information-limited 결과는 기존 방법의 불가능성을 뜻하지 않는다.

## 3. 무효 trial과 관측된 실패

R01의 특이점/충돌 stop과 50 ms 증거 공백을 일괄 무효 처리하는 규칙은 조건부 성공만 남길 위험이 있다. 시작 상태 미정착, 기록 손상 등 실행 이전·계측 문제와 시험 동작 때문에 발생한 안전 개입/지연/공백은 구분된다.

pre-flight 이후 resume 동작이 유발한 특이점/충돌 개입은 해당 구성의 결과다. 개입으로 보호 효과를 직접 판정할 수 없는 부분은 masked로 표시할 수 있으나, 실행 횟수·개입률·전체 결과에는 남는다. 증거 timeout/fail-closed로 인한 정상 차단도 가용성 결과다. 불리한 arm/조건만 재실행하여 성공 trial로 바뀌지 않는다.

## 4. liveness와 정상 clutch

영구 차단은 정지와 재누름 정책을 겉으로 만족시키지만 유효한 재허가 뒤 조작 가능성을 보장하지 않는다. 정상 재누름 이후 재개 지연과 추종 회복 조건이 추가로 필요하다. I1에서 fresh press 없이 정지 유지하는 B1과 I2에서 fresh press 후 재개하는 B1은 다른 기대 결과다.

N1의 정상 release 동안 의도한 hold는 오차단이 아니다. grip-held 정상 조작 및 유효 재허가 이후 필요한 움직임의 불필요한 억제가 정상 실패다. 재개가 없는 trial의 P_resume은 평가 불가로 남고 성공으로 합산되지 않는다.

## 5. re-basing의 의미

C1은 명령의 좌표·target link·absolute/relative 의미를 알아야 한다. target과 측정 EE의 SE(3) 합성 순서, translation/rotation 기준 좌표, 적용되는 epoch가 명시될 필요가 있다. 첫 목표가 연속적이어도 이후 정상 motion 의미가 바뀌면 보완 성공이 아니다. 병진·회전 및 두 동작의 결합을 독립 입력으로 확인하는 근거가 필요하다.

## 6. pre-flight의 한계

R01의 B0 N0/I1 성공만으로 축을 고르는 방식은 실제 문제 결과를 선별할 가능성이 있다. 중립적인 시작 pose/IK/작업공간·정착·의도한 정상 궤적의 실행 가능성을 기준으로 자격을 확인하는 편이 더 적절하다. 모든 arm의 동일한 초기 상태와 parameter는 본 trial 전에 고정된다.

고정 world target의 reachability나 kinematic singularity는 robot base 배치만 바꿔서 해결된다고 보장되지 않는다. 배치 변경은 frame·collision·목표 정의에 미치는 영향이 별도로 확인되어야 한다. 다른 팔 모델로 전환하면 별도 protocol의 다른 경로가 된다.

## 7. 측정과 반복

single host CLOCK_REALTIME은 clock jump 부재를 보장하지 않는다. 경과 시간은 monotonic 및 ROS/sim time과의 대응이 필요하며 injection 효력, collector 관측, 판정, Servo/controller 처리, EE 반응이 분리된다. 위협 정책의 onset은 각 arm의 detection 시각과 구분된다.

3회 반복은 탐색 pilot의 반복성 근거이며 희귀 실패 부재나 보편적 안전의 근거가 아니다. discordance 발생 후 반복을 늘리는 규칙은 freeze 전에 명시되고, 전체 실행과 추가 실행을 구분해 보고한다. 명령 수는 독립 trial 수로 해석되지 않는다.

## 8. 주장 범위

현재 actor는 S0, robot은 Gazebo이며 실제 앱이 synthetic remote input을 받는다. runtime/headset의 실제 focus 전환, 물리 로봇, 손상 앱 방어, 복수 구현의 일반화는 이번 pilot으로 입증되지 않는다. B1 순서 문제는 root-cause 및 기존 수정 가능성 확인 뒤 integration finding으로 기록된다.

## 저장소 정합성

CONTEXT의 과거 33–45 mm 요약은 최신 감사의 27.9–42.4 mm로 정정 대상이다. STATUS의 미착수 후보 문단은 완료된 감사/설계를 반영하지 못했다. 이번 검토에서 현재 DB 수치와 완료 단계로 맞췄다. 기존 R01은 draft 원문으로 보존된다.
