#!/usr/bin/env bash
# Diagnostic bring-up: why does servo_node stall at "Waiting to receive robot state update"?
set -o pipefail
out="${1:-/ws/results/diag}"
mkdir -p "${out}"
source /opt/ros/jazzy/setup.bash
source /ws/install/setup.bash
export ROS_DOMAIN_ID="${ROS_DOMAIN_ID:-98}"
export GZ_SIM_RESOURCE_PATH="/ws/install/ur5_description/share:${GZ_SIM_RESOURCE_PATH:-}"

cleanup() {
  pkill -KILL -f 'gz sim'; pkill -KILL -f ruby; pkill -KILL -f servo_node
  pkill -KILL -f ros2_control_node; pkill -KILL -f component_container; sleep 2
}
trap cleanup EXIT

setsid xvfb-run -a ros2 launch ur5_description gazebo.launch.py >"${out}/gazebo.log" 2>&1 &
until ros2 topic list 2>/dev/null | grep -qx '/joint_states'; do sleep 2; done
setsid ros2 launch ur5_controller controller.launch.py is_sim:=True >"${out}/controller.log" 2>&1 &
until ros2 control list_controllers 2>/dev/null | grep -q 'ur5_arm_controller.*active'; do sleep 2; done
setsid ros2 launch ur5_moveit_config ur5_servo.launch.py >"${out}/servo.log" 2>&1 &
until ros2 node list 2>/dev/null | grep -q '/servo_node'; do sleep 2; done
sleep 10

{
  echo "### /clock rate (5s) ###"
  timeout 6 ros2 topic hz /clock 2>&1 | head -5
  echo "### /clock sample ###"
  timeout 6 ros2 topic echo /clock --once 2>&1 | head -10
  echo "### /joint_states sample ###"
  timeout 6 ros2 topic echo /joint_states --once 2>&1 | head -20
  echo "### servo_node use_sim_time ###"
  ros2 param get /servo_node use_sim_time 2>&1
  echo "### robot model joints (srdf group) ###"
  ros2 param get /servo_node moveit_servo.move_group_name 2>&1
  echo "### robot_description present on servo_node ###"
  ros2 param get /servo_node robot_description 2>&1 | head -c 300; echo
  echo "### /tf sample ###"
  timeout 6 ros2 topic echo /tf --once 2>&1 | head -20
  echo "### node list ###"
  ros2 node list 2>&1
} >"${out}/diag.txt" 2>&1

echo "[diag] done"
