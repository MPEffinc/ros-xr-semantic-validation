#!/usr/bin/env bash
# One F2 run. env: CASE, RUN. Frozen tables: harness/cases.py, PROTOCOL_F2.md.
R=/results; mkdir -p $R /tmp/xdg; export XDG_RUNTIME_DIR=/tmp/xdg HOME=/tmp
cd /tmp && gcc -O2 -o sa /f2/collector/sa_client.c -lopenxr_loader && gcc -O2 -I/opt/monado/include -o mc /f2/collector/mnd_collector.c -L/opt/monado/lib -lmonado \
  && gcc -O2 -I/opt/monado/include -o sched /f2/collector/mnd_sched.c -L/opt/monado/lib -lmonado || exit 3
source /opt/ros/jazzy/setup.bash; export ROS_DOMAIN_ID=84 ROS_LOCALHOST_ONLY=1
(sleep 40 | XRT_COMPOSITOR_NULL=1 P_OVERRIDE_ACTIVE_CONFIG=remote XRT_LOG=warn /opt/monado/bin/monado-service > $R/service.log 2>&1 &)
sleep 3
T0=$(python3 -c 'import time;print(time.time()+4.0)')
EVD=$(python3 -c "import sys;sys.path.insert(0,'/f2/harness');import cases;print(cases.evidence_delay('$CASE'))")
WIN=$(python3 -c "import sys;sys.path.insert(0,'/f2/harness');import cases;print(' '.join(f'{a:.3f} {b:.3f}' for a,b in cases.windows('$CASE')))")
echo "{\"t0\":$T0,\"case\":\"$CASE\",\"run\":\"$RUN\",\"evidence_delay\":$EVD,\"load\":\"$(cut -d' ' -f1-3 /proc/loadavg)\"}" > $R/setup.json
echo '{"duration": 30, "grip": [[0.5, 30]]}' > /tmp/sc.json; python3 /f2/harness/remote_feeder.py /tmp/sc.json $T0 $R/feeder.jsonl &
mkfifo /tmp/ev.fifo
python3 /f2/harness/gate.py /tmp/ev.fifo $R/gate.jsonl $T0 $EVD sa_main > $R/gate.log 2>&1 &
/tmp/mc 0.005 26 | tee $R/collector.jsonl > /tmp/ev.fifo &
/tmp/sa 24 sa_main > $R/sa_main.jsonl 2> $R/sa_main.err &
python3 /f2/harness/injector.py $CASE $T0 $R/injector.jsonl > $R/injector.log 2>&1 &
[ -n "$WIN" ] && { /tmp/sched sa_main $T0 $WIN > $R/sched.jsonl 2>&1 & }
python3 - <<PY &
import os, signal, subprocess, sys, time, json
sys.path.insert(0, '/f2/harness'); import cases
t0 = $T0; log = open('$R/outage.jsonl', 'w', buffering=1)
for a, b in cases.outages('$CASE'):
    time.sleep(max(0, t0 + a - time.time())); pid = int(subprocess.check_output(['pgrep', '-x', 'mc']).split()[0])
    os.kill(pid, signal.SIGSTOP); log.write(json.dumps({"stop": time.time()}) + "\n")
    time.sleep(max(0, t0 + b - time.time())); os.kill(pid, signal.SIGCONT); log.write(json.dumps({"cont": time.time()}) + "\n")
PY
python3 -c "import time;time.sleep(max(0,$T0+15.8-time.time()))"; wait
