# PickNik Quest hardware-validation readiness

> **Correction notice (2026-09-14, `PICKNIK_QUESTLESS_CONVERGENCE.md`):** the
> environment statements below are out of date. A Unity `6000.1.6f1` editor **is**
> installed at `/home/cclab/Unity/Hub/Editor/6000.1.6f1/Editor/Unity`, with the
> Android and Linux Standalone modules. It was actually invoked in batch mode and
> failed with `No valid Unity Editor license found. Please activate your license.`
> (exit 1). The blocker is a **license entitlement**, not a missing editor. The
> `ros_env/ros2_ws` `ros_tcp_endpoint` install referenced below is also broken (a
> stale `--symlink-install` egg-link); a working rebuild and an actual endpoint run
> are recorded in the new report. Source findings below are unchanged and were
> re-verified (33/33, 10/10) on 2026-09-14.


## Status

**Instrumentation/harness: `MACHINE_CHECKED_STATIC READY`**  
**Unity/APK build: `BLOCKED_USER_ACTION` (licence entitlement)**
**Quest execution: `BLOCKED_HW`**

Unity `6000.1.6f1`과 Android module은 설치되어 있지만 batch mode는 licence entitlement가
없어 project import 전에 종료된다. ADB-connected Quest도 없으므로 APK/hardware trial은
실행하지 않았다. Docker Humble의 official ROS-TCP Endpoint는 실제 build/listen 및
backend-only 3600/3600 relay까지 확인됐지만, injection은 PickNik code 뒤이므로
`BOUNDARY_LIMITED_REPLAY`다.

## Hardware question

### H-PICKNIK-1

> Real Quest tracking loss에서 source `isTracked`/`trackingState`가 invalid로 바뀌어도 controller Transform과 ROS Odometry/TF publication이 계속되는가?

주의: Unity `InputTrackingState`와 WebXR `emulatedPosition`은 같은 field가 아니다. `trackingState` bit 또는 `isTracked` 변화가 실제 Quest에서 무엇을 뜻하는지는 raw observation과 함께만 해석한다.

## Prepared components

| Component | Purpose | Current verification |
| --- | --- | --- |
| [`PickNikTrackingSidebandLogger.cs`](../instrumentation/picknik/PickNikTrackingSidebandLogger.cs) | `isTracked`, `trackingState`, controller Transform, Unity frame/monotonic time, input presence, GameObject active state, focus/pause, XR display state를 JSONL로 기록 | structure/non-interference machine check PASS; Unity compile 미수행 |
| [`PickNikSemanticValidationBuild.cs`](../instrumentation/picknik/Editor/PickNikSemanticValidationBuild.cs) | disposable project의 Android development APK batch-build entry point | source prepared; Unity build `SKIP_ENV` |
| [`prepare_picknik_hw_project.py`](../harness/prepare_picknik_hw_project.py) | pinned clean target을 disposable copy로 복제하고 side-band asset만 추가 | executed PASS |
| [`picknik_ros_observer.py`](../harness/picknik_ros_observer.py) | robot-free ROS 2에서 actual Odometry/TF receive event, header stamp, pose를 JSONL 기록 | syntax/help PASS; current shell `rclpy` 없음 |
| [`picknik_hw_analyze.py`](../harness/picknik_hw_analyze.py) | future side-band/ROS logs에서 valid->invalid->reacquired interval 및 downstream continuation 분류 | synthetic self-test PASS; hardware data 미입력 |

Prepared disposable project:

`/tmp/picknik_hw_ready_20260831T151950Z/UnityProject`

이 `/tmp` copy는 재생성 가능하며 canonical source가 아니다.

## Production-payload non-interference

- Upstream `ROSPublishers.cs`는 수정하지 않았다.
- Staged `ROSPublishers.cs`는 upstream과 byte-identical하다.
- 양쪽 SHA-256: `9fd803f080f5fd2c8ae1f01f1ffd1711f669f05da6a0d8a274cf5f95f454873a`.
- Side-band logger는 ROS client/message namespace를 import하지 않고 `Publish()`를 호출하지 않는다.
- Side-band fields는 Odometry/TF payload에 추가되지 않는다.
- Target checkout은 staging 전/후 clean이며 commit은 `bbaef0762fdb0b429b8ea12a4ca65040748b41dd`다.

Evidence: [`hw_staging_manifest.json`](../logs/picknik/picknik_deep_20260831T151950Z/hw_staging_manifest.json).

## What each log proves

### Quest side-band JSONL

Location on device:

`Application.persistentDataPath/picknik_semantic_validation_<UTC>.jsonl`

Each 60 Hz side record contains:

- Quest wall time and Unity monotonic/frame time
- left/right source input presence and device ID/name
- `is_tracked`
- `tracking_state` integer bitmask
- controller GameObject presence and active state
- world position/orientation read from the same GameObject referenced by `RosPublishers`
- application focus/pause and XR display running state
- transition events for tracking, input-device, focus, and pause changes

