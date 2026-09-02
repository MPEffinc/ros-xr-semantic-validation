# PickNik deep source + executable validation

## Result

**PASS — strongest evidence: `SOURCE_DATAFLOW_CONFIRMED`; Unity/Quest/ROS runtime: `BLOCKED_ENV` / `BLOCKED_HW`**

Pinned target:

- Repository: `https://github.com/PickNikRobotics/meta_quest_teleoperation.git`
- Branch/commit: `main@bbaef0762fdb0b429b8ea12a4ca65040748b41dd`
- `ROSPublishers.cs` SHA-256: `9fd803f080f5fd2c8ae1f01f1ffd1711f669f05da6a0d8a274cf5f95f454873a`
- Target status: validation 전/후 clean
- Canonical run: `picknik_deep_20260831T151950Z`, 33/33 checks PASS

이 결과는 Unity scene/prefab/input-action serialization과 C# source를 기계적으로 연결한 것이다. Unity Editor, APK, Quest app, ROS endpoint, robot은 실행하지 않았으므로 runtime finding이 아니다.

## Important correction to the earlier wording

다음 넓은 해석은 **기각**한다.

> PickNik repository에는 tracking-state API/configuration이 없다.

Repository-wide search 결과 `isTracked`와 `trackingState`가 존재하며, build scene의 controller Transform driver까지 실제 serialized reference로 연결된다. 정확한 finding은 다음과 같다.

> Tracking state는 OpenXR/Input System에서 controller GameObject Transform을 갱신하는 단계에는 연결되어 있지만, `RosPublishers.Update()` 이후 Odometry/TF schema에는 전달되지 않는다.

따라서 기존 checker의 `tracking_state_not_queried_in_source`는 **`ROSPublishers.cs` source file 내부**에만 한정하면 맞고, repository 전체에 대한 문장으로 사용하면 안 된다.

## Exact connected data flow

```text
Android OpenXR loader + Quest 3/Oculus Touch profile
  -> XRI Left/Right input actions
       devicePosition
       deviceRotation
       trackingState
       isTracked (asset에는 존재)
  -> left/right controller tracked-pose component
       Position input connected
       Rotation input connected
       Tracking State input connected
       m_IgnoreTrackingState = 0
  -> Left Controller / Right Controller GameObject Transform
  -> enabled SampleScene serialized references
  -> RosPublishers.Update() at 1/60 s
  -> GetPositionAndRotation()
  -> REP-103 FLU conversion
  -> nav_msgs/Odometry + tf2_msgs/TFMessage
```

### 1. OpenXR and Quest source configuration

- Android provider selects the OpenXR loader: `UnityProject/Assets/XR/XRGeneralSettings.asset:27-33`.
- Meta Quest Android feature is enabled and Quest 3 is selected: `OpenXRPackageSettings.asset:1043-1065`.
- Oculus Touch controller profile is enabled for Android: `OpenXRPackageSettings.asset:1378-1384`.
- Locked packages include Input System `1.14.0`, XRI `3.1.1`, OpenXR `1.14.3`, XR Management `4.5.1`, and ROS-TCP-Connector hash `c27f00c6cf750d2d0564349b3039d19aa3925e7c`.

### 2. Pose and tracking actions

The referenced `XRI Default Input Actions.inputactions` contains:

| Side | Position | Rotation | Tracking state | Is tracked |
| --- | --- | --- | --- | --- |
| Left | `:527` | `:483` | `:560` | `:802` |
| Right | `:1576` | `:1532` | `:1609` | `:1851` |

각 binding은 `<XRController>{LeftHand|RightHand}/...`를 사용한다.

### 3. Actions to the exact published GameObjects

- XRI rig의 `Left Controller`와 `Right Controller`는 active이고 tracked-pose component를 가진다: `XR Origin (XR Rig).prefab:3-22,117-167,186-205,300-350`.
- 두 component 모두 Position/Rotation/Tracking State action을 reference하며 `m_IgnoreTrackingState: 0`이다.
- nested complete-rig prefab은 이 GameObject들을 각각 source object `202364687`와 `1670256624`로 연결한다: `Complete XR Origin Set Up Hands Variant.prefab:8864-8873,9051-9060`.
- enabled build scene은 이 nested objects를 `581284854`와 `821107281`로 materialize한다: `SampleScene.unity:172-176,372-376`.
- 같은 scene의 단일 `RosPublishers` component가 그 두 file ID를 `leftController`와 `rightController`로 직접 참조한다: `SampleScene.unity:1104-1145`.
- 유일한 enabled build scene은 `Assets/Scenes/SampleScene.unity`이다: `EditorBuildSettings.asset:7-10`.

이는 repository의 다른 sample/demo에 token이 존재한다는 이유만으로 연결을 주장한 것이 아니라, build scene에서 publisher field까지 file ID/GUID chain을 따라간 결과다.

### 4. Transform to ROS boundary

- `Update()`는 등록 gate가 열린 동안 1/60초마다 두 controller의 `.transform`을 동일한 publish method로 전달한다: `ROSPublishers.cs:286-293,318-340`.
- `PublishOdomAndTf()`는 `GetPositionAndRotation()`을 읽고 Odometry와 TF를 publish한다: `:381-416`.
- 이 method의 argument, body, output message에는 `isTracked`, `trackingState`, `InputTrackingState`, controller active/enabled, sample timestamp, age/freshness가 없다.
- ROS header stamp는 source sample time이 아니라 `DateTime.UtcNow`로 새로 생성한다: `:367-379,394`.
- `OnApplicationFocus`와 `OnApplicationPause` invalidation은 repository의 publisher path에서 발견되지 않았다.

## Semantic result by field

