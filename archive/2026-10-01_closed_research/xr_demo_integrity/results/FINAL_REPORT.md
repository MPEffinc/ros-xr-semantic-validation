# Final Report — Integrity of XR-Teleoperation Demonstrations for Robot Learning

Date: 2026-09-30. Repository base `a619e23d2`; workspace commits `970e9261` (init), `ee281ee3` (literature),
`679634a3` (system audit), `3e6a9fc8` (threat model), and this commit (verdict).

## 1. Executive Summary

**Verdict: NO_REAL_THREAT_BOUNDARY** for the candidate as posed (a limited-authority component changing
the meaning of XR-teleoperation demonstrations). The issues that were found are **DATA_QUALITY** issues at
source level. No framework is developed; PHASE 4–7 were not run because the PHASE 3 gate was not met.

- The public NVIDIA XR → demonstration paths (IsaacTeleop → LeRobot SO-101; IsaacTeleop → Isaac Lab HDF5)
  **do not use ROS**. Isaac ROS Teleop publishes XR poses to ROS 2 but has no recorder or dataset path.
- The only public implementation joining XR (phone WebXR), ROS 2 and a learning dataset is
  `roahmlab/tidybot_ros`. Its recorder is a separate ROS 2 node, but the graph has no SROS2, so every
  participant has full authority (unauthenticated, a known generic class).
- The only real *limited* writer on XR paths is the XR input provider. What it writes is executed by the
  robot and recorded together with the measured result, so it yields a genuine demonstration of chosen
  behaviour — the published "data provider" poisoning model, not a recording-integrity violation.
- Demonstration poisoning with small dataset edits is well-established prior art (SilentDrift, DropVLA,
  !Imperio, State Backdoor, 2609.26868 on teleoperation demonstrations). All of these assume dataset write
  access; none needs XR or ROS.
- Evidence is literature (FULL text) and pinned source code. **No experiment was run**, so there is no
  EXPERIMENT_CONFIRMED result in this workspace.

## 2. Systems reviewed and pinned revisions

| System | Revision |
|---|---|
| NVIDIA-ISAAC-ROS/isaac_ros_teleop | `e80602863a0c4c94360a22b02248164c2dad6fa4`; IsaacTeleop gitlink `de761a036a0e7188409c0741de861fe691c7b739` |
| NVIDIA/IsaacTeleop | `47f33af3cc50d01bc3d60f51d17ef0a480fa0969` |
| isaac-sim/IsaacLab | `5eef1d70f3c7f3af1e1c99eae85192b61cda52ac` |
| huggingface/lerobot | `e0d50211ef236143ae867228662b7dfaba554f02` |
| XR-Robotics/XRoboToolkit-Teleop-Sample-Python | `79e5cb8a56e3455515ce1b476e993c764ec58739` |
| roahmlab/tidybot_ros | `e32cb459514abe556a9a9a954d9131d0bb50c210` |
| 16 further ROS/XR recorder repos | `../systems/SYSTEM_INVENTORY.md` §3 |

Re-create with `../scripts/fetch_upstreams.sh`. Nothing was built or executed.

## 3. Verified key papers and citation relations

All 10 listed items resolve with matching titles (`../literature/SOURCE_LEDGER.md` §A). BadVLA is confirmed
as a NeurIPS 2025 poster; 2609.26868 is an IROS 2026 workshop paper; XRoboToolkit is accepted at SII 2026;
the rest are arXiv preprints. The security papers and the XR-teleop/simulation papers form two disconnected
citation clusters. No security paper in the set cites an XR teleop system, and no teleop paper cites a
security paper (`../literature/CITATION_GRAPH.md`).

## 4. Author-stated limitations (relevant excerpts; `../literature/LIMITATION_MATRIX.md`)

