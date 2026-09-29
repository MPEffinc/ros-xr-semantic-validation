#!/usr/bin/env bash
# S2-only launcher.  It intentionally avoids run_tabletop_sim.sh because that
# helper kills broad process names.  This script starts only processes owned by
# the dedicated S2 container and never launches servo_test.launch.py.
set -euo pipefail

# Humble's generated setup scripts reference optional variables under `set -u`.
set +u
source /opt/ros/humble/setup.bash
source /home/noah/ws_moveit/install/setup.bash
set -u

RESULT_ROOT=/results
RUN_LABEL="${RUN_LABEL:-runtime_default}"
LOG_ROOT="${RESULT_ROOT}/${RUN_LABEL}"
mkdir -p "${LOG_ROOT}/stdout" "${LOG_ROOT}/stderr" "${LOG_ROOT}/bags" "${LOG_ROOT}/summaries"
export IGN_GAZEBO_SYSTEM_PLUGIN_PATH="/opt/ros/humble/lib:${IGN_GAZEBO_SYSTEM_PLUGIN_PATH:-}"
export IGN_GAZEBO_RESOURCE_PATH="/home/noah/ws_moveit/install/robotiq_hande_description/share:/home/noah/ws_moveit/install/ur_hande_description/share:/opt/ros/humble/share:${IGN_GAZEBO_RESOURCE_PATH:-}"

start_bg() {
  local label="$1"
  shift
  "$@" >"${LOG_ROOT}/stdout/${label}.stdout" 2>"${LOG_ROOT}/stderr/${label}.stderr" &
  echo "$! ${label}" >>"${LOG_ROOT}/summaries/owned_pids.txt"
}

start_bg gazebo ign gazebo -s -r /home/noah/ws_moveit/simulation/worlds/ur_hande_tabletop.sdf
sleep 3
start_bg clock_bridge ros2 run ros_gz_bridge parameter_bridge '/clock@rosgraph_msgs/msg/Clock[ignition.msgs.Clock'
sleep 1

xacro /home/noah/ws_moveit/src/ur_hande_description/urdf/ur_hande.urdf.xacro \
  ur_type:=ur5e name:=ur5e use_fake_hardware:=false sim_ignition:=true sim_gazebo:=false \
  initial_positions_file:=/home/noah/ws_moveit/src/ur_hande_description/config/initial_positions.yaml \
  simulation_controllers:=/home/noah/ws_moveit/simulation/config/ur5e_gz_controllers.yaml \
  >/tmp/s2_ur5e_hande_tabletop.urdf
start_bg robot_state_publisher ros2 run robot_state_publisher robot_state_publisher /tmp/s2_ur5e_hande_tabletop.urdf

timeout 30 ros2 run ros_gz_sim create -world ur_hande_tabletop -name s2_ur5e_hande -file /tmp/s2_ur5e_hande_tabletop.urdf -x 0.0 -y 0.0 -z 0.0 \
  >"${LOG_ROOT}/stdout/create.stdout" 2>"${LOG_ROOT}/stderr/create.stderr"

for controller in joint_state_broadcaster joint_group_velocity_controller hande_position_controller; do
  timeout 30 ros2 run controller_manager spawner "$controller" --controller-manager /controller_manager \
    -p /home/noah/ws_moveit/simulation/config/ur5e_gz_controllers.yaml \
    >"${LOG_ROOT}/stdout/spawn_${controller}.stdout" 2>"${LOG_ROOT}/stderr/spawn_${controller}.stderr"
done

start_bg servo_gz ros2 launch servo_test_config servo_gz.launch.py
sleep 4
start_bg receiver ros2 run receiver quest_controller_receiver --ros-args -p listen_port:=5005
start_bg mapper ros2 run teleop_bridge hand_pose_mapper
start_bg bridge ros2 run teleop_bridge servo_command_bridge
sleep 3

start_bg bag_record ros2 bag record -o "${LOG_ROOT}/bags/${BAG_NAME:-s2_docker_bag}" \
  /received_pose_states /target_twist_states /servo_node/delta_twist_cmds /joint_states \
  /joint_group_velocity_controller/commands /servo_node/status

echo 'S2_GAZEBO_ONLY_READY' | tee "${LOG_ROOT}/summaries/start_ready.txt"
