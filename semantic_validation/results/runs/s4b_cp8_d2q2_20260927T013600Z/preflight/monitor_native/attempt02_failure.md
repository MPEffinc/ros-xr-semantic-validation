Pre-freeze component attempt 02: container exited 1 before monitor/oracle start.
ROS setup emitted missing install-relative `build/` and package `local_setup.bash` paths; Python then raised `ModuleNotFoundError: No module named 'teleop_bridge_msgs'`.
Cause: the host-only container mounted the reused workspace `install/` but omitted its read-only `build/` and vendor `src/` mounts used in qualified Q4 launch.
Next environment correction: add those exact read-only mounts. No policy, fixture, official monitor or vendor source change; no ROS event or Gazebo run occurred.
