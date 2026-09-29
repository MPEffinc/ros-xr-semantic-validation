# XR→ROS Semantic Validation

이 디렉터리는 XR tracking/source/freshness semantic이 ROS teleoperation 경로에서 어떻게 변하는지 고정 revision으로 감사하고, Quest/robot 없이 실행 가능한 경계를 재생하기 위한 독립 작업 영역이다. Upstream checkout은 수정하지 않는다.

## 현재 상태

- 정적 audit: Spes H1–H3, PickNik H4, Quest2ROS2 H5, NVIDIA H6 완료
- S1-A: 실제 `SpesRobotics/teleop`의 `teleop/index.html` inline script를 mock WebXR 환경에서 실행, PASS
- S1-B: 실제 `teleop.Teleop._Teleop__update`를 synthetic sequence로 실행, PASS
- Spes no-Quest suite: semantic collision + actual HTTPS/WSS reconnect/freshness/control/application replay 10 scenario PASS
- Quest2ROS2: actual `_pose_callback` age sweep/future stamp/stale trajectory/frame provenance PASS (`RUNTIME WITH SYNTHETIC SOURCE`); ROS graph는 `BLOCKED_ENV`
- PickNik: `ROSPublishers.cs` 10개 machine-check PASS; Unity runtime은 `BLOCKED_ENV`
- NVIDIA: linked-release 8개 static check와 current-main upstream test 10개 PASS
- Integrated canonical run `no_quest_20260830T142000Z`: 7 PASS, 0 FAIL, 2 SKIP_ENV, 4 BLOCKED_HW
- ROS dummy sink: 구현 완료, 호스트 ROS 2 부재 및 Docker API 접근 제한으로 실행하지 않음
- Spes Quest hardware instrumentation: DOM overlay와 2.5 m 전방의 stereo world-space WebGL HUD, audio/left-controller operator, 별도 experiment WSS와 actual server ACK, payload equivalence 및 live endpoint preflight PASS
- Quest hardware run `spes_quest_hw_20260831T001349Z`: T0 PASS, valid T1 `HW_EMULATED_CONTINUES` 5/5, no-user-rearm recovery 5/5; controller-null fallback과 real disconnect는 NOT OBSERVED
- Quest raw independent re-analysis: 주요 field 129개 mismatch 0, `INDEPENDENT_REANALYSIS_PASS`; descriptive hardware summary는 emulated/continuation/no-rearm 5/5와 loss-window jump reject 4/5
- Recovery classifier: loss detection 이후 jump만 집계하도록 수정; actual T1-1 continuous, T1-2~5 jump-reject/re-anchor regression PASS; invalid/session-generation exclusion PASS
- Instrumentation integrity: frontend 7-case exact serialized payload/send decision과 server wrapper 12-case callback/state/exception differential PASS, `INSTRUMENTATION_NON_INTERFERENCE_PASS`
- PickNik deep validation: tracking state가 exact controller Transform driver까지 연결된 뒤 `Transform -> Odometry/TF`에서 소실됨을 33/33 `SOURCE_DATAFLOW_CONFIRMED`; Unity/Quest/ROS runtime은 미실행
- Quest2ROS2 actual ROS retry: Docker daemon authorization으로 `BLOCKED_ENV`; actual ROS transport evidence로 승격하지 않음
- NVIDIA revalidation: linked release 8/8 machine checks, current-main validity/recovery test 10/10 PASS; `VALID`는 gate하지만 `TRACKED` 보존은 확인되지 않음
- Autonomous suite `semantic_validation_20260831T153536Z`: 11 PASS, 0 FAIL, 2 SKIP_ENV, 1 BLOCKED_HW; current decision `GO — NOT STRONG GO`
- Robot/controller/driver: 연결하거나 구동하지 않음

판정과 근거는 [results/EVIDENCE_LEDGER.md](results/EVIDENCE_LEDGER.md), [results/INVARIANT_MATRIX.md](results/INVARIANT_MATRIX.md), [results/RESEARCH_DECISION.md](results/RESEARCH_DECISION.md)에 정규화했다. Quest raw 재분석은 [results/SPES_HW_REANALYSIS.md](results/SPES_HW_REANALYSIS.md), instrumentation 검증은 [results/SPES_INSTRUMENTATION_INTEGRITY.md](results/SPES_INSTRUMENTATION_INTEGRITY.md), PickNik deep path는 [results/PICKNIK_DEEP_VALIDATION.md](results/PICKNIK_DEEP_VALIDATION.md), 전체 보고는 [results/AUTONOMOUS_VALIDATION_REPORT.md](results/AUTONOMOUS_VALIDATION_REPORT.md)에 있다.

