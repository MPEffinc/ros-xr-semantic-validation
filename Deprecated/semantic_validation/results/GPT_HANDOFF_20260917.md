# GPT Handoff Report — 2026-09-17

## 1. Handoff purpose

This document hands the project to a subsequent GPT/Codex agent after the first
actual Quest 3 session. It distinguishes committed Quest-free evidence from the
new uncommitted hardware evidence. Do not treat a source finding, synthetic
runtime, Pi reception, simulator response, or physical actuator behavior as
interchangeable.

Repository: `MPEffinc/ros-xr-semantic-validation`  
Working tree: `/home/cclab/ros_xr`  
Branch: `main`  
Committed `HEAD` and `origin/main` at handoff: `e946e1187b67d1aab3d3c120abb0815b4181550e`

The committed research decision remains **`GO — NOT STRONG GO`**. The new
Docker_Teleop hardware artifact is not yet integrated into canonical documents
or committed, and it must be re-reviewed before it affects that decision.

## 2. Non-negotiable safety and evidence rules

- Never start `servo_test.launch.py`, `ur_robot_driver`, any `robot_ip` path,
  CAN bring-up, Flexiv driver, or another physical robot driver.
- The current Docker runtime is `docker_teleop_sim`; it is Gazebo-only.
- `semantic_robot_sink` / `PI_RECEIVED` is an observation boundary, not
  controller acceptance, actuator execution, or robot movement.
- A physical occlusion is not by itself a valid trial. Preserve and correlate a
  raw native state transition.
- The Docker application field `rightTracked` is source-audited as connection
  derived (`OVRInput.GetConnectedControllers()`); it is not a proven optical
  tracking-validity field.
- Do not label a framework `unsafe`, `vulnerable`, `secure`, or `fail-safe`
  from these results.

## 3. Current local state and preservation requirements

The following paths were untracked at handoff and must be preserved until their
contents are reviewed and either committed intentionally or archived by an
authorized owner:

```text
quest_wireless_adb.sh
semantic_validation/logs/picknik/picknik_hw_20260914T093808Z/
semantic_validation/logs/picknik/picknik_hw_20260914T094213Z/
semantic_validation/logs/picknik/picknik_hw_20260914T095052Z/
semantic_validation/results/runs/hw_docker_native_20260917T071824Z/
```

The last path is the new hardware evidence root. Its `OBSERVATION_BOUNDARY.txt`
states:

```text
container=docker_teleop_sim
topics=/received_pose_states /target_twist_states /servo_node/delta_twist_cmds /joint_states
safety=Gazebo-only; no physical robot or driver
```

The original continuous Unity log file is small and incomplete. The usable
native device evidence is `quest_system_tracking_t02.log` and its curated
non-destructive filter `t02_system_tracking_excerpt.txt`. Do not delete the
larger raw log after reading the excerpt.

## 4. Committed baseline before hardware connection

The canonical Quest-free matrix is
[`QUESTLESS_COMPLETION_MATRIX.md`](QUESTLESS_COMPLETION_MATRIX.md). Its key
results are:

| Framework | Strongest committed Quest-free result | Hardware question still open at start of session |
| --- | --- | --- |
| Docker_Teleop | Synthetic Unity-compatible TCP → production receiver → mapper → MoveIt Servo → Gazebo; D1 motion and D2/D3 halt; source timestamp re-stamped | Does actual optical degradation alter connection-derived `isTracked` and what follows downstream? |
| OpenVR UR5e | Fake OpenVR → production app → MoveIt Servo → Gazebo; `Running_OK` and `Running_OutOfRange` equivalent, `bPoseIsValid=false` gated | Does real Quest/ALVR/SteamVR produce the tested OpenVR state pair? |
| Quest2ROS2 | Production `RightArmController`, reconnect/latch/anchor tests, DDS → Pi `619/619` | Actual external Quest2ROS app tracking and reconnect behavior |
| PickNik | Full source dataflow plus ROS-TCP backend replay `3600/3600`; replay is downstream of PickNik publishers | Actual Unity/OpenXR tracking transition through `ROSPublishers.cs` → Odometry/TF |
| OpenArmX | Production UDP → C++ bridge → `PoseStamped`; timestamp handling at bridge | Closed downstream arm driver/IK and PICO frontend semantics |
| Spes | Actual Quest 3 → server callback previously held; separate upstream native ROS2 → Pi `30/30` | One continuous actual Quest → upstream ROS2 → Pi run |

