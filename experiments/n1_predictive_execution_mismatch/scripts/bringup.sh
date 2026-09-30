#!/usr/bin/env bash
# Long-lived bring-up of the pinned UR5 stack (Gazebo + ros2_control + MoveIt Servo) inside the n1sim
# container. Adapted (copied, not edited) from
# Deprecated/semantic_validation/harness/openvr_ur5e_downstream/run_trial.sh; pinned launch files unmodified.
# Usage (inside container): bash /scripts/bringup.sh <logdir>
set -o pipefail
logdir="${1:-/results/raw/bringup}"; mkdir -p "$logdir"
source /opt/ros/jazzy/setup.bash; source /ws/install/setup.bash
export GZ_SIM_RESOURCE_PATH="/ws/install/ur5_description/share:${GZ_SIM_RESOURCE_PATH:-}"
setsid xvfb-run -a ros2 launch ur5_description gazebo.launch.py >"$logdir/gazebo.log" 2>&1 &
d=$((SECONDS+150)); until ros2 topic list 2>/dev/null | grep -qx /joint_states; do [ $SECONDS -ge $d ] && { echo FAIL_JOINT_STATES; exit 10; }; sleep 2; done
setsid ros2 launch ur5_controller controller.launch.py is_sim:=True >"$logdir/controller.log" 2>&1 &
d=$((SECONDS+120)); until ros2 control list_controllers 2>/dev/null | grep -q 'ur5_arm_controller.*active'; do [ $SECONDS -ge $d ] && { echo FAIL_CONTROLLER; exit 11; }; sleep 2; done
setsid ros2 launch ur5_moveit_config ur5_servo.launch.py >"$logdir/servo.log" 2>&1 &
d=$((SECONDS+120)); until ros2 node list 2>/dev/null | grep -q /servo_node; do [ $SECONDS -ge $d ] && { echo FAIL_SERVO; exit 12; }; sleep 2; done
sleep 8
timeout 20 ros2 service call /servo_node/switch_command_type moveit_msgs/srv/ServoCommandType "{command_type: 1}" >"$logdir/switch.log" 2>&1
ros2 node list >"$logdir/nodes.txt"; ros2 topic list -t >"$logdir/topics.txt"
echo BRINGUP_OK