## 현재 workspace 조사

초기 workspace 조사는 `2026-08-30T21:45:46+09:00`, 이번 autonomous 재검증은 `2026-09-01` KST에 수행했다.

- `/home/cclab/ros_xr` 자체는 Git repository가 아니다. `frameworks/` 아래의 COMPAS XR, COMPAS Unity Assembly, HORUS, HORUS ROS 2, HORUS SDK가 각각 독립 Git checkout이며 조사 당시 모두 clean이었다.
- 기존 연구 문서는 `RESEARCH_CONTEXT.md`, `XR_BRIDGE_ANALYSIS.md`, `EXPERIMENT_RESULTS.md`, `AUTHORIZATION_CONTINUITY_RESULTS.md`, `DECISIVE_FOLLOWUP_RESULTS.md`, `XR2ACT_DECISIVE_RESULTS.md`, `XR_NAV2_FEASIBILITY_RESULTS.md`이다.
- 기존 ROS workspace는 `ros_env/ros2_ws`이고 자체 package는 `origin_test` 하나다. 기존 `ros_env/Dockerfile`은 ROS 2 Humble/Jammy, colcon, NumPy, SROS2, rosbridge, TF 관련 package를 설치하도록 구성돼 있다.
- 기존 Quest2ROS2 ROS-side 결과와 raw evidence가 있지만, 이번 freshness/re-stamping audit 및 Spes S1과는 구분해 보존했다.
- 호스트: Ubuntu 24.04.3, Python 3.12.3, Node 22.22.2, npm 10.9.7, Git 2.43.0, CMake 3.28.3, Docker CLI 29.1.3.
- 호스트에서 `ros2`, `colcon`, `pytest`, `pip3`는 없었다. `python3 -m venv`는 `python3.12-venv` 부재로 생성되지 않았다.
- Docker daemon socket은 이 세션에서 `permission denied`였다. 기존 image/container의 live 상태는 `UNKNOWN`; 기존 문서의 과거 성공 기록을 현재 상태로 간주하지 않았다.

## 구조

```text
semantic_validation/
├── audit/                  # canonical static audit
├── harness/                # upstream 외부의 S1, hardware runner, ROS sink
├── instrumentation/        # frontend observer source
├── instrumented/           # fixed upstream에서 생성한 별도 working copy
├── logs/                   # 실행으로 생성되는 raw JSONL
├── results/                # canonical runtime result
└── targets/                # 수정하지 않는 shallow upstream checkout
```

## 고정 target

| Target | Branch / commit |
| --- | --- |
| SpesRobotics/teleop | `main@c5d808155a87b584d6147a5943d4b87c34c92db0` |
| PickNikRobotics/meta_quest_teleoperation | `main@bbaef0762fdb0b429b8ea12a4ca65040748b41dd` |
| Taokt/Quest2ROS2 | `main@07aaf65149c9e29103f1fc61deb466cef8a55cef` |
| NVIDIA-ISAAC-ROS/isaac_ros_teleop | `main@197f5cd9ff2cbd90533a93c67be2a661319048ba` |
| NVIDIA/IsaacTeleop current comparison | `main@9fba23c4a3bd5b6de732cac77a47f471fca25276` |
| Isaac ROS Teleop의 실제 gitlink | `IsaacTeleop@465ce637120ac35404f5f741a9f25f3f1a1a25ea` (`release/1.3.x`) |

세부 clone 시각과 최근 commit date는 audit의 revision table에 있다.

NVIDIA current-main test는 local `9fba23c4`에서 실행했다. 재검증 당시 official remote main `334978b0ee73ce3e9102a22bd4c889d8b77dcf82`는 local HEAD의 direct child였고 semantic files는 SHA-256 동일했지만, 실행 revision과 remote revision을 같은 것으로 쓰지 않는다.

## S1 재실행

Node harness는 추가 package가 없다. Python server replay는 시스템을 변경하지 않도록 임시 target directory를 쓴다.

