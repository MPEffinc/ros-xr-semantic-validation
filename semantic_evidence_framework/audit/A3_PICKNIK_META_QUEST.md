> **Provenance.** This audit was delegated to a read-only subagent on 2026-10-01 under `AUDIT_METHOD.md` and reviewed by the lead auditor. Claims spot-checked against the pinned source by the lead: message-object reuse plus asynchronous serialization (`ROSPublishers.cs` L76–90, L386–416; connector `RosTopicState.cs` L211–216, `TopicMessageSender.cs` L47–62, L109–117 at `c27f00c6`). Other claims carry the subagent's citations and have not been re-read line by line. Treat them as SOURCE_CONFIRMED at the cited lines, subject to re-check before any claim is published. Scratchpad paths (`rtc/`) refer to read-only copies of upstream files fetched by commit.

# Source audit: PickNik meta_quest_teleoperation (XR -> ROS 2), A1-A9

## Pins & scope

| Item | Value | How verified |
|---|---|---|
| Target repo | `https://github.com/PickNikRobotics/meta_quest_teleoperation` | `git remote -v` |
| Target commit | **`bbaef0762fdb0b429b8ea12a4ca65040748b41dd`** (local HEAD = `origin HEAD` via `git ls-remote`, 2026-10-01). `git status --porcelain` is empty | git |
| History | 1 commit (`bbaef07 2026-08-12 chore: Add BSD-3-Clause LICENSE file`), so the history was squashed | `git log` |
| Lineage | GitHub `fork:false`, `parent:null` (`gh api repos/...`). Built from the Unity **VR Template** (`Assets/VRTemplateAssets/**`), **XRI 3.1.1 Starter Assets** (`Assets/Samples/XR Interaction Toolkit/3.1.1/**`) and Unity **ROS-TCP-Connector**. The only project-authored runtime code is `UnityProject/Assets/ROSPublishers.cs` (SHA-256 `9fd803f0...873a`) plus `Assets/DataCollectionActions.inputactions`. It is not a derivative of another teleop repo, so count it once. The XRI rig and connector behaviour are generic upstream code shared with every other XRI/ROS-TCP app. | SOURCE_CONFIRMED |
| Unity packages | Input System 1.14.0, XRI 3.1.1, OpenXR 1.14.3, XR Mgmt 4.5.1, XR Hands 1.5.0 (`UnityProject/Packages/manifest.json`). Package sources are not in the repo (Library/PackageCache is gitignored), so their behaviour is **NOT_VERIFIED** beyond the serialized config. | SOURCE_CONFIRMED (versions) |
| ROS-TCP-Connector | `packages-lock.json:167-173` hash `c27f00c6cf750d2d0564349b3039d19aa3925e7c` = upstream "Release 0.7.0" (2022-02-02). Files were fetched read-only via `gh api .../contents?ref=c27f00c6` to scratchpad `rtc/`. | SOURCE_CONFIRMED |
| ROS-TCP-Endpoint (host bridge) | **Not pinned by the target** (README only names `ros_tcp_endpoint`). Audited local checkout `Deprecated/ros_env/ros2_ws/src/ros_tcp_endpoint` @ `54c1a64b6d5ef6ffa0a0431570bb74329b79b15b` (= upstream `refs/heads/main-ros2` per `ls-remote`). The version pairing is an assumption. | SOURCE_CONFIRMED for that SHA only |
| Host mapper / clutch / command generation | MoveIt Pro Objective "Teleop With Meta via Pose v11" (closed, commercial). It is **not in the repo**, so everything past the endpoint ROS publishers is **NOT_VERIFIED**. README:58-62 is the only description. | AUTHOR_CLAIM |
| Build scene | `ProjectSettings/EditorBuildSettings.asset`: only `Assets/Scenes/SampleScene.unity` is enabled. The Android XR loader is `Open XR Loader` (`Assets/XR/XRGeneralSettings.asset:27-33`, guid `28fe0472...` = `Assets/XR/Loaders/Open XR Loader.asset`). | SOURCE_CONFIRMED |