This is side-band observation only; it does not prove ROS delivery.

### Robot-free ROS observer JSONL

The host observer subscribes to:

- `/left_controller_odom`
- `/right_controller_odom`
- `/tf`

It records actual receive time, ROS header stamp, frame/child identity, pose, and per-topic index. This proves endpoint delivery to a dummy observer, not MoveIt Pro consumption or robot motion.

Because both `ROSPublishers.GetRosTime()` and the side-band wall timestamp use Quest `DateTime.UtcNow`, the analyzer correlates source loss intervals to received ROS header stamps without relying only on host/Quest wall-clock synchronization.

## Automatic classifications prepared

The analyzer first requires a valid tracked sample, then identifies a valid -> invalid -> reacquired interval. Invalid means `is_tracked=false` or missing Position/Rotation tracking bits.

| Classification | Required observation |
| --- | --- |
| `HW_PICKNIK_UNTRACKED_ROS_CONTINUES` | actual loss interval plus at least two progressing Odometry and two TF observations during it |
| `HW_PICKNIK_NO_DOWNSTREAM_DURING_LOSS` | loss interval and no matching Odometry/TF during it |
| `HW_PICKNIK_PARTIAL_DOWNSTREAM_OBSERVATION` | only one stream or insufficient progression |
| `INVALID_FOCUS_OR_XR_SESSION` | focus/pause/XR-display interruption overlaps loss |
| `HW_NO_LOSS_OBSERVED` | no valid->invalid transition; not a hypothesis failure |

`distinct_ros_transforms=1` with progressing ROS stamps would indicate a repeated/frozen Transform; multiple values would indicate continued/changed Transform values. Neither is pre-claimed.

## Build and run sequence when the existing Unity environment is available

No new Unity installation is required by the harness. Point it at an already installed compatible editor.

```bash
cd /home/cclab/ros_xr

python3 semantic_validation/harness/prepare_picknik_hw_project.py \
  --output /tmp/picknik_hw_run \
  --manifest semantic_validation/logs/picknik/<run-id>/hw_staging_manifest.json \
  --build-if-available \
  --apk /tmp/picknik_hw_run/Builds/picknik_semantic_validation.apk
```

Equivalent direct Unity command after staging:

```bash
PICKNIK_VALIDATION_APK=/tmp/picknik_hw_run/Builds/picknik_semantic_validation.apk \
/path/to/Unity -batchmode -quit \
  -projectPath /tmp/picknik_hw_run/UnityProject \
  -executeMethod PickNikSemanticValidationBuild.BuildAndroid \
  -logFile semantic_validation/logs/picknik/<run-id>/unity_batch_build.log
```

Robot-free host observation in a ROS 2 shell containing `rclpy`, `nav_msgs`, and `tf2_msgs`:

```bash
python3 semantic_validation/harness/picknik_ros_observer.py \
  --output semantic_validation/logs/picknik/<run-id>/ros_observer.jsonl
```

After the run:

```bash
python3 semantic_validation/harness/picknik_hw_analyze.py \
  --sideband semantic_validation/logs/picknik/<run-id>/quest_sideband.jsonl \
  --ros semantic_validation/logs/picknik/<run-id>/ros_observer.jsonl \
  --output semantic_validation/logs/picknik/<run-id>/analysis.json
```

APK installation, app launch, and side-band extraction must use the actual authorized Quest/ADB environment. The configured Android application identifier is `com.unity.template.vr`; a Development build may permit `run-as`, but that must be verified rather than assumed.

## Minimal physical procedure

No robot or robot driver should be connected.

1. Start only `ros_tcp_endpoint` and the dummy ROS observer.
2. Launch the instrumented disposable APK and confirm baseline `is_tracked=true`, Position+Rotation tracking bits, Transform motion, Odometry, and TF reception.
3. Keep the controller powered and occlude it from Quest tracking for 3–5 seconds without causing headset focus loss.
4. Continue recording for at least 1–2 seconds after the first tracking-state transition.
5. Restore visibility and record reacquisition for at least 2 seconds; repeat until five valid transitions or report `HW_NO_LOSS_OBSERVED`.

The experiment does not require or authorize physical robot actuation.

## Current blocker

- Compatible Unity executable and Android module: installed at
  `/home/cclab/Unity/Hub/Editor/6000.1.6f1/`; batch mode exits `1` with
  `Found 0 entitlement groups` / `No valid Unity Editor license found`.
- Existing repository tests/build artifact: none.
- Current host shell ROS 2 Python environment: unavailable; the isolated Docker Humble image has
  `rclpy`, `nav_msgs`, `tf2_msgs`, and `geometry_msgs`.
- ADB binary: available, connected Quest: none.

Therefore the remaining manual work is: activate a legitimate Unity entitlement, build/install the
prepared disposable app, authorize the Quest over ADB, and perform controller occlusion. Until
then PickNik remains `SOURCE_DATAFLOW_CONFIRMED`; its ROS-TCP result is backend-only replay, not
PickNik publisher runtime.
