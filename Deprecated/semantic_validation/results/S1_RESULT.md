# S1 Result — Controller → Viewer Semantic Substitution

## 목적과 범위

Right controller pose가 unavailable한 WebXR frame에서 Spes frontend가 viewer pose를 선택하고, 그 pose가 기존 controller control stream과 구분되지 않은 채 server target 계산에 들어갈 수 있는지 확인했다.

실제 Quest, browser WebXR runtime, ROS 2 runtime, robot은 사용하지 않았다. S1-A는 실제 upstream HTML script를 mock WebXR API로 실행했고, S1-B는 실제 upstream Python update method를 synthetic sequence로 실행했다.

## 고정 revision과 환경

- Target: `SpesRobotics/teleop main@c5d808155a87b584d6147a5943d4b87c34c92db0`
- Commit date: `2026-07-17T12:17:58+02:00`
- S1-A: Node `v22.22.2`, 실행 source `teleop/index.html` inline script
- S1-B: Python `3.12.3`, NumPy `2.5.2`, 실행 source `teleop.Teleop._Teleop__update`
- Upstream patch: 없음
- Robot/hardware connection: 없음

재실행:

```bash
cd /home/cclab/ros_xr
SEMANTIC_PY_DEPS=/tmp/ros_xr_semantic_deps \
  semantic_validation/harness/run_s1.sh
```

## S1-A — actual frontend script

Harness는 upstream `teleop/index.html`의 inline script를 직접 읽어 Node VM에서 실행했다. `XRSession`, `XRFrame`, `inputSources`, gamepad, `WebSocket`, DOM만 mock했다. 별도로 복사한 source-selection 함수가 아니다.

| Case | Controller pose | Viewer pose | Move | 실제 WebSocket payload position | 결과 |
| --- | --- | --- | --- | --- | --- |
| controller available | `(0.1, 0.2, 0.3)` | `(9, 9, 9)` | false | `(0.1, 0.2, 0.3)` | PASS — controller 선택 |
| controller null | null | `(1.1, 1.2, 1.3)` | false | `(1.1, 1.2, 1.3)` | PASS — viewer fallback |
| controller null + move | null | `(2.1, 2.2, 2.3)` | true | `(2.1, 2.2, 2.3)`, `move=true` | PASS |

세 packet 모두 `device="VR"`였고 `source`, `tracking_valid`, `emulatedPosition`, source timestamp field는 없었다.

Raw log: `logs/s1_frontend.jsonl`  
SHA-256: `899fb0d3f912bb33ddf2e963d65ee93e1d7cd3ede46e4493534d0f842b8d6604`

## S1-B — actual server replay

Input은 source identity가 없는 upstream 형태이며 모두 `device="VR"`, `move=true`, identity orientation이었다. 좌표는 WebXR input 좌표이고 아래 target은 upstream RUB→FLU 변환 후 translation이다.

| Step | Input | Callback | Anchor/previous state | Target translation | 판단 |
| --- | --- | --- | --- | --- | --- |
| 1 | controller P1 `(0, 0, 0)` | yes | anchor set, previous clear | `(0, 0, 0)` | initial anchor |
| 2 | controller P2 `(0, .02, 0)` | yes | anchor retained, previous set | `(0, 0, .02)` | controller motion accepted |
| 3 | viewer Q1 `(1, 0, 0)` | no | anchor cleared, Q1 saved as previous | `(0, 0, .02)` | first source jump rejected |
| 4 | viewer Q2 `(1.02, 0, 0)` | yes | Q2 becomes new anchor, previous clear | `(0, 0, .02)` | nearby viewer pose accepted/re-anchored |
| 5 | viewer Q3 `(1.04, 0, 0)` | yes | viewer trajectory continues | `(0, -.02, .02)` | control target changed |

Callback label sequence는 `P1, P2, Q2, Q3`였다. 따라서 Q1 하나의 reject 뒤 Q2가 새 reference로 수용되고 Q3부터 viewer-relative motion이 target에 반영됐다.

Raw log: `logs/s1_server_replay.jsonl`  
SHA-256: `ea6127bf4808f8e704894b88036358c57b2f27136d65ca313cb7d251d22ef3d9`

## PASS / FAIL

