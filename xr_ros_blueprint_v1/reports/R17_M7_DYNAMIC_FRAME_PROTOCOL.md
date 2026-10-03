# R17 — M7: commands expressed in a moving frame and the time of the transform (protocol; frozen before formal runs)

**Kind of configuration.** This is a **new experimental configuration** on the existing UR5e app path. A scripted
dynamic frame and a representation adapter are added. It is not a reproduction of a problem that arose naturally in
the original app, and not a second app path. Results are **command level**. The Gazebo reaction is recorded but not
judged.

## 1. Task semantics (declared first)

| Semantics | The command means | The correct transform time |
|---|---|---|
| **H — hold** | "the world target that the input denoted when it was expressed" | the **representation time** (when the pose was expressed in the moving frame) |
| **F — follow** | "this pose relative to the moving frame, wherever that frame is now" | the **latest** transform (intended behaviour) |

Every arm is scored against **both** semantics. Neither is assumed universally correct.

## 2. Chain

- The unmodified app (`use_sim_time:=true`) publishes `base_link` targets stamped with the generation time t_g
  (sim) on `/m7/app_cmd`.
- **Representation adapter** (`harness/repr_adapter.py`): looks up tf `base_link→moving_ref` **at t_g** (bounded
  wait 50 ms) and publishes `m7_msgs/RepresentedPose` with `header.stamp = represented_at = t_g`,
  `represented_frame = moving_ref`, and the pose expressed in that frame.
  - The representation time is the **generation time** the app has. There is no source sample time on this path
    (R13/R15).
- **Bridge** (`harness/m7_bridge.py`): PASS / DELAY (80 ms, stamps kept) / RESTAMP (in 6.0–7.5 s, the last message is
  republished at 20 Hz with `header.stamp = now`; `represented_at` is kept).
- **Converter arms** (`harness/m7_converter.py`): `moving_ref → base_link`, then Servo. The same policy for every arm:
  - age check `now − header.stamp ≤ 100 ms` (sim);
  - tf lookup with a bounded wait of 50 ms;
  - default tf buffer history (10 s).

| Arm | Transform time used |
|---|---|
| L | latest tf (`Time()`) |
| S | `header.stamp` (the transport stamp, which may be re-stamped) |
| R | `represented_at` (time-indexed tf at the declared representation time; standard tf2 usage) |

**Scripted frame** (`harness/frame_script.py`):

- moving_ref = base_link + (0, A·sin(2π f (t − t_start)), 0), with A = 0.05 m, f = 0.5 Hz (peak 0.157 m/s);
- no rotation;
- STATIC = identity;
- published at 100 Hz (sim) by `harness/tf_frame_pub.py`;
- t_start is logged.

## 3. Ground truth (independent of tf and of the app output)

From the script function and the logged t_start:

- **H truth** = p_F + offset(represented_at);
- **F truth** = p_F + offset(sim time at conversion).

**Error** = |converted target − truth| for each admitted message.

**Adapter check.** |(p_w − p_F) − offset(t_g)|, i.e. whether the tf lookup at t_g matched the script.

The script function is a harness-side reference. It is used only for scoring and is never given to any arm.

## 4. Conditions and schedule

| ID | Frame | Bridge | Purpose |
|---|---|---|---|
| STATIC | static | PASS | normal; transform time irrelevant |
| DYN | dynamic | PASS | no added delay (natural pipeline latency only) |
| DYN_DELAY | dynamic | DELAY 80 ms (within the 100 ms age) | delay admitted by the age check |
| DYN_RESTAMP | dynamic | RESTAMP | cache with fresh stamps |

3 arms × 4 × 3 = **36 formal trials** (`schedule_m7.csv`; `Random(170 + rep)`; Latin rotation).

**Tf time alignment and age blocking are separated:**

- errors are computed over admitted messages only;
- blocks are counted by reason (age / tf_unavailable), so the two effects are reported apart.

**Also descriptive:** restamped messages whose `represented_at` is older than 100 ms. This is what a
representation-time age check would additionally block.

## 5. Measures and validity

**Measures:**

- per arm and condition: H-error and F-error (median / p95 / max; whole run and the 6.0–7.5 s window);
- admitted / blocked by reason;
- false blocks in STATIC/DYN;
- tf wait p95;
- the adapter's representation error.

**Validity:**

- R03 instrumentation rules (frozen `analyze_m39`);
- missing tf or converter logs.

Reruns at most 2; all attempts are kept.

## 6. Limits

- One translation-only frame motion.
- Generation-time semantics only. No real source sample time exists on this path.
- tf from a scripted broadcaster on the same host clock: no tf transport loss or clock-skew study.

## 7. Pre-flight (excluded; snapshot 2d46a49; 02:49–02:53)

m7_msgs built (colcon) in the trial image. Errors in mm:

| Run | H error (median / max) | F error (median / max) | Notes |
|---|---|---|---|
| PF1 R DYN | 0.002 / 0.009 | 4.11 / 6.81 | adapter representation error ≤ 0.009 mm; 2 adapter tf failures at start; flagged `joint_state_gap` |
| PF2 L DYN_RESTAMP | 3.46 / **81.6** (window median 13.8) | 0.41 / 1.55 | 26 restamped messages had `represented_at` > 100 ms old |
| PF3 S STATIC | 0 / 0 | 0 / 0 | — |

All arms waited ≤ 0.2 ms (p95) for tf. **No rule changed after the pre-flight.**
