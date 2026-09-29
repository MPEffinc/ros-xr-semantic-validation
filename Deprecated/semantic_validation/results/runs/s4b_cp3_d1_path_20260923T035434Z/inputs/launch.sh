#!/bin/bash
set -eo pipefail
export TRIAL_ROOT=/results
mkdir -p /results/stdout /results/stderr
export PYTHONPATH=/code:${PYTHONPATH:-}
source /opt/ros/$ROS_DISTRO/setup.bash
pids=()
start() {
  label=$1; shift
  "$@" > /results/stdout/$label.log 2> /results/stderr/$label.log &
  pids+=($!)
}
if [ "$STACK" = docker ]; then
  source /home/noah/ws_moveit/install/setup.bash
  export IGN_GAZEBO_SYSTEM_PLUGIN_PATH=/opt/ros/humble/lib
  export IGN_GAZEBO_RESOURCE_PATH=/home/noah/ws_moveit/install/robotiq_hande_description/share:/home/noah/ws_moveit/install/ur_hande_description/share:/opt/ros/humble/share
  start gazebo ign gazebo -s -r /home/noah/ws_moveit/simulation/worlds/ur_hande_tabletop.sdf
  sleep 3
  start clock ros2 run ros_gz_bridge parameter_bridge '/clock@rosgraph_msgs/msg/Clock[ignition.msgs.Clock'
  xacro /home/noah/ws_moveit/src/ur_hande_description/urdf/ur_hande.urdf.xacro ur_type:=ur5e name:=ur5e use_fake_hardware:=false sim_ignition:=true sim_gazebo:=false initial_positions_file:=/home/noah/ws_moveit/src/ur_hande_description/config/initial_positions.yaml simulation_controllers:=/home/noah/ws_moveit/simulation/config/ur5e_gz_controllers.yaml > /results/robot.urdf
  start rsp ros2 run robot_state_publisher robot_state_publisher /results/robot.urdf
  timeout 30 ros2 run ros_gz_sim create -world ur_hande_tabletop -name closure_arm -file /results/robot.urdf > /results/stdout/spawn.log 2>&1
  for c in joint_state_broadcaster joint_group_velocity_controller hande_position_controller; do
    timeout 30 ros2 run controller_manager spawner "$c" --controller-manager /controller_manager -p /home/noah/ws_moveit/simulation/config/ur5e_gz_controllers.yaml >> /results/stdout/controllers.log 2>&1
  done
  if [ "$MODE" = b0 ]; then
    start servo ros2 launch servo_test_config servo_gz.launch.py
  else
    start servo env LD_PRELOAD=/code/libservo_payload_humble.so XR_SERVO_HOOK_LOG=/results/servo_callback_payload.jsonl ros2 launch servo_test_config servo_gz.launch.py
  fi
  sleep 4
  if [ "$MODE" = b0 ]; then
    start receiver ros2 run receiver quest_controller_receiver
    start mapper ros2 run teleop_bridge hand_pose_mapper
    start bridge ros2 run teleop_bridge servo_command_bridge
  else
    if [ "$MODE" = b2 ]; then
      source /monitor_ws/install/setup.bash
      export PYTHONPATH=/code:/d1deps:${PYTHONPATH:-}
      export XR_D1_PROPERTY_LOG=/results/property.jsonl
      if [ "$INFO_REGIME" = full ]; then
        monitor_id=d1_full_guard
        oracle_port=18841
      else
        monitor_id=d1_native_guard
        oracle_port=18842
      fi
      start oracle python3 -u /official/oracle/TLOracle/oracle.py --online --discrete --property d1_tloracle_property --port "$oracle_port"
      start monitor ros2 run monitor "$monitor_id"
    fi
    start observed python3 /code/d1_nodes.py
  fi
  sleep 2
  ros2 control list_controllers > /results/controllers.txt
  ros2 node list > /results/nodes.txt
  ros2 service list -t > /results/services.txt
  touch /results/production.ready
  start sender python3 /code/d1_sender.py
else
  source /ws/install/setup.bash
  if [ "$MODE" != b0 ]; then source /observer/install/local_setup.bash; fi
  export GZ_SIM_RESOURCE_PATH=/ws/install/ur5_description/share:${GZ_SIM_RESOURCE_PATH:-}
  start gazebo xvfb-run -a ros2 launch ur5_description gazebo.launch.py
  timeout 120 bash -c 'until ros2 topic list | grep -qx /joint_states; do sleep 2; done'
  start controller ros2 launch ur5_controller controller.launch.py is_sim:=True
  timeout 90 bash -c 'until ros2 control list_controllers | grep -q "ur5_arm_controller.*active"; do sleep 2; done'
  if [ "$MODE" = b0 ]; then
    start servo ros2 launch ur5_moveit_config ur5_servo.launch.py
  else
    start servo env XR_SERVO_CALLBACK_LOG=/results/servo_callback_overlay.jsonl ros2 launch ur5_moveit_config ur5_servo.launch.py
  fi
  timeout 90 bash -c 'until ros2 service list | grep -q /servo_node/switch_command_type; do sleep 2; done'
  ros2 service call /servo_node/switch_command_type moveit_msgs/srv/ServoCommandType '{command_type: 2}' > /results/servo_mode.txt
  ros2 control list_controllers > /results/controllers.txt
  ros2 service list -t > /results/services.txt
  start production python3 /code/openvr_production.py
fi
python3 /code/d1_probe.py > /results/stdout/probe.log 2> /results/stderr/probe.log
