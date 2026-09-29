#!/bin/bash
set -x
source /opt/ros/humble/setup.bash
source /wk/ws/install/setup.bash
export ROS_DOMAIN_ID=72
export ROS_LOCALHOST_ONLY=1
ros2 run xr_hand_pipeline hand_ws_publisher > /wk/out/bridge.log 2>&1 &
BRIDGE=$!
sleep 5
python3 /wk/harness/vr_hand_bridge_ws_trials.py --out-dir /wk/out > /wk/out/harness.log 2>&1
RC=$?
sleep 1
if kill -0 $BRIDGE 2>/dev/null; then echo "BRIDGE_ALIVE_AFTER_TRIALS=yes" >> /wk/out/bridge_state.txt; else echo "BRIDGE_ALIVE_AFTER_TRIALS=no" >> /wk/out/bridge_state.txt; fi
ros2 topic list >> /wk/out/bridge_state.txt 2>&1
kill $BRIDGE 2>/dev/null
wait $BRIDGE 2>/dev/null
exit $RC
