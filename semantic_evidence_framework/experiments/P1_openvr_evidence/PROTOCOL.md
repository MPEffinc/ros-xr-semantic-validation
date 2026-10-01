# P1 — OpenVR path: interruption, cached deadman and recenter evidence (pilot protocol)

Frozen before any scheduled trial was run, on 2026-10-01. Three setup smoke trials are excluded from
the results: C0/B0, C0/PAUSE and C0/EPOCH_A. They only checked bring-up, settling, the gate path and
the patched app. C0/PAUSE and C0/EPOCH_A are not schedule cells.

## 1. Question and status of the hypotheses

The pilot tests the ROS-side **consumption** of three code-derived candidates from audit A1. All three
are HYPOTHESIS until measured.

| Case | Candidate | Source of the candidate |
|---|---|---|
| C1 | After deadman release the arm keeps moving until Servo's `incoming_command_timeout` (0.5 s) | `quest_teleop.py` L55–59; `servo_node.cpp` L297–316 |
| C2 vs C3 | ALVR forwards edges only, so a deadman pressed before focus loss can stay *pressed* in SteamVR (H-A1). With only `bPoseIsValid`, a ROS-side re-arm rule cannot tell focus loss (C2) from a brief tracking glitch (C3). | A1 §A1/A2; OpenXR `input.adoc` L864–866 |
| C4L / C4S | A recenter during engagement mixes the pre-change offset with post-change raw poses (H-B1). A jump guard catches large changes but not small ones. | A1 §A5; Spes guard `__init__.py` L246–264 (A4) |

**What this pilot does not claim:**

- It does not reproduce a real runtime or headset transition. The OpenVR source is a time-scripted
  fake that emits what audit A1 says ALVR would deliver.
- It makes no physical-robot claim (Gazebo only).
- It does not claim that SteamVR actually keeps the stale grip. That hop is NOT_VERIFIED, and C2
  *assumes* it in order to test what the ROS side does if it happens.

## 2. Protected task condition, policy and allowed transitions

| Element | Declared policy |
|---|---|
| Manipulation permission | The arm may follow the hand only while the deadman is held **and** the permission was granted by a press within the current uninterrupted active interval. |
| Interruption | On deadman release, focus/action deactivation or a recenter epoch change, new commands stop. The common stop is `/servo_node/pause_servo(true)`. |
| Resume | Only a fresh deadman rising edge while valid (and active, where known) resumes. |
| Allowed normal transitions | (a) A brief tracking glitch (≤ 100 ms) while active and held: motion continues without a re-press (C3). (b) Normal hand motion of up to 0.4 m/s raw (C0, C1). (c) A recenter is legitimate, but it must not *move the robot* (C4). Stopping is permitted, and so is continuing with a continuity-preserving re-anchor. |

The OpenXR rule that deactivates actions is not taken as a robot policy. The declared resume rule
above is ours.

## 3. Cause, injection point and trust boundary

| Item | Value |
|---|---|
| Injection point | The fake `openvr` module (`harness/openvr.py`, through `PYTHONPATH`). Its state is a pure function of wall time since `P1_T0_NS`, so the app and the gate see the same source. |
| Attacker | none. These are benign faults (F0, `docs/02` §3). There is no tf forgery, and the app is trusted. |
| Events kept separate | E-DEACT (C2), E-TRACK (C3), E-ORIGIN (C4). C2 has invalid and inactive together, because ALVR maps an inactive pose action to an invalid pose. C3 has invalid only. |

## 4. Defenses and evidence regimes (equal information within a regime)

| ID | Placement | Evidence regime | Rule |
|---|---|---|---|
| B0 | original wiring | — | none |
| D_TO | Servo config | — | `incoming_command_timeout` 0.5 → 0.1 s (`P1_SERVO_TIMEOUT`); everything else identical (`harness/servo_launch.py`) |
| PAUSE | gate | I_ALVR | stop on a grip falling edge |
| REARM_V | gate | I_ALVR (`bPoseIsValid`, grip) | stop on grip falling **or** valid falling; resume only on a fresh rising edge |
| REARM_C | gate | I_FULL (adds action activity) | stop on grip falling **or** action inactive; a tracking-only loss does not stop |
| JUMP | gate | I_ALVR (raw pose) | stop on grip falling **or** a raw jump of more than 5 cm / 35° against the pose 20 ms earlier. These are the Spes thresholds (A4), not chosen by us. |
| EPOCH_G | gate | I_FULL (recenter epoch) | stop on grip falling **or** an epoch change |
| EPOCH_A | app retrofit | I_FULL (epoch, `R`, `d`) | `harness/quest_teleop_epoch.py` = pinned app + 15 lines. It carries the offsets into the new frame so the target stays continuous. There is no gate. |

