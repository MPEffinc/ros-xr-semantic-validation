# Docker_Teleop simulator-only baseline

- Framework revision: `64cbdde88bc52c6a80d37f994752e50f95ba537e`
- Environment: disposable x86_64 `docker-teleop-humble:local`, isolated Docker bridge network, read-only pinned `src/` and `simulation/` mounts.
- Adaptations: only `DEBIAN_FRONTEND=noninteractive` and ownership of `/home/noah/ws_moveit`; upstream semantic/control source is unchanged.

## Safety audit

Executed path: `simulation/launch/run_tabletop_sim.sh` followed by `servo_test_config/launch/servo_gz.launch.py`.

- `run_tabletop_sim.sh` uses `ros_gz_sim`, `ros_gz_bridge`, `robot_state_publisher`, and Gazebo controller spawners.
- `servo_gz.launch.py` starts `joint_states_filter` and `moveit_servo/servo_node_main` with `sim_ignition:=true`.
- Neither file references `ur_robot_driver` or `robot_ip`.
- `servo_test.launch.py` does reference both and was not executed.

## Observed startup

The isolated run spawned `ur5e_hande` in `ur_hande_tabletop`.  `joint_state_broadcaster`, `joint_group_velocity_controller`, and `hande_position_controller` were all `active`.  Active ROS nodes included `/servo_node`, `/joint_states_filter`, `/controller_manager`, `/gz_ros2_control`, `/robot_state_publisher`, and `/ros_gz_bridge`.

This is a simulator-only readiness result, not a teleoperation consequence result.  Next: start the unmodified production receiver, mapper, and servo bridge in this session, then execute the controlled D1/D2 pair.
