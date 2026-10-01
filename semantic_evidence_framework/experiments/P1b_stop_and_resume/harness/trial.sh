#!/usr/bin/env bash
# One P1b trial inside a fresh openvr-jazzy-sim:local container (--network none).
#   env: P1_CASE P1_DEFENSE P1_TRIAL (set by run_pilot.py); scenario in /p1/scenarios/<case>.json
# Fresh Gazebo + controllers + Servo per trial; pinned target launch files and the unmodified
# quest_teleop entry point are used, with only the OpenVR module faked (PYTHONPATH).
set -o pipefail
R=/results; mkdir -p "$R"
log() { echo "[$(date +%s.%N)] $*" >> "$R/harness.log"; }
source /opt/ros/jazzy/setup.bash
source /ws/install/setup.bash
export ROS_DOMAIN_ID=77 ROS_LOCALHOST_ONLY=1
export GZ_SIM_RESOURCE_PATH="/ws/install/ur5_description/share:${GZ_SIM_RESOURCE_PATH:-}"
pids=()
cleanup() { for p in "${pids[@]}"; do kill -INT -- "-$p" 2>/dev/null; done; sleep 2;
            for p in "${pids[@]}"; do kill -KILL -- "-$p" 2>/dev/null; done; }
trap cleanup EXIT
wait_for() { local d=$((SECONDS+$2)); until eval "$1" >/dev/null 2>&1; do
  [ $SECONDS -ge $d ] && { log "TIMEOUT: $1"; echo "{\"setup\":\"timeout\",\"step\":\"$3\"}" > "$R/setup.json"; exit 20; }; sleep 1; done; }

log "gazebo"; setsid xvfb-run -a ros2 launch ur5_description gazebo.launch.py > "$R/gazebo.log" 2>&1 & pids+=($!)
wait_for "ros2 topic list | grep -qx /joint_states" 120 joint_states
log "controllers"; setsid ros2 launch ur5_controller controller.launch.py is_sim:=True > "$R/controller.log" 2>&1 & pids+=($!)
wait_for "ros2 control list_controllers | grep -q 'ur5_arm_controller.*active'" 90 controller
log "servo"; setsid ros2 launch /p1/harness/servo_launch.py > "$R/servo.log" 2>&1 & pids+=($!)
wait_for "ros2 service list | grep -qx /servo_node/switch_command_type" 120 servo
sleep 3
timeout 20 ros2 service call /servo_node/switch_command_type moveit_msgs/srv/ServoCommandType "{command_type: 2}" > "$R/switch.log" 2>&1 \
  || { echo '{"setup":"switch_failed"}' > "$R/setup.json"; exit 21; }
ros2 param get /servo_node moveit_servo.incoming_command_timeout > "$R/servo_timeout.txt" 2>&1

# Scenario clock starts 3 s from now (all processes share P1_T0_NS).
export P1_T0_NS=$(( $(date +%s%N) + 3000000000 ))
export P1_SCENARIO="/p1/scenarios/${P1_CASE}.json" PYTHONPATH="/p1/harness:${PYTHONPATH:-}"
echo "{\"setup\":\"ok\",\"t0_ns\":$P1_T0_NS,\"case\":\"$P1_CASE\",\"defense\":\"$P1_DEFENSE\",\"trial\":\"$P1_TRIAL\",\"load\":\"$(cut -d' ' -f1-3 /proc/loadavg)\"}" > "$R/setup.json"
log "barrier t0=$P1_T0_NS"
setsid python3 /p1/harness/observer.py "$R/observer.jsonl" 12.5 > "$R/observer.log" 2>&1 & obs=$!; pids+=($obs)
APP=/ws/install/quest_bridge/lib/quest_bridge/quest_teleop
case "$P1_DEFENSE" in
  B0|D_TO) ARGS=() ;;
  EPOCH_A) APP="python3 /p1/harness/quest_teleop_epoch.py"; ARGS=() ;;
  *) ARGS=(--ros-args -r /servo_node/pose_target_cmds:=/p1/app_cmd)
     P1_GATE_LOG="$R/gate.jsonl" P1_OPENVR_LOG="$R/openvr_gate.jsonl" setsid python3 /p1/harness/evidence_gate.py > "$R/gate.log" 2>&1 & pids+=($!) ;;
esac
P1_OPENVR_LOG="$R/openvr_app.jsonl" setsid $APP "${ARGS[@]}" > "$R/app.log" 2>&1 & pids+=($!)
wait $obs
log "done"
echo '{"done":true}' > "$R/done.json"
