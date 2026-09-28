#!/bin/bash
# OpenVR trial launcher (trial-owned container only). B0 uses the vendor Servo; every
# other arm uses the CP2 observational Servo callback overlay (payload log only).
set -eo pipefail
export TRIAL_ROOT=/results
mkdir -p /results/stdout /results/stderr
source /opt/ros/jazzy/setup.bash
source /ws/install/setup.bash
if [ "$MODE" != b0 ]; then source /observer/install/local_setup.bash; fi
export PYTHONPATH=/code:/ovrdeps:${PYTHONPATH:-}
export GZ_SIM_RESOURCE_PATH=/ws/install/ur5_description/share:${GZ_SIM_RESOURCE_PATH:-}
source /code/child_supervisor.sh
pids=()
labels=()
start() {
  label=$1; shift
  python3 /code/participant_entry.py "$label" "$@" > /results/stdout/$label.log 2> /results/stderr/$label.log &
  pids+=($!)
  labels+=("$label")
}
start gazebo ros2 launch /code/ovr_gazebo.launch.py
timeout 120 bash -c 'until ros2 topic list | grep -qx /joint_states; do sleep 1; done'
timeout 120 ros2 launch ur5_controller controller.launch.py is_sim:=True > /results/stdout/controller.log 2> /results/stderr/controller.log
timeout 90 bash -c 'until ros2 control list_controllers | grep -q "ur5_arm_controller.*active"; do sleep 1; done'
if [ "$MODE" = b0 ]; then
  start servo ros2 launch ur5_moveit_config ur5_servo.launch.py
else
  start servo env XR_SERVO_CALLBACK_LOG=/results/servo_callback_overlay.jsonl ros2 launch ur5_moveit_config ur5_servo.launch.py
fi
timeout 90 bash -c 'until ros2 service list | grep -q /servo_node/switch_command_type; do sleep 1; done'
ros2 service call /servo_node/switch_command_type moveit_msgs/srv/ServoCommandType '{command_type: 2}' > /results/servo_mode.txt
ros2 control list_controllers > /results/controllers.txt
ros2 service list -t > /results/services.txt
if [ "$MODE" = b2 ]; then
  source /monitor_ws/install/setup.bash
  export XR_D3_PROPERTY_LOG=/results/property.jsonl
  echo 18851 > /results/oracle.port
  if [ "${CMON_FAULT:-}" != ORACLE_ABSENT ]; then
    start oracle python3 -u /official/oracle/TLOracle/oracle.py --online --discrete --property ovr_tloracle_property --port 18851
    echo "${pids[${#pids[@]}-1]}" > /results/oracle.pid
  fi
  if [ "${B2_EXECUTOR:-OFFICIAL}" = ST ]; then
    # Separately named diagnostic B2-ST: generated monitor with a single-threaded executor.
    start monitor python3 /code/ovr_full_guard_st.py
  else
    start monitor ros2 run monitor ovr_full_guard
  fi
  start stripper python3 /code/ovr_nodes.py
fi
if [ "$MODE" = b1 ] || [ "$MODE" = b3 ] || { [ "$MODE" = b2 ] && [ "${COMPOSED:-0}" = 1 ]; }; then
  start stop_adapter python3 /code/ovr_stop_adapter.py
fi
if [ -n "${CMON_FAULT:-}" ]; then
  start fault python3 /code/cmon_fault.py
fi
start production python3 /code/ovr_production.py
start resources python3 /code/resource_sampler.py
python3 /code/participant_entry.py recorder python3 /code/ovr_probe.py > /results/stdout/probe.log 2> /results/stderr/probe.log
for i in "${!pids[@]}"; do
  if [ "${CMON_FAULT:-}" = ORACLE_DISCONNECT ] && [ "${labels[$i]}" = oracle ]; then continue; fi
  assert_required_running "${pids[$i]}" "${labels[$i]}"
done
