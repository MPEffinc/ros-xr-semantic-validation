# Legged source map and limitation

The pinned tree was audited from a temporary Git object checkout because the large normal clone
was incomplete; the exact commit above is available and source reads were from that commit.

| Chain stage | Pinned source | Observed boundary |
| --- | --- | --- |
| Native hand source | `Assets/RSL/Telemetry/Hands/Scripts/HandPub.cs:90-108,183-262` | running `XRHandSubsystem.updatedHands` invokes `OnHandUpdate`; right `hand.isTracked` gates landmark/point-cloud publication, and optional `_highConfidence` gates zero success flags. |
| Representation | `HandPub.cs:194-260` | joint poses become MANO landmarks/PointCloud with frame ID; raw `isTracked`, update flags and source timestamp are not serialized. |
| Other XR telemetry | `HeadsetPublisher.cs:79-150` | Unity InputAction values become PoseStamped/TF; default zero quaternion is replaced with identity. |
| ROS transport | `Packages/manifest.json`; `Core/Menu/ROSManager/Scripts/ROSManager.cs` | project uses ROS-TCP Connector; IP/port reconnect code is source-visible. |
| Downstream control | no connected original robot-control consumer found | telemetry-to-robot-control chain is `SOURCE_PATH_UNCONFIRMED`. |

`Assets/Scenes/Main.unity` references `HandPub`, but the native downstream control path is not
established merely by that telemetry scene linkage.