| 질문 | 결과 |
| --- | --- |
| controller→viewer fallback 재현 | **PASS** |
| viewer fallback과 `move=true` 결합 | **PASS** |
| 첫 viewer pose jump reject | **PASS** |
| 이후 nearby viewer trajectory 수용 | **PASS** |
| 수용된 viewer trajectory가 server target 변경 | **PASS** |
| ROS `target_frame` runtime 수신 | **NOT RUN** — 호스트 ROS 2 부재, Docker API 접근 제한 |
| 실제 Quest tracking loss에서 `getPose()==null` 발생 | **UNKNOWN** |

## 정적 확인과 남은 가설

### CONFIRMED_STATIC

- `frame.getPose(right targetRaySpace, local-floor)`가 null이면 `frame.getViewerPose(local-floor).views[0]`을 선택한다.
- fallback payload에는 controller/viewer identity, tracking validity, `emulatedPosition`, XR sample timestamp가 없다.
- `move`는 right gamepad button state에서 읽혀 선택된 pose와 결합된다.
- server는 source field를 검사하지 않고 spatial jump만 검사한다.
- ROS interface는 output `PoseStamped`와 TF header를 `node.get_clock().now()`로 생성한다.

### HYPOTHESIS

- Quest 3 browser/runtime에서 controller tracking obstruction이 실제로 `getPose()==null`을 만든다.
- 실제 WebSocket reconnect 중 기존 XR session/gamepad move state와 server anchor가 예상대로 유지된다.
- 실제 ROS subscriber가 Q2/Q3에 해당하는 target을 수신한다.

### UNKNOWN

- Quest runtime이 controller loss 때 null, frozen pose, emulated pose 중 무엇을 언제 반환하는지.
- 실제 application focus/session transition과 fallback 사이의 ordering.
- end-to-end latency와 browser별 차이.

## 연구 판단

**PROMISING, NEEDS QUEST VALIDATION**

공개 구현의 source alias와 jump-recovery mechanism은 정적 분석뿐 아니라 source-faithful software replay에서 확인됐다. 그러나 실제 Quest controller obstruction에서 non-null pose의 `emulatedPosition=true` 또는 controller-null fallback이 발생하는지는 아직 확인되지 않았으므로 `STRONG CANDIDATE`로 올리지 않는다.

Primary criterion: Quest 3에서 controller tracking loss 중 `controllerPose != null`, `emulatedPosition=true`, `move=true`, downstream target 지속이 함께 관측되면 hardware tracking-semantic loss를 지지한다. `emulatedPosition` 변화가 전혀 없으면 device path를 `UNKNOWN`으로 남긴다. Controller-null은 secondary path이며, 한 번도 발생하지 않으면 `DEVICE PATH NOT OBSERVED`로 기록하고 S1 synthetic evidence를 폐기하지 않는다.

## 다음 Quest 3 실험

실제 robot/controller driver는 시작하지 않고 dummy sink만 사용한다.

1. 별도 visible terminal에서 frontend packet log, Spes server warning/callback log, ROS dummy sink를 같은 run ID로 시작한다.
2. 한국어로 실험 목적과 controller obstruction 동작을 설명한 뒤 `준비 완료`를 기다린다.
3. `INSTRUCTION → WAIT_READY → COUNTDOWN → CAPTURE` 순서로 T0 정상 controller tracking과 target 대응을 기록한다.
4. T1은 `move=true`를 유지한 채 HMD tracking은 보존하고 right controller positional tracking만 2–5초 가리는 방법으로 5회 반복한다.
5. 각 T1에서 source 존재, pose null 여부, `emulatedPosition`, 선택 source, callback/target, recovery correction과 jump reject/reaccept를 함께 기록한다.
6. controller-null이 실제 관측된 경우에만 T3 viewer fallback을 hardware path로 분석한다. 관측되지 않으면 `DEVICE PATH NOT OBSERVED`다.
7. T4 disconnect는 tracking loss와 별도 trial로 수행한다. focus loss가 생기면 해당 trial을 폐기하고 같은 phase를 다시 시작한다.
8. `FINISHED` 후 frontend semantic event와 server update를 control packet order로 정렬한다. ROS가 가능할 때만 같은 run ID의 `target_frame`/TF를 추가한다.

## Privileged command

완료된 S1-A/S1-B에는 privileged command가 없다. ROS/Docker 단계는 이 자동화 세션에서 실행하지 않았다. 사용자 terminal에서 먼저 다음 비-sudo 명령으로 group/session 상태만 확인한다.

```bash
newgrp docker
docker info
```

계속 거부되면 sudo로 socket permission을 임의 변경하지 말고 host Docker 설정을 점검해야 한다.
