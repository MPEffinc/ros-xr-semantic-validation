#!/usr/bin/env bash
# One M12_receiver trial (component level; no XR runtime, no Quest frontend): producer -> receiver (B0 original
# @64cbdde, or B1 patched copy) -> gate. env: ARM (B0|B1) COND SCEN END
set -o pipefail; R=/results; source /opt/ros/humble/setup.bash; source /build/install/setup.bash
export ROS_DOMAIN_ID=90 ROS_LOCALHOST_ONLY=1 HOME=/tmp
pids=(); cleanup(){ for p in "${pids[@]}"; do kill -INT -- "-$p" 2>/dev/null; done; sleep 1; for p in "${pids[@]}"; do kill -KILL -- "-$p" 2>/dev/null; done; }
trap cleanup EXIT
if [ "$ARM" = B1 ]; then setsid python3 /build/b1/quest_controller_receiver_b1.py > $R/receiver.log 2>&1 & pids+=($!)
else setsid ros2 run receiver quest_controller_receiver > $R/receiver.log 2>&1 & pids+=($!); fi
sleep 3; T0=$(python3 -c "import time;print(time.time()+2)")
echo "{\"setup\":\"ok\",\"t0\":$T0,\"arm\":\"$ARM\",\"cond\":\"$COND\",\"load\":\"$(cut -d' ' -f1-3 /proc/loadavg)\",\"build_sha\":\"$(tr '\n' ' ' < /build/BUILD_SHA256.txt)\"}" > $R/setup.json
cp $SCEN $R/scenario.json
setsid python3 /m12r/harness/r_gate.py $ARM $R/gate.jsonl $T0 $END > $R/gate.log 2>&1 & g=$!; pids+=($g)
python3 /m12r/harness/producer.py $SCEN $T0 $R/producer.jsonl $ARM > $R/producer.log 2>&1
wait $g; echo '{"done":true}' > $R/done.json
