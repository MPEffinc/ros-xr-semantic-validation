# Spes Quest 3 Hardware Result

## 현재 상태

**COMPLETE — ACTUAL QUEST 3 T0 PASS; T1 `HW_EMULATED_CONTINUES` 5/5**

이 문서는 실제 Quest 3 trial 결과를 기록할 canonical 파일이다. Run `spes_quest_hw_20260831T001349Z`에서 T0가 통과했고 5회의 valid T1 모두 controller pose가 non-null인 채 `emulatedPosition=true`로 전환됐다. 모든 valid critical window에서 `move=true`, selected source `CONTROLLER`, control packet 증가, Spes server update/target callback 증가가 함께 관측됐다. 따라서 primary H1은 이 Quest 3/Spes revision에서 **5/5 hardware-confirmed**다. Controller-null/viewer fallback은 발생하지 않아 H2는 `NOT OBSERVED`다.

## 고정 대상과 계측 경계

| 항목 | 값 |
| --- | --- |
| Spes target | `SpesRobotics/teleop@c5d808155a87b584d6147a5943d4b87c34c92db0` |
| Upstream checkout | clean, patch 없음 |
| Instrumented frontend | `semantic_validation/instrumented/spes_frontend` |
| Frontend log | semantic transition 즉시 + 200 ms sample; operator raw event는 별도 `/experiment` WSS |
| Control packet | upstream `type:"pose"` payload 유지 |
| Server observation | actual `Teleop.__update()` 전후 wrapper + subscriber callback + observation ACK |
| Operator | DOM overlay runtime check, 2.5 m stereo world-space WebGL HUD fallback, speech synthesis 또는 Web Audio, left select-only state machine |
| Terminal marker | hardware mode에서는 사용하지 않음 |
| Robot | 연결하지 않음 |
| ROS sink | 준비됨, 현재 Docker daemon permission으로 NOT RUN |

Frontend preflight는 `emulatedPosition=true` controller와 controller-null fallback에서 instrumented/upstream control packet의 구조적 동등성을 확인했다. Server preflight는 actual update method의 callback/jump/anchor 관찰과 실제 WSS pose→side-band order correlation을 확인했다. 이는 instrumentation 검증이지 Quest hardware 결과가 아니다.

사후 독립 differential은 frontend 7개 case의 raw serialized pose bytes/send condition과 server wrapper 12개 case의 callback/private state/exception parity를 확인해 `INSTRUMENTATION_NON_INTERFERENCE_PASS`를 기록했다. 이 결과는 tested instrumentation-artifact 대안을 약화하지만 모든 browser scheduling/overhead를 증명하지 않는다.

Preflight/raw evidence:

- `semantic_validation/logs/spes_hardware_preflight.jsonl`
- `semantic_validation/logs/quest_hw/spes_quest_hw_20260831T001349Z/preflight.jsonl`
- `semantic_validation/logs/quest_hw/spes_quest_hw_20260831T001349Z/live_probe.json`
- `semantic_validation/logs/quest_hw/spes_quest_hw_20260831T001349Z/live_lan_probe.json`
- `semantic_validation/logs/quest_hw/spes_quest_hw_20260831T001349Z/experiment.jsonl`
- `semantic_validation/logs/quest_hw/spes_quest_hw_20260831T001349Z/server.jsonl`
- `semantic_validation/logs/quest_hw/spes_quest_hw_20260831T001349Z/analysis.json`
- `semantic_validation/results/SPES_HW_REANALYSIS.md`
- `semantic_validation/results/SPES_CLASSIFIER_REGRESSION.md`

## Evidence strata

| 구분 | 현재 결과 | hardware finding에 사용 가능 여부 |
| --- | --- | --- |
| Actual Quest 3 | T0 PASS; valid T1 5/5 `HW_EMULATED_CONTINUES`; H3 no-rearm recovery 5/5 | H1/H3에 사용 |
| Synthetic frontend paths | emulated controller / controller-null fallback payload equivalence `PASS` | instrumentation 검증에만 사용 |
| Local HTTPS/WSS preflight | HTTPS, production WSS, experiment WSS, ACK `PASS` | live endpoint 준비 증거에만 사용 |

## Excluded operator diagnostic session