**Confirmed frontend scope:** OpenXR feature config -> Input System actions -> XRI rig TrackedPoseDriver (TPD) config -> `RosPublishers` -> ROS-TCP-Connector 0.7.0 -> ROS-TCP-Endpoint main-ros2 `rclpy` publishers.
**Unverified scope:** OpenXR/Input System/XRI runtime internals, the MoveIt Pro receiver/mapper/clutch, whether MoveIt Servo is used, and the robot driver.

PRIOR_INTERNAL (background only, not new): `PICKNIK_QUESTLESS_CONVERGENCE.md` §5.1-5.2 and `PICKNIK_QUEST_FEASIBILITY_20260917.md` report a Quest run in which `isTracked=false, trackingState=0` coincided with continued `/right_controller_odom` and `/tf` publication carrying 1 distinct transform (frozen pose) for 3.9-21.3 s.

---

## Command path table

| # | Hop | Code location | What crosses |
|---|---|---|---|
| 0 | OpenXR runtime (Quest) | `Assets/XR/Settings/OpenXRPackageSettings.asset`: Android-enabled `OculusTouchControllerProfile Android` (block @1378), `MetaQuestFeature Android` (@1043), `HandTracking Android` (@239), `MetaHandTrackingAim Android` (@1088). Touch Plus/Pro and HandInteraction profiles are disabled for Android. | `xrSyncActions`/`xrLocateSpace` results inside the Unity OpenXR plugin: NOT_VERIFIED (wrapper boundary) |
| 1 | Input System devices/actions (pose) | `Assets/Samples/.../Starter Assets/XRI Default Input Actions.inputactions`, map "XRI Left" @327: `Position` (Value) bindings `<XRController>{LeftHand}/pointerPosition` :516, `/devicePosition` :527, `<XRHandDevice>{LeftHand}/devicePosition` :538. `Rotation` :472/483/494. `Tracking State` :560/:571. `MetaAimHand` :582/:626. `Is Tracked` :802/:813. The right map is symmetric @1376. | Vector3/Quaternion + `trackingState` (InputTrackingState flags) + `isTracked` |
| 2 | Input System actions (buttons) | `Assets/DataCollectionActions.inputactions:9-117` (13 Button actions), bindings :130-262 `<XRController>{Left/RightHand}/{GripButton,TriggerButton,PrimaryButton,SecondaryButton,MenuButton}` | button bits |
| 3 | XRI rig -> GameObject Transform | `.../Starter Assets/Prefabs/XR Origin (XR Rig).prefab`: Left Controller GO `&202364687` (:3-20), TPD `&6693052528577237899` (:117-185): `m_TrackingType:0`, `m_UpdateType:0`, **`m_IgnoreTrackingState:0`** (:131), `m_PositionInput`/`m_RotationInput`/`m_TrackingStateInput` -> refs into guid `c348712b...` (XRI Default Input Actions). Right Controller `&1670256624` (:186), TPD :300-339. XROrigin `m_RequestedTrackingOriginMode:0`, `m_CameraYOffset:1.36144` (:972-973). XRInputModalityManager `&5826056641483426609` (:1013-1028) `m_LeftController/m_RightController` = these GOs, with hands set in the Hands Variant (`VRTemplateAssets/Prefabs/Setup/Complete XR Origin Set Up Hands Variant.prefab:8792-8798`). | Transform pose in Unity world. The tracking state is consumed by the TPD (config) but not exposed further |
| 4 | Scene wiring | `Assets/Scenes/SampleScene.unity:1104-1145`: `RosPublishers` (`m_Script guid 9bc4be09...`), `leftController:{fileID:581284854}` -> Left Controller (:172-176 -> Hands Variant :8869 -> XR Rig :3), `rightController:{fileID:821107281}` (:372). `odomPublishFrequency: 0.016666668`. Camera Offset override yaw 90 deg, y=0 (:1914-1929). ROSConnection :1067-1090 `m_ConnectOnStart:0`, `m_KeepaliveTime:1`, `m_NetworkTimeoutSeconds:2`, `m_SleepTimeSeconds:0.01`. | references only |
| 5 | XR app publisher | `ROSPublishers.cs` `Update()` :258-341. `PublishEventIfPressed` :343-349, `PublishBoolState` :351-357, `GetRosTime` :367-380, `PublishOdomAndTf` :381-417 | `nav_msgs/Odometry{header.frame_id="quest", header.stamp, child_frame_id, pose.pose.position, pose.pose.orientation, twist=0, covariance=0}`; `tf2_msgs/TFMessage{transforms[1]: header(shared), child_frame_id, transform.translation/rotation}`; `std_msgs/Bool{data}` x10; `std_msgs/Empty{}` x10 |
| 6 | Connector (Unity side transport) | `ROSConnection.cs:998-1013` `Publish` -> `RosTopicState.cs:211-217` `Publish` -> `TopicMessageSender.cs:47-62` `Queue(message)` (by reference, queue size 10 = `ROSConnection.cs:61`). Background `ConnectionThread` `ROSConnection.cs:763-870` -> `SendInternal` :822-823 -> `TopicMessageSender.cs:109-117` `SendMessageWithStream` (serialization happens here, off the main thread) | length-prefixed `[topic][CDR bytes]` over a single TCP socket |
| 7 | Endpoint (host bridge) | `ros_tcp_endpoint/client.py:174-229` `ClientThread.run` -> `publishers_table[destination].send(data)` :213-215 -> `publisher.py:43-57` `self.pub.publish(data)` (raw serialized bytes). Registration `server.py:222-248` -> `RosPublisher(topic, cls, queue_size=10)` `publisher.py:29-41` | the same CDR bytes, republished verbatim on ROS 2 |
| 8 | ROS receiver / mapper / clutch / command | MoveIt Pro Objective "Teleop With Meta via Pose v11" (README:58-62) | NOT_VERIFIED (closed) |
| 9 | Final consumer (Servo/controller) | Unknown. Generic MoveIt Servo has `incoming_command_timeout` (`moveit2_2.12.4/moveit_ros/moveit_servo/src/servo_node.cpp:228,262,298`; `moveit2_2.5.9/.../servo_calcs.cpp:343-345`), but whether MoveIt Pro uses it on this path is NOT_VERIFIED | NOT_VERIFIED |

