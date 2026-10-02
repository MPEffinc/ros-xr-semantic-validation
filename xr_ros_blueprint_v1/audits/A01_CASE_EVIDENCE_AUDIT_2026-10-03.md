# A01 — Evidence audit of the 40 cases (2026-10-03)

**Scope.** Each case in `data/blueprint.json` was compared with the internal documents and code
it cites, under `semantic_evidence_framework/` (audits A1–A6, R0, P1/P1b, P2, F1–F3, docs 03–07)
and the pinned upstream sources. **No experiment was run** in this audit. Literature was checked
only where a case's judgment depends on it; that work is in A02/A03.

## Columns

| Column | Meaning |
|---|---|
| `protection` | **SPECIFIC**: a measurable policy with thresholds exists in a frozen internal protocol. **PARTIAL**: the protected condition is named, but the policy choice or threshold is open. **GENERIC**: only a goal sentence. |
| `attacker/fault` | **YES**: the scenario says who causes it, and the fault baseline (S0) is kept separate. **PARTIAL**: actors are listed but the scenario mixes them, or a listed actor has no mechanism. |
| `basis` | The kind of evidence behind the current judgment: paper, code, prior trace, surrogate, real app, physical robot. |
| `verified` / `pending` | What has already been executed or read, and what is still to be checked. |
| `issues` | Duplicates, insufficient evidence, overclaims found in this audit. |

## Summary

- protection: {'PARTIAL': 24, 'SPECIFIC': 4, 'GENERIC': 12}
- attacker/fault split: {'PARTIAL': 28, 'YES': 12}
- judgments (unchanged by this audit): {'KNOWN_METHOD': 14, 'CANDIDATE': 12, 'IMPLEMENTATION_GAP': 3, 'UNKNOWN': 11}

**Corrections made in the DB, from source data:**

| Case | Correction |
|---|---|
| **M3** | The residual range was "33–45 mm". The P1/P1b data give **27.9–42.4 mm** (medians 32.8–40.4 mm). |
| **M4** | "Solved" is now limited to the **command level**; the physical consequence was masked by the Servo singularity stop. |
| **M6** | Added the P1 rotation-criterion confound; the claims are position-level only. |

**New sources and limitations:** sources L37–L41 and limitations U44–U48 (JTC/Servo code facts,
the Safe-ROS automatic resume, the singularity masking, the WebXR follow-up lead, the Nav2 stale-tf
issue).

**Overclaims and expressibility-only judgments**, kept as `KNOWN_METHOD` but flagged:

| Case | Status |
|---|---|
| M11 | expressible; not executed |
| M19 | the method is known; not deployment-verified |
| M5 | the strongest fix was never executed on a real app |
| M1 | the S2 entry is moot: a compromised app forges the tracked field itself |

**Overlaps.** These are recorded as relations; no case is deleted:

| Relation | Kind |
|---|---|
| M2 is an instance of M12 | fresh stamp on stale content |
| M20 and M40 | share the F2 evidence-delay data |
| M33 and M12 | evidence availability |
| M39 | an umbrella over M3–M6. It must not be counted as an independent finding. |
| M17 / M18 / M19 | the same I05 requirement set |

**Insufficient evidence, kept as UNKNOWN or CANDIDATE:** M22, M24, M26–M29, M31, M32, M37 and M38
have no execution and no implementation trace in this repository. M22 has no target-selection
implementation among the audited apps.

## Per-case table

