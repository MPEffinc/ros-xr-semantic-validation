# PickNik no-hardware validation

> Superseded interpretation notice: repository-wide connected-dataflow analysis is now in [`PICKNIK_DEEP_VALIDATION.md`](PICKNIK_DEEP_VALIDATION.md). `trackingState/isTracked` do exist upstream; `trackingState` reaches the exact controller Transform driver and is then dropped at the `Transform -> Odometry/TF` publisher boundary. The older statements below about absence apply only to `ROSPublishers.cs`, not the full repository.

## Result

**PASS — canonical `CONFIRMED_STATIC`, evidence tag `CONFIRMED_STATIC_MACHINE_CHECKED`; runtime `BLOCKED_ENV`**

Target는 `bbaef0762fdb0b429b8ea12a4ca65040748b41dd`, checked file SHA-256은 `9fd803f080f5fd2c8ae1f01f1ffd1711f669f05da6a0d8a274cf5f95f454873a`이다.

## Environment check

- Project editor: Unity `6000.1.6f1 (d64b1a599cad)`.
- `Unity`, `unity-editor`, `unityhub`: 없음.
- repository C# test source: 찾지 못함.
- 따라서 거대한 Unity 설치를 새로 수행하지 않았고 EditMode/PlayMode/scene/Transform runtime은 `BLOCKED_ENV`다.

## Machine-checked assertions

10개 source assertion이 모두 PASS했다.

- `Update()`는 left/right 모두 같은 `PublishOdomAndTf(Transform, childFrame, odomTopic)`를 호출한다(`ROSPublishers.cs:318-340`).
- publish method는 `sourceTransform.GetPositionAndRotation`을 조건 없이 읽는다(`:381-387`).
- source 전체와 method signature에 `isTracked`, `trackingState`, `TryGetFeatureValue`, `InputTrackingState`, `CommonUsages.isTracked`가 없다.
- `OnApplicationFocus` invalidation hook이 없다.
- header stamp는 source sample time이 아니라 `DateTime.UtcNow` 기반 `GetRosTime()`이다(`:367-394`).
- odom과 TF를 publish한다(`:404-416`).
- left/right child frame은 보존되지만 header의 coarse parent는 `quest`로 고정되고 reference-space/session generation은 표현하지 않는다.

## Counterfactual boundary

Tracked Transform A와 stale/emulated Transform B가 같은 숫자 pose를 가진다는 counterfactual을 source contract에 대입하면 publisher schema는 둘을 구별할 tracking field가 없다. 그러나 Unity를 실행하지 않았으므로 이것은 runtime collision이 아니다.

## Claim

> PickNik Unity publisher source는 tracking validity/inferred state를 publish path의 입력이나 출력 schema로 보존하지 않고 publication-time stamp를 생성한다.

실제 Quest tracking loss 때 Unity Transform이 freeze, infer, reset 중 무엇을 하는지와 ROS endpoint의 실제 결과는 `BLOCKED_HW`/`BLOCKED_ENV`다.

## Evidence

- Checker: [`harness/picknik_machine_check.py`](../harness/picknik_machine_check.py)
- Raw: [`picknik_machine_check.jsonl`](../logs/no_quest/no_quest_20260830T142000Z/picknik_machine_check.jsonl)
- Reproduce: `python3 semantic_validation/harness/picknik_machine_check.py --output <new-jsonl>`

Finding: `F-PICKNIK-001`.
