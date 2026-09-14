# XRoboToolkit inert SDK substitute

Not upstream code. These files exist so that the **unmodified** upstream
translation unit `ros2/picoxr/src/publisher.cpp` can be compiled and executed in
a robot-free, network-free container.

- `PXREARobotSDK.h` — declares only the symbols `publisher.cpp` uses, inferred
  from its call sites. Contains no PICO code.
- `pxrea_stub.cpp` — `PXREAInit` starts one thread that replays newline-delimited
  synthetic device-state JSON records from the file named by `XRT_SYNTHETIC_JSON`
  into the upstream callback. It performs **no** device discovery, opens **no**
  socket, and can reach **no** headset or robot.
- `xr_msgs_inject.cmake` — injected via `CMAKE_PROJECT_xr_msgs_INCLUDE`. Upstream
  `ros2/xr_msgs/CMakeLists.txt` calls `rosidl_generate_interfaces()` but only does
  `find_package(rosidl_generator_cpp)`, which does not define that macro on ROS 2
  Jazzy; the missing `find_package(rosidl_default_generators)` is supplied here
  rather than by editing upstream source.
- `build_stub.sh` — installs the header and builds the `.so` at the exact path
  upstream's `CMakeLists.txt` probes (`/opt/apps/picobusinesssuite/SDK/clientso/64`).

Without the substitute the upstream build fails hard; that failure is the
`BLOCKED_EXTERNAL_DEPENDENCY` half of the evidence and is captured verbatim in
`results/runs/xrobotoolkit_*/attempt2_picoxr_no_sdk.log`.

Driver: `harness/xrobotoolkit_publisher_runtime.py`.
