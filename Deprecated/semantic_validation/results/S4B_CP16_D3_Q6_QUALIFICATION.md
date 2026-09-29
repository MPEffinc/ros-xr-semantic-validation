# CP16 Docker D3 Q6 자격 검증 결과 (2026-09-28)

## 범위와 고정 조건

이번 checkpoint는 XRROS-S4-1.0.0 (SHA-256 `3a40337121f8d687dc68036ff2ffc85a1bc6eda275a700ba7d9e8119cd322969`)의 Docker D3 정식 비교를 위한 **설정·계측 자격 검증**이다. Q6 구현은 `13109a3d4ca18fa00d8a97be839afe39d33b67c4`에서 먼저 동결·push했다. Q6 프로토콜 XRROS-S4B-D3Q6-1.0.0 SHA-256은 `172b5d309d99e1b1e4ed2c3b805fc9093e772dcde89e50914f3899e38f5bfef0`이다. 이전 D3Q1–Q5, D1 48/50, D2 47/50 결과는 변경하지 않았다.

## 실제 실행과 결과

결과 root: [`runs/s4b_cp16_d3q6_20260928T032320Z/`](runs/s4b_cp16_d3q6_20260928T032320Z/). `commands.jsonl`은 격리된 trial-owned Docker/Gazebo 실행 명령을, `raw/<trial>/`은 각 trial의 원본 로그·입력·출력·종료 기록을 보존한다. `analysis/d3_qualification_audit.py`는 freeze 당시의 분석기이고 `analysis/d3_qualification_summary.json`이 계산된 판정이다. `runtime_evidence_manifest.sha256`의 760개 파일 해시는 `manifest_verification.txt`에서 재검증했다.

| Setup cell | 판정 | exact source-parent→Servo callback |
| --- | --- | ---: |
| B0 I_FULL | MEASUREMENT_QUALIFIED | 비계측 원본 |
| B0 observational shim I_FULL | MEASUREMENT_QUALIFIED | 312 |
| B1 I_NATIVE / I_FULL | 둘 다 MEASUREMENT_QUALIFIED | 311 / 312 |
| B2-native I_NATIVE / I_FULL | 둘 다 MEASUREMENT_QUALIFIED | 311 / 312 |
| B2-composed I_NATIVE / I_FULL | 둘 다 MEASUREMENT_QUALIFIED | 312 / 311 |
| B3 I_NATIVE / I_FULL | 둘 다 MEASUREMENT_QUALIFIED | 312 / 311 |

새 B0/shim 쌍은 동일한 100개 실제 source sample fixture에서 최대 source-index 시각 차이 **0.039295 ms**, 최종 여섯 관절 차이 **0.001574341 rad**로 동결된 5 ms / 0.02 rad 허용 범위를 만족했다. 각 cell은 계획된 120 slot 중 100개의 실제 source 전송과 20개의 무전송 slot, 별도의 300개 health tick, fault 이전 Gazebo 움직임, 전체 start ACK·clock·resource capture, post-capture bridge quiescence와 해당 source-parent Servo callback drain을 통과했다. B2의 네 cell은 각 calibration event에 대해 실제 official monitor→oracle→guarded receipt ACK를 얻었고, 이후 original source event association에 분석기상 누락이 없었다(각 original publication 655/678/645/660). Calibration은 sender sample이나 health tick으로 세지 않았다.

이 판정은 **방어 정책 성공이 아니다**. 이 setup 분석기는 D3의 정확한 250 ms local receipt timeout 후 decision/neutral request 50 ms, continuing nonzero controller 300 ms, Gazebo settle 1 s 등의 formal threshold를 채점하지 않는다. source→Servo callback까지만 event-level exact join이며, 특정 source→Servo 내부 선택/output→controller output→관절 변화의 1:1 parent는 UNKNOWN이다. Controller와 Gazebo는 별도 구간별 관측이다. 실제 Quest 또는 물리 로봇 결과가 아니다.

## 중간 중단과 다음 실행 조건

사용자 요청에 따라 여기서 일시중지했다. **D3 formal trial 0개**, formal schedule·분석기 freeze **아직 없음**, S5 `INSUFFICIENT_EVIDENCE`이다. 재개 시 Q6의 열 cell·해시를 재확인하고, XRROS-S4-1.0.0의 5회 반복/seed 20260922 및 별도 D3 정책 분석기를 정식 첫 trial보다 먼저 작성·preflight·commit-push해야 한다. 그 후에만 정식 Gazebo trial을 시작한다. Q6 setup PASS를 D3 formal PASS로 소급하지 않는다.