---

## Findings A1-A9

### A1 Focus/session and action-active state
- **SOURCE_CONFIRMED:** `ROSPublishers.cs` has no `OnApplicationFocus`, `OnApplicationPause`, XR session-state, `XRDisplaySubsystem.running` or `InputAction` active/`enabled` check. NOT_FOUND_IN_SEARCH (queries: `OnApplicationPause|OnApplicationFocus|trackingOriginUpdated|Recenter|OVRManager|OVRInput|isTracked|trackingState|onDeviceChange|InputDevices.` over `ROSPublishers.cs`). The only "Focus" hit is `TouchScreenKeyboard.Status.LostFocus` (:269-274), which concerns the IP keyboard.
- **SOURCE_CONFIRMED:** `ProjectSettings/ProjectSettings.asset:85 runInBackground: 1`, `:107 visibleInBackground: 1`. While Unity keeps ticking, `Update()` keeps publishing pose and button state with fresh stamps no matter the focus state.
- **NOT_VERIFIED:** how Unity OpenXR 1.14.3 maps OpenXR `isActive=false` when unfocused (OpenXR `input.adoc:834-841` requires `isActive=XR_FALSE` when not FOCUSED) onto `IsPressed()` and the TPD Transform.
- No focus or active-state field exists in any of the published messages (Odometry/TFMessage/Bool/Empty), so this information is dropped at hop 5.
- Host side: NOT_VERIFIED.

### A2 Valid vs tracked
- **SOURCE_CONFIRMED (config):** the TPD has `m_TrackingStateInput` bound and `m_IgnoreTrackingState: 0` (`XR Origin (XR Rig).prefab:131,156,314,339`). The action asset exposes `trackingState`/`isTracked` (`XRI Default Input Actions.inputactions:560,571,802,813`). The tracking state is consumed only by the TPD to decide whether to write the Transform.
- **NOT_VERIFIED (package source absent):** per Input System TPD semantics, the Transform is not written when the position/rotation flags are absent, which leaves the last pose in place. PRIOR_INTERNAL runtime is consistent with a frozen pose.
- **SOURCE_CONFIRMED:** `PublishOdomAndTf` reads `sourceTransform.GetPositionAndRotation` (:384) unconditionally for both controllers (:326-327). The only gates are `_registered` (:290-293) and the rate divider (:321-324). No valid/tracked bit reaches the messages: `pose.covariance` stays at default 0 and `twist` = 0 (:110-113). The OpenXR distinction between `*_VALID_BIT` and `*_TRACKED_BIT` (`spaces.adoc:220,267,716,728`) is therefore collapsed upstream (NOT_VERIFIED where) and dropped entirely at hop 5 (SOURCE_CONFIRMED).