- **2609.26868 §V.** Their defense misses in-task and multimodal triggers; they suggest "cross-modal consistency checks".
- **State Backdoor §VIII.** Future work is detection/certification, plus signatures for **model** provenance (watermark), not for datasets.
- **SoK Limitation 4 / OP7.** Provenance records are missing, and an end-to-end evidence mechanism "remains an open problem".
- **2608.16843 §5.6, §10.2–10.3.** They call for state provenance, sensor-to-state consistency and cross-modal checks.
- **XRoboToolkit, Isaac Lab and XRoboToolKit-T.** None states any limitation about demonstration integrity or provenance.

## 5. Actual data-collection paths (`../systems/DATAFLOW.md`)

**P1 LeRobot (single process, no ROS).** XR controller → constant anchor transform → clutch → EE bounds → IK → `send_action`.
- The stored `action` is the target before clipping. The `send_action` return value is discarded (`record.py:160`).
- `observation.state` is read before the action is computed.
- Timestamps are synthetic: `frame_index/fps` (`dataset_writer.py:224`).

**P2 Isaac Lab (single Kit process, no ROS).** The recorder stores `actions`, `processed_actions` and `states` separately.
- Paused steps are not recorded, and no gap marker is written.
- Only succeeded episodes are exported.
- A state-replay check exists (absolute tolerance 0.01).

**P4 tidybot_ros (ROS 2).**
- A separate recorder node samples, at a 10 Hz timer, the latest commanded targets, TF poses and images.
- The recorded action topic is the same topic the IK solver consumes.
- Start, stop and finalize are open ROS services.
- The phone endpoint `0.0.0.0:5000` has no authentication.

**P3 XRoboToolkit.** In-process pickle logging; Galaxea uses ROS 1 topics.

## 6. Real attacker authority (`../systems/TRUST_BOUNDARIES.md`, `../hypotheses/THREAT_MODEL.md`)

| Candidate attacker | Real in code? | Class |
|---|---|---|
| XR input / tracking provider | yes (CloudXR client, WebXR replay, phone SocketIO) | LIMITED; its dataset influence equals its robot influence |
| retargeting component | in-process only | NONE (no boundary) |
| specific ROS message publisher | ROS 2 graph without SROS2; ROS 1 | UNAUTH (full graph authority) |
| recorder-field writer | none | — |
| limited dataset writer | only whole-file / Hub writers | FULL_WRITE (excluded; equals published poisoning model) |

## 7. Normal data meaning and changeable points

- **P1.** `action[t]` = the joint target decided at step *t*; the executed result appears in `observation.state[t+1]`.
- **P2.** `actions` = the controller command; `states` = the simulator state after the step.
- **P4.** `action` = the commanded target; observations = the latest poses and images.

A lag between command and state, clipping, and commanded-action labels are intended behaviour, not attacks.

The only place found where a narrowly authorised writer *might* change a recorded field without changing control is P4's TF-derived observations. That applies only under a hypothetical SROS2 deployment, because ROS 2 permissions are per topic, not per frame. It is not XR-related, and a consistency check against `/joint_states` closes it (THREAT_MODEL §4).

## 8. Comparison with existing defenses

- **Schema and count checks.** LeRobot (`validate_frame`, `validate_episode_buffer`) and tidybot (equal counts) detect structural damage only.
- **Timestamp checks.** LeRobot `check_delta_timestamps` and the video-PTS tolerance, and RDA's checks, test only whether the declared timestamps are consistent with each other.
- **Replay.** Isaac Lab `replay_demos` and robomimic/robosuite playback compare states, but the docs acknowledge drift and non-determinism.
- **Curation.** CUPID, DemInf, Demo-SCORE, DataMIL and DMDR are evaluated on benign defects only.
- **Provenance.** Only the MCAP/rosbag2 CRC, the Hub git revision and the Black Block Recorder (abstract only) exist.

For the data-quality items found, the missing pieces are ordinary metadata: validity, clutch and pause flags; measured per-stream timestamps; the post-clip sent action; raw-input logs (IsaacTeleop MCAP already exists); config and version capture; and hash manifests. None of these requires a new method.