```bash
cd /home/cclab/ros_xr
curl -fL https://bootstrap.pypa.io/pip/pip.pyz \
  -o /tmp/ros_xr_semantic_pip.pyz
python3 /tmp/ros_xr_semantic_pip.pyz install \
  --target /tmp/ros_xr_semantic_deps \
  -r semantic_validation/harness/requirements-s1.txt
SEMANTIC_PY_DEPS=/tmp/ros_xr_semantic_deps \
  semantic_validation/harness/run_s1.sh
```

생성 로그:

- `logs/s1_frontend.jsonl`
- `logs/s1_server_replay.jsonl`

`run_s1.sh`는 WebXR/Unity/ROS/robot을 시작하지 않는다. 첫 명령은 실제 upstream HTML script를 sandboxed mock object와 함께 실행하고, 둘째 명령은 네트워크 server를 시작하지 않은 채 upstream private update method에 synthetic message를 직접 전달한다.

## Integrated no-Quest regression

Spes actual WSS suite, Quest2ROS2 callback, PickNik machine check, NVIDIA positive control과 legacy S1을 한 번에 실행한다. 한 component가 실패해도 나머지를 계속하며 `PASS`, `FAIL`, `SKIP_ENV`, `BLOCKED_HW`를 분리한다.

```bash
cd /home/cclab/ros_xr
python3 /tmp/ros_xr_semantic_pip.pyz install \
  --target /tmp/ros_xr_nvidia_deps \
  -r semantic_validation/harness/requirements-nvidia.txt
SEMANTIC_PY_DEPS=/tmp/ros_xr_semantic_deps \
NVIDIA_PY_DEPS=/tmp/ros_xr_nvidia_deps \
  ./run_no_quest_validation.sh
```

Spes dependency setup은 위 S1 절과 `requirements-hardware.txt`를 사용한다. Runner는 Quest나 robot을 시작하지 않는다. Quest-only 항목은 실패 대신 `BLOCKED_HW`, Docker/Unity 부재는 `SKIP_ENV`로 남긴다. Raw logs는 `logs/no_quest/<run-id>/` 아래 JSONL로 보존된다.

## Autonomous integrated validation

기존 no-Quest runner를 유지하면서 raw Quest re-analysis, classifier regression, full hardware preflight, instrumentation differential, Quest2ROS environment/runtime probe, PickNik deep/staging/self-tests, NVIDIA tests, semantic-binding oracle를 계속 실행하는 상위 runner다. 한 component가 실패해도 나머지를 계속하며 `PASS`, `FAIL`, `DISPROVED`, `SKIP_ENV`, `BLOCKED_HW`로 정규화한다.

```bash
cd /home/cclab/ros_xr
semantic_validation/run_semantic_validation.sh
```

Canonical run은 `semantic_validation/logs/semantic_validation_20260831T153536Z/summary.jsonl`이다. 이 sandbox에서는 loopback socket 생성이 금지돼 live HTTPS/WSS 재실행이 `SKIP_ENV`였고 Docker daemon도 `SKIP_ENV`였다. 이는 이전 canonical WSS runtime PASS를 무효화하지 않지만, 이번 run에서 네트워크 test를 재확인했다고 주장하지도 않는다. `BLOCKED_HW`는 남은 manual Quest/Unity/NVIDIA activation을 뜻한다.

## ROS dummy sink

ROS 2가 source된 환경에서 다음 sink는 `target_frame`과 `/tf`만 구독한다. 어떤 command도 publish하지 않는다.

```bash
python3 semantic_validation/harness/ros_dummy_sink.py \
  --output semantic_validation/logs/ros_dummy_sink.jsonl \
  --run-id <same-hardware-run-id> \
  --target-topic target_frame \
  --tf-topic /tf \
  --duration-sec 30
```

기존 local image가 실제로 존재하고 Docker 접근이 복구된 뒤에는 다음처럼 read-only source mount로 sink만 실행할 수 있다.

```bash
cd /home/cclab/ros_xr
docker run --rm --network host \
  -v "$PWD:/workspace:ro" \
  -v "$PWD/semantic_validation/logs:/logs" \
  ros-xr-humble:local \
  bash -lc 'source /opt/ros/humble/setup.bash && python3 /workspace/semantic_validation/harness/ros_dummy_sink.py --output /logs/ros_dummy_sink.jsonl --run-id <same-hardware-run-id> --duration-sec 30'
```

