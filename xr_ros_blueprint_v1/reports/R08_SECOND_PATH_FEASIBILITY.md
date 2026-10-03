# R08 — A second real XR→ROS app path for the M39 full-contract comparison: feasibility (2026-10-03)

**Result: no second real app path can be run with the resources on this host.**

- No smoke was run, because no real frontend ran.
- No stand-in app was substituted.
- No ROS-backend-only synthetic run is counted.

## What was checked, and how

- **Prior records** (read first, not repeated):
  - audits A2 (Quest2ROS2), A3 (PickNik) and A5 (Docker_Teleop);
  - `F1_independent_evidence/APP_COMPATIBILITY.md` (2026-10-02: all three frontends excluded as
    Android/Unity Quest apps);
  - S-track `PICKNIK_QUESTLESS_CONVERGENCE.md` (2026-09-14: PickNik build BLOCKED by a missing
    Unity license entitlement);
  - R0 (a 2026-09-17 real-Quest PickNik capture, PRIOR_INTERNAL).
- **Host resources found today:**
  - Unity Hub with Editor **6000.1.6f1** (modules: LinuxStandaloneSupport, AndroidPlayer);
  - a Personal license that resolves entitlements (`Pro License: NO`);
  - `adb` with **no device attached**;
  - **no Quest headset** (`lsusb` shows no Meta/Oculus device);
  - Quest APKs from the closed S-track in `ros_xr/Deprecated/local_artifacts/quest_apps/`
    (`docker_teleop/R.U_7.0.7.apk`, `picknik/picknik_semantic_validation.apk`). Their
    correspondence to the audited commits is NOT_VERIFIED.
- **Re-checked at the pinned sources** (key claims only):
  - Docker_Teleop @64cbdde: grip level `>= analogPressThreshold`
    (`HandPoseSender.cs` L434–436); `isTracked` = controller connected (L1240–1251); receiver
    neutral-on-stale (`quest_controller_receiver.py` L428–436, `_neutral_state` L588); Unity
    **6000.2.10f1**; Meta XR SDK core/interaction/platform 72.0.0.
  - Quest2ROS2 @07aaf65: `allow_pose_update = True` at start (L89); `button_lower` rising edge
    toggles (L356–358).
  - PickNik @bbaef07: `RosPublishers` publishes a per-button `Bool` = `IsPressed()` at 60 Hz and an
    `Empty` on `WasPressedThisFrame()`; it connects to the IP in PlayerPrefs `RosIPAddress`.
  - Monado 045931d: the remote driver is an Index controller (`r_device.c` L216–218), and Monado
    binds the Index device to the Oculus Touch profile (`vive_bindings.c` `touch_inputs_index[19]`).

## Bring-up attempt (one candidate, about 25 min of the 60 min budget)

**Chosen candidate: PickNik.** It is the only candidate whose frontend source and toolchain exist
on this host. Its project already enables the OpenXR loader and the Oculus Touch profile for
Standalone. On Linux, it could in principle be driven by Monado's scripted controllers without a
headset.

**Steps.**

- The project was copied to an ignored work directory
  (`experiments/SP2_second_path/work/`, unmodified).
- It was built with the Unity CLI and **no project change**:
  `Unity -batchmode -nographics -quit -projectPath … -buildTarget Linux64 -buildLinux64Player …`.

**Result (12:16:38 → 12:17:21 KST).**

- Licensing succeeded and the packages resolved.
- The build failed in OpenXR project validation: *"The only standalone targets supported are
  Windows x64 and OSX with OpenXR. Other architectures and operating systems are not supported at
  this time."* (`BuildFailedException: OpenXR Build Failed`).
- **This is a platform limit, not a validation setting.** The resolved `com.unity.xr.openxr` 1.14.3
  ships `UnityOpenXR` native plugins only for Android, macOS, Windows and UWP. There is no Linux
  binary (`notes/unity_openxr_1.14.3_native_plugins.txt`). Bypassing the validation would still leave
  no OpenXR provider in a Linux player. The attempt stopped there.
- **Side observations:**
  - the audio `.wav` assets in the pinned checkout are Git LFS pointers (import errors, not fatal);
  - the Editor rewrote `~/.local/share/unity3d/prefs` (normal Editor side effect).
- **Evidence:** `notes/picknik_linux_build_log_excerpt.txt`. The full log stays local and ignored
  (sha256 `32bfb8d8…`).

**Not attempted, with reasons:**

- **Docker_Teleop.** Its frontend reads input through the Meta XR SDK (`OVRInput`/OVRPlugin), and
  its project needs Unity 6000.2.10f1, which is not installed. No Quest is attached for the APK.
  - Running OVRPlugin on Linux is NOT_VERIFIED here and is not assumed. An inference from the SDK's
    targets (Android/Windows) is not used as evidence.
  - The ROS backend alone could be run (image `docker-teleop-humble:local`). That would be a backend
    with synthetic messages and is not counted.
- **Quest2ROS2.** Its frontend is a closed Quest APK, and its consumer (Cartesian controller) is not
  in the repository.

## Candidate table