| Semantic | Exact result | Evidence |
| --- | --- | --- |
| controller position/rotation | XRI action -> tracked-pose component -> GameObject Transform -> FLU Odometry/TF로 연결 | `SOURCE_DATAFLOW_CONFIRMED` |
| `trackingState` | Transform driver에는 연결되지만 `RosPublishers` input/output에는 없음 | `SOURCE_DATAFLOW_CONFIRMED` |
| `isTracked` | input-action asset에는 존재; publisher 또는 ROS schema로의 연결은 없음 | `SOURCE_DATAFLOW_CONFIRMED` |
| actively tracked vs inferred/emulated | inspected ROS boundary에서 표현되지 않음; Unity/OpenXR이 이를 `trackingState`에 어떻게 매핑하는지는 실행 전 미확인 | `MACHINE_CHECKED_STATIC` |
| controller active/enabled | scene objects는 active이나 publisher가 runtime active state를 gate/encode하지 않음 | `SOURCE_DATAFLOW_CONFIRMED` |
| source kind | 같은 left/right action에는 `XRController`와 `XRHandDevice` pose binding이 함께 존재하며 ROS output은 side만 표현; 어느 binding이 실제로 drive했는지는 보존되지 않음 | `SOURCE_DATAFLOW_CONFIRMED` schema/dataflow, runtime switching 미확인 |
| source timestamp/freshness | source timestamp input 없음; publication wall time 재생성 | `SOURCE_DATAFLOW_CONFIRMED` |
| focus/session state | publisher invalidation/serialization 없음 | `MACHINE_CHECKED_STATIC` |
| left/right identity | separate topics와 child frame으로 보존 | `SOURCE_DATAFLOW_CONFIRMED` |

## Machine-executable source model

`picknik_deep_validation.py`는 `PublishOdomAndTf()`가 실제로 assign하는 fields만으로 작은 model을 실행했다. 동일 numeric Transform과 동일 publication time에 대해 `tracking_state=3`과 `tracking_state=0` 입력은 같은 modeled Odometry/TF를 생성했다.

이것은 **schema/dataflow collision의 `MACHINE_CHECKED_STATIC` evidence**일 뿐 Unity serialization 또는 runtime replay가 아니다.

## Runtime feasibility result

| Item | Observation |
| --- | --- |
| Unity project version | `6000.1.6f1 (d64b1a599cad)` |
| `Unity`, `unity-editor`, `unityhub` | 없음 |
| common Unity Hub editor paths | 없음 |
| repository test C# / test assemblies | 0 / 0 |
| Unity Test Framework | lockfile의 transitive `1.5.1`; repository test assembly는 없음 |
| GitHub workflow / CI | 없음 |
| APK/AAB/executable build artifact | 없음 |
| `adb` | `/usr/bin/adb` 존재, connected device 0 |
| `ros2` / `rclpy` in current shell | 없음 / 없음 |

그러므로 Unity batch mode, EditMode, PlayMode, scene execution, APK build, Quest run, ROS transmission은 실행하지 않았다. 새 Unity 설치도 수행하지 않았다. Runtime status는 `BLOCKED_ENV`, hardware status는 `BLOCKED_HW`다.

## Tests and commands

```bash
python3 semantic_validation/harness/picknik_deep_validation.py \
  --output semantic_validation/logs/picknik/picknik_deep_20260831T151950Z/deep_validation.jsonl \
  --summary semantic_validation/logs/picknik/picknik_deep_20260831T151950Z/summary.json \
  --probe-adb

python3 semantic_validation/harness/picknik_machine_check.py \
  --output semantic_validation/logs/picknik/picknik_deep_20260831T151950Z/legacy_machine_check.jsonl

python3 semantic_validation/harness/picknik_deep_validation_selftest.py
```

Results:

- Deep checks: 33/33 PASS.
- Existing PickNik checks: 10/10 PASS.
- New parser/model/hardware-classifier self-tests: 4/4 PASS.
- Disposable instrumented staging: PASS; upstream and staged `ROSPublishers.cs` byte-identical.
- Unity build: `SKIP_ENV`.

## Evidence

- Checker: [`picknik_deep_validation.py`](../harness/picknik_deep_validation.py)
- Canonical summary: [`summary.json`](../logs/picknik/picknik_deep_20260831T151950Z/summary.json)
- Raw checks/search: [`deep_validation.jsonl`](../logs/picknik/picknik_deep_20260831T151950Z/deep_validation.jsonl)
- Legacy regression: [`legacy_machine_check.jsonl`](../logs/picknik/picknik_deep_20260831T151950Z/legacy_machine_check.jsonl)
- Staging/non-interference: [`hw_staging_manifest.json`](../logs/picknik/picknik_deep_20260831T151950Z/hw_staging_manifest.json)

## Bounded conclusion

`F-PICKNIK-001`은 다음 범위에서 강화된다.

> **`SOURCE_DATAFLOW_CONFIRMED`:** enabled Quest/OpenXR scene에서 controller pose와 tracking-state input은 같은 controller GameObject의 tracked-pose component에 연결된다. `RosPublishers`는 그 resulting Transform을 주기적으로 읽지만 tracking state/source time을 Odometry/TF에 싣지 않고 current wall-clock stamp를 생성한다.

아직 확인되지 않은 것:

- real Quest tracking loss에서 `isTracked`/`trackingState`가 실제로 어떻게 변하는지
- controller/hand binding 중 어느 source가 실제 Transform을 drive하는지와 mode switching behavior
- 그때 Transform이 freeze, partial update, inferred update, reset 중 무엇을 하는지
- Odometry/TF가 실제 ROS endpoint에서 계속 수신되는지
- downstream MoveIt Pro clutch/objective가 이를 actionable하게 사용하는지

따라서 PickNik에 대해 actual runtime/hardware 또는 robot consequence를 주장하지 않는다.
