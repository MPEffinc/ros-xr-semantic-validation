# AgileX semantic map

| Axis | Publicly auditable result |
| --- | --- |
| I1 / T1 | `UNMAPPED` at native source; the host treats a matrix as usable if both side entries are non-null. |
| I2 / T2 | left/right key is preserved through host source; native controller/hand/fallback identity is unknown. |
| I3 / T3 | source time is absent from logcat representation; `pub_pose` and `pub_delta_pose` create host ROS timestamps. |
| I4 / T4 | APK/ADB/session generation is not present in the representation. |
| I5 / T5/T6 | A/B is a host control flag, not evidence of native XR invalidation/re-arm. |

`python -m py_compile` passed for the four host scripts on 2026-09-07. This is syntax
integrity, not an import/runtime/ROS/Quest result.
