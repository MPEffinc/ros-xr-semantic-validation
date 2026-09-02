# Handoff: Decisive XR–ROS Authorization Follow-up

## 1. Executive Summary

- 목적: 기존 HORUS의 0.7–1.0초 bounded observation을 5회 독립 반복·10초 checkpoint·handoff conflict로 강화하고, COMPAS XR의 공개 실행 경계를 끝까지 추적해 `Revocable Exact-Action Authorization in XR–ROS Systems`의 GO/NO-GO를 결정했다.
- 결정적 결과: unmodified HORUS에서 공식 cancel은 5/5 정상 동작했지만, lease release·TTL expiry·disconnect는 각각 5/5에서 accepted Nav2 Goal을 cancel하지 않았다. Goal은 모든 0.5/1/3/5/10초 checkpoint에서 `EXECUTING`이었다.
- Handoff 결과: A release 후 B는 5/5에서 새 lease와 서로 다른 Goal UUID를 얻었다. A와 B Goal은 5/5 모두 10초 checkpoint까지 동시에 active였고 cancel/preemption은 없었다.
- 최소 수정 결과: robot-wide cancel hook은 nominal R1–R4를 멈췄지만, ownership selectivity challenge 5/5에서 lease-owned A Goal이 아니라 더 최근의 unrelated Goal을 잘못 취소했다. 안전한 production fix는 owner/lease epoch/Goal UUID의 구조적 binding을 요구한다.
- COMPAS 결과: 공개 공식/대표 executor는 찾지 못했다. 공식 component/example은 final robot control을 custom integration에 위임하므로 **Case C**다. T_A→T_B 실제 robot-input acceptance는 수행하지 않았다.
- 최종 판정: **CONDITIONAL GO**.
- Blocker: STRONG GO에 필요한 두 번째 공식 Action 또는 두 번째 framework의 end-to-end consequence, 실제 Quest focus lifecycle, COMPAS downstream executor가 아직 없다. 현재 software-only HORUS 결과 자체에는 실행 blocker가 없다.

## 2. Previous Evidence vs New Evidence

| 구분 | 이전 증거 | 이번 증거 | 변화 |
|---|---|---|---|
| Explicit cancel | 별도 정량 기준선 없음 | 5/5 동일 Goal UUID cancel, `CANCELED` terminal | Revocation 비교의 control path 유효성 확보 |
| Release | 1.0초 active, cancel 0 | 5/5, 10초까지 active, cancel 0 | 단순 asynchronous delay 설명을 반박 |
| TTL expiry | 0.7초 active, cancel 0 | 5/5, 10초까지 active, cancel 0 | 반복성과 장시간 영향 강화 |
| Disconnect | 1.0초 active, cancel 0 | 5/5, 10초까지 active, cancel 0 | transport cleanup과 action lifecycle 분리 강화 |
| Handoff | B acquire 가능만 확인 | 5/5 A/B distinct Goal 동시 active, max 2 | conflict 가능성을 runtime으로 추가 |
| Fix coverage | source gap만 확인 | nominal cancel 성공 + wrong-goal cancel 5/5 | 단순 robot-wide hook과 ownership-safe fix를 구분 |
| COMPAS | T_B가 inert handoff까지 도달 | 공식 GHX/component/executor boundary 재감사, Case C 확정 | physical execution claim은 여전히 미확인 |

새 runtime은 unmodified HORUS 25 trials와 별도 test-only variant 30 trials로 구성된다. 모든 trial은 시작 전 active Goal 0과 lease snapshot empty를 확인했고, 종료 후 action cleanup 및 backend robot unregistration을 확인했다.

## 3. Environment and Fixed Revisions

| Component | Repository | Fixed revision |
|---|---|---|
| HORUS ROS 2 | `RICE-unige/horus_ros2` | `eca75cbf559f09ff793d8993338b2f1ffed1adfd` |
| HORUS app artifacts/docs | `RICE-unige/horus` | `819cdfdc74f1a0c2bd73946dc14897a533f68b61` |
| HORUS SDK | `RICE-unige/horus_sdk` | `f4f00dab41910676519d545515531ec243414044` |
| COMPAS XR | `compas-dev/compas_xr` | `b86e6fbbacdc8e84183fc08c846176a1c79304ca` |
| COMPAS XR Unity Assembly | `compas-dev/compas_xr_unity_assembly` | `f1516ca568b101447507aebc28a594bdc358df3e` |