PickNik Unity `6000.1.6f1` and Android tooling are installed. The real blocker
is Unity licence entitlement, not a missing editor. The Quest APK package
`com.unity.template.vr` was observed installed in this session, but the hardware
backend must be deliberately launched and logged before any claim is made.

## 5. Actual Quest 3 / Docker_Teleop session

### 5.1 Device and safe transport setup actually observed

- Quest 3 was wirelessly ADB-authorized at `192.168.0.178:5555`.
- The Docker official APK package `com.noahli.ROSUNITY` (`Ros_Unity`) was
  launched. Its production log reported TCP connection to `127.0.0.1:5026`.
- The app originally failed when `tcp:5026` was reversed to host port `5026`.
  The correct, verified mapping for the existing receiver container was:

```text
Quest localhost:5026 → desktop localhost:15005 → container port 5005
```

  Command used:

```bash
ADB=/home/cclab/Unity/Hub/Editor/6000.1.6f1/Editor/Data/PlaybackEngines/AndroidPlayer/SDK/platform-tools/adb
$ADB -s 192.168.0.178:5555 reverse --remove tcp:5026
$ADB -s 192.168.0.178:5555 reverse tcp:5026 tcp:15005
```

- `tcp:10001 → tcp:10001` remained reversed. The app emitted ROS-TCP socket
  errors on that port because the reused Docker_Teleop simulator did not run a
  ROS-TCP Endpoint. This does **not** invalidate the independent
  `HandPoseSender` TCP → production receiver path under test.
- No physical robot driver or actuator path was started.

### 5.2 Controlled baseline

The relevant engagement control is the right **side grip**, not the index
trigger. Source confirms:

```text
teleopHeld = rightGripValue >= analogPressThreshold
```

For the controlled baseline window (`2026-09-17T07:28:27Z` through
`07:29:17Z`), the saved bag analysis records:

```text
received=3000
tracked_teleop=667
target=3000
servo=3000
servo_nonzero=667
servo_peak=0.30000000000000004
joint_samples=2941
joint_max_abs_delta=0.14416248413941968
ee_displacement=0.04333756692236975
```

This establishes the actual official Quest app → production receiver → mapper
→ Servo → Gazebo path under a controlled user input. It is simulator-only.

### 5.3 Trial status

| Trial | Time / artifacts | Result | Use in claims |
| --- | --- | --- | --- |
| `hw_dt_t01` | Bag retained under `hw_dt_t01/bag/`; `07:31:14Z`–`07:32:27Z` | Production `tracked` field never became false | `NO_TRANSITION_OBSERVED`; not a negative safety result |
| `hw_dt_t02` | Bag `hw_dt_t02/bag/`; native log and metrics retained; `07:33:08Z`–`07:34:15Z` | System controller-status transition and contemporaneous production/Gazebo continuation observed | Primary new hardware evidence; bounded as below |
| `hw_dt_t03` | `hw_dt_t03/quest_native_and_app.log`; `07:39:29Z`–`07:40:42Z` | Logger dumped its existing buffer then terminated before the user-action interval | Instrumentation failure; exclude from repetition count and claims |

### 5.4 `hw_dt_t02`: exact bounded finding

The right-controller device system log contains a transition during the user
degradation interval:

```text
09-17 16:33:33.145 ... CONNECTED_ACTIVE tracking: ORIENTATION
09-17 16:33:39.904 ... CONNECTED_ACTIVE tracking: POSITION
09-17 16:33:39.915 ... CONNECTED_ACTIVE tracking: ORIENTATION
09-17 16:33:40.110 ... CONNECTED_ACTIVE tracking: POSITION
```

The conservative correlation window is
`2026-09-17T07:33:35.417Z`–`2026-09-17T07:33:40.414Z` (4.997 s). It is recorded
in `t02_degraded_window_metrics.txt`:

