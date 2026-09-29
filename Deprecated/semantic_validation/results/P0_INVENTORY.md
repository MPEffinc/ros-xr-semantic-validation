# P0 컨텍스트·증거·실행환경 인벤토리 (2026-09-22)

## 범위와 판정

이 문서는 새 실험을 실행하지 않은 읽기 전용 점검 결과다. `DEFENSE_FRAMEWORK_EXECUTION_PLAN_V1.md`는 GitHub에 있던 **참고 초안**이며, 본 인벤토리와 함께 추가된 `SEMANTIC_VALIDATION_EXECUTION_PLAN_V2.md` 및 `SEMANTIC_VALIDATION_STATUS.md`가 이후 작업의 로컬 기준이다. 원시 evidence, 원본 upstream source, Docker/Pi/네트워크 설정은 수정하지 않았다.

P0 상태는 **DONE**이다. 완료 범위는 현재 Git·원시 데이터·재사용 가능한 source/image/path·Pi 역할의 확인 및 결과 문서화이며, raw 내용의 재분석이나 ROS/Gazebo/Quest 실행은 하지 않았다.

## Git 기준과 동기화

- 저장소/branch: `MPEffinc/ros-xr-semantic-validation`, `main`.
- 점검 시작 local HEAD 및 당시 `origin/main`: `1f4b64e86f5eeba564798c241a7d65f591d409a8`.
- `git fetch --prune origin` 뒤 `origin/main`은 `81a8b60a125d523820f7c2bc284302fbb1f59416`으로 전진했다.
- `HEAD..origin/main` 변경은 `semantic_validation/results/DEFENSE_FRAMEWORK_EXECUTION_PLAN_V1.md` 하나의 추가뿐이었다. 사용자 untracked 파일과 path 충돌이 없어 `git merge --ff-only origin/main`으로 안전하게 동기화했다.
- 동기화 직후 local HEAD=`origin/main`=`81a8b60a125d523820f7c2bc284302fbb1f59416`.
- 동기화 전에 사용자/기존 연구 산출물로 보이는 untracked Quest run roots, PickNik staging logs, `GPT_HANDOFF_20260917.md`, `quest_wireless_adb.sh`가 있었다. 삭제·reset·clean·stash는 하지 않았다. 이들 중 연구 evidence/운영 handoff는 본 커밋에서 명시적으로 포함하되, APK·Unity cache·credential은 발견·추가하지 않았다.

## 2026-09-17 이후 우선 결과의 경계

| Stack | 현재 local evidence가 뒷받침하는 범위 | 명시적 한계 |
| --- | --- | --- |
| PickNik | 실제 Quest side-band `isTracked=false, trackingState=0`와 원본 `ROSPublishers`의 Odometry/TF가 robot-free observer에서 계속 발행된 동일 실행 (`PICKNIK_QUEST_FEASIBILITY_20260917.md`) | 원본 robot-control consumer, MoveIt, physical robot은 미확인 |
| Spes | 실제 Quest WebXR→원본 server→pinned upstream ROS2→DDS→Pi observation 경로. Pi는 5,197 header stamp를 포함했지만 4,100 extra record가 있어 strict 1:1은 불가 (`SPES_QUEST_NATIVE_ROS_FEASIBILITY_20260917.md`) | Pi는 `PI_RECEIVED` observation sink이며 controller/actuator가 아님 |
| Quest2ROS2 | actual Quest→NUL/CDR-compatible **외부 bridge adaptation**→변경 없는 `RightArmController`→target topic. XR tracking state는 black box (`QUEST2ROS2_QUEST_FEASIBILITY_20260917.md`) | CLIK final consumer, physical robot, tracking-loss attribution은 없음 |
| Docker_Teleop | synthetic TCP→원본 receiver/mapper/MoveIt Servo→Gazebo 기존 D1/D2/D3 및 2026-09-17 actual Quest app→동일 Gazebo-only path artifact | D1–D5는 synthetic; 2026-09-17 system `POSITION/ORIENTATION` 전환은 `OVRInput.GetConnectedControllers()` 기반 `tracked`와 동의어가 아님; no physical robot |
| OpenVR UR5e | fake OpenVR→원본 `quest_teleop.py`→MoveIt Servo→Gazebo. `bPoseIsValid=false` gate, `Running_OutOfRange`는 drop (`OPENVR_UR5E_DOWNSTREAM_RUNTIME.md`) | fake input E2이며 native Quest/ALVR/SteamVR 혹은 physical robot 결과가 아님 |

## 원시 evidence manifest

해시는 이번 P0에서 실제 파일에 대해 계산했다. `JSONL`은 newline-delimited JSON, `DB3`은 SQLite3 ROS bag storage이며 이 표의 `원시/분석` 표시는 evidence level이 아니라 파일 역할이다.

