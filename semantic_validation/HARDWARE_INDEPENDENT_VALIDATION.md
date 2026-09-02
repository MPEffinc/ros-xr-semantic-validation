# Hardware-independent semantic validation matrix

기준 revision과 정적 감사는 [`audit/SEMANTIC_AUDIT.md`](audit/SEMANTIC_AUDIT.md), canonical no-Quest 실행은 `logs/no_quest/no_quest_20260830T142000Z/`이다. 이 문서의 `R-SYN`은 실제 target code/path를 합성 입력으로 실행했다는 뜻이며 Quest/OpenXR hardware 실행을 뜻하지 않는다.

## 판정 어휘

| 표기 | canonical status | 의미 |
| --- | --- | --- |
| `S` | `CONFIRMED_STATIC` | 고정 source를 확인했다. 실행 증거는 아니다. |
| `SM` | `CONFIRMED_STATIC` + machine-checked | source assertion을 자동 실행했다. Unity/OpenXR runtime 증거는 아니다. |
| `R` | `CONFIRMED_RUNTIME` | 해당 software/transport 경계를 실제 실행했다. |
| `R-SYN` | `CONFIRMED_RUNTIME_SYNTHETIC_SOURCE` | 실제 target path를 실행했지만 semantic ground truth는 합성했다. |
| `HW` | `BLOCKED_HW` | Quest/runtime에서 해당 상태가 실제 발생하는지는 확인하지 못했다. |
| `ENV` | `BLOCKED_ENV` | 로컬 권한 또는 실행기 부재로 경계를 실행하지 못했다. |
| `U` | `UNKNOWN` | source/runtime 증거가 충분하지 않다. |

`PASS`는 harness assertion의 성공이지 target이 안전하다는 뜻이 아니다. 각 cell은 `보존 판정; 증거; 남은 경계` 순서다.

## 4-stack matrix

