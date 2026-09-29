Pre-freeze component attempt 01: container exited 1 before monitor/oracle start.
stderr: `/opt/ros/humble/setup.bash: line 8: AMENT_TRACE_SETUP_FILES: unbound variable`
Cause: new `run_monitor_preflight.sh` enabled `set -u` before sourcing ROS setup.
Correction before any freeze: use `set -eo pipefail`; no policy, fixture, monitor, or vendor change.
No ROS event, Gazebo run, or defense outcome occurred in this attempt.