Rosbag2를 함께 쓸 때도 robot topic이나 hardware driver를 launch하지 않는다.

```bash
ros2 bag record -o semantic_validation/logs/s1_rosbag target_frame /tf
```

## Spes Quest hardware instrumentation

Hardware dependency는 host Python을 변경하지 않고 임시 target directory에 설치한다. `websockets`는 실제 WSS upgrade에 필요하다.

```bash
python3 /tmp/ros_xr_semantic_pip.pyz install \
  --target /tmp/ros_xr_semantic_deps \
  -r semantic_validation/harness/requirements-hardware.txt
```

Quest나 robot 없이 전체 instrumentation preflight를 재실행한다.

```bash
SEMANTIC_PY_DEPS=/tmp/ros_xr_semantic_deps \
  python3 semantic_validation/harness/run_spes_hardware_preflight.py --overwrite
```

Preflight는 fixed revision/clean status, 별도 frontend 생성, actual `onXRFrame()` control payload 동등성, `emulatedPosition` side-band, actual server update callback/jump/anchor observer, DOM overlay runtime probe, framework 없는 stereo world-space WebGL HUD fallback, speech/Web Audio fallback, left-controller-only control, HTTPS, production WSS와 별도 `/experiment` WSS/ACK를 확인한다. WebGL fallback은 HUD를 양안 projection에 맞춰 시야 전방 2.5 m의 1 m 패널로 그린다. 이 PASS는 Quest hardware 실행을 뜻하지 않는다.

Hardware run은 terminal marker를 사용하지 않는다. Quest에서 `START WEBXR`를 누른 뒤 HUD/audio와 left trigger만으로 T0/T1을 진행한다. 다음 helper는 preflight 후 detached server를 시작하며, 현재 host에서는 user systemd service를 사용한다.

```bash
cd /home/cclab/ros_xr
SEMANTIC_PY_DEPS=/tmp/ros_xr_semantic_deps \
  QUEST_HOST=<quest-reachable-host-ip> \
  semantic_validation/start_quest_experiment.sh <run-id> 4443

semantic_validation/status_quest_experiment.sh
semantic_validation/stop_quest_experiment.sh
```

MOVE button은 production `teleopJoystick.isMotionEnabled()`이 `TRUE`가 되는 오른쪽 버튼을 사용자가 HUD로 확인한다. Left trigger short press는 시작/다음 trial, 2초 이상 long press는 manual abort다. Focus/visibility/input-source/WebSocket 변화는 자동 기록한다. T0 후 T1 valid trial 5회를 수행하고 T4는 선택 사항이다.

Hardware raw log는 `logs/quest_hw/<run-id>/experiment.jsonl`, server update는 같은 directory의 `server.jsonl`에 생성된다. `control_packet_index`, `server_update_index`, callback, jump reject와 target delta를 함께 기록한다.

## 현재 blocker와 다음 단계

현재 S1은 controller→viewer 선택과 server target 계산까지 확인했다. `teleop.ros2`가 `target_frame`을 publish하는 경로는 정적으로 확인했지만, 이 세션에서는 ROS message 수신을 runtime으로 확인하지 못했다.

Actual Quest 3 T0/T1은 run `spes_quest_hw_20260831T001349Z`에서 완료됐다. 다음 hardware 단계는 독립 session/device replication 또는 controller-null/viewer-fallback을 실제로 발생시키는 targeted H2 protocol이다. Docker socket 접근은 계속 거부돼 ROS sink/rosbag은 `NOT RUN`이며 이번 downstream evidence는 server target callback까지다. sudo/firewall/network 설정은 자동 변경하지 않는다.

## 보존 원칙

- `targets/`의 upstream source를 patch하지 않는다.
- JSONL raw log를 결과 문서와 분리한다.
- `CONFIRMED_STATIC`, `HYPOTHESIS`, `UNKNOWN`을 혼용하지 않는다.
- `P/D/R/A/G/U`는 audit에 정의된 stage-local 분류다.
- Quest finding은 이번에 관측된 non-null `emulatedPosition=true` path로 한정하며 controller-null fallback, disconnect, 다른 browser/runtime/device로 일반화하지 않는다.
- 실제 robot actuation은 이 작업 범위에 포함하지 않는다.