Run `spes_quest_hw_20260830T230327Z`에서 actual Quest 접속과 WebXR frame/control packet은 관측됐지만, `domOverlayState=UNAVAILABLE`, `speechSynthesis=false`로 안내가 보이지 않았고 state machine은 `MOVE_BUTTON_CHECK`에 머물렀다. Left select event는 정상 수신됐으나 `move=false`였으며 valid T0/T1은 시작되지 않았다. 이 session은 `INVALID_OPERATOR_GUIDANCE` diagnostic으로 보존하고 H1/H2/H3 hardware trial count와 finding에서 제외한다.

Diagnostic evidence: `semantic_validation/logs/quest_hw/spes_quest_hw_20260830T230327Z/experiment.jsonl` 및 같은 directory의 `server.jsonl`.

Run `spes_quest_hw_20260830T232948Z`에서는 WebGL HUD renderer가 ready였고 state machine상 T0가 완료됐지만, 사용자가 HUD text를 해석할 수 없다고 보고했으며 T1에서 long-press manual abort가 두 번 발생했다. Experimental integrity를 위해 이 session 전체를 `INVALID_OPERATOR_READABILITY`로 제외한다.

Run `spes_quest_hw_20260831T000620Z`에서는 단순화한 clip-space HUD가 표시됐지만 사용자가 글씨가 너무 크고 가까워 읽을 수 없다고 보고했다. 이 session 전체를 `INVALID_OPERATOR_READABILITY`로 제외하며 실제 T0/T1 finding에 사용하지 않는다. 서버 교체 직후 이전 browser page가 새 run에 자동 reconnect한 frame은 fresh page load의 `operator_preflight`/`xr_session_start` 이전 carryover이므로 `INVALID_STALE_CLIENT_CARRYOVER`로 제외한다.

## Hardware run metadata

| 항목 | 값 |
| --- | --- |
| Run ID | `spes_quest_hw_20260831T001349Z` |
| Quest/browser/runtime version | `NOT RECORDED` |
| Quest URL | `https://192.168.0.3:4443/?run=001349` — cache-busted page, host-side verified |
| Production connection | generation `4`; prior production client last update `00:16:22.813900Z`, generation 4 connected `00:16:38.564367Z`; overlap 없음 |
| Trial interval | fresh operator preflight `00:16:41.033Z` → experiment complete `00:19:15.194Z` |
| Detached server | `spes_quest_hw.service`, preparation PID `450396` |
| Server log | `semantic_validation/logs/quest_hw/spes_quest_hw_20260831T001349Z/server.jsonl` |
| Experiment raw log | `semantic_validation/logs/quest_hw/spes_quest_hw_20260831T001349Z/experiment.jsonl` |
| Derived analysis | `semantic_validation/logs/quest_hw/spes_quest_hw_20260831T001349Z/analysis.json` |
| stdout/stderr | same run directory의 `server.stdout.log`, `server.stderr.log` |
| ROS sink log | `NOT RUN` |
| rosbag2 | `NOT RUN` |
| Quest trial state | T0 PASS, T1 valid 5, T1 invalid 1, T4 no disconnect observed, FINAL reached |

Fresh generation의 sampled semantic event 788개에서 `server_update_index - control_packet_index = 11942`가 모두 동일했다. 절대 index 불일치는 server가 이전 진단 traffic 이후 재사용됐기 때문이며, valid session 내부에서는 두 index가 일정 offset으로 함께 진행했다. 이전 production client와 generation 4의 시간 중첩은 없다.

## Trial별 raw observation

| Trial | Loss behavior | Pose | Emulated | Source | Move | Server continues | Recovery | Classification |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| T0 | normal baseline | non-null | false observed | CONTROLLER | true | packet/server 각각 +447 | N/A | PASS |
| T1-1 | EMULATED_TRACKING_LOSS | non-null | true | CONTROLLER | true throughout | packet/server +403/+403; callback 404/404 | continuous, no re-arm | HW_EMULATED_CONTINUES |
| T1-2 | EMULATED_TRACKING_LOSS | non-null | true | CONTROLLER | true throughout | packet/server +359/+359; callback 356/360 | 4 rejects, 2 reset/create, auto resume | HW_EMULATED_CONTINUES |
| T1-3 | EMULATED_TRACKING_LOSS | non-null | true | CONTROLLER | true throughout | packet/server +360/+361; callback 358/362 | 4 rejects, 1 reset/create, auto resume | HW_EMULATED_CONTINUES |
| T1-4 | EMULATED_TRACKING_LOSS | non-null | true | CONTROLLER | true throughout | packet/server +358/+357; callback 353/358 | 5 rejects, 2 reset/create, auto resume | HW_EMULATED_CONTINUES |
| T1-5 | EMULATED_TRACKING_LOSS | non-null | true | CONTROLLER | true throughout | packet/server +359/+360; callback 356/361 | 5 rejects, 2 reset/create, auto resume | HW_EMULATED_CONTINUES |
| T4 | right input never disappeared | non-null | false→true | CONTROLLER | false→true | 진행했으나 disconnect 없음 | disconnect recovery N/A | HW_T4_NO_DISCONNECT_OBSERVED |

