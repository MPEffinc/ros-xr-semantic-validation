#!/usr/bin/env bash
R=/results; mkdir -p $R /tmp/xdg; export XDG_RUNTIME_DIR=/tmp/xdg HOME=/tmp
cd /tmp && gcc -O2 -o sa /f2/collector/sa_client.c -lopenxr_loader && gcc -O2 -I/opt/monado/include -o mc /f2/collector/mnd_collector.c -L/opt/monado/lib -lmonado && gcc -O2 -I/opt/monado/include -o sched /f2/collector/mnd_sched.c -L/opt/monado/lib -lmonado || exit 3
(sleep 30 | XRT_COMPOSITOR_NULL=1 P_OVERRIDE_ACTIVE_CONFIG=remote XRT_LOG=warn /opt/monado/bin/monado-service > $R/service.log 2>&1 &)
sleep 3; T0=$(python3 -c 'import time;print(time.time()+3.0)'); echo "{\"t0\":$T0}" > $R/setup.json
echo '{"duration": 25, "grip": [[0.5, 25]]}' > /tmp/sc.json; python3 /f2/harness/remote_feeder.py /tmp/sc.json $T0 $R/feeder.jsonl &
/tmp/mc 0.005 18 > $R/collector.jsonl &
/tmp/sa 18 sa_main > $R/sa_main.jsonl 2>/dev/null &
/tmp/sched sa_main $T0 3.000 3.005 4.000 4.010 5.000 5.020 6.000 6.040 7.000 7.005 8.000 8.010 9.000 9.020 10.000 10.040 > $R/sched.jsonl
wait