- Test date: 2026-08-26 (Asia/Seoul).
- Docker: client/server 29.1.3; reused image `ros-xr-horus-jazzy:local`, ID `sha256:77e3a03de6660509f56a5b029916840c5e39399504be48f8c30035bdd960afed`.
- ROS: ROS 2 Jazzy, default Fast DDS RMW observed in the fixed build/runtime.
- Actual HORUS path: HorusLink client → `horus_unity_bridge` → protected goal/cancel topic → `horus_backend/Nav2ActionAdapter` → dummy `NavigateToPose` action server.
- Test configuration: 32초 Goal, 2초 뒤 revocation, TTL 1200 ms, 0.25초 feedback, 0.5/1/3/5/10초 checkpoints, 0.1 m/s software model.
- Isolation: `docker run --network none`, container loopback listeners only, no host network, privileged mode, public broker/port, Quest, or physical robot.
- SROS2: 이번 follow-up runtime에는 적용하지 않았다. 이전 SROS2/bridge baseline과 혼합해서 해석하지 않는다.

## 4. Explicit Cancel Baseline

- Expected: A가 lease를 유지한 상태에서 공식 `/robot1/goal_cancel` path를 사용하면 Nav2 adapter가 action server에 같은 Goal UUID의 cancel을 보내고 terminal state가 `CANCELED`가 된다.
- Observed: **5/5 PASS**. 각 trial에서 cancel callback UUID가 accepted Goal UUID와 일치했다.
- Cancel callback latency: 1.403–18.571 ms, 평균 4.966 ms.
- Cancel sent→terminal latency: 10.052–57.937 ms, 평균 23.629 ms.
- Feedback: cancel 전 각 trial 8회, feedback error 0.
- Verdict: action server와 HORUS 공식 cancel path는 정상이다. 따라서 R1–R3의 cancel 0은 “cancel 기능 자체가 고장”이라는 설명으로 환원되지 않는다.

## 5. Lease Revocation Results

| Case | Trials | Cancel Requests | Goal Active Duration | Terminal State | Verdict |
|---|---:|---:|---:|---|---|
| R1 Release | 5/5 | 0 | 10.000063–10.002296 s lower bound | `EXECUTING @ 10s`; 이후 test cleanup abort | 5/5 continued |
| R2 TTL Expiry | 5/5 | 0 | 10.000068–10.000172 s lower bound | `EXECUTING @ 10s`; 이후 test cleanup abort | 5/5 continued |
| R3 Disconnect | 5/5 | 0 | 10.000044–10.000076 s lower bound | `EXECUTING @ 10s`; 이후 test cleanup abort | 5/5 continued |
| R4 Handoff | 5/5 | 0 | A: 10.000059–10.000643 s lower bound | A/B 모두 `EXECUTING @ 10s`; 이후 test cleanup abort | 5/5 simultaneous |

Case별 해석:

- Release: lease snapshot에서 A가 제거된 뒤에도 모든 0.5/1/3/5/10초 checkpoint에서 같은 Goal UUID가 `EXECUTING`이었다. 0.1 m/s 모델의 추가 거리는 1.000006–1.000230 m다.
- TTL: heartbeat 중단과 `lease_expired` event 확인 뒤에도 모든 checkpoint에서 `EXECUTING`이었다. 추가 거리는 1.000007–1.000017 m다.
- Disconnect: A의 두 HorusLink lane을 종료하고 `client_disconnected_release`를 확인한 뒤에도 모든 checkpoint에서 `EXECUTING`이었다. 추가 거리는 1.000004–1.000008 m다.
- Handoff: A release 뒤 B의 새 lease grant와 Goal acceptance가 모두 성공했다. A의 추가 거리는 1.000006–1.000064 m다.

이 시간과 거리는 right-censored lower bound다. Goal은 32초로 설정됐지만 10초 measurement 뒤 test harness가 강제 abort해 trial을 깨끗하게 만들었으므로 자연 완료까지 지속됐다고 주장하지 않는다. 거리도 실제 이동이 아니라 constant-speed software model이다.

## 6. Action Handoff / Conflict

