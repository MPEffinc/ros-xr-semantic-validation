# Manual and Environment Requirements

## Current disposition

자동 검증은 안전한 범위까지 완료됐다. 남은 차단은 연구 finding이 아니라 **environment/privilege/hardware availability**다.

- Privilege escalation: **사용하지 않음**
- Docker/socket permission 변경: **수행하지 않음**
- Firewall/network configuration 변경: **수행하지 않음**
- Actual robot, robot driver, gripper, actuator: **연결·실행하지 않음**
- New Quest/Unity/NVIDIA hardware run: **수행하지 않음**

아래 수동 조치는 해당 시스템의 소유자 또는 승인된 사용자가 로컬 정책에 따라 수행해야 한다. `chmod 666 /var/run/docker.sock`, 임의 `sudo`, firewall disable, host networking, device mount는 요구하지 않으며 사용하지 말아야 한다.

## 1. Quest2ROS2 actual ROS transport — `BLOCKED_ENV`

### Observed blocker

현재 shell은 Docker client를 실행할 수 있지만 daemon socket에 연결하지 못했다.

```text
uid=1000(cclab), groups=cclab,nogroup
/var/run/docker.sock: srw-rw----, nobody:nogroup, 0660
docker info: permission denied
host ros2/colcon: not found
```

Socket group과 process supplementary group이 겉으로 일치해도 managed environment가 Unix socket access를 차단하므로, 무조건적인 group 추가나 mode 변경이 해결책이라는 근거는 없다. Image/container inventory도 열지 못했으므로 `ros-xr-humble:local` image가 없다고 결론내리지 않는다. Canonical raw probe는 [QUEST2ROS2_ROS_RUNTIME.md](QUEST2ROS2_ROS_RUNTIME.md)에 있다.

### Required manual environment action

시스템 관리자 또는 host owner가 **기존 정책상 Docker daemon access가 허가된 일반 host shell**을 제공해야 한다. 먼저 그 shell에서 read-only diagnostics만 실행한다.

```bash
cd /home/cclab/ros_xr
id
stat -Lc '%A %a %U:%G %n' /var/run/docker.sock
docker info
docker images --format '{{.Repository}}:{{.Tag}} {{.ID}}'
docker ps -a
docker compose -f ros_env/compose.yaml config --quiet
```

`docker info`가 성공할 때만 prepared robot-free harness를 실행한다.

```bash
cd /home/cclab/ros_xr
python3 semantic_validation/harness/run_quest2ros2_ros_runtime.py
```

Harness는 synthetic `PoseStamped` publisher → actual Quest2ROS2 node/callback → actual ROS publisher → dummy subscriber를 age/frame sweep하고, `--network none`, capability drop, `no-new-privileges`, no device mount, no robot/driver로 제한한다. 새 log는 `semantic_validation/logs/quest2ros2_ros_runtime/<run-id>/`에 생성된다.

이 실행이 PASS해도 synthetic pose source이므로 **actual ROS transport evidence**만 추가한다. Actual Quest tracking-state hardware confirmation으로 승격하지 않는다. Admin access가 계속 불가능하면 status는 `BLOCKED_ENV`로 유지한다.

## 2. PickNik decisive hardware run — `BLOCKED_ENV` + `BLOCKED_HW`

### Required environment

- Project-declared Unity `6000.1.6f1`과 호환되는 existing Unity editor
- Android Build Support, OpenJDK, Android SDK/NDK가 설치된 해당 editor environment
- USB debugging이 승인된 actual Quest와 `adb devices -l`에서 `device`로 보이는 연결
- `rclpy`, `nav_msgs`, `tf2_msgs` 및 robot-free `ros_tcp_endpoint`를 제공하는 ROS 2 shell
- Dummy ROS observer만 연결된 network; robot/MoveIt execution/driver는 연결하지 않음

현재는 Unity executable 없음, APK 없음, ROS 2 Python shell 없음, ADB-connected Quest 없음이다. Prepared instrumentation은 `MACHINE_CHECKED_STATIC READY`일 뿐 runtime result가 아니다.

### Build and observer commands

기존 compatible Unity/Android environment가 준비된 뒤 disposable project를 stage/build한다.

```bash
cd /home/cclab/ros_xr
python3 semantic_validation/harness/prepare_picknik_hw_project.py \
  --output /tmp/picknik_hw_run \
  --manifest semantic_validation/logs/picknik/<run-id>/hw_staging_manifest.json \
  --build-if-available \
  --apk /tmp/picknik_hw_run/Builds/picknik_semantic_validation.apk
```

Auto-detection이 안 되면 prepared project에 existing editor를 명시한다.

```bash
PICKNIK_VALIDATION_APK=/tmp/picknik_hw_run/Builds/picknik_semantic_validation.apk \
/path/to/Unity -batchmode -quit \
  -projectPath /tmp/picknik_hw_run/UnityProject \
  -executeMethod PickNikSemanticValidationBuild.BuildAndroid \
  -logFile semantic_validation/logs/picknik/<run-id>/unity_batch_build.log
```