## 9. Minimal experiment results

**NOT_RUN.** The PHASE 3 gate was not met (`../hypotheses/GO_NO_GO.md`), and no protocol was frozen (`../experiments/PROTOCOL.md`). Two resource limits also apply:
- Isaac Sim cannot run on the GTX 1050 Ti.
- No SO-101, ARX, Galaxea or XR headset is available.

No inference or simulation has been substituted for these results.

## 10. Learning-impact verification

**NOT_RUN.** Its precondition was a residual change that survives B2, and no such change can arise without a limited boundary. Learning impact of dataset-level poisoning is established by prior art and was not re-tested. No claim about robot behaviour is made.

## 11. Difference from S5 / XR2Act / Authority Continuity

| Closed study | What it covered | Overlap here |
|---|---|---|
| S5 (NO_METHOD_GAP) | command-time validity, freshness, silence, generation/re-arm, binding and monitor fail-closed | The XR-specific items found here (tracking validity D4, pause/hold D3) are the same signals, now at recording time; S5 methods already cover them |
| XR2Act (WEAK / CASE-STUDY ONLY) | unauthenticated bridges and principal collapse (Quest2ROS2, rosbridge, HORUS) | tidybot's SocketIO endpoint and SROS2-less graph are the same UNAUTH class |
| Authority Continuity (IMPLEMENTATION_GAP_ONLY) | lease/handoff lifecycle, stale holders | recorder lifecycle services are open (UNAUTH); no lifecycle-specific finding |

What is new in this study is the demonstration-recording layer, which "Demonstration Poisoning" had excluded from the earlier scope (`../../Deprecated/RESEARCH_CONTEXT.md` §16). It adds no new security result.

## 12. XR necessity and ROS necessity

- **XR is not necessary.** Recorders store post-retargeting commands and robot state. The same code serves leader-arm, joint-teleop and policy-generated commands. XR-specific items are data-quality signals (RQ4, H1 rejected at source level).
- **ROS is not necessary.** The NVIDIA XR→dataset paths use no ROS. In P4, ROS adds only a generic unauthenticated graph. The one ROS-specific candidate (TF granularity) is hypothetical and not XR-related.

## 13. Research-gap verdict

**NO_REAL_THREAT_BOUNDARY.** Residual issues observed are DATA_QUALITY (source level, not experiment-confirmed). The ten PHASE 8 questions:

1. **Reproduced in a real public XR–ROS system?** No experiment was run. At source level, no public system is a connected XR–ROS recording path with a limited boundary.
2. **Only real limited authority used?** The only real limited writer (the XR input provider) cannot change the recorded meaning.
3. **Intended meaning damaged?** Not by a limited writer.
4. **Solved by existing validation?** The data-quality items are fixable with standard metadata and checks. Full-write poisoning is prior art.
5. **Is XR essential?** No.
6. **Is ROS essential?** No.
7. **Does the attack or defense already exist?** Poisoning: yes (C1 HIGH collision). Curation, timestamp checks and provenance: yes, for benign or generic cases.
8. **One bug or a general problem?** Implementation- and definition-level quality issues that differ per recorder (D1–D7).
9. **Learning impact confirmed?** Not tested.
10. **New method needed?** No evidence.

Not REPRODUCED_RESEARCH_GAP or OPEN_RESEARCH_HYPOTHESIS: none of the required conditions (reproduction, residual after correctly applied defenses, XR+ROS relevance, novelty) holds. Not INCONCLUSIVE_RESOURCE_LIMITATION as the overall verdict: the resource limits affect only H3 (Isaac Lab Mimic amplification) and would not change the boundary finding.

## 14. New framework development

None. Motivating example, Need, RQ, Approach, Contribution, NABC and a main experiment plan are **not** written, because the gate condition (a confirmed gap) is not met.

## 15. Next directions or reasons to stop