### A3 Buttons / toggle / clutch / deadman
- **SOURCE_CONFIRMED:** the app holds no latch. Each frame it emits `Empty` on `WasPressedThisFrame()` (:343-349, press edge only, no release event) and `Bool(IsPressed())` at the odom rate (:351-357).
- **SOURCE_CONFIRMED:** while `_registered==false`, which lasts 2 s after every `ConnectAndRegister` (:166-186, `kRegistrationDelaySeconds=2.0f` :74), `Update()` returns early (:290-293), so press edges in that window are lost. They are not replayed later.
- **SOURCE_CONFIRMED:** on a TCP break the connector clears the queued messages (`ROSConnection.cs:866` `ClearMessageQueue`), so queued press edges are dropped, not delivered late.
- **AUTHOR_CLAIM:** the clutch ("grip button event/state combination") lives in MoveIt Pro (README:56-60). Where it latches and whether it resets on silence or disconnect is NOT_VERIFIED.
- **NOT_VERIFIED:** whether `IsPressed()` reads false or holds its last value when the device is lost or unfocused (Input System internals). The Bool message has no field that could tell the two apart.

### A4 Device / interaction profile / hand vs controller
- **SOURCE_CONFIRMED (config):** Android hand tracking and Meta Hand Tracking Aim are enabled (OpenXRPackageSettings @239, @1088). The pose `Position`/`Rotation` actions bind both `<XRController>` and `<XRHandDevice>` (:516-538, :472-494). The Hands Variant wires `XRInputModalityManager.m_LeftHand/m_RightHand` (`Hands Variant.prefab:8792-8798`) alongside `m_LeftController/m_RightController` (`XR Rig.prefab:1027-1028`).
- **SOURCE_CONFIRMED:** `RosPublishers` holds fixed GameObject references (`SampleScene.unity:1144-1145`) and publishes their Transform even when the GO is inactive. There is no `activeInHierarchy` check (:326-327, :384).
- **HYPOTHESIS (XRI source not local):** in hand-tracking mode the XRInputModalityManager deactivates the controller GOs. The published pose would then freeze at its last value, or follow a hand device if the TPD stays active, while the topics keep the `*_controller_odom` name.
- **SOURCE_CONFIRMED:** no device, profile or modality field is published.

### A5 Origin / recenter change
- **SOURCE_CONFIRMED:** no subscription to `XRInputSubsystem.trackingOriginUpdated`, `XrEventDataReferenceSpaceChangePending` or `OVRManager.display.RecenteredPose`. NOT_FOUND_IN_SEARCH (queries above). There is no OVR SDK in `manifest.json`.
- **SOURCE_CONFIRMED:** the published pose is Unity **world** space (`GetPositionAndRotation` :384, then `To<FLU>` :386-387, `frame_id="quest"` :105). The `quest` frame is therefore XR Origin root × Camera Offset (scene override yaw 90 deg, `SampleScene.unity:1914-1929`; y set at runtime by XROrigin, `m_RequestedTrackingOriginMode:0` = NotSpecified, `m_CameraYOffset 1.36144`) × the runtime tracking space. A recenter or origin change would appear on ROS as a pose jump with no marker. Effective time: NOT_VERIFIED.
- Host-side handling: NOT_VERIFIED.