| 범주 | 파일 (상대 경로) | bytes / 형식 | SHA-256 | 대응 문서·범위 |
| --- | --- | ---: | --- | --- |
| PickNik actual Quest 원시 | `results/runs/hw_picknik_native_20260917T074600Z/sideband_final.jsonl` | 15,449,362 / JSONL | `313eaa39ebd4c07df4e3791e943d7bf2fc983971d34ea0de55c0b74bc91de062` | PickNik feasibility의 Quest state side-band |
| PickNik ROS 관측 원시 | `results/runs/hw_picknik_native_20260917T074600Z/ros_observer.jsonl` | 24,156,047 / JSONL | `7e1fdcfd05cd8a85145b33ac9ca1b1b57e852d8852f7383910e0f7bdb171c43c` | 동일 실행의 robot-free Odometry/TF observer |
| PickNik 분석 | `results/runs/hw_picknik_native_20260917T074600Z/hardware_analysis_final.json` | 14,220 / JSON | `c0ca90cd480df69f7912452fd12ce958c0f92a6c0eb430ead1248e744c0a3f2d` | 3개 제외되지 않은 right interval 분류; P0가 내용 재검증한 것은 아님 |
| Spes actual Quest 원시 | `results/runs/hw_spes_native_20260917T081300Z/experiment_sideband.jsonl` | 797,634 / JSONL | `0d479b95aae2957ddf82aa10f08333281ff0bfa2c954cada83e966014dae6797` | actual WebXR side-band |
| Spes ROS/Pi 원시 | `results/runs/hw_spes_native_20260917T081300Z/native_ros_observer.jsonl` | 2,370,488 / JSONL | `516d0c7dd61a8608aa85fe610a78d96398d1d0664159ca2bd7d6e6d466302b72` | upstream ROS output observer |
| Spes Pi 원시 | `results/runs/hw_spes_native_20260917T081300Z/pi_sink.jsonl` | 6,126,601 / JSONL | `e5e1cadbed9abbad2bb8f552a0cb3eeec89438c81d9ee82fae546079d35582cd` | Pi reception only; strict one-to-one 미성립 |
| Quest2ROS2 actual baseline | `results/runs/hw_quest2ros2_cdr_20260917T093000Z/bag/bag_0.db3` | 1,253,376 / SQLite3 DB3 | `bf23dea2f3c4abad4348d0e5613dfc948fd0af4f8525914014a4d9990a8613f2` | CDR-compatible bridge→unchanged controller baseline |
| Quest2ROS2 actual visibility | `results/runs/hw_quest2ros2_visibility_20260917T094000Z/bag/bag_0.db3` | 1,511,424 / SQLite3 DB3 | `409a46dc5c642c74e8d5a1d339d3d8269750ffe40afff9558f738566a9fbae1e` | `NO_TRANSITION_OBSERVED`; this root has no `metadata.yaml` |
| Docker synthetic Gazebo | `results/runs/docker_teleop_e2e_20260914/bag/docker_teleop_e2e_bag_0.db3` | 1,126,400 / SQLite3 DB3 | `43537a60d205cefc3d95a9f751eb02010ce852b27c3c8b099ccb5379270a1fea` | D1 0.134070 m / D2-D3 settling after halt; existing offline extraction |
| Docker actual Quest→Gazebo | `results/runs/hw_docker_native_20260917T071824Z/bag/bag_0.db3` | 42,950,656 / SQLite3 DB3 | `064e5985da6c11f730ec67ef07ee3e594b837327f3dfef3328dc9799598d763d` | actual official app to Gazebo-only run; no physical robot |
| Docker device-state raw | `results/runs/hw_docker_native_20260917T071824Z/quest_system_tracking_t02.log` | 985,092 / text | `5e0b87b45eb738fb4b8f0279fadb9aa35655d25f95f782c3956a498f91aa5900` | system `POSITION/ORIENTATION` trace; not app `isTracked` proof |
| OpenVR fake-input Gazebo | `results/runs/openvr_ur5e_downstream_20260914T065659Z/W1_downstream.json` | 852,794 / JSON | `c820e80405a6b4545988b941f37258d7005e0805c115c81e9dcc10af1ba023ae` | fake `Running_OK`; ROS/Servo/joint capture |
| OpenVR fake-input Gazebo | `results/runs/openvr_ur5e_downstream_20260914T065659Z/W2_downstream.json` | 845,699 / JSON | `4de36c556141a197305101e0430be14d0745614c820193a080dcab621fa33fb7` | fake `Running_OutOfRange`; comparison capture |
| OpenVR aggregate | `results/runs/openvr_ur5e_downstream_20260914T065659Z/summary.json` | 4,062 / JSON | `0779985a5c3e8e540291e3b860aadb59fd96cbac049c13dd581e6a8be2ec99a2` | W0-W3 summary; original detailed captures remain in run root |

Other preserved Quest2ROS2 diagnostic DB3 bags exist: `native` (24,576 B; `1d1d10a4d867d5a871afde0ae95a964a68524713b1a5a1088803aa6512aeaa95`), `compat` (1,003,520 B; `d18f4332ea96583fc792e9b2711ddb7546dcd225a1c429022ec1d531972a5b27`), `offset20` (1,376,256 B; `57fd78473fa140fdbcb0d65e4c7f8b3fbed5b7cfa2a38a28406f42464805f1aa`), and `probe` (512,000 B; `aa7daf207d9b9d292a891bbd391266c85c273895c9e13fc670b39e3b0536c8f7`).

