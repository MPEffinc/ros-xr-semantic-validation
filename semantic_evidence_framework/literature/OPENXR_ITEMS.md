# OpenXR items examined (spec `KhronosGroup/OpenXR-Docs` release-1.1.63 @ 5a82d45b)

Scope statement: these items were selected because they bear on command-applicability evidence.
Covering them is **not** a claim that the specification is complete. It is also not a claim that
runtime-, vendor- or physical-environment behaviour is complete. For each item, conformance by a real
runtime (Meta Quest, SteamVR, Monado) is NOT_VERIFIED here.

| Item | Spec location | Normative content used |
|---|---|---|
| Action inactive when unfocused | `chapters/input.adoc` L839–841, L1344–1346 | When the session is not focused, `isActive=false` and `xrSyncActions` returns `XR_SESSION_NOT_FOCUSED`. |
| State of inactive actions | `input.adoc` L864–866 | state = 0/false, **`changedSinceLastSync=false`**, `lastChangeTime=0` |
| Edge after inactivity | `input.adoc` L853–858 | If the action was inactive at the previous sync, `changedSinceLastSync=false`. |
| `lastChangeTime` | `input.adoc` ≈L844–846 | the runtime's best estimate of the physical change time |
| Valid vs tracked | `chapters/spaces.adoc` L833–856 | A valid but untracked pose may be inferred or last-known. |
| Reference-space change | `spaces.adoc` L395–417 | `XrEventDataReferenceSpaceChangePending{changeTime, poseValid, poseInPreviousSpace}`. Results respect the change after `changeTime`. |
| Interaction-profile change | `input.adoc` L490, L784–797 | `XrEventDataInteractionProfileChanged`. Profile changes happen only at `xrSyncActions`. |

## Corresponding semantics in non-OpenXR APIs (from audits)

| API | Activity / focus | Validity | Origin change |
|---|---|---|---|
| OpenVR (legacy) | `IsInputAvailable()` (header L2594), `VREvent_InputFocusChanged` | `bPoseIsValid`, `eTrackingResult`, `bDeviceIsConnected` | `VREvent_SeatedZeroPoseReset` / `StandingZeroPoseReset` / `ChaperoneUniverseHasChanged`. A Raw universe is driver-defined. |
| WebXR (Spes) | `XRSession.visibilityState` | `XRPose.emulatedPosition`, null pose | `XRReferenceSpace` `reset` event |
| Unity XR / OVR (PickNik, Docker_Teleop) | `OnApplicationFocus`/`Pause` | `InputTrackingState`, `isTracked`. OVR `GetConnectedControllers` means *connected*. | `XRInputSubsystem.trackingOriginUpdated`, OVR recenter |
