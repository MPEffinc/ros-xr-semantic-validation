#!/usr/bin/env bash
# Restart only servo_node with moveit_servo overrides (JSON); used for condition E (smoothing) and to restore.
# Usage (inside container): servo_swap.sh '<json overrides>' <logfile>
source /opt/ros/jazzy/setup.bash; source /ws/install/setup.bash
pkill -INT -f 'moveit_servo/servo_node' ; sleep 3; pkill -KILL -f 'moveit_servo/servo_node'; sleep 1
N1_SERVO_OVERRIDES="$1" setsid ros2 launch /scripts/ur5_servo_variant.launch.py >"$2" 2>&1 &
d=$((SECONDS+60)); until ros2 service list 2>/dev/null | grep -q /servo_node/switch_command_type; do [ $SECONDS -ge $d ] && { echo SWAP_FAIL; exit 1; }; sleep 1; done
sleep 3; timeout 20 ros2 service call /servo_node/switch_command_type moveit_msgs/srv/ServoCommandType "{command_type: 1}" | grep -q "success=True" && echo SWAP_OK
