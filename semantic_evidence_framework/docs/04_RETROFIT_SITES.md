# 04 — Where each recurring requirement must be retrofitted, per implementation

Source: audits A1–A6. Every cell is SOURCE_CONFIRMED at the audited commit unless it is marked `?`.
This table is the input to brief §8, condition 2: "manual retrofits need implementation-specific,
repeated edits".

## Recurring requirements (each seen in at least 3 structurally different implementations)

In the column "Implementations where it is unmet", *unmet* refers to the ROS-facing interface (wire
and consumer). It does not mean the app failed to read an available field. See `06_CLAIM_SCOPE_CORRECTION.md`.

| R | Requirement | Implementations where it is unmet |
|---|---|---|
| R1 | Deliver the tracked state (not just valid or connected) per sample | all 6 |
| R2 | Deliver input activity or focus, and the cause of an interruption | all 6 (R0 shows the real-device consequence for PickNik) |
| R3 | Deliver the recenter or origin epoch with its effective time | all 6 (ALVR drops `changeTime`; the others have no handler) |
| R4 | Deliver per-sample device identity, bound to the command | 6/6 implicit (topic, label or role). R0 shows that it broke in practice. |
| R5 | Deliver the source sample time | 6/6 restamp or drop it |
| R6 | Consumer-side stop and re-arm keyed to R1–R3 | 0/6 complete. Docker_Teleop has receive-time freshness and re-anchoring. |

## Where the edit has to happen

| Implementation | Source-side site (where the evidence exists) | Wire format change | ROS-side site | Can the ROS side alone meet R1–R3? |
|---|---|---|---|---|
| OpenVR UR5e + ALVR | ALVR client `interaction.rs` (buttons, flags), `lib.rs` (events) | ALVR protocol, then the SteamVR driver. **OpenVR has no field for "inactive" or "epoch"**: the legacy pose struct is fixed. | `quest_teleop.py` (one node) | **No.** The cause is collapsed into `bPoseIsValid` (P1 C2/C3). |
| Quest2ROS2 | closed APK | custom `OVR2ROSInputs` msg | `BaseArmController` (Python) | No. There are no fields. |
| PickNik | `ROSPublishers.cs` (Unity) | `nav_msgs/Odometry` has no slot. A new topic or msg is needed. | closed MoveIt Pro objective (`?`) | No (and the host is NOT_VERIFIED). |
| Spes | `index.html` (WebXR JS) | JSON packet | `teleop/__init__.py` | No. |
| Docker_Teleop | `HandPoseSender.cs` (Unity/OVR) | newline JSON | receiver, mapper and bridge (3 Python nodes) | Partly. Freshness is enforced, but the "tracked" bool means connected. |
| OpenArmX | closed APK | UDP text packet | C++ bridge + Python node | No. |

## Observations

1. **Six implementations give five different transport formats and five different ROS-side code
   sites.** Delivery would also require the frontend to *read* the field first, which is confirmed
   absent or not found in most open frontends. Each edit to deliver R1–R3 lands in different code. The S5 conclusion (PRIOR_INTERNAL) was
   that once the evidence is delivered, the ROS-side check is a few lines. So the repeated cost is in
   *delivery and linking*, not in the check.
2. **Two of the six frontends are closed binaries** (Quest2ROS2, OpenArmX), and PickNik's host is
   closed. For these, any defense that needs source-side evidence must either get vendor cooperation
   or use an independent evidence path, for example a second OpenXR or OpenVR client, or the runtime's
   own API. **Self-reported app fields cannot provide such a path** (A3 threat class; brief §8).
3. **OpenVR legacy cannot carry R2 or R3 at all.** The API struct has no slot for them, so a source
   change alone does not fix it on that path. A side channel is needed. In P1 this is modelled as
   `xr_evidence()`, which is explicitly not OpenVR.
4. These observations make §8 condition 1 (recurrence) and condition 2 (implementation-specific
   repeated edits) **plausible from source**. Condition 3 has not been shown: that a common model gives
   the same guarantee with fewer edits or lower latency/false blocks. P1 tests only the ROS-side half on
   one path.