**Stop the candidate as an XR+ROS security item.** Possible non-research follow-ups (not performed; the user decides):
- Upstream issues on the data-definition inconsistencies:
  - LeRobot `lerobot_record.py:359-361`: the comment and the code disagree about which action is saved.
  - LeRobot's stale `tolerance_s` docstring.
  - The example ignores `GRIP_IS_VALID`.
  - Isaac Lab Mimic's docstring lists `src_demo_inds` but they are not exported.
  - Isaac Lab drops paused steps without a marker.
- A data-quality (non-security) study of XR-collected datasets, if that is of interest.
- An evaluation of existing curation methods against published poisoning attacks. The literature flags this as unaddressed (LIMITATION_MATRIX C2), but it is a generic robot-learning security question, not XR+ROS.

---

### 본 연구 후보에서 실제로 새롭게 확인한 사실은 무엇인가?

모두 고정 SHA의 소스 수준 사실(SOURCE_CONFIRMED)이며, 실험으로 확인한 것은 없다.

1. NVIDIA가 공개한 XR→시연 데이터셋 경로(LeRobot, Isaac Lab)는 ROS를 사용하지 않는다.
2. Isaac ROS Teleop에는 recorder가 없다.
3. XR, ROS 2, 학습 데이터셋을 하나로 연결하는 공개 구현은 tidybot_ros뿐이다.
   - 그 ROS 2 graph에는 SROS2가 없어 모든 참여자가 동등한 권한을 가진다.
4. XR 입력 제공자는 실제로 존재하는 유일한 제한 권한이지만, 데이터셋에 미치는 영향이 로봇에 미치는 영향과 같다.
5. 각 recorder에는 데이터 정의·품질 결함(D1–D7)이 있다.
   - LeRobot: 저장되는 label이 clip 이전 값이다.
   - LeRobot: timestamp가 합성값이다.
   - Isaac Lab: pause 구간이 표시 없이 누락된다.
   - Isaac Lab Mimic: 원본 시연과의 연결이 남지 않는다.

### 이미 알려진 공격 및 기존 검증으로 해결되는 부분은 무엇인가?

- 데이터셋에 쓰기 권한이 있는 공격자가 시연 일부를 수정해 백도어를 심는 공격은 이미 발표되었다. SilentDrift, DropVLA, !Imperio, State Backdoor, 2609.26868이 해당한다.
- 인증이 없는 bridge나 endpoint 문제는 기존 내부 연구(XR2Act)에서 다룬 것과 같은 종류다.
- XR tracking의 유효성, freshness, 재시작 문제는 S5에서 확인한 기존 방법으로 해결된다.
- 발견한 데이터 품질 결함은 표준적인 방법으로 해결할 수 있다.
  - 유효성, pause, clutch 플래그 기록
  - 측정 timestamp 저장
  - 실제 전송된 action 저장
  - 원본 입력 로그(MCAP) 보존
  - 해시 manifest 작성

### 새로운 방법론이 필요하다는 근거가 실제로 존재하는가?

없다. 기존 방어가 실패하는 잔여 사례를 관찰하지 못했다. 그런 사례를 만들 수 있는 제한 권한 경계도 실제 구현에서 찾지 못했다.

### 이 결과가 XR+ROS Security/Safety 논문으로 발전할 수 있는가?

현재 증거로는 불가능하다.

- XR과 ROS가 모두 필수 조건이 아니다.
- 공격 모델은 이미 발표된 데이터 poisoning으로 환원된다.
- 실험 결과가 없다.

가능한 산출물은 upstream 이슈 보고와 비보안 데이터 품질 노트 정도다. 보안 논문으로 이어지려면 두 가지가 모두 필요하다.

- 실제 배포에서 사용되는 제한 권한 경계를 새로 찾는다. 예를 들어 SROS2가 실제로 적용된 XR 수집 시스템이 있다.
- 그 경계에서 기존 검증(B2)을 통과하는 의미 변경을 실험으로 보인다.
