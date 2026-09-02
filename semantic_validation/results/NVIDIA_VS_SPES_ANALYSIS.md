# NVIDIA vs Spes Semantic Analysis

## 결론

**NVIDIA는 partial positive control이다.** 고정 `isaac_ros_teleop` release와 현재 `IsaacTeleop` main 모두 controller active와 pose `VALID`를 명시적으로 다루며, 현재 main은 invalid pose 차단과 recovery rebaseline까지 synthetic regression으로 검증된다. 그러나 controller tracker는 OpenXR `POSITION_VALID`/`ORIENTATION_VALID`만 읽고 `POSITION_TRACKED`/`ORIENTATION_TRACKED`는 읽지 않는다. 따라서 NVIDIA가 actively tracked pose와 inferred/extrapolated pose를 보존하거나 후자를 항상 차단한다고 결론 내릴 수 없다.

상태는 다음처럼 분리한다.

- `NVIDIA_LINKED_RELEASE_MACHINE_CHECKED_STATIC_PASS`
- `NVIDIA_CURRENT_MAIN_RUNTIME_SYNTHETIC_PASS` — upstream pure-Python test 10/10
- `NVIDIA_TRACKED_VS_INFERRED_PRESERVATION_NOT_FOUND`
- `NVIDIA_NATIVE_OPENXR_ROS_HARDWARE_NOT_RUN`
- `ISSUE_731_PUBLIC_HARDWARE_SELF_REPORT` — 독립 재현 아님

## 고정 revision과 current-main 경계

