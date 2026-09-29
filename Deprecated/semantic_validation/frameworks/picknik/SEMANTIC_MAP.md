# PickNik semantic map

| Invariant / transition | Native/raw observation | Canonical mapping | Publisher treatment | Result boundary |
| --- | --- | --- | --- | --- |
| I1 / T1 | `trackingState` and `isTracked` reach controller Transform driver | `IMPLEMENTATION_INFERRED` | publisher reads only Transform; ROS has no tracking field/gate | `DROPPED` at publisher boundary, E1 |
| I2 / T2 | left/right actions/topics/child frames separate | `IMPLEMENTATION_INFERRED` | handedness preserved; controller-vs-hand modality absent | `PARTIAL`, E1 |
| I3 / T3 | no source sample time reaches publisher | `DIRECT` omission | `GetRosTime()` regenerates wall-clock stamp | `DROPPED`, E1 |
| I4 / T4 | connector reconnect/re-registration exists | `IMPLEMENTATION_INFERRED` | no XR session/generation payload field | `UNKNOWN`, E1 |
| I5 / T5/T6 | no inspected lifecycle signal feeds publisher | `UNMAPPED` | no re-arm contract found | `UNKNOWN`, E1 |

Source-validator `PASS` is not Unity, Quest, ROS, Pi or MoveIt Pro runtime evidence.
