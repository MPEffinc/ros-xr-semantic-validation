#!/usr/bin/env bash
# One F1 linkage run. env: CASE (K1..K6), RUN. Frozen schedule: PROTOCOL_LINKAGE.md §4.
R=/results; mkdir -p $R /tmp/xdg; export XDG_RUNTIME_DIR=/tmp/xdg HOME=/tmp
cd /tmp && gcc -O2 -o sa /f1/collector/sa_client.c -lopenxr_loader && gcc -O2 -I/opt/monado/include -o mc /f1/collector/mnd_collector.c -L/opt/monado/lib -lmonado \
  && gcc -O2 -I/opt/monado/include -o ctl /f1/collector/mnd_ctl.c -L/opt/monado/lib -lmonado || exit 3
source /opt/ros/jazzy/setup.bash; export ROS_DOMAIN_ID=83 ROS_LOCALHOST_ONLY=1
(sleep 40 | XRT_COMPOSITOR_NULL=1 P_OVERRIDE_ACTIVE_CONFIG=remote XRT_LOG=warn /opt/monado/bin/monado-service > $R/service.log 2>&1 &)
sleep 3
GRIP='[[1, 15]]'; [ "$CASE" = K6 ] && GRIP='[[1, 6]]'
EVD=0; [ "$CASE" = K5b ] && EVD=0.030
T0=$(python3 -c 'import time;print(time.time()+4.0)'); echo "{\"t0\":$T0,\"case\":\"$CASE\",\"run\":\"$RUN\",\"load\":\"$(cut -d' ' -f1-3 /proc/loadavg)\"}" > $R/setup.json
echo "{\"duration\": 30, \"grip\": $GRIP}" > /tmp/sc.json
python3 /f1/harness/remote_feeder.py /tmp/sc.json $T0 $R/feeder.jsonl &
mkfifo /tmp/ev.fifo
python3 /f1/harness/gate.py /tmp/ev.fifo $R/gate.jsonl $T0 $EVD sa_main > $R/gate.log 2>&1 &
/tmp/mc 0.005 25 | tee $R/collector.jsonl > /tmp/ev.fifo &
sleep 0.2; MC=$(pgrep -x mc | head -1)
/tmp/sa 22 sa_main > $R/sa_main.jsonl 2> $R/sa_main.err &
[ "$CASE" = K4 ] && { sleep 0.3; /tmp/sa 22 sa_other > $R/sa_other.jsonl 2> $R/sa_other.err & }
python3 /f1/harness/app_state.py $R/sa_main.jsonl $T0 > $R/app_state.log 2>&1 &
python3 /f1/harness/injector.py $CASE $T0 $R/sa_main.jsonl $R/injector.jsonl > $R/injector.log 2>&1 &
at(){ python3 -c "import time,sys;d=$T0+$1-time.time();time.sleep(max(0,d))"; }
act(){ echo "{\"wall\":$(date +%s.%N),\"action\":\"$1\"}" >> $R/actions.jsonl; }
case $CASE in
  K1|K3c) ;;
  K5a) at 5.0; kill -STOP $MC; act collector_stop; at 6.0; kill -CONT $MC; act collector_cont ;;
  *) at 5.0; act "io_off_call"; /tmp/ctl io sa_main >> $R/ctl.jsonl; act "io_off_done"; at 7.0; act "io_on_call"; /tmp/ctl io sa_main >> $R/ctl.jsonl; act "io_on_done" ;;
esac
at 14.5; wait
