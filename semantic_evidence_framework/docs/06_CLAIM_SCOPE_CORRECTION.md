# 06 — Claim-scope correction (2026-10-02)

This file supersedes three wordings used earlier in `docs/03`, `docs/04`, `docs/05`, `STATUS.md`,
`results/R0`, `results/P1` and the 2026-10-01 chat report. Those documents now point here.

| Earlier wording | Corrected scope |
|---|---|
| "In all 6 implementations the evidence exists at the source but is lost on the way to ROS" | Two separate claims: **(a)** the *API/specification* used by each frontend can provide the evidence, and this is confirmed only where the API is known (table below); **(b)** the *ROS-facing interface* lacks it in 6/6. Neither (a) nor (b) means that the app *reads* the evidence. The app reads it in only a few confirmed cases. |
| "Once evidence is delivered, existing methods solve everything" | Limited to what was **executed**: P1/P1b on the OpenVR UR5e path with a synthetic source (M3 release → controller hold; M4 cached deadman → cause-aware re-arm *with* activity; M6 recenter → epoch gate or app retrofit *with* an epoch), plus S5's PRIOR_INTERNAL cases (synthetic Docker/fake OpenVR). Every other matrix row is "expressible by an existing mechanism", **not executed**. |
| "Kill if the runtime cannot expose the facts headless" | Withdrawn. One headless failure on one Monado build does not show that an independent path is impossible (`docs/05` revised). |

## Four levels per evidence item and implementation

Legend:

- **P** — provided by the API/spec. Source given.
- **R** — read by the app's own code (SOURCE_CONFIRMED).
- **W** — carried on the wire to ROS (SOURCE_CONFIRMED from the message or packet definition).
- **C** — consumed on the ROS side.
- `–` — not done (SOURCE_CONFIRMED).
- `nf` — NOT_FOUND_IN_SEARCH.
- `?` — NOT_VERIFIED: closed source, or the API is unknown.

### E1 tracked state (tracked, as distinct from valid)

| Impl. | P | R | W | C |
|---|---|---|---|---|
| OpenVR + ALVR | OpenXR `*_TRACKED_BIT` (`spaces.adoc` L852–856) | ALVR reads VALID bits only (`interaction.rs` L793–798); TRACKED: nf | `eTrackingResult` is constant `Running_OK` (`Controller.cpp` L205), so it is uninformative | app reads `bPoseIsValid` only |
| Quest2ROS2 | ? (closed APK; SDK unknown) | ? | – (`OVR2ROSInputs.msg`, `PoseStamped`) | – |
| PickNik | Unity Input System `trackingState`/`isTracked`, bound in the XRI action map (A3) | used only inside XRI's TrackedPoseDriver; `ROSPublishers.cs` does not read it | – (`Odometry` covariance 0) | host ? |
| Spes | WebXR `XRPose.emulatedPosition` | nf | – | – |
| Docker_Teleop | OVR SDK (controller tracked APIs: vendor documentation, not checked here, ?); `OVRHand.IsTracked` for hands | controllers: **connected** only (`HandPoseSender.cs` L1240–1268); hands: R | W (bool, meaning "connected" for controllers) | C at 3 hops |
| OpenArmX | ? (closed APK) | ? | – (UDP payload) | receive-time freshness only |

### E2 focus / input activity

| Impl. | P | R | W | C |
|---|---|---|---|---|
| OpenVR + ALVR | OpenXR session state + `isActive` (`input.adoc` L839–846) | R: `is_active` for the pose action; session READY/STOPPING/EXITING/LOSS_PENDING; VISIBLE/FOCUSED nf | – (OpenVR legacy struct has no slot) | – |
| Quest2ROS2 | ? | ? | – | – |
| PickNik | Unity `OnApplicationFocus` (engine) | nf in `ROSPublishers.cs`. The 2026-09-17 sideband was **our instrumentation**, not app code. | – | host ? |
| Spes | WebXR `visibilityState` | nf | – | – |
| Docker_Teleop | Unity `OnApplicationFocus/Pause` | a handler exists in `VRCameraFix.cs` but is attached to no scene (A5) | – | – |
| OpenArmX | ? | ? | – | – |

### E3 origin change and effective time

| Impl. | P | R | W | C |
|---|---|---|---|---|
| OpenVR + ALVR | `XrEventDataReferenceSpaceChangePending.changeTime` (`spaces.adoc` L395–417) | R (event) but `changeTime` dropped (`lib.rs` L448–458) | – | – |
| Quest2ROS2 / OpenArmX | ? | ? | – | – |
| PickNik / Docker_Teleop | Unity `trackingOriginUpdated` / OVR recenter event (A3/A5) | nf | – | – |
| Spes | WebXR `XRReferenceSpace` `reset` | nf | – | – |

**What the corrected claims say:**

- **The ROS interface lacks E1–E3 in 6/6 (W/C columns).** This is SOURCE_CONFIRMED from the message
  and packet definitions. Docker_Teleop's E1 bool is the one exception, and its meaning is
  "connected".
- **Provision by the API (P) is documented for the 4 open frontends.** For the 2 closed APKs it is
  unknown.
- **The app reads the evidence (R) only where confirmed:** ALVR (E1 valid only, E2 pose-action
  activity, E3 event without its time) and Docker hands (E1). Absence in the other open apps is
  `nf`, not proof.

## Executed vs. expressible (matrix scope)

| Matrix item | Executed with an existing mechanism? | Where |
|---|---|---|
| M3 release | yes (controller hold) | P1b, OpenVR path, Gazebo |
| M4 cached deadman | yes, at the command level (cause-aware re-arm *given* activity) | P1, OpenVR path |
| M6 recenter | yes (epoch gate / app retrofit *given* an epoch) | P1, OpenVR path |
| M1, M12, M13, parts of M2 | yes, PRIOR_INTERNAL | S5, synthetic Docker / fake OpenVR |
| M2 frozen stream, M5, M7, M8, M9, M10, M11, M14, M15 | **not executed in this study**. "Expressible by an existing mechanism" is a design statement. | — |
