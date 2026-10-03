#!/usr/bin/env bash
# R10 1B standalone JTC trial: Gazebo + JTC 4.42.1 only (no XR runtime, no app, no Servo). env: CFG (DECEL|HOLD) V OVERRIDE
set -o pipefail; R=/results; source /opt/ros/jazzy/setup.bash; source /ws/install/setup.bash; export ROS_DOMAIN_ID=89 ROS_LOCALHOST_ONLY=1 HOME=/tmp
export GZ_SIM_RESOURCE_PATH="/ws/install/ur5_description/share:${GZ_SIM_RESOURCE_PATH:-}"
pids=(); cleanup(){ for p in "${pids[@]}"; do kill -INT -- "-$p" 2>/dev/null; done; sleep 2; for p in "${pids[@]}"; do kill -KILL -- "-$p" 2>/dev/null; done; }
trap cleanup EXIT
wait_for(){ local d=$((SECONDS+$2)); until eval "$1" >/dev/null 2>&1; do [ $SECONDS -ge $d ] && { echo "{\"setup\":\"timeout\",\"step\":\"$3\"}" > $R/setup.json; exit 20; }; sleep 1; done; }
setsid xvfb-run -a ros2 launch ur5_description gazebo.launch.py > $R/gazebo.log 2>&1 & pids+=($!)
wait_for "ros2 service list | grep -qx /controller_manager/list_controllers" 120 cm
ros2 run controller_manager spawner joint_state_broadcaster --controller-manager /controller_manager > $R/spawn_jsb.log 2>&1
PF=""; [ "$CFG" = DECEL ] && PF="--param-file /m39s/config/jtc_decel_on_cancel.yaml"
ros2 run controller_manager spawner ur5_arm_controller --controller-manager /controller_manager $PF > $R/spawn_arm.log 2>&1
wait_for "ros2 control list_controllers | grep -q 'ur5_arm_controller.*active'" 60 controller
ros2 param get /ur5_arm_controller constraints.decelerate_on_cancel > $R/param_decel.txt 2>&1
ros2 param get /ur5_arm_controller constraints.elbow_joint.max_deceleration_on_cancel >> $R/param_decel.txt 2>&1
python3 /m39/harness/setup_start.py $R/setup_start.json $QSTART 6.0 > $R/setup_start.log 2>&1 || { echo '{"setup":"start_config_not_qualified"}' > $R/setup.json; exit 22; }
echo "{\"setup\":\"ok\",\"cfg\":\"$CFG\",\"v\":$V,\"override\":\"$OVERRIDE\",\"load\":\"$(cut -d' ' -f1-3 /proc/loadavg)\"}" > $R/setup.json
python3 /m39s/jtc_action/action_cancel.py $R/action.jsonl $V $OVERRIDE > $R/action.log 2>&1
grep -h -i "cancel\|decelerat\|hold" $R/gazebo.log | tail -20 > $R/jtc_log_excerpt.txt
echo '{"done":true}' > $R/done.json