### A6 Calibration / anchor; which transform multiplies which sample
- **SOURCE_CONFIRMED:** the app applies no calibration. The only transform is the fixed basis change `CoordinateSpaceExtensions.To<FLU>` (:386-387). The comment at :391-393 says consumers apply their own change of basis (AUTHOR_CLAIM about the host).
- **SOURCE_CONFIRMED:** the TF and Odometry carry the same pose with a publish-time stamp (`GetRosTime()` = `DateTime.UtcNow`, :367-380, :394). The stamp is taken when `Update()` runs, not at the XR sample/display time, and it comes from the Quest wall clock with no host clock sync in the repo.
- How MoveIt Pro composes `quest -> *_controller_odom` with the EE (e.g. a `tf` lookup with `Time(0)` vs at the stamp, or snapshot at engage) is NOT_VERIFIED.
- Re-anchoring on engage is described as "snap initial poses, apply controller delta" (README:58, AUTHOR_CLAIM). It is a known application-level pattern and is not novel.

### A7 Disconnect/reconnect, pause/resume
- **SOURCE_CONFIRMED (connector 0.7.0):** on a socket error, `ConnectionThread` waits 1 s (`ROSConnection.cs:853-855`), clears queues and deregisters (:857-868), then reconnects in a loop and re-sends registrations (`OnConnectionStartedCallback` :522-534 -> `RosTopicState.cs:256-265`). Keepalive is 1 s and read timeout 2 s (scene :1082-1083). `OnApplicationQuit -> Disconnect` (:950-953).
- **SOURCE_CONFIRMED:** the app's 2 s registration gate applies only to user-initiated `ConnectAndRegister` (:166-186). Background reconnects are ungated, which matches the README "Known limitations" (AUTHOR_CLAIM, consistent with code).
- **SOURCE_CONFIRMED (endpoint):** on disconnect, `client.py:224-229` closes the socket and logs. `publishers_table` (`server.py:68`) is **not** cleared, so the ROS publishers stay alive and simply stop publishing. No "source lost" message is emitted on ROS.
- **SOURCE_CONFIRMED:** `RosPublishers` has no pause/resume hook (A1).
- Host staleness detection: NOT_VERIFIED. Generic Servo has `incoming_command_timeout` (cited above), but whether it is on this path is NOT_VERIFIED.

### A8 Pending commands / previous goal / auto-resume
- **SOURCE_CONFIRMED:** the frontend sends no goals. Connector queues are size 10 per topic with drop-oldest (`TopicMessageSender.cs:47-62`) and are cleared on connection loss (`ROSConnection.cs:866`). `latch` defaults false, so `PrepareLatchMessage` (:120-127) does not run and stale replay after reconnect is not expected at transport level.
- **SOURCE_CONFIRMED (new structural issue):** messages are queued **by reference** (`RosTopicState.cs:215`) and serialized later on the `ConnectionThread` (`TopicMessageSender.cs:109-117`, called from `ROSConnection.cs:822-823`). `RosPublishers` reuses one mutable `_odomMsg`/`_odomHeader`/`_tfMessage` instance for **both** controllers (:80-95, :103-127, :394-416). It mutates `child_frame_id` and the pose between consecutive `Publish` calls with no lock. The code comments at :76-79 and :389-390 ("serializes synchronously inside Publish(), so reuse is safe") are AUTHOR_CLAIMs contradicted by the pinned connector source.
- **HYPOTHESIS (runtime):** this can produce a `/left_controller_odom` message carrying the right pose and/or `child_frame_id=right_controller_odom`, torn poses, or repeated identical messages when several references sit in a queue. Frequency is unmeasured.
- Auto-resume of a teleop session after reconnect or refocus depends on MoveIt Pro: NOT_VERIFIED.

### A9 Traceability (consumed command -> source sample)
- **SOURCE_CONFIRMED:** there are no sequence ids. Odometry and TF share one `HeaderMsg` (:124), so they get an identical stamp per controller call. `Bool` and `Empty` carry no stamp at all. The stamp is publish-time Quest wall clock (A6). The endpoint republishes the bytes verbatim (`publisher.py:57`) and adds no receive stamp.
- A press edge cannot be tied to a specific pose sample except by arrival order on separate topics.
- The host's linkage from command to source: NOT_VERIFIED.

---

## Information-delivery table

Hops: H1 OpenXR/Unity plugin -> H2 Input System action -> H3 XRI TPD/Transform -> H5 RosPublishers -> H6 Connector -> H7 Endpoint -> H8 MoveIt Pro.

