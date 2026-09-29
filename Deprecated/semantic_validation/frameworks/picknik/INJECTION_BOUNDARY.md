# PickNik replay injection boundary

- Relevant source: Unity Input System `trackingState`/`isTracked` actions and their controller
  Transform driver.
- Candidate packet/topic/Transform replay occurs after that source path.
- Such replay keeps only later ROS-TCP behavior and bypasses native Input System/OpenXR semantics
  and every preceding tracking decision.

Classification: **`BOUNDARY_LIMITED_REPLAY`**. No adapter is generated until a pre-gate Unity
injection can be shown without changing production behavior; the side-band logger is observer
instrumentation, not an adapter.
