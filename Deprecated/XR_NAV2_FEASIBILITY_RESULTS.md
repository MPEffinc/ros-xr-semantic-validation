# Handoff: XR Mock → HORUS → Nav2 Feasibility

## 1. Executive Summary

- Canonical run `xr-nav2-20260826T125755Z`에서 F0–F6을 각각 5회, 총 **35/35 clean trial**로 완료했다. `RUN_COMPLETE`는 `measurement_valid=true`, `trial_errors=0`이었다.
- 검증 경로는 **Mock OpenXR-style lifecycle → 실제 HorusLink → 고정 HORUS bridge/backend/Nav2 adapter → 실제 Nav2 `NavigateToPose` → `nav2_loopback_sim` simulated robot**이다.
- F0 공식 explicit cancel은 5/5에서 같은 Goal을 `CANCELED`로 만들고 robot stop을 확인했다.
- 핵심 P2 결과인 F2 release와 F3 disconnect에서는 lease revoke가 5/5 관찰됐지만 cancel/terminal/stop은 5초 내 0/5였다. 실제 simulated `/odom` 누적 이동은 각각 중앙값 2.363350 m와 2.359485 m였다.
- F4 TTL expiry도 cancel 0/5였고 Goal은 5/5 revoke가 아니라 자연 `SUCCEEDED`로 끝났다. expiry 뒤 1.734535–2.008395 m를 더 이동했다.
- F5에서 B Goal은 5/5 A를 preempt했고 A는 `ABORTED`, B는 `EXECUTING`이었다. 따라서 dummy server의 A/B 동시 active 결과는 stock Nav2에서 재현되지 않았지만, B가 오기 전에는 A가 5/5 계속 실행 중이었다.
- 최종 판정은 **CONDITIONAL GO**다. actual Nav2와 actual simulated pose에서 revocation mismatch는 강화됐지만, 실제 Quest lifecycle과 second Action/framework는 아직 없다.

## 2. Why Mock XR

Quest/OpenXR runtime 전체를 모방하지 않고, `XR_SESSION_READY/FOCUSED/VISIBLE/STOPPING/EXITING`, `APP_ACTIVE/PAUSED`, `CONTROL_ACTIVE/RELEASED` 전이와 wall/monotonic timestamp만 재현했다.

