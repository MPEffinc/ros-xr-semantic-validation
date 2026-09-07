# NU-MECH semantic map

| Axis | Disposition at the observed boundary |
| --- | --- |
| I1 tracking validity | `GATED` before UDP: `IsTrackedDataValid=false` returns. It is then `DISCARDED` from the UDP and ROS message. |
| I2 handedness/source | `handSide` labels the formatted text, but the ROS `Float32MultiArray` has no typed handedness field. |
| I3 source time/freshness | no source timestamp or freshness check found. |
| I4 session/generation | no session or generation representation found. |
| I5 invalidation/recovery | invalid samples are not sent; no downstream re-arm/recovery consumer contract is visible. |

`IHand.IsTrackedDataValid` must not be equated with Unity `isTracked`, Meta `IsTracked`, or OpenXR validity bits.
