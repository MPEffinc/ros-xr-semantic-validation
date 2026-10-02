# F1 candidate 2 — NVIDIA IsaacTeleop `teleop_ros2` on Monado main (2026-10-02): INCOMPATIBLE

## Build (no source change)

- Source: IsaacTeleop `9fba23c4a3bd`, a clean copy in `results/raw/F1/isaac_build/src`.
- Base image: `f1-monado-main:045931d`.
- CMake options as in the upstream `examples/teleop_ros2/Dockerfile`, except
  `ENABLE_CLOUDXR_BUNDLE_CHECK=OFF` (the CloudXR SDK is not public) and `BUILD_PLUGINS=OFF`.
- The upstream Dockerfile itself needs BuildKit (`--mount=type=cache`, heredoc `COPY`), which this
  host's Docker lacks (no buildx).
- Two failed attempts, recorded:
  - The Python stub step failed because `pybind11-stubgen` is unpinned and 3.0.0 (released
    2026-09-25) changed `run()`. `UV_CONSTRAINT` is ignored by `uv run --project`.
  - **Fix:** the build environment sets `UV_EXCLUDE_NEWER=2026-09-20T00:00:00Z`. This is an
    environment pin, not a source change.
- **Result:** the build succeeded in about 4 minutes. It produced the wheel
  `isaacteleop-1.5+local-cp312-cp312-linux_x86_64.whl` and `teleop_ros2_interfaces`.

## Why it cannot run on Monado

| `teleop_ros2` mode | Trackers used | Required vendor extension | Source |
|---|---|---|---|
| controller_teleop, controller_teleop_with_hand_wrist_ee, controller_raw | controllers | `XR_NVX1_action_context` | `live_controller_tracker_impl.hpp` L31 |
| hand_teleop | hands + head + **Generic3AxisPedalSource** | `XR_NVX1_tensor_data` (pedal = schema tracker) | `session_config.py` L294–303; `schema_tracker_base.cpp` L61–63 |
| full_body | controllers + full body | `XR_NVX1_action_context` (+ tensor) | `session_config.py` |

**Monado main (`045931d`) instance extensions, measured** (58 in total,
`results/raw/F1/monado_main_instance_extensions.txt`): no `XR_NVX1_*` and no `XR_NV_*`. It does
offer `XR_MND_headless`, `XR_EXTX_overlay`, `XR_EXT_hand_tracking`, `XR_MNDX_xdev_space` and
`XR_KHR_convert_timespec_time`.

**Verdict.** Every `teleop_ros2` mode requests at least one NVX1 extension, which only the CloudXR
runtime provides. The app is **not Monado-compatible** as shipped. Using the `isaacteleop` library
from a script we write (hands only) would be our own client, so it is **not counted** as this app.
