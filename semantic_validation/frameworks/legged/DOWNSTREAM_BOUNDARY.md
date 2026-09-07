# Legged downstream boundary

Current source audit reaches XR hand/head telemetry and ROS-TCP registration only. Robot models
and ROS packages are separately referenced dependencies, and no original controller callback,
control decision, pre-write stub, or Pi integration is connected. Consequence is `UNKNOWN`; Pi
reception would still be only `PI_RECEIVED`.