```text
received_count=299
tracked_true=299/299
teleop_true=278/299
pose_endpoint_delta_m=0.933084594
servo_count=300
servo_nonzero_count=95
servo_peak_abs_component=0.300000000
joint_samples=294
joint_max_abs_delta_from_window_start_rad=0.391955691
```

Defensible conclusion:

> During a user-initiated interval in which the Quest system reported a
> right-controller `POSITION`/`ORIENTATION` tracking-mode transition, the
> official Docker_Teleop production receiver retained `tracked=true` for all
> 299 sampled messages. It also received teleop-active messages and the
> original downstream Servo/Gazebo path produced non-zero simulated commands
> and joint change. The result is an actual Quest device → production
> application/ROS → simulated-native-consumer observation, not physical robot
> evidence.

The following **must not** be claimed:

- `ORIENTATION` proves an optical tracking loss, invalid pose, or a particular
  OpenXR/Oculus `isTracked` transition.
- The Quest system status is the exact same semantic field as
  `OVRInput.GetConnectedControllers()`.
- The 0.933 m pose endpoint difference or 0.392 rad joint difference is caused
  solely by degradation; user motion and teleop input are confounders.
- A physical actuator moved or would move identically.

Evidence-level handling: this is an actual native Quest application-to-original
simulated-consumer run and can be discussed as **E6-scope hardware evidence**
only with the exact source-system/application semantic caveat above. It is not
an E6 physical-actuation result and should not by itself upgrade the overall
decision until raw-correlation integrity and a repeatable valid-trial protocol
are reviewed.

## 6. Recommended immediate continuation

1. **Preserve and review Docker artifacts first.** Add a canonical hardware
   result document only after extracting a concise, reproducible evidence table
   from `t02` and marking `t01`/`t03` exclusions. Do not overwrite the current
   run root.
2. **Repair the recorder before another Docker repetition.** Use an attached
   PTY/session or a process supervisor that stays alive; confirm file growth
   *after* the trial start marker. Record a bag and native system log from the
   same monotonic/wall-time interval.
3. **Do not call an occlusion trial valid unless a raw system/application
   transition is preserved.** Five valid repetitions remain the target; `t01`
   and `t03` do not count. `t02` is one bounded candidate, not five.
4. **PickNik is the highest-value independent next target** once the actual
   ROS-TCP Endpoint/observer is launched. Keep `ROSPublishers.cs` byte
   identical. Collect native Unity side-band tracking state, controller
   Transform, Odometry/TF, focus/session status, and a run ID in one run.
5. **Spes** can upgrade its already-held actual Quest finding by using
   `spes_native_hardware_day.py` so that actual Quest/WebXR → production server
   callback → upstream `teleop/ros2` → DDS → Pi is correlated in one run.
6. **Quest2ROS2** requires the external app; keep its frontend black-box and
   do not infer source tracking semantics from its host-side ROS result.

## 7. Operational commands and current environment caveat

ADB tool path:

```bash
ADB=/home/cclab/Unity/Hub/Editor/6000.1.6f1/Editor/Data/PlaybackEngines/AndroidPlayer/SDK/platform-tools/adb
$ADB devices -l
$ADB -s 192.168.0.178:5555 reverse --list
```

Observed reverse rules at handoff:

```text
host-15 tcp:10001 tcp:10001
host-15 tcp:5026 tcp:15005
```

The inherited safe simulator container was `docker_teleop_sim`. In this agent
shell, new `docker exec` calls were denied at `/var/run/docker.sock`, and
`sudo` required an interactive password. This is an automation/environment
blocker only; it is not a Docker_Teleop research result. Resolve standard
Docker group/session access before attempting a new bag recorder, and recheck
that only the Gazebo launch is selected.

## 8. Handoff checklist

- [ ] Verify `git status --short`; do not delete the listed untracked evidence.
- [ ] Copy raw logs/bags to a new immutable result root before any destructive
  recorder housekeeping.
- [ ] Update canonical evidence ledger and research decision only after
  reviewing the `t02` source-time correlation and exclusions.
- [ ] Commit documentation/raw-result manifest intentionally; do not commit
  APKs, Unity caches, credentials, or private ADB material.
- [ ] Keep overall decision `GO — NOT STRONG GO` until independent native
  hardware evidence is reviewed and repeated under the methodology.