T0 전 `INVALID_MANUAL_ABORT` 3회와 T1 중 `INVALID_MOVE_RELEASED` 1회는 valid count에서 제외됐다. `INVALID_SESSION_FOCUS`는 없었다. T1 표의 4번은 move-release invalid attempt를 반복한 뒤 얻은 valid trial이다.

hardware run 당시 자동 logger는 T1-1에도 working label `RECOVERY_JUMP_REJECT_THEN_REANCHOR`를 부여했지만, 해당 trial-scope jump 1회는 loss 이전 `HOLD_MOVE`에서 발생했다. Loss→reacquisition raw server window에는 reject/reset/create가 0회이고 callback 178/178이므로 canonical recovery 판정은 `RECOVERY_CONTINUOUS`다. 이후 classifier를 loss-detection counter boundary로 수정했고, actual raw regression에서 T1-1 `RECOVERY_CONTINUOUS`, T1-2~5 `RECOVERY_JUMP_REJECT_THEN_REANCHOR`, invalid-attempt/session-generation exclusion이 모두 PASS했다. 독립 재분석은 주요 field 129개 mismatch 0으로 `INDEPENDENT_REANALYSIS_PASS`였다. T1-2~5는 loss/reacquisition window 안에서 `pose_jump_warning`, `relative_anchor_reset`, 다음 accepted update의 `relative_anchor_created`, 이후 callback 진행이 실제 순서로 관측됐다.

## H1-A Tracking semantic loss

**CONFIRMED — 5/5 VALID QUEST 3 TRIALS (`HW_EMULATED_CONTINUES`)**

각 trial의 동일 critical interval에서 `controllerPose != null`, `emulatedPosition=true`, selected source `CONTROLLER`, `move=true`가 관측됐다. Production payload에는 tracking validity/source field가 없었고 control packet과 server update가 계속 증가했으며 server target callback도 계속됐다. Trials 2–5에는 각각 4/4/5/5개의 일시적인 geometric jump reject가 있었지만 callback은 자동 재개되어 fail-close하지 않았다.

## H1-B Recovery behavior

**CONFIRMED — AUTOMATIC ACTIONABILITY WITHOUT USER RE-ARM 5/5**

모든 valid trial에서 critical window의 `move_ever_false=false`였고 recovery 후 packet/update/callback이 사용자 release/re-press 없이 진행했다. Raw recovery는 T1-1 `RECOVERY_CONTINUOUS`, T1-2~5 `RECOVERY_JUMP_REJECT_THEN_REANCHOR`다. 후자의 reject frame은 callback이 일시적으로 false였지만 relative anchor가 자동 reset/create되고 다음 accepted callback이 재개됐다.

## H1-C Viewer substitution

**NOT OBSERVED ON HARDWARE — SYNTHETIC PATH ONLY**

5 valid T1과 optional T4에서 controller pose는 null이 되지 않았다. 따라서 S1의 viewer-fallback implementation path는 유지되지만 H2 hardware confirmation 또는 rejection으로 해석하지 않는다.

## H1-D Disconnect semantics

**NO DISCONNECT OBSERVED**

T4는 별도로 실행됐지만 10초 window 동안 right input source가 사라지지 않아 `HW_T4_NO_DISCONNECT_OBSERVED`로 종료됐다. 후반에 `emulatedPosition=true`는 나타났지만 disconnect와 합치지 않는다.

## Research decision

**HARDWARE-CONFIRMED FOR QUEST 3 EMULATED-POSITION PATH — H1/H3 5/5; H2 NOT OBSERVED**

확정 범위는 이 Quest 3, browser session, Spes fixed revision, instrumented server target callback까지다. “모든 tracking loss”, controller-null fallback, disconnect, ROS/robot/actuator consequence로 일반화하지 않는다.

## Scope exclusions

This run does not include network fault injection, `tc netem`, reconnect composition, PickNik/Quest2ROS2 hardware tests, eBPF, defenses, ROS sink, or any physical robot connection. Quest browser/runtime version was not recorded, and this is one hardware session with five repeated valid trials rather than independent-device replication.