- A Goal: 5/5에서 release 후 10초까지 `EXECUTING`, cancel 0.
- B Goal: 5/5 accepted. A release event 관측 뒤 62.712–70.274 ms에 action server가 B Goal을 수락했다.
- Goal identity: A/B 10개 Goal UUID가 모두 서로 달랐고 unique했다.
- Concurrent state: 모든 0.5/1/3/5/10초 checkpoint에서 A와 B가 함께 `EXECUTING`; maximum active Goal count 2.
- Preemption: 없음. action server cancel callback 0, A terminal 전환 0.
- 해석: tested HORUS bridge/backend는 lease handoff를 accepted Action ownership handoff로 변환하지 않았다. 다만 dummy server는 concurrency 관찰을 위해 여러 Goal을 수락하도록 구성됐다. 실제 Nav2 controller의 preemption, 물리 충돌 또는 실제 로봇 이동을 입증한 결과는 아니다.

## 7. Minimal Fix Coverage

적용한 patch는 fixed repository가 아니라 container의 `/tmp` source copy에만 다음 counterfactual을 추가했다.

```text
lease release / expiry / disconnect
→ robot-name-scoped /<robot>/goal_cancel publish
→ Nav2ActionAdapter가 보유한 latest active_goal_handle cancel
```

Nominal coverage:

| Case | Trials | Outcome | Revocation event→terminal |
|---|---:|---|---:|
| R1 Release | 5/5 | A `CANCELED` | 12.115–20.391 ms |
| R2 TTL Expiry | 5/5 | A `CANCELED` | 12.712–36.152 ms |
| R3 Disconnect | 5/5 | A `CANCELED` | 10.232–17.389 ms |
| R4 Handoff | 5/5 | A `CANCELED`, B `EXECUTING` | A: 0.137–26.087 ms |

R4의 probe label `B_PREEMPTED_A_WITH_CANCEL`은 outcome 분류명일 뿐, 실제 cancel 원인은 B Goal이 아니라 release hook이다.

Selectivity challenge:

1. A가 HorusLink/lease path로 Goal G_A를 시작했다.
2. 같은 robot에 독립 ROS-side Goal G_U를 나중에 넣어 adapter의 latest handle로 만들었다.
3. A lease를 release했다.
4. 기대는 G_A만 cancel하고 G_U는 보존하는 것이었다.

실제 결과는 **5/5 `WRONG_LATEST_GOAL_CANCELLED`**였다.

- `cancel_goal_id == G_U != G_A`가 모든 trial에서 성립했다.
- G_A cancel count 0, G_U cancel count 1.
- G_A는 10.000065–10.002784초 더 `EXECUTING`; modeled 1.000007–1.000278 m.
- G_U는 `CANCELED`.
- max active Goals 2.

다른 robot의 Goal은 runtime으로 추가 시험하지 않았다. Test patch가 robot-name topic으로 scope된다는 source 사실은 있지만, 같은 robot의 unrelated Goal에서 이미 selectivity가 실패했으므로 production-safe 판정은 불가능하다.

결론: nominal stop coverage는 작은 hook으로 만들 수 있지만, “회수된 holder가 시작한 Goal만” 정확히 정리하는 것은 한 줄 fix가 아니다. 최소 production 구조는 다음을 요구한다.

- canonical robot ID
- owner logical connection ID
- monotonically increasing lease epoch
- command ID와 action Goal UUID mapping
- pending/accepted/active/canceling/terminal state machine
- revocation 시 해당 epoch의 새 command 선차단
- cancel acceptance와 terminal result의 bounded wait
- old Goal의 늦은 response/result가 새 epoch Goal state를 덮지 못하는 isolation

Source trace:

- Admission 후 publish: `frameworks/horus_ros2@eca75cbf559f09ff793d8993338b2f1ffed1adfd:horus_unity_bridge/src/message_router.cpp:391-449`
- Disconnect lease erase only: `frameworks/horus_ros2@eca75cbf559f09ff793d8993338b2f1ffed1adfd:horus_unity_bridge/src/control_lease_manager.cpp:165-181`
- Release lease erase only: `frameworks/horus_ros2@eca75cbf559f09ff793d8993338b2f1ffed1adfd:horus_unity_bridge/src/control_lease_manager.cpp:469-496`
- TTL lease erase only: `frameworks/horus_ros2@eca75cbf559f09ff793d8993338b2f1ffed1adfd:horus_unity_bridge/src/control_lease_manager.cpp:560-583`
- Adapter stores robot plus one pending/latest handle, not connection/epoch: `frameworks/horus_ros2@eca75cbf559f09ff793d8993338b2f1ffed1adfd:horus_backend/include/horus_backend/nav2_action_adapter.hpp:47-68`
- Goal and explicit cancel paths: `frameworks/horus_ros2@eca75cbf559f09ff793d8993338b2f1ffed1adfd:horus_backend/src/nav2_action_adapter.cpp:106-183`