| 대상 | 재검증 revision | 결과 |
| --- | --- | --- |
| [`NVIDIA-ISAAC-ROS/isaac_ros_teleop`](https://github.com/NVIDIA-ISAAC-ROS/isaac_ros_teleop/commit/197f5cd9ff2cbd90533a93c67be2a661319048ba) | local/remote `main@197f5cd9ff2cbd90533a93c67be2a661319048ba` | 일치; worktree clean |
| linked `IsaacTeleop` | `.gitmodules` branch `release/1.3.x`, gitlink [`465ce637120ac35404f5f741a9f25f3f1a1a25ea`](https://github.com/NVIDIA/IsaacTeleop/commit/465ce637120ac35404f5f741a9f25f3f1a1a25ea) | production-linked comparison 기준 |
| local `IsaacTeleop` main | `9fba23c4a3bd5b6de732cac77a47f471fca25276` | worktree clean; tests 실행 기준 |
| remote `IsaacTeleop` main | [`334978b0ee73ce3e9102a22bd4c889d8b77dcf82`](https://github.com/NVIDIA/IsaacTeleop/commit/334978b0ee73ce3e9102a22bd4c889d8b77dcf82) | local HEAD의 direct child; 추가 변경은 CI/download 파일뿐 |

Remote main의 tracker, controller/timestamp schema, DeviceIO controller source, SE3 retargeter, ROS message builder, validity test 7개 파일을 official raw source와 SHA-256 비교했고 local 파일과 모두 일치했다. 따라서 semantic 분석과 synthetic test는 remote `334978b0`에도 source-equivalent이다. 단, 실행한 checkout 자체는 `9fba23c4`이며 이 차이를 숨기지 않는다.

Raw provenance: `semantic_validation/logs/nvidia/nvidia_revalidation_20260831T150323Z/source_provenance.jsonl`

## `VALID`와 `TRACKED`는 다르다

Khronos OpenXR 1.1은 runtime이 inferred 또는 last-known position을 제공하는 동안 `POSITION_VALID`을 유지하면서 `POSITION_TRACKED`를 해제할 수 있다고 규정한다. 즉 `VALID=true`는 active optical tracking의 동의어가 아니다. [OpenXR `XrSpaceLocationFlags`](https://registry.khronos.org/OpenXR/specs/1.1/html/xrspec.html#XrSpaceLocationFlags)

NVIDIA controller tracker는 grip과 aim 각각에 대해 position/orientation `VALID` 두 비트의 conjunction을 `ControllerPose.is_valid` 하나로 만든다. `TRACKED` 비트 검사는 없다. [linked release tracker](https://github.com/NVIDIA/IsaacTeleop/blob/465ce637120ac35404f5f741a9f25f3f1a1a25ea/src/core/live_trackers/cpp/live_controller_tracker_impl.cpp#L375-L415), [controller schema](https://github.com/NVIDIA/IsaacTeleop/blob/465ce637120ac35404f5f741a9f25f3f1a1a25ea/src/core/schema/fbs/controller.fbs#L24-L48)

따라서 다음 문장은 증거에 맞지 않는다.

> NVIDIA가 `VALID`를 확인하므로 tracked-vs-inferred semantic을 보존한다.

증거에 맞는 문장은 다음이다.

> NVIDIA는 pose-localizability `VALID`와 controller activity를 보존·사용하지만, 검사한 controller 경로에서는 actively tracked와 inferred pose를 구분하지 않는다.

## Requested semantic matrix

`P`는 preserved, `G`는 gate, `A`는 implicit/assumed convention, `R`은 regenerated/replaced, `D`는 dropped/not represented, `U`는 확인되지 않음을 뜻한다.

| Semantic | Linked release `465ce637` | Current main `334978b0` | 판정과 근거 |
| --- | --- | --- | --- |
| pose valid | `P/G` | `P/G` | tracker가 position+orientation `VALID` conjunction을 `GRIP_IS_VALID`/`AIM_IS_VALID`로 전달한다. release ROS EE builder도 aim-valid를 gate하지만 invalid side를 identity pose로 대체한다. main은 `NamedPoseArray.is_valid`를 내보내고 invalid wrist TF를 생략한다. |
| position tracked | `D` | `D` | `XR_SPACE_LOCATION_POSITION_TRACKED_BIT` 검사·schema field가 없다. |
| orientation tracked | `D` | `D` | `XR_SPACE_LOCATION_ORIENTATION_TRACKED_BIT` 검사·schema field가 없다. |
| controller active | `P/G` | `P/G` | `xrGetActionStatePose().isActive`가 false면 tracked object를 clear한다. raw controller ROS payload에는 좌우 `is_active`가 있다. |
| source identity | `P` internal, `A` ROS | `P` internal, `P/A` ROS | left/right subaction path와 tensor group은 분리된다. release EE `PoseArray`는 좌우 positional convention, main `NamedPoseArray`는 side name을 보존한다. controller-vs-hand modality는 generic EE message에 first-class field로 남지 않는다. |
| sample timestamp | `P` record, `D/R` control/ROS | `P` record, `D/R` control/ROS | MCAP `ControllerSnapshotRecord`에는 pose를 평가한 update/query time의 `DeviceDataTimestamp`가 있으나 controller tensor/ROS EE 경로에는 이어지지 않는다. 별도 physical sensor capture time을 읽는 증거는 아니며, ROS header는 node `now`, raw payload timestamp는 `time.time_ns()`로 새로 생성된다. |
| freshness/age | `D` | `D` | 검사한 controller→retargeter→ROS 경로에 source-age threshold가 없다. |
| reconnect generation | `D` | `D` | controller/session generation을 actionable ROS output에 결합하는 field/check를 찾지 못했다. tensor-list의 내부 schema generation은 transport reconnect generation의 증거로 세지 않았다. |
| recovery/rebaseline | implementation-specific | `G/P` for invalid pose | release generic `Se3Abs/RelRetargeter`는 `GRIP_IS_VALID`를 gate하지 않는다. release의 SO-101-specific clutch는 invalid grip을 hold한다. main generic absolute retargeter는 hold-last, relative retargeter는 zero delta, smoothing clear, 다음 valid frame rebaseline을 수행한다. |

주요 source:

- activity clear, validity, timestamp record: [release tracker](https://github.com/NVIDIA/IsaacTeleop/blob/465ce637120ac35404f5f741a9f25f3f1a1a25ea/src/core/live_trackers/cpp/live_controller_tracker_impl.cpp#L340-L449)
- validity가 DeviceIO tensor로 전달되는 지점: [release `controllers_source.py`](https://github.com/NVIDIA/IsaacTeleop/blob/465ce637120ac35404f5f741a9f25f3f1a1a25ea/src/core/retargeting_engine/python/deviceio_source_nodes/controllers_source.py#L170-L199)
- release ROS validity gate와 identity substitution: [release `messages.py`](https://github.com/NVIDIA/IsaacTeleop/blob/465ce637120ac35404f5f741a9f25f3f1a1a25ea/examples/teleop_ros2/python/messages.py#L114-L158)
- main ROS per-side validity: [main `messages.py`](https://github.com/NVIDIA/IsaacTeleop/blob/334978b0ee73ce3e9102a22bd4c889d8b77dcf82/examples/teleop_ros2/python/messages.py#L43-L85)
- main generic invalid/recovery handling: [main `se3_retargeter.py`](https://github.com/NVIDIA/IsaacTeleop/blob/334978b0ee73ce3e9102a22bd4c889d8b77dcf82/src/python/isaacteleop/retargeters/se3_retargeter.py#L248-L258), [relative recovery](https://github.com/NVIDIA/IsaacTeleop/blob/334978b0ee73ce3e9102a22bd4c889d8b77dcf82/src/python/isaacteleop/retargeters/se3_retargeter.py#L393-L416)
- generic gate가 linked release 뒤 main에 추가된 commit: [`43428130` / PR #743](https://github.com/NVIDIA/IsaacTeleop/commit/434281306357f271b83048fac853cd6c8fb1e097)

## Automated revalidation

실행 command:

```bash
PYTHONPATH=/tmp/ros_xr_nvidia_deps /usr/bin/python3 \
  semantic_validation/harness/nvidia_positive_control.py \
  --output semantic_validation/logs/nvidia/nvidia_revalidation_20260831T150323Z/nvidia_positive_control.jsonl
```

결과:

- linked release machine checks: 8/8 PASS
- current-main upstream pure-Python tests: 10/10 PASS
  - controller SE3 validity/recovery tests 5개
  - hand tracking gate tests 5개
- suite: `PASS`
- native DeviceIO/OpenXR: 실행하지 않음
- ROS transport: 실행하지 않음
- Quest/robot: 실행하지 않음

Raw result: `semantic_validation/logs/nvidia/nvidia_revalidation_20260831T150323Z/nvidia_positive_control.jsonl`

이 결과는 main의 invalid-grip hold/zero/rebaseline behavior에 대한 `RUNTIME_SYNTHETIC` 증거다. 실제 Quest inferred interval에서 NVIDIA의 `GRIP_IS_VALID`가 false가 되는지에 대한 hardware evidence는 아니다.

## NVIDIA Issue #731

공개 [NVIDIA/IsaacTeleop issue #731](https://github.com/NVIDIA/IsaacTeleop/issues/731)은 2026-07-06 생성된 contributor report다. 2026-08-31 재확인 시 open, `Blocked`, comment 0이었다. 작성자는 다음을 보고했다.

- Quest 3 + CloudXR에서 controller occlusion 시 IMU-extrapolated pose가 계속 나오고 `is_tracking`은 true로 남음
- reacquisition 때 pose snap/teleport 발생
- SO-101 follower에서 최대 73 cm/frame robot lurch 측정
- example-layer `PoseGate`가 `GRIP_IS_VALID`를 사용
- synthetic replay에서 73.2 cm/frame이 0.2 cm/frame으로 감소
- validity를 first-class output으로 제공하거나 stock PoseGate를 제공하자는 제안

이는 **실제 hardware/robot을 사용했다는 공개 1차 보고**지만, 이 작업에서 raw telemetry나 robot run을 독립 재실행한 것은 아니다. Issue 본문에는 exact OpenXR `VALID`/`TRACKED` flag trace가 없으며 `is_tracking`이 어느 API field인지도 고정되지 않는다. 따라서 이 issue만으로 NVIDIA가 inferred pose를 검출한다거나, 모든 Quest runtime에서 `GRIP_IS_VALID=false`가 된다고 일반화하지 않는다.

## Issue #731과 Spes finding 비교

| 축 | NVIDIA issue #731 | Spes F-SPES-HW-001/002 |
| --- | --- | --- |
| acquisition | Quest 3 via CloudXR, contributor self-report | Quest 3 WebXR raw instrumentation |
| loss behavior | occlusion 중 extrapolated pose, `is_tracking=true` 보고 | controller pose non-null + `emulatedPosition=true`, valid trial 5/5 |
| semantic evidence | `GRIP_IS_VALID` mitigation을 보고하지만 exact OpenXR flag trace 없음 | WebXR `emulatedPosition`과 production packet을 같은 frame에서 기록; packet에는 field 없음 |
| boundary consequence | SO-101 follower robot lurch 최대 73 cm/frame 보고 | production control packet과 actual Spes server update/target callback 계속; robot 미연결 |
| recovery | reacquisition snap/teleport | user re-arm 없이 1/5 continuous, 4/5 reject→automatic re-anchor→callback resume |
| mitigation | PoseGate/hold or disengage 제안; synthetic replay 수치 | defense를 구현하지 않은 observational validation |
| evidence level | `PUBLIC_ISSUE_SELF_REPORT`; 독립 raw 재검증 없음 | `ACTUAL_XR_HARDWARE` through server callback; actual robot 아님 |

공통 핵심은 “pose object가 계속 존재한다”와 “actionable control로 사용해도 된다”가 동일하지 않다는 것이다. 둘 다 occlusion과 recovery discontinuity가 downstream action으로 이어질 수 있음을 보여준다. 다만 mechanism과 evidence endpoint는 다르다. NVIDIA report는 CloudXR/DeviceIO/retargeter/physical robot 경로이고, Spes는 WebXR `emulatedPosition`이 XR→JSON control boundary에서 소실된 뒤 server callback까지 계속되는 경로다.

## Novelty와 motivating evidence 판정

### Issue #731이 침해하는 claim

다음 주장은 novelty claim으로 사용하면 안 된다.

- Quest controller occlusion이 extrapolated pose와 recovery snap을 만들 수 있다는 최초 관찰
- 그 현상이 robot lurch를 만들 수 있다는 최초 관찰
- validity gate, hold-last, clutch disengage가 필요하다는 최초 제안
- 단순 rate limiter만으로 semantic invalidity를 해결하기 어렵다는 최초 주장

Issue #731은 Spes hardware run보다 먼저 공개됐고 위 broad problem/mitigation을 상당 부분 선취한다. 따라서 연구 framing이 “Quest tracking loss 때문에 robot이 움직일 수 있다” 한 문장에 머물면 novelty threat가 크다.

### Issue #731이 직접 보여주지 않는 것

- WebXR의 actual `emulatedPosition=true` interval과 해당 field의 production payload omission
- 동일 interval의 control-packet↔actual server callback progression correlation
- explicit user re-arm 없이 continuous 또는 automatic re-anchor로 actionable 상태가 복구된다는 5-trial evidence
- `VALID`와 `TRACKED`를 분리한 end-to-end semantic matrix
- source identity, source-time/freshness, reconnect generation, causal re-arm을 함께 묶는 boundary invariant

따라서 현재 Spes contribution의 방어 가능한 중심은 “occlusion hazard의 최초 발견”이 아니라 **XR semantic이 여러 control boundary에서 어떻게 축약되고, 그 축약이 actionability 및 recovery와 어떻게 결합되는지를 재현 가능한 evidence로 검증하는 것**이다. 다만 이 문서는 issue 한 건과 source code 비교이며, paper-level novelty를 확정하려면 별도 문헌 조사가 필요하다.

### Motivating evidence로서의 가치

Issue #731은 같은 Quest 3 occlusion/recovery 계열 문제가 다른 stack과 실제 robot endpoint에서도 보고됐다는 외부 motivation이다. 그러나 raw artifact가 없고 이 작업에서 재현하지 않았으므로 Spes finding의 “두 번째 독립 hardware confirmation”으로 세지 않는다. NVIDIA main의 validity/rebaseline regression은 안전한 대조군을 제공하지만 `TRACKED` omission 때문에 complete positive control도 아니다.

## 최종 boundary

현재 증거로 허용되는 결론:

> NVIDIA linked release와 current main은 controller activity와 OpenXR pose `VALID`를 명시적으로 gate한다. Current main은 invalid grip에서 hold/zero 및 relative rebaseline을 synthetic tests로 확인했다. 그러나 두 revision 모두 controller `TRACKED` bits와 ROS source-time/freshness, reconnect generation을 inspected actionable path에 보존하지 않는다. Issue #731은 Quest occlusion과 robot lurch의 public motivating report지만, 여기서 독립 재현한 hardware evidence는 아니다.

허용되지 않는 결론:

- NVIDIA가 모든 inferred/extrapolated pose를 fail-close한다.
- NVIDIA issue #731의 73 cm/frame 결과를 이 실험이 재현했다.
- NVIDIA와 Spes가 동일 runtime flag 또는 동일 failure mechanism을 사용한다.
- 공개 issue 하나만으로 cross-stack generality 또는 paper novelty가 확정됐다.
