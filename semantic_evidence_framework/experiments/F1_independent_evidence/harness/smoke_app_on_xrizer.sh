#!/usr/bin/env bash
# Feasibility smoke (not a measured trial): unmodified quest_teleop.py on xrizer on Monado main.
R=/results; mkdir -p $R /tmp/xdg; export XDG_RUNTIME_DIR=/tmp/xdg HOME=/tmp
mkdir -p /tmp/xrizer/bin/linux64 && cp /src/xrizer/target/release/libxrizer.so /tmp/xrizer/bin/linux64/vrclient.so
mkdir -p $HOME/.config/openvr && echo '{"version":1,"runtime":["/tmp/xrizer"]}' > $HOME/.config/openvr/openvrpaths.vrpath
(sleep 60 | XRT_COMPOSITOR_NULL=1 P_OVERRIDE_ACTIVE_CONFIG=remote XRT_LOG=info /opt/monado/bin/monado-service > $R/service.log 2>&1 &)
sleep 3; T0=$(date +%s.%N)
python3 /f1/harness/remote_feeder.py /f1/scenarios/SMOKE.json $T0 $R/feeder.jsonl &
gcc -O2 -I/opt/monado/include -o /tmp/mc /f1/collector/mnd_collector.c -L/opt/monado/lib -lmonado && /tmp/mc 0.02 25 > $R/collector.jsonl 2>$R/collector.err &
source /opt/ros/jazzy/setup.bash; source /ws/install/setup.bash; export ROS_DOMAIN_ID=79 ROS_LOCALHOST_ONLY=1
python3 /f1/harness/count_cmds.py /servo_node/pose_target_cmds $R/cmds.jsonl 22 &
sleep 1; timeout 20 /ws/install/quest_bridge/lib/quest_bridge/quest_teleop > $R/app.log 2>&1
sleep 2; /opt/monado/bin/monado-ctl > $R/ctl.txt 2>&1; wait