공식 OpenXR 1.1에서 `FOCUSED`는 XR input을 받을 수 있는 상태이고 `VISIBLE`은 화면은 보이지만 XR input 대상이 아니다. `STOPPING`에서는 frame loop를 끝내고 `xrEndSession`을 호출해야 하며, `EXITING`은 XR 경험 종료, `LOSS_PENDING`은 현재 session 손실과 destroy/recreate 처리를 뜻한다. 이 의미는 [Khronos `XrSessionState` 공식 문서](https://registry.khronos.org/OpenXR/specs/1.1/man/html/XrSessionState.html)를 기준으로 했다.

- P1은 focus event만 만들고 connection, heartbeat, lease를 유지한다. HORUS가 OpenXR event를 직접 받지 않으므로 보조 대조군이다.
- P2는 `CONTROL_RELEASED` 뒤 lease release, disconnect 또는 heartbeat 중단/TTL expiry를 실제 HorusLink로 전달한다. 이것이 주 실험이다.
- Mock으로 확인한 것은 authority transition의 software end-to-end propagation이다. 실제 Quest 3에서 HMD removal, Home/background 또는 app stop이 같은 event/policy를 만든다는 것은 확인하지 않았다.
- OpenXR가 ROS/Nav2 Goal cancel을 자동 보장한다고 가정하지 않는다.

## 3. Architecture

```text
[Mock XR session/app/control state machine]
                    ↓ HorusLink TCP loopback
[Actual horus_unity_bridge @ fixed revision]
                    ↓ protected goal/cancel topics
[Actual HORUS backend / Nav2ActionAdapter]
                    ↓ /navigate_to_pose
[Actual Nav2 planner/controller/BT navigator]
                    ↓ /cmd_vel
[nav2_loopback_sim simulated robot]
                    ↓ /odom + TF
```

Mock인 부분은 XR state/event와 client policy뿐이다. Bridge, backend, adapter 및 Nav2 Action Server를 dummy로 대체하지 않았다. 모든 주요 event는 동일 process의 monotonic timestamp와 UTC wall timestamp로 `xr-horus-nav2-timeline/v1` JSONL에 기록했다.

## 4. Environment / Fixed Revisions

| Component | Revision / version |
|---|---|
| HORUS ROS 2 | `eca75cbf559f09ff793d8993338b2f1ffed1adfd` |
| HORUS | `819cdfdc74f1a0c2bd73946dc14897a533f68b61` |
| HORUS SDK | `f4f00dab41910676519d545515531ec243414044` |
| COMPAS XR, secondary only | `b86e6fbbacdc8e84183fc08c846176a1c79304ca` |
| COMPAS XR Unity Assembly | `f1516ca568b101447507aebc28a594bdc358df3e` |
| ROS | ROS 2 Jazzy |
| Navigation2 | `1.3.12-1noble.20260615.181551` |
| nav2_bringup | `1.3.12-1noble.20260616.082701` |
| nav2_loopback_sim | `1.3.12-1noble.20260615.151554` |
| nav2_msgs | `1.3.12-1noble.20260615.145957` |

- Image: `ros-xr-horus-nav2-jazzy:local`, ID `sha256:ff6138bc9bdb6864ffaff12d3a03030c6fab65a6ae18787e0aa0ce7840ccdc86`, 1,205,775,265 bytes.
- Test time: 2026-08-26 21:57:55–22:03:07 KST.
- Runtime: `docker run --network none`, `ROS_LOCALHOST_ONLY=1`, domain 95, no host network, privileged mode, public port, Quest 또는 physical robot.
- Nav2 preflight에서 map/planner/controller/BT lifecycle node가 `active`, `/navigate_to_pose`, `/cmd_vel`, `/odom`과 두 목표의 free-space를 확인했다.
- 시작 pose `(-2.0,-0.5)`, Goal A `(1.5,-0.5)`, Goal B `(-1.5,1.0)`, motion 확인 뒤 2초에 event, 관찰 5초, lease TTL 1200 ms, heartbeat 300 ms였다.
- Nova Carter/Isaac Sim은 GPU와 대규모 dependency 비용 때문에 사용하지 않았다. 대신 공식 `tb3_loopback_simulation.launch.py`를 사용했다. [Nav2 공식 문서](https://docs.nav2.org/configuration/packages/configuring-loopback-sim.html)에 따르면 loopback simulator는 실제 hardware/physics simulator를 대신해 `cmd_vel`로 ideal frictionless-plane odometry를 만든다. 즉 actual Nav2 고수준 behavior는 사용하지만 inertia, wheel slip, actuator/brake, collision dynamics는 모델링하지 않는다.
- SROS2는 이번 runtime에 적용하지 않았으며 이전 SROS2 bridge 결과와 혼합하지 않는다.

## 5. F0 Explicit Cancel Baseline

공식 HORUS cancel path가 actual Nav2까지 정상 도달하는지 확인했다.

| Metric | Result, median [min, max] |
|---|---:|
| Trials | 5/5 `EXPLICIT_CANCEL_SAFE` |
| cancel send → HORUS cancel topic | 3.572 ms [0.900, 6.654] |
| cancel send → `CANCELED` | 24.738 ms [22.251, 29.866] |
| cancel send → first zero-cmd period | 228.873 ms [220.321, 238.102] |
| cancel send → certified robot stop | 738.931 ms [735.905, 758.254] |
| post-cancel `/odom` path | 0.079426 m [0.066757, 0.084921] |

Stop은 cmd magnitude `hypot(vx,vy)+|wz| ≤ 0.01`이고 0.5초 동안 `/odom` path가 0.005 m 이하일 때 확정했다. 따라서 F2–F4의 cancel 0은 cancel 경로 자체가 고장 난 결과가 아니다.

## 6. F1 Focus Loss Only

`XR_SESSION_FOCUSED → XR_SESSION_VISIBLE`를 만들되 `CONTROL_ACTIVE`, connection, heartbeat, lease를 유지했다.

- XR input inactive: 5/5.
- heartbeat 유지 및 lease present: 5/5.
- Goal: 5/5 `EXECUTING @ 5s`.
- focus event 뒤 `/odom` path: 중앙값 2.357993 m [2.351485, 2.371290], 모두 5초 right-censored.

이는 P1에서 자동 cross-domain propagation이 없다는 결과다. HORUS가 OpenXR state를 입력으로 받지 않는 구조이므로 이것만으로 vulnerability라고 판정하지 않는다.

## 7. F2 Focus Loss + Lease Release

`FOCUSED → VISIBLE → CONTROL_RELEASED → explicit lease release`를 수행했다.

- authority event → `lease_released`: 중앙값 1.209 ms [0.848, 1.882], 5/5.
- HORUS cancel topic, Nav2 `CANCELING`, terminal, robot stop: 각각 0/5 within 5 s.
- Goal: 5/5 `EXECUTING @ 5s`.
- release 뒤 actual `/odom` path: 중앙값 **2.363350 m** [2.351388, 2.372768], 5/5 right-censored.

XR mock application이 control authority 종료를 HORUS까지 명시 전달했지만 accepted Goal과 motion은 회수되지 않았다. 이것이 가장 직접적인 feasibility evidence다.

## 8. F3 STOPPING + Disconnect

`XR_SESSION_STOPPING → CONTROL_RELEASED → HorusLink disconnect`를 수행했다.

- authority event → `client_disconnected_release`: 중앙값 0.920 ms [0.537, 2.925], 5/5.
- cancel topic, Nav2 `CANCELING`, terminal, robot stop: 각각 0/5 within 5 s.
- Goal: 5/5 `EXECUTING @ 5s`.
- disconnect 뒤 `/odom` path: 중앙값 **2.359485 m** [2.344652, 2.362556], 5/5 right-censored.

Transport/lease cleanup과 이미 accepted된 Nav2 Action lifecycle이 분리돼 있음을 actual stack에서 확인했다.

## 9. F4 TTL Expiry

`CONTROL_RELEASED`를 기록하고 heartbeat를 중단해 TTL expiry를 기다렸다.

- authority event → `lease_expired`: 중앙값 1439.974 ms [946.773, 1481.202], 5/5. heartbeat phase와 expiry polling 때문에 고정 1200 ms와 차이가 난다.
- cancel topic과 Nav2 `CANCELING`: 0/5.
- Goal: 5/5 revoke로 끝나지 않고 자연 `SUCCEEDED`.
- expiry → natural terminal: 중앙값 3878.639 ms [3836.037, 4488.081].
- expiry 뒤 `/odom` path: 중앙값 **1.757236 m** [1.734535, 2.008395].
- certified stop은 4/5에서 5006.436–5008.333 ms에 관찰됐다. F4-T02는 Goal이 `SUCCEEDED`였지만 5초 창 안에 0.5초 stop hold가 완성되지 않아 stop latency만 right-censored다.

정지는 revocation cancel 때문이 아니라 Goal의 자연 완료 뒤 발생했다.

## 10. F5 Authority Handoff

A가 release한 뒤 B가 새 lease와 Goal B를 요청했다.

- A release → B lease grant: 중앙값 29.527 ms [28.922, 34.890].
- B grant 시 A Goal: 5/5 `EXECUTING`.
- A release → B Goal accepted: 중앙값 74.696 ms [71.712, 95.923], 5/5.
- B Goal send → accepted: 중앙값 20.066 ms [17.284, 36.137].
- B Goal send → A terminal: 중앙값 30.370 ms [19.472, 35.977].
- 결과: **5/5 `C_B_PREEMPTS_A`**. A는 모두 `ABORTED`, B는 모두 `EXECUTING`이었다. Release 자체의 cancel topic은 없었다.
- A release 뒤 5초 `/odom` path는 중앙값 0.629290 m [0.624602, 0.659297]. 이는 A와 B motion이 섞인 전체 path이지 A-only unauthorized distance가 아니다.
- release부터 B preemption 사이 `moving=false` cmd transition은 0/5로, command stream에 확인 가능한 stop gap이 없었다.
- 측정 종료 뒤 integrity check에서 B의 일반 HORUS cancel은 0/5였고 direct ROS Action cancel-all이 B UUID를 5/5 정리했다. Cleanup fallback은 위 측정치에서 제외했다. 이는 B response가 단일 `active_goal_handle`을 설정한 뒤 A의 늦은 result가 그 handle을 무조건 reset하는 fixed adapter 구조와 일치하는 race 진단이지, 별도 production-fix 검증은 아니다.

동일 `NavigateToPose`의 새 Goal이 기존 Goal을 preempt하는 것은 fixed Nav2의 [`NavigateToPoseNavigator::onPreempt` 경로](https://github.com/ros-navigation/navigation2/blob/1.3.12/nav2_bt_navigator/src/navigators/navigate_to_pose.cpp)와 일치한다. 그러나 이는 B Goal이 들어온 뒤의 handoff만 정리하며, 새 Goal이 없는 F2–F4 revocation을 해결하지 않는다.

## 11. F6 Replay / Epoch

- Public HORUS Goal command에는 session/lease epoch field가 없고, `lease_version`은 heartbeat마다 바뀌는 global counter라 Goal에 bind된 안정 epoch가 아니다.
- B가 lease를 보유할 때 old A connection의 Goal은 5/5 차단됐다. 이는 현재 holder와 HorusLink connection ownership에 의한 보호다.
- B release 뒤 새 connection이 A의 예전 logical `session_id`를 재사용해 lease를 다시 얻은 경우는 5/5였고, 이어 stale-labeled Goal도 5/5 accepted됐다.
- B release → stale logical session grant는 중앙값 28.712 ms [26.708, 32.537], Goal send → accept는 19.794 ms [16.921, 30.768]였다.
- 이후 `/odom` path 중앙값은 0.932142 m [0.886753, 1.200063], 5초 right-censored였다.

이는 **epoch capability probe**다. 재사용 가능한 authenticated credential이나 cryptographic packet replay를 시험한 것이 아니므로 session resurrection exploit로 주장하지 않는다. 관찰된 사실은 command schema가 stale epoch를 표현하거나 검증할 수 없다는 점과, old logical string 자체가 새 lease를 막지 않는다는 점이다.

## 12. Actual Nav2 vs Previous Dummy Server

| Property | Previous Dummy | Actual Nav2 |
|---|---|---|
| Action server | Synthetic multi-goal `NavigateToPose` | Actual `bt_navigator` `NavigateToPose` |
| Explicit cancel | 5/5 `CANCELED`; terminal 10.052–57.937 ms | 5/5 `CANCELED`; terminal 22.251–29.866 ms |
| Release | cancel 0/5, `EXECUTING ≥10s` | cancel 0/5, `EXECUTING ≥5s`, 2.351388–2.372768 m |
| Disconnect | cancel 0/5, `EXECUTING ≥10s` | cancel 0/5, `EXECUTING ≥5s`, 2.344652–2.362556 m |
| TTL | cancel 0/5, `EXECUTING ≥10s` | cancel 0/5, 자연 `SUCCEEDED` 5/5, 1.734535–2.008395 m |
| Handoff | A/B distinct Goal 동시 active 5/5 | B가 A preempt 5/5; A `ABORTED`, B `EXECUTING` |
| Distance | 0.1 m/s software estimate | actual loopback `/odom` polyline |
| Robot dynamics | 없음 | ideal frictionless loopback; physical dynamics 없음 |

Dummy의 장시간 revocation gap은 actual Nav2에서도 F2–F4에서 실질적으로 유지됐다. 반면 dummy의 concurrent multi-goal conflict는 actual Nav2의 same-type preemption으로 흡수됐다. 따라서 physical-risk 주장은 좁아졌지만 revocation mismatch 자체는 강화됐다.

## 13. Quantitative Impact

값은 median [min, max]이며 `NOT OBSERVED`는 5초 measurement window의 right-censored 결과다.

| Case | Authority/cancel → lease/topic | Revoke/cancel → terminal | → certified stop | Post-event `/odom` path |
|---|---:|---:|---:|---:|
| F0 cancel | topic 3.572 [0.900, 6.654] ms | 24.738 [22.251, 29.866] ms | 738.931 [735.905, 758.254] ms | 0.079426 [0.066757, 0.084921] m |
| F1 event only | N/A | Goal `EXECUTING ≥5s` | NOT OBSERVED | 2.357993 [2.351485, 2.371290] m |
| F2 release | 1.209 [0.848, 1.882] ms | NOT OBSERVED | NOT OBSERVED | 2.363350 [2.351388, 2.372768] m |
| F3 disconnect | 0.920 [0.537, 2.925] ms | NOT OBSERVED | NOT OBSERVED | 2.359485 [2.344652, 2.362556] m |
| F4 TTL | 1439.974 [946.773, 1481.202] ms | natural success 3878.639 [3836.037, 4488.081] ms | 4/5, 5006.436–5008.333 ms | 1.757236 [1.734535, 2.008395] m |
| F5 handoff | B grant 29.527 [28.922, 34.890] ms | B send→A abort 30.370 [19.472, 35.977] ms | no stop gap | 0.629290 [0.624602, 0.659297] m |
| F6 epoch probe | stale grant 28.712 [26.708, 32.537] ms | N/A | NOT OBSERVED | 0.932142 [0.886753, 1.200063] m |

F2/F3 거리는 관찰 종료 시에도 이동 중이어서 lower bound다. F4는 4/5 stop detection만 집계했고, F5 거리는 preemption 전후 Goal의 혼합 경로다.

## 14. Minimal Ownership Fix

**이번 canonical run에서는 NOT RUN**이다. Fixed checkout을 변경하지 않고 actual-stack feasibility를 먼저 확정했다. 기존 test-only robot-wide/latest-handle hook은 nominal revoke를 멈췄지만 same-robot unrelated latest Goal을 5/5 잘못 cancel했으므로 재사용하지 않았다.

다음 최소 prototype은 `{canonical_robot, logical_connection, lease_epoch, command_id, goal_uuid, action_type, state}`를 bind하고, revoked epoch의 pending/active Goal만 cancel해야 한다. A exact cancel, B/unrelated/other-robot Goal 보존, late goal response, reconnect stale epoch를 함께 검증해야 한다. 이는 ORBIT/eBPF 또는 production defense가 아니다.

## 15. Confirmed / Unconfirmed / Rejected

**CONFIRMED**

- 고정 HORUS와 actual Nav2 path의 35/35 trial이 clean하게 완료됐다.
- F0 official cancel은 actual Nav2와 simulated robot을 5/5 멈췄다.
- F2/F3는 lease cleanup 뒤에도 cancel 없이 5초 이상 Goal과 motion이 지속됐다.
- F4는 TTL expiry 뒤 cancel 없이 Goal이 자연 완료됐다.
- F5 same-type handoff는 actual Nav2가 5/5 preempt했다.
- F5 post-measurement HORUS B-cancel miss는 fixed adapter의 late-result/single-handle race와 일치했지만, direct cancel-all cleanup과 본 측정 결과는 분리했다.
- F6 public Goal schema에는 lease/session epoch binding이 없다.

**UNCONFIRMED**

- 실제 Quest/HORUS Unity app이 focus/pause/STOPPING을 어떤 lease/cancel policy로 변환하는지.
- physical robot의 stop distance, collision 또는 safety impact.
- Nav2 외 Action이나 다른 maintained XR–ROS framework의 같은 mismatch.
- owner/epoch prototype의 race/selectivity correctness와 최종 novelty.
- F6의 authenticated replay/session-resurrection 공격 가능성.
- COMPAS custom executor에서의 actual execution.

**REJECTED 또는 하향**

- “Dummy의 A/B 동시 active가 stock Nav2에서도 그대로 발생한다”: 5/5 preemption으로 반박됐다.
- “Nav2 자체 preemption이 lease revocation 전체를 자동 해결한다”: 새 Goal이 없는 F2–F4에서 반박됐다.
- “모든 revoke Goal이 무기한 실행된다”: F4는 자연 완료했으므로 과도한 표현이다.
- “Mock 결과가 실제 Quest exploit이다”: 증거 범위를 벗어나 기각한다.

## 16. XR Relevance

이 결과가 단순 일반 ROS Action 시험만은 아닌 이유는 XR session/app/control state 전이를 P1/P2 정책으로 만들고, 실제 HorusLink lease lifecycle과 downstream Nav2 Action/motion까지 하나의 timeline으로 추적했기 때문이다. 문제의 핵심은 ROS Action primitive 자체가 아니라 **XR authority 종료가 bridge admission과 이미 실행 중인 robot Action에 종단 간 bind되는가**다.

XR relevance는 이전 dummy 실험보다 **부분적으로 강해졌다**. Actual HORUS, actual Nav2 controller output과 simulated pose에서 P2 mismatch를 측정했기 때문이다. 그러나 앞단 event는 real OpenXR/Quest event가 아니므로 actual device/user interaction relevance는 여전히 미확인이다. 이는 OpenXR, ROS 2, Nav2 또는 SROS2 자체의 취약점 주장이 아니다.

## 17. Final Research Interpretation

현재 Item인 **“XR control authority revocation과 in-flight ROS/robot Action lifecycle의 end-to-end binding”**은 Main Item 후보로 유지할 수 있다.

- Admission-time lease가 끝나도 accepted Action ownership은 자동 회수되지 않았다.
- Actual Nav2 preemption은 새 holder Goal이 들어온 handoff conflict는 정리했지만, release/disconnect/TTL 뒤 새 Goal이 없는 실행 공백은 해결하지 못했다.
- 따라서 strongest claim은 concurrent goals가 아니라 **revocation-to-execution termination gap과 measurable simulated consequence**다.
- 정확한 방어에는 owner/lease epoch/Goal UUID selectivity가 필요하다는 기존 동기는 유지된다.
- COMPAS XR는 final executor가 custom인 Case C라 secondary evidence로만 유지한다.

## 18. GO / NO-GO

**CONDITIONAL GO**

근거:

1. P2 authority event가 실제 HORUS lease release/cleanup으로 5/5 전파됐다.
2. 그 뒤 actual Nav2 cancel은 0/15(F2–F4)이었다.
3. F2/F3는 Goal과 motion이 5초 이상 지속됐고 약 2.35–2.37 m의 actual simulated path가 측정됐다.
4. F4도 revoke가 아니라 자연 완료까지 약 1.73–2.01 m 이동했다.
5. F5 preemption은 dummy의 동시-active 위험을 낮췄지만 revocation gap을 제거하지 않았다.
6. 반면 real Quest lifecycle, second Action/framework, physical dynamics 및 ownership fix는 미확인이다.

따라서 WEAK/NO-GO로 내릴 만큼 Nav2가 revoke를 안전하게 흡수하지 않았지만, STRONG GO로 일반화할 증거도 아직 부족하다.

## 19. What We Can Claim

- “OpenXR-style authority transition을 재현한 software testbed에서 실제 HORUS lease lifecycle과 actual Nav2 execution termination의 종단 간 전파를 측정했다.”
- “고정 HORUS revision에서 release와 disconnect 뒤 accepted Nav2 Goal은 5회 모두 cancel 없이 최소 5초 계속 실행됐다.”
- “TTL expiry 뒤 Goal은 cancel되지 않고 5회 모두 자연 성공까지 진행됐다.”
- “Lease revoke 뒤 `nav2_loopback_sim`의 actual `/odom` 출력 기준으로 case별 1.73–2.37 m의 추가 path를 관찰했다.”
- “Actual Nav2는 B의 same-type Goal로 A를 5/5 preempt해 dummy server의 simultaneous-active 결과를 완화했지만, 새 Goal 없는 revocation은 해결하지 않았다.”
- “이 결과는 shared XR–ROS bridge에서 revocable, owner-bound exact-action authorization을 검증할 필요성을 뒷받침한다.”

## 20. What We Must Not Claim

- 실제 Quest 3에서 HMD를 벗거나 focus를 잃으면 공격이 발생했다고 주장하지 않는다.
- physical robot이 1.7–2.4 m 이동했거나 충돌했다고 주장하지 않는다.
- 모든 XR–ROS framework, 모든 ROS Action 또는 모든 Nav2 deployment에 일반화하지 않는다.
- OpenXR, ROS 2, Nav2 또는 SROS2 자체의 취약점/우회라고 주장하지 않는다.
- F1 event-only 지속을 단독 vulnerability로 부르지 않는다.
- F5 path를 old A의 unauthorized distance로 부르지 않는다.
- F6를 authenticated replay나 confirmed session resurrection으로 표현하지 않는다.
- test-only latest-handle hook을 production defense로 제시하지 않는다.
- COMPAS physical execution, 최종 novelty 또는 최초성을 주장하지 않는다.

## 21. Next Recommended Work

1. **실제 Quest/OpenXR lifecycle trace가 이제 필요하다.** HORUS Unity app에서 `OnApplicationFocus`, `OnApplicationPause`, `XrSessionStateChanged`, heartbeat/release/cancel을 같은 timestamp로 5회씩 기록한다. 실제 Quest trigger claim에는 필수지만 이번 software mechanism을 다시 확인하는 데는 필요 없다.
2. `{connection, robot, lease_epoch, command_id, goal_uuid}` owner-aware 최소 prototype을 만들고 pending/accepted/active Goal, late result, reconnect, same/other-robot selectivity를 회귀 시험한다.
3. Official second Action adapter 또는 다른 maintained XR–ROS framework에서 같은 P2 matrix를 반복한다.
4. 필요하면 Gazebo/Isaac 같은 physics simulator로 braking/dynamics를 추가한다. Physical robot은 software defense와 kill criteria를 통과한 뒤에만 검토한다.
5. Actual Quest가 모든 relevant transition에서 bounded explicit cancel을 안정적으로 보내면 focus-trigger attack claim은 폐기하거나 integration case study로 축소한다.

## 22. 사용자 이해용 쉬운 설명

1. **앞단 XR을 어떻게 Mock했는가?** Quest 기기나 OpenXR runtime을 흉내 낸 것이 아니라, focus/visible/stopping과 app/control 상태 전이 및 policy만 재현했다.
2. **중간 HORUS는 실제 코드인가?** 그렇다. HorusLink, bridge, backend와 Nav2 adapter 모두 고정된 공개 HORUS code를 실제로 build/run했다.
3. **뒷단 Nav2는 실제 stack인가?** 그렇다. 실제 planner/controller/BT navigator를 썼고, robot hardware만 ideal loopback simulator로 바꿨다.
4. **XR 권한이 끝났을 때 Robot은 어떻게 됐는가?** Release/disconnect 뒤 lease는 즉시 없어졌지만 Goal은 cancel되지 않았고 5초 동안 약 2.35 m 더 움직였다. TTL도 자연 완료까지 이동했다.
5. **Dummy 실험과 결과가 달랐는가?** Revocation 뒤 지속은 같았지만, handoff에서는 actual Nav2가 B Goal로 A를 5/5 preempt해 A/B 동시 active는 사라졌다.
6. **이게 정말 XR 연구라고 할 수 있는가?** XR authority event가 bridge lease와 robot Action까지 어떻게 전파되는지를 보는 XR–ROS integration 연구다. 다만 실제 Quest event를 아직 쓰지 않아 XR relevance는 부분적으로만 확정됐다.
7. **다음에는 실제 Quest가 필요한가?** Software mechanism에는 필요 없지만, 실제 HMD/user action이 이 경로를 촉발한다는 최종 claim에는 필요하다.

## 23. Files / Evidence Links

- [XR/Nav2 Evidence Summary](/home/cclab/ros_xr/evidence/xr_nav2_feasibility_summary.md)
- [Unified Mock XR Timeline](/home/cclab/ros_xr/evidence/xr_mock_timeline.log) — SHA-256 `1108870c60533aaf7cdad3c97aee37281a37238747c66b5a14c7596322ba8afd`
- [Nav2 Revocation Runtime](/home/cclab/ros_xr/evidence/nav2_revocation_runtime.log) — SHA-256 `8fb5cbffd2c909b7e0fde9be9b654ff0a2171751b3cdffbd05188059f71d71f1`
- [Nav2 Handoff Runtime](/home/cclab/ros_xr/evidence/nav2_handoff_runtime.log) — SHA-256 `4c82afd5cad559eeee5e1b59121fdf9ad2475f97eb6f74247a0d361c2240db4e`
- [Mock XR Client](/home/cclab/ros_xr/authorization_env/xr_mock_client.py)
- [Reproduction Runner](/home/cclab/ros_xr/authorization_env/run_xr_nav2_feasibility.sh)
- [Isolated Docker Image Definition](/home/cclab/ros_xr/authorization_env/Dockerfile)
- [Previous Dummy Follow-up](/home/cclab/ros_xr/DECISIVE_FOLLOWUP_RESULTS.md)
- [Research Context](/home/cclab/ros_xr/RESEARCH_CONTEXT.md)

Evidence summary SHA-256: `7748ede609274532c38c128fef8945cefa476a9f4f3cadf1a52e1595d6572b78`.
