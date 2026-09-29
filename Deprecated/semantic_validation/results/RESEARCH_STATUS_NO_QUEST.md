# Research status without Quest

> Historical boundary: this file is the pre-hardware snapshot. Actual Quest result and current cross-stack decision are in [`SPES_QUEST_HW_RESULT.md`](SPES_QUEST_HW_RESULT.md), [`INVARIANT_MATRIX.md`](INVARIANT_MATRIX.md), and [`RESEARCH_DECISION.md`](RESEARCH_DECISION.md).

## 1. Starting hypothesis

XR tracking loss, inferred/emulated pose, source switch, focus/reconnect, stale sample 같은 safety-relevant state가 XR→ROS teleoperation 경로에서 pose/control value와 분리되어 사라질 수 있고, downstream은 서로 다른 source states를 동일한 command representation으로 처리할 수 있다는 가설에서 시작했다.

## 2. Related-work-driven refinement

Generic cross-layer state-transition 또는 network delay만으로는 XR contribution과 actionable boundary를 분리하기 어렵다. 따라서 연구 질문을 다음 세 층으로 제한했다.

1. XR source가 의미를 생성하는가.
2. XR app/wire/ROS/controller가 그 의미를 보존·gate·regenerate하는가.
3. 의미 소실 뒤 downstream callback/target consequence가 있는가.

이번 작업은 Quest가 없는 조건에서 2와 software-level 3을 최대한 실행하고, 1의 actual hardware activation을 명시적으로 남겼다.

## 3. Revised research question

> XR safety-relevant tracking/source/freshness semantics가 XR→ROS boundary에서 보존되고 downstream control decision에 사용되는가?

핵심은 pose 숫자의 정확성만이 아니라 validity, actively-tracked/inferred, source identity, sample time, session/reference identity, clutch state의 lineage다.

## 4. Framework audit

| Stack | 핵심 결과 | 현재 evidence |
| --- | --- | --- |
| Spes | controller-valid/emulated/viewer states가 같은 packet으로 collapse; timestamp/generation 없음; reconnect와 jump recovery가 persistent invalidation을 제공하지 않음 | static + actual frontend/WSS/server `RUNTIME WITH SYNTHETIC SOURCE` |
| Quest2ROS2 | callback이 input stamp/frame을 읽지 않고 output now/base frame으로 대체; freshness guard 없음 | actual callback `RUNTIME WITH SYNTHETIC SOURCE`; ROS transport `BLOCKED_ENV` |
| PickNik | Unity publisher가 tracking state를 query/encode하지 않고 publication time 사용 | `CONFIRMED_STATIC_MACHINE_CHECKED`; Unity runtime `BLOCKED_ENV` |
| NVIDIA | linked release가 active/valid gating을 일부 제공; current main invalid recovery 10 tests PASS; tracked-vs-inferred와 timestamp는 완전 보존 아님 | linked release machine-checked static + current main runtime synthetic positive control |

## 5. Runtime findings without Quest

Canonical integrated run [`no_quest_20260830T142000Z`](../logs/no_quest/no_quest_20260830T142000Z/integrated_summary.jsonl): **7 PASS, 0 FAIL, 2 SKIP_ENV, 4 BLOCKED_HW**.

- Spes actual inline frontend A/B/C semantic collision: PASS.
- Spes actual HTTPS/WSS + actual server update 10 scenarios: PASS.
  - near/far reconnect, normal/delayed sample/delayed trajectory,
  - near/far explicit re-arm, hidden source switch,
  - application-level stall replay/old-generation replay.
- Quest2ROS2 actual callback age sweep, future stamp, stale trajectory, frame provenance: PASS.
- PickNik source assertion 10개: PASS, runtime 아님.
- NVIDIA linked-release machine check 8개 + current-main existing test 10개: PASS.
- Legacy S1 frontend/server: PASS.

`no_quest_20260830T141000Z`에서 WSS startup 직후 handshake timeout 1회가 있었고 suite는 중단 없이 9개를 계속 수행했다. 이 환경성 실패는 보존했으며 connection-only bounded retry 보강 뒤 canonical run이 10/10 PASS했다. Semantic assertion failure로 해석하지 않는다.

## 6. What remains hardware-dependent

Quest 없이는 다음만 답할 수 없다.

- Spes T1에서 controller pose가 non-null `emulatedPosition=true`가 되는지, null→viewer fallback이 되는지, 또는 완전히 다른 runtime behavior인지.
- 그 interval에 `move=true`와 server target callback이 실제로 계속되는지.
- recovery에서 last inferred pose→first reacquired pose correction과 explicit re-arm 유무.
- PickNik Unity Transform이 real tracking loss/focus loss에서 freeze, infer, reset 중 무엇을 하는지.
- NVIDIA native OpenXR/DeviceIO가 actual validity/tracked flags와 timestamp를 어떻게 생성하는지.
- Quest2ROS2 repository에 없는 XR producer가 source stamp/frame/validity를 어떻게 만드는지.

Physical robot motion은 hardware hypothesis 확인에도 필요하지 않으며 현재 범위 밖이다. dummy sink/server callback으로 먼저 판정한다.

## 7. Current research decision

**PROMISING — NEEDS QUEST VALIDATION**

이유는 semantic collision, missing freshness lineage, reconnect/control recovery가 actual software path에서 runtime으로 확인됐고 NVIDIA partial positive control과 대조가 가능해졌기 때문이다. 그러나 실제 Quest state activation과 end-to-end ROS/robot consequence가 없으므로 `STRONG GO` 또는 실제 safety impact claim으로 올릴 수 없다.

현재 허용 claim:

> The examined teleoperation implementations can collapse semantically distinct synthetic XR states or source-time histories into downstream representations that cannot distinguish them.

현재 금지 claim:

> Quest 3 tracking loss causes unsafe robot motion.

## 8. Next experiment

Quest 확보 즉시 가장 먼저 Spes T0/T1을 실행한다.

1. T0 baseline: controller source/pose exists, `emulatedPosition`, viewer pose, selected source, move, control packet index, server update index와 target delta를 기록한다.
2. T1 loss/recovery 5회: controller obstruction 동안 동일 필드를 기록한다. primary confirmation은 같은 interval의 `controllerPose != null`, `emulatedPosition=true`, `move=true`, continuing server callback이다.
3. controller pose가 null이면 secondary T3 viewer-fallback condition으로 분류한다. null이 아니면 fallback을 억지로 주장하지 않는다.
4. recovery는 last emulated pose, first reacquired pose, jump reject, first accepted/re-anchor, re-press move 여부를 기록한다.
5. 실제 trial은 [`SPES_QUEST_HW_RESULT.md`](SPES_QUEST_HW_RESULT.md)의 canonical table에만 반영한다.

## Environment/privileged boundary

Actual ROS/Docker validation을 추가하려면 사용자 terminal에서 다음을 먼저 실행한다.

```bash
newgrp docker
docker info
```

현재 session에서는 socket mode/ownership에도 불구하고 `docker info`가 permission denied다. `sudo`, socket chmod, daemon 변경은 수행하지 않았다. Unity executable도 없다.