| ID | Title | Judgment | Protection | Attacker/fault | Basis | Verified | Pending | Issues |
|---|---|---|---|---|---|---|---|---|
| M1 | 추적되지 않는 pose의 로봇 구동 | KNOWN_METHOD | PARTIAL | PARTIAL | PRIOR_INTERNAL(S5)+CODE(A1-A6) | S5 synthetic: tracked gate works when field delivered; 6 wires lack tracked (SOURCE) | real runtime occlusion; S2 entry is moot for app-reported flags | S2 listed but a compromised app can forge the tracked field itself; tracking check is an S0/S3 defense only |
| M2 | focus 상실 중 fresh-stamped 고정 pose | CANDIDATE | PARTIAL | YES | PRIOR_TRACE(R0)+CODE(A3)+REAL_APP(F3) | R0: 5 unfocused intervals with fresh-stamped frozen 60 Hz stream (prior data, new analysis); F3: real UR5e app stops itself | a runnable app that keeps streaming while unfocused | instance of M12 (fresh stamp on stale content) for the focus cause; keep as linked, not independent count |
| M3 | grip 해제 뒤 잔여 이동 | KNOWN_METHOD | SPECIFIC | PARTIAL | SYNTHETIC_GAZEBO(P1/P1b)+CODE(Servo 2.12.4, JTC 4.42.1) | P1/P1b: 27.9-42.4 mm residual (medians 32.8-40.4) with Servo-level stop; controller hold 1.0 mm (3/3) | pose/speed/load dependence; deceleration-to-hold option; real robot | findings text "33-45 mm" does not match P1/P1b data (27.9-42.4 mm); S3 role unclear (who induces release) |
| M4 | 비활성 중 해제된 deadman의 눌림 캐시 | KNOWN_METHOD | SPECIFIC | PARTIAL | SYNTHETIC(P1)+RUNTIME(F1 K6 Monado)+CODE(ALVR) | command level: stale-grip resume reproduced; cause-aware re-arm passes C2+C3 (P1); edge rule confirmed on Monado (K6) | physical consequence (masked by Servo singularity stop in P1 C2 and P1b C2M); ALVR/Quest/SteamVR real chain | "solved" holds at command level only; physical not interpretable; Quest premise NOT_VERIFIED |
| M5 | 오래된 anchor로 재개 | KNOWN_METHOD | PARTIAL | PARTIAL | PRIOR_INTERNAL(S5 #10)+REAL_APP(F3)+CODE | F3: 35 mm command-target jump at resume in 6/6 trials; S5 classified APPLICATION | strongest fix (re-anchor to current EE + fresh press) never executed on a real app; physical effect masked (F3 singularity) | "KNOWN_METHOD" is by design argument; execution of the fix absent |
| M6 | recenter의 효력 구간 혼합 | KNOWN_METHOD | SPECIFIC | YES | SYNTHETIC_GAZEBO(P1)+CODE(ALVR) | P1: B0 180/15 mm; epoch gate 0 mm (1 leaked command in 1/3); app retrofit 0 mm; jump guard misses 3 cm | real headset recenter; orientation outcomes (P1 angle criterion confounded by unsettled orientation) | findings omit the P1 angle-criterion confound; position results only |
| M7 | 오래된 입력과 latest tf 사용 | KNOWN_METHOD | PARTIAL | PARTIAL | CODE(Servo servo.cpp L565 Time(0)) | tf2 stamped lookup exists; Servo uses latest | effect size on any path; nav2 #6320 open (stale tf detection not standard) | S1 (network) listed without mechanism |
| M8 | 왼손 topic에 오른손 메시지 내용 | IMPLEMENTATION_GAP | PARTIAL | PARTIAL | PRIOR_TRACE(R0)+CODE(A3) | 54% left msgs with right frame (real Quest data, prior) | root fix untested; frame-consistent swap undetectable | none beyond U37 |
| M9 | controller 부재 시 head pose 대체 | IMPLEMENTATION_GAP | GENERIC | PARTIAL | CODE(A4 Spes) | source-confirmed fallback | runtime/physical effect | none |
| M10 | 양팔 rate / override fan-out | IMPLEMENTATION_GAP | GENERIC | PARTIAL | CODE(A6 OpenArmX) | source-confirmed fan-out | runtime effect | S4/S5 listed without scenario |
| M11 | latched override의 deadman 우회 | KNOWN_METHOD | PARTIAL | PARTIAL | CODE(A6) | TRANSIENT_LOCAL override source-confirmed | policy for scripted motion not declared; no run | KNOWN_METHOD by expressibility only |
| M12 | 묵은 값에 새 stamp 부여 | CANDIDATE | PARTIAL | PARTIAL | CODE_AUDIT(I06)+SURROGATE(F1/F2) | 7 audited apps: none stamps sample time unmodified (SOURCE) | one real app with sample-time stamping change; clock-domain conversion | parent of M2; F1 freshness confound documented |
| M13 | monitor / gate 고장 | KNOWN_METHOD | PARTIAL | PARTIAL | PRIOR_INTERNAL(S5 C-MON) | fail-closed watchdog in pinned S5 setup | direct consumer bypass, restart, physical hold | ROSMonitoring result scoped to 2026-09-22 image |
| M14 | lease / authority 전환 | KNOWN_METHOD | PARTIAL | YES | PRIOR_INTERNAL(authority_continuity) | IMPLEMENTATION_GAP_ONLY (HORUS) | new multi-user XR path | closed class; do not re-raise |
| M15 | 인증 없는 XR bridge | KNOWN_METHOD | PARTIAL | YES | CODE | unauthenticated bridges source-confirmed (Spes bundled key, OpenArmX UDP) | active security config per hop | none |
| M16 | DDS 권한·발견 구현의 우회 | UNKNOWN | PARTIAL | YES | PAPER_SCOPE(L16,L17) | reported patched/mitigated (L17) | installed DDS version check | none (UNKNOWN kept) |
| M17 | 정상 키 앱의 pose·stamp·상태 공동 위조 | CANDIDATE | PARTIAL | YES | DESIGN(I05) | not defended | minimal trusted mapper baseline | none |
| M18 | runtime 제어 권한·client identity 사칭 | CANDIDATE | PARTIAL | YES | CODE(libmonado API)+DESIGN | unauthenticated setters on app socket (F1 probe) | authenticated control variant | none |
| M19 | gate를 건너뛴 controller 직접 접근 | KNOWN_METHOD | PARTIAL | YES | DESIGN | SROS2/OS mediation is a known method; not deployed here | negative bypass test with permissions | KNOWN_METHOD here = expressible/deployable, not deployment-verified |
| M20 | 증거·제어 경로 과부하 및 fail-closed DoS | CANDIDATE | PARTIAL | PARTIAL | PAPER+SURROGATE(F2) | F2 +30 ms: 6 leaks; +80 ms: 1770/1770 fail-closed | flood/load scenarios; queue isolation baseline | shares F2 evidence with M40; avoid double counting |
| M21 | 다른 운영자의 승인·goal 취소 침범 | KNOWN_METHOD | PARTIAL | YES | PAPER+PRIOR_SCOPE | goal ownership known method | XR multi-user path | none |
| M22 | 본 장면의 target와 실행 target가 달라짐 | CANDIDATE | GENERIC | PARTIAL | RESEARCH_INFERENCE(L06,L27,L28) | none executed | a target-selection XR->ROS app; scene-version baseline | no audited implementation is target-selection based |
| M23 | XR overlay / synthetic cursor로 잘못 승인 | CANDIDATE | PARTIAL | YES | PAPER(L10)+INFERENCE | WebXR UI attacks shown by authors (browser/ad setting); follow-up workshop paper exists (L39, content unread) | robot-command consequence; current browser mitigations | robot harm is our inference |
| M24 | 공간·chaperone 기만으로 operator motion 유도 | UNKNOWN | GENERIC | PARTIAL | ABSTRACT(L09) | none | attack surface in a robot task | none (UNKNOWN kept) |
| M25 | 명령·feedback의 coordinated FDI | CANDIDATE | PARTIAL | YES | PAPER(L24-L26) | attacks and a 2025 defense exist (abstract) | full-text comparison | none |
| M26 | haptic / force feedback의 누락·변형 | UNKNOWN | GENERIC | PARTIAL | AUTHOR_LIMITATION(L28) | none | task definition | none |
| M27 | 물리 가림·방해로 정상 transition 유발 | UNKNOWN | GENERIC | PARTIAL | AUTHOR_LIMITATION(L29) | none | hardware path | none |
| M28 | hand/controller/profile 교체 중 기준점 변경 | UNKNOWN | GENERIC | PARTIAL | UNTESTED | none | spec event + 2 implementations | none |
| M29 | static tf / calibration 갱신과 cache의 엇갈림 | UNKNOWN | GENERIC | PARTIAL | UNTESTED | none | versioned repro | none |
| M30 | XR camera / mesh / 공간 데이터 과다 공유 | KNOWN_METHOD | PARTIAL | PARTIAL | PAPER(L07,L12,L13) | controls exist in other XR settings | XR->ROS flow inventory | none |
| M31 | teleop motion으로 사용자 식별 | UNKNOWN | GENERIC | PARTIAL | PAPER(L14) | VR identification shown (Beat Saber) | teleop data | none |
| M32 | 암호화 트래픽의 작업·행동 추론 | UNKNOWN | GENERIC | YES | SEED_LEAD | none | full text | none |
| M33 | 닫힌 앱·runtime의 증거 미노출 | UNKNOWN | PARTIAL | PARTIAL | CODE_SCOPE(I06) | 2 closed APKs; PickNik host closed | capability manifests | overlaps M12 (evidence availability); keep linked |
| M34 | 인과 로그 부족·위조로 잘못된 audit | CANDIDATE | PARTIAL | PARTIAL | PAPER(L11,L12) | none | trace + provenance audit | none |
| M35 | runtime IPC query로 service 가용성 상실 | UNKNOWN | PARTIAL | PARTIAL | INTERNAL_OBSERVATION(F1 bring-up, isolated repro) | service terminated on one libmonado query for a sessionless client (045931d) | upstream issue search; recovery behaviour | not a CVE claim; upstream status unknown |
| M36 | 재연결·QoS queue에서 묵은 목표 실행 | KNOWN_METHOD | PARTIAL | PARTIAL | CODE+DESIGN | known freshness/epoch/QoS methods | reconnect chain run | none |
| M37 | 안전 범위 안이지만 잘못된 mode/작업 명령 | CANDIDATE | GENERIC | PARTIAL | RESEARCH_INFERENCE | none | policy definition | none |
| M38 | 자연 drift / 보정 오차의 독립 판정 | UNKNOWN | GENERIC | PARTIAL | UNTESTED | none | calibration/SLAM literature | none |
| M39 | 중단→정지→재허가→재기준화의 결합 | CANDIDATE | PARTIAL | PARTIAL | CROSS_CASE(P1/P1b/F3)+CODE | components executed separately (M3 hold, M4 re-arm, M6 epoch); combination never executed; F3 resume jump unmitigated | combined contract on a real path without singularity confound | umbrella of M3-M6; must not count as an independent finding; S5 attacker listed without scenario |
| M40 | 짧은 transition·지연 증거의 검사 race | CANDIDATE | SPECIFIC | PARTIAL | SURROGATE(F2) | 5 ms window: interval 1/18 leak; +30 ms: 6 leaks per state arm | event-delivery or bounded-wait baseline | shares F2 data with M20 |