## 재사용 가능한 source·환경

| 경로 | 확인 상태 | 재실행 시 사용할 범위 |
| --- | --- | --- |
| `semantic_validation/targets/docker_teleop` | clean Git worktree, `Noah727/Docker_Teleop@64cbdde88bc52c6a80d37f994752e50f95ba537e` | mounted original `ros_backend1.1/src` and `simulation`; simulator-only `run_tabletop_sim.sh` + `servo_gz.launch.py`, receiver/mapper/bridge. `servo_test.launch.py` 및 `robot_ip` path 금지 |
| `semantic_validation/targets/openvr_ur5e_jazzy` | clean Git worktree, upstream `@170dad582d624f536359a3192a7f829669c2b031` | original `src/quest_bridge/quest_bridge/quest_teleop.py`; fake OpenVR is external harness dependency substitution |
| `semantic_validation/targets/quest2ros2` | clean Git worktree, `Taokt/Quest2ROS2@07aaf65149c9e29103f1fc61deb466cef8a55cef` | original `RightArmController` exists; missing CLIK consumer must not be substituted and misattributed |
| `semantic_validation/targets/spes_teleop` | clean Git worktree, `SpesRobotics/teleop@c5d808155a87b584d6147a5943d4b87c34c92db0` | actual trace is reusable for analysis only; no new session in this P0 |
| `docker-teleop-humble:local` | exists (image `ce5200f1d8d5`, 5.46 GB); `docker_teleop_sim` running since 2026-09-14 | container uses `sleep infinity`, bridge network, target source/simulation mounts; P0 did not exec/start/stop it |
| `openvr-jazzy-sim:local` | exists (image `73c0291d9547`, 4.65 GB); `openvr_sim` running since 2026-09-14 | `sleep infinity`, network none, `/harness` and `/ws_src` mounts; P0 did not exec/start/stop it |

Static reproduction entry points (not run in P0): Docker sender `python3 semantic_validation/harness/docker_teleop_tcp_trials.py --host 127.0.0.1 --port 15005`; Docker simulator path in `FRAMEWORK_TESTBED_ADAPTATION_PLAN.md`; OpenVR `semantic_validation/harness/openvr_ur5e_downstream/build_ws.sh` then `run_trial.sh <W0..W3> <valid> <tracking_result> <motion_z> <new-result-root> [run_teleop]`. The OpenVR script creates/cleans trial processes, so it is explicitly a future experiment action, not a P0 check.

## Pi: 확인된 것과 아닌 것

- Read-only SSH to `rosxr` succeeded: hostname `rosxr`, architecture `aarch64`.
- A non-sourced shell has no `ros2` on `PATH`; after sourcing `/home/cclab/ros2_ws/install/setup.bash`, `/opt/ros/humble/bin/ros2` and `semantic_robot_endpoint semantic_robot_sink` are installed.
- No `semantic_robot_sink` or `ros2` process was observed during P0. The default earlier probe path `/home/cclab/pi_ws/...` is absent; it must not be used as current-state evidence.
- The installed endpoint remains an observation sink by design. P0 found no source evidence that a PickNik/Spes/Docker/OpenVR original controller is installed or executable on the Pi. It therefore supports neither controller acceptance nor robot actuation claims.

## Uncertainty and next prerequisites

1. Hash presence proves only that local files exist unchanged at P0; it does not independently validate documents' counts, timestamps, correlations, or conclusions. That is the next trace-audit phase.
2. Current long-lived simulation containers are available but their live ROS graph was intentionally not queried or altered. A future run must use a new result root and preserve command/stdout/stderr/environment manifests.
3. The actual Docker 2026-09-17 evidence requires a raw correlation/exclusion audit before it changes an overall research decision. Its system tracking mode is not proven app tracking validity.
4. PickNik/Spes lack a demonstrated original downstream controller; Quest2ROS2 lacks the original CLIK final consumer. Do not build a substitute and call its outcome original control.
5. Before any future runtime phase, obtain explicit approval after this commit, reread the V2 plan/status board, check `git status`, and verify that the selected launch is Gazebo-only with no driver/CAN/`robot_ip` path.

## P0 actions and non-actions

Performed: Git fetch and conflict-free fast-forward; all specified context-document reads; existence/size/format/SHA-256 checks above; target worktree revision/clean-state checks; read-only Docker image/container inspection; read-only Pi state inspection; candidate credential-pattern scan; new inventory/plan/status documentation.

Not performed: Quest, ADB, Gazebo, ROS, ROSMonitoring, Docker `exec`, source build, bag playback, reanalysis, source mutation, network/Docker/Pi configuration change, robot driver/CAN/physical robot action, or defense implementation.
