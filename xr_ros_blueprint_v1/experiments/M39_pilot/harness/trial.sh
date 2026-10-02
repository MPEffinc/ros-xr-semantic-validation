#!/usr/bin/env bash
# One M39 trial (fresh container = fresh state). env: ARM (B0|B1|C1)  COND  TRIAL  QSTART "q1 .. q6"  SCEN (json path)
#   SCHED ("off on" seconds after T0, empty = no runtime deactivation)  END (capture end, s after T0)
# Stack: quest_teleop.py @170dad5 (B0/C1 original, B1 app copy) -> xrizer v3 (deployment component) -> Monado main
# 045931d (remote driver) ; [C1: /m39/app_cmd -> c1_transition] -> MoveIt Servo 2.12.4 -> JTC 4.42.1 -> Gazebo.
set -o pipefail; R=/results; mkdir -p $R /tmp/xdg; export XDG_RUNTIME_DIR=/tmp/xdg HOME=/tmp M39_HARNESS=/m39/harness
log(){ echo "[$(date +%s.%N) $(cat /proc/uptime | cut -d' ' -f1)] $*" >> $R/harness.log; }
cd /tmp && gcc -O2 -I/opt/monado/include -o mc /m39/harness/mnd_collector.c -L/opt/monado/lib -lmonado && gcc -O2 -I/opt/monado/include -o sched /m39/harness/mnd_sched.c -L/opt/monado/lib -lmonado || { echo '{"setup":"build_failed"}' > $R/setup.json; exit 3; }
mkdir -p /tmp/xrizer/bin/linux64 && cp /src/xrizer/target/release/libxrizer.so /tmp/xrizer/bin/linux64/vrclient.so
mkdir -p $HOME/.config/openvr && echo '{"version":1,"runtime":["/tmp/xrizer"]}' > $HOME/.config/openvr/openvrpaths.vrpath
source /opt/ros/jazzy/setup.bash; source /ws/install/setup.bash; export ROS_DOMAIN_ID=87 ROS_LOCALHOST_ONLY=1
export GZ_SIM_RESOURCE_PATH="/ws/install/ur5_description/share:${GZ_SIM_RESOURCE_PATH:-}"
pids=(); cleanup(){ for p in "${pids[@]}"; do kill -INT -- "-$p" 2>/dev/null; done; sleep 2; for p in "${pids[@]}"; do kill -KILL -- "-$p" 2>/dev/null; done; pkill -f monado-service; }
trap cleanup EXIT
wait_for(){ local d=$((SECONDS+$2)); until eval "$1" >/dev/null 2>&1; do [ $SECONDS -ge $d ] && { echo "{\"setup\":\"timeout\",\"step\":\"$3\"}" > $R/setup.json; exit 20; }; sleep 1; done; }
(while true; do echo "{\"wall\":$(date +%s.%N),\"load\":\"$(cut -d' ' -f1-3 /proc/loadavg)\",\"cpu\":\"$(head -1 /proc/stat)\"}"; sleep 1; done > $R/load.jsonl) & pids+=($!)
log bringup
setsid xvfb-run -a ros2 launch ur5_description gazebo.launch.py > $R/gazebo.log 2>&1 & pids+=($!)
wait_for "ros2 topic list | grep -qx /joint_states" 120 joint_states
setsid ros2 launch ur5_controller controller.launch.py is_sim:=True > $R/controller.log 2>&1 & pids+=($!)
wait_for "ros2 control list_controllers | grep -q 'ur5_arm_controller.*active'" 90 controller
setsid ros2 launch /m39/harness/servo_launch.py > $R/servo.log 2>&1 & pids+=($!)
wait_for "ros2 service list | grep -qx /servo_node/switch_command_type" 120 servo
sleep 3; timeout 20 ros2 service call /servo_node/switch_command_type moveit_msgs/srv/ServoCommandType "{command_type: 2}" > $R/switch.log 2>&1 || { echo '{"setup":"switch_failed"}' > $R/setup.json; exit 21; }
log start_setup
python3 /m39/harness/setup_start.py $R/setup_start.json $QSTART 6.0 > $R/setup_start.log 2>&1 || { echo '{"setup":"start_config_not_qualified"}' > $R/setup.json; exit 22; }
log start_ok
(sleep 60 | XRT_COMPOSITOR_NULL=1 P_OVERRIDE_ACTIVE_CONFIG=remote XRT_LOG=warn /opt/monado/bin/monado-service > $R/service.log 2>&1 &)
sleep 2
export P1_T0_NS=$(( $(date +%s%N) + 4000000000 )); T0=$(python3 -c "print($P1_T0_NS/1e9)")
echo "{\"setup\":\"ok\",\"t0\":$T0,\"t0_mono_offset_s\":$(python3 -c "import time;print(time.time()-time.monotonic())"),\"arm\":\"$ARM\",\"cond\":\"$COND\",\"trial\":\"$TRIAL\",\"sched\":\"$SCHED\",\"load\":\"$(cut -d' ' -f1-3 /proc/loadavg)\"}" > $R/setup.json
cp $SCEN $R/scenario.json
python3 /m39/harness/remote_feeder.py $SCEN $T0 $R/feeder.jsonl > $R/feeder.log 2>&1 &
mkfifo /tmp/ev.fifo
/tmp/mc 0.005 40 | tee $R/collector.jsonl > /tmp/ev.fifo &
P1_EE_FRAME=wrist_3_link setsid python3 /m39/harness/observer.py $R/observer.jsonl $END > $R/observer.log 2>&1 & obs=$!; pids+=($obs)
case "$ARM" in
  B0) cat /tmp/ev.fifo > /dev/null &
      XRIZER_F3_LEGACY_ON_TEMP=1 setsid /ws/install/quest_bridge/lib/quest_bridge/quest_teleop > $R/app.log 2>&1 & pids+=($!) ;;
  B1) XRIZER_F3_LEGACY_ON_TEMP=1 M39_ARM_LOG=$R/arm.jsonl M39_EV_FIFO=/tmp/ev.fifo setsid python3 /m39/arms/quest_teleop_b1.py > $R/app.log 2>&1 & pids+=($!) ;;
  C1) setsid python3 /m39/arms/c1_transition.py $R/arm.jsonl /tmp/ev.fifo $END > $R/c1.log 2>&1 & pids+=($!)
      XRIZER_F3_LEGACY_ON_TEMP=1 setsid /ws/install/quest_bridge/lib/quest_bridge/quest_teleop --ros-args -r /servo_node/pose_target_cmds:=/m39/app_cmd > $R/app.log 2>&1 & pids+=($!) ;;
esac
[ -n "$SCHED" ] && /tmp/sched python3.12 $T0 $SCHED > $R/sched.jsonl 2>&1 &
wait $obs; log done; echo "{\"done\":true,\"load\":\"$(cut -d' ' -f1-3 /proc/loadavg)\"}" > $R/done.json
