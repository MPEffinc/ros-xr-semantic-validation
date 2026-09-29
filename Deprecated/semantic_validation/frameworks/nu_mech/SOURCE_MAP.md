# NU-MECH source map

Pinned repository: `NU-MECH-ENG-495/vr-hand-tracking@8b685f91727bba98cd28322f296fef30c3173309`.

| Stage | Connected source path | Observed behavior |
| --- | --- | --- |
| Unity hand callback | `UnityProject/Assets/HandTracking.cs:32-45` | A same-GameObject `Oculus.Interaction.Input.IHand` is required and `WhenHandUpdated` is subscribed. Scene/prefab linkage still needs Unity-editor verification. |
| Native validity decision | `HandTracking.cs:70-95` | `IsTrackedDataValid=false` returns before joint extraction and UDP send; failed `GetJointPosesLocal` also sends nothing. |
| Representation | `HandTracking.cs:78-90,102-188` | Local joint rotations become selected flexion/adduction angles. Raw validity, confidence, joint validity, source time and update/frame ID are not serialized. `handSide` survives only as formatted text. |
| Transport | `HandTracking.cs:25-27,44-45,216-225` | UTF-8 text is sent by UDP to configured address/port 9000. |
| ROS boundary | `src/hand_tracking_quest/src/HandTrackerQuest.cpp:38-55,87-121` | UDP text is regex-parsed and emitted as `hand_joint_angles` `Float32MultiArray`; no header, validity, handedness, source time, or frame is retained. |
| Consumer | `launch/hand.launch.xml:3-10` | The linked launch starts receiver plus Qt visualizer. No robot-hand/control subscriber is connected. |

This is E1 source/dataflow only. It is not a Quest runtime result.
