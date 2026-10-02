# F3 — one real XR→ROS app, end to end, under the receive-time-state claim (frozen 2026-10-02, before formal trials)

## Stack (components labelled)

| Component | Version | Modified? |
|---|---|---|
| App | `quest_teleop.py` @ 170dad5, entry point from the P1 workspace build | **unmodified** |
| OpenVR runtime | xrizer @ 0989a7f + `xrizer_extfilter.patch` + `xrizer_bg_pump.py` v1–v3 (image `f3-xrizer-bgpump:0989a7f-v3`, env `XRIZER_F3_LEGACY_ON_TEMP=1`) | **modified deployment component** (see below) |
| OpenXR runtime | Monado main `045931d` | unmodified |
| Consumer | MoveIt Servo 2.12.4 + Gazebo (the P1 testbed launch files) | unmodified |
| Input | Monado `remote` driver (scripted controllers) | not a headset |

The xrizer changes, each needed by an OpenVR **Background** app:

- **(1)** request only the Vulkan device extensions that are supported (lavapipe);
- **(2)** drive empty OpenXR frames and update `display_time` on every pose query;
- **(3)** allow legacy input actions on the temporary session.

Without them the app produces 0 commands (`F1_CANDIDATE1_BRINGUP.md`, F3 probes). **No GPU
environment change is needed:** lavapipe suffices once (1) is applied.

## Claim tested (from `results/F2_TIMESTAMP_REVIEW.md`)

**Receive-time state only.** The gate admits a command iff the latest runtime evidence for the bound
client, at the gate's receive time, satisfies all of these:

- it is ≤ 50 ms old;
- `FOCUSED` (observable here, because the client is compositor-backed);
- `IO_ACTIVE`;
- `¬INPUTS_BLOCKED`.

The command stamp is not used. The binding is by configuration (client name `python3.12`,
self-reported).

## Scenario

| Time (s) | Event |
|---|---|
| 2.0 → | grip held |
| 4.0–7.0 | right controller moves at 0.05 m/s |
| 8.0–9.5 | runtime-applied input deactivation (`mnd_sched` IO toggle) |
| 8.5–9.2 (inside the deactivation) | hand moves at 0.10 m/s |
| 11.0–13.0 | hand moves at 0.05 m/s |

Capture lasts 16.5 s.

## Arms and runs

- **Arms:** B0 (app → Servo directly) and GATED (app → `/f3/app_cmd` → gate → Servo).
- **Runs:** 3 per arm, interleaved B0, G, G, B0, B0, G. One GATED setup smoke is excluded.

## Measures (`analyze_f3.py`, frozen)

- app commands per run, and the pre-window rate;
- app commands, and commands reaching Servo, inside the window (excluding ±20 ms) and in the boundary
  band;
- EE displacement inside the window, and the EE jump within 1 s after resume;
- for GATED: pre-window false blocks, admits inside the window, and the median stamp − receive time.

## Criteria (fixed)

| Criterion | Requirement |
|---|---|
| Normal | GATED pre-window false blocks ≤ 1 % |
| Gate claim | GATED: 0 commands reach Servo inside the window (±20 ms excluded) |
| Descriptive only | B0 in-window commands, and the post-resume jump (expected in both arms: the app keeps its pre-window offset, and a receive-time gate makes no claim about resume semantics) |
