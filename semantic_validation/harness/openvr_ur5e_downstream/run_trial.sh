#!/usr/bin/env bash
# One downstream trial for the pinned OpenVR UR5e target.
#
#   run_trial.sh <trial_id> <valid> <tracking_result> <motion_z> <result_dir> [run_teleop]
#
# Each trial gets a FRESH Gazebo/controller/Servo bring-up so that every trial
# starts the simulated arm from the same configuration.  The pinned launch
# files are used unmodified; only the OpenVR dependency is faked, upstream of
# every production decision in quest_teleop.py.
#
# No ur_robot_driver, no robot_ip, no physical hardware is involved: the pinned
# repository contains no such path.
set -o pipefail

trial_id="${1:?trial id}"
valid="${2:?valid}"
tracking_result="${3:?tracking result}"
motion_z="${4:?motion step}"
result_dir="${5:?result dir}"
run_teleop="${6:-true}"

mkdir -p "${result_dir}"
log() { echo "[trial ${trial_id}] $*" | tee -a "${result_dir}/${trial_id}_harness.log"; }

source /opt/ros/jazzy/setup.bash
source /ws/install/setup.bash

export ROS_DOMAIN_ID="${ROS_DOMAIN_ID:-98}"
export GZ_SIM_RESOURCE_PATH="/ws/install/ur5_description/share:${GZ_SIM_RESOURCE_PATH:-}"

pids=()
cleanup() {
  log "cleanup"
  for pid in "${pids[@]:-}"; do
    [ -n "${pid}" ] && kill -INT -- "-${pid}" 2>/dev/null
  done
  sleep 3
  for pid in "${pids[@]:-}"; do
    [ -n "${pid}" ] && kill -KILL -- "-${pid}" 2>/dev/null
  done
  pkill -KILL -f 'gz sim' 2>/dev/null
  pkill -KILL -f ruby 2>/dev/null
  pkill -KILL -f quest_teleop 2>/dev/null
  pkill -KILL -f servo_node 2>/dev/null
  pkill -KILL -f ros2_control_node 2>/dev/null
  sleep 2
}
trap cleanup EXIT

# --- 1. Gazebo + robot_state_publisher + spawn + gz bridge --------------------
log "starting gazebo"
setsid xvfb-run -a ros2 launch ur5_description gazebo.launch.py \
  >"${result_dir}/${trial_id}_gazebo.log" 2>&1 &
pids+=($!)

# Wait for the simulated robot's joint feedback to appear.
deadline=$((SECONDS + 120))
until ros2 topic list 2>/dev/null | grep -qx '/joint_states'; do
  if [ "${SECONDS}" -ge "${deadline}" ]; then
    log "FAIL: /joint_states never appeared"
    exit 10
  fi
  sleep 2
done
log "/joint_states present after $((SECONDS))s"

# --- 2. ros2_control spawners ------------------------------------------------
log "starting controllers"
setsid ros2 launch ur5_controller controller.launch.py is_sim:=True \
  >"${result_dir}/${trial_id}_controller.log" 2>&1 &
pids+=($!)

deadline=$((SECONDS + 90))
until ros2 control list_controllers 2>/dev/null | grep -q 'ur5_arm_controller.*active'; do
  if [ "${SECONDS}" -ge "${deadline}" ]; then
    log "FAIL: ur5_arm_controller not active"
    ros2 control list_controllers >>"${result_dir}/${trial_id}_harness.log" 2>&1
    exit 11
  fi
  sleep 2
done
ros2 control list_controllers >"${result_dir}/${trial_id}_controllers.txt" 2>&1
log "ur5_arm_controller active"

# --- 3. MoveIt Servo ---------------------------------------------------------
log "starting servo"
setsid ros2 launch ur5_moveit_config ur5_servo.launch.py \
  >"${result_dir}/${trial_id}_servo.log" 2>&1 &
pids+=($!)

deadline=$((SECONDS + 120))
until ros2 node list 2>/dev/null | grep -q '/servo_node'; do
  if [ "${SECONDS}" -ge "${deadline}" ]; then
    log "FAIL: /servo_node never appeared"
    exit 12
  fi
  sleep 2
done
sleep 8
ros2 node list >"${result_dir}/${trial_id}_nodes.txt" 2>&1
ros2 topic list >"${result_dir}/${trial_id}_topics.txt" 2>&1
log "servo_node present"

# Servo accepts pose commands only in POSE command mode.  Switching mode is the
# documented operator-facing service call, not a source change.  Record the
# attempt and its outcome either way.
{
  echo "--- switch_command_type service list ---"
  ros2 service list | grep -i servo || true
  echo "--- switch to POSE (2) ---"
  timeout 20 ros2 service call /servo_node/switch_command_type \
    moveit_msgs/srv/ServoCommandType "{command_type: 2}" || echo "SWITCH_CALL_FAILED"
} >"${result_dir}/${trial_id}_switch.log" 2>&1
log "command-type switch attempted"

# --- 4. Capture + production node -------------------------------------------
log "capture start"
setsid python3 /harness/capture_downstream.py --duration 14 \
  --out "${result_dir}/${trial_id}_downstream.json" \
  >"${result_dir}/${trial_id}_capture.log" 2>&1 &
capture_pid=$!
pids+=("${capture_pid}")
sleep 2

if [ "${run_teleop}" = "true" ]; then
  log "starting production quest_teleop (valid=${valid} tracking=${tracking_result} motion_z=${motion_z})"
  OPENVR_FAKE_VALID="${valid}" \
  OPENVR_FAKE_TRACKING_RESULT="${tracking_result}" \
  OPENVR_FAKE_GRIP=true \
  OPENVR_FAKE_MOTION_Z="${motion_z}" \
  OPENVR_FAKE_MOTION_MAX_STEPS=300 \
  PYTHONPATH="/harness:${PYTHONPATH:-}" \
    setsid /ws/install/quest_bridge/lib/quest_bridge/quest_teleop \
      >"${result_dir}/${trial_id}_node.log" 2>&1 &
  pids+=($!)
else
  log "baseline trial: production node NOT started"
fi

wait "${capture_pid}"
log "capture done"
exit 0