## 8. Second Action Type

- 수행 여부: **NOT RUN**.
- 정확한 이유: fixed public HORUS backend의 유일한 `rclcpp_action` adapter/type은 `nav2_msgs/action/NavigateToPose`다. `horus_interfaces`에 `.action` interface가 없고, waypoint는 `nav_msgs/Path`, takeoff/land는 one-shot topic, `ExecuteCommand`는 long-running executor가 아니다.
- 판정: **Nav2-adapter-specific limitation**.
- 억지로 FollowJointTrajectory 또는 synthetic vulnerable adapter를 추가하면 HORUS 공식 경로의 재현이 아니므로 수행하지 않았다.
- 보완 가능한 다음 실험: 같은 Nav2 adapter에서 G_A/epoch1 revoke 후 G_B/epoch2를 시작하고 늦은 G_A result가 G_B handle을 reset하지 않는지 검증한다. 이는 두 번째 action type이 아니라 epoch-isolation regression이다.

## 9. COMPAS XR Executor Validation

- 공식/대표 executor 발견 여부: 검색한 fixed repository, shipped `.ghx`, 공식 문서, `compas-dev` 조직 및 paper artifact 범위에서 재현 가능한 executor를 찾지 못했다.
- Case 판정: **Case C — Framework delegates final robot execution to custom integration**.
- T_A→T_B 결과: 이전 runtime은 서로 다른 digest의 T_A/T_B가 같은 element-derived `trajectory_id`를 갖고 T_B가 official message/MQTT handoff subscriber까지 도달함을 확인했다. 이번 audit에서도 approval binding field는 0개였다. 그러나 actual robot-input test는 **NOT RUN**이다.
- 공식 packaged `Cx_SendTrajectory`는 full message를 subscriber worker에 받지만 downstream outputs는 element ID와 robot name뿐이다. shipped GHX도 이 두 값을 display panel에 연결하고 robot control을 RRC/RTDE/UR Script placeholder로 남긴다.
- 공식 user guide도 COMPAS XR가 complete planning routine을 제공하지 않으며 CAD의 planning/execution에 사용자별 추가 입력이 필요하다고 설명한다. 따라서 framework vulnerability가 아니라 **missing framework guarantee / integration hazard**로 분류한다. [공식 user guide](https://compas.dev/compas_xr/latest/userguide.html), [공식 repository](https://github.com/compas-dev/compas_xr)
- 관련 2024/2025 논문은 project-specific ROS/MoveIt 또는 UR RTDE physical integration을 보고하지만, 검색 가능한 executor source나 exact-binding comparison logic을 제공하지 않는다. [2024 paper](https://doi.org/10.1007/s41693-024-00138-6), [2025 paper](https://doi.org/10.1007/s41693-025-00158-w)

Source trace:

- Message schema/element-derived ID: `frameworks/compas_xr@b86e6fbbacdc8e84183fc08c846176a1c79304ca:src/compas_xr/mqtt/messages.py:459-506`
- Official subscriber/output boundary: `frameworks/compas_xr@b86e6fbbacdc8e84183fc08c846176a1c79304ca:src/compas_xr/ghpython/components/Cx_SendTrajectory/code.py:19-65`
- Packaged output metadata: `frameworks/compas_xr@b86e6fbbacdc8e84183fc08c846176a1c79304ca:src/compas_xr/ghpython/components/Cx_SendTrajectory/metadata.json:28-37`
- Official GHX control placeholder: `frameworks/compas_xr@b86e6fbbacdc8e84183fc08c846176a1c79304ca:docs/examples/scripts/ex2_robotic_trajectory_visualization_example.ghx:23132-23140`

## 10. Confirmed / Unconfirmed / Rejected

### CONFIRMED

- Fixed HORUS official cancel path는 5/5 정상이며 cancel UUID가 accepted Goal UUID와 일치한다.
- Unmodified R1/R2/R3는 각각 5/5 cancel 0이며 10초의 모든 checkpoint에서 accepted Goal이 `EXECUTING`이다.
- R4에서 B는 5/5 새 lease/Goal을 얻었고 A/B distinct Goal은 10초 동안 동시에 active였다.
- Fixed source의 lease release/expiry/disconnect path는 lease state만 제거하며 Nav2 cancel/goal ownership mapping을 호출하지 않는다.
- Test-only latest-handle hook은 nominal path를 멈추지만 같은 robot의 unrelated latest Goal을 5/5 잘못 취소한다.
- Fixed HORUS에는 두 번째 official action adapter가 없다.
- COMPAS XR `SendTrajectory`에 approval digest/version/approver set/authorization epoch가 없고, public official example의 final controller는 custom placeholder다.

### UNCONFIRMED

- 실제 Quest/HORUS Unity app의 focus loss가 release, heartbeat stop, disconnect 또는 explicit cancel 중 무엇을 발생시키는지.
- 실제 Nav2 stack/controller가 두 Goal을 concurrent, preempt, reject 중 어떻게 처리하는지.
- 실제 robot의 이동, stop distance, collision 또는 safety impact.
- Nav2 이외의 Action과 다른 XR–ROS framework에서 같은 lifecycle gap이 재현되는지.
- Production ownership/epoch patch의 pending-goal race, late-result isolation, multi-robot correctness.
- COMPAS project-specific executor가 T_B를 검증 없이 robot input으로 수용하는지.
- 현재 finding의 최종 novelty 또는 최초성.

### REJECTED

- “기존 0.7–1.0초 결과는 단순 asynchronous cancel delay였다”: 5회·10초에서 cancel 0으로 반박됐다.
- “공식 cancel path 자체가 동작하지 않는다”: 5/5 baseline으로 반박됐다.
- “robot-wide/latest-handle cancel 한 줄이 production-safe하다”: wrong-goal cancel 5/5로 반박됐다.
- “공개 COMPAS XR가 inspectable complete robot executor를 제공한다”: 검색한 official artifact 범위에서 반박됐다.
- “이번 결과가 실제 Quest focus attack 또는 COMPAS T_B physical execution을 증명한다”: 증거 범위를 벗어나므로 기각한다.

## 11. Research Interpretation

- Main Item 가능성: 가능하되 범위를 **revocable, owner-bound ROS Action lifecycle**로 좁혀야 한다. HORUS Nav2가 현재 primary runtime case다.
- 일반화 수준: 현재는 HORUS case study에서 관찰된 강한 evidence이며, 여러 XR–ROS framework나 모든 ROS Action의 일반적 취약점으로 일반화할 수 없다.
- 구조적 의미: admission-time lease와 execution-time Action ownership 사이에 연결이 없으면 revocation은 future publish authority만 제거하고 이미 accepted Goal을 회수하지 못한다. 정확한 cancellation에는 origin/owner, live epoch, exact Goal의 binding이 필요하다.
- COMPAS Track: 동일한 “exact action binding” 연구 동기를 보조하지만 final executor가 custom이므로 main exploit evidence가 아니다. `Framework Guarantee Missing / Secondary Evidence Only`로 포함하거나 related case로 분리한다.
- 기존 방어 관계: TLS, MQTT authentication, SROS2 topic permission은 주체/transport admission에 중요하지만, accepted action의 owner/epoch lifecycle을 자동으로 제공한다는 증거는 아니다. 이것은 SROS2 취약점 주장이 아니다.

## 12. Final GO / NO-GO

**CONDITIONAL GO**

근거:

1. Explicit cancel 5/5 정상인데 unmodified release/TTL/disconnect cancel은 각 0/5다.
2. R1–R3가 모든 10초 checkpoint에서 5/5 재현되어 기존 short-window 결과가 강화됐다.
3. R4에서 B가 5/5 수락되고 A/B Goal이 5/5 동시에 active여서 lease handoff와 Action ownership handoff의 분리가 관찰됐다.
4. 단순 latest-handle hook이 nominal case를 멈추면서 unrelated Goal을 5/5 잘못 취소해 precise owner/epoch binding 필요성을 runtime으로 보여줬다.
5. 반면 증거는 HORUS의 한 Nav2 adapter와 synthetic action server에 한정된다.
6. Quest focus lifecycle, 실제 Nav2/robot consequence, 두 번째 Action/framework는 미확인이다.
7. COMPAS는 Case C이며 actual executor consequence가 없어 secondary evidence만 제공한다.

따라서 NO-GO나 WEAK로 내릴 정도로 단순 delay/한 줄 safe fix는 아니지만, STRONG GO로 올릴 cross-action/cross-framework evidence도 아직 없다.

## 13. What We Can Claim

- “고정 HORUS ROS 2 revision의 Nav2 adapter 경로에서 정상 cancel은 동작했지만, lease release·expiry·disconnect는 5회 반복의 10초 관찰 동안 이미 accepted Goal을 cancel하지 않았다.”
- “Lease handoff 후 새 holder의 Goal이 수락됐고, software-only multi-goal action server에서 이전 holder와 새 holder의 Goal이 동시에 active로 관찰됐다.”
- “Robot-wide latest-goal cancel hook은 nominal cleanup을 제공했지만 owner selectivity를 보존하지 못해, precise revocation에는 lease owner/epoch와 Goal UUID의 binding이 필요했다.”
- “공개 COMPAS XR message/handoff boundary는 exact approval proof를 `SendTrajectory`에 포함하지 않으며 final robot execution을 custom integration에 맡긴다.”
- “이 결과는 revocable exact-action authorization을 XR–ROS bridge의 admission과 downstream ROS Action lifecycle 사이에서 검증해야 할 필요성을 뒷받침한다.”

## 14. What We Must Not Claim

- 실제 robot이 1 m 이동했거나 충돌했다고 주장하지 않는다.
- 모든 XR–ROS framework 또는 모든 ROS Action이 취약하다고 주장하지 않는다.
- HORUS가 공식 specification을 위반했다고 주장하지 않는다.
- SROS2 자체의 취약점 또는 우회라고 주장하지 않는다.
- COMPAS XR가 T_B를 실제 robot에서 실행했다고 주장하지 않는다.
- OpenXR focus loss 공격을 완료했다고 주장하지 않는다.
- dummy action server의 concurrent acceptance를 stock Nav2 controller 동작으로 일반화하지 않는다.
- Authorization Continuity, trajectory integrity, runtime revocation 또는 exact-action authorization을 최초 제안했다고 주장하지 않는다.
- Test-only patch를 production defense 또는 최종 ORBIT 설계로 표현하지 않는다.

## 15. Next Recommended Work

1. **Owner/epoch-aware 최소 HORUS prototype**
   - 무엇: `{canonical_robot_id, owner_connection_id, lease_epoch, command_id, goal_uuid}`를 goal lifecycle에 저장하고 release/expiry/disconnect 시 해당 epoch의 pending/active Goal만 cancel한다. cancel acceptance/terminal bounded wait와 late-result isolation을 추가한다.
   - 왜: latest-handle hook의 wrong-goal cancel을 해결해야 구조적 claim과 defense baseline이 성립한다.
   - 판정 변화: 아주 작은 stateless hook으로 race/selectivity/multi-robot까지 모두 통과하면 WEAK로 하향한다. 구조적 state가 필요하고 overhead/compatibility가 합리적이면 CONDITIONAL GO를 유지한다.

2. **Second action 또는 second framework**
   - 무엇: official FollowJointTrajectory/mission adapter가 있는 다른 maintained XR–ROS framework, 또는 HORUS가 향후 제공하는 두 번째 real task adapter에서 같은 R1–R4 matrix를 반복한다.
   - 왜: Nav2 adapter-specific limitation을 벗어나야 일반적 연구 item이 된다.
   - 판정 변화: 유사 결과와 ownership-safe fix 필요성이 재현되면 STRONG GO 후보, 재현되지 않으면 HORUS case study로 축소한다.

3. **실제 Quest/OpenXR lifecycle trace**
   - 무엇: HORUS Unity build에 `OnApplicationFocus(bool)`, `OnApplicationPause(bool)`, lease heartbeat/release/cancel send timestamps를 기록한다. 가능하면 OpenXR `xrPollEvent`의 `XrEventDataSessionStateChanged`에서 `FOCUSED→VISIBLE/STOPPING` 시간을 함께 기록한다. HMD removal, Home/background, app stop을 각각 5회 수행한다.
   - 왜: 현재 R1–R3는 focus-loss proxy이며 actual app behavior가 explicit cancel을 보낼 가능성이 남아 있다.
   - 판정 변화: focus loss마다 bounded cancel이 안정적으로 발생하면 focus-attack claim은 폐기한다. lease loss만 발생하고 Goal이 지속되면 실제 XR relevance가 강화된다.

4. **COMPAS maintainer-linked executor 확보**
   - 무엇: 논문 저자/maintainer가 사용한 GH→ROS/MoveIt 또는 UR RTDE graph와 fixed revision을 확보해 T_A baseline/T_B substitution을 dummy controller 앞에서 재현한다.
   - 왜: Case C에서는 framework handoff만으로 actual execution 결론을 낼 수 없다.
   - 판정 변화: exact digest/version/epoch를 검증하면 COMPAS track을 main item에서 제거한다. 검증 없이 T_B가 faithful executor input에 도달하면 cross-framework evidence가 강화된다.

5. **실제 Nav2 simulation impact와 novelty matrix**
   - 무엇: physical robot 없이 Nav2 simulation의 preemption/rejection/stop distance를 측정하고, revocable capabilities·ROS action authorization·XR consent 관련 work와 claim-by-claim 비교한다.
   - 왜: dummy concurrency를 현실적인 consequence와 publication claim으로 연결하기 전 필요한 gate다.
   - 판정 변화: 실제 Nav2가 항상 안전하게 preempt해 영향이 사라지면 위험 claim을 낮춘다. bounded stop gap이 남고 prior art와 차별화되면 main-item 근거가 강화된다.

## 16. 사용자 이해용 쉬운 설명

1. **기존 실험과 무엇이 달라졌는가?** 1초 정도 한 번 본 것이 아니라, 각 종료 방식마다 5번씩 실행하고 10초 동안 0.5/1/3/5/10초 상태를 기록했다. 새 사용자에게 제어권을 넘기는 상황과 간단한 수정의 정확성도 추가했다.
2. **Lease가 끝난 뒤 Robot Action은 실제로 어떻게 됐는가?** 실제 robot은 없었다. software dummy Action 기준으로 release, timeout, disconnect 뒤에도 Goal은 5번 모두 10초 내내 실행 상태였고 cancel 요청은 한 번도 없었다.
3. **새 사용자의 Action과 충돌했는가?** B의 새 Goal은 5번 모두 받아들여졌고 A/B 두 Goal이 동시에 active였다. 이것은 software-level conflict 가능성이지 실제 충돌 증거는 아니다.
4. **간단한 수정으로 해결되는가?** “권한이 끝나면 robot의 최신 Goal을 cancel”하면 단순한 경우는 멈춘다. 하지만 다른 Goal이 더 늦게 들어오면 그 잘못된 Goal을 취소하고 원래 A Goal은 남았다. 그래서 누가 어떤 lease epoch에서 어떤 Goal을 만들었는지 저장해야 한다.
5. **COMPAS에서는 실제 실행까지 확인했는가?** 아니다. 공식 공개 예제는 메시지를 받은 뒤 실제 controller 연결을 사용자 코드에 맡긴다. 따라서 Case C이고 physical execution은 미확인이다.
6. **이 연구를 논문 Main Item으로 잡아도 되는가?** 현재는 **CONDITIONAL GO**다. HORUS Nav2 evidence는 강하지만 두 번째 Action/framework와 실제 XR/robot relevance가 더 필요하다.
7. **사용자가 다음에 해야 할 것은 무엇인가?** 우선 owner/lease epoch/Goal UUID를 연결한 최소 prototype과 actual Quest focus trace를 수행한다. 동시에 공식 COMPAS executor artifact를 maintainer에게 확보한다.

## 17. Files and Evidence Links

- [Follow-up Results](/home/cclab/ros_xr/DECISIVE_FOLLOWUP_RESULTS.md)
- [Evidence Summary](/home/cclab/ros_xr/evidence/decisive_followup_summary.md)
- [HORUS Long-run Log](/home/cclab/ros_xr/evidence/horus_revocation_longrun.log)
- [HORUS Handoff/Fix Log](/home/cclab/ros_xr/evidence/horus_action_handoff.log)
- [COMPAS Validation Log](/home/cclab/ros_xr/evidence/compas_executor_validation.log)
- [Reproduction Script](/home/cclab/ros_xr/authorization_env/run_decisive_followup.sh)
- [HORUS Long Action Probe](/home/cclab/ros_xr/authorization_env/horus_long_action_probe.py)
- [COMPAS Executor Probe](/home/cclab/ros_xr/authorization_env/compas_executor_probe.py)
- [Test-only Patch](/home/cclab/ros_xr/authorization_env/horus_revocation_cancel_test.patch)
- [Research Context](/home/cclab/ros_xr/RESEARCH_CONTEXT.md)
- [Previous Authorization Continuity Report](/home/cclab/ros_xr/AUTHORIZATION_CONTINUITY_RESULTS.md)