- **Gate.** `harness/evidence_gate.py` reads the source through its own OpenVR client at 100 Hz. It sits
  between the app (remapped to `/p1/app_cmd`) and Servo, and it uses `harness/gate_core.py`. The host
  test `host_logic_test.py` runs the same core.
- **Equal evidence.** I_FULL is available to *every* I_FULL defense: REARM_C, EPOCH_G and EPOCH_A.
  None of them receives simulator ground truth, such as `grip_truth` or hand position.

## 5. Oracles (frozen in `analysis/analyze.py`)

EE pose is `tf base_link → wrist_3_link` (Servo's tracked frame), polled at 100 Hz. Times are in s from T0.

| Case | Script | Oracle |
|---|---|---|
| C0 normal (control) | hand +0.10 m/s raw for 5.0–9.0 s | FALSE_BLOCK if the EE x-progress over 5.0→9.8 s is < 0.10 m (commanded 0.20 m) |
| C1 release | hand +0.40 m/s for 5.0–7.0 s; grip released at 6.5 s | VIOLATION if max EE displacement over [6.6, 12.4] exceeds 5 mm |
| C2 deact + cached grip | hand +0.10 m/s for 5.0–8.0 s; invalid and inactive for 6.0–8.0 s; reported grip held; true grip released at 6.0 s | VIOLATION if displacement over [8.0, 12.4] exceeds 5 mm, or rotation exceeds 2° |
| C3 tracking glitch (control) | hand +0.10 m/s for 5.0–9.0 s; invalid for 6.0–6.1 s; active; grip held | FALSE_BLOCK if x-progress over 6.1→9.5 s is < 0.0725 m (50 % of commanded 0.145 m) |
| C4L recenter | hand still; recenter at 6.0 s, d = (0.30, 0, 0.10) m, yaw 30° | VIOLATION if displacement over [6.0, 12.4] exceeds 5 mm, or rotation exceeds 2° |
| C4S recenter | hand still; recenter at 6.0 s, d = (0.03, 0, 0) m | as C4L |
| C5 fast legit motion | 3 m/s for 0.1 s | **host-only** (gate logic): FALSE_BLOCK if the gate disarms |

**Distinguishing filtering from stopping.** `servo_in` counts show whether commands were filtered.
The EE displacement shows whether the executing target was neutralized and the arm stopped
physically. These are reported separately.

## 6. Schedule, trial count and runtime

- **Schedule.** 18 cells × 3 repetitions = **54 Gazebo trials** (`make_schedule.py`, seed 20261001,
  rep-major blocks shuffled). The schedule is in `schedule.csv`.
- **Runtime.** About 40 s per trial in a fresh container, so about 40 min sequentially.
- **Host-only layer.** All 7 cases × 5 gates (`analysis/host_logic_result.json`).
- **Why 3 repetitions.** The source is deterministic; repetitions only expose simulator and timing
  variance. This is a pilot, not the S4 formal protocol.
- **Expansion rule.** A cell whose 3 outcomes disagree is extended to 5 repetitions with identical
  parameters, and both counts are reported.
- **Setup retries.** At most 2 identical retries, and only for a trial that did not reach the barrier.

## 7. Load and environment

- Image `openvr-jazzy-sim:local` with MoveIt Servo 2.12.4.
- Containers run with `--network none`, `--cap-drop ALL` and user 1000.
- Three containers belonging to other work stay running (`docs/00_ENVIRONMENT.md`). The background
  load average is about 1.5, and each trial records the load in `setup.json`.
- Nothing else of ours runs during the campaign.

## 8. Interpretation rules (fixed in advance)

- If B0 shows no violation in a case, the candidate is **not reproduced** on the ROS side for that
  case, and it is recorded as such.
- If a single conventional defense passes both the violating case and its control (C2+C3, or C4+C0),
  the case is **solved by an existing method with that evidence**. The evidence regime it needed is
  recorded.
- If every I_ALVR defense either violates or false-blocks while an I_FULL defense passes, the
  limitation is **METADATA** (evidence delivery), not a checker limit.
- Retrofit cost:
  - gate rules, as lines in `gate_core.py`;
  - the app retrofit, at 15 lines;
  - whether each one needs implementation-specific knowledge. EPOCH_A needs the app's offset
    semantics; the gate rules do not.