| Evidence | H1 | H2 | H3 | H5 | H6/H7 | H8 |
|---|---|---|---|---|---|---|
| Pose (pos/rot) | read (NV) | read (SC config) | written to Transform (SC config) | read world Transform (SC) | forwarded (SC; by-ref race HYP) | consumed (AC) |
| VALID vs TRACKED bits | read (NV) | `trackingState`/`isTracked` bound (SC) | consumed to gate write (SC config; semantics NV) | **not-read / dropped** (SC) | n/a | NV |
| Session focus / action isActive | read (NV) | NV | NV | **not-read** (SC) | n/a | NV |
| Button pressed | read (NV) | read (SC) | n/a | forwarded as Bool + press-edge Empty (SC) | forwarded; dropped on disconnect / gate window (SC) | consumed (AC) |
| Button release edge | NV | available | n/a | **not forwarded as event** (SC; only via Bool) | n/a | NV |
| Device / profile / hand-vs-controller | read (NV) | multiple bindings (SC) | ModalityManager toggles GO (HYP) | **not-read / dropped** (SC) | n/a | NV |
| Recenter / origin change | NV | n/a | applied implicitly to Transform (NV) | **not-read** (SC) | n/a | NV |
| Sample time | NV | NV | NV | **replaced by publish-time UtcNow** (SC) | forwarded verbatim (SC) | NV |
| Sequence id | n/a | n/a | n/a | **not produced** (SC) | none (SC) | NV |
| Connection lost | n/a | n/a | n/a | not-read (SC) | handled internally (reconnect + queue clear) but **not signalled to ROS** (SC) | NV |

SC=SOURCE_CONFIRMED, AC=AUTHOR_CLAIM, HYP=HYPOTHESIS, NV=NOT_VERIFIED.

---

## Candidate matrix rows

| Item | Class candidate | Label |
|---|---|---|
| Tracking state consumed by TPD but dropped before Odometry/TF; untracked pose continues to publish (`ROSPublishers.cs:326-327,384`; `XR Rig.prefab:131,156`) | METADATA | SOURCE_CONFIRMED (runtime: PRIOR_INTERNAL) |
| No focus/pause/session gate, `runInBackground:1` (`ProjectSettings.asset:85`; `ROSPublishers.cs:258-341`) | INTEGRATION | SOURCE_CONFIRMED (Unity mapping of isActive NV) |
| Stamp = publish-time Quest `DateTime.UtcNow`, not sample time; Bool/Empty unstamped; no seq (`:367-380,:394,:343-357`) | OBSERVATION | SOURCE_CONFIRMED |
| Shared mutable message instance queued by reference and serialized off-thread; comment claims sync serialization (`ROSPublishers.cs:76-79,389-390,394-416`; `RosTopicState.cs:215`; `TopicMessageSender.cs:109-117`; `ROSConnection.cs:822-823`) | IMPLEMENTATION | SOURCE_CONFIRMED (structure); cross-topic corruption at runtime HYPOTHESIS |
| No recenter/origin-change handling; world-space pose includes XR Origin/Camera Offset (`:384`, `SampleScene.unity:1914-1929`) | PLACEMENT | SOURCE_CONFIRMED (effect timing NV) |
| Hand-vs-controller modality: fixed GO refs, inactive-GO pose still published, no modality field (`SampleScene.unity:1144-1145`; `Hands Variant.prefab:8792-8798`) | INTEGRATION | SOURCE_CONFIRMED config / HYPOTHESIS runtime |
| Press edges lost during 2 s registration gate and on TCP reset; no release edge (`:290-293`, `ROSConnection.cs:866`) | IMPLEMENTATION | SOURCE_CONFIRMED |
| Endpoint keeps ROS publishers alive after Unity disconnect; no loss signal (`client.py:224-229`, `server.py:68`) | INTEGRATION | SOURCE_CONFIRMED (endpoint @54c1a64; pairing assumed) |
| Clutch/deadman, re-anchor on engage, timeout and auto-resume all in MoveIt Pro (README:56-62) | APPLICATION | AUTHOR_CLAIM / NOT_VERIFIED (re-anchor-on-engage is a known app-level pattern, not novel) |
| Transport-level stale replay after reconnect | IMPLEMENTATION | SOURCE_CONFIRMED **not present** (queues cleared, latch=false) |