별도 ROS 2 shell에서 dummy observer를 실행한다.

```bash
cd /home/cclab/ros_xr
python3 semantic_validation/harness/picknik_ros_observer.py \
  --output semantic_validation/logs/picknik/<run-id>/ros_observer.jsonl
```

APK install/launch와 Quest side-band 추출은 승인된 ADB 환경에서 수행한다. Package identifier는 `com.unity.template.vr`이지만 Development build의 `run-as` 지원은 실제 기기에서 확인해야 하며 가정하지 않는다. Environment별 launch activity를 확인하지 않은 상태에서 임의 command를 사용하지 않는다.

Run이 끝나면 두 raw stream을 결합한다.

```bash
cd /home/cclab/ros_xr
python3 semantic_validation/harness/picknik_hw_analyze.py \
  --sideband semantic_validation/logs/picknik/<run-id>/quest_sideband.jsonl \
  --ros semantic_validation/logs/picknik/<run-id>/ros_observer.jsonl \
  --output semantic_validation/logs/picknik/<run-id>/analysis.json
```

### Required physical procedure

1. Baseline에서 `isTracked=true`, Position+Rotation tracking bits, Transform motion, Odometry/TF reception을 동시에 확인한다.
2. Headset focus를 유지하고 controller를 tracking view 밖으로 3–5초 occlude한다.
3. 첫 tracking transition 뒤에도 1–2초 유지해 production Odometry/TF progression을 기록한다.
4. Controller를 복구하고 explicit user re-arm 없이 2초 이상 기록한다.
5. 다섯 valid transitions 또는 명시적 `HW_NO_LOSS_OBSERVED`까지 반복한다.

상세 classification과 production non-interference boundary는 [PICKNIK_HW_READY.md](PICKNIK_HW_READY.md)에 있다.

## 3. Independent Spes replication — manual Quest operation

현재 H1/H3는 actual Quest 3 한 device/session에서 valid T1 5/5로 확인됐지만 independent replication은 아니다. 별도 session, 가능하면 별도 Quest/browser/runtime로 반복할 때 existing detached helper를 사용한다. 이 명령은 새 server/run을 시작하므로 실제 실험을 수행할 시점에만 실행한다.

```bash
cd /home/cclab/ros_xr
QUEST_HOST=<quest-reachable-lan-ip> \
  semantic_validation/start_quest_experiment.sh <new-run-id> 4443
semantic_validation/status_quest_experiment.sh
```

Quest trial 종료 후:

```bash
cd /home/cclab/ros_xr
semantic_validation/stop_quest_experiment.sh
```

T1 replication과 controller-null viewer fallback H2, actual disconnect T4는 섞지 않는다. H2/T4 transition이 나오지 않으면 `NO_LOSS_OBSERVED`/`NO_DISCONNECT_OBSERVED`로 남기며 fail-closed evidence로 해석하지 않는다. No robot/ROS driver is required.

## 4. NVIDIA native trace — manual runtime/hardware environment

NVIDIA comparison은 linked release static check와 current-main synthetic tests까지만 완료됐다. Native confirmation에는 다음이 필요하다.

- Actual Quest/native OpenXR 또는 연구 대상 CloudXR path
- Linked release와 current main을 서로 다른 run으로 고정한 build/runtime
- Exact `POSITION_VALID`, `ORIENTATION_VALID`, `POSITION_TRACKED`, `ORIENTATION_TRACKED`, controller activity, query/update time의 side-band trace
- Retargeter output과 dummy ROS subscriber progression의 correlation
- Occlusion과 recovery 동안 explicit re-arm 여부, session/reconnect generation 기록

현재 repository에는 이 environment를 안전하게 launch하는 검증된 one-command harness가 없으므로 임의 install/launch command를 만들지 않는다. Robot과 SO-101은 필요하지 않으며 연결하지 않는다. NVIDIA issue #731의 contributor self-report는 실험 입력이나 독립 결과로 복사하지 않는다. 비교 경계는 [NVIDIA_VS_SPES_ANALYSIS.md](NVIDIA_VS_SPES_ANALYSIS.md)에 있다.

## 5. Priority and completion criteria

1. **환경만 복구:** Authorized Docker shell에서 Quest2ROS2 harness를 실행해 actual ROS transport 여부를 판정한다. 이는 I3 evidence upgrade이지 second XR hardware confirmation은 아니다.
2. **Primary manual experiment:** PickNik Quest-to-dummy-ROS를 실행한다. Repeated actual tracking transition과 production Odometry/TF dummy-endpoint progression이 확인될 때만 STRONG GO 후보로 재평가한다.
3. **Replication/alternative:** Independent Spes replication과 NVIDIA native exact-flag trace를 수행한다.

어떤 단계에서도 실제 robot/actuator consequence를 요구하지 않는다. Environment가 준비되지 않거나 semantic transition이 발생하지 않으면 `BLOCKED_ENV`, `BLOCKED_HW`, `NO_LOSS_OBSERVED`를 그대로 보존하며 PASS 또는 safety proof로 치환하지 않는다.
