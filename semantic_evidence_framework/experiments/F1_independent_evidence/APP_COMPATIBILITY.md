# F1 — Real-app compatibility check before environment construction (2026-10-02)

**Purpose.** Brief step 3: before building anything, decide which *real, existing* XR→ROS apps can run
against a runtime on which we could collect evidence independently. Clients we write ourselves
(`p2_client`) are **not** counted as real apps.

## Candidate table

| App (pin) | API / runtime it targets / OS | Runs as an existing build? | Source change | Rebuild | Config change | Loader/layer/runtime install | Evidence we would collect, and where | Can the app forge or bypass it? | Verdict before building |
|---|---|---|---|---|---|---|---|---|---|
| **OpenVR UR5e** `quest_teleop.py` @ 170dad5 | OpenVR legacy (`IVRSystem`, Raw universe, `GetControllerState`); SteamVR; Linux | Yes. Python, unmodified, already built in `P1_openvr_evidence/ws`. | none | none (app) | `openvrpaths.vrpath` or `VR_OVERRIDE`, plus `XR_RUNTIME_JSON` | **xrizer** (OpenVR→OpenXR, in-process `vrclient.so`) @ `0989a7fa`; Monado main build; a Vulkan driver (lavapipe in a container) | Per-client focus/activity of the app's OpenXR session, as held by **monado-service** (`libmonado` client state; out of process) | It cannot set its service-side focus. A compromised app can skip OpenVR and publish ROS commands directly, so the evidence then bounds *state*, not *command provenance* (see `SECURITY_SCOPE.md`). xrizer is in-process, so its view is **not** independent. | **Candidate 1.** Risk: xrizer drives OpenXR frames from `WaitGetPoses`/`Submit` (`compositor.rs` L102–150), which this Background app never calls. The session may stay in READY, actions would then be inactive on main Monado, and the app would never see the grip. NOT_VERIFIED, test first. |
| **NVIDIA IsaacTeleop** `teleop_ros2` @ 9fba23c | OpenXR headless + `XR_EXTX_overlay` (`oxr_session.cpp` L106–110); CloudXR runtime by default (`XR_RUNTIME_JSON` default `~/.cloudxr/...`, L69–70, overridable); Linux | No build in the environment (`isaac-teleop-jazzy:local` contains ROS only) | none | **yes** (CMake + Python bindings) | `XR_RUNTIME_JSON` → Monado | Monado main build | The same service-side client state. Note: this app is a *tracking reader* overlay, so its own focus is **not** the operator-facing app's focus. | as above | **Partial.** The controller path needs `XR_NVX1_action_context` (`live_controller_tracker_impl.hpp` L31), which Monado main does not list (`oxr_extension_support.py` @ 045931d), so it is **incompatible**. The hand path needs `XR_EXT_hand_tracking` + `XR_MNDX_xdev_space`; both are listed, so it is *plausible*, NOT_VERIFIED. |
| Quest2ROS2 app `com.Tiguin.Q2R` | Android APK, Quest runtime | not on Linux/Monado | — | — | — | — | — | — | **Excluded** (no Linux build; Android Monado requires a device) |
| PickNik Unity app | Unity Android/Quest | not on Linux without a Unity rebuild | — | Unity rebuild for Linux (editor unavailable) | — | — | — | — | **Excluded** |
| Docker_Teleop Unity app | Unity/OVR Android | as above | — | as above | — | — | — | — | **Excluded** |
| OpenArmX APK | Android (PICO/Quest) | no | — | — | — | — | — | — | **Excluded** |
| Spes (WebXR in a browser) | WebXR | Desktop-browser WebXR on Linux through OpenXR: NOT_VERIFIED, not assumed | — | — | — | — | — | — | **Excluded** (not assumed compatible) |
| `tomadimcic/openxr_ros2_bridge` | no OpenXR client (its "console"/"sim" are stand-ins, per its own docstring) | — | — | — | — | — | — | — | **Excluded** (not a real XR client) |

**Consequence.** At most two real apps are candidates (OpenVR UR5e via xrizer; IsaacTeleop hand
path). Neither is known to work on Monado yet. If either fails, that is recorded. A self-written
client is not substituted for it.

## Environment time budget (fixed before building)

| Item | Budget | Stop rule |
|---|---|---|
| Monado main (pinned commit) build in a container, with libmonado, lavapipe Vulkan, null compositor | 60 min | If it does not build or start within budget, record the failure. Do not patch the runtime. |
| xrizer build (cargo, pinned) | 45 min | as above |
| OpenVR UR5e app on xrizer + Monado: reach a running session with grip visible | 60 min | If the session never reaches FOCUSED (the risk above), record the result and **do not** modify the app or xrizer |
| IsaacTeleop hand path | 90 min | Attempted only after candidate 1 is decided |
| Total | ≤ 4.5 h | — |
