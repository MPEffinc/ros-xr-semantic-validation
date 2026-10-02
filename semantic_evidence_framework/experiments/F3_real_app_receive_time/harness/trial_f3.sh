#!/usr/bin/env bash
# One F3 trial: UNMODIFIED quest_teleop.py -> (xrizer v3, a patched deployment component) -> Monado main (unmodified)
# -> [B0: direct | GATED: receive-time-state gate] -> MoveIt Servo 2.12.4 -> Gazebo.  env: ARM (B0|GATED), TRIAL
set -o pipefail; R=/results; mkdir -p $R /tmp/xdg; export XDG_RUNTIME_DIR=/tmp/xdg HOME=/tmp
log(){ echo "[$(date +%s.%N)] $*" >> $R/harness.log; }
cd /tmp && gcc -O2 -I/opt/monado/include -o mc /f3/harness/mnd_collector.c -L/opt/monado/lib -lmonado && gcc -O2 -I/opt/monado/include -o sched /f3/harness/mnd_sched.c -L/opt/monado/lib -lmonado || exit 3
mkdir -p /tmp/xrizer/bin/linux64 && cp /src/xrizer/target/release/libxrizer.so /tmp/xrizer/bin/linux64/vrclient.so
mkdir -p $HOME/.config/openvr && echo '{"version":1,"runtime":["/tmp/xrizer"]}' > $HOME/.config/openvr/openvrpaths.vrpath
source /opt/ros/jazzy/setup.bash; source /ws/install/setup.bash; export ROS_DOMAIN_ID=86 ROS_LOCALHOST_ONLY=1
export GZ_SIM_RESOURCE_PATH="/ws/install/ur5_description/share:${GZ_SIM_RESOURCE_PATH:-}"
pids=(); cleanup(){ for p in "${pids[@]}"; do kill -INT -- "-$p" 2>/dev/null; done; sleep 2; for p in "${pids[@]}"; do kill -KILL -- "-$p" 2>/dev/null; done; pkill -f monado-service; }
trap cleanup EXIT
wait_for(){ local d=$((SECONDS+$2)); until eval "$1" >/dev/null 2>&1; do [ $SECONDS -ge $d ] && { echo "{\"setup\":\"timeout\",\"step\":\"$3\"}" > $R/setup.json; exit 20; }; sleep 1; done; }
setsid xvfb-run -a ros2 launch ur5_description gazebo.launch.py > $R/gazebo.log 2>&1 & pids+=($!)
wait_for "ros2 topic list | grep -qx /joint_states" 120 joint_states
setsid ros2 launch ur5_controller controller.launch.py is_sim:=True > $R/controller.log 2>&1 & pids+=($!)
wait_for "ros2 control list_controllers | grep -q 'ur5_arm_controller.*active'" 90 controller
setsid ros2 launch /f3/harness/servo_launch.py > $R/servo.log 2>&1 & pids+=($!)
wait_for "ros2 service list | grep -qx /servo_node/switch_command_type" 120 servo
sleep 3; timeout 20 ros2 service call /servo_node/switch_command_type moveit_msgs/srv/ServoCommandType "{command_type: 2}" > $R/switch.log 2>&1 || { echo '{"setup":"switch_failed"}' > $R/setup.json; exit 21; }
(sleep 60 | XRT_COMPOSITOR_NULL=1 P_OVERRIDE_ACTIVE_CONFIG=remote XRT_LOG=warn /opt/monado/bin/monado-service > $R/service.log 2>&1 &)
sleep 2
export P1_T0_NS=$(( $(date +%s%N) + 4000000000 )); T0=$(python3 -c "print($P1_T0_NS/1e9)")
echo "{\"setup\":\"ok\",\"t0\":$T0,\"arm\":\"$ARM\",\"trial\":\"$TRIAL\",\"load\":\"$(cut -d' ' -f1-3 /proc/loadavg)\"}" > $R/setup.json
echo '{"duration": 40, "grip": [[2.0, 40]], "motion_x": [[4.0, 7.0, 0.05], [8.5, 9.2, 0.10], [11.0, 13.0, 0.05]]}' > /tmp/sc.json
python3 /f3/harness/remote_feeder.py /tmp/sc.json $T0 $R/feeder.jsonl > /dev/null 2>&1 &
mkfifo /tmp/ev.fifo
if [ "$ARM" = GATED ]; then python3 /f3/harness/gate_rt.py /tmp/ev.fifo $R/gate.jsonl $T0 python3.12 16.5 > $R/gate.log 2>&1 & pids+=($!); else cat /tmp/ev.fifo > /dev/null & fi
/tmp/mc 0.005 30 | tee $R/collector.jsonl > /tmp/ev.fifo &
P1_EE_FRAME=wrist_3_link setsid python3 /f3/harness/observer.py $R/observer.jsonl 16.5 > $R/observer.log 2>&1 & obs=$!; pids+=($obs)
ARGS=(); [ "$ARM" = GATED ] && ARGS=(--ros-args -r /servo_node/pose_target_cmds:=/f3/app_cmd)
XRIZER_F3_LEGACY_ON_TEMP=1 setsid /ws/install/quest_bridge/lib/quest_bridge/quest_teleop "${ARGS[@]}" > $R/app.log 2>&1 & pids+=($!)
/tmp/sched python3.12 $T0 8.000 9.500 > $R/sched.jsonl 2>&1 &
wait $obs; log done; echo '{"done":true}' > $R/done.json