| Target | Tracking validity preservation | Tracked vs inferred/emulated preservation | Source identity preservation | Source timestamp lineage | Message freshness guard | Reconnect/session isolation | Control/clutch invalidation | Reference identity | Downstream re-stamp | Actionable consequence |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| **SpesRobotics/teleop** | **DROPPED; R-SYN.** Valid/emulated/controller/viewer가 pose packet에서 구별되지 않음. 실제 loss activation은 HW. | **DROPPED; R-SYN.** `emulatedPosition` true/false가 같은 packet. 실제 Quest emulation은 HW. | **DROPPED; R-SYN.** controller와 viewer가 같은 representation. | **DROPPED; R-SYN.** source stamp/sequence가 packet에 없고 >1 s queue age가 server에 전달되지 않음. | **ABSENT; R-SYN.** delayed sample/trajectory를 실제 WSS+`Teleop.__update`가 처리. | **NOT ISOLATED; R-SYN.** disconnect가 anchors를 reset하지 않으며 새 connection의 near pose가 즉시 callback. | **EXPLICIT ONLY; R-SYN.** `move=false`는 anchors를 clear하지만 callback을 내며 tracking loss/source switch는 자동 invalidation이 아님. | **DROPPED; R-SYN.** reference-space/source generation field 없음. | **YES; S.** ROS wrapper는 publish 시 ROS clock과 fixed frame을 생성. ROS runtime은 ENV. | **Server target callback까지 R-SYN.** semantic collision과 old-generation replay 후 target 변화 확인. ROS/robot actuation은 ENV/HW이며 주장하지 않음. |
| **PickNik meta_quest_teleoperation** | **DROPPED AT PUBLISHER; SM.** `Transform`을 tracking check 없이 읽음. 실제 lost tracking Transform은 HW. | **DROPPED; SM.** tracked/emulated argument와 query가 없음. | **PARTIAL; SM.** left/right child frame은 분리되지만 session/source generation은 없음. | **REGENERATED; SM.** `DateTime.UtcNow`로 publication time을 생성. | **ABSENT; SM.** pose age 입력/threshold 없음. | **TRANSPORT GATE ONLY; S.** reconnect registration delay는 있으나 semantic generation isolation은 없음. | **ABSENT FOR POSE; SM.** focus-loss/tracking invalidation hook 없음. | **FIXED/COARSE; SM.** header `quest`와 child frame만 있고 runtime reference-space identity는 없음. | **YES; SM.** odom/TF가 publication time 공유. | **Source-level only.** pose/TF publish call은 확인했지만 Unity scene/Quest/ROS endpoint 실행은 ENV/HW. |
| **Quest2ROS2** | **NOT REPRESENTED ON CALLBACK INPUT; R-SYN.** callback은 pose 배열만 소비. XR producer semantics는 U/HW. | **NOT REPRESENTED; S.** producer가 제공하는지는 U. | **DROPPED; R-SYN.** 서로 다른 input frame ID가 모두 `robot_base` 출력. | **DROPPED; R-SYN.** 10 ms–10 s 과거 및 1 s 미래 stamp 모두 output now로 교체. | **ABSENT; R-SYN.** 모든 age sample과 3 s stale trajectory가 publish. | **U.** inspected callback에는 generation/session key가 없지만 XR/wire reconnect source가 repository에 없음. | **LOCAL GATE; S.** `allow_pose_update`가 있으나 freshness/source invalidation과 결합되지 않음. | **DROPPED; R-SYN.** arbitrary upstream frame provenance가 보존되지 않음. | **YES; R-SYN.** actual `_pose_callback` output가 callback-time stamp 사용. | **Stub publisher까지 R-SYN.** actual ROS graph/DDS는 Docker permission 때문에 ENV; robot/Quest는 미실행. |
| **NVIDIA Isaac ROS Teleop / IsaacTeleop** | **PARTIAL POSITIVE CONTROL.** linked release active/VALID gate는 S; current main grip/hand invalid handling 10 tests는 R-SYN. | **DROPPED; S.** controller locate가 VALID bits는 보지만 TRACKED bits는 보존하지 않음. 실제 inferred state는 HW. | **LEFT/RIGHT PRESERVED; S.** separate paths/objects. Session generation은 U. | **INTERNAL YES, ROS NO; S.** internal sample clocks가 있으나 inspected ROS outputs use now/time.time_ns. | **NOT FOUND; S.** inspected controller→ROS path에 age threshold 없음. | **U/PARTIAL.** inactive/failure clears data; reconnect generation binding은 확인되지 않음. | **VALIDITY INVALIDATION; R-SYN current main.** invalid absolute holds; relative emits zero, clears smoothing, recovery rebaselines. | **NOT END-TO-END; S.** configured ROS frame만 남고 OpenXR reference identity는 보존되지 않음. | **YES; S.** ROS publication timestamp regenerated. | **Positive control R-SYN on current main.** invalid fixture does not create jump; native DeviceIO/OpenXR and linked-release runtime remain HW/ENV. |

## 직접 검증된 경계와 남은 경계

- 직접 검증: Spes actual inline frontend, HTTPS/WSS route, actual server update; Quest2ROS2 actual callback body; NVIDIA current-main pure-Python retargeters/tests; PickNik source assertions.
- 실행하지 않음: Quest 3 WebXR/OpenXR, Unity scene, ROS 2 graph/DDS for the new tests, physical robot/driver.
- 따라서 허용되는 강한 문장은 “서로 다른 합성 semantic state가 같은 downstream representation으로 collapse한다”와 “downstream logic이 source age/identity를 받을 수 없어 이를 구별하지 못한다”까지다.
- 금지되는 문장은 “Quest 3 tracking loss가 unsafe robot motion을 발생시킨다”이다.

## 재현

```bash
cd /home/cclab/ros_xr
./run_no_quest_validation.sh
```

필요 임시 dependency와 환경 경계는 [`README.md`](README.md) 및 [`results/RESEARCH_STATUS_NO_QUEST.md`](results/RESEARCH_STATUS_NO_QUEST.md)에 기록한다.