| Item | Docker_Teleop (@64cbdde) | Quest2ROS2 (@07aaf65 + closed APK) | PickNik (@bbaef07) |
|---|---|---|---|
| Real frontend; open / closed | Unity app (source open) + Meta XR SDK 72 (binary package) | `com.Tiguin.Q2R` APK (**closed**) | Unity app (source open; Unity OpenXR/XRI/Input System packages) |
| Needs | Quest + adb reverse; Unity 6000.2.10f1 + Android module for a rebuild | Quest + ROS-TCP (`ros_tcp_communication`, which needed CDR/NUL fixes in PRIOR_INTERNAL) | Quest (Android OpenXR) **or** Windows/macOS + an OpenXR runtime; plus MoveIt Pro for commands |
| Available now | backend image yes; **no Quest**; Editor version mismatch | **no Quest** | Editor yes; Linux build **impossible** (no Unity OpenXR Linux); **no Quest**; no MoveIt Pro |
| Pose on the wire | JSON/TCP per frame: Unity world pose, `isTracked` (= connected) → `ReceivedPoseStates` (60 Hz) | `PoseStamped` (frame and stamp ignored by the controller) | `nav_msgs/Odometry` frame `quest` + `/tf` at 60 Hz (shared mutable message; R0: left topic carried right pose in 54 %) |
| Button on the wire | `teleop_enable` = grip analog ≥ 0.55 (**level**, per frame) | `OVR2ROSInputs.button_lower` (level; the controller uses its rising edge as a **toggle**) | `Bool` = `IsPressed()` (level, 60 Hz) + `Empty` press event |
| Real release/press vs default/cached | Receiver neutral-on-stale (0.25 s) forces `teleop_enable=False` and sets `source="stale_timeout"`. A detector reading only `teleop_enable` sees a **fake release**, then a fake press on reconnect. The `source` field can tell them apart. Unity values while unfocused: NOT_VERIFIED. | No neutral/stale field. While unfocused the app's output is unknown (closed). A false→true across an interruption **flips the toggle**, which can enable or disable streaming. | No neutral/source field. If the Input System reports not-pressed while inactive and pressed on refocus, the wire shows false→true **and** a press `Empty`, indistinguishable from a real re-press (NOT_VERIFIED). `runInBackground: 1` keeps publishing. |
| Independent runtime evidence linkable to the app | none on a Quest: no libmonado; Meta OS runtime closed | none on a Quest | none on a Quest; on Monado it would be libmonado, but there is no Linux player |
| Command semantics / final controller | mapper twist (P-control, relative anchor) → Servo 2.5.9 twist → JointGroupVelocityController (bridge always publishes zero twist) | absolute pose target re-anchored on enable → Cartesian controller (not in repo) | closed MoveIt Pro objective (clutch and command generation) |
| C1 reusable parts | shared stop core (Servo pause; the hold must become zero velocity, not a JTC hold); silence detection. Re-basing not needed (relative twist). Evidence reader not usable (no libmonado). | stop/suppress core; re-basing adapter (absolute pose); evidence reader not usable | none confirmable: the consumer is closed |
| Adapter / deployment changes | button adapter must read `source`/stale state; velocity-controller hold; own backend container | button adapter for toggle semantics; substitute consumer (**backend replacement**, to be labelled) | substitute host mapper (**backend replacement**), i.e. no original B0 exists |
| Status | **needs additional resources:** a Quest headset (and either the APK verified against 64cbdde, or Unity 6000.2.10f1 for a rebuild) | **needs additional resources** (Quest) **and a consumer substitute** | **blocked here** (Linux not supported by Unity OpenXR 1.14.3; executed). Needs a Quest or a Windows/macOS host with an OpenXR runtime, **and** MoveIt Pro for an original command path. |

## Consequence for the M39 question

- **A level on the wire is not a fresh-press guarantee** in any of the three candidates:
  - stale neutralization (Docker_Teleop);
  - toggle semantics (Quest2ROS2);
  - possible inactive→false→true transitions with a press event (PickNik).

  Each can create a fake release→press. A ROS-side re-arm adapter would need app-specific
  knowledge of these (for example Docker_Teleop's `source`) and could not use independent runtime
  evidence on a Quest.
- **No comparison design was written.** No path was secured, so per this round's scope the next
  B0/B1/C1 comparison design is not written.
- **What would let it proceed (recommendation, not an instruction):** a Quest headset attached by
  adb to this host. With it, Docker_Teleop is the candidate with the most open path: open backend
  and mapper, grip level on the wire, and a stale `source` field.
  - Its original B0 would be the APK, after verifying its correspondence to 64cbdde, or a rebuild
    with Unity 6000.2.10f1.
  - The independent-evidence part of C1 would be unavailable. The comparison would test fresh-press
    re-arm from wire buttons plus app-specific stale handling.

## Recommendations if no second path becomes available (recommendations only)

- **M39 remaining questions on the existing path, all runnable here:**
  - log Servo's collision scale or replay the self-collision distance, to quantify status 4
    (R05 §B);
  - test JTC `decelerate_to_hold_position` against the M3 residual (R07);
  - a second start configuration or speed.
- **Another matrix case on the same stack:** M12 (stamp meaning), the second candidate in C02. It
  needs a modified-app arm that stamps the sample time. Expected to be solved by known fixes, with
  residuals for inferred poses and buttons.
